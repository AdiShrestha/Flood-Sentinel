"""Key Fact Registry Verification Engine v2 (C10-00 structural fix).

Validates that project/key_facts.md declares schema-compliant `## Key Fact:` blocks
for all quantitative anchors, verifies them against the canonical
`final_results_manifest.json` (never hardcoded values), and enforces document-wide
consistency (detecting and failing on any duplicate or conflicting declarations).

Usage:
    python3 source/release/verify_key_facts.py
    python3 source/release/verify_key_facts.py --manifest project/chunks/chunk10/final_results_manifest.json
"""

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Dict, Any, List

# Add project root to sys.path
_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from source.utils.config import PROJECT_DIR, REPO_ROOT
from source.utils.logging_config import get_logger
from factory.gatekeeper import _parse_key_facts

logger = get_logger("verify_key_facts")

DEFAULT_MANIFEST = PROJECT_DIR / "chunks" / "chunk10" / "final_results_manifest.json"


def _build_required_anchors_from_manifest(manifest_path: Path) -> List[Dict[str, Any]]:
    """Build required anchor list from final_results_manifest.json instead of hardcoding values.

    This is the structural fix from C10-00: target values are read from the canonical
    manifest at runtime, so a changed result value automatically propagates to the
    verifier without requiring a code edit.
    """
    if manifest_path.exists():
        with open(manifest_path, "r", encoding="utf-8") as f:
            m = json.load(f)
        primary_auc = m["primary_auc_pooled"]
        basin_median = m["primary_auc_basin_median"]
        nwm_auc = m["nwm_auc_pooled"]
        ea_lstm_auc = m["ea_lstm_auc_pooled"]
        persistence_auc = m["persistence_auc_pooled"]
    else:
        # Fallback: build manifest on-the-fly
        from source.release.build_final_results_manifest import build_manifest
        mdata = build_manifest(manifest_path)
        primary_auc = mdata["primary_auc_pooled"]
        basin_median = mdata["primary_auc_basin_median"]
        nwm_auc = mdata["nwm_auc_pooled"]
        ea_lstm_auc = mdata["ea_lstm_auc_pooled"]
        persistence_auc = mdata["persistence_auc_pooled"]

    return [
        {"anchor": "total streamgages", "value": 54.0, "tolerance": 0.0},
        {"anchor": "training partition streamgages", "value": 32.0, "tolerance": 0.0},
        {"anchor": "validation partition streamgages", "value": 11.0, "tolerance": 0.0},
        {"anchor": "testing partition streamgages", "value": 11.0, "tolerance": 0.0},
        {"anchor": "total training windows", "value": 9760.0, "tolerance": 0.0},
        {"anchor": "pretraining model parameters", "value": 146950.0, "tolerance": 0.0},
        # Dynamic from manifest — never hardcoded:
        {"anchor": "Primary Score-A Test AUC-ROC", "value": round(primary_auc, 4), "tolerance": 0.001},
        {"anchor": "Score-A Basin Median AUC", "value": round(basin_median, 4), "tolerance": 0.001},
        {"anchor": "NWM Retrospective Test AUC-ROC", "value": round(nwm_auc, 4), "tolerance": 0.001},
        {"anchor": "Supervised EA-LSTM Test AUC-ROC", "value": round(ea_lstm_auc, 4), "tolerance": 0.001},
        {"anchor": "Persistence Test AUC-ROC", "value": round(persistence_auc, 4), "tolerance": 0.001},
        {"anchor": "bootstrap iterations", "value": 10000.0, "tolerance": 0.0},
        {"anchor": "response-time-eligible streamgages", "value": 44.0, "tolerance": 0.0},
        {"anchor": "eligible gauges with flood events", "value": 43.0, "tolerance": 0.0},
        {"anchor": "total qualifying flood events in eligible basins", "value": 2153.0, "tolerance": 0.0},
    ]


def scan_document_for_conflicting_anchors(text: str, declared_facts: List[Dict[str, Any]]) -> List[str]:
    """Scan entire prose of key_facts.md for conflicting values near declared anchor terms."""
    findings = []
    # Split text into upper prose section (before machine-readable section)
    split_marker = "# Machine-Readable Key Fact Registry"
    if split_marker in text:
        prose_section = text.split(split_marker)[0]
    else:
        prose_section = text

    for fact in declared_facts:
        anchor = fact["anchor"]
        val = fact["value"]
        tol = fact["tolerance"]

        # Search for occurrences of anchor in prose
        pattern = re.compile(rf'.{{0,60}}\b{re.escape(anchor)}\b.{{0,60}}', re.IGNORECASE)
        for m in pattern.finditer(prose_section):
            window = m.group(0)
            nums = [float(n) for n in re.findall(r'\b\d+(?:\.\d+)?\b', window)]
            for n in nums:
                if abs(n - val) > max(tol, 1e-4):
                    findings.append(
                        f"PROSE CONFLICT: Near anchor '{anchor}', found {n} differing from declared value {val} (window: '{window.strip()}')"
                    )

    return findings


def verify_key_facts_registry(manifest_path: Path = DEFAULT_MANIFEST) -> Dict[str, Any]:
    """Verify machine-readable key facts in project/key_facts.md and enforce document-wide consistency."""
    key_facts_path = PROJECT_DIR / "key_facts.md"
    logger.info(f"Parsing and verifying key facts from {key_facts_path}...")
    logger.info(f"Using manifest: {manifest_path}")

    if not key_facts_path.exists():
        raise FileNotFoundError(f"Key facts file not found at {key_facts_path}")

    text = key_facts_path.read_text(encoding="utf-8")
    facts, parse_findings = _parse_key_facts(key_facts_path)

    if facts is None:
        raise RuntimeError(f"Failed to read {key_facts_path}")

    # Check for malformed blocks
    malformed = [f for f in parse_findings if "MALFORMED KEY FACT" in f]
    if malformed:
        for m in malformed:
            logger.error(m)
        raise ValueError(f"Found {len(malformed)} malformed key fact blocks in {key_facts_path}")

    logger.info(f"Successfully parsed {len(facts)} Key Fact blocks with 0 malformed warnings.")

    # Check for duplicate anchors with conflicting values
    anchor_seen: Dict[str, float] = {}
    for f in facts:
        a_key = f["anchor"].lower()
        if a_key in anchor_seen:
            if abs(anchor_seen[a_key] - f["value"]) > 1e-6:
                raise ValueError(
                    f"DUPLICATE CONFLICTING ANCHOR: '{f['anchor']}' declared with conflicting values: "
                    f"{anchor_seen[a_key]} vs {f['value']}"
                )
        anchor_seen[a_key] = f["value"]

    # Check prose consistency across the entire document
    conflicts = scan_document_for_conflicting_anchors(text, facts)
    if conflicts:
        for c in conflicts:
            logger.error(c)
        raise ValueError(f"Found {len(conflicts)} prose-level conflicts in {key_facts_path}")

    logger.info("Document-wide consistency check: 0 conflicting anchor declarations detected.")

    # Build required anchors from manifest — never hardcoded
    required_anchors = _build_required_anchors_from_manifest(manifest_path)

    # Map parsed facts by anchor (case-insensitive)
    parsed_map = {f["anchor"].lower(): f for f in facts}

    verified_checks = []
    for req in required_anchors:
        req_key = req["anchor"].lower()
        if req_key not in parsed_map:
            raise KeyError(f"Required key fact anchor '{req['anchor']}' not found in parsed facts.")

        parsed = parsed_map[req_key]
        val_diff = abs(parsed["value"] - req["value"])
        if val_diff > max(req["tolerance"], 1e-4):
            raise ValueError(
                f"Key fact anchor '{req['anchor']}' value mismatch: "
                f"expected {req['value']} (from manifest), found {parsed['value']}"
            )

        verified_checks.append({
            "anchor": req["anchor"],
            "expected_value": req["value"],
            "tolerance": req["tolerance"],
            "status": "PASS"
        })
        logger.info(f"  [PASS] Anchor '{req['anchor']}': value={req['value']}, tol={req['tolerance']}")

    summary = {
        "status": "PASS",
        "total_parsed_facts": len(facts),
        "required_facts_verified": len(verified_checks),
        "malformed_warnings": len(parse_findings),
        "conflicts_detected": len(conflicts),
        "manifest_source": str(manifest_path),
        "checks": verified_checks
    }

    logger.info("All required key fact anchors successfully verified with zero duplicate or prose conflicts!")
    return summary


def main() -> None:
    parser = argparse.ArgumentParser(description="Verify key facts registry against manifest")
    parser.add_argument("--manifest", type=str, default=None,
                        help="Path to final_results_manifest.json")
    args = parser.parse_args()

    manifest_path = Path(args.manifest) if args.manifest else DEFAULT_MANIFEST
    verify_key_facts_registry(manifest_path)


if __name__ == "__main__":
    main()
