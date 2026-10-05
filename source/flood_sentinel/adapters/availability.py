"""Causal availability and publication latency adapter for hydrologic issue boundaries."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Mapping, Sequence


class CausalLeakageError(ValueError):
    """Raised when an observation timestamp or publication availability leaks future information."""
    pass


@dataclass(frozen=True)
class AvailabilityAuditResult:
    """Audit receipt verifying causal timing compliance for an issue sample."""
    sample_id: str
    issue_time_utc: datetime
    lookback_start_utc: datetime
    earliest_obs_utc: datetime
    latest_obs_utc: datetime
    record_count: int
    is_causally_valid: bool


class AvailabilityAdapter:
    """Adapter enforcing strict causal boundaries and transmission latency at issue time."""

    @staticmethod
    def audit_sample_causality(
        sample_id: str,
        issue_time_utc: datetime,
        source_records: Sequence[Mapping[str, str]],
        lookback_hours: float = 24.0,
    ) -> AvailabilityAuditResult:
        """Audit that all constituent source records for an issue strictly precede issue time.

        Args:
            sample_id: Unique issue identifier.
            issue_time_utc: The exact forecast issue timestamp (timezone-aware UTC).
            source_records: Constituent observation records for this issue.
            lookback_hours: Maximum lookback duration preceding issue time.

        Raises:
            CausalLeakageError: If any observation timestamp is strictly greater than issue time,
                                or if telemetry publication timestamp is after issue time.
        """
        if not source_records:
            raise ValueError(f"Sample {sample_id} has zero source records to audit.")

        if issue_time_utc.tzinfo is None:
            issue_time_utc = issue_time_utc.replace(tzinfo=timezone.utc)

        t_lookback_start = issue_time_utc - timedelta(hours=lookback_hours)

        timestamps: list[datetime] = []
        for r in source_records:
            rec_id = r.get("record_id", "UNKNOWN")
            ts_str = r.get("timestamp_utc")
            if not ts_str:
                continue

            dt = datetime.fromisoformat(ts_str)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)

            timestamps.append(dt)

            # Strict Causality Check 1: Observation time cannot be in the future
            if dt > issue_time_utc:
                raise CausalLeakageError(
                    f"Causal violation in sample '{sample_id}' (record '{rec_id}'): "
                    f"observation timestamp {dt.isoformat()} > issue_time {issue_time_utc.isoformat()}."
                )

            # Strict Causality Check 2: Lookback lower boundary
            # Threshold records (NWPS) may be static baselines, but time-series observations must fit lookback
            param = r.get("parameter", "")
            if "flood_stage" not in param:
                # For stage and discharge, enforce lookback
                if dt < t_lookback_start - timedelta(minutes=15):  # allow 15m tolerance for boundary binning
                    raise CausalLeakageError(
                        f"Lookback boundary violation in sample '{sample_id}' (record '{rec_id}'): "
                        f"observation timestamp {dt.isoformat()} < lookback start {t_lookback_start.isoformat()}."
                    )

            # Strict Causality Check 3: Publication latency if recorded
            avail_str = r.get("available_utc")
            if avail_str:
                avail_dt = datetime.fromisoformat(avail_str)
                if avail_dt.tzinfo is None:
                    avail_dt = avail_dt.replace(tzinfo=timezone.utc)
                if avail_dt > issue_time_utc:
                    raise CausalLeakageError(
                        f"Publication latency violation in sample '{sample_id}' (record '{rec_id}'): "
                        f"available timestamp {avail_dt.isoformat()} > issue_time {issue_time_utc.isoformat()}."
                    )

        if not timestamps:
            raise ValueError(f"Sample {sample_id} contains no dated observation records.")

        return AvailabilityAuditResult(
            sample_id=sample_id,
            issue_time_utc=issue_time_utc,
            lookback_start_utc=t_lookback_start,
            earliest_obs_utc=min(timestamps),
            latest_obs_utc=max(timestamps),
            record_count=len(source_records),
            is_causally_valid=True,
        )

    @classmethod
    def audit_cohort_causality(
        cls,
        cohort_rows: Sequence[Mapping[str, str]],
        issue_times_lookup: Mapping[str, datetime],
        source_records_lookup: Mapping[str, Mapping[str, str]],
        lookback_hours: float = 24.0,
    ) -> dict[str, AvailabilityAuditResult]:
        """Audit causal availability across an entire cohort."""
        results: dict[str, AvailabilityAuditResult] = {}
        for row in cohort_rows:
            sid = row["sample_id"]
            t_issue = issue_times_lookup.get(sid)
            if t_issue is None:
                raise ValueError(f"Missing issue time for sample {sid}")
            sids = [s for s in row["source_ids"].split("|") if s]
            records = [source_records_lookup[s] for s in sids if s in source_records_lookup]
            results[sid] = cls.audit_sample_causality(sid, t_issue, records, lookback_hours)
        return results
