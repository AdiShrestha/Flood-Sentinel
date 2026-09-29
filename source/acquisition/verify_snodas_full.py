"""Verification script for Full-Scale SNODAS SWE Acquisition (C02-06 / FR-003).

Validates that daily Snow Water Equivalent Parquet files exist for all
54 full-panel streamgages, records span 2003-10-01 to 2023-12-31, non-snow basins
are correctly flagged, no pre-October-2003 observations exist, and manifests are valid.
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

logger = get_logger("verify_snodas_full")


def validate_snodas_full() -> List[str]:
    """Validate full-scale SNODAS acquisition deliverables."""
    errors: List[str] = []

    panel_file = CHUNK02_DIR / "full_panel.json"
    if not panel_file.exists():
        return [f"Full panel manifest missing at {panel_file}"]

    with open(panel_file, "r", encoding="utf-8") as f:
        panel_data = json.load(f)

    gauges = panel_data.get("gauges", [])
    snodas_dir = CHUNK02_DATA_DIR / "snodas"

    if not snodas_dir.exists():
        return [f"SNODAS data directory does not exist: {snodas_dir}"]

    expected_cols = {"date", "site_no", "swe_mm", "snodas_applicable"}
    valid_stations = 0

    for g in gauges:
        site_no = g["site_no"]
        is_snow = g.get("snow_influenced", False)
        parquet_file = snodas_dir / site_no / "snodas_daily.parquet"

        if not parquet_file.exists():
            errors.append(f"Missing Parquet file for site {site_no} at {parquet_file}")
            continue

        try:
            df = pd.read_parquet(parquet_file)
            if len(df) != 7397:
                errors.append(f"Site {site_no} expected 7397 daily records, got {len(df)}")

            missing_cols = expected_cols - set(df.columns)
            if missing_cols:
                errors.append(f"Site {site_no} missing columns: {missing_cols}")

            if df["date"].min() != "2003-10-01" or df["date"].max() != "2023-12-31":
                errors.append(f"Site {site_no} date span mismatch: {df['date'].min()} to {df['date'].max()}")

            if not is_snow:
                if not (df["snodas_applicable"] == False).all():
                    errors.append(f"Snow-free site {site_no} has snodas_applicable == True")
                if not (df["swe_mm"].isna() | (df["swe_mm"] == 0.0)).all():
                    errors.append(f"Snow-free site {site_no} has non-zero non-null swe_mm")

            valid_stations += 1
        except Exception as e:
            errors.append(f"Failed to read Parquet for site {site_no}: {e}")

    # Check minimum 90% stations present
    min_required = int(len(gauges) * 0.9)
    if valid_stations < min_required:
        errors.append(f"Valid stations count ({valid_stations}) below minimum 90% threshold ({min_required}/{len(gauges)})")

    # Validate data manifest
    manifest_file = CHUNK02_MANIFESTS_DIR / "snodas_data_manifest.json"
    if not manifest_file.exists():
        errors.append(f"snodas_data_manifest.json missing at {manifest_file}")
    else:
        try:
            with open(manifest_file, "r", encoding="utf-8") as f:
                manifest_data = json.load(f)
            manifest_errors = validate_data_manifest(manifest_data)
            errors.extend([f"Manifest error: {e}" for e in manifest_errors])
        except Exception as e:
            errors.append(f"Failed to read data manifest: {e}")

    # Validate provenance manifest
    prov_file = CHUNK02_MANIFESTS_DIR / "snodas_acquisition_provenance.json"
    if not prov_file.exists():
        errors.append(f"snodas_acquisition_provenance.json missing at {prov_file}")
    else:
        try:
            with open(prov_file, "r", encoding="utf-8") as f:
                p_data = json.load(f)
            p_errors = validate_acquisition_provenance(p_data)
            errors.extend([f"Provenance error: {e}" for e in p_errors])
            dl_manifest = p_data.get("downloaded_file_manifest", [])
            if len(dl_manifest) < len(gauges):
                errors.append(f"Provenance downloaded_file_manifest ({len(dl_manifest)}) fewer than gauges ({len(gauges)})")
        except Exception as e:
            errors.append(f"Failed to parse provenance manifest: {e}")

    return errors


def main() -> None:
    errors = validate_snodas_full()
    if errors:
        logger.error(f"Full-Scale SNODAS Acquisition Verification FAILED with {len(errors)} error(s):")
        for err in errors:
            logger.error(f"  - {err}")
        sys.exit(1)
    else:
        logger.info("Full-Scale SNODAS Acquisition Verification PASSED.")
        sys.exit(0)


if __name__ == "__main__":
    main()
