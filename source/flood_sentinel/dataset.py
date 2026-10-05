"""Streaming causal dataset loaders consuming cohort, source records, and domain adapters.

Constructs regular-interval time-series matrices causal to each prediction issue,
enforces strict observation availability filtration (t_obs <= t_issue), and integrates
with domain adapters and PersistentScaler for normalized model inputs.
Adheres to Factory Principle C03, C14, and plan.md Section 6.1.
"""
from __future__ import annotations

import csv
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Optional, Sequence
import numpy as np
import torch
from torch.utils.data import Dataset, DataLoader

from flood_sentinel.adapters.availability import AvailabilityAdapter
from flood_sentinel.adapters.ancestry import AncestryAdapter
from flood_sentinel.scaler import PersistentScaler


DEFAULT_CHANNELS = ("gage_height_m", "discharge_cms")


@dataclass(frozen=True)
class CausalHydroSample:
    """A single causal time-series sample ready for model ingestion."""
    sample_id: str
    values: torch.Tensor       # Shape: (T, C), float32
    observed: torch.Tensor     # Shape: (T, C), bool
    label: int                 # 0 or 1
    group_id: str
    split: str                 # 'train' | 'validation' | 'test'
    site_no: str
    issue_time_utc: str
    timestamps_utc: tuple[str, ...]
    source_record_ids: tuple[str, ...]


def parse_compact_issue_time(sample_id: str) -> datetime:
    """Extract UTC datetime from sample_id format '{site_no}_{YYYYMMDDTHHMMSSZ}'."""
    parts = sample_id.split("_")
    ts_str = parts[-1]
    return datetime.strptime(ts_str, "%Y%m%dT%H%M%SZ").replace(tzinfo=timezone.utc)


class CausalHydroDataset(Dataset):
    """Causal hydrological time-series dataset with strict temporal filtration."""

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
    ) -> None:
        self.cohort_path = Path(cohort_path)
        self.source_records_path = Path(source_records_path)
        self.split = split
        self.scaler = scaler
        self.channels = tuple(channels)
        self.lookback_hours = float(lookback_hours)
        self.cadence_minutes = int(cadence_minutes)

        if not self.cohort_path.is_file():
            raise FileNotFoundError(f"Cohort CSV not found: {self.cohort_path}")
        if not self.source_records_path.is_file():
            raise FileNotFoundError(f"Source records CSV not found: {self.source_records_path}")

        # 1. Load source records catalog indexed by record_id
        self._source_records: dict[str, dict[str, str]] = {}
        with self.source_records_path.open("r", encoding="utf-8") as f:
            for r in csv.DictReader(f):
                self._source_records[r["record_id"]] = r

        # 2. Load cohort rows, optionally filtered by split
        self._cohort_rows: list[dict[str, str]] = []
        with self.cohort_path.open("r", encoding="utf-8") as f:
            for r in csv.DictReader(f):
                if split is None or r["split"] == split:
                    self._cohort_rows.append(r)

        if not self._cohort_rows:
            raise ValueError(f"No cohort rows found for split '{split}' in {self.cohort_path}")

        # 3. Domain adapter verifications
        if verify_adapters:
            self._verify_adapters()

    def _verify_adapters(self) -> None:
        """Run P05 Ancestry and Availability adapter verifications on all loaded samples."""
        for row in self._cohort_rows:
            sample_id = row["sample_id"]
            issue_dt = parse_compact_issue_time(sample_id)
            src_ids = row["source_ids"].split("|")

            # Collect source records for this sample
            sample_recs = []
            for sid in src_ids:
                if sid not in self._source_records:
                    raise KeyError(f"Sample '{sample_id}' references unknown source record '{sid}'")
                sample_recs.append(self._source_records[sid])

            # 1. P05 Availability check: strictly enforces t_obs <= t_issue and lookback bounds
            AvailabilityAdapter.audit_sample_causality(
                sample_id=sample_id,
                issue_time_utc=issue_dt,
                source_records=sample_recs,
                lookback_hours=self.lookback_hours,
            )

            # 2. P05 Ancestry check: validates cryptographic provenance and source record existence
            AncestryAdapter.resolve_sample_ancestry(
                sample_id=sample_id,
                source_ids=src_ids,
                source_records_lookup=self._source_records,
            )

    def __len__(self) -> int:
        return len(self._cohort_rows)

    def __getitem__(self, idx: int) -> CausalHydroSample:
        row = self._cohort_rows[idx]
        sample_id = row["sample_id"]
        label = int(row["label"])
        group_id = row["group_id"]
        split = row["split"]
        src_ids = row["source_ids"].split("|")

        issue_dt = parse_compact_issue_time(sample_id)
        site_no = row["sample_id"].split("_")[0]

        # Construct time grid from (t_issue - lookback) to t_issue
        delta_cadence = timedelta(minutes=self.cadence_minutes)
        lookback_delta = timedelta(hours=self.lookback_hours)
        grid_start = issue_dt - lookback_delta

        num_steps = int(round(lookback_delta.total_seconds() / delta_cadence.total_seconds())) + 1
        grid_times = [grid_start + i * delta_cadence for i in range(num_steps)]
        grid_strings = tuple(t.strftime("%Y-%m-%dT%H:%M:%SZ") for t in grid_times)

        # Build mapping from grid time string to step index
        time_to_idx = {t_str: i for i, t_str in enumerate(grid_strings)}
        channel_to_idx = {ch: c for c, ch in enumerate(self.channels)}

        # Allocate raw value matrix and observed mask
        # NaN represents missing observations prior to normalization
        raw_matrix = np.full((num_steps, len(self.channels)), np.nan, dtype=np.float64)
        obs_mask = np.zeros((num_steps, len(self.channels)), dtype=bool)

        for sid in src_ids:
            rec = self._source_records[sid]
            ts = rec["timestamp_utc"]
            param = rec["parameter"]

            # Map to grid
            if ts in time_to_idx and param in channel_to_idx:
                t_idx = time_to_idx[ts]
                c_idx = channel_to_idx[param]
                raw_matrix[t_idx, c_idx] = float(rec["value_si"])
                obs_mask[t_idx, c_idx] = True

        # Apply PersistentScaler if provided
        if self.scaler is not None:
            norm_values, norm_mask = self.scaler.transform(raw_matrix)
            values_t = torch.from_numpy(norm_values).float()
            observed_t = torch.from_numpy(norm_mask).bool()
        else:
            values_t = torch.from_numpy(raw_matrix).float()
            observed_t = torch.from_numpy(obs_mask).bool()

        return CausalHydroSample(
            sample_id=sample_id,
            values=values_t,
            observed=observed_t,
            label=label,
            group_id=group_id,
            split=split,
            site_no=site_no,
            issue_time_utc=issue_dt.strftime("%Y-%m-%dT%H:%M:%SZ"),
            timestamps_utc=grid_strings,
            source_record_ids=tuple(src_ids),
        )

    def get_raw_observations_matrix(self) -> np.ndarray:
        """Extract concatenated unnormalized observations matrix for scaler fitting.

        Only valid when self.split == 'train'.
        """
        if self.split != "train":
            raise ValueError(
                f"Cannot extract raw training observations from split '{self.split}'. "
                "Normalizer must strictly be fitted on 'train' split."
            )
        all_blocks = []
        for i in range(len(self)):
            # Temporarily fetch sample without scaler
            saved_scaler = self.scaler
            self.scaler = None
            try:
                sample = self[i]
                arr = sample.values.numpy()
                all_blocks.append(arr)
            finally:
                self.scaler = saved_scaler
        return np.concatenate(all_blocks, axis=0)


def collate_causal_batch(samples: Sequence[CausalHydroSample]) -> dict[str, Any]:
    """Collate function for PyTorch DataLoader."""
    values = torch.stack([s.values for s in samples], dim=0)       # (B, T, C)
    observed = torch.stack([s.observed for s in samples], dim=0)   # (B, T, C)
    labels = torch.tensor([s.label for s in samples], dtype=torch.long)
    sample_ids = [s.sample_id for s in samples]
    group_ids = [s.group_id for s in samples]
    splits = [s.split for s in samples]
    issue_times = [s.issue_time_utc for s in samples]

    return {
        "values": values,
        "observed": observed,
        "labels": labels,
        "sample_ids": sample_ids,
        "group_ids": group_ids,
        "splits": splits,
        "issue_times": issue_times,
    }


def create_dataloader(
    dataset: CausalHydroDataset,
    batch_size: int = 4,
    shuffle: bool = False,
) -> DataLoader:
    """Create PyTorch DataLoader for CausalHydroDataset."""
    return DataLoader(
        dataset,
        batch_size=batch_size,
        shuffle=shuffle,
        collate_fn=collate_causal_batch,
    )
