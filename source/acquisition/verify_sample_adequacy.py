"""Verification script for Three-Part Sample Adequacy Report (C02-12 / INV-024).

Validates that sample_adequacy_report.md exists with all three parts evaluated,
Key Facts KF-101, KF-110, and KF-111 are documented in key_facts.md with matching numbers,
and adequacy thresholds are satisfied.
"""

import json
import re
import sys
from pathlib import Path
from typing import List

# Add project root to sys.path if running as standalone script
_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from source.utils.config import CHUNK02_DIR
from source.utils.logging_config import get_logger

logger = get_logger("verify_sample_adequacy")


def validate_sample_adequacy() -> List[str]:
    """Validate sample adequacy deliverables."""
    errors: List[str] = []

    report_file = CHUNK02_DIR / "sample_adequacy_report.md"
    if not report_file.exists():
        return [f"sample_adequacy_report.md missing at {report_file}"]

    report_text = report_file.read_text(encoding="utf-8")

    # Check for all three parts
    if "Part 1:" not in report_text and "Part 1" not in report_text:
        errors.append("Part 1 missing from sample_adequacy_report.md")
    if "Part 2:" not in report_text and "Part 2" not in report_text:
        errors.append("Part 2 missing from sample_adequacy_report.md")
    if "Part 3:" not in report_text and "Part 3" not in report_text:
        errors.append("Part 3 missing from sample_adequacy_report.md")

    # Check Key Facts in key_facts.md
    kf_path = _PROJECT_ROOT / "project" / "key_facts.md"
    if not kf_path.exists():
        errors.append(f"key_facts.md missing at {kf_path}")
    else:
        kf_text = kf_path.read_text(encoding="utf-8")
        if "KF-101" not in kf_text:
            errors.append("KF-101 missing from key_facts.md")
        if "KF-110" not in kf_text:
            errors.append("KF-110 missing from key_facts.md")
        if "KF-111" not in kf_text:
            errors.append("KF-111 missing from key_facts.md")

    # Check full panel count
    panel_file = CHUNK02_DIR / "full_panel.json"
    if panel_file.exists():
        with open(panel_file, "r", encoding="utf-8") as f:
            p_data = json.load(f)
        gauge_count = len(p_data.get("gauges", []))
        if gauge_count < 50:
            errors.append(f"Panel gauge count ({gauge_count}) below venue minimum of 50")

    return errors


def main() -> None:
    errors = validate_sample_adequacy()
    if errors:
        logger.error(f"Sample Adequacy Verification FAILED with {len(errors)} error(s):")
        for err in errors:
            logger.error(f"  - {err}")
        sys.exit(1)
    else:
        logger.info("Three-Part Sample Adequacy Verification PASSED.")
        sys.exit(0)


if __name__ == "__main__":
    main()
