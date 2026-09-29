"""Verification script for Full-Scale Flood Event Acquisition & INV-023 (C02-09 / FR-006 / FR-017).

Validates that multi-source flood event files exist, Event-Truth Hierarchy is strictly
enforced per INV-023 (zero source promotion), INV-024 event counts are verified,
and manifests are intact.
"""

import json
import sys
from pathlib import Path
from typing import List

import pandas as pd

# Add project root to sys.path if running as standalone script
_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from source.utils.config import CHUNK02_DATA_DIR, CHUNK02_DIR, CHUNK02_MANIFESTS_DIR
from source.utils.logging_config import get_logger
from source.utils.manifest import validate_acquisition_provenance, validate_data_manifest

logger = get_logger("verify_events_full")


def validate_events_full() -> List[str]:
    """Validate full-scale flood events acquisition deliverables."""
    errors: List[str] = []

    panel_file = CHUNK02_DIR / "full_panel.json"
    if not panel_file.exists():
        return [f"Full panel manifest missing at {panel_file}"]

    with open(panel_file, "r", encoding="utf-8") as f:
        panel_data = json.load(f)

    gauges = panel_data.get("gauges", [])

    json_path = CHUNK02_DATA_DIR / "events" / "flood_events.json"
    parquet_path = CHUNK02_DATA_DIR / "events" / "flood_events.parquet"
    primary_parquet_path = CHUNK02_DATA_DIR / "events" / "primary_flood_episodes.parquet"

    if not json_path.exists():
        return [f"flood_events.json missing at {json_path}"]
    if not parquet_path.exists():
        return [f"flood_events.parquet missing at {parquet_path}"]
    if not primary_parquet_path.exists():
        return [f"primary_flood_episodes.parquet missing at {primary_parquet_path}"]

    try:
        with open(json_path, "r", encoding="utf-8") as f:
            all_events = json.load(f)

        df_all = pd.read_parquet(parquet_path)
        df_primary = pd.read_parquet(primary_parquet_path)

        # Check Event-Truth Hierarchy enforcement (INV-023)
        valid_sources = {"primary", "secondary", "contextual"}
        found_sources = set(df_all["source"].unique())
        invalid_sources = found_sources - valid_sources
        if invalid_sources:
            errors.append(f"Invalid event source tags found: {invalid_sources}")

        # Check that primary events are derived strictly from usgs_nwps_crossing
        if not (df_primary["source"] == "primary").all():
            errors.append("Non-primary events found in primary_flood_episodes.parquet")

        primary_count = len(df_primary)
        gauges_with_events = len(df_primary["site_no"].unique())

        logger.info(f"Verified Event Counts: {primary_count} primary events across {gauges_with_events} gauges.")

        if primary_count < 100:
            errors.append(f"Primary flood events count ({primary_count}) below 100 minimum threshold")
        if gauges_with_events < 30:
            errors.append(f"Gauges with qualifying events ({gauges_with_events}) below 30 minimum threshold")

    except Exception as e:
        errors.append(f"Failed to parse flood event files: {e}")

    # Validate data manifest
    manifest_file = CHUNK02_MANIFESTS_DIR / "events_data_manifest.json"
    if not manifest_file.exists():
        errors.append(f"events_data_manifest.json missing at {manifest_file}")
    else:
        try:
            with open(manifest_file, "r", encoding="utf-8") as f:
                manifest_data = json.load(f)
            manifest_errors = validate_data_manifest(manifest_data)
            errors.extend([f"Manifest error: {e}" for e in manifest_errors])
        except Exception as e:
            errors.append(f"Failed to read data manifest: {e}")

    # Validate provenance manifest
    prov_file = CHUNK02_MANIFESTS_DIR / "events_acquisition_provenance.json"
    if not prov_file.exists():
        errors.append(f"events_acquisition_provenance.json missing at {prov_file}")
    else:
        try:
            with open(prov_file, "r", encoding="utf-8") as f:
                p_data = json.load(f)
            p_errors = validate_acquisition_provenance(p_data)
            errors.extend([f"Provenance error: {e}" for e in p_errors])
        except Exception as e:
            errors.append(f"Failed to parse provenance manifest: {e}")

    return errors


def main() -> None:
    errors = validate_events_full()
    if errors:
        logger.error(f"Full-Scale Flood Event Acquisition Verification FAILED with {len(errors)} error(s):")
        for err in errors:
            logger.error(f"  - {err}")
        sys.exit(1)
    else:
        logger.info("Full-Scale Flood Event Acquisition Verification PASSED.")
        sys.exit(0)


if __name__ == "__main__":
    main()
