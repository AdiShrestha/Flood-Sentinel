"""Verification script for NWM Retrospective Baseline Acquisition (C01-09).

Validates Parquet files, column structure, data manifest, provenance manifest,
and enforces Rev. 7 language discipline (no use of 'operational' in reference
to NWM Retrospective).
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

from source.utils.config import CHUNK01_DATA_DIR, CHUNK01_DIR, CHUNK01_MANIFESTS_DIR
from source.utils.logging_config import get_logger
from source.utils.manifest import (
    load_acquisition_provenance,
    load_data_manifest,
    validate_acquisition_provenance,
    validate_data_manifest,
)

logger = get_logger("verify_nwm_retro")

REQUIRED_COLUMNS = {"datetime", "site_no", "comid", "nwm_discharge_cms"}


def validate_nwm_retrospective_acquisition() -> List[str]:
    """Validate all C01-09 NWM Retrospective acquisition outputs."""
    errors: List[str] = []

    pilot_panel_path = CHUNK01_DIR / "pilot_panel.json"
    if not pilot_panel_path.exists():
        return [f"pilot_panel.json missing at {pilot_panel_path}"]

    with open(pilot_panel_path, "r", encoding="utf-8") as f:
        panel_data = json.load(f)

    gauges = panel_data.get("gauges", [])
    if not gauges:
        return ["pilot_panel.json contains no gauges"]

    nwm_dir = CHUNK01_DATA_DIR / "nwm_retro"
    if not nwm_dir.exists():
        return [f"NWM Retrospective data directory {nwm_dir} does not exist"]

    # 1. Verify Parquet files
    for g in gauges:
        site_no = g["site_no"]
        parquet_file = nwm_dir / site_no / "nwm_retro_daily.parquet"

        if not parquet_file.exists():
            errors.append(f"NWM Retrospective Parquet missing for site {site_no}: {parquet_file}")
            continue

        try:
            df = pd.read_parquet(parquet_file)
            missing_cols = REQUIRED_COLUMNS - set(df.columns)
            if missing_cols:
                errors.append(f"Site {site_no} Parquet missing required columns: {sorted(missing_cols)}")

            if len(df) == 0:
                errors.append(f"Site {site_no} NWM Retrospective Parquet is empty")

            if df["nwm_discharge_cms"].notna().sum() == 0:
                errors.append(f"Site {site_no} has 0 valid nwm_discharge_cms observations")

        except Exception as e:
            errors.append(f"Failed to read NWM Retrospective Parquet for site {site_no}: {e}")

    # 2. Validate data_manifest.json
    manifest_path = CHUNK01_MANIFESTS_DIR / "nwm_retro_data_manifest.json"
    if not manifest_path.exists():
        errors.append(f"Manifest missing: {manifest_path}")
    else:
        try:
            manifest = load_data_manifest(manifest_path)
            errors.extend(validate_data_manifest(manifest))

            pc = manifest.get("provenance_chain", {})
            for ch_name, ch_info in pc.items():
                if ch_info.get("undocumented_step") is not False:
                    errors.append(f"Channel '{ch_name}' in nwm_retro_data_manifest has undocumented_step != False")

        except Exception as e:
            errors.append(f"Failed to validate nwm_retro_data_manifest: {e}")

    # 3. Validate acquisition_provenance.json
    provenance_path = CHUNK01_MANIFESTS_DIR / "nwm_retro_acquisition_provenance.json"
    if not provenance_path.exists():
        errors.append(f"Provenance missing: {provenance_path}")
    else:
        try:
            prov = load_acquisition_provenance(provenance_path)
            errors.extend(validate_acquisition_provenance(prov))
        except Exception as e:
            errors.append(f"Failed to validate nwm_retro_acquisition_provenance: {e}")

    # 4. Enforce Rev. 7 language discipline: verify "operational" does NOT appear in manifest or provenance
    for p in [manifest_path, provenance_path]:
        if p.exists():
            content = p.read_text(encoding="utf-8").lower()
            if "operational" in content:
                errors.append(f"Rev. 7 Language Violation: forbidden word 'operational' found in {p.name}")

    return errors


def main() -> None:
    errors = validate_nwm_retrospective_acquisition()
    if errors:
        logger.error(f"NWM Retrospective Verification FAILED with {len(errors)} error(s):")
        for err in errors:
            logger.error(f"  - {err}")
        sys.exit(1)
    else:
        logger.info("NWM Retrospective Baseline Acquisition Verification PASSED.")
        sys.exit(0)


if __name__ == "__main__":
    main()
