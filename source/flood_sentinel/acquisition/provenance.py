"""Record-level provenance tracking and source records compilation.

Extracts normalized observation records from cryptographic manifests and raw payloads,
verifies byte-level integrity, and exports the authoritative data/source_records.csv catalog.
"""
from __future__ import annotations

import csv
import hashlib
import json
from pathlib import Path
from typing import Sequence

from .decoder import (
    NormalizedRecord,
    parse_usgs_iv_json,
    parse_noaa_nwps_json,
    parse_daymet_json,
)

SOURCE_RECORDS_COLUMNS = [
    "record_id",
    "origin",
    "provider",
    "site_no",
    "parameter",
    "timestamp_utc",
    "value_si",
    "unit_si",
    "quality_code",
    "raw_sha256",
]


def write_source_records_csv(records: Sequence[NormalizedRecord], output_path: Path) -> int:
    """Write normalized records to CSV file with schema verification."""
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # Check uniqueness of record_id
    seen_ids = set()
    unique_records: list[NormalizedRecord] = []
    for r in records:
        if r.record_id not in seen_ids:
            seen_ids.add(r.record_id)
            unique_records.append(r)

    # Sort records deterministically by site_no, parameter, timestamp_utc, record_id
    sorted_records = sorted(
        unique_records,
        key=lambda r: (r.site_no, r.parameter, r.timestamp_utc, r.record_id),
    )

    with output_path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=SOURCE_RECORDS_COLUMNS)
        writer.writeheader()
        for rec in sorted_records:
            writer.writerow(
                {
                    "record_id": rec.record_id,
                    "origin": rec.origin,
                    "provider": rec.provider,
                    "site_no": rec.site_no,
                    "parameter": rec.parameter,
                    "timestamp_utc": rec.timestamp_utc,
                    "value_si": rec.value_si,
                    "unit_si": rec.unit_si,
                    "quality_code": rec.quality_code,
                    "raw_sha256": rec.raw_sha256,
                }
            )

    return len(sorted_records)


def load_source_records_csv(csv_path: Path) -> list[dict[str, str]]:
    """Load and validate records from source_records.csv."""
    if not csv_path.is_file():
        raise FileNotFoundError(f"Source records CSV not found: {csv_path}")

    with csv_path.open("r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        if reader.fieldnames != SOURCE_RECORDS_COLUMNS:
            raise ValueError(
                f"CSV fieldnames mismatch. Expected {SOURCE_RECORDS_COLUMNS}, got {reader.fieldnames}"
            )
        rows = list(reader)

    # Validate non-emptiness and uniqueness of record_ids
    seen = set()
    for row in rows:
        rid = row.get("record_id")
        if not rid or rid in seen:
            raise ValueError(f"Duplicate or empty record_id: '{rid}'")
        seen.add(rid)

    return rows


def build_source_records_from_samples(
    manifest_path: Path,
    workspace_root: Path,
    output_csv_path: Path,
) -> int:
    """Build authoritative data/source_records.csv from provider manifest and raw payloads."""
    if not manifest_path.is_file():
        raise FileNotFoundError(f"Manifest not found: {manifest_path}")

    all_records: list[NormalizedRecord] = []

    with manifest_path.open("r", encoding="utf-8") as f:
        for line_num, line in enumerate(f, 1):
            if not line.strip():
                continue
            entry = json.loads(line)
            provider = entry["provider"]
            site_no = entry["site_no"]
            expected_sha = entry["sha256"]
            raw_rel_path = entry["raw_path"]

            raw_file = workspace_root / raw_rel_path
            if not raw_file.is_file():
                raise FileNotFoundError(f"Raw payload file missing: {raw_file} (manifest line {line_num})")

            raw_bytes = raw_file.read_bytes()
            actual_sha = hashlib.sha256(raw_bytes).hexdigest()
            if actual_sha != expected_sha:
                raise ValueError(
                    f"Cryptographic hash mismatch for {raw_file}! "
                    f"Manifest has {expected_sha}, computed {actual_sha}"
                )

            # Route to appropriate decoder
            if provider == "USGS-NWIS":
                decoded = parse_usgs_iv_json(raw_bytes, actual_sha)
                all_records.extend(decoded)
            elif provider == "NOAA-NWPS":
                decoded = parse_noaa_nwps_json(raw_bytes, actual_sha)
                all_records.extend(decoded)
            elif provider == "NASA-Daymet":
                decoded = parse_daymet_json(raw_bytes, actual_sha, site_no)
                all_records.extend(decoded)
            elif provider == "USGS-NWIS-SiteService":
                # Static site metadata probe; no observation timeseries
                continue
            else:
                raise ValueError(f"Unknown provider '{provider}' in manifest line {line_num}")

    return write_source_records_csv(all_records, output_csv_path)
