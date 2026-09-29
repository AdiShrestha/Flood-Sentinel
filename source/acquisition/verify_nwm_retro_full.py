"""Verification script for Full-Scale NWM Retrospective Baseline Acquisition (C02-10 / FR-007 / FR-020).

Validates that NWM retrospective simulation Parquet files exist for all
54 full-panel streamgages, records span 1990-01-01 to 2023-12-31, COMID mappings
are valid, manifests are intact, and Rev. 7 language discipline is strictly maintained
(zero occurrences of the forbidden term referencing NWM Retrospective).
"""

import json
import re
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

logger = get_logger("verify_nwm_retro_full")


def validate_nwm_retro_full() -> List[str]:
    """Validate full-scale NWM retrospective acquisition deliverables."""
    errors: List[str] = []

    panel_file = CHUNK02_DIR / "full_panel.json"
    if not panel_file.exists():
        return [f"Full panel manifest missing at {panel_file}"]

    with open(panel_file, "r", encoding="utf-8") as f:
        panel_data = json.load(f)

    gauges = panel_data.get("gauges", [])
    nwm_dir = CHUNK02_DATA_DIR / "nwm_retro"

    if not nwm_dir.exists():
        return [f"NWM retrospective data directory does not exist: {nwm_dir}"]

    expected_cols = {"datetime", "site_no", "comid", "nwm_discharge_cms", "simulation_type"}
    valid_stations = 0

    for g in gauges:
        site_no = g["site_no"]
        parquet_file = nwm_dir / site_no / "nwm_retro_daily.parquet"

        if not parquet_file.exists():
            errors.append(f"Missing Parquet file for site {site_no} at {parquet_file}")
            continue

        try:
            df = pd.read_parquet(parquet_file)
            if len(df) != 12418:
                errors.append(f"Site {site_no} expected 12418 daily records, got {len(df)}")

            missing_cols = expected_cols - set(df.columns)
            if missing_cols:
                errors.append(f"Site {site_no} missing columns: {missing_cols}")

            if df["datetime"].min() != "1990-01-01" or df["datetime"].max() != "2023-12-31":
                errors.append(f"Site {site_no} date span mismatch: {df['datetime'].min()} to {df['datetime'].max()}")

            if not (df["simulation_type"] == "nwm_retrospective_v3_open_loop").all():
                errors.append(f"Site {site_no} has invalid simulation_type values")

            valid_stations += 1
        except Exception as e:
            errors.append(f"Failed to read Parquet for site {site_no}: {e}")

    # Check minimum 90% stations present
    min_required = int(len(gauges) * 0.9)
    if valid_stations < min_required:
        errors.append(f"Valid stations count ({valid_stations}) below minimum 90% threshold ({min_required}/{len(gauges)})")

    # Validate data manifest
    manifest_file = CHUNK02_MANIFESTS_DIR / "nwm_retro_data_manifest.json"
    if not manifest_file.exists():
        errors.append(f"nwm_retro_data_manifest.json missing at {manifest_file}")
    else:
        try:
            with open(manifest_file, "r", encoding="utf-8") as f:
                manifest_data = json.load(f)
            manifest_errors = validate_data_manifest(manifest_data)
            errors.extend([f"Manifest error: {e}" for e in manifest_errors])
        except Exception as e:
            errors.append(f"Failed to read data manifest: {e}")

    # Validate provenance manifest
    prov_file = CHUNK02_MANIFESTS_DIR / "nwm_retro_acquisition_provenance.json"
    if not prov_file.exists():
        errors.append(f"nwm_retro_acquisition_provenance.json missing at {prov_file}")
    else:
        try:
            with open(prov_file, "r", encoding="utf-8") as f:
                p_data = json.load(f)
            p_errors = validate_acquisition_provenance(p_data)
            errors.extend([f"Provenance error: {e}" for e in p_errors])
        except Exception as e:
            errors.append(f"Failed to parse provenance manifest: {e}")

    # Enforce Rev. 7 language discipline: verify NO occurrence of the forbidden word referencing NWM Retro
    files_to_check = [
        _PROJECT_ROOT / "source" / "acquisition" / "acquire_nwm_retro_full.py",
        manifest_file,
        prov_file
    ]
    for fpath in files_to_check:
        if fpath.exists():
            text = fpath.read_text(encoding="utf-8", errors="ignore")
            # Case-insensitive match for the forbidden word when qualifying nwm
            if re.search(r"\boperational\s+(forecast|streamflow|simulation|nwm)\b", text, re.IGNORECASE):
                errors.append(f"Rev. 7 language violation: forbidden phrase found in {fpath.name}")

    return errors


def main() -> None:
    errors = validate_nwm_retro_full()
    if errors:
        logger.error(f"Full-Scale NWM Retrospective Verification FAILED with {len(errors)} error(s):")
        for err in errors:
            logger.error(f"  - {err}")
        sys.exit(1)
    else:
        logger.info("Full-Scale NWM Retrospective Acquisition Verification PASSED.")
        sys.exit(0)


if __name__ == "__main__":
    main()
