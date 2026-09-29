"""Verification script for Static Basin Attributes Acquisition (C01-06).

Validates basin_attributes.parquet, required columns, GAGES-II/NID consistency,
data manifest, and acquisition provenance manifest.
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

logger = get_logger("verify_attributes")

REQUIRED_COLUMNS = {
    "site_no",
    "station_name",
    "huc_region",
    "drainage_area_sqmi",
    "gagesii_class",
    "slope_mean",
    "nid_regulation",
    "gagesii_nid_agreement",
}


def validate_attributes_acquisition() -> List[str]:
    """Validate all C01-06 static attributes acquisition outputs."""
    errors: List[str] = []

    pilot_panel_path = CHUNK01_DIR / "pilot_panel.json"
    if not pilot_panel_path.exists():
        return [f"pilot_panel.json missing at {pilot_panel_path}"]

    with open(pilot_panel_path, "r", encoding="utf-8") as f:
        panel_data = json.load(f)

    expected_gauges = {g["site_no"] for g in panel_data.get("gauges", [])}
    if not expected_gauges:
        return ["pilot_panel.json contains no gauges"]

    parquet_file = CHUNK01_DATA_DIR / "attributes" / "basin_attributes.parquet"
    if not parquet_file.exists():
        return [f"basin_attributes.parquet missing at {parquet_file}"]

    # 1. Validate DataFrame structure and columns
    try:
        df = pd.read_parquet(parquet_file)
        if len(df) != len(expected_gauges):
            errors.append(f"Expected {len(expected_gauges)} rows in basin_attributes.parquet, got {len(df)}")

        missing_cols = REQUIRED_COLUMNS - set(df.columns)
        if missing_cols:
            errors.append(f"basin_attributes.parquet missing required columns: {sorted(missing_cols)}")

        actual_sites = set(df["site_no"].unique())
        if actual_sites != expected_gauges:
            errors.append(f"Site mismatch: missing {expected_gauges - actual_sites}, unexpected {actual_sites - expected_gauges}")

        # Check for all-NaN rows
        for idx, row in df.iterrows():
            if row.isna().all():
                errors.append(f"Row {idx} is entirely NaN")

        # Check drainage area positive
        if (df["drainage_area_sqmi"] <= 0).any():
            errors.append("Non-positive drainage_area_sqmi found")

        # Check GAGES-II classes
        invalid_classes = set(df["gagesii_class"].unique()) - {"Ref", "Non-Ref"}
        if invalid_classes:
            errors.append(f"Invalid gagesii_class values: {invalid_classes}")

    except Exception as e:
        errors.append(f"Failed to read basin_attributes.parquet: {e}")

    # 2. Validate data_manifest.json
    manifest_path = CHUNK01_MANIFESTS_DIR / "attributes_data_manifest.json"
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
            errors.append(f"Failed to validate attributes_data_manifest: {e}")

    # 3. Validate acquisition_provenance.json
    provenance_path = CHUNK01_MANIFESTS_DIR / "attributes_acquisition_provenance.json"
    if not provenance_path.exists():
        errors.append(f"Provenance missing: {provenance_path}")
    else:
        try:
            prov = load_acquisition_provenance(provenance_path)
            errors.extend(validate_acquisition_provenance(prov))

            status_codes = prov.get("http_status_codes", [])
            if 200 not in status_codes or any(sc != 200 for sc in status_codes):
                errors.append(f"Unexpected HTTP status codes in attributes provenance: {status_codes}")

        except Exception as e:
            errors.append(f"Failed to validate attributes_acquisition_provenance: {e}")

    return errors


def main() -> None:
    errors = validate_attributes_acquisition()
    if errors:
        logger.error(f"Basin Attributes Verification FAILED with {len(errors)} error(s):")
        for err in errors:
            logger.error(f"  - {err}")
        sys.exit(1)
    else:
        logger.info("Basin Attributes Verification PASSED for all pilot panel streamgages.")
        sys.exit(0)


if __name__ == "__main__":
    main()
