"""Verification script for Response-Time Eligibility Tagging (C02-11 / INV-025 / KF-113).

Validates that eligibility_tags.json exists with all 54 gauges classified,
computation date respects freeze discipline, no negative response times exist,
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

logger = get_logger("verify_response_time")


def validate_response_time() -> List[str]:
    """Validate full-scale response time deliverables."""
    errors: List[str] = []

    panel_file = CHUNK02_DIR / "full_panel.json"
    if not panel_file.exists():
        return [f"Full panel manifest missing at {panel_file}"]

    with open(panel_file, "r", encoding="utf-8") as f:
        panel_data = json.load(f)

    gauges = panel_data.get("gauges", [])
    expected_site_nos = {g["site_no"] for g in gauges}

    json_path = CHUNK02_DATA_DIR / "response_time" / "eligibility_tags.json"
    parquet_path = CHUNK02_DATA_DIR / "response_time" / "eligibility_tags.parquet"

    if not json_path.exists():
        return [f"eligibility_tags.json missing at {json_path}"]
    if not parquet_path.exists():
        return [f"eligibility_tags.parquet missing at {parquet_path}"]

    try:
        with open(json_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        decl_date = data.get("kf113_declaration_date")
        comp_date = data.get("computation_date")

        if not decl_date or not comp_date:
            errors.append("Missing kf113_declaration_date or computation_date in eligibility_tags.json")
        elif comp_date < decl_date:
            errors.append(f"Freeze violation: computation date ({comp_date}) is before KF-113 declaration date ({decl_date})")

        gauge_entries = data.get("gauges", [])
        if len(gauge_entries) != len(gauges):
            errors.append(f"Expected {len(gauges)} gauge entries, got {len(gauge_entries)}")

        valid_statuses = {"eligible", "ineligible", "undetermined"}
        for g in gauge_entries:
            s_no = g.get("site_no")
            status = g.get("eligibility_status")
            t_val = g.get("T_response_proxy_hours")

            if status not in valid_statuses:
                errors.append(f"Site {s_no} has invalid status '{status}'")

            if t_val is not None and t_val < 0:
                errors.append(f"Site {s_no} has negative response time: {t_val} hours")

            if status == "eligible" and (t_val is None or t_val < 24.0):
                errors.append(f"Site {s_no} marked eligible but T_response_proxy_hours is {t_val}")
            elif status == "ineligible" and (t_val is None or t_val >= 24.0):
                errors.append(f"Site {s_no} marked ineligible but T_response_proxy_hours is {t_val}")

        summary = data.get("summary", {})
        logger.info(
            f"Verified Summary: {summary.get('eligible_count')} Eligible, "
            f"{summary.get('ineligible_count')} Ineligible, {summary.get('undetermined_count')} Undetermined."
        )

    except Exception as e:
        errors.append(f"Failed to parse eligibility tags JSON: {e}")

    # Validate data manifest
    manifest_file = CHUNK02_MANIFESTS_DIR / "response_time_data_manifest.json"
    if not manifest_file.exists():
        errors.append(f"response_time_data_manifest.json missing at {manifest_file}")
    else:
        try:
            with open(manifest_file, "r", encoding="utf-8") as f:
                manifest_data = json.load(f)
            manifest_errors = validate_data_manifest(manifest_data)
            errors.extend([f"Manifest error: {e}" for e in manifest_errors])
        except Exception as e:
            errors.append(f"Failed to read data manifest: {e}")

    # Validate provenance manifest
    prov_file = CHUNK02_MANIFESTS_DIR / "response_time_acquisition_provenance.json"
    if not prov_file.exists():
        errors.append(f"response_time_acquisition_provenance.json missing at {prov_file}")
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
    errors = validate_response_time()
    if errors:
        logger.error(f"Response-Time Eligibility Verification FAILED with {len(errors)} error(s):")
        for err in errors:
            logger.error(f"  - {err}")
        sys.exit(1)
    else:
        logger.info("Response-Time Eligibility Verification PASSED.")
        sys.exit(0)


if __name__ == "__main__":
    main()
