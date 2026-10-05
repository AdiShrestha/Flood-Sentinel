"""Unit and integration tests for hardware benchmarking and reproducibility auditing."""
from __future__ import annotations

import csv
import json
from pathlib import Path
import pytest
import torch

from flood_sentinel.hardware import (
    benchmark_inference,
    count_parameters,
    get_current_rss_mb,
    get_host_hardware_info,
)
from flood_sentinel.reproducibility import (
    compare_prediction_series,
)
from source.runners.run_hardware_benchmark import (
    benchmark_all_model_families,
    execute_reproducibility_audit,
)
from source.runners.run_postprocessing import find_latest_runs_dir


@pytest.fixture
def root_dir() -> Path:
    return Path(__file__).resolve().parents[2]


# ---------------------------------------------------------------------------
# Hardware Profiling Tests
# ---------------------------------------------------------------------------

def test_host_hardware_info_structure() -> None:
    info = get_host_hardware_info()
    assert "platform" in info
    assert "architecture" in info
    assert "cpu_model" in info
    assert "python_version" in info
    assert "torch_version" in info
    assert info["device"] == "cpu"
    assert info["torch_threads"] >= 1


def test_get_current_rss_mb_positive() -> None:
    rss = get_current_rss_mb()
    assert isinstance(rss, float)
    assert rss > 0.0


def test_count_parameters_calculation() -> None:
    linear = torch.nn.Linear(10, 5, bias=True)
    # 10*5 + 5 = 55 parameters
    assert count_parameters(linear) == 55

    conv = torch.nn.Conv1d(2, 4, kernel_size=3, bias=False)
    # 2 * 4 * 3 = 24 parameters
    assert count_parameters(conv) == 24

    # Tuple of modules
    assert count_parameters((linear, conv)) == 79


def test_benchmark_inference_timing() -> None:
    call_count = 0

    def dummy_forward() -> float:
        nonlocal call_count
        call_count += 1
        x = torch.randn(10, 10)
        return float(torch.sum(x @ x.T).item())

    res = benchmark_inference(
        dummy_forward,
        n_samples=10,
        warmup_trials=5,
        measured_trials=10,
    )

    assert call_count == 15
    assert res["mean_latency_ms"] > 0.0
    assert res["p50_latency_ms"] > 0.0
    assert res["throughput_samples_per_sec"] > 0.0
    assert res["peak_rss_mb"] > 0.0


# ---------------------------------------------------------------------------
# Reproducibility & Tolerance Tests
# ---------------------------------------------------------------------------

def test_compare_prediction_series_bitwise_identity() -> None:
    records_a = [
        {"sample_id": "s1", "score": 0.85},
        {"sample_id": "s2", "score": 0.12},
    ]
    records_b = [
        {"sample_id": "s1", "score": 0.85},
        {"sample_id": "s2", "score": 0.12},
    ]

    res = compare_prediction_series(records_a, records_b, tolerance=1e-6)
    assert res["within_tolerance"] is True
    assert res["bitwise_identical"] is True
    assert res["max_absolute_error"] == 0.0


def test_compare_prediction_series_tolerance_boundary() -> None:
    records_a = [{"sample_id": "s1", "score": 0.5000001}]
    records_b = [{"sample_id": "s1", "score": 0.5000002}]

    # 1e-7 difference is within 1e-6
    res = compare_prediction_series(records_a, records_b, tolerance=1e-6)
    assert res["within_tolerance"] is True
    assert res["bitwise_identical"] is False
    assert res["max_absolute_error"] < 1e-6

    # Outside stricter tolerance
    res_strict = compare_prediction_series(records_a, records_b, tolerance=1e-8)
    assert res_strict["within_tolerance"] is False


def test_compare_prediction_series_empty_error() -> None:
    records_a = [{"sample_id": "s1", "score": 0.5}]
    records_b = [{"sample_id": "s2", "score": 0.5}]

    with pytest.raises(ValueError, match="No common sample_ids"):
        compare_prediction_series(records_a, records_b)


# ---------------------------------------------------------------------------
# Traceability Audit Tests
# ---------------------------------------------------------------------------

def test_traceability_figures_and_statistical_summary(root_dir: Path) -> None:
    fig_path = root_dir / "project/figures_data.json"
    stat_path = root_dir / "project/statistical_summary.json"

    assert fig_path.is_file(), "Missing figures_data.json"
    assert stat_path.is_file(), "Missing statistical_summary.json"

    fig_data = json.loads(fig_path.read_text(encoding="utf-8"))
    stat_data = json.loads(stat_path.read_text(encoding="utf-8"))

    fam_stats = stat_data["family_aggregates"]
    cal_curves = fig_data["calibration_curves"]

    for fam, cdata in cal_curves.items():
        assert fam in fam_stats, f"Model family '{fam}' missing in statistical summary"
        stat_ece = fam_stats[fam]["expected_calibration_error"]["mean"]
        fig_ece = cdata["ece"]
        assert abs(stat_ece - fig_ece) < 1e-9, f"ECE mismatch for {fam}: {fig_ece} vs {stat_ece}"


# ---------------------------------------------------------------------------
# Output Artifact Validation Tests
# ---------------------------------------------------------------------------

def test_hardware_metrics_artifacts_exist_and_valid(root_dir: Path) -> None:
    json_path = root_dir / "project/hardware_metrics.json"
    csv_path = root_dir / "project/hardware_summary.csv"
    repro_path = root_dir / "project/reproducibility_audit.json"

    assert json_path.is_file(), "Missing hardware_metrics.json"
    assert csv_path.is_file(), "Missing hardware_summary.csv"
    assert repro_path.is_file(), "Missing reproducibility_audit.json"

    # Validate JSON
    hw_data = json.loads(json_path.read_text(encoding="utf-8"))
    assert "host_hardware" in hw_data
    assert "models" in hw_data
    assert "causal_forecasting_head" in hw_data["models"]
    assert "persistence" in hw_data["models"]

    # Validate CSV
    with csv_path.open(encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
        assert len(rows) == 7
        for r in rows:
            assert float(r["sustained_throughput_samples_per_sec"]) > 0.0
            assert float(r["single_sample_latency_mean_ms"]) > 0.0
            assert float(r["peak_rss_mb"]) > 0.0

    # Validate Reproducibility Audit
    audit_data = json.loads(repro_path.read_text(encoding="utf-8"))
    assert audit_data["overall_status"] == "PASS"
    assert audit_data["all_within_tolerance"] is True
    assert audit_data["n_runs_audited"] == 36
    assert audit_data["traceability_audit"]["status"] == "PASS"
