"""Unit and integration tests for calibration, Brier decomposition, and lead-time analysis."""
from __future__ import annotations

import csv
import json
import math
from pathlib import Path
import pytest
import numpy as np

from flood_sentinel.calibration import (
    compute_calibration_curve,
    decompose_brier_score,
    TrainPlattCalibrator,
    IsotonicCalibrator,
    out_of_fold_calibration,
)
from flood_sentinel.lead_time import (
    evaluate_warning_lead_times,
    LeadTimeSummary,
    LeadTimeRecord,
)
from source.runners.run_postprocessing import (
    find_latest_runs_dir,
    load_cohort_split_map,
    analyze_run,
    run_all_postprocessing,
)


@pytest.fixture
def root_dir() -> Path:
    return Path(__file__).resolve().parents[2]


# ---------------------------------------------------------------------------
# Calibration Curve & Error Tests
# ---------------------------------------------------------------------------

def test_compute_calibration_curve_uniform() -> None:
    y_true = [0, 0, 0, 0, 1, 1, 1, 1]
    y_prob = [0.1, 0.15, 0.2, 0.25, 0.75, 0.8, 0.85, 0.9]

    res = compute_calibration_curve(y_true, y_prob, n_bins=4, strategy="uniform")

    assert res.n_samples == 8
    assert len(res.bin_confs) == 4
    assert len(res.bin_accs) == 4
    assert len(res.bin_counts) == 4

    for conf, acc, cnt in zip(res.bin_confs, res.bin_accs, res.bin_counts):
        assert 0.0 <= conf <= 1.0
        assert 0.0 <= acc <= 1.0
        assert cnt >= 0

    assert 0.0 <= res.expected_calibration_error <= 1.0
    assert 0.0 <= res.maximum_calibration_error <= 1.0
    assert 0.0 <= res.root_mean_squared_calibration_error <= 1.0


def test_compute_calibration_curve_quantile() -> None:
    y_true = [0, 0, 1, 1]
    y_prob = [0.1, 0.4, 0.6, 0.9]

    res = compute_calibration_curve(y_true, y_prob, n_bins=2, strategy="quantile")
    assert res.n_samples == 4
    assert len(res.bin_confs) == 2
    # Both quantile bins must have samples
    assert res.bin_counts[0] == 2
    assert res.bin_counts[1] == 2


def test_calibration_curve_perfect_calibration() -> None:
    # Construct synthetic data where accuracy matches confidence in each bin
    # Bin 1: prob = 0.2, 1 pos, 4 neg -> acc = 0.2
    # Bin 2: prob = 0.8, 4 pos, 1 neg -> acc = 0.8
    y_prob = [0.2] * 5 + [0.8] * 5
    y_true = [1, 0, 0, 0, 0] + [1, 1, 1, 1, 0]

    res = compute_calibration_curve(y_true, y_prob, n_bins=5, strategy="uniform")
    # For occupied bins, |acc - conf| = 0
    assert math.isclose(res.expected_calibration_error, 0.0, abs_tol=1e-7)
    assert math.isclose(res.maximum_calibration_error, 0.0, abs_tol=1e-7)


def test_calibration_curve_input_validation() -> None:
    with pytest.raises(ValueError, match="aligned 1D sequences"):
        compute_calibration_curve([0, 1], [0.5])

    with pytest.raises(ValueError, match="empty"):
        compute_calibration_curve([], [])

    with pytest.raises(ValueError, match="n_bins must be >= 2"):
        compute_calibration_curve([0, 1], [0.2, 0.8], n_bins=0)

    with pytest.raises(ValueError, match="strategy must be"):
        compute_calibration_curve([0, 1], [0.2, 0.8], strategy="invalid")


# ---------------------------------------------------------------------------
# Murphy (1973) Brier Score Decomposition Tests
# ---------------------------------------------------------------------------

def test_murphy_brier_exact_algebraic_identity() -> None:
    # Test across random probability configurations
    np.random.seed(42)
    for _ in range(5):
        y_true = np.random.choice([0, 1], size=100, p=[0.7, 0.3]).tolist()
        y_prob = np.random.uniform(0.01, 0.99, size=100).tolist()

        res = decompose_brier_score(y_true, y_prob, n_bins=10, strategy="uniform")

        # Murphy partition: BS_binned = REL - RES + UNC
        murphy_sum = res.reliability - res.resolution + res.uncertainty
        diff = abs(res.brier_score_binned - murphy_sum)
        assert diff < 1e-12, f"Murphy partition failed: {res.brier_score_binned} != {murphy_sum} (diff={diff})"

        # Uncertainty check: p_bar * (1 - p_bar)
        p_bar = sum(y_true) / len(y_true)
        expected_unc = p_bar * (1.0 - p_bar)
        assert math.isclose(res.uncertainty, expected_unc, abs_tol=1e-12)


def test_murphy_brier_skill_score() -> None:
    # Good forecast (lower Brier than climatology) -> positive BSS
    y_true = [0, 0, 0, 0, 1, 1, 1, 1]
    y_prob = [0.05, 0.1, 0.1, 0.15, 0.85, 0.9, 0.9, 0.95]
    res = decompose_brier_score(y_true, y_prob, n_bins=4)
    assert res.brier_skill_score > 0.0

    # Constant climatology forecast -> BSS = 0
    p_bar = sum(y_true) / len(y_true)
    res_clim = decompose_brier_score(y_true, [p_bar] * len(y_true), n_bins=4)
    assert math.isclose(res_clim.brier_skill_score, 0.0, abs_tol=1e-5)


# ---------------------------------------------------------------------------
# Calibrators: Platt and Isotonic Tests
# ---------------------------------------------------------------------------

def test_train_platt_calibrator_properties() -> None:
    scores = [-3.0, -1.0, 0.5, 2.0]
    labels = [0, 0, 1, 1]

    cal = TrainPlattCalibrator().fit(scores, labels)

    # Constraint: slope w >= 0.01
    assert cal.w >= 0.01

    probs = cal.predict_proba(scores)
    assert len(probs) == len(scores)

    # Strictly bounded in (0, 1)
    for p in probs:
        assert 0.0 < p < 1.0

    # Monotonicity: preserving ranks
    assert probs[0] < probs[1] < probs[2] < probs[3]

    # Serialization roundtrip
    d = cal.to_dict()
    cal2 = TrainPlattCalibrator.from_dict(d)
    np.testing.assert_allclose(probs, cal2.predict_proba(scores))


def test_isotonic_calibrator_monotonicity() -> None:
    scores = [-2.0, -1.0, 0.0, 1.0, 2.0]
    labels = [0, 0, 1, 0, 1]

    cal = IsotonicCalibrator().fit(scores, labels)
    probs = cal.predict_proba(scores)

    # Must be non-decreasing
    for i in range(len(probs) - 1):
        assert probs[i] <= probs[i + 1]
        assert 0.0 <= probs[i] <= 1.0
    assert 0.0 <= probs[-1] <= 1.0


def test_out_of_fold_calibration() -> None:
    scores = [-2.0, -1.5, -1.0, -0.5, 0.5, 1.0, 1.5, 2.0]
    labels = [0, 0, 0, 0, 1, 1, 1, 1]

    oof_probs, master_cal = out_of_fold_calibration(
        scores, labels, calibrator_cls=TrainPlattCalibrator, n_splits=4, seed=42
    )

    assert len(oof_probs) == len(scores)
    assert isinstance(master_cal, TrainPlattCalibrator)
    for p in oof_probs:
        assert 0.0 < p < 1.0


# ---------------------------------------------------------------------------
# Lead-Time Analysis Tests
# ---------------------------------------------------------------------------

def test_evaluate_warning_lead_times_on_authentic_intervals(root_dir: Path) -> None:
    intervals_path = root_dir / "data/event_intervals.csv"
    assert intervals_path.is_file(), "Missing data/event_intervals.csv"

    # Test alerts on Potomac gauge 01646500
    # True event onset: 2018-06-04T09:45:00Z to 2018-06-04T10:00:00Z
    # Alert at 2018-06-03T18:00:00Z is approx 15.75h to 16.0h ahead
    predictions = [
        {
            "sample_id": "01646500_20180603T180000Z",
            "score": 0.85,
            "label": 1,
        },
        {
            "sample_id": "01463500_20210901T060000Z",
            "score": 0.90,
            "label": 1,
        },
        {
            "sample_id": "01434000_20210902T120000Z",
            "score": 0.75,
            "label": 0,
        },
    ]

    res = evaluate_warning_lead_times(
        predictions,
        intervals_path,
        threshold=0.5,
        horizon_hours=24.0,
        cooldown_hours=12.0,
    )

    assert res.total_alerts == 3
    assert res.matched_alerts >= 1
    assert res.false_alerts >= 1
    assert res.mean_lead_time_hours is not None
    assert 10.0 <= res.mean_lead_time_hours <= 24.0

    # Check alert records structure
    for a in res.records:
        assert a.site_no in {"01646500", "01463500", "01434000"}
        if a.is_advance_warning:
            assert a.matched_event_id is not None
            assert a.lead_time_lower_hours is not None
            assert a.lead_time_upper_hours is not None
            assert a.lead_time_lower_hours <= a.lead_time_upper_hours


def test_evaluate_warning_lead_times_empty_predictions(root_dir: Path) -> None:
    intervals_path = root_dir / "data/event_intervals.csv"
    res = evaluate_warning_lead_times([], intervals_path)
    assert res.total_alerts == 0
    assert res.matched_alerts == 0
    assert res.false_alerts == 0
    assert res.mean_lead_time_hours is None


# ---------------------------------------------------------------------------
# Integration Runner Tests
# ---------------------------------------------------------------------------

def test_postprocessing_runner_integration(root_dir: Path) -> None:
    runs_dir = find_latest_runs_dir(root_dir)
    assert runs_dir.is_dir()

    cohort_map = load_cohort_split_map(root_dir)
    assert "01646500_20180603T180000Z" in cohort_map

    # Test analyze_run on one active run attempt
    run_folders = sorted(p for p in runs_dir.iterdir() if p.is_dir())
    assert len(run_folders) >= 1
    first_attempt = run_folders[0] / "attempt0001"
    res = analyze_run(
        first_attempt,
        cohort_map,
        root_dir / "data/event_intervals.csv",
        n_bins=5,
        threshold=0.5,
    )
    assert "validation" in res
    assert "test" in res
    assert "calibration" in res["test"]
    assert "brier_decomposition" in res["test"]
    assert "lead_time" in res["test"]


def test_postprocessing_summary_files_exist_and_valid(root_dir: Path) -> None:
    summary_path = root_dir / "project/postprocessing_summary.json"
    cal_path = root_dir / "project/calibration_report.json"
    lead_path = root_dir / "project/lead_time_report.json"
    csv_path = root_dir / "project/comparator_postprocessing_summary.csv"

    assert summary_path.is_file(), "Missing postprocessing_summary.json"
    assert cal_path.is_file(), "Missing calibration_report.json"
    assert lead_path.is_file(), "Missing lead_time_report.json"
    assert csv_path.is_file(), "Missing comparator_postprocessing_summary.csv"

    # Verify JSON content
    summary_data = json.loads(summary_path.read_text(encoding="utf-8"))
    assert summary_data["n_runs_evaluated"] == 36
    assert "causal_forecasting_head" in summary_data["family_summary"]
    assert "persistence" in summary_data["family_summary"]

    # Verify CSV content
    with csv_path.open(encoding="utf-8") as f:
        reader = csv.DictReader(f)
        rows = list(reader)
        assert len(rows) == 6
        families = {r["model_family"] for r in rows}
        assert "causal_forecasting_head" in families
        assert "ea_lstm" in families
