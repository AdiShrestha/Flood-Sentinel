"""Verification script for gridMET Meteorological Forcing Acquisition (C01-04).

Validates Parquet files, column structure, vintage tagging, data manifest,
and acquisition provenance for the pilot gauge panel.
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

logger = get_logger("verify_gridmet")

REQUIRED_COLUMNS = {"date", "site_no", "precipitation_mm", "tmin_c", "tmax_c", "vintage_id"}
VALID_VINTAGES = {"pre_nrt_reanalysis_only", "nrt_proxy_available"}


def validate_gridmet_acquisition() -> List[str]:
    """Validate all C01-04 gridMET acquisition outputs."""
    errors: List[str] = []

    pilot_panel_path = CHUNK01_DIR / "pilot_panel.json"
    if not pilot_panel_path.exists():
        return [f"pilot_panel.json missing at {pilot_panel_path}"]

    with open(pilot_panel_path, "r", encoding="utf-8") as f:
        panel_data = json.load(f)

    gauges = panel_data.get("gauges", [])
    if not gauges:
        return ["pilot_panel.json contains no gauges"]

    gridmet_dir = CHUNK01_DATA_DIR / "gridmet"
    if not gridmet_dir.exists():
        return [f"gridMET data directory {gridmet_dir} does not exist"]

    # 1. Verify Parquet files for each site
    for g in gauges:
        site_no = g["site_no"]
        parquet_file = gridmet_dir / site_no / "gridmet_daily.parquet"

        if not parquet_file.exists():
            errors.append(f"gridMET Parquet file missing for site {site_no}: {parquet_file}")
            continue

        try:
            df = pd.read_parquet(parquet_file)
            missing_cols = REQUIRED_COLUMNS - set(df.columns)
            if missing_cols:
                errors.append(f"Site {site_no} Parquet missing columns: {sorted(missing_cols)}")

            if len(df) == 0:
                errors.append(f"Site {site_no} Parquet is empty")

            # Check no all-NaN columns
            for col in ["precipitation_mm", "tmin_c", "tmax_c"]:
                if col in df and df[col].notna().sum() == 0:
                    errors.append(f"Site {site_no} column '{col}' is all-NaN")

            # Check vintage_id validity
            if "vintage_id" in df:
                invalid_vintages = set(df["vintage_id"].unique()) - VALID_VINTAGES
                if invalid_vintages:
                    errors.append(f"Site {site_no} has invalid vintage_id values: {invalid_vintages}")

                # Check vintage transition at 2013-01-01
                pre_2013_mask = df["date"] < "2013-01-01"
                post_2013_mask = df["date"] >= "2013-01-01"

                if not (df.loc[pre_2013_mask, "vintage_id"] == "pre_nrt_reanalysis_only").all():
                    errors.append(f"Site {site_no} has non-'pre_nrt_reanalysis_only' entries before 2013-01-01")

                if not (df.loc[post_2013_mask, "vintage_id"] == "nrt_proxy_available").all():
                    errors.append(f"Site {site_no} has non-'nrt_proxy_available' entries on/after 2013-01-01")

        except Exception as e:
            errors.append(f"Failed to read gridMET Parquet for site {site_no}: {e}")

    # 2. Validate data_manifest.json
    manifest_path = CHUNK01_MANIFESTS_DIR / "gridmet_data_manifest.json"
    if not manifest_path.exists():
        errors.append(f"Manifest missing: {manifest_path}")
    else:
        try:
            manifest = load_data_manifest(manifest_path)
            errors.extend(validate_data_manifest(manifest))

            pc = manifest.get("provenance_chain", {})
            for ch_name, ch_info in pc.items():
                if ch_info.get("undocumented_step") is not False:
                    errors.append(f"Channel '{ch_name}' in gridmet_data_manifest has undocumented_step != False")

        except Exception as e:
            errors.append(f"Failed to validate gridmet_data_manifest: {e}")

    # 3. Validate acquisition_provenance.json
    provenance_path = CHUNK01_MANIFESTS_DIR / "gridmet_acquisition_provenance.json"
    if not provenance_path.exists():
        errors.append(f"Provenance missing: {provenance_path}")
    else:
        try:
            prov = load_acquisition_provenance(provenance_path)
            errors.extend(validate_acquisition_provenance(prov))

            status_codes = prov.get("http_status_codes", [])
            if 200 not in status_codes or any(sc != 200 for sc in status_codes):
                errors.append(f"Unexpected HTTP status codes in gridMET provenance: {status_codes}")

        except Exception as e:
            errors.append(f"Failed to validate gridmet_acquisition_provenance: {e}")

    return errors


def main() -> None:
    errors = validate_gridmet_acquisition()
    if errors:
        logger.error(f"gridMET Acquisition Verification FAILED with {len(errors)} error(s):")
        for err in errors:
            logger.error(f"  - {err}")
        sys.exit(1)
    else:
        logger.info("gridMET Acquisition Verification PASSED for all pilot panel streamgages.")
        sys.exit(0)


if __name__ == "__main__":
    main()
