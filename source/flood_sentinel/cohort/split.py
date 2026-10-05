"""Group-safe spatio-temporal split partitioning and cluster definitions.

Implements basin-time clustering and zero-group-leakage assignment to prevent
spatial and temporal autocorrelation between training, validation, and testing.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Sequence


@dataclass(frozen=True)
class GroupPartition:
    """Spatiotemporal partition definition representing an independent evaluation group."""
    group_id: str
    split: str  # 'train' | 'validation' | 'test'
    basin_cluster: str
    site_no: str
    temporal_block: str
    start_utc: str
    end_utc: str
    description: str


# Canonical basin clusters
CLUSTER_POTOMAC_FALLS = "potomac_falls"  # USGS 01646500, HUC-4 0207
CLUSTER_DELAWARE_LOWER = "delaware_lower"  # USGS 01463500, HUC-4 0204
CLUSTER_DELAWARE_UPPER = "delaware_upper"  # USGS 01434000, HUC-4 0204

SITE_TO_CLUSTER = {
    "01646500": CLUSTER_POTOMAC_FALLS,
    "01463500": CLUSTER_DELAWARE_LOWER,
    "01434000": CLUSTER_DELAWARE_UPPER,
}

# Canonical partitions across river basin systems
CANONICAL_PARTITIONS: tuple[GroupPartition, ...] = (
    GroupPartition(
        group_id="grp_potomac_train_a",
        split="train",
        basin_cluster=CLUSTER_POTOMAC_FALLS,
        site_no="01646500",
        temporal_block="2018_may_baseflow",
        start_utc="2018-05-01T00:00:00Z",
        end_utc="2018-05-10T23:59:59Z",
        description="Potomac River early May 2018 background baseflow",
    ),
    GroupPartition(
        group_id="grp_potomac_train_b",
        split="train",
        basin_cluster=CLUSTER_POTOMAC_FALLS,
        site_no="01646500",
        temporal_block="2018_may_rising",
        start_utc="2018-05-29T00:00:00Z",
        end_utc="2018-05-30T23:59:59Z",
        description="Potomac River late May 2018 pre-event rising limb",
    ),
    GroupPartition(
        group_id="grp_potomac_val_a",
        split="validation",
        basin_cluster=CLUSTER_POTOMAC_FALLS,
        site_no="01646500",
        temporal_block="2018_june_crest_rising",
        start_utc="2018-06-02T12:00:00Z",
        end_utc="2018-06-04T12:00:00Z",
        description="Potomac River early June 2018 minor flood crest rising limb",
    ),
    GroupPartition(
        group_id="grp_potomac_val_b",
        split="validation",
        basin_cluster=CLUSTER_POTOMAC_FALLS,
        site_no="01646500",
        temporal_block="2018_june_recession",
        start_utc="2018-06-07T00:00:00Z",
        end_utc="2018-06-08T23:59:59Z",
        description="Potomac River June 2018 secondary flood recession and quiescence",
    ),
    GroupPartition(
        group_id="grp_delaware_test_ida",
        split="test",
        basin_cluster=CLUSTER_DELAWARE_LOWER,
        site_no="01463500",
        temporal_block="2021_sept_ida_event",
        start_utc="2021-08-30T00:00:00Z",
        end_utc="2021-09-02T12:00:00Z",
        description="Lower Delaware River at Trenton Hurricane Ida flood event",
    ),
    GroupPartition(
        group_id="grp_delaware_test_headwater",
        split="test",
        basin_cluster=CLUSTER_DELAWARE_UPPER,
        site_no="01434000",
        temporal_block="2021_sept_ida_headwater",
        start_utc="2021-08-30T00:00:00Z",
        end_utc="2021-09-03T12:00:00Z",
        description="Upper Delaware River at Port Jervis non-flooded headwater runoff",
    ),
)


def get_canonical_partitions() -> dict[str, GroupPartition]:
    """Return dictionary of canonical group partitions mapped by group_id."""
    return {p.group_id: p for p in CANONICAL_PARTITIONS}


def validate_zero_group_leakage(partitions: Sequence[GroupPartition]) -> None:
    """Verify that no group_id appears in more than one split.

    Fails closed if duplicate group_id is found with contradictory split assignments.
    """
    seen_groups: dict[str, str] = {}
    for p in partitions:
        if p.group_id in seen_groups:
            existing_split = seen_groups[p.group_id]
            if existing_split != p.split:
                raise ValueError(
                    f"Group leakage detected! Group '{p.group_id}' assigned to both "
                    f"'{existing_split}' and '{p.split}'."
                )
        seen_groups[p.group_id] = p.split


def validate_temporal_embargo(
    partitions: Sequence[GroupPartition],
    min_embargo_hours: float = 24.0,
) -> None:
    """Verify that within the same basin cluster, different splits are separated by embargo."""
    by_cluster: dict[str, list[GroupPartition]] = {}
    for p in partitions:
        by_cluster.setdefault(p.basin_cluster, []).append(p)

    for cluster, parts in by_cluster.items():
        # Check pairwise across distinct splits
        for i in range(len(parts)):
            for j in range(i + 1, len(parts)):
                p1, p2 = parts[i], parts[j]
                if p1.split == p2.split:
                    continue
                t1_start = datetime.fromisoformat(p1.start_utc.replace("Z", "+00:00"))
                t1_end = datetime.fromisoformat(p1.end_utc.replace("Z", "+00:00"))
                t2_start = datetime.fromisoformat(p2.start_utc.replace("Z", "+00:00"))
                t2_end = datetime.fromisoformat(p2.end_utc.replace("Z", "+00:00"))

                # Check overlap
                if not (t1_end < t2_start or t2_end < t1_start):
                    raise ValueError(
                        f"Temporal overlap in cluster '{cluster}' between split '{p1.split}' "
                        f"({p1.group_id}) and split '{p2.split}' ({p2.group_id})!"
                    )
                # Check minimum embargo buffer
                gap_hours = (
                    (t2_start - t1_end).total_seconds() / 3600.0
                    if t1_end < t2_start
                    else (t1_start - t2_end).total_seconds() / 3600.0
                )
                if gap_hours < min_embargo_hours:
                    raise ValueError(
                        f"Embargo violation in cluster '{cluster}' between '{p1.group_id}' and '{p2.group_id}': "
                        f"separation {gap_hours:.1f}h is less than required {min_embargo_hours}h."
                    )
