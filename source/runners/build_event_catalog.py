"""Retired event-fragment entrypoint. Complete site-period evidence is required."""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import sys

# Ensure local source directory is available on sys.path
SRC_DIR = Path(__file__).resolve().parent.parent
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from flood_sentinel.acquisition.units import feet_to_meters
from flood_sentinel.events.thresholds import ThresholdRegistry
from flood_sentinel.events.detector import detect_episodes, EventEpisode
from flood_sentinel.events.catalog import write_catalog_files


def build_catalog(
    workspace_root: Path,
    parquet_out: Path,
    csv_out: Path,
) -> list[EventEpisode]:
    """Compile event interval catalog across candidate basins."""
    raise ValueError(
        "Named-event fragment catalog is quarantined; use predeclared complete site-period truth."
    )

def main() -> int:
    parser = argparse.ArgumentParser(description="Build flood event interval catalog.")
    parser.add_argument("--parquet-out", default="data/event_intervals.parquet")
    parser.add_argument("--csv-out", default="data/event_intervals.csv")
    args = parser.parse_args()

    root = Path(".").resolve()
    parquet_out = root / args.parquet_out
    csv_out = root / args.csv_out

    episodes = build_catalog(root, parquet_out, csv_out)
    print("=" * 80)
    print(f"Compiled Flood Event Catalog: {len(episodes)} episodes")
    print(f"Parquet: {parquet_out}")
    print(f"CSV: {csv_out}")
    print("=" * 80)
    for e in episodes:
        print(f" - {e.event_id} | Cat: {e.category} (Max: {e.max_category_attained}) | Onset: ({e.onset_lower_utc} .. {e.onset_upper_utc}] | Peak: {e.peak_value_si} m at {e.peak_time_utc} | Duration: {e.duration_hours} h")
    return 0


if __name__ == "__main__":
    sys.exit(main())
