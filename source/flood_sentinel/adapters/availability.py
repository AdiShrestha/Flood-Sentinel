"""Causal availability and publication latency adapter for hydrologic issue boundaries."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Mapping, Sequence
from flood_sentinel.identifiers import require_identifier, split_source_ids, validate_record_lookup
from flood_sentinel.temporal import utc


class CausalLeakageError(ValueError):
    """Raised when an observation timestamp or publication availability leaks future information."""
    pass


@dataclass(frozen=True)
class AvailabilityAuditResult:
    """Temporal-consistency result for caller-supplied availability fields.

    `is_causally_valid` means only that supplied interval/release timestamps obey
    the chronology checks. The `availability_basis` string and any local digest
    do not authenticate a provider's historical release or arrival time.
    """
    sample_id: str
    issue_time_utc: datetime
    lookback_start_utc: datetime
    earliest_obs_utc: datetime
    latest_obs_utc: datetime
    record_count: int
    is_causally_valid: bool
    availability_evidence_status: str = "unverified_caller_claim"


class AvailabilityAdapter:
    """Adapter enforcing strict causal boundaries and transmission latency at issue time."""

    @staticmethod
    def audit_sample_causality(
        sample_id: str,
        issue_time_utc: datetime,
        source_records: Sequence[Mapping[str, str]],
        lookback_hours: float = 24.0,
        *, allow_assumed: bool = False,
    ) -> AvailabilityAuditResult:
        """Check supplied observation/release chronology; do not authenticate vintages.

        Args:
            sample_id: Unique issue identifier.
            issue_time_utc: The exact forecast issue timestamp (timezone-aware UTC).
            source_records: Constituent observation records for this issue.
            lookback_hours: Maximum lookback duration preceding issue time.

        Raises:
            CausalLeakageError: If any observation timestamp is strictly greater than issue time,
                                or if telemetry publication timestamp is after issue time.
        """
        sample_id = require_identifier(sample_id, field="sample_id")
        if not source_records:
            raise ValueError(f"Sample {sample_id} has zero source records to audit.")

        issue_time_utc = utc(issue_time_utc)
        if type(allow_assumed) is not bool:
            raise ValueError("Explicit allow_assumed boolean required")
        if not 0 < lookback_hours < float("inf"):
            raise ValueError("Finite positive lookback required")

        t_lookback_start = issue_time_utc - timedelta(hours=lookback_hours)

        record_ids: list[str] = []
        for record in source_records:
            if not isinstance(record, Mapping):
                raise ValueError("Source record mappings are required")
            record_ids.append(require_identifier(record.get("record_id"), field="record_id"))
        if len(record_ids) != len(set(record_ids)):
            raise ValueError("Duplicate source record IDs")

        timestamps: list[datetime] = []
        for r in source_records:
            rec_id = require_identifier(r.get("record_id"), field="record_id")
            ts_str = r.get("observation_end_utc")
            start_str = r.get("observation_start_utc")
            if not ts_str or not start_str:
                raise CausalLeakageError("Missing physical observation interval")
            dt = utc(datetime.fromisoformat(ts_str))
            start = utc(datetime.fromisoformat(start_str))
            if start > dt:
                raise CausalLeakageError("Inverted observation interval")
            basis = r.get("availability_basis")
            if basis != "observed" and not (basis == "assumed" and allow_assumed):
                raise CausalLeakageError("Missing actual release/vintage evidence; assumed replay must be explicit")
            if not r.get("available_utc"):
                raise CausalLeakageError("Missing release/vintage timestamp")

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
                avail_dt = utc(avail_dt)
                if avail_dt < dt:
                    raise CausalLeakageError("Release precedes physical closure")
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
            availability_evidence_status="unverified_caller_claim",
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
        validate_record_lookup(source_records_lookup)
        if set(issue_times_lookup) != {require_identifier(row.get("sample_id"), field="sample_id")
                                      for row in cohort_rows}:
            raise ValueError("Issue-time lookup keys must exactly match cohort sample IDs")
        results: dict[str, AvailabilityAuditResult] = {}
        for row in cohort_rows:
            sid = require_identifier(row.get("sample_id"), field="sample_id")
            t_issue = issue_times_lookup.get(sid)
            if t_issue is None:
                raise ValueError(f"Missing issue time for sample {sid}")
            sids = split_source_ids(row.get("source_ids"))
            if any(s not in source_records_lookup for s in sids):
                raise ValueError("Unresolved source ID")
            records = [source_records_lookup[s] for s in sids]
            results[sid] = cls.audit_sample_causality(sid, t_issue, records, lookback_hours)
        return results
