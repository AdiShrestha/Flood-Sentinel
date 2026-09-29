"""Verification script for Pilot Gauge Panel Selection (C01-02).

Validates pilot_panel.json against schema, stratification constraints,
and USGS site ID format.
"""

import json
import re
import sys
from pathlib import Path
from typing import Any, Dict, List

# Add project root to sys.path if running as standalone script
_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from source.utils.config import CHUNK01_DIR
from source.utils.logging_config import get_logger

logger = get_logger("verify_pilot_panel")

USGS_SITE_REGEX = re.compile(r"^\d{8,15}$")


def validate_pilot_panel_file(path: Path) -> List[str]:
    """Validate pilot_panel.json against C01-02 contract constraints."""
    errors: List[str] = []

    if not path.exists():
        return [f"pilot_panel.json not found at {path}"]

    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception as e:
        return [f"Failed to parse JSON from {path}: {e}"]

    # Required top-level keys
    required_keys = {"panel_id", "selection_date", "gauges", "stratification_summary"}
    missing = required_keys - set(data.keys())
    if missing:
        errors.append(f"Missing required top-level keys: {sorted(missing)}")

    gauges = data.get("gauges", [])
    if not isinstance(gauges, list):
        errors.append("gauges field must be a list")
        return errors

    total_gauges = len(gauges)
    if not (15 <= total_gauges <= 20):
        errors.append(f"total_gauges must be between 15 and 20, got {total_gauges}")

    ref_count = 0
    non_ref_count = 0
    huc_regions = set()
    site_ids = set()

    for idx, g in enumerate(gauges):
        site_no = g.get("site_no", "")
        if not USGS_SITE_REGEX.match(site_no):
            errors.append(f"Gauge #{idx} has invalid USGS site_no format: '{site_no}'")

        if site_no in site_ids:
            errors.append(f"Duplicate site_no detected: '{site_no}'")
        site_ids.add(site_no)

        cls = g.get("gagesii_class")
        if cls == "Ref":
            ref_count += 1
        elif cls == "Non-Ref":
            non_ref_count += 1
        else:
            errors.append(f"Gauge {site_no} has invalid gagesii_class: '{cls}' (expected Ref or Non-Ref)")

        huc = g.get("huc_region")
        if huc:
            huc_regions.add(huc)
        else:
            errors.append(f"Gauge {site_no} missing huc_region")

        if not g.get("station_name"):
            errors.append(f"Gauge {site_no} missing station_name")

        if g.get("drainage_area_sqmi") is None or g["drainage_area_sqmi"] <= 0:
            errors.append(f"Gauge {site_no} has invalid drainage_area_sqmi: {g.get('drainage_area_sqmi')}")

    if ref_count < 1:
        errors.append(f"reference_count must be >= 1, got {ref_count}")
    if non_ref_count < 1:
        errors.append(f"non_reference_count must be >= 1, got {non_ref_count}")

    if len(huc_regions) < 3:
        errors.append(f"huc_regions_represented must be >= 3, got {len(huc_regions)}: {sorted(huc_regions)}")

    # Check stratification_summary consistency
    strat = data.get("stratification_summary", {})
    if strat.get("total_gauges") != total_gauges:
        errors.append(f"stratification_summary.total_gauges ({strat.get('total_gauges')}) != len(gauges) ({total_gauges})")
    if strat.get("reference_count") != ref_count:
        errors.append(f"stratification_summary.reference_count ({strat.get('reference_count')}) != calculated ({ref_count})")
    if strat.get("non_reference_count") != non_ref_count:
        errors.append(f"stratification_summary.non_reference_count ({strat.get('non_reference_count')}) != calculated ({non_ref_count})")

    return errors


def main() -> None:
    panel_path = CHUNK01_DIR / "pilot_panel.json"
    errors = validate_pilot_panel_file(panel_path)

    if errors:
        logger.error(f"Verification FAILED with {len(errors)} error(s):")
        for err in errors:
            logger.error(f"  - {err}")
        sys.exit(1)
    else:
        logger.info(f"Verification PASSED: {panel_path} is valid and meets all contract requirements.")
        sys.exit(0)


if __name__ == "__main__":
    main()
