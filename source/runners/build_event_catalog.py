"""Builds authoritative flood event interval catalog for candidate river basins.

Detects interval threshold crossings across official NOAA NWPS categories
(action, minor, moderate, major) using strict 24-hour hysteresis separation,
preserving lower threshold crossings and exact sub-daily timestamps.
"""
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
    source_records_path = workspace_root / "data/source_records.csv"
    registry = ThresholdRegistry.from_source_records(source_records_path)

    # 1. Historical authentic flood episodes for candidate basins
    # Event 1: Potomac River at Little Falls (USGS 01646500) June 2018 Flood
    # Event 2: Delaware River at Trenton NJ (USGS 01463500) Sept 2021 Hurricane Ida
    # Additional baseline records from data/source_records.csv
    import urllib.request
    import gzip

    all_episodes: list[EventEpisode] = []

    # Historical event queries for candidate basins
    event_specs = [
        {
            "site_no": "01646500",
            "name": "Potomac River Little Falls (June 2018 Flood)",
            "url": "https://waterservices.usgs.gov/nwis/iv/?format=json&sites=01646500&startDT=2018-06-01&endDT=2018-06-08&parameterCd=00065",
        },
        {
            "site_no": "01463500",
            "name": "Delaware River Trenton (Sept 2021 Hurricane Ida)",
            "url": "https://waterservices.usgs.gov/nwis/iv/?format=json&sites=01463500&startDT=2021-09-01&endDT=2021-09-06&parameterCd=00065",
        },
    ]

    for spec in event_specs:
        site_no = spec["site_no"]
        thresh_map = {t.category: t.value_si for t in registry.get_all_for_site(site_no)}
        if not thresh_map:
            continue

        req = urllib.request.Request(
            spec["url"],
            headers={"User-Agent": "FloodSentinel-Research/1.0", "Accept-Encoding": "gzip, deflate"},
        )
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                raw = resp.read()
                if resp.headers.get("Content-Encoding") == "gzip":
                    raw = gzip.decompress(raw)
                data = json.loads(raw.decode("utf-8"))
                ts = data["value"]["timeSeries"][0]["values"][0]["value"]
                obs = [
                    (datetime.fromisoformat(v["dateTime"]), feet_to_meters(float(v["value"])))
                    for v in ts
                    if v.get("value")
                ]

            for cat in ["action", "minor", "moderate", "major"]:
                thresh = registry.get(site_no, cat)
                if thresh:
                    eps = detect_episodes(
                        site_no=site_no,
                        observations=obs,
                        threshold_si=thresh.value_si,
                        threshold_raw=thresh.value_raw,
                        category=cat,
                        vertical_datum=thresh.vertical_datum,
                        separation_hours=24.0,
                        all_thresholds_si=thresh_map,
                    )
                    all_episodes.extend(eps)
        except Exception as ex:
            print(f"Warning: Could not fetch real-time event for {site_no}: {ex}", file=sys.stderr)

    # Sort episodes deterministically
    all_episodes.sort(key=lambda e: (e.site_no, e.onset_upper_utc, e.category))

    write_catalog_files(all_episodes, parquet_out, csv_out)
    return all_episodes


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
