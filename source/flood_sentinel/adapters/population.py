"""Population inference adapter aggregating predictions over independent hydrologic groups."""
from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from typing import Mapping, Sequence
import numpy as np


class InsufficientGroupSupportError(ValueError):
    """Raised when cluster degrees of freedom or class balance is insufficient for population inference."""
    pass


@dataclass(frozen=True)
class GroupAggregationResult:
    """Cluster-level aggregated evaluation summary."""
    group_id: str
    sample_count: int
    positive_count: int
    negative_count: int
    mean_score: float
    accuracy: float
    brier: float | None = None


class PopulationAdapter:
    """Adapter organizing predictions into independent hydrologic-temporal cluster units."""

    @staticmethod
    def aggregate_by_group(
        sample_ids: Sequence[str],
        labels: Sequence[int],
        scores: Sequence[float],
        group_ids: Sequence[str],
        threshold: float = 0.5,
    ) -> dict[str, GroupAggregationResult]:
        """Aggregate sample-level predictions into independent group statistics."""
        if not (len(sample_ids) == len(labels) == len(scores) == len(group_ids)):
            raise ValueError("All input sequences must have identical non-zero length.")

        groups: dict[str, list[tuple[int, float]]] = defaultdict(list)
        for sid, y, s, g in zip(sample_ids, labels, scores, group_ids):
            groups[g].append((y, s))

        results: dict[str, GroupAggregationResult] = {}
        for gid, pairs in groups.items():
            ys = [p[0] for p in pairs]
            ss = [p[1] for p in pairs]
            n = len(pairs)
            pos = sum(ys)
            neg = n - pos
            preds = [int(s >= threshold) for s in ss]
            acc = sum(p == y for p, y in zip(preds, ys)) / n
            brier = float(np.mean([(s - y) ** 2 for s, y in zip(ss, ys)]))

            results[gid] = GroupAggregationResult(
                group_id=gid,
                sample_count=n,
                positive_count=pos,
                negative_count=neg,
                mean_score=float(np.mean(ss)),
                accuracy=acc,
                brier=brier,
            )

        return results

    @staticmethod
    def validate_population_support(
        group_ids: Sequence[str],
        labels: Sequence[int],
        min_groups: int = 2,
        min_class_count: int = 2,
    ) -> None:
        """Validate that the sample population contains sufficient independent clusters and classes."""
        unique_groups = set(group_ids)
        if len(unique_groups) < min_groups:
            raise InsufficientGroupSupportError(
                f"Cohort contains {len(unique_groups)} independent groups; "
                f"minimum required for population inference is {min_groups}."
            )

        pos = sum(labels)
        neg = len(labels) - pos
        if pos < min_class_count or neg < min_class_count:
            raise InsufficientGroupSupportError(
                f"Class distribution ({pos} positives, {neg} negatives) fails class floor of {min_class_count}."
            )
