"""Verification script for Full-Panel Stratification Report & Panel Finalization (C02-14).

Validates that stratification_report.md exists, covers all 8 required dimensions,
includes A-001 and A-003 checks, and contains the formal panel finalization declaration.
"""

import sys
from pathlib import Path
from typing import List

# Add project root to sys.path if running as standalone script
_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from source.utils.config import CHUNK02_DIR
from source.utils.logging_config import get_logger

logger = get_logger("verify_stratification_report")


def validate_stratification_report() -> List[str]:
    """Validate full-panel stratification report deliverables."""
    errors: List[str] = []

    report_path = CHUNK02_DIR / "stratification_report.md"
    if not report_path.exists():
        return [f"stratification_report.md missing at {report_path}"]

    report_text = report_path.read_text(encoding="utf-8")

    # Required section checks
    required_sections = [
        ("A-001 Check", "A-001 Check: Ref/Non-Ref Ratio"),
        ("A-003 Check", "A-003 Check: GAGES-II vs. NID Classification"),
        ("Hydrologic Region", "Hydrologic Region Distribution"),
        ("Drainage Area", "Drainage Area Class Distribution"),
        ("Snow Influence", "Snow Influence Distribution"),
        ("Climate Regime", "Climate Regime Distribution"),
        ("Response-Time Eligibility", "Response-Time Eligibility Distribution"),
        ("Historical Flood Frequency", "Historical Flood Frequency"),
        ("Sample Adequacy Summary", "Sample Adequacy Summary"),
        ("Panel Finalization", "Panel Finalization Declaration")
    ]

    for label, pattern in required_sections:
        if pattern.lower() not in report_text.lower():
            errors.append(f"Required section '{label}' missing from stratification_report.md")

    # Check panel size mentioned
    if "54" not in report_text:
        errors.append("Expected 54 panel streamgages count in stratification_report.md")

    return errors


def main() -> None:
    errors = validate_stratification_report()
    if errors:
        logger.error(f"Stratification Report Verification FAILED with {len(errors)} error(s):")
        for err in errors:
            logger.error(f"  - {err}")
        sys.exit(1)
    else:
        logger.info("Full-Panel Stratification Report Verification PASSED.")
        sys.exit(0)


if __name__ == "__main__":
    main()
