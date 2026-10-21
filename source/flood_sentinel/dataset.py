"""Fail-closed causal loader for explicitly bound point-observation records.

Legacy source catalogs without stable versions, physical intervals, exact series
identities, and release evidence are rejected before materialization or scaling.
"""
from __future__ import annotations

import csv
import math
import re
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Mapping, Optional, Sequence

import numpy as np
import torch
from torch.utils.data import Dataset, DataLoader

from flood_sentinel.adapters.availability import AvailabilityAdapter, CausalLeakageError
from flood_sentinel.adapters.ancestry import AncestryAdapter
from flood_sentinel.identifiers import (
    SourceIdentityError, canonical_site, parse_sample_identity,
    require_identifier, split_source_ids,
)
from flood_sentinel.scaler import PersistentScaler
from flood_sentinel.temporal import utc


DEFAULT_CHANNELS = ("gage_height_m", "discharge_cms")
_SHA256 = re.compile(r"^[a-f0-9]{64}$")
_UNITS = {"gage_height_m": "m", "discharge_cms": "m3/s"}


@dataclass(frozen=True)
class CausalHydroSample:
    """A single causal time-series sample ready for model ingestion."""
    sample_id: str
    values: torch.Tensor
    observed: torch.Tensor
    label: int
    group_id: str
    split: str
    site_no: str
    issue_time_utc: str
    timestamps_utc: tuple[str, ...]
    source_record_ids: tuple[str, ...]


def parse_compact_issue_time(sample_id: str) -> datetime:
    """Extract an exact UTC issue instant from a canonical sample identifier."""
    _, timestamp = parse_sample_identity(sample_id)
    return datetime.strptime(timestamp, "%Y%m%dT%H%M%SZ").replace(tzinfo=timezone.utc)


def _read_csv(path: Path, *, key: str, allow_exact_duplicates: bool) -> dict[str, dict[str, str]]:
    out: dict[str, dict[str, str]] = {}
    with path.open("r", encoding="utf-8", newline="") as stream:
        reader = csv.DictReader(stream)
        if not reader.fieldnames or len(reader.fieldnames) != len(set(reader.fieldnames)):
            raise SourceIdentityError(f"{path} has missing or duplicate CSV headers")
        if key not in reader.fieldnames:
            raise SourceIdentityError(f"{path} is missing required key column {key!r}")
        for line, row in enumerate(reader, start=2):
            if None in row:
                raise SourceIdentityError(f"{path}:{line} has more fields than its header")
            ident = require_identifier(row.get(key), field=key)
            if ident in out:
                if not allow_exact_duplicates or out[ident] != row:
                    raise SourceIdentityError(f"Conflicting duplicate {key} {ident!r} at {path}:{line}")
                continue
            out[ident] = row
    return out


class CausalHydroDataset(Dataset):
    """Causal loader that binds every record to its canonical sample and grid cell.

    `series_by_site` is a reviewed identity manifest mapping canonical site to
    parameter to exact provider series ID. The loader intentionally has no
    inferred/default series and does not treat a hash or local signature as
    evidence of historical availability.
    """

    def __init__(
        self,
        cohort_path: Path,
        source_records_path: Path,
        split: Optional[str] = None,
        scaler: Optional[PersistentScaler] = None,
        channels: Sequence[str] = DEFAULT_CHANNELS,
        lookback_hours: float = 24.0,
        cadence_minutes: int = 15,
        verify_adapters: bool = True,
        *,
        series_by_site: Mapping[str, Mapping[str, str]] | None = None,
        allow_assumed_availability: bool = False,
    ) -> None:
        self.cohort_path = Path(cohort_path)
        self.source_records_path = Path(source_records_path)
        self.split, self.scaler = split, scaler
        self.channels = tuple(require_identifier(x, field="channel") for x in channels)
        self.lookback_hours, self.cadence_minutes = float(lookback_hours), int(cadence_minutes)
        if not self.channels or len(set(self.channels)) != len(self.channels):
            raise SourceIdentityError("Channels must be nonempty and unique")
        if any(ch not in _UNITS for ch in self.channels):
            raise SourceIdentityError("A unit contract is missing for a configured channel")
        if not math.isfinite(self.lookback_hours) or self.lookback_hours <= 0 or self.cadence_minutes <= 0:
            raise ValueError("Finite positive lookback and cadence are required")
        if type(allow_assumed_availability) is not bool:
            raise ValueError("allow_assumed_availability must be an explicit boolean")
        if verify_adapters is not True:
            raise CausalLeakageError("Adapter verification cannot be disabled for source materialization")
        if not self.cohort_path.is_file():
            raise FileNotFoundError(f"Cohort CSV not found: {self.cohort_path}")
        if not self.source_records_path.is_file():
            raise FileNotFoundError(f"Source records CSV not found: {self.source_records_path}")

        self._source_records = _read_csv(self.source_records_path, key="record_id", allow_exact_duplicates=True)
        # Validate catalog-key/record identity even when a caller later reuses this mapping.
        natural_keys: dict[tuple[str, str, str, str], str] = {}
        provider_versions: dict[tuple[str, str], str] = {}
        for key, record in self._source_records.items():
            if require_identifier(record.get("record_id"), field="record_id") != key:
                raise SourceIdentityError(f"Catalog key {key!r} differs from record_id")
            # Detect version ambiguity across all schema-complete rows, including
            # records not co-occurring in one sample window. Incomplete legacy
            # rows still fail at the strict linked-record checks below.
            if all(record.get(field) for field in ("site_no", "series_id", "parameter", "timestamp_utc")):
                instant = utc(datetime.fromisoformat(record["timestamp_utc"])).isoformat()
                natural = (canonical_site(record["site_no"]), record["series_id"],
                           record["parameter"], instant)
                prior = natural_keys.get(natural)
                if prior is not None and prior != key:
                    raise SourceIdentityError(f"Unresolved versions for one observation identity {natural!r}")
                natural_keys[natural] = key
            if record.get("provider") and record.get("provider_record_id"):
                version = (record["provider"], record["provider_record_id"])
                prior = provider_versions.get(version)
                if prior is not None and prior != key:
                    raise SourceIdentityError(f"Provider version ID {version!r} maps to multiple catalog IDs")
                provider_versions[version] = key

        all_rows = _read_csv(self.cohort_path, key="sample_id", allow_exact_duplicates=False)
        self._cohort_rows = [r for r in all_rows.values() if split is None or r.get("split") == split]
        if not self._cohort_rows:
            raise ValueError(f"No cohort rows found for split {split!r} in {self.cohort_path}")

        self.series_by_site: dict[str, dict[str, str]] | None = None
        if series_by_site is not None:
            self.series_by_site = {}
            for site, params in series_by_site.items():
                canonical = canonical_site(site, field="series manifest site")
                if canonical in self.series_by_site:
                    raise SourceIdentityError(f"Conflicting duplicate canonical site {canonical!r} in series manifest")
                if not isinstance(params, Mapping):
                    raise SourceIdentityError("Series manifest entries must map parameters to series IDs")
                normalized = {}
                for parameter, series_id in params.items():
                    parameter = require_identifier(parameter, field="series manifest parameter")
                    if parameter not in self.channels:
                        raise SourceIdentityError(f"Unexpected series-manifest parameter {parameter!r}")
                    normalized[parameter] = require_identifier(series_id, field="series_id")
                self.series_by_site[canonical] = normalized

        self._verified_rows: dict[str, tuple[str, ...]] = {}
        self._verify_adapters(allow_assumed=allow_assumed_availability)

    def _verify_adapters(self, *, allow_assumed: bool) -> None:
        """Validate release, site, series, parameter, units, interval, and grid before use."""
        for row in self._cohort_rows:
            sample_id = require_identifier(row.get("sample_id"), field="sample_id")
            sample_site, _ = parse_sample_identity(sample_id)
            if row.get("site_no"):
                if canonical_site(row["site_no"], field="cohort site_no") != sample_site:
                    raise SourceIdentityError(f"Cohort site conflicts with sample {sample_id!r}")
            issue_dt = parse_compact_issue_time(sample_id)
            group_id = require_identifier(row.get("group_id"), field="group_id")
            split_value = require_identifier(row.get("split"), field="split")
            if row.get("label") not in {"0", "1"}:
                raise SourceIdentityError(f"Sample {sample_id!r} has a nonbinary legacy cohort label")
            row["group_id"], row["split"] = group_id, split_value
            src_ids = split_source_ids(row.get("source_ids"))
            try:
                sample_recs = [self._source_records[sid] for sid in src_ids]
            except KeyError as exc:
                raise SourceIdentityError(f"Sample {sample_id!r} references unknown record {exc.args[0]!r}") from exc

            # Site binding is checked before any availability exception can mask a cross-site join.
            seen_slots: set[tuple[datetime, str]] = set()
            bound_records = []
            for rec in sample_recs:
                record_site = canonical_site(rec.get("site_no") or rec.get("site"), field="record site")
                if record_site != sample_site:
                    raise SourceIdentityError(
                        f"Cross-site source join: sample {sample_id!r} is {sample_site}, record is {record_site}"
                    )
                parameter = require_identifier(rec.get("parameter"), field="parameter")
                if parameter not in self.channels:
                    raise SourceIdentityError(f"Unexpected source parameter {parameter!r}")
                timestamp = utc(datetime.fromisoformat(require_identifier(rec.get("timestamp_utc"), field="timestamp_utc")))
                slot = (timestamp, parameter)
                if slot in seen_slots:
                    raise SourceIdentityError(f"Conflicting duplicate source grid slot {slot!r}")
                seen_slots.add(slot)
                bound_records.append((rec, timestamp, parameter))

            # Preserve all strict physical/release/issue/lookback checks.
            AvailabilityAdapter.audit_sample_causality(
                sample_id=sample_id, issue_time_utc=issue_dt, source_records=sample_recs,
                lookback_hours=self.lookback_hours, allow_assumed=allow_assumed,
            )
            AncestryAdapter.resolve_sample_ancestry(sample_id, src_ids, self._source_records)

            if self.series_by_site is None:
                raise SourceIdentityError("No reviewed site/parameter to exact-series identity manifest was supplied")
            if sample_site not in self.series_by_site:
                raise SourceIdentityError(f"No exact-series identity manifest for {sample_site}")
            lookback_start = issue_dt - timedelta(hours=self.lookback_hours)
            cadence = timedelta(minutes=self.cadence_minutes)
            steps = int(round((issue_dt - lookback_start).total_seconds() / cadence.total_seconds())) + 1
            grid = {lookback_start + i * cadence for i in range(steps)}
            for rec, timestamp, parameter in bound_records:
                expected_series = self.series_by_site[sample_site].get(parameter)
                if expected_series is None:
                    raise SourceIdentityError(f"No exact series ID for {sample_site}/{parameter}")
                if require_identifier(rec.get("series_id"), field="series_id") != expected_series:
                    raise SourceIdentityError(f"Series mismatch for sample {sample_id!r}, record {rec['record_id']!r}")
                if require_identifier(rec.get("provider_record_id"), field="provider_record_id") == "":
                    raise SourceIdentityError("Provider version identity is unresolved")
                if require_identifier(rec.get("provider"), field="provider") == "":
                    raise SourceIdentityError("Provider identity is unresolved")
                if rec.get("origin") != "observational":
                    raise SourceIdentityError("Constructed/simulated values cannot enter observational loader")
                if rec.get("unit_si") != _UNITS[parameter]:
                    raise SourceIdentityError(f"Unit mismatch for {parameter}: expected {_UNITS[parameter]!r}")
                raw_sha = require_identifier(rec.get("raw_sha256"), field="raw_sha256")
                if not _SHA256.fullmatch(raw_sha):
                    raise SourceIdentityError("raw_sha256 must be a lowercase SHA-256 digest")
                start = utc(datetime.fromisoformat(require_identifier(rec.get("observation_start_utc"), field="observation_start_utc")))
                end = utc(datetime.fromisoformat(require_identifier(rec.get("observation_end_utc"), field="observation_end_utc")))
                if start != timestamp or end != timestamp:
                    raise SourceIdentityError("This point-observation loader requires timestamp==physical interval start==end")
                if timestamp not in grid:
                    raise SourceIdentityError(f"Source timestamp {timestamp.isoformat()} is outside sample grid")
                value = rec.get("value_si")
                if value not in (None, ""):
                    number = float(value)
                    if not math.isfinite(number):
                        raise SourceIdentityError("Non-finite value cannot be materialized")
            self._verified_rows[sample_id] = src_ids

    def __len__(self) -> int:
        return len(self._cohort_rows)

    def __getitem__(self, idx: int) -> CausalHydroSample:
        row = self._cohort_rows[idx]
        sample_id = row["sample_id"]
        src_ids = self._verified_rows[sample_id]
        issue_dt = parse_compact_issue_time(sample_id)
        site_no, _ = parse_sample_identity(sample_id)
        lookback_delta = timedelta(hours=self.lookback_hours)
        delta_cadence = timedelta(minutes=self.cadence_minutes)
        grid_start = issue_dt - lookback_delta
        num_steps = int(round(lookback_delta.total_seconds() / delta_cadence.total_seconds())) + 1
        grid_times = [grid_start + i * delta_cadence for i in range(num_steps)]
        grid_strings = tuple(t.strftime("%Y-%m-%dT%H:%M:%SZ") for t in grid_times)
        time_to_idx = {t: i for i, t in enumerate(grid_times)}
        channel_to_idx = {ch: c for c, ch in enumerate(self.channels)}
        raw_matrix = np.full((num_steps, len(self.channels)), np.nan, dtype=np.float64)
        obs_mask = np.zeros((num_steps, len(self.channels)), dtype=bool)
        for sid in src_ids:
            rec = self._source_records[sid]
            ts = utc(datetime.fromisoformat(rec["timestamp_utc"]))
            param = rec["parameter"]
            t_idx, c_idx = time_to_idx[ts], channel_to_idx[param]
            if rec.get("value_si") not in (None, ""):
                raw_matrix[t_idx, c_idx] = float(rec["value_si"])
                obs_mask[t_idx, c_idx] = True
        if self.scaler is not None:
            norm_values, norm_mask = self.scaler.transform(raw_matrix)
            values_t, observed_t = torch.from_numpy(norm_values).float(), torch.from_numpy(norm_mask).bool()
        else:
            values_t, observed_t = torch.from_numpy(raw_matrix).float(), torch.from_numpy(obs_mask).bool()
        return CausalHydroSample(
            sample_id=sample_id, values=values_t, observed=observed_t,
            label=int(row["label"]), group_id=row["group_id"], split=row["split"],
            site_no=site_no, issue_time_utc=issue_dt.strftime("%Y-%m-%dT%H:%M:%SZ"),
            timestamps_utc=grid_strings, source_record_ids=tuple(src_ids),
        )

    def get_raw_observations_matrix(self) -> np.ndarray:
        """Return unique, already-validated training values for scaler fitting."""
        if self.split != "train":
            raise ValueError(f"Cannot extract raw training observations from split {self.split!r}")
        ids = sorted({sid for row in self._cohort_rows for sid in self._verified_rows[row["sample_id"]]})
        matrix = np.full((len(ids), len(self.channels)), np.nan, dtype=np.float64)
        for i, sid in enumerate(ids):
            record = self._source_records[sid]
            if record.get("value_si") not in (None, ""):
                matrix[i, self.channels.index(record["parameter"])] = float(record["value_si"])
        self.raw_fit_record_ids = tuple(ids)
        return matrix


def collate_causal_batch(samples: Sequence[CausalHydroSample]) -> dict[str, Any]:
    return {
        "values": torch.stack([s.values for s in samples]),
        "observed": torch.stack([s.observed for s in samples]),
        "labels": torch.tensor([s.label for s in samples], dtype=torch.long),
        "sample_ids": [s.sample_id for s in samples],
        "group_ids": [s.group_id for s in samples],
        "splits": [s.split for s in samples],
        "issue_times": [s.issue_time_utc for s in samples],
    }


def create_dataloader(dataset: CausalHydroDataset, batch_size: int = 4, shuffle: bool = False) -> DataLoader:
    return DataLoader(dataset, batch_size=batch_size, shuffle=shuffle, collate_fn=collate_causal_batch)
