"""Verification script for Full-Scale Static Basin Attribute Acquisition (C02-07 / FR-004).

Validates that static_basin_attributes.parquet exists with exactly 54 rows,
all KF-113 input attributes are non-null, A-003 GAGES-II vs NID cross-checks are logged,
and dataset and provenance manifests are intact.
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

logger = get_logger("verify_attributes_full")


def validate_attributes_full() -> List[str]:
    """Validate full-scale attributes acquisition deliverables."""
    errors: List[str] = []

    panel_file = CHUNK02_DIR / "full_panel.json"
    if not panel_file.exists():
        return [f"Full panel manifest missing at {panel_file}"]

    with open(panel_file, "r", encoding="utf-8") as f:
        panel_data = json.load(f)

    gauges = panel_data.get("gauges", [])
    expected_count = len(gauges)

    attr_file = CHUNK02_DATA_DIR / "attributes" / "static_basin_attributes.parquet"
    if not attr_file.exists():
        return [f"static_basin_attributes.parquet missing at {attr_file}"]

    try:
        df = pd.read_parquet(attr_file)
        if len(df) != expected_count:
            errors.append(f"Expected {expected_count} attribute rows, got {len(df)}")

        # Check required KF-113 estimator inputs
        kf113_required_cols = [
            "flow_length_ft", "slope_pct", "curve_number_cn",
            "drainage_area_sqkm", "mainstem_length_km"
        ]
        for col in kf113_required_cols:
            if col not in df.columns:
                errors.append(f"Missing required KF-113 attribute column: '{col}'")
            elif df[col].isna().any():
                errors.append(f"KF-113 attribute '{col}' contains NaN values")

        # Check A-003 agreement
        if "gagesii_nid_agreement" not in df.columns:
            errors.append("Missing 'gagesii_nid_agreement' column")
        else:
            agreement_rate = float(df["gagesii_nid_agreement"].mean())
            if agreement_rate < 0.90:
                errors.append(f"A-003 agreement rate ({agreement_rate:.2%}) below 90% threshold")

    except Exception as e:
        errors.append(f"Failed to read Parquet from {attr_file}: {e}")

    # Validate data manifest
    manifest_file = CHUNK02_MANIFESTS_DIR / "attributes_data_manifest.json"
    if not manifest_file.exists():
        errors.append(f"attributes_data_manifest.json missing at {manifest_file}")
    else:
        try:
            with open(manifest_file, "r", encoding="utf-8") as f:
                manifest_data = json.load(f)
            manifest_errors = validate_data_manifest(manifest_data)
            errors.extend([f"Manifest error: {e}" for e in manifest_errors])
        except Exception as e:
            errors.append(f"Failed to read data manifest: {e}")

    # Validate provenance manifest
    prov_file = CHUNK02_MANIFESTS_DIR / "attributes_acquisition_provenance.json"
    if not prov_file.exists():
        errors.append(f"attributes_acquisition_provenance.json missing at {prov_file}")
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
    errors = validate_attributes_full()
    if errors:
        logger.error(f"Full-Scale Static Basin Attribute Verification FAILED with {len(errors)} error(s):")
        for err in errors:
            logger.error(f"  - {err}")
        sys.exit(1)
    else:
        logger.info("Full-Scale Static Basin Attribute Verification PASSED.")
        sys.exit(0)


if __name__ == "__main__":
    main()
