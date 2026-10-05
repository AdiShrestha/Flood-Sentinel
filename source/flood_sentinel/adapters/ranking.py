"""Lossless ranking and probability adapter for hydrological domain predictions."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
import hashlib
import math
from typing import Sequence
import numpy as np


class UncalibratedProbabilityError(ValueError):
    """Raised when an uncalibrated ranking score is passed to a probability scoring rule."""
    pass


@dataclass(frozen=True)
class DomainPrediction:
    """Hydrological prediction entity retaining domain metadata and score distinction.

    Attributes:
        sample_id: Unique issue identifier from cohort.csv.
        ranking_score: Real-valued monotonic score (e.g. reconstruction residual, stage anomaly).
        calibrated_probability: Optional calibrated probability in [0, 1] (e.g. isotonic or Platt).
        decision_threshold: Operating cutoff threshold in [0, 1].
        issue_time_utc: Timestamp when forecast was causally issued.
    """
    sample_id: str
    ranking_score: float
    calibrated_probability: float | None = None
    decision_threshold: float = 0.5
    issue_time_utc: datetime | None = None

    def __post_init__(self) -> None:
        if not self.sample_id or not isinstance(self.sample_id, str):
            raise ValueError("sample_id must be a non-empty string.")
        if not math.isfinite(self.ranking_score):
            raise ValueError(f"ranking_score must be a finite real number, got {self.ranking_score}.")
        if self.calibrated_probability is not None:
            if not (0.0 <= self.calibrated_probability <= 1.0) or not math.isfinite(self.calibrated_probability):
                raise ValueError(
                    f"calibrated_probability must lie in [0, 1], got {self.calibrated_probability}."
                )
        if not (0.0 <= self.decision_threshold <= 1.0) or not math.isfinite(self.decision_threshold):
            raise ValueError(f"decision_threshold must lie in [0, 1], got {self.decision_threshold}.")


class RankingAdapter:
    """Adapter projecting domain predictions into native evaluation formats losslessly."""

    @staticmethod
    def to_native_predictions(
        predictions: Sequence[DomainPrediction],
        use_probability: bool = False,
    ) -> list[tuple[str, float]]:
        """Project domain predictions to native (sample_id, score) pairs.

        Args:
            predictions: Sequence of DomainPrediction records.
            use_probability: If True, projects calibrated_probability (must be present).
                             If False, projects ranking_score directly.

        Returns:
            List of (sample_id, score) tuples.
        """
        out: list[tuple[str, float]] = []
        for p in predictions:
            if use_probability:
                if p.calibrated_probability is None:
                    raise UncalibratedProbabilityError(
                        f"Sample {p.sample_id} lacks calibrated_probability; "
                        "cannot project uncalibrated ranking score into probability metric."
                    )
                out.append((p.sample_id, float(p.calibrated_probability)))
            else:
                out.append((p.sample_id, float(p.ranking_score)))
        return out

    @staticmethod
    def compute_conversion_digest(predictions: Sequence[DomainPrediction]) -> str:
        """Compute an immutable SHA-256 digest of predictions and projection state."""
        h = hashlib.sha256()
        # Sort deterministically by sample_id
        sorted_preds = sorted(predictions, key=lambda x: x.sample_id)
        for p in sorted_preds:
            prob_str = f"{p.calibrated_probability:.10e}" if p.calibrated_probability is not None else "None"
            ts_str = p.issue_time_utc.isoformat() if p.issue_time_utc else "None"
            entry = f"{p.sample_id}:{p.ranking_score:.10e}:{prob_str}:{p.decision_threshold:.6f}:{ts_str}\n"
            h.update(entry.encode("utf-8"))
        return h.hexdigest()

    @staticmethod
    def validate_ranking_integrity(predictions: Sequence[DomainPrediction]) -> None:
        """Verify no duplicate sample IDs, no NaNs, and valid numeric types."""
        seen: set[str] = set()
        for p in predictions:
            if p.sample_id in seen:
                raise ValueError(f"Duplicate sample_id detected in predictions: {p.sample_id}")
            seen.add(p.sample_id)
            if not math.isfinite(p.ranking_score):
                raise ValueError(f"Non-finite ranking score for sample {p.sample_id}")
            if p.calibrated_probability is not None and not (0.0 <= p.calibrated_probability <= 1.0):
                raise UncalibratedProbabilityError(
                    f"Calibrated probability outside [0, 1] for sample {p.sample_id}: {p.calibrated_probability}"
                )

    @staticmethod
    def rank_order(scores: Sequence[float]) -> np.ndarray:
        """Compute 1-based ranks with average mid-rank resolution for ties."""
        arr = np.asarray(scores, dtype=np.float64)
        if arr.ndim != 1 or not len(arr) or not np.isfinite(arr).all():
            raise ValueError("Non-empty 1D finite score vector required for ranking.")
        n = len(arr)
        order = np.argsort(arr, kind="stable")
        ranks = np.empty(n, dtype=np.float64)
        i = 0
        while i < n:
            j = i + 1
            while j < n and arr[order[j]] == arr[order[i]]:
                j += 1
            ranks[order[i:j]] = (i + 1 + j) / 2.0
            i = j
        return ranks
