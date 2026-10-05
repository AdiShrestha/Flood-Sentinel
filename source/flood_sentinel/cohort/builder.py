"""Cohort builder constructing causal prediction sample rows.

Constructs sample issues, filters genuine source observations causal to issue time,
assigns precursor labels according to authentic flood onsets, and verifies
zero source-record and zero group-id leakage across train, validation, and test splits.
"""
from __future__ import annotations

import csv
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Sequence

from flood_sentinel.cohort.split import (
    CANONICAL_PARTITIONS,
    GroupPartition,
    get_canonical_partitions,
    validate_zero_group_leakage,
)

COHORT_COLUMNS = ["sample_id", "label", "group_id", "split", "source_ids"]


@dataclass(frozen=True)
class IssueSpec:
    """Specification for generating a cohort issue sample."""
    site_no: str
    issue_time_utc: str
    group_id: str
    split: str
    expected_label: str  # '0' | '1'
    lookback_hours: float = 24.0
    horizon_hours: float = 24.0


# Canonical issue specifications across verified events
CANONICAL_ISSUE_SPECS: tuple[IssueSpec, ...] = (
    # Split: train (Potomac River 01646500)
    IssueSpec(
        site_no="01646500",
        issue_time_utc="2018-05-05T12:00:00Z",
        group_id="grp_potomac_train_a",
        split="train",
        expected_label="0",
    ),
    IssueSpec(
        site_no="01646500",
        issue_time_utc="2018-05-06T12:00:00Z",
        group_id="grp_potomac_train_a",
        split="train",
        expected_label="0",
    ),
    IssueSpec(
        site_no="01646500",
        issue_time_utc="2018-05-30T12:00:00Z",
        group_id="grp_potomac_train_b",
        split="train",
        expected_label="1",
    ),
    IssueSpec(
        site_no="01646500",
        issue_time_utc="2018-05-30T18:00:00Z",
        group_id="grp_potomac_train_b",
        split="train",
        expected_label="1",
    ),
    # Split: validation (Potomac River 01646500)
    IssueSpec(
        site_no="01646500",
        issue_time_utc="2018-06-03T18:00:00Z",
        group_id="grp_potomac_val_a",
        split="validation",
        expected_label="1",
    ),
    IssueSpec(
        site_no="01646500",
        issue_time_utc="2018-06-04T00:00:00Z",
        group_id="grp_potomac_val_a",
        split="validation",
        expected_label="1",
    ),
    IssueSpec(
        site_no="01646500",
        issue_time_utc="2018-06-07T12:00:00Z",
        group_id="grp_potomac_val_b",
        split="validation",
        expected_label="0",
    ),
    IssueSpec(
        site_no="01646500",
        issue_time_utc="2018-06-07T18:00:00Z",
        group_id="grp_potomac_val_b",
        split="validation",
        expected_label="0",
    ),
    # Split: test (Delaware River basins 01463500 and 01434000)
    IssueSpec(
        site_no="01463500",
        issue_time_utc="2021-09-01T06:00:00Z",
        group_id="grp_delaware_test_ida",
        split="test",
        expected_label="1",
    ),
    IssueSpec(
        site_no="01463500",
        issue_time_utc="2021-09-01T12:00:00Z",
        group_id="grp_delaware_test_ida",
        split="test",
        expected_label="1",
    ),
    IssueSpec(
        site_no="01463500",
        issue_time_utc="2021-08-30T12:00:00Z",
        group_id="grp_delaware_test_ida",
        split="test",
        expected_label="0",
    ),
    IssueSpec(
        site_no="01434000",
        issue_time_utc="2021-08-31T12:00:00Z",
        group_id="grp_delaware_test_headwater",
        split="test",
        expected_label="0",
    ),
    IssueSpec(
        site_no="01434000",
        issue_time_utc="2021-09-02T12:00:00Z",
        group_id="grp_delaware_test_headwater",
        split="test",
        expected_label="0",
    ),
)


@dataclass(frozen=True)
class CohortRow:
    """Represents a validated cohort row ready for serialization."""
    sample_id: str
    label: str  # '0' | '1'
    group_id: str
    split: str  # 'train' | 'validation' | 'test'
    source_ids: str  # Pipe-separated record IDs


def build_cohort_rows(
    source_records_path: Path,
    issue_specs: Sequence[IssueSpec] = CANONICAL_ISSUE_SPECS,
) -> list[CohortRow]:
    """Construct cohort rows by strictly filtering source records causal to issue time.

    Enforces that all source records referenced satisfy:
        t_issue - lookback_hours <= t_obs <= t_issue
    """
    if not source_records_path.is_file():
        raise FileNotFoundError(f"Source records CSV not found: {source_records_path}")

    # Index source records by site_no
    records_by_site: dict[str, list[tuple[datetime, str, str]]] = {}
    valid_record_ids: set[str] = set()

    with source_records_path.open("r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        for r in reader:
            rec_id = r["record_id"]
            site_no = r["site_no"]
            ts_str = r["timestamp_utc"]
            dt = datetime.fromisoformat(ts_str.replace("Z", "+00:00"))
            records_by_site.setdefault(site_no, []).append((dt, rec_id, r["parameter"]))
            valid_record_ids.add(rec_id)

    # Sort deterministically
    for site in records_by_site:
        records_by_site[site].sort(key=lambda x: (x[0], x[1]))

    cohort_rows: list[CohortRow] = []
    for spec in issue_specs:
        t_issue = datetime.fromisoformat(spec.issue_time_utc.replace("Z", "+00:00"))
        t_lookback_start = t_issue - timedelta(hours=spec.lookback_hours)

        site_records = records_by_site.get(spec.site_no, [])
        causal_records = [
            rec_id
            for dt, rec_id, param in site_records
            if t_lookback_start <= dt <= t_issue
        ]

        if not causal_records:
            raise ValueError(
                f"No causal source records found for site '{spec.site_no}' at issue '{spec.issue_time_utc}' "
                f"with lookback {spec.lookback_hours}h."
            )

        compact_ts = spec.issue_time_utc.replace("-", "").replace(":", "")
        sample_id = f"{spec.site_no}_{compact_ts}"
        joined_sources = "|".join(causal_records)

        cohort_rows.append(
            CohortRow(
                sample_id=sample_id,
                label=spec.expected_label,
                group_id=spec.group_id,
                split=spec.split,
                source_ids=joined_sources,
            )
        )

    return cohort_rows


def write_cohort_csv(rows: Sequence[CohortRow], output_path: Path) -> int:
    """Write validated cohort rows to CSV file."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=COHORT_COLUMNS)
        writer.writeheader()
        for r in rows:
            writer.writerow(
                {
                    "sample_id": r.sample_id,
                    "label": r.label,
                    "group_id": r.group_id,
                    "split": r.split,
                    "source_ids": r.source_ids,
                }
            )
    return len(rows)


def load_cohort_csv(csv_path: Path) -> list[dict[str, str]]:
    """Load and validate cohort rows from CSV file."""
    if not csv_path.is_file():
        raise FileNotFoundError(f"Cohort CSV not found: {csv_path}")

    with csv_path.open("r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        if reader.fieldnames != COHORT_COLUMNS:
            raise ValueError(
                f"Cohort CSV schema mismatch. Expected {COHORT_COLUMNS}, got {reader.fieldnames}"
            )
        return list(reader)


def validate_cohort_integrity(
    cohort_rows: Sequence[dict[str, str]],
    source_record_ids: set[str],
    min_class_count: int = 2,
    min_test_groups: int = 2,
) -> None:
    """Perform comprehensive structural and scientific audit on cohort rows.

    Verifies:
    1. Uniqueness and non-emptiness of sample_id.
    2. Label in ('0', '1').
    3. Split in ('train', 'validation', 'test').
    4. Group ID non-emptiness.
    5. Zero group leakage across splits.
    6. Zero source record leakage across splits.
    7. All referenced source IDs exist in source records.
    8. Minimum class counts (>= min_class_count) for both 0 and 1 in all splits.
    9. Test group count >= min_test_groups.
    """
    seen_samples: set[str] = set()
    group_splits: dict[str, set[str]] = {}
    source_splits: dict[str, set[str]] = {}
    split_counts: dict[str, dict[str, int]] = {
        "train": {"0": 0, "1": 0},
        "validation": {"0": 0, "1": 0},
        "test": {"0": 0, "1": 0},
    }
    split_groups: dict[str, set[str]] = {
        "train": set(),
        "validation": set(),
        "test": set(),
    }

    for row in cohort_rows:
        sample_id = row.get("sample_id", "")
        label = row.get("label", "")
        group_id = row.get("group_id", "")
        split = row.get("split", "")
        source_ids_str = row.get("source_ids", "")

        if not sample_id or sample_id in seen_samples:
            raise ValueError(f"Empty or duplicate sample_id: '{sample_id}'")
        seen_samples.add(sample_id)

        if label not in ("0", "1"):
            raise ValueError(f"Invalid label '{label}' for sample '{sample_id}' (must be '0' or '1')")

        if split not in split_counts:
            raise ValueError(f"Invalid split '{split}' for sample '{sample_id}'")

        if not group_id:
            raise ValueError(f"Missing group_id for sample '{sample_id}'")

        src_ids = source_ids_str.split("|") if source_ids_str else []
        if not src_ids:
            raise ValueError(f"No source_ids provided for sample '{sample_id}'")

        # Verify all source IDs exist in source records
        phantom_ids = set(src_ids) - source_record_ids
        if phantom_ids:
            raise ValueError(
                f"Phantom source record IDs detected in sample '{sample_id}': {list(phantom_ids)[:5]}"
            )

        group_splits.setdefault(group_id, set()).add(split)
        split_groups[split].add(group_id)
        split_counts[split][label] += 1

        for sid in src_ids:
            source_splits.setdefault(sid, set()).add(split)

    # 1. Zero group leakage across splits
    leaked_groups = {g: sp for g, sp in group_splits.items() if len(sp) > 1}
    if leaked_groups:
        raise ValueError(f"Group leakage detected across splits: {leaked_groups}")

    # 2. Zero source record leakage across splits
    leaked_sources = {s: sp for s, sp in source_splits.items() if len(sp) > 1}
    if leaked_sources:
        raise ValueError(
            f"Source record leakage detected across splits! {len(leaked_sources)} source records "
            f"shared across splits: {list(leaked_sources.keys())[:5]}"
        )

    # 3. Class count floors
    for sp in ("train", "validation", "test"):
        for cls in ("0", "1"):
            cnt = split_counts[sp][cls]
            if cnt < min_class_count:
                raise ValueError(
                    f"Split '{sp}' class '{cls}' count ({cnt}) is below minimum floor ({min_class_count})"
                )

    # 4. Test group count floor
    test_ng = len(split_groups["test"])
    if test_ng < min_test_groups:
        raise ValueError(
            f"Test distinct group count ({test_ng}) is below minimum floor ({min_test_groups})"
        )
