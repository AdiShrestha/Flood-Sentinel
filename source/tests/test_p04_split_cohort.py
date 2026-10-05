"""Unit and regression tests for split, availability, and cohort design.

Verifies zero group leakage across splits, zero source record leakage across splits,
class count floors (>= 2 in all splits), test independent group floor (>= 2),
strict causal issue-time filtration, and tamper detection.
"""
from __future__ import annotations

import csv
from datetime import datetime, timedelta, timezone
from pathlib import Path
import pytest

from flood_sentinel.cohort.split import (
    CANONICAL_PARTITIONS,
    GroupPartition,
    get_canonical_partitions,
    validate_zero_group_leakage,
    validate_temporal_embargo,
)
from flood_sentinel.cohort.builder import (
    COHORT_COLUMNS,
    CANONICAL_ISSUE_SPECS,
    CohortRow,
    build_cohort_rows,
    write_cohort_csv,
    load_cohort_csv,
    validate_cohort_integrity,
)
from flood_sentinel.acquisition.provenance import load_source_records_csv

WORKSPACE_ROOT = Path(__file__).resolve().parent.parent.parent
COHORT_PATH = WORKSPACE_ROOT / "data/cohort.csv"
SOURCE_RECORDS_PATH = WORKSPACE_ROOT / "data/source_records.csv"


# ==============================================================================
# 1. Canonical Cohort Schema and Integrity
# ==============================================================================

def test_cohort_file_exists_and_schema_valid():
    """Verify data/cohort.csv exists and conforms strictly to contract schema."""
    assert COHORT_PATH.is_file(), f"Missing cohort file: {COHORT_PATH}"
    rows = load_cohort_csv(COHORT_PATH)
    assert len(rows) >= 10, f"Expected at least 10 cohort rows, got {len(rows)}"

    seen_samples = set()
    for r in rows:
        sid = r["sample_id"]
        assert sid not in seen_samples, f"Duplicate sample_id: {sid}"
        seen_samples.add(sid)
        assert r["label"] in ("0", "1")
        assert r["split"] in ("train", "validation", "test")
        assert len(r["group_id"]) > 0
        assert len(r["source_ids"]) > 0


# ==============================================================================
# 2. Zero Group and Zero Source Record Leakage Across Splits
# ==============================================================================

def test_zero_group_leakage_across_splits():
    """Verify that no group_id appears in more than one split."""
    rows = load_cohort_csv(COHORT_PATH)
    group_splits: dict[str, set[str]] = {}
    for r in rows:
        group_splits.setdefault(r["group_id"], set()).add(r["split"])

    leaked = {g: sp for g, sp in group_splits.items() if len(sp) > 1}
    assert not leaked, f"Group leakage detected across splits: {leaked}"


def test_zero_source_record_leakage_across_splits():
    """Verify that no source record is shared between train, validation, or test."""
    rows = load_cohort_csv(COHORT_PATH)
    source_splits: dict[str, set[str]] = {}
    for r in rows:
        for sid in r["source_ids"].split("|"):
            source_splits.setdefault(sid, set()).add(r["split"])

    leaked = {s: sp for s, sp in source_splits.items() if len(sp) > 1}
    assert not leaked, (
        f"Source record leakage detected across splits! {len(leaked)} shared records: "
        f"{list(leaked.keys())[:5]}"
    )


def test_all_source_ids_exist_in_source_records():
    """Verify that every source record referenced in cohort.csv exists in source_records.csv."""
    cohort_rows = load_cohort_csv(COHORT_PATH)
    source_rows = load_source_records_csv(SOURCE_RECORDS_PATH)
    known_source_ids = {r["record_id"] for r in source_rows}

    for r in cohort_rows:
        src_ids = r["source_ids"].split("|")
        phantom_ids = set(src_ids) - known_source_ids
        assert not phantom_ids, (
            f"Phantom source IDs in sample '{r['sample_id']}': {list(phantom_ids)[:5]}"
        )


# ==============================================================================
# 3. Minimum Class Counts and Group Floors
# ==============================================================================

def test_minimum_class_counts_in_all_splits():
    """Verify that every split (train, validation, test) contains >= 2 positives and >= 2 negatives."""
    rows = load_cohort_csv(COHORT_PATH)
    split_counts: dict[str, dict[str, int]] = {
        "train": {"0": 0, "1": 0},
        "validation": {"0": 0, "1": 0},
        "test": {"0": 0, "1": 0},
    }
    for r in rows:
        split_counts[r["split"]][r["label"]] += 1

    for sp in ("train", "validation", "test"):
        assert split_counts[sp]["0"] >= 2, (
            f"Split '{sp}' negative count {split_counts[sp]['0']} is below floor 2"
        )
        assert split_counts[sp]["1"] >= 2, (
            f"Split '{sp}' positive count {split_counts[sp]['1']} is below floor 2"
        )


def test_test_split_independent_group_floor():
    """Verify that the test split contains at least 2 distinct group IDs."""
    rows = load_cohort_csv(COHORT_PATH)
    test_groups = {r["group_id"] for r in rows if r["split"] == "test"}
    assert len(test_groups) >= 2, (
        f"Test split distinct groups ({len(test_groups)}) is below floor 2. Groups: {test_groups}"
    )


# ==============================================================================
# 4. Strict Causal Issue-Time Filtration
# ==============================================================================

def test_strict_causal_availability_filtering():
    """Verify that every source record is strictly causal to its sample's issue timestamp."""
    source_rows = load_source_records_csv(SOURCE_RECORDS_PATH)
    timestamp_by_id = {
        r["record_id"]: datetime.fromisoformat(r["timestamp_utc"].replace("Z", "+00:00"))
        for r in source_rows
    }

    cohort_rows = load_cohort_csv(COHORT_PATH)
    for r in cohort_rows:
        sample_id = r["sample_id"]
        # Extract issue timestamp from sample_id: {site_no}_{YYYYMMDDTHHMMSSZ}
        parts = sample_id.split("_")
        ts_compact = parts[-1]
        t_issue = datetime.strptime(ts_compact, "%Y%m%dT%H%M%SZ").replace(tzinfo=timezone.utc)
        t_lookback_start = t_issue - timedelta(hours=24.0)

        for sid in r["source_ids"].split("|"):
            t_obs = timestamp_by_id[sid]
            assert t_obs <= t_issue, (
                f"Future observation leakage in sample '{sample_id}'! "
                f"Observation timestamp {t_obs} > issue timestamp {t_issue}"
            )
            assert t_obs >= t_lookback_start, (
                f"Observation outside 24h lookback window in sample '{sample_id}'! "
                f"Observation timestamp {t_obs} < lookback start {t_lookback_start}"
            )


# ==============================================================================
# 5. Spatiotemporal Embargo and Partition Verification
# ==============================================================================

def test_canonical_partitions_validation():
    """Verify canonical partition definitions pass group leakage and embargo checks."""
    partitions = CANONICAL_PARTITIONS
    validate_zero_group_leakage(partitions)
    validate_temporal_embargo(partitions, min_embargo_hours=24.0)


def test_embargo_violation_rejection():
    """Verify that overlapping temporal windows within the same cluster fail closed."""
    overlapping_parts = [
        GroupPartition(
            group_id="grp_train",
            split="train",
            basin_cluster="test_basin",
            site_no="0001",
            temporal_block="blk_1",
            start_utc="2026-06-01T00:00:00Z",
            end_utc="2026-06-05T00:00:00Z",
            description="train block",
        ),
        GroupPartition(
            group_id="grp_val",
            split="validation",
            basin_cluster="test_basin",
            site_no="0001",
            temporal_block="blk_2",
            start_utc="2026-06-04T00:00:00Z",  # Overlaps with train!
            end_utc="2026-06-10T00:00:00Z",
            description="val block",
        ),
    ]
    with pytest.raises(ValueError, match="Temporal overlap"):
        validate_temporal_embargo(overlapping_parts)


# ==============================================================================
# 6. Tamper Detection and Integrity Audit
# ==============================================================================

def test_tamper_detection_in_cohort():
    """Verify that tampering with cohort integrity causes validation to fail closed."""
    cohort_rows = load_cohort_csv(COHORT_PATH)
    source_rows = load_source_records_csv(SOURCE_RECORDS_PATH)
    known_source_ids = {r["record_id"] for r in source_rows}

    # 1. Tamper: inject cross-split group leakage
    tampered_group = [dict(r) for r in cohort_rows]
    tampered_group[0]["group_id"] = tampered_group[-1]["group_id"]  # train sample given test group
    with pytest.raises(ValueError, match="Group leakage"):
        validate_cohort_integrity(tampered_group, known_source_ids)

    # 2. Tamper: inject phantom source ID
    tampered_phantom = [dict(r) for r in cohort_rows]
    tampered_phantom[0]["source_ids"] += "|PHANTOM_RECORD_9999"
    with pytest.raises(ValueError, match="Phantom source record"):
        validate_cohort_integrity(tampered_phantom, known_source_ids)

    # 3. Tamper: reduce test groups below floor
    tampered_test_groups = [dict(r) for r in cohort_rows]
    for r in tampered_test_groups:
        if r["split"] == "test":
            r["group_id"] = "single_test_group"
    with pytest.raises(ValueError, match="Test distinct group count"):
        validate_cohort_integrity(tampered_test_groups, known_source_ids)
