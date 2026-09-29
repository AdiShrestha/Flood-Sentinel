"""Verification script for Full Gauge Panel Selection & Stratification (C02-03).

Validates full_panel.json structure, gauge count (>= 50), Ref/Non-Ref balance,
HUC regional diversity (>= 10), and complete retention of all 18 pilot gauges.
"""

import json
import sys
from pathlib import Path
from typing import List, Set

# Add project root to sys.path if running as standalone script
_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from source.utils.config import CHUNK01_DIR, CHUNK02_DIR
from source.utils.logging_config import get_logger

logger = get_logger("verify_full_panel")


def validate_full_panel() -> List[str]:
    """Validate full_panel.json deliverables."""
    errors: List[str] = []

    panel_file = CHUNK02_DIR / "full_panel.json"
    if not panel_file.exists():
        return [f"full_panel.json missing at {panel_file}"]

    try:
        with open(panel_file, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception as e:
        return [f"Failed to parse JSON from {panel_file}: {e}"]

    # 1. Check top-level fields
    for k in ["panel_id", "selection_date", "total_gauges", "gauges", "stratification_summary"]:
        if k not in data:
            errors.append(f"Missing required top-level key: {k}")

    gauges = data.get("gauges", [])
    total_gauges = data.get("total_gauges", 0)

    # 2. Check total gauge count (>= 50)
    if total_gauges < 50:
        errors.append(f"Total gauge count ({total_gauges}) is less than required minimum of 50")
    if len(gauges) != total_gauges:
        errors.append(f"Gauge array length ({len(gauges)}) does not match declared total ({total_gauges})")

    # 3. Check pilot panel retention (all 18 pilot gauges must be present)
    pilot_panel_file = CHUNK01_DIR / "pilot_panel.json"
    if pilot_panel_file.exists():
        with open(pilot_panel_file, "r", encoding="utf-8") as f:
            pilot_data = json.load(f)
        pilot_sites = {g["site_no"] for g in pilot_data.get("gauges", [])}
        full_sites = {g["site_no"] for g in gauges}
        missing_pilot = pilot_sites - full_sites
        if missing_pilot:
            errors.append(f"Pilot panel gauges missing from full panel: {sorted(missing_pilot)}")
    else:
        errors.append("Chunk 01 pilot_panel.json not found for retention cross-check")

    # 4. Check Ref / Non-Ref balance
    ref_count = sum(1 for g in gauges if g.get("gagesii_class") == "Ref")
    non_ref_count = sum(1 for g in gauges if g.get("gagesii_class") == "Non-Ref")

    if ref_count == 0:
        errors.append("No Reference basins found in full panel")
    if non_ref_count == 0:
        errors.append("No Non-Reference basins found in full panel")

    # 5. Check HUC regions (>= 10)
    huc_regions: Set[str] = {g.get("huc_region", "") for g in gauges if g.get("huc_region")}
    if len(huc_regions) < 10:
        errors.append(f"HUC regions count ({len(huc_regions)}) is less than required minimum of 10 ({sorted(huc_regions)})")

    # 6. Check required gauge fields
    required_gauge_fields = [
        "site_no", "station_name", "huc_region", "gagesii_class",
        "drainage_area_sqmi", "drainage_area_class", "koppen_climate",
        "snow_influenced", "in_pilot_panel", "record_start", "record_end",
        "selection_reason"
    ]
    for idx, g in enumerate(gauges):
        for field in required_gauge_fields:
            if field not in g:
                errors.append(f"Gauge #{idx} ({g.get('site_no', 'unknown')}) missing required field: '{field}'")

    # 7. Check stratification summary
    strat = data.get("stratification_summary", {})
    if not isinstance(strat, dict) or "huc_distribution" not in strat or "reference_distribution" not in strat:
        errors.append("stratification_summary is missing or malformed")

    return errors


def main() -> None:
    errors = validate_full_panel()
    if errors:
        logger.error(f"Full Gauge Panel Verification FAILED with {len(errors)} error(s):")
        for err in errors:
            logger.error(f"  - {err}")
        sys.exit(1)
    else:
        logger.info("Full Gauge Panel Verification PASSED.")
        sys.exit(0)


if __name__ == "__main__":
    main()
