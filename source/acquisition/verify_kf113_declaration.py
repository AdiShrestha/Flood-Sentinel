"""Verification script for KF-113 Response-Time Estimator Declaration (C02-02).

Validates that project/key_facts.md contains the formal KF-113 declaration
specifying the T_response_proxy estimator formula, citations, drainage-area
stratification boundaries, and declaration timestamp prior to eligibility computation.
"""

import re
import sys
from pathlib import Path
from typing import List

# Add project root to sys.path if running as standalone script
_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from source.utils.config import PROJECT_DIR
from source.utils.logging_config import get_logger

logger = get_logger("verify_kf113_declaration")


def validate_kf113_declaration() -> List[str]:
    """Validate KF-113 declaration in project/key_facts.md."""
    errors: List[str] = []

    key_facts_file = PROJECT_DIR / "key_facts.md"
    if not key_facts_file.exists():
        return [f"key_facts.md missing at {key_facts_file}"]

    content = key_facts_file.read_text(encoding="utf-8")

    # 1. Check KF-113 presence
    if "KF-113" not in content:
        errors.append("KF-113 entry not found in project/key_facts.md")

    # 2. Check for estimator formula and methodology
    if "T_{lag}" not in content and "T_lag" not in content and "NRCS" not in content:
        errors.append("KF-113 missing hydrological estimator formulation (NRCS / lag / wave routing)")

    # 3. Check for genuine citations
    required_citations = ["Mockus", "Simas", "Jobson"]
    missing_citations = [c for c in required_citations if c not in content]
    if missing_citations:
        errors.append(f"KF-113 missing peer-reviewed citation(s): {missing_citations}")

    # 4. Check for declaration date
    if "2026-08-17" not in content:
        errors.append("KF-113 missing frozen declaration date (2026-08-17)")

    # 5. Check for drainage-area stratification boundary
    if "500" not in content or "km" not in content:
        errors.append("KF-113 missing drainage-area stratification boundary (500 km^2)")

    return errors


def main() -> None:
    errors = validate_kf113_declaration()
    if errors:
        logger.error(f"KF-113 Declaration Verification FAILED with {len(errors)} error(s):")
        for err in errors:
            logger.error(f"  - {err}")
        sys.exit(1)
    else:
        logger.info("KF-113 Response-Time Estimator Declaration Verification PASSED.")
        sys.exit(0)


if __name__ == "__main__":
    main()
