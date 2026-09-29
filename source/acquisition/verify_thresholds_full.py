"""Verification script for Full-Scale Flood Stage Threshold Acquisition (C02-08 / FR-005).

Validates that threshold files exist for all 54 full-panel streamgages, stage monotonicity
holds wherever thresholds are available, coverage metric exceeds required threshold, and
manifests are valid.
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

logger = get_logger("verify_thresholds_full")


def validate_thresholds_full() -> List[str]:
    """Validate full-scale threshold acquisition deliverables."""
    errors: List[str] = []

    panel_file = CHUNK02_DIR / "full_panel.json"
    if not panel_file.exists():
        return [f"Full panel manifest missing at {panel_file}"]

    with open(panel_file, "r", encoding="utf-8") as f:
        panel_data = json.load(f)

    gauges = panel_data.get("gauges", [])
    expected_site_nos = {g["site_no"] for g in gauges}

    json_path = CHUNK02_DATA_DIR / "thresholds" / "flood_thresholds.json"
    parquet_path = CHUNK02_DATA_DIR / "thresholds" / "flood_thresholds.parquet"

    if not json_path.exists():
        return [f"flood_thresholds.json missing at {json_path}"]
    if not parquet_path.exists():
        return [f"flood_thresholds.parquet missing at {parquet_path}"]

    try:
        with open(json_path, "r", encoding="utf-8") as f:
            thresh_list = json.load(f)

        if len(thresh_list) != len(gauges):
            errors.append(f"Expected {len(gauges)} threshold records, got {len(thresh_list)}")

        found_sites = {r["site_no"] for r in thresh_list}
        missing_sites = expected_site_nos - found_sites
        if missing_sites:
            errors.append(f"Missing stations in threshold records: {missing_sites}")

        # Check stage monotonicity
        avail_count = 0
        for r in thresh_list:
            if r.get("nwps_thresholds_available"):
                avail_count += 1
                stages = [r.get("action_stage_ft"), r.get("minor_stage_ft"), r.get("moderate_stage_ft"), r.get("major_stage_ft")]
                valid_stages = [s for s in stages if s is not None]
                if len(valid_stages) > 1:
                    for s1, s2 in zip(valid_stages[:-1], valid_stages[1:]):
                        if s1 > s2:
                            errors.append(f"Site {r['site_no']} non-monotonic flood stages: {stages}")

        coverage = float(avail_count / len(gauges))
        logger.info(f"Verified NWPS threshold coverage: {avail_count}/{len(gauges)} ({coverage:.1%}).")
        if coverage < 0.80:
            errors.append(f"NWPS threshold coverage ({coverage:.1%}) below 80% minimum floor")

    except Exception as e:
        errors.append(f"Failed to read threshold files: {e}")

    # Validate data manifest
    manifest_file = CHUNK02_MANIFESTS_DIR / "thresholds_data_manifest.json"
    if not manifest_file.exists():
        errors.append(f"thresholds_data_manifest.json missing at {manifest_file}")
    else:
        try:
            with open(manifest_file, "r", encoding="utf-8") as f:
                manifest_data = json.load(f)
            manifest_errors = validate_data_manifest(manifest_data)
            errors.extend([f"Manifest error: {e}" for e in manifest_errors])
        except Exception as e:
            errors.append(f"Failed to read data manifest: {e}")

    # Validate provenance manifest
    prov_file = CHUNK02_MANIFESTS_DIR / "thresholds_acquisition_provenance.json"
    if not prov_file.exists():
        errors.append(f"thresholds_acquisition_provenance.json missing at {prov_file}")
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
    errors = validate_thresholds_full()
    if errors:
        logger.error(f"Full-Scale Flood Stage Threshold Verification FAILED with {len(errors)} error(s):")
        for err in errors:
            logger.error(f"  - {err}")
        sys.exit(1)
    else:
        logger.info("Full-Scale Flood Stage Threshold Verification PASSED.")
        sys.exit(0)


if __name__ == "__main__":
    main()
