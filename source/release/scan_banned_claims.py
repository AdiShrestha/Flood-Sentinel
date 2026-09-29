"""scan_banned_claims.py -- Global Submission-Safe Scrub & Banned-Claim Scanner.

Scans all active release artifacts for:
1. Banned / restricted phrases & overclaiming terminology.
2. Superseded numerical values (0.8226, 168.0h, etc.).
3. Superseded hypothesis verdicts (lingering H2 SUPPORTED, etc.).
4. Local paths, personal directories, credentials, private tokens.
5. Dual-venue hedging on active submission surfaces.

Usage:
    python3 source/release/scan_banned_claims.py --scope release
    python3 source/release/scan_banned_claims.py --scope release --out project/chunks/chunk10/submission_safe_scrub_report.md
"""

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any, Dict, List, Tuple

# Add project root to sys.path
_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from source.utils.logging_config import get_logger

logger = get_logger("scan_banned_claims")

# Release files subject to binding audit
RELEASE_FILES = [
    _PROJECT_ROOT / "project" / "chunks" / "chunk09" / "manuscript_draft.md",
    _PROJECT_ROOT / "project" / "chunks" / "chunk09" / "final_synthesis_report.md",
    _PROJECT_ROOT / "project" / "chunks" / "chunk09" / "ai_disclosure.md",
    _PROJECT_ROOT / "project" / "chunks" / "chunk09" / "ieee_dataport_deposit.md",
    _PROJECT_ROOT / "project" / "chunks" / "chunk09" / "dataport_manifest.json",
    _PROJECT_ROOT / "REPRODUCIBILITY.md",
    _PROJECT_ROOT / "project" / "chunks" / "chunk10" / "final_results_manifest.json",
    _PROJECT_ROOT / "project" / "chunks" / "chunk10" / "venue_compliance_matrix.md",
    _PROJECT_ROOT / "project" / "chunks" / "chunk10" / "venue_decision_rationale.md",
    _PROJECT_ROOT / "project" / "chunks" / "chunk10" / "baseline_parity_audit.md",
    _PROJECT_ROOT / "project" / "chunks" / "chunk10" / "data_license_manifest.json",
    _PROJECT_ROOT / "project" / "chunks" / "chunk10" / "effective_sample_audit.json",
    _PROJECT_ROOT / "project" / "chunks" / "chunk10" / "h2_cohort_accounting.md",
    _PROJECT_ROOT / "LICENSE",
]

# Prohibited patterns with explanation and exclusion rules
BANNED_RULES = [
    {
        "id": "B-001",
        "name": "Stale Anchor: 0.8226",
        "pattern": r"\b0\.8226\b",
        "description": "Superseded collapsed test AUC anchor; canonical is 0.8296.",
        "exempt_files": []
    },
    {
        "id": "B-002",
        "name": "Stale Anchor: 168.0h / 168h lead time",
        "pattern": r"\b168(?:\.0)?\s*h(?:ours)?\b",
        "description": "Superseded 7-day lead-time claim; H2 is falsified (0.0h median).",
        "exempt_files": []
    },
    {
        "id": "B-003",
        "name": "Ungauged Basin Overclaiming",
        "pattern": r"\bungauged\s+(?:basin|catchment)s?\s+(?:generalization|prediction|forecasting)\b",
        "description": "Prohibited ungauged generalization claim (must be gauged/label-scarce).",
        "exempt_files": []
    },
    {
        "id": "B-004",
        "name": "Statistical Parity Claim",
        "pattern": r"\bstatistical\s+parity\b",
        "description": "Mathematical equivalence / statistical parity is prohibited per venue rules.",
        "exempt_files": []
    },
    {
        "id": "B-005",
        "name": "Superior or Equivalent Claim",
        "pattern": r"\bsuperior\s+or\s+equivalent\b",
        "description": "Prohibited overclaiming comparative phrase.",
        "exempt_files": []
    },
    {
        "id": "B-006",
        "name": "Unqualified NWM Superiority",
        "pattern": r"\b(?:beats|outperforms)\s+the\s+National\s+Water\s+Model\b(?!.*Retrospective)",
        "description": "Must cite NWM Retrospective specifically, not blanket operational NWM.",
        "exempt_files": []
    },
    {
        "id": "B-007",
        "name": "Superseded H2 Supported Verdict",
        "pattern": r"\bH(?:ypothesis)?[- ]?2\s+(?:is\s+)?SUPPORTED\b",
        "description": "H2 was empirically falsified (0/8 detections); lingering SUPPORTED verdict is forbidden.",
        "exempt_files": []
    },
    {
        "id": "B-008",
        "name": "Dual-Venue Hedging on Title Page",
        "pattern": r"\bTarget Venue:\s*IEEE Access\s*/\s*IEEE JSTARS\b",
        "description": "Manuscript must be committed to a single venue (IEEE Access per C10-09).",
        "exempt_files": []
    },
    {
        "id": "B-009",
        "name": "Local Path Leaks",
        "pattern": r"(?:/Users/[a-zA-Z0-9_\-]+|/home/[a-zA-Z0-9_\-]+|[A-Z]:\\[a-zA-Z0-9_\-]+)",
        "description": "Hardcoded personal filesystem paths violate INV-012.",
        "exempt_files": []
    },
    {
        "id": "B-010",
        "name": "API Key / Credential Leaks",
        "pattern": r"(?:ghp_[a-zA-Z0-9]{36}|AIza[0-9A-Za-z-_]{35}|AKIA[0-9A-Z]{16})",
        "description": "Exposed authentication tokens or cloud API keys.",
        "exempt_files": []
    },
]


def scan_file(filepath: Path) -> List[Dict[str, Any]]:
    """Scan a single file against all banned rules."""
    if not filepath.exists():
        return [{"rule_id": "ERR", "rule_name": "File Not Found", "match": str(filepath), "line": 0}]

    try:
        content = filepath.read_text(encoding="utf-8")
    except Exception as e:
        return [{"rule_id": "ERR", "rule_name": f"Read Error: {e}", "match": str(filepath), "line": 0}]

    findings = []
    lines = content.splitlines()

    for rule in BANNED_RULES:
        if filepath.name in rule["exempt_files"]:
            continue

        for line_idx, line in enumerate(lines, 1):
            # Check if line matches pattern
            matches = re.finditer(rule["pattern"], line, re.IGNORECASE)
            for m in matches:
                # Discard false positives where pattern is explicitly marked as 'prohibited' or in negative context
                match_text = m.group(0)
                findings.append({
                    "rule_id": rule["id"],
                    "rule_name": rule["name"],
                    "description": rule["description"],
                    "file": str(filepath.relative_to(_PROJECT_ROOT)),
                    "line": line_idx,
                    "snippet": line.strip()[:100],
                    "match": match_text,
                })

    return findings


def execute_scrub(scope: str = "release", out_path: Path = None) -> bool:
    """Run full submission-safe scrub."""
    logger.info("Executing Global Submission-Safe Scrub & Banned-Claim Audit (C10-15)...")

    files_to_scan = list(RELEASE_FILES)
    
    # Also add all figures in project/chunks/chunk10/figures/
    fig_dir = _PROJECT_ROOT / "project" / "chunks" / "chunk10" / "figures"
    if fig_dir.exists():
        files_to_scan.extend(fig_dir.glob("*.svg"))

    all_findings = []
    files_scanned_count = 0

    for fpath in files_to_scan:
        if fpath.exists():
            files_scanned_count += 1
            findings = scan_file(fpath)
            all_findings.extend(findings)

    # Generate Markdown Report
    report_lines = [
        "# Submission-Safe Artifact Scrub & Global Banned-Claim Report",
        "",
        "**Contract:** C10-15 · **Risk Tier:** High · **Evaluation Date:** 2026-08-18",
        f"**Files Scanned:** {files_scanned_count} release artifacts · **Total Violations:** {len(all_findings)}",
        f"**Audit Verdict:** {'✅ 100% SUBMISSION-SAFE (PASS)' if len(all_findings) == 0 else '❌ VIOLATIONS DETECTED (FAIL)'}",
        "",
        "---",
        "",
        "## 1. Executive Summary",
        "",
        "This automated scrub scans all outward-facing publication artifacts (manuscript, synthesis reports, replication guides, AI disclosures, deposit manifests, and figures) against the complete dictionary of venue restrictions, prohibited overclaims, stale numerical anchors, and local path/credential leaks.",
        "",
        "---",
        "",
        "## 2. Audit Rules Evaluated",
        "",
        "| Rule ID | Rule Name | Prohibited Target | Status |",
        "|---|---|---|---|",
    ]

    for rule in BANNED_RULES:
        rule_findings = [f for f in all_findings if f["rule_id"] == rule["id"]]
        status_str = "✅ PASS (0 matches)" if len(rule_findings) == 0 else f"❌ FAIL ({len(rule_findings)} matches)"
        report_lines.append(f"| `{rule['id']}` | **{rule['name']}** | {rule['description']} | {status_str} |")

    report_lines.extend([
        "",
        "---",
        "",
        "## 3. Scanned Release Artifacts",
        "",
    ])

    for fpath in files_to_scan:
        if fpath.exists():
            rel = str(fpath.relative_to(_PROJECT_ROOT))
            f_findings = [f for f in all_findings if f.get("file") == rel]
            status = "✅ Clean" if len(f_findings) == 0 else f"❌ {len(f_findings)} Flagged"
            report_lines.append(f"- `{rel}` ({fpath.stat().st_size:,} bytes) — {status}")

    report_lines.extend([
        "",
        "---",
        "",
        "## 4. Itemized Findings & Disclosures",
        "",
    ])

    if len(all_findings) == 0:
        report_lines.append("🎉 **Zero prohibited phrases, stale values, or secret leaks detected across all release artifacts.**")
    else:
        for f in all_findings:
            report_lines.append(f"- **[{f['rule_id']} - {f['rule_name']}]** `{f['file']}` (Line {f['line']}): `{f['snippet']}`")

    report_lines.append("")

    if out_path:
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text("\n".join(report_lines) + "\n", encoding="utf-8")
        logger.info(f"Submission scrub report written to: {out_path}")

    if len(all_findings) == 0:
        logger.info(f"\nSubmission-Safe Scrub PASSED: {files_scanned_count} artifacts scanned with 0 findings.")
        return True
    else:
        logger.error(f"\nSubmission-Safe Scrub FAILED: {len(all_findings)} violations detected.")
        return False


def main():
    parser = argparse.ArgumentParser(description="Scan release artifacts for banned claims and secrets.")
    parser.add_argument("--scope", default="release", choices=["release", "all"], help="Scan scope")
    parser.add_argument("--out", help="Output Markdown report path")
    args = parser.parse_args()

    out_p = Path(args.out) if args.out else _PROJECT_ROOT / "project" / "chunks" / "chunk10" / "submission_safe_scrub_report.md"
    ok = execute_scrub(scope=args.scope, out_path=out_p)
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
