"""Verification script for Flood Stage Threshold Acquisition (C01-07).

Validates flood_thresholds.json, stage ordering constraints, vintage tagging,
data manifest, and acquisition provenance manifest.
"""

import json
import sys
from pathlib import Path
from typing import Any, Dict, List

# Add project root to sys.path if running as standalone script
_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from source.utils.config import CHUNK01_DATA_DIR, CHUNK01_DIR, CHUNK01_MANIFESTS_DIR
from source.utils.logging_config import get_logger
from source.utils.manifest import (
    load_acquisition_provenance,
    load_data_manifest,
    validate_acquisition_provenance,
    validate_data_manifest,
)

logger = get_logger("verify_thresholds")


def validate_thresholds_acquisition() -> List[str]:
    """Validate all C01-07 flood stage threshold acquisition outputs."""
    errors: List[str] = []

    pilot_panel_path = CHUNK01_DIR / "pilot_panel.json"
    if not pilot_panel_path.exists():
        return [f"pilot_panel.json missing at {pilot_panel_path}"]

    with open(pilot_panel_path, "r", encoding="utf-8") as f:
        panel_data = json.load(f)

    expected_gauges = {g["site_no"] for g in panel_data.get("gauges", [])}
    if not expected_gauges:
        return ["pilot_panel.json contains no gauges"]

    json_file = CHUNK01_DATA_DIR / "thresholds" / "flood_thresholds.json"
    if not json_file.exists():
        return [f"flood_thresholds.json missing at {json_file}"]

    # 1. Validate threshold JSON content
    try:
        with open(json_file, "r", encoding="utf-8") as f:
            records = json.load(f)

        if not isinstance(records, list):
            errors.append("flood_thresholds.json must contain a list of records")
            return errors

        if len(records) != len(expected_gauges):
            errors.append(f"Expected {len(expected_gauges)} records, got {len(records)}")

        actual_sites = {r.get("site_no") for r in records}
        if actual_sites != expected_gauges:
            errors.append(f"Site mismatch in thresholds: missing {expected_gauges - actual_sites}")

        for r in records:
            s_id = r.get("site_no")
            has_thresh = r.get("nwps_thresholds_available", False)

            if has_thresh:
                if not r.get("threshold_vintage"):
                    errors.append(f"Site {s_id} has thresholds but is missing threshold_vintage")

                # Validate ordering: action <= minor <= moderate <= major
                act = r.get("action_stage_ft")
                minr = r.get("minor_stage_ft")
                mod = r.get("moderate_stage_ft")
                maj = r.get("major_stage_ft")

                vals = [("action", act), ("minor", minr), ("moderate", mod), ("major", maj)]
                valid_vals = [(name, v) for name, v in vals if v is not None]

                for i in range(len(valid_vals) - 1):
                    n1, v1 = valid_vals[i]
                    n2, v2 = valid_vals[i + 1]
                    if v1 > v2:
                        errors.append(f"Site {s_id} violated threshold ordering: {n1} ({v1}) > {n2} ({v2})")

    except Exception as e:
        errors.append(f"Failed to read/parse flood_thresholds.json: {e}")

    # 2. Validate data_manifest.json
    manifest_path = CHUNK01_MANIFESTS_DIR / "thresholds_data_manifest.json"
    if not manifest_path.exists():
        errors.append(f"Manifest missing: {manifest_path}")
    else:
        try:
            manifest = load_data_manifest(manifest_path)
            errors.extend(validate_data_manifest(manifest))

            pc = manifest.get("provenance_chain", {})
            for ch_name, ch_info in pc.items():
                if ch_info.get("undocumented_step") is not False:
                    errors.append(f"Channel '{ch_name}' has undocumented_step != False")

        except Exception as e:
            errors.append(f"Failed to validate thresholds_data_manifest: {e}")

    # 3. Validate acquisition_provenance.json
    provenance_path = CHUNK01_MANIFESTS_DIR / "thresholds_acquisition_provenance.json"
    if not provenance_path.exists():
        errors.append(f"Provenance missing: {provenance_path}")
    else:
        try:
            prov = load_acquisition_provenance(provenance_path)
            errors.extend(validate_acquisition_provenance(prov))

            status_codes = prov.get("http_status_codes", [])
            if 200 not in status_codes or any(sc != 200 for sc in status_codes):
                errors.append(f"Unexpected HTTP status codes in thresholds provenance: {status_codes}")

        except Exception as e:
            errors.append(f"Failed to validate thresholds_acquisition_provenance: {e}")

    return errors


def main() -> None:
    errors = validate_thresholds_acquisition()
    if errors:
        logger.error(f"Thresholds Acquisition Verification FAILED with {len(errors)} error(s):")
        for err in errors:
            logger.error(f"  - {err}")
        sys.exit(1)
    else:
        logger.info("Thresholds Acquisition Verification PASSED for all pilot panel streamgages.")
        sys.exit(0)


if __name__ == "__main__":
    main()
