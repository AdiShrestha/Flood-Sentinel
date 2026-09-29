"""Release Integrity and Zero-Leakage Verification Engine (C09-05).

Executes Gatekeeper release-check across all release-bound artifacts:
- project/chunks/chunk09/manuscript_draft.md
- REPRODUCIBILITY.md
- project/chunks/chunk09/ai_disclosure.md
- project/chunks/chunk09/ieee_dataport_deposit.md
against project/key_facts.md.
"""

import json
import subprocess
import sys
from pathlib import Path
from typing import Dict, Any

# Add project root to sys.path
_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from source.utils.config import (
    REPO_ROOT,
    PROJECT_DIR,
    CHUNK09_DIR
)
from source.utils.logging_config import get_logger

logger = get_logger("verify_release_integrity")


def verify_release_integrity() -> Dict[str, Any]:
    """Execute gatekeeper release-check and certify zero leakage / zero fact drift."""
    logger.info("Executing Gatekeeper Release Check & Zero-Leakage Certification (C09-05)...")

    manuscript = PROJECT_DIR / "chunks/chunk09/manuscript_draft.md"
    reproducibility = REPO_ROOT / "REPRODUCIBILITY.md"
    ai_disclosure = PROJECT_DIR / "chunks/chunk09/ai_disclosure.md"
    dataport_deposit = PROJECT_DIR / "chunks/chunk09/ieee_dataport_deposit.md"
    key_facts = PROJECT_DIR / "key_facts.md"

    for p in [manuscript, reproducibility, ai_disclosure, dataport_deposit, key_facts]:
        if not p.exists():
            raise FileNotFoundError(f"Required release check artifact not found: {p}")

    cmd = [
        sys.executable,
        str(REPO_ROOT / "factory/gatekeeper.py"),
        "release-check",
        "--manuscript", str(manuscript),
        "--files", str(reproducibility), str(ai_disclosure), str(dataport_deposit),
        "--key-facts", str(key_facts)
    ]

    logger.info(f"Running release check command: {' '.join(cmd)}")
    result = subprocess.run(cmd, capture_output=True, text=True, cwd=str(REPO_ROOT))

    print(result.stdout)
    if result.stderr:
        print(result.stderr, file=sys.stderr)

    if result.returncode != 0:
        logger.error(f"Release check failed with exit code {result.returncode}")
        raise RuntimeError(f"Gatekeeper release-check failed (code {result.returncode})")

    # Check output text for failures
    if "Failures: 0" not in result.stdout:
        raise ValueError("Release check did not report Failures: 0")

    # Serialize release check report
    rel_cmd = [
        "python3",
        "factory/gatekeeper.py",
        "release-check",
        "--manuscript", manuscript.relative_to(REPO_ROOT).as_posix(),
        "--files", reproducibility.relative_to(REPO_ROOT).as_posix(),
        ai_disclosure.relative_to(REPO_ROOT).as_posix(),
        dataport_deposit.relative_to(REPO_ROOT).as_posix(),
        "--key-facts", key_facts.relative_to(REPO_ROOT).as_posix()
    ]
    report_data = {
        "status": "PASS",
        "command": " ".join(rel_cmd),
        "return_code": result.returncode,
        "scanned_manuscript": manuscript.relative_to(REPO_ROOT).as_posix(),
        "scanned_files": [
            reproducibility.relative_to(REPO_ROOT).as_posix(),
            ai_disclosure.relative_to(REPO_ROOT).as_posix(),
            dataport_deposit.relative_to(REPO_ROOT).as_posix()
        ],
        "key_facts_registry": key_facts.relative_to(REPO_ROOT).as_posix(),
        "local_path_leaks_found": 0,
        "key_fact_mismatches_found": 0,
        "summary": "Gatekeeper release check passed cleanly with 0 path leaks and 0 key fact mismatches."
    }

    CHUNK09_DIR.mkdir(parents=True, exist_ok=True)
    report_path = CHUNK09_DIR / "release_check_report.json"
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(report_data, f, indent=2)

    logger.info(f"Release check report serialized to {report_path}")
    logger.info("C09-05 Release Integrity Certification: 100% PASS.")
    return report_data


def main() -> None:
    verify_release_integrity()


if __name__ == "__main__":
    main()
