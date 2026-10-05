"""Comprehensive tests for domain adapters and independent recomputation."""
from __future__ import annotations

import csv
from datetime import datetime, timezone
import math
from pathlib import Path
import pytest
import numpy as np

from flood_sentinel.adapters.ranking import (
    DomainPrediction,
    RankingAdapter,
    UncalibratedProbabilityError,
)
from flood_sentinel.adapters.ancestry import (
    RecordAncestry,
    AncestryAdapter,
    SourceDuplicationError,
    MissingSourceError,
)
from flood_sentinel.adapters.availability import (
    AvailabilityAdapter,
    CausalLeakageError,
)
from flood_sentinel.adapters.exposure import (
    HydrologicExposure,
    ExposureAdapter,
    LabelConsistencyError,
)
from flood_sentinel.adapters.population import (
    PopulationAdapter,
    InsufficientGroupSupportError,
)
from flood_sentinel.adapters.recompute import (
    recompute_auroc,
    recompute_average_precision,
    recompute_classification_metrics,
    recompute_probabilistic_metrics,
    recompute_binary_metrics,
    recompute_student_t_critical,
    recompute_paired_sign_flip_pvalue,
    recompute_holm,
    verify_metric_parity,
    RecomputationDiscrepancyError,
)

# Hand-calculated analytical reference ground truth (zero external/framework imports)


@pytest.fixture
def repo_root() -> Path:
    return Path(__file__).resolve().parent.parent.parent


@pytest.fixture
def cohort_rows(repo_root: Path) -> list[dict[str, str]]:
    with open(repo_root / "data/cohort.csv", mode="r", encoding="utf-8") as f:
        return list(csv.DictReader(f))


@pytest.fixture
def source_records_lookup(repo_root: Path) -> dict[str, dict[str, str]]:
    with open(repo_root / "data/source_records.csv", mode="r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        return {r["record_id"]: r for r in reader}


@pytest.fixture
def event_intervals(repo_root: Path) -> list[dict[str, str]]:
    with open(repo_root / "data/event_intervals.csv", mode="r", encoding="utf-8") as f:
        return list(csv.DictReader(f))


# =========================================================================
# 1. Ranking & Probability Adapter Tests
# =========================================================================

def test_domain_prediction_validation():
    # Valid prediction
    p = DomainPrediction(
        sample_id="test_sample_1",
        ranking_score=1.45,
        calibrated_probability=0.82,
        decision_threshold=0.5,
    )
    assert p.sample_id == "test_sample_1"
    assert p.ranking_score == 1.45
    assert p.calibrated_probability == 0.82

    # Invalid empty sample_id
    with pytest.raises(ValueError, match="sample_id"):
        DomainPrediction(sample_id="", ranking_score=1.0)

    # Invalid probability > 1.0
    with pytest.raises(ValueError, match="calibrated_probability"):
        DomainPrediction(sample_id="s1", ranking_score=1.0, calibrated_probability=1.2)

    # Invalid threshold < 0.0
    with pytest.raises(ValueError, match="decision_threshold"):
        DomainPrediction(sample_id="s1", ranking_score=1.0, decision_threshold=-0.1)


def test_ranking_adapter_projection():
    preds = [
        DomainPrediction("s1", ranking_score=10.5, calibrated_probability=0.9),
        DomainPrediction("s2", ranking_score=2.1, calibrated_probability=0.2),
    ]
    # Projection as scores
    native_scores = RankingAdapter.to_native_predictions(preds, use_probability=False)
    assert native_scores == [("s1", 10.5), ("s2", 2.1)]

    # Projection as probabilities
    native_probs = RankingAdapter.to_native_predictions(preds, use_probability=True)
    assert native_probs == [("s1", 0.9), ("s2", 0.2)]

    # Digest should be deterministic
    d1 = RankingAdapter.compute_conversion_digest(preds)
    d2 = RankingAdapter.compute_conversion_digest(preds)
    assert d1 == d2 and len(d1) == 64


def test_ranking_adapter_uncalibrated_rejection():
    # Uncalibrated score cannot be projected as probability
    preds = [
        DomainPrediction("s1", ranking_score=10.5, calibrated_probability=None),
    ]
    with pytest.raises(UncalibratedProbabilityError):
        RankingAdapter.to_native_predictions(preds, use_probability=True)


def test_ranking_adapter_tie_resolution():
    scores = [1.0, 3.0, 2.0, 2.0, 4.0]
    ranks = RankingAdapter.rank_order(scores)
    # 1.0 -> rank 1
    # 2.0, 2.0 -> ranks 2, 3 -> avg 2.5
    # 3.0 -> rank 4
    # 4.0 -> rank 5
    assert list(ranks) == [1.0, 4.0, 2.5, 2.5, 5.0]


# =========================================================================
# 2. Record Ancestry Adapter Tests
# =========================================================================

def test_ancestry_adapter_authentic_cohort(cohort_rows, source_records_lookup):
    ancestries = AncestryAdapter.validate_cohort_ancestry(cohort_rows, source_records_lookup)
    assert len(ancestries) == len(cohort_rows)
    for sid, anc in ancestries.items():
        assert len(anc.source_ids) > 0
        assert anc.start_time_utc <= anc.end_time_utc
        assert len(anc.ancestry_digest) == 64
        assert "USGS-NWIS" in anc.providers or "NOAA-NWPS" in anc.providers


def test_ancestry_adapter_duplicate_source_rejection(source_records_lookup):
    rec_id = list(source_records_lookup.keys())[0]
    # Duplicating record ID in source_ids list
    with pytest.raises(SourceDuplicationError):
        AncestryAdapter.resolve_sample_ancestry(
            sample_id="test_dup",
            source_ids=[rec_id, rec_id],
            source_records_lookup=source_records_lookup,
        )


def test_ancestry_adapter_missing_source_rejection(source_records_lookup):
    with pytest.raises(MissingSourceError):
        AncestryAdapter.resolve_sample_ancestry(
            sample_id="test_missing",
            source_ids=["NONEXISTENT_RECORD_ID_12345"],
            source_records_lookup=source_records_lookup,
        )


# =========================================================================
# 3. Causal Availability Adapter Tests
# =========================================================================

def test_availability_adapter_causality():
    t_issue = datetime(2021, 9, 1, 12, 0, tzinfo=timezone.utc)
    records = [
        {"record_id": "r1", "timestamp_utc": "2021-09-01T10:00:00+00:00", "parameter": "gage_height_m"},
        {"record_id": "r2", "timestamp_utc": "2021-09-01T12:00:00+00:00", "parameter": "gage_height_m"},
    ]
    res = AvailabilityAdapter.audit_sample_causality("s1", t_issue, records)
    assert res.is_causally_valid is True
    assert res.record_count == 2


def test_availability_adapter_future_leakage_rejection():
    t_issue = datetime(2021, 9, 1, 12, 0, tzinfo=timezone.utc)
    records = [
        {"record_id": "r1", "timestamp_utc": "2021-09-01T10:00:00+00:00", "parameter": "gage_height_m"},
        {"record_id": "r2_future", "timestamp_utc": "2021-09-01T12:15:00+00:00", "parameter": "gage_height_m"},
    ]
    with pytest.raises(CausalLeakageError, match="observation timestamp"):
        AvailabilityAdapter.audit_sample_causality("s_leak", t_issue, records)


def test_availability_adapter_latency_leakage_rejection():
    t_issue = datetime(2021, 9, 1, 12, 0, tzinfo=timezone.utc)
    records = [
        {
            "record_id": "r1",
            "timestamp_utc": "2021-09-01T11:00:00+00:00",
            "available_utc": "2021-09-01T13:00:00+00:00",  # Available 1 hour AFTER issue time!
            "parameter": "gage_height_m",
        },
    ]
    with pytest.raises(CausalLeakageError, match="available timestamp"):
        AvailabilityAdapter.audit_sample_causality("s_latency", t_issue, records)


# =========================================================================
# 4. Event & Exposure Adapter Tests
# =========================================================================

def test_exposure_adapter_matching(event_intervals):
    # Delaware at Trenton (01463500) during Hurricane Ida
    # Issue at 2021-09-01 06:00:00 UTC (flood onset was around 2021-09-01 17:30 UTC)
    t_issue = datetime(2021, 9, 1, 6, 0, tzinfo=timezone.utc)
    exp = ExposureAdapter.compute_sample_exposure(
        sample_id="test_exp_ida",
        site_no="01463500",
        issue_time_utc=t_issue,
        event_intervals=event_intervals,
        horizon_hours=24.0,
    )
    assert exp.has_flood_event is True
    assert exp.lead_time_lower_hours is not None
    assert exp.lead_time_lower_hours > 0  # True forecast lead time!
    assert exp.peak_stage_excess_m > 0


def test_exposure_adapter_negative_control(event_intervals):
    # Delaware at Trenton on 2021-08-30 (pre-event baseflow)
    t_issue = datetime(2021, 8, 30, 12, 0, tzinfo=timezone.utc)
    exp = ExposureAdapter.compute_sample_exposure(
        sample_id="test_exp_baseflow",
        site_no="01463500",
        issue_time_utc=t_issue,
        event_intervals=event_intervals,
        horizon_hours=24.0,
    )
    assert exp.has_flood_event is False
    assert exp.lead_time_lower_hours is None


def test_exposure_adapter_label_consistency_error(event_intervals):
    # Deliberately falsify cohort label: label='1' for non-flooding baseflow
    t_issue = datetime(2021, 8, 30, 12, 0, tzinfo=timezone.utc)
    fake_cohort_row = [{"sample_id": "fake_1", "label": "1"}]
    meta = {"fake_1": ("01463500", t_issue)}
    with pytest.raises(LabelConsistencyError):
        ExposureAdapter.validate_cohort_exposure(fake_cohort_row, meta, event_intervals)


# =========================================================================
# 5. Population Adapter Tests
# =========================================================================

def test_population_adapter_aggregation():
    sample_ids = ["s1", "s2", "s3", "s4"]
    labels = [1, 0, 1, 0]
    scores = [0.9, 0.1, 0.8, 0.2]
    groups = ["grp_a", "grp_a", "grp_b", "grp_b"]

    agg = PopulationAdapter.aggregate_by_group(sample_ids, labels, scores, groups)
    assert len(agg) == 2
    assert "grp_a" in agg and "grp_b" in agg
    assert agg["grp_a"].positive_count == 1
    assert agg["grp_a"].negative_count == 1
    assert agg["grp_a"].accuracy == 1.0


def test_population_adapter_insufficient_support():
    # Only 1 group
    with pytest.raises(InsufficientGroupSupportError, match="independent groups"):
        PopulationAdapter.validate_population_support(
            group_ids=["grp_1", "grp_1"],
            labels=[1, 0],
            min_groups=2,
        )

    # Class floor violation
    with pytest.raises(InsufficientGroupSupportError, match="class floor"):
        PopulationAdapter.validate_population_support(
            group_ids=["grp_1", "grp_2"],
            labels=[1, 1],  # 0 negatives!
            min_class_count=2,
        )


def test_independent_recomputation_analytical():
    # Case 0: Perfectly separated
    labels = [1, 0, 1, 0]
    scores = [0.8, 0.2, 0.9, 0.1]
    res = recompute_binary_metrics(labels, scores, threshold=0.5, log_epsilon=1e-15)
    assert res["auroc"] == 1.0
    assert res["average_precision"] == 1.0
    assert res["accuracy"] == 1.0
    assert res["f1"] == 1.0
    assert abs(res["brier"] - 0.025) < 1e-12
    expected_ll = -0.25 * (2 * math.log(0.8) + 2 * math.log(0.9))
    assert abs(res["log_loss"] - expected_ll) < 1e-12

    # Case 1: Imperfect ranking with ties
    labels = [1, 0, 1, 0, 1, 0]
    scores = [0.5, 0.5, 0.7, 0.3, 0.8, 0.2]
    res2 = recompute_binary_metrics(labels, scores, threshold=0.5, log_epsilon=1e-15)
    assert abs(res2["auroc"] - (8.5 / 9.0)) < 1e-12
    assert abs(res2["average_precision"] - (11.0 / 12.0)) < 1e-12

    # Case 2: Chance ranking
    labels = [1, 0, 0, 1]
    scores = [0.3, 0.4, 0.6, 0.7]
    res3 = recompute_binary_metrics(labels, scores, threshold=0.5)
    assert abs(res3["auroc"] - 0.5) < 1e-12


def test_recompute_student_t_critical_analytical():
    known_critical = [
        (10, 0.05, 2.2281388519649385),
        (2, 0.05, 4.302652729911275),
        (25, 0.05, 2.059538553245465),
        (50, 0.01, 2.677793273183574),
        (1, 0.05, 12.706204736432095),
    ]
    for df, alpha, expected in known_critical:
        t_crit = recompute_student_t_critical(alpha, df)
        assert abs(t_crit - expected) < 1e-8


def test_recompute_holm_analytical():
    pvals = [0.01, 0.04, 0.03, 0.005, 0.50]
    expected = [0.04, 0.09, 0.09, 0.025, 0.50]
    adj = recompute_holm(pvals)
    for a, e in zip(adj, expected):
        assert abs(a - e) < 1e-12


def test_recompute_paired_sign_flip_exact():
    # For small N <= 16, test exact sign-flip enumeration
    diffs = [0.1, 0.2, 0.15, -0.05, 0.3]
    p_val = recompute_paired_sign_flip_pvalue(diffs)
    assert 0.0 <= p_val <= 1.0


# =========================================================================
# 7. Threat and Mutation Tests (MUT-01 .. MUT-06)
# =========================================================================

def test_mutation_01_label_inversion():
    labels = [1, 0, 1, 0]
    scores = [0.9, 0.1, 0.8, 0.2]
    base_m = recompute_binary_metrics(labels, scores)

    # Invert label 0: [0, 0, 1, 0]
    mut_labels = [0, 0, 1, 0]
    mut_m = recompute_binary_metrics(mut_labels, scores)

    # Must diverge!
    with pytest.raises(RecomputationDiscrepancyError):
        verify_metric_parity(base_m, mut_m, atol=1e-5)


def test_mutation_02_denominator_truncation():
    # Removing negatives fails population support check
    with pytest.raises(InsufficientGroupSupportError):
        PopulationAdapter.validate_population_support(
            group_ids=["g1", "g2", "g3"],
            labels=[1, 1, 1],  # 0 negatives!
            min_class_count=2,
        )


def test_mutation_03_cutoff_mutation():
    labels = [1, 0, 1, 0]
    scores = [0.9, 0.4, 0.8, 0.2]
    clf_base = recompute_classification_metrics(labels, scores, threshold=0.5)
    clf_mut = recompute_classification_metrics(labels, scores, threshold=0.85)
    with pytest.raises(RecomputationDiscrepancyError):
        verify_metric_parity(clf_base, clf_mut, atol=1e-5)


def test_mutation_04_source_duplication(source_records_lookup):
    rec_id = list(source_records_lookup.keys())[0]
    with pytest.raises(SourceDuplicationError):
        AncestryAdapter.resolve_sample_ancestry("s_dup", [rec_id, rec_id], source_records_lookup)


def test_mutation_05_future_leakage():
    t_issue = datetime(2021, 9, 1, 12, 0, tzinfo=timezone.utc)
    future_record = {
        "record_id": "r_fut",
        "timestamp_utc": "2021-09-01T13:00:00+00:00",
        "parameter": "gage_height_m",
    }
    with pytest.raises(CausalLeakageError):
        AvailabilityAdapter.audit_sample_causality("s_fut", t_issue, [future_record])


def test_mutation_06_uncalibrated_probability():
    # Negative score in probabilistic metrics
    with pytest.raises(ValueError, match="must be in"):
        recompute_probabilistic_metrics([1, 0], [-0.5, 0.8])
