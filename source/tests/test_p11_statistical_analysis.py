"""Unit and integration tests for statistical analysis, multiplicity adjustment, and failure review."""
from __future__ import annotations

import csv
import json
import math
from pathlib import Path
import pytest
import numpy as np

from flood_sentinel.statistical_analysis import (
    exact_paired_sign_flip_pvalue,
    compute_paired_contrast,
    apply_holm_stepdown,
    categorize_sample_failure,
    evaluate_model_failures,
    PairedContrastResult,
    SampleFailureRecord,
    ModelFailureSummary,
)
from source.runners.run_statistical_evaluation import (
    find_active_runs_dir,
    run_statistical_evaluation,
)


@pytest.fixture
def root_dir() -> Path:
    return Path(__file__).resolve().parents[2]


# ---------------------------------------------------------------------------
# Exact Permutation Test
# ---------------------------------------------------------------------------

def test_exact_paired_sign_flip_pvalue_symmetric() -> None:
    # All 5 differences strictly positive
    diffs = [0.1, 0.2, 0.15, 0.3, 0.25]
    p_val, is_exact = exact_paired_sign_flip_pvalue(diffs)
    assert is_exact is True
    # For n=5, 2^5 = 32. Only 2 extreme states (all + and all -), so p = 2/32 = 0.0625
    assert math.isclose(p_val, 0.0625, abs_tol=1e-6)


def test_exact_paired_sign_flip_pvalue_zero() -> None:
    diffs = [0.0, 0.0, 0.0, 0.0]
    p_val, is_exact = exact_paired_sign_flip_pvalue(diffs)
    assert is_exact is True
    assert p_val == 1.0


def test_exact_paired_sign_flip_pvalue_large_n() -> None:
    # Large n triggers Monte Carlo path
    diffs = [0.5] * 20
    p_val, is_exact = exact_paired_sign_flip_pvalue(diffs)
    assert is_exact is False
    assert 0.0 <= p_val <= 0.01


# ---------------------------------------------------------------------------
# Paired Contrast Computation
# ---------------------------------------------------------------------------

def test_compute_paired_contrast_metrics() -> None:
    scores_a = [0.9, 0.85, 0.95, 0.8, 0.9]
    scores_b = [0.5, 0.55, 0.5, 0.6, 0.55]
    contrast = compute_paired_contrast(
        comparison_id="test_cmp",
        model_a="model_a",
        model_b="model_b",
        scores_a=scores_a,
        scores_b=scores_b,
        metric_name="average_precision",
        alpha=0.05,
    )

    assert contrast.comparison_id == "test_cmp"
    assert contrast.n_seeds == 5
    assert contrast.mean_difference > 0.3
    assert contrast.standard_error > 0.0
    assert contrast.cohens_dz is not None and contrast.cohens_dz > 0.0
    assert contrast.ci_lower < contrast.mean_difference < contrast.ci_upper
    assert contrast.p_raw == 0.0625


def test_compute_paired_contrast_validation() -> None:
    with pytest.raises(ValueError, match="equal length"):
        compute_paired_contrast("c1", "a", "b", [0.5, 0.6], [0.5])

    with pytest.raises(ValueError, match="at least 2"):
        compute_paired_contrast("c2", "a", "b", [0.5], [0.5])


# ---------------------------------------------------------------------------
# Holm-Bonferroni Step-Down Multiplicity Adjustment
# ---------------------------------------------------------------------------

def test_apply_holm_stepdown() -> None:
    c1 = PairedContrastResult(
        comparison_id="c1",
        model_a="a",
        model_b="b",
        metric_name="ap",
        n_seeds=5,
        mean_difference=0.4,
        std_difference=0.05,
        standard_error=0.02,
        cohens_dz=8.0,
        ci_lower=0.34,
        ci_upper=0.46,
        ci_level=0.95,
        p_raw=0.01,
        p_holm=0.01,
        sign_flip_exact=True,
        decision="superiority",
        inference_scope="fixed_test_corpus",
    )
    c2 = PairedContrastResult(
        comparison_id="c2",
        model_a="a",
        model_b="c",
        metric_name="ap",
        n_seeds=5,
        mean_difference=0.2,
        std_difference=0.05,
        standard_error=0.02,
        cohens_dz=4.0,
        ci_lower=0.14,
        ci_upper=0.26,
        ci_level=0.95,
        p_raw=0.04,
        p_holm=0.04,
        sign_flip_exact=True,
        decision="superiority",
        inference_scope="fixed_test_corpus",
    )
    c3 = PairedContrastResult(
        comparison_id="c3",
        model_a="a",
        model_b="d",
        metric_name="ap",
        n_seeds=5,
        mean_difference=0.05,
        std_difference=0.05,
        standard_error=0.02,
        cohens_dz=1.0,
        ci_lower=-0.01,
        ci_upper=0.11,
        ci_level=0.95,
        p_raw=0.20,
        p_holm=0.20,
        sign_flip_exact=True,
        decision="inconclusive",
        inference_scope="fixed_test_corpus",
    )

    adjusted = apply_holm_stepdown([c1, c2, c3], alpha=0.05)
    assert len(adjusted) == 3

    # Rank 0 (p_raw=0.01): adjusted = 0.01 * 3 = 0.03 <= 0.05 -> superiority
    assert math.isclose(adjusted[0].p_holm, 0.03, abs_tol=1e-5)
    assert adjusted[0].decision == "superiority"

    # Rank 1 (p_raw=0.04): adjusted = max(0.03, 0.04 * 2) = 0.08 > 0.05 -> inconclusive
    assert math.isclose(adjusted[1].p_holm, 0.08, abs_tol=1e-5)
    assert adjusted[1].decision == "inconclusive"

    # Rank 2 (p_raw=0.20): adjusted = max(0.08, 0.20 * 1) = 0.20 -> inconclusive
    assert math.isclose(adjusted[2].p_holm, 0.20, abs_tol=1e-5)
    assert adjusted[2].decision == "inconclusive"


def test_apply_holm_stepdown_empty() -> None:
    assert apply_holm_stepdown([]) == []


# ---------------------------------------------------------------------------
# Failure Categorization & Taxonomy
# ---------------------------------------------------------------------------

def test_categorize_sample_failure() -> None:
    # True Positive
    err, cat, _ = categorize_sample_failure("01646500_20210901T120000Z", "group_1", 1, 0.85, 0.5)
    assert err == "TP"
    assert cat == "none"

    # True Negative
    err, cat, _ = categorize_sample_failure("01646500_20210829T000000Z", "group_1", 0, 0.15, 0.5)
    assert err == "TN"
    assert cat == "none"

    # Near threshold pulse false positive
    err, cat, _ = categorize_sample_failure("01434000_20210902T120000Z", "group_3", 0, 0.75, 0.5)
    assert err == "FP"
    assert cat == "near_threshold_pulse"

    # Datum elevation shift false positive
    err, cat, _ = categorize_sample_failure("01463500_20210830T120000Z", "group_2", 0, 0.65, 0.5)
    assert err == "FP"
    assert cat == "datum_elevation_shift"

    # Nascent limb miss false negative
    err, cat, _ = categorize_sample_failure("01463500_20210901T060000Z", "group_2", 1, 0.35, 0.5)
    assert err == "FN"
    assert cat == "nascent_limb_miss"


def test_evaluate_model_failures() -> None:
    sids = ["01646500_20210901T120000Z", "01434000_20210902T120000Z", "01463500_20210830T120000Z"]
    gids = ["g1", "g3", "g2"]
    splits = ["test", "test", "test"]
    labels = [1, 0, 0]
    probs = [0.85, 0.70, 0.10]

    summary = evaluate_model_failures("test_fam", sids, gids, splits, labels, probs, 0.5)

    assert summary.n_eval_samples == 3
    assert summary.true_positives == 1
    assert summary.false_positives == 1
    assert summary.true_negatives == 1
    assert summary.false_negatives == 0
    assert math.isclose(summary.accuracy, 2.0 / 3.0, abs_tol=1e-5)
    assert summary.failure_mode_counts["near_threshold_pulse"] == 1


# ---------------------------------------------------------------------------
# Runner End-to-End Execution
# ---------------------------------------------------------------------------

def test_run_statistical_evaluation_e2e(root_dir: Path) -> None:
    summary = run_statistical_evaluation(root_dir)

    assert summary["n_evaluated_runs"] == 36
    assert summary["n_test_samples"] == 5
    assert len(summary["paired_contrasts"]) == 4

    stat_file = root_dir / "project/statistical_summary.json"
    tax_file = root_dir / "project/failure_taxonomy.json"
    samp_file = root_dir / "project/sample_level_predictions.csv"
    fig_file = root_dir / "project/figures_data.json"

    assert stat_file.is_file()
    assert tax_file.is_file()
    assert samp_file.is_file()
    assert fig_file.is_file()

    with stat_file.open(encoding="utf-8") as f:
        stat_data = json.load(f)
    assert "causal_forecasting_head" in stat_data["family_aggregates"]

    with tax_file.open(encoding="utf-8") as f:
        tax_data = json.load(f)
    assert "causal_forecasting_head" in tax_data["models"]

    with samp_file.open(encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    assert len(rows) > 0
    assert "predicted_probability" in rows[0]
