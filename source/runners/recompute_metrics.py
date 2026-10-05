#!/usr/bin/env python3
"""Runner for independent metric recomputation and deliberate mutation auditing.

Usage:
    PYTHONPATH=source python3 source/runners/recompute_metrics.py

CRITICAL INVARIANT:
This runner does NOT import factory.engine.metrics.
"""
from __future__ import annotations

import csv
from datetime import datetime, timezone
import json
from pathlib import Path
import sys

from flood_sentinel.adapters.ancestry import AncestryAdapter, SourceDuplicationError
from flood_sentinel.adapters.availability import AvailabilityAdapter, CausalLeakageError
from flood_sentinel.adapters.exposure import ExposureAdapter, LabelConsistencyError
from flood_sentinel.adapters.ranking import (
    DomainPrediction,
    RankingAdapter,
    UncalibratedProbabilityError,
)
from flood_sentinel.adapters.recompute import (
    recompute_binary_metrics,
    recompute_probabilistic_metrics,
    recompute_classification_metrics,
    verify_metric_parity,
    RecomputationDiscrepancyError,
)


def load_cohort(cohort_path: Path) -> list[dict[str, str]]:
    with open(cohort_path, mode="r", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def load_source_records(src_path: Path) -> dict[str, dict[str, str]]:
    with open(src_path, mode="r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        return {r["record_id"]: r for r in reader}


def run_independent_recomputation_suite() -> int:
    root = Path(__file__).resolve().parent.parent.parent
    cohort_path = root / "data/cohort.csv"
    src_path = root / "data/source_records.csv"
    event_path = root / "data/event_intervals.csv"

    print("==================================================================")
    print(" FLOOD SENTINEL P05: INDEPENDENT METRIC RECOMPUTATION & AUDIT")
    print("==================================================================")

    cohort_rows = load_cohort(cohort_path)
    src_records = load_source_records(src_path)
    print(f"Loaded {len(cohort_rows)} cohort rows and {len(src_records)} source records.")

    # 1. Test authentic development predictions on cohort
    # For demonstration / validation, construct baseline domain predictions
    labels = [int(r["label"]) for r in cohort_rows]
    # Synthetic realistic anomaly scores for test harness: higher for positive
    # Real baseline scores will come in P06/P07; here we verify arithmetic on real labels
    base_scores = [0.85 if y == 1 else 0.15 for y in labels]
    
    indep_metrics = recompute_binary_metrics(labels, base_scores, threshold=0.5)
    print("\n[+] Independently Recomputed Baseline Metrics:")
    for k, v in indep_metrics.items():
        print(f"    {k:20s}: {v:.6f}")

    assert indep_metrics["auroc"] == 1.0, f"Expected 1.0 AUROC on separable data, got {indep_metrics['auroc']}"
    assert indep_metrics["accuracy"] == 1.0, f"Expected 1.0 accuracy, got {indep_metrics['accuracy']}"

    # 2. Test Ancestry Adapter
    print("\n[+] Testing Record Ancestry Adapter on authentic cohort...")
    ancestry = AncestryAdapter.validate_cohort_ancestry(cohort_rows, src_records)
    print(f"    Successfully validated ancestry for {len(ancestry)} cohort samples with 0 missing records.")

    # 3. Test Deliberate Threat & Mutation Suite
    print("\n[+] Executing Deliberate Threat & Mutation Suite:")

    # Mutation 1: Label Inversion Mutation
    mut1_passed = False
    try:
        mutated_labels = list(labels)
        mutated_labels[0] = 1 - mutated_labels[0]
        mut_metrics = recompute_binary_metrics(mutated_labels, base_scores, threshold=0.5)
        verify_metric_parity(mut_metrics, indep_metrics, atol=1e-6)
    except RecomputationDiscrepancyError:
        mut1_passed = True
    assert mut1_passed, "MUT-01: Label inversion mutation was NOT detected!"
    print("    [PASS] MUT-01: Label inversion mutation detected by metric divergence.")

    # Mutation 2: Source Duplication Mutation
    mut2_passed = False
    try:
        # Deliberately duplicate a source ID
        sample_0 = cohort_rows[0]
        sids = sample_0["source_ids"].split("|")
        duplicated_sids = sids + [sids[0]]
        AncestryAdapter.resolve_sample_ancestry(sample_0["sample_id"], duplicated_sids, src_records)
    except SourceDuplicationError:
        mut2_passed = True
    assert mut2_passed, "MUT-02: Source duplication mutation was NOT detected!"
    print("    [PASS] MUT-02: Source duplication mutation detected by AncestryAdapter.")

    # Mutation 3: Causal Leakage Mutation (Future observation)
    mut3_passed = False
    try:
        t_issue = datetime(2021, 9, 1, 12, tzinfo=timezone.utc)
        future_record = {
            "record_id": "REC_FUTURE_TEST",
            "timestamp_utc": "2021-09-01T14:00:00+00:00",  # 2 hours in the future!
            "parameter": "gage_height_m",
            "value_si": "3.5",
        }
        AvailabilityAdapter.audit_sample_causality("test_future", t_issue, [future_record])
    except CausalLeakageError:
        mut3_passed = True
    assert mut3_passed, "MUT-03: Future causal leakage mutation was NOT detected!"
    print("    [PASS] MUT-03: Future causal leakage mutation detected by AvailabilityAdapter.")

    # Mutation 4: Uncalibrated Probability Mutation
    mut4_passed = False
    try:
        uncalibrated_pred = DomainPrediction(
            sample_id="test_uncal",
            ranking_score=15.4,
            calibrated_probability=None,  # No probability!
        )
        RankingAdapter.to_native_predictions([uncalibrated_pred], use_probability=True)
    except UncalibratedProbabilityError:
        mut4_passed = True
    assert mut4_passed, "MUT-04: Uncalibrated probability mutation was NOT detected!"
    print("    [PASS] MUT-04: Uncalibrated score passed to probability rule detected by RankingAdapter.")

    # Mutation 5: Cutoff Divergence Mutation
    mut5_passed = False
    try:
        clf_05 = recompute_classification_metrics(labels, base_scores, threshold=0.5)
        # Shift threshold to 0.95 without re-evaluating
        clf_095 = recompute_classification_metrics(labels, base_scores, threshold=0.95)
        verify_metric_parity(clf_05, clf_095, atol=1e-6)
    except RecomputationDiscrepancyError:
        mut5_passed = True
    assert mut5_passed, "MUT-05: Cutoff shift divergence was NOT detected!"
    print("    [PASS] MUT-05: Cutoff mutation detected by classification recomputation.")

    # Mutation 6: Negative probability score
    mut6_passed = False
    try:
        recompute_probabilistic_metrics([1, 0], [-0.2, 0.5])
    except ValueError:
        mut6_passed = True
    assert mut6_passed, "MUT-06: Negative probability was NOT detected!"
    print("    [PASS] MUT-06: Out-of-bounds probability detected by recompute_probabilistic_metrics.")

    print("\n==================================================================")
    print(" ALL 6 DELIBERATE THREAT & MUTATION TESTS PASSED (100% BLOCKED)")
    print(" INDEPENDENT RECOMPUTATION VALIDATION SUITE COMPLETE.")
    print("==================================================================")
    return 0


if __name__ == "__main__":
    sys.exit(run_independent_recomputation_suite())
