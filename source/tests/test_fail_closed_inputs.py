"""Fail-closed behavior of legacy helpers: thresholds, isotonic calibration, replay comparison."""
from __future__ import annotations

import math

import pytest

from flood_sentinel.calibration import IsotonicCalibrator
from flood_sentinel.events.thresholds import FloodThreshold, ThresholdRegistry
from flood_sentinel.reproducibility import compare_prediction_series


def _threshold(value_si: float) -> FloodThreshold:
    return FloodThreshold(
        site_no="00000000",
        parameter="stage",
        category="minor",
        value_si=value_si,
        value_raw=value_si,
        unit_si="m",
        unit_raw="m",
    )


def test_threshold_registry_rejects_conflicting_duplicate() -> None:
    registry = ThresholdRegistry([_threshold(2.0)])
    with pytest.raises(ValueError, match="Conflicting threshold"):
        registry.register(_threshold(2.5))
    assert registry.get("00000000", "minor").value_si == 2.0


def test_threshold_registry_accepts_identical_reregistration() -> None:
    registry = ThresholdRegistry([_threshold(2.0)])
    registry.register(_threshold(2.0))
    assert registry.get("00000000", "minor").value_si == 2.0


@pytest.mark.parametrize("labels", [[0, 1, 2], [0, 1, 0.5], [0, 1, float("nan")]])
def test_isotonic_fit_rejects_non_binary_labels(labels) -> None:
    with pytest.raises(ValueError, match="binary"):
        IsotonicCalibrator().fit([0.1, 0.2, 0.3], labels)


@pytest.mark.parametrize("bad", [float("nan"), float("inf"), -float("inf")])
def test_isotonic_fit_rejects_nonfinite_scores(bad) -> None:
    with pytest.raises(ValueError, match="finite"):
        IsotonicCalibrator().fit([0.1, bad, 0.3], [0, 1, 1])


def test_isotonic_predict_rejects_nonfinite_scores_and_bad_eps() -> None:
    cal = IsotonicCalibrator().fit([0.1, 0.2, 0.3, 0.4], [0, 0, 1, 1])
    with pytest.raises(ValueError, match="finite"):
        cal.predict_proba([0.2, float("nan")])
    for eps in (-1e-6, 0.5, float("nan")):
        with pytest.raises(ValueError, match="eps"):
            cal.predict_proba([0.2], eps=eps)
    probs = cal.predict_proba([0.0, 0.25, 1.0])
    assert all(0.0 < p < 1.0 for p in probs)


def test_replay_comparison_fails_on_missing_rows() -> None:
    recorded = [{"sample_id": "a", "score": 0.1}, {"sample_id": "b", "score": 0.2}]
    replayed = [{"sample_id": "a", "score": 0.1}]
    res = compare_prediction_series(recorded, replayed)
    assert res["missing_sample_ids"] == ["b"]
    assert res["complete_id_match"] is False
    assert res["within_tolerance"] is False
    assert res["bitwise_identical"] is False


def test_replay_comparison_fails_on_extra_rows() -> None:
    recorded = [{"sample_id": "a", "score": 0.1}]
    replayed = [{"sample_id": "a", "score": 0.1}, {"sample_id": "z", "score": 0.9}]
    res = compare_prediction_series(recorded, replayed)
    assert res["extra_sample_ids"] == ["z"]
    assert res["within_tolerance"] is False


def test_replay_comparison_fails_on_duplicate_ids() -> None:
    recorded = [{"sample_id": "a", "score": 0.1}, {"sample_id": "a", "score": 0.1}]
    replayed = [{"sample_id": "a", "score": 0.1}]
    res = compare_prediction_series(recorded, replayed)
    assert res["duplicate_recorded_ids"] == ["a"]
    assert res["within_tolerance"] is False


def test_replay_comparison_fails_on_nonfinite_scores() -> None:
    recorded = [{"sample_id": "a", "score": 0.1}, {"sample_id": "b", "score": 0.2}]
    replayed = [{"sample_id": "a", "score": 0.1}, {"sample_id": "b", "score": float("nan")}]
    res = compare_prediction_series(recorded, replayed)
    assert res["nonfinite_sample_ids"] == ["b"]
    assert res["within_tolerance"] is False
    assert math.isclose(res["max_absolute_error"], 0.0)


def test_replay_comparison_passes_on_complete_identical_sets() -> None:
    recorded = [{"sample_id": "a", "score": 0.1}, {"sample_id": "b", "score": 0.2}]
    res = compare_prediction_series(recorded, list(reversed(recorded)))
    assert res["complete_id_match"] is True
    assert res["within_tolerance"] is True
    assert res["bitwise_identical"] is True
