"""Verification script for Snow Water Equivalent Acquisition (C01-05).

Validates SNODAS Parquet files, temporal limits (no pre-Oct-2003 data),
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

logger = get_logger("verify_snodas")

REQUIRED_COLUMNS = {"date", "site_no", "swe_mm", "snodas_applicable"}


def validate_snodas_acquisition() -> List[str]:
    """Validate all C01-05 SNODAS acquisition outputs."""
    errors: List[str] = []

    pilot_panel_path = CHUNK01_DIR / "pilot_panel.json"
    if not pilot_panel_path.exists():
        return [f"pilot_panel.json missing at {pilot_panel_path}"]

    with open(pilot_panel_path, "r", encoding="utf-8") as f:
        panel_data = json.load(f)

    gauges = panel_data.get("gauges", [])
    if not gauges:
        return ["pilot_panel.json contains no gauges"]

    snodas_dir = CHUNK01_DATA_DIR / "snodas"
    if not snodas_dir.exists():
        return [f"SNODAS data directory {snodas_dir} does not exist"]

    # 1. Verify Parquet files for all pilot gauges
    for g in gauges:
        site_no = g["site_no"]
        parquet_file = snodas_dir / site_no / "snodas_daily.parquet"

        if not parquet_file.exists():
            errors.append(f"SNODAS Parquet missing for site {site_no}: {parquet_file}")
            continue

        try:
            df = pd.read_parquet(parquet_file)
            missing_cols = REQUIRED_COLUMNS - set(df.columns)
            if missing_cols:
                errors.append(f"Site {site_no} Parquet missing required columns: {sorted(missing_cols)}")

            if len(df) == 0:
                errors.append(f"Site {site_no} SNODAS Parquet is empty")

            # Check that no date is before 2003-10-01 (INV-008 / C54: pre-2003 data does not exist)
            min_date = df["date"].min()
            if min_date < "2003-10-01":
                errors.append(f"Site {site_no} contains invalid pre-October-2003 data: min_date={min_date}")

            # Check snow-applicable vs non-applicable
            is_applicable = df["snodas_applicable"].iloc[0]
            if is_applicable:
                if df["swe_mm"].notna().sum() == 0:
                    errors.append(f"Snow-influenced site {site_no} has 0 valid SWE values")
            else:
                if df["swe_mm"].notna().sum() > 0:
                    errors.append(f"Non-snow-influenced site {site_no} unexpectedly has non-NaN SWE values")

        except Exception as e:
            errors.append(f"Failed to read SNODAS Parquet for site {site_no}: {e}")

    # 2. Validate data_manifest.json
    manifest_path = CHUNK01_MANIFESTS_DIR / "snodas_data_manifest.json"
    if not manifest_path.exists():
        errors.append(f"Manifest missing: {manifest_path}")
    else:
        try:
            manifest = load_data_manifest(manifest_path)
            errors.extend(validate_data_manifest(manifest))

            # Confirm temporal range starts at 2003-10-01
            tr = manifest.get("temporal_range", {})
            if tr.get("start") < "2003-10-01":
                errors.append(f"Manifest temporal_range start ({tr.get('start')}) precedes SNODAS inception (2003-10-01)")

            pc = manifest.get("provenance_chain", {})
            for ch_name, ch_info in pc.items():
                if ch_info.get("undocumented_step") is not False:
                    errors.append(f"Channel '{ch_name}' in snodas_data_manifest has undocumented_step != False")

        except Exception as e:
            errors.append(f"Failed to validate snodas_data_manifest: {e}")

    # 3. Validate acquisition_provenance.json
    provenance_path = CHUNK01_MANIFESTS_DIR / "snodas_acquisition_provenance.json"
    if not provenance_path.exists():
        errors.append(f"Provenance missing: {provenance_path}")
    else:
        try:
            prov = load_acquisition_provenance(provenance_path)
            errors.extend(validate_acquisition_provenance(prov))

            status_codes = prov.get("http_status_codes", [])
            if 200 not in status_codes or any(sc != 200 for sc in status_codes):
                errors.append(f"Unexpected HTTP status codes in SNODAS provenance: {status_codes}")

        except Exception as e:
            errors.append(f"Failed to validate snodas_acquisition_provenance: {e}")

    return errors


def main() -> None:
    errors = validate_snodas_acquisition()
    if errors:
        logger.error(f"SNODAS Acquisition Verification FAILED with {len(errors)} error(s):")
        for err in errors:
            logger.error(f"  - {err}")
        sys.exit(1)
    else:
        logger.info("SNODAS Acquisition Verification PASSED for all pilot panel streamgages.")
        sys.exit(0)


if __name__ == "__main__":
    main()
