"""Recompute Declaration: Independent Second Implementation of Provenance Chain Check (C01-11).

Provides an entirely independent verification of Check 5 (Provenance Chain Validation)
per INV-018 and factory_spec.md. Validates that every channel in every manifest
possesses zero undocumented steps without sharing code with reality_gate.py.
"""

import json
import sys
from pathlib import Path
from typing import Dict, List, Tuple

# Add project root to sys.path if running as standalone script
_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from source.utils.config import CHUNK01_MANIFESTS_DIR
from source.utils.logging_config import get_logger

logger = get_logger("recompute_provenance_check")


def scan_manifest_provenance_independently(manifest_file: Path) -> Tuple[bool, List[str]]:
    """Independently parse JSON and scan for undocumented steps or missing provenance."""
    issues: List[str] = []

    with open(manifest_file, "r", encoding="utf-8") as f:
        data = json.load(f)

    if "provenance_chain" not in data:
        return False, [f"{manifest_file.name}: 'provenance_chain' top-level key missing"]

    pc = data["provenance_chain"]
    if not isinstance(pc, dict) or len(pc) == 0:
        return False, [f"{manifest_file.name}: 'provenance_chain' is empty or not an object"]

    for channel, details in pc.items():
        if not isinstance(details, dict):
            issues.append(f"{manifest_file.name} [{channel}]: details object missing")
            continue

        raw = details.get("raw_product")
        if not raw or not isinstance(raw, str) or len(raw.strip()) == 0:
            issues.append(f"{manifest_file.name} [{channel}]: raw_product missing or empty")

        steps = details.get("transformation_steps")
        if not steps or not isinstance(steps, list) or len(steps) == 0:
            issues.append(f"{manifest_file.name} [{channel}]: transformation_steps list missing or empty")

        undoc = details.get("undocumented_step")
        if undoc is not False:
            issues.append(f"{manifest_file.name} [{channel}]: undocumented_step is {undoc} (must be False)")

    passed = (len(issues) == 0)
    return passed, issues


def execute_recompute_provenance_validation(manifest_dir: Path) -> bool:
    """Run independent provenance scan across all data manifests in the directory."""
    logger.info(f"Recompute provenance validation scanning directory: {manifest_dir}...")
    manifest_files = sorted(list(manifest_dir.glob("*_data_manifest.json")))

    if not manifest_files:
        logger.error(f"No data manifests found in {manifest_dir}")
        return False

    all_passed = True
    total_channels = 0

    for mf in manifest_files:
        passed, issues = scan_manifest_provenance_independently(mf)
        if passed:
            logger.info(f"  [RECOMPUTE PASS] {mf.name}")
        else:
            logger.error(f"  [RECOMPUTE FAIL] {mf.name}: {issues}")
            all_passed = False

    return all_passed


def main() -> None:
    manifest_dir = CHUNK01_MANIFESTS_DIR
    success = execute_recompute_provenance_validation(manifest_dir)
    # Output final JSON summary line for gatekeeper recompute parsing
    result_payload = {
        "undocumented_step": not success,
        "status": "PASS" if success else "FAIL"
    }
    print(json.dumps(result_payload))
    if success:
        sys.exit(0)
    else:
        sys.exit(1)


if __name__ == "__main__":
    main()
