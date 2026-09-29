"""Verification script for USGS Streamflow Acquisition (C01-03).

Validates Parquet files, column schemas, data manifest, and acquisition
provenance manifest for the pilot gauge panel.
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

from source.utils.config import CHUNK01_DATA_DIR, CHUNK01_DIR, CHUNK01_MANIFESTS_DIR
from source.utils.logging_config import get_logger
from source.utils.manifest import (
    load_acquisition_provenance,
    load_data_manifest,
    validate_acquisition_provenance,
    validate_data_manifest,
)

logger = get_logger("verify_usgs")

REQUIRED_COLUMNS = {"datetime", "site_no", "discharge_cfs", "gage_height_ft", "quality_flag"}


def validate_usgs_acquisition() -> List[str]:
    """Validate all C01-03 USGS acquisition outputs."""
    errors: List[str] = []

    pilot_panel_path = CHUNK01_DIR / "pilot_panel.json"
    if not pilot_panel_path.exists():
        return [f"pilot_panel.json missing at {pilot_panel_path}"]

    with open(pilot_panel_path, "r", encoding="utf-8") as f:
        panel_data = json.load(f)

    gauges = panel_data.get("gauges", [])
    if not gauges:
        return ["pilot_panel.json contains no gauges"]

    usgs_dir = CHUNK01_DATA_DIR / "usgs"
    if not usgs_dir.exists():
        return [f"USGS data directory {usgs_dir} does not exist"]

    # 1. Verify Parquet files and columns for every gauge
    for g in gauges:
        site_no = g["site_no"]
        parquet_file = usgs_dir / site_no / "daily_streamflow.parquet"

        if not parquet_file.exists():
            errors.append(f"Parquet file missing for site {site_no}: {parquet_file}")
            continue

        try:
            df = pd.read_parquet(parquet_file)
            missing_cols = REQUIRED_COLUMNS - set(df.columns)
            if missing_cols:
                errors.append(f"Site {site_no} Parquet missing required columns: {sorted(missing_cols)}")

            if len(df) == 0:
                errors.append(f"Site {site_no} Parquet is empty (0 rows)")

            # Check datetime format and sorting
            if not pd.to_datetime(df["datetime"], errors="coerce").notna().all():
                errors.append(f"Site {site_no} has invalid datetime values")

            # Check that discharge has at least some valid non-nan numbers
            if df["discharge_cfs"].notna().sum() == 0:
                errors.append(f"Site {site_no} has 0 valid discharge observations")

        except Exception as e:
            errors.append(f"Failed to read Parquet for site {site_no}: {e}")

    # 2. Validate data_manifest.json
    manifest_path = CHUNK01_MANIFESTS_DIR / "usgs_data_manifest.json"
    if not manifest_path.exists():
        errors.append(f"Manifest missing: {manifest_path}")
    else:
        try:
            manifest = load_data_manifest(manifest_path)
            schema_errors = validate_data_manifest(manifest)
            errors.extend(schema_errors)

            # Check provenance chain has no undocumented steps
            pc = manifest.get("provenance_chain", {})
            for ch_name, ch_info in pc.items():
                if ch_info.get("undocumented_step") is not False:
                    errors.append(f"Channel '{ch_name}' has undocumented_step != False")

        except Exception as e:
            errors.append(f"Failed to validate data_manifest: {e}")

    # 3. Validate acquisition_provenance.json
    provenance_path = CHUNK01_MANIFESTS_DIR / "usgs_acquisition_provenance.json"
    if not provenance_path.exists():
        errors.append(f"Provenance manifest missing: {provenance_path}")
    else:
        try:
            prov = load_acquisition_provenance(provenance_path)
            prov_errors = validate_acquisition_provenance(prov)
            errors.extend(prov_errors)

            # Check HTTP 200
            status_codes = prov.get("http_status_codes", [])
            if 200 not in status_codes or any(sc != 200 for sc in status_codes):
                errors.append(f"Unexpected HTTP status codes in provenance: {status_codes}")

            file_list = prov.get("downloaded_file_manifest", [])
            if len(file_list) < len(gauges):
                errors.append(f"Downloaded file manifest count ({len(file_list)}) < gauge count ({len(gauges)})")

        except Exception as e:
            errors.append(f"Failed to validate acquisition_provenance: {e}")

    return errors


def main() -> None:
    errors = validate_usgs_acquisition()
    if errors:
        logger.error(f"USGS Acquisition Verification FAILED with {len(errors)} error(s):")
        for err in errors:
            logger.error(f"  - {err}")
        sys.exit(1)
    else:
        logger.info("USGS Acquisition Verification PASSED for all pilot panel streamgages.")
        sys.exit(0)


if __name__ == "__main__":
    main()
