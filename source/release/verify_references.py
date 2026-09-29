"""verify_references.py -- Verifies in-text citations and References list in manuscript draft.

Checks:
1. Every in-text citation marker [N] corresponds to an entry [N] in the References section.
2. Every entry [N] in the References section is cited at least once in the text (no orphaned references).
3. Numbering is sequential 1..M without gaps.
4. Reports total references, list of citations, and verification status.

Usage:
    python3 source/release/verify_references.py --manuscript project/chunks/chunk09/manuscript_draft.md
"""

import argparse
import re
import sys
from pathlib import Path

# Add project root to path
_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from source.utils.logging_config import get_logger

logger = get_logger("verify_references")


def parse_references_section(content: str):
    """Extract all numbered reference entries from the References section."""
    ref_section_match = re.search(r"##\s*References\s*\n(.*)", content, re.DOTALL)
    if not ref_section_match:
        logger.error("No '## References' section found in manuscript!")
        return {}

    ref_text = ref_section_match.group(1)
    # Find entries like [1] ...
    entries = {}
    pattern = r"\[(\d+)\]\s+([^\n]+(?:\n(?!\s*\[\d+\]|\s*##|\s*---)[^\n]+)*)"
    for m in re.finditer(pattern, ref_text):
        num = int(m.group(1))
        text = m.group(2).strip()
        entries[num] = text

    return entries


def parse_in_text_citations(content: str):
    """Extract all in-text citation numbers from the body (excluding References section)."""
    ref_section_match = re.search(r"##\s*References\s*\n", content)
    body_text = content[:ref_section_match.start()] if ref_section_match else content

    # Strip inline and block LaTeX math ($...$ and $$...$$) to avoid matching intervals like [$T \in [180, 540]$]
    clean_body = re.sub(r"\$\$.*?\$\$", "", body_text, flags=re.DOTALL)
    clean_body = re.sub(r"\$.*?\$", "", clean_body)

    # Find [1], [2], [1, 2], [1]-[3], etc.
    citations = set()
    bracket_matches = re.finditer(r"\[(\d+(?:\s*,\s*\d+)*)\]", clean_body)
    for bm in bracket_matches:
        parts = bm.group(1).split(",")
        for p in parts:
            p_str = p.strip()
            if p_str.isdigit():
                citations.add(int(p_str))

    return citations


def verify_references(manuscript_path: Path) -> bool:
    """Run full references validation."""
    if not manuscript_path.exists():
        logger.error(f"Manuscript not found at: {manuscript_path}")
        return False

    content = manuscript_path.read_text(encoding="utf-8")
    ref_entries = parse_references_section(content)
    in_text_cites = parse_in_text_citations(content)

    logger.info(f"Loaded manuscript from: {manuscript_path}")
    logger.info(f"Found {len(ref_entries)} reference entries in References section.")
    logger.info(f"Found {len(in_text_cites)} distinct in-text citation markers.")

    success = True

    # Check sequential numbering
    if ref_entries:
        max_num = max(ref_entries.keys())
        expected_set = set(range(1, max_num + 1))
        missing_entries = expected_set - set(ref_entries.keys())
        if missing_entries:
            logger.error(f"FAIL: Missing reference numbers in bibliography: {sorted(missing_entries)}")
            success = False
        else:
            logger.info(f"[PASS] References are sequentially numbered 1 through {max_num}.")

    # Check 1: In-text citations without reference entry
    orphaned_citations = in_text_cites - set(ref_entries.keys())
    if orphaned_citations:
        logger.error(f"FAIL: In-text citations have no matching reference entry: {sorted(orphaned_citations)}")
        success = False
    else:
        logger.info("[PASS] 0 orphaned in-text citation markers.")

    # Check 2: Reference entries never cited in text
    uncited_entries = set(ref_entries.keys()) - in_text_cites
    if uncited_entries:
        logger.error(f"FAIL: Reference entries never cited in body text: {sorted(uncited_entries)}")
        success = False
    else:
        logger.info("[PASS] 0 uncited reference entries.")

    # Log all verified entries
    logger.info("\n--- Verified Bibliography ---")
    for num in sorted(ref_entries.keys()):
        logger.info(f"  [{num}] {ref_entries[num][:90]}...")

    if success and len(ref_entries) >= 9:
        logger.info(f"\nReferences Verification: PASS ({len(ref_entries)} citations perfectly verified)")
        return True
    elif not success:
        logger.error("\nReferences Verification: FAIL")
        return False
    else:
        logger.error(f"FAIL: Too few references ({len(ref_entries)} < 9 minimum)")
        return False


def main():
    parser = argparse.ArgumentParser(description="Verify manuscript references.")
    parser.add_argument("--manuscript", required=True, help="Path to manuscript markdown file")
    args = parser.parse_args()

    ok = verify_references(Path(args.manuscript))
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
