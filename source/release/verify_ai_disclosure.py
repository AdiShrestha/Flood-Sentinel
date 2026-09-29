"""AI-Assistance Disclosure Verification Engine (C09-04).

Validates that project/chunks/chunk09/ai_disclosure.md comprehensively covers:
1. Architectural Role (Claude Opus 4.6)
2. Implementation Role (Gemini)
3. Mechanical Verification Framework (Gatekeeper, Invariants, Recomputation)
4. Human Oversight & Editorial Responsibility
and passes local-path leak scanning with 0 findings.
"""

import sys
from pathlib import Path
from typing import Dict, Any, List

# Add project root to sys.path
_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from source.utils.config import CHUNK09_DIR
from source.utils.logging_config import get_logger
from factory.gatekeeper import _scan_local_paths

logger = get_logger("verify_ai_disclosure")


def verify_ai_disclosure() -> Dict[str, Any]:
    """Verify AI disclosure statement contents and compliance."""
    logger.info("Verifying AI-Assistance Disclosure Specification (C09-04)...")

    disclosure_path = CHUNK09_DIR / "ai_disclosure.md"
    if not disclosure_path.exists():
        raise FileNotFoundError(f"AI disclosure file not found at {disclosure_path}")

    text = disclosure_path.read_text(encoding="utf-8")

    # Required thematic keywords and concepts
    required_sections = [
        {"name": "Architect Role (Claude Opus)", "terms": ["Claude Opus", "Architect", "invariant", "contract", "T-COMP"]},
        {"name": "Implementation Role (Gemini)", "terms": ["Gemini", "Implementation", "data acquisition", "pretraining", "ablation"]},
        {"name": "Mechanical Verification", "terms": ["Gatekeeper", "Reality Gate", "key_facts.md", "recomputation"]},
        {"name": "Human Oversight", "terms": ["Human", "authorship", "responsibility", "COPE", "IEEE"]},
        {"name": "Venue & Policy Compliance", "terms": ["IEEE Access", "ACM", "disclosure", "authenticity"]}
    ]

    section_checks = []
    for sec in required_sections:
        missing = [t for t in sec["terms"] if t.lower() not in text.lower()]
        passed = len(missing) == 0
        section_checks.append({
            "section": sec["name"],
            "required_terms": sec["terms"],
            "missing_terms": missing,
            "status": "PASS" if passed else "FAIL"
        })
        if not passed:
            raise ValueError(f"AI disclosure missing required terms for {sec['name']}: {missing}")
        logger.info(f"  [PASS] {sec['name']} fully documented.")

    # Check for path leaks
    leaks = _scan_local_paths([disclosure_path])
    if leaks:
        for leak in leaks:
            logger.error(leak)
        raise ValueError(f"Found {len(leaks)} local path leaks in {disclosure_path}!")

    logger.info("AI-Assistance disclosure path leak scan: 0 leaks found (PASS).")
    logger.info("AI disclosure verification complete: 100% compliant.")

    return {
        "status": "PASS",
        "file": str(disclosure_path),
        "checks": section_checks,
        "path_leaks": len(leaks)
    }


def main() -> None:
    verify_ai_disclosure()


if __name__ == "__main__":
    main()
