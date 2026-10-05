"""Event episode catalog builder exporting to Parquet and CSV."""
from __future__ import annotations

from dataclasses import asdict
from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Sequence

import pyarrow as pa
import pyarrow.parquet as pq

from flood_sentinel.acquisition.units import feet_to_meters
from flood_sentinel.events.detector import EventEpisode, detect_episodes
from flood_sentinel.events.thresholds import ThresholdRegistry, FloodThreshold


CATALOG_COLUMNS = [
    "event_id",
    "site_no",
    "category",
    "threshold_si",
    "threshold_raw",
    "vertical_datum",
    "onset_lower_utc",
    "onset_upper_utc",
    "peak_time_utc",
    "peak_value_si",
    "end_time_utc",
    "duration_hours",
    "is_left_censored",
    "is_right_censored",
    "max_category_attained",
]

CATALOG_SCHEMA = pa.schema([
    pa.field("event_id", pa.string(), nullable=False),
    pa.field("site_no", pa.string(), nullable=False),
    pa.field("category", pa.string(), nullable=False),
    pa.field("threshold_si", pa.float64(), nullable=False),
    pa.field("threshold_raw", pa.float64(), nullable=False),
    pa.field("vertical_datum", pa.string(), nullable=False),
    pa.field("onset_lower_utc", pa.string(), nullable=True),
    pa.field("onset_upper_utc", pa.string(), nullable=False),
    pa.field("peak_time_utc", pa.string(), nullable=False),
    pa.field("peak_value_si", pa.float64(), nullable=False),
    pa.field("end_time_utc", pa.string(), nullable=True),
    pa.field("duration_hours", pa.float64(), nullable=True),
    pa.field("is_left_censored", pa.bool_(), nullable=False),
    pa.field("is_right_censored", pa.bool_(), nullable=False),
    pa.field("max_category_attained", pa.string(), nullable=False),
])


def episodes_to_pyarrow_table(episodes: Sequence[EventEpisode]) -> pa.Table:
    """Convert sequence of EventEpisode dataclasses to PyArrow Table."""
    dict_list = [asdict(e) for e in episodes]
    if not dict_list:
        # Return empty table with schema
        return pa.Table.from_arrays([pa.array([], type=f.type) for f in CATALOG_SCHEMA], schema=CATALOG_SCHEMA)

    arrays = []
    for field in CATALOG_SCHEMA:
        col_vals = [d[field.name] for d in dict_list]
        arrays.append(pa.array(col_vals, type=field.type))

    return pa.Table.from_arrays(arrays, schema=CATALOG_SCHEMA)


def write_catalog_files(
    episodes: Sequence[EventEpisode],
    parquet_path: Path,
    csv_path: Path,
) -> int:
    """Write episodes catalog to Parquet and CSV files."""
    parquet_path.parent.mkdir(parents=True, exist_ok=True)
    csv_path.parent.mkdir(parents=True, exist_ok=True)

    table = episodes_to_pyarrow_table(episodes)

    # 1. Write Parquet with snappy compression
    pq.write_table(table, parquet_path, compression="snappy")

    # 2. Write CSV
    import csv
    with csv_path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=CATALOG_COLUMNS)
        writer.writeheader()
        for ep in episodes:
            writer.writerow(asdict(ep))

    return len(episodes)


def load_catalog_parquet(parquet_path: Path) -> list[dict]:
    """Load episode catalog from Parquet file."""
    if not parquet_path.is_file():
        raise FileNotFoundError(f"Catalog Parquet not found: {parquet_path}")
    table = pq.read_table(parquet_path)
    return table.to_pylist()


def load_catalog_csv(csv_path: Path) -> list[dict]:
    """Load episode catalog from CSV file."""
    if not csv_path.is_file():
        raise FileNotFoundError(f"Catalog CSV not found: {csv_path}")
    import csv
    with csv_path.open("r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        return list(reader)
