"""Verification script for NWM Operational-Forecast Archive Pre-Check (C01-10).

Validates nwm_op_precheck_results.json structure, required candidate checks,
and conclusion formatting.
"""

import json
import sys
from pathlib import Path
from typing import List

# Add project root to sys.path if running as standalone script
_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from source.utils.config import CHUNK01_DIR
from source.utils.logging_config import get_logger

logger = get_logger("verify_nwm_op_precheck")


def validate_nwm_op_precheck() -> List[str]:
    """Validate all C01-10 pre-check deliverables."""
    errors: List[str] = []

    results_file = CHUNK01_DIR / "reports" / "C01-10" / "nwm_op_precheck_results.json"
    if not results_file.exists():
        return [f"nwm_op_precheck_results.json not found at {results_file}"]

    try:
        with open(results_file, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception as e:
        return [f"Failed to parse JSON from {results_file}: {e}"]

    # Required top-level keys
    for k in ["precheck_date", "archives_checked", "qualifying_archive_found", "conclusion"]:
        if k not in data:
            errors.append(f"Missing required top-level key: {k}")

    if not isinstance(data.get("qualifying_archive_found"), bool):
        errors.append("qualifying_archive_found must be a boolean")

    if not isinstance(data.get("conclusion"), str) or len(data.get("conclusion", "")) < 10:
        errors.append("conclusion must be a non-empty string with explanation")

    archives = data.get("archives_checked", [])
    if not isinstance(archives, list) or len(archives) < 2:
        errors.append("archives_checked must be a list with at least 2 candidate archives")

    archive_names = {a.get("archive_name", "") for a in archives}
    if not any("NOMADS" in n for n in archive_names):
        errors.append("NOMADS archive was not checked in archives_checked")
    if not any("AWS" in n for n in archive_names):
        errors.append("AWS archive was not checked in archives_checked")

    return errors


def main() -> None:
    errors = validate_nwm_op_precheck()
    if errors:
        logger.error(f"NWM Operational Pre-Check Verification FAILED with {len(errors)} error(s):")
        for err in errors:
            logger.error(f"  - {err}")
        sys.exit(1)
    else:
        logger.info("NWM Operational Pre-Check Verification PASSED.")
        sys.exit(0)


if __name__ == "__main__":
    main()
