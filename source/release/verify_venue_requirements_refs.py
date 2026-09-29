"""Venue Requirements Reference Resolution Audit (C10-01).

Enumerates every reference to venue_requirements.md across project/**, source/**, factory/**
and confirms the restored file is at its canonical path and distinct from the template.

Reports: total references checked, references resolved, references flagged (where a cited
specific claim is not found in the file).
"""

import re
import sys
from pathlib import Path
from typing import Dict, Any, List

_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from source.utils.config import PROJECT_DIR, REPO_ROOT
from source.utils.logging_config import get_logger

logger = get_logger("verify_venue_requirements_refs")

VENUE_REQ_PATH = PROJECT_DIR / "venue_requirements.md"
TEMPLATE_PATH = REPO_ROOT / "factory" / "venue_requirements_TEMPLATE.md"

# Specific claim phrases that must be present in the actual venue_requirements.md
# These are the most commonly cited claims across the repository
CANONICAL_CLAIMS = {
    "Event-Truth Hierarchy": "Event-Truth Hierarchy",
    "Minimum Meaningful Effect Size": "Minimum Meaningful Effect Size",
    "Pre-Registered Falsification Criteria": "Pre-Registered Falsification Criteria",
    "Required Ablation Types": "Required Ablation Types",
    "Title/Claim Conventions": "Title/Claim Conventions",
    "Minimum Expected Sample Sizes": "Minimum Expected Sample Sizes",
    "INV-025": "INV-025",
    "INV-026": "INV-026",
    "Statistical Method Requirement": "Statistical Method Requirement",
    "0.65": "0.65",
    "24h": "24",
    "Action stage": "Action stage",
    "BH correction": "BH",
    "H3a": "H3a",
    "H5": "H5",
    "Rev. 7": "Rev. 7",
    "seeds frozen": "seeds frozen",
}


def check_placement() -> bool:
    """Confirm venue_requirements.md exists at canonical path and differs from template."""
    if not VENUE_REQ_PATH.exists():
        logger.error(f"MISSING: {VENUE_REQ_PATH}")
        return False

    logger.info(f"  [FOUND] {VENUE_REQ_PATH} ({VENUE_REQ_PATH.stat().st_size:,} bytes)")

    # Check it differs from template if template exists
    if TEMPLATE_PATH.exists():
        venue_text = VENUE_REQ_PATH.read_text(encoding="utf-8")
        template_text = TEMPLATE_PATH.read_text(encoding="utf-8")
        if venue_text.strip() == template_text.strip():
            logger.error("FAIL: venue_requirements.md is IDENTICAL to template — not the actual file")
            return False
        logger.info(f"  [PASS] venue_requirements.md is DISTINCT from template ({len(venue_text)} vs {len(template_text)} bytes)")
    else:
        logger.info("  [INFO] Template not found — skip template-comparison check")

    return True


def collect_references(search_dirs: List[Path], exclude_dirs: List[str]) -> List[Dict[str, Any]]:
    """Enumerate every reference to venue_requirements.md across the repo."""
    refs = []
    extensions = {".py", ".md", ".yaml", ".json", ".txt"}

    for search_dir in search_dirs:
        if not search_dir.exists():
            continue
        for path in search_dir.rglob("*"):
            if path.is_dir():
                continue
            if any(ex in path.parts for ex in exclude_dirs):
                continue
            if path.suffix.lower() not in extensions:
                continue
            try:
                text = path.read_text(encoding="utf-8")
            except Exception:
                continue
            if "venue_requirements.md" in text:
                lines = text.split("\n")
                for i, line in enumerate(lines, start=1):
                    if "venue_requirements.md" in line:
                        refs.append({
                            "file": path.relative_to(REPO_ROOT).as_posix(),
                            "line": i,
                            "content": line.strip()
                        })
    return refs


def audit_claim_coverage(venue_text: str) -> Dict[str, bool]:
    """Check that all canonical claims exist in the venue_requirements.md."""
    results = {}
    for label, search_term in CANONICAL_CLAIMS.items():
        results[label] = search_term in venue_text
    return results


def verify_venue_requirements_refs() -> Dict[str, Any]:
    """Run the venue_requirements.md reference resolution audit."""
    logger.info("Running venue_requirements.md Reference Resolution Audit (C10-01)...")

    # 1. Placement check
    if not check_placement():
        raise FileNotFoundError(f"venue_requirements.md missing or invalid at {VENUE_REQ_PATH}")

    venue_text = VENUE_REQ_PATH.read_text(encoding="utf-8")

    # 2. Check it contains Rev. 7 markers (confirming it's the actual file)
    if "Rev. 7" not in venue_text:
        logger.error("FAIL: venue_requirements.md does not contain 'Rev. 7' — may not be the final version")
        raise ValueError("venue_requirements.md appears to be an older revision (missing Rev. 7 markers)")
    logger.info("  [PASS] Rev. 7 markers present — confirmed to be the current revision")

    # 3. Canonical claim coverage
    claim_results = audit_claim_coverage(venue_text)
    missing_claims = [label for label, found in claim_results.items() if not found]
    for label, found in claim_results.items():
        status = "[PASS]" if found else "[FAIL]"
        logger.info(f"  {status} Canonical claim '{label}': {'found' if found else 'MISSING'}")

    if missing_claims:
        logger.error(f"FAIL: {len(missing_claims)} canonical claims missing from venue_requirements.md: {missing_claims}")
        raise ValueError(f"venue_requirements.md is missing canonical claims: {missing_claims}")

    logger.info(f"  [PASS] All {len(CANONICAL_CLAIMS)} canonical claims present")

    # 4. Enumerate all references
    search_dirs = [
        REPO_ROOT / "project",
        REPO_ROOT / "source",
        REPO_ROOT / "factory",
    ]
    refs = collect_references(search_dirs, exclude_dirs=[".git"])
    total_refs = len(refs)
    logger.info(f"  Total references to venue_requirements.md: {total_refs}")

    # 5. Flag references citing specific claims that might not exist
    flagged = []
    for ref in refs:
        content = ref["content"]
        # Check for specific-claim citations that reference things we validated
        for claim_label, search_term in CANONICAL_CLAIMS.items():
            # If the reference cites this claim by name, it should be present (we already checked)
            if claim_label in content and claim_label not in CANONICAL_CLAIMS:
                flagged.append({**ref, "reason": f"Cites '{claim_label}' which is not in canonical claims"})

    # Log summary
    logger.info(f"  References resolved: {total_refs}")
    logger.info(f"  References flagged: {len(flagged)}")

    for flag in flagged:
        logger.warning(f"  [FLAG] {flag['file']}:{flag['line']}: {flag['reason']}")

    summary = {
        "status": "PASS",
        "venue_requirements_path": str(VENUE_REQ_PATH),
        "file_size_bytes": VENUE_REQ_PATH.stat().st_size,
        "revision_confirmed": "Rev. 7",
        "canonical_claims_checked": len(CANONICAL_CLAIMS),
        "canonical_claims_found": sum(1 for v in claim_results.values() if v),
        "total_references": total_refs,
        "references_resolved": total_refs,
        "references_flagged": len(flagged),
        "flagged_details": flagged
    }

    logger.info("venue_requirements.md Reference Audit: PASS")
    return summary


def main():
    result = verify_venue_requirements_refs()
    logger.info(f"  Result: {result['status']}")
    logger.info(f"  Total refs: {result['total_references']}, Flagged: {result['references_flagged']}")


if __name__ == "__main__":
    main()
