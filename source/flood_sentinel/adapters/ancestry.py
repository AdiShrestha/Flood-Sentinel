"""Multi-origin record ancestry adapter for tracking raw observation provenance."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
import hashlib
from typing import Mapping, Sequence
from flood_sentinel.identifiers import require_identifier, split_source_ids, validate_record_lookup


class SourceDuplicationError(ValueError):
    """Raised when duplicate source IDs or artificial observation padding is detected."""
    pass


class MissingSourceError(ValueError):
    """Raised when a referenced source_id is missing from the authoritative catalog."""
    pass


@dataclass(frozen=True)
class RecordAncestry:
    """Provenance and lineage descriptor for a single cohort sample.

    Attributes:
        sample_id: Cohort sample ID.
        source_ids: Distinct ordered tuple of constituent source record IDs.
        providers: Set of distinct source providers (e.g. USGS, NOAA-NWPS, NASA-Daymet).
        parameters: Set of physical parameters (e.g. gage_height_m, discharge_cms).
        start_time_utc: Earliest observation timestamp in the constituent records.
        end_time_utc: Latest observation timestamp in the constituent records.
        ancestry_digest: Local SHA-256 digest over supplied source IDs and raw hashes; not authentication.
    """
    sample_id: str
    source_ids: tuple[str, ...]
    providers: frozenset[str]
    parameters: frozenset[str]
    start_time_utc: datetime
    end_time_utc: datetime
    ancestry_digest: str

    def __post_init__(self) -> None:
        require_identifier(self.sample_id, field="sample_id")
        if not self.source_ids:
            raise ValueError(f"sample_id {self.sample_id} must have at least one source record.")
        for source_id in self.source_ids:
            require_identifier(source_id, field="source_id")
        if len(self.source_ids) != len(set(self.source_ids)):
            raise SourceDuplicationError(
                f"Sample {self.sample_id} contains duplicate source_ids in ancestry."
            )


class AncestryAdapter:
    """Bind ancestry to supplied catalogs without authenticating provider origin or release."""

    @staticmethod
    def compute_ancestry_digest(
        source_ids: Sequence[str],
        source_records_lookup: Mapping[str, Mapping[str, str]],
    ) -> str:
        """Compute a deterministic local SHA-256 digest of supplied source records.

        Sorted strictly by source_id to ensure canonical hashing regardless of delimiter order.
        The digest detects later byte changes only if its reference is trusted; it
        is not a provider signature or proof of historical availability.
        """
        validate_record_lookup(source_records_lookup)
        h = hashlib.sha256()
        sorted_ids = sorted(require_identifier(s, field="source_id") for s in source_ids)
        for sid in sorted_ids:
            rec = source_records_lookup.get(sid)
            if rec is None:
                raise MissingSourceError(f"source_id '{sid}' not found in source records lookup.")
            raw_sha = rec.get("raw_sha256", "")
            rec_id = rec.get("record_id", sid)
            entry = f"{rec_id}:{raw_sha}\n"
            h.update(entry.encode("utf-8"))
        return h.hexdigest()

    @classmethod
    def resolve_sample_ancestry(
        cls,
        sample_id: str,
        source_ids: Sequence[str],
        source_records_lookup: Mapping[str, Mapping[str, str]],
    ) -> RecordAncestry:
        """Resolve a cohort sample into an audited RecordAncestry object."""
        sample_id = require_identifier(sample_id, field="sample_id")
        validate_record_lookup(source_records_lookup)
        source_ids = tuple(require_identifier(s, field="source_id") for s in source_ids)
        if not source_ids:
            raise ValueError(f"Sample {sample_id} has empty source_ids.")

        # Check for duplicate source IDs within the sample
        if len(source_ids) != len(set(source_ids)):
            raise SourceDuplicationError(
                f"Duplicate source IDs detected for sample '{sample_id}'."
            )

        providers: set[str] = set()
        parameters: set[str] = set()
        timestamps: list[datetime] = []

        for sid in source_ids:
            rec = source_records_lookup.get(sid)
            if rec is None:
                raise MissingSourceError(
                    f"Sample '{sample_id}' references unknown source_id '{sid}'."
                )
            providers.add(rec.get("provider", "UNKNOWN"))
            parameters.add(rec.get("parameter", "UNKNOWN"))
            ts_str = rec.get("timestamp_utc")
            if ts_str:
                timestamps.append(datetime.fromisoformat(ts_str))

        if not timestamps:
            raise ValueError(f"Sample '{sample_id}' has no timestamped source records.")

        t_min = min(timestamps)
        t_max = max(timestamps)
        digest = cls.compute_ancestry_digest(source_ids, source_records_lookup)

        return RecordAncestry(
            sample_id=sample_id,
            source_ids=tuple(sorted(source_ids)),
            providers=frozenset(providers),
            parameters=frozenset(parameters),
            start_time_utc=t_min,
            end_time_utc=t_max,
            ancestry_digest=digest,
        )

    @classmethod
    def validate_cohort_ancestry(
        cls,
        cohort_rows: Sequence[Mapping[str, str]],
        source_records_lookup: Mapping[str, Mapping[str, str]],
    ) -> dict[str, RecordAncestry]:
        """Validate an entire cohort's ancestry, ensuring 0 missing records and 0 duplicated IDs."""
        resolved: dict[str, RecordAncestry] = {}
        for row in cohort_rows:
            sid = require_identifier(row.get("sample_id"), field="sample_id")
            raw_sids = split_source_ids(row.get("source_ids"))
            resolved[sid] = cls.resolve_sample_ancestry(sid, raw_sids, source_records_lookup)
        return resolved
