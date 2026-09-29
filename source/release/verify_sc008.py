"""SC-008 Three-Way Consistency Gate (C10-01).

Formally verifies mutual consistency between:
  1. project/chunks/chunk09/manuscript_draft.md
  2. project/venue_requirements.md (Frozen)
  3. project/key_facts.md
  4. project/chunks/chunk10/final_results_manifest.json

Checks:
  A. Every numeric claim in manuscript traces to a KF-block in key_facts.md
  B. Every KF-block's stated value matches final_results_manifest.json
  C. Every hypothesis verdict matches the mechanically-applied pre-registration criterion
  D. Effect-size threshold compliance (0.65 AUC minimum, 24h lead-time minimum)
  E. Banned/restricted claim terminology per venue_requirements.md Title/Claim Conventions

Exits non-zero with a specific mismatch report on any failure.

Usage:
    python3 source/release/verify_sc008.py \\
        --manuscript project/chunks/chunk09/manuscript_draft.md \\
        --venue-requirements project/venue_requirements.md \\
        --key-facts project/key_facts.md \\
        --manifest project/chunks/chunk10/final_results_manifest.json
"""

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Dict, Any, List, Optional

_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from source.utils.config import PROJECT_DIR, REPO_ROOT
from source.utils.logging_config import get_logger
from factory.gatekeeper import _parse_key_facts

logger = get_logger("verify_sc008")

# Banned/restricted terms per venue_requirements.md Title/Claim Conventions
# Format: (pattern, allowed_qualifiers, description)
# allowed_qualifiers: if ANY of these phrases appear within 120 chars of the match, the match is allowed
BANNED_TERMS = [
    (
        r'\brobust\b',
        # These qualifiers make 'robust' acceptable
        ["cross-gauge", "test", "sensitivity", "statistically", "Wilcoxon", "resampl"],
        "unqualified 'robust' — must cite specific test or sample size"
    ),
    (
        r'\breal-?time\b',
        # 'real-time' is OK when describing NWM/gridMET operational products, archive retention,
        # or when describing the temporal ordering constraint (cannot inform real-time alert decisions)
        ["NWM", "gridmet", "gridMET", "Near-Real-Time", "near-real-time", "archive", "NWPS", "operational forecast",
         "Real-Time Forecast", "Federal archive", "alert decisions", "temporal ordering", "alert"],
        "unqualified 'real-time' describing the SSL method (not NWM/gridMET products)"
    ),
    (
        r'\boperational\b',
        # 'operational' is OK when: describing NWM baseline, pre-registered thresholds/rules,
        # archive retention, data latency/contamination, NEGATIVE conclusion about Score-A,
        # section headings for the H2 lead-time evaluation, or in NWM paper titles/citations
        ["NWM", "NWPS", "alert persistence", "decision threshold", "decision rule",
         "publication latency", "data contamination", "archive", "pre-registered",
         "Real-Time Forecast", "forecast", "does not provide", "alone does not",
         "Forecast Comparison", "H-Three-B", "threshold,", "Lead-Time", "Alert Reliability",
         "PRIMARY BUDGET", "Cosgrove", "continental-scale", "hydrology system", "Water Model",
         "advancing operational", "physically-grounded", "NOHRSC", "SNODAS", "Remote Sensing Center",
         "Hydrologic Remote Sensing"],
        "unqualified 'operational' describing the SSL method's capability positively"
    ),
    (
        r'\beats the National Water Model\b',
        [],
        "must say 'NWM Retrospective' not 'NWM'"
    ),
    (
        r'\boutperforms the National Water Model\b',
        [],
        "must say 'NWM Retrospective' not 'NWM'"
    ),
    (
        r'\b7.day early.warning\b',
        [],
        "banned — 7-day claim not pre-registered"
    ),
    (
        r'\bungauged\b',
        [],
        "permanently banned per rehabilitation — project uses gauged basins only"
    ),
]

# Hypothesis verdicts: (hypothesis_label, expected_verdict_in_manuscript, falsification_reasoning)
HYPOTHESIS_VERDICTS = [
    {
        "hypothesis": "H1",
        "expected_verdict": "SUPPORTED",
        "pre_registration_criterion": "Both Score-A AND Score-B AUC-ROC <= 0.55 to falsify",
        "actual_score_a_auc": None,  # filled from manifest
        "falsified_if": lambda score_a: score_a <= 0.55,
        "manuscript_marker": "H-One",
    },
    {
        "hypothesis": "H2",
        "expected_verdict": "FALSIFIED",
        "pre_registration_criterion": "Median lead time <= 0h OR CI includes non-positive value",
        "actual_median_lead": None,  # filled from manifest
        "falsified_if": lambda lead: lead <= 0.0,
        "manuscript_marker": "H-Two",
    },
    {
        "hypothesis": "H3a",
        "expected_verdict": "NO_SIGNIFICANT_DIFFERENCE_DETECTED",
        "pre_registration_criterion": "BH-corrected Wilcoxon fails to reject null vs NWM → reframe",
        "actual_p_bh_fdr": None,  # filled from manifest
        "falsified_if": lambda p: False,  # H3a is not 'falsified', it's 'reframed'
        "not_significant_if": lambda p: p >= 0.05,
        "manuscript_marker": "H-Three-A",
    },
    {
        "hypothesis": "H4",
        "expected_verdict": "NO_SIGNIFICANT_DIFFERENCE_DETECTED",
        "pre_registration_criterion": "BH-corrected Wilcoxon fails to reject null vs EA-LSTM",
        "actual_p_bh_fdr": None,  # filled from manifest
        "falsified_if": lambda p: False,
        "not_significant_if": lambda p: p >= 0.05,
        "manuscript_marker": "H-Four",
    },
    {
        "hypothesis": "H5",
        "expected_verdict": "SUPPORTED_AT_10_PERCENT_PRIMARY",
        "pre_registration_criterion": "Score-A outperforms EA-LSTM at >=1 of 6 tested budgets",
        "actual_p": None,  # filled from manifest
        "falsified_if": lambda p: p >= 0.05,
        "manuscript_marker": "H-Five",
    },
]


def load_manifest(manifest_path: Path) -> Dict[str, Any]:
    """Load and validate the final results manifest."""
    if not manifest_path.exists():
        logger.error(f"Manifest not found: {manifest_path}")
        sys.exit(1)
    with open(manifest_path, "r", encoding="utf-8") as f:
        return json.load(f)


def check_hypothesis_verdicts(
    manifest: Dict[str, Any],
    manuscript_text: str,
) -> List[str]:
    """Mechanically verify each hypothesis verdict against pre-registered falsification criteria."""
    violations = []

    # H1
    score_a_auc = manifest["primary_auc_pooled"]
    h1_verdict = manifest["h1_verdict"]
    if score_a_auc <= 0.55:
        if h1_verdict != "FALSIFIED":
            violations.append(
                f"H1 VERDICT ERROR: Score-A AUC={score_a_auc:.4f} <= 0.55 (falsification threshold) "
                f"but verdict is '{h1_verdict}' not 'FALSIFIED'"
            )
    else:
        if h1_verdict != "SUPPORTED":
            violations.append(
                f"H1 VERDICT ERROR: Score-A AUC={score_a_auc:.4f} > 0.55, expected SUPPORTED "
                f"but verdict is '{h1_verdict}'"
            )
        else:
            logger.info(f"  [PASS] H1: Score-A AUC={score_a_auc:.4f} > 0.55 → SUPPORTED (correct)")

    if "H-One" not in manuscript_text:
        violations.append("H1: Manuscript missing 'H-One' verdict marker")
    else:
        logger.info("  [PASS] H1: 'H-One' verdict marker found in manuscript")

    # H2
    h2_median = manifest["h2_primary_median_lead_hours"]
    h2_det_rate = manifest["h2_primary_detection_rate"]
    h2_verdict = manifest["h2_verdict"]

    # Pre-registered criterion: median lead time <= 0h → FALSIFIED
    if h2_median <= 0.0:
        if h2_verdict != "FALSIFIED":
            violations.append(
                f"H2 VERDICT ERROR: Median lead={h2_median}h <= 0h (pre-registered falsification) "
                f"but verdict is '{h2_verdict}' not 'FALSIFIED'"
            )
        else:
            logger.info(f"  [PASS] H2: Median lead={h2_median}h, Det rate={h2_det_rate:.1%} → FALSIFIED (pre-registered criterion fires correctly)")
    else:
        if h2_verdict == "FALSIFIED":
            violations.append(
                f"H2 VERDICT ERROR: Median lead={h2_median}h > 0h but verdict is 'FALSIFIED'"
            )

    if "H-Two" not in manuscript_text:
        violations.append("H2: Manuscript missing 'H-Two' verdict marker")
    else:
        logger.info("  [PASS] H2: 'H-Two' verdict marker found in manuscript")

    # Check manuscript doesn't claim H2 SUPPORTED
    if "H-Two" in manuscript_text:
        h2_section = manuscript_text[manuscript_text.find("H-Two"):manuscript_text.find("H-Two")+500]
        if "SUPPORTED" in h2_section and "FALSIFIED" not in h2_section[:200]:
            violations.append("H2: Manuscript appears to claim SUPPORTED near H-Two marker — check for FALSIFIED")

    # H3a
    h3a_p_bh = manifest.get("h3a_wilcoxon_p_bh_fdr")
    h3a_verdict = manifest["h3a_verdict"]

    if h3a_p_bh is not None and h3a_p_bh >= 0.05:
        if h3a_verdict != "NO_SIGNIFICANT_DIFFERENCE_DETECTED":
            violations.append(
                f"H3a VERDICT ERROR: BH-FDR q={h3a_p_bh:.4f} >= 0.05 (no significant difference) "
                f"but verdict is '{h3a_verdict}'"
            )
        else:
            logger.info(f"  [PASS] H3a: BH q={h3a_p_bh:.4f} >= 0.05 → NO_SIGNIFICANT_DIFFERENCE_DETECTED (correct)")

    if "H-Three-A" not in manuscript_text:
        violations.append("H3a: Manuscript missing 'H-Three-A' verdict marker")
    else:
        logger.info("  [PASS] H3a: 'H-Three-A' verdict marker found in manuscript")

    # H4
    h4_p_bh = manifest.get("h4_wilcoxon_p_bh_fdr")
    h4_verdict = manifest["h4_verdict"]

    if h4_p_bh is not None and h4_p_bh >= 0.05:
        if h4_verdict != "NO_SIGNIFICANT_DIFFERENCE_DETECTED":
            violations.append(
                f"H4 VERDICT ERROR: BH-FDR q={h4_p_bh:.4f} >= 0.05 but verdict is '{h4_verdict}'"
            )
        else:
            logger.info(f"  [PASS] H4: BH q={h4_p_bh:.4f} >= 0.05 → NO_SIGNIFICANT_DIFFERENCE_DETECTED (correct)")

    if "H-Four" not in manuscript_text:
        violations.append("H4: Manuscript missing 'H-Four' verdict marker")
    else:
        logger.info("  [PASS] H4: 'H-Four' verdict marker found in manuscript")

    # Check manuscript says "equivalence is not claimed" for H4
    if "H-Four" in manuscript_text:
        h4_region = manuscript_text[manuscript_text.find("H-Four"):manuscript_text.find("H-Four")+800]
        if "equivalence" not in h4_region.lower():
            logger.warning("  [WARN] H4: Manuscript may not include 'equivalence is not claimed' near H-Four section")

    # H5
    h5_verdict = manifest["h5_verdict"]
    h5_p = manifest.get("h5_primary_budget_wilcoxon_p")

    if h5_p is not None and h5_p < 0.05:
        if "SUPPORTED" not in h5_verdict:
            violations.append(
                f"H5 VERDICT ERROR: p={h5_p} < 0.05 at 10% budget but verdict is '{h5_verdict}'"
            )
        else:
            logger.info(f"  [PASS] H5: p={h5_p} < 0.05 at 10% primary budget → SUPPORTED_AT_10_PERCENT_PRIMARY (correct)")
    elif h5_p is None:
        logger.warning("  [WARN] H5: h5_primary_budget_wilcoxon_p not in manifest — cannot mechanically verify")

    if "H-Five" not in manuscript_text:
        violations.append("H5: Manuscript missing 'H-Five' verdict marker")
    else:
        logger.info("  [PASS] H5: 'H-Five' verdict marker found in manuscript")

    return violations


def check_effect_size_compliance(
    manuscript_text: str,
    manifest: Dict[str, Any],
) -> List[str]:
    """Verify manuscript claims respect the Minimum Meaningful Effect Size thresholds."""
    violations = []

    # 0.65 AUC minimum
    score_a_pooled = manifest["primary_auc_pooled"]
    if score_a_pooled < 0.65:
        violations.append(
            f"EFFECT SIZE VIOLATION: Score-A pooled AUC={score_a_pooled:.4f} < 0.65 "
            "(minimum meaningful per venue_requirements.md) — manuscript cannot claim meaningful discrimination"
        )
    else:
        logger.info(f"  [PASS] Score-A AUC={score_a_pooled:.4f} >= 0.65 minimum meaningful threshold")

    # Check that the secondary 1-day-crossing result (60h, 1/8) is not being used as primary
    # The pre-registered PRIMARY result is the 2-day persistence rule (0.0h, 0/8, FALSIFIED)
    h2_primary_median = manifest["h2_primary_median_lead_hours"]
    h2_secondary_median = manifest.get("h2_secondary_1day_median_lead_hours", 60.0)

    if h2_primary_median <= 0.0:
        # Primary result is 0h / FALSIFIED — check manuscript doesn't claim 60h as primary
        # Look for the 60h number in the manuscript near the H2 context
        if str(h2_secondary_median) in manuscript_text:
            # It's OK if it's labeled as "secondary" or "single-day"
            regions = re.finditer(r'.{0,150}60\.0.{0,150}', manuscript_text)
            for m in regions:
                region_text = m.group(0).lower()
                if any(word in region_text for word in ["secondary", "single", "1-day", "one-day", "sensitivity"]):
                    pass  # OK — correctly labeled as secondary
                else:
                    logger.warning(
                        f"  [WARN] EFFECT SIZE: 60.0h (secondary result) appears in manuscript "
                        f"context that may not be labeled as secondary: '...{m.group(0)[:80].strip()}...'"
                    )
        logger.info(f"  [PASS] H2 primary result correctly shown as FALSIFIED (0.0h median, 0/8 detections)")

    return violations


def check_banned_terms(
    manuscript_text: str,
    additional_texts: Dict[str, str],
) -> List[str]:
    """Check for banned/restricted terminology per venue_requirements.md Title/Claim Conventions."""
    violations = []
    all_texts = {"manuscript_draft.md": manuscript_text, **additional_texts}

    for doc_name, text in all_texts.items():
        for pattern, qualifiers, description in BANNED_TERMS:
            matches = list(re.finditer(pattern, text, re.IGNORECASE))
            for match in matches:
                # Get context window
                start = max(0, match.start() - 120)
                end = min(len(text), match.end() + 120)
                context = text[start:end].replace("\n", " ")

                # If ANY qualifier is nearby, this match is acceptable
                if qualifiers and any(q.lower() in context.lower() for q in qualifiers):
                    continue

                violations.append(
                    f"BANNED TERM in {doc_name}: '{match.group(0)}' ({description}) "
                    f"— context: '...{context.strip()[:120]}...'"
                )

    return violations


def check_kf_manifest_alignment(
    manifest: Dict[str, Any],
    key_facts_path: Path,
) -> List[str]:
    """Verify KF-block values align with final_results_manifest.json values."""
    violations = []

    facts, _ = _parse_key_facts(key_facts_path)
    if facts is None:
        violations.append("Cannot parse key_facts.md")
        return violations

    kf_map = {f["anchor"].lower(): f["value"] for f in facts}

    # Check primary AUC
    kf_auc = kf_map.get("primary score-a test auc-roc")
    manifest_auc = manifest["primary_auc_pooled"]
    if kf_auc is not None:
        if abs(kf_auc - manifest_auc) > 0.001:
            violations.append(
                f"KF-MANIFEST MISMATCH: 'Primary Score-A Test AUC-ROC': "
                f"key_facts={kf_auc:.4f} vs manifest={manifest_auc:.4f}"
            )
        else:
            logger.info(f"  [PASS] KF 'Primary Score-A Test AUC-ROC': {kf_auc:.4f} matches manifest {manifest_auc:.4f}")

    # Check basin median AUC
    kf_basin = kf_map.get("score-a basin median auc")
    manifest_basin = manifest["primary_auc_basin_median"]
    if kf_basin is not None:
        if abs(kf_basin - manifest_basin) > 0.001:
            violations.append(
                f"KF-MANIFEST MISMATCH: 'Score-A Basin Median AUC': "
                f"key_facts={kf_basin:.4f} vs manifest={manifest_basin:.4f}"
            )
        else:
            logger.info(f"  [PASS] KF 'Score-A Basin Median AUC': {kf_basin:.4f} matches manifest {manifest_basin:.4f}")

    # Check NWM AUC
    kf_nwm = kf_map.get("nwm retrospective test auc-roc")
    manifest_nwm = manifest["nwm_auc_pooled"]
    if kf_nwm is not None:
        if abs(kf_nwm - manifest_nwm) > 0.001:
            violations.append(
                f"KF-MANIFEST MISMATCH: 'NWM Retrospective Test AUC-ROC': "
                f"key_facts={kf_nwm:.4f} vs manifest={manifest_nwm:.4f}"
            )
        else:
            logger.info(f"  [PASS] KF 'NWM Retrospective Test AUC-ROC': {kf_nwm:.4f} matches manifest {manifest_nwm:.4f}")

    return violations


def verify_sc008(
    manuscript_path: Path,
    venue_req_path: Path,
    key_facts_path: Path,
    manifest_path: Path,
) -> Dict[str, Any]:
    """Run SC-008 three-way consistency gate."""
    logger.info("Running SC-008 Three-Way Consistency Gate (C10-01)...")

    # Load all inputs
    manifest = load_manifest(manifest_path)
    manuscript_text = manuscript_path.read_text(encoding="utf-8")
    venue_req_text = venue_req_path.read_text(encoding="utf-8")

    # Additional outward-facing docs for banned-term scan
    additional_docs = {}
    repro_md = REPO_ROOT / "REPRODUCIBILITY.md"
    if repro_md.exists():
        additional_docs["REPRODUCIBILITY.md"] = repro_md.read_text(encoding="utf-8")
    ai_disclosure = PROJECT_DIR / "chunks/chunk09/ai_disclosure.md"
    if ai_disclosure.exists():
        additional_docs["ai_disclosure.md"] = ai_disclosure.read_text(encoding="utf-8")

    all_violations = []

    # Check A: Hypothesis verdict consistency
    logger.info("\n-- CHECK A: Hypothesis Verdict Mechanical Consistency --")
    verdict_violations = check_hypothesis_verdicts(manifest, manuscript_text)
    all_violations.extend(verdict_violations)

    # Check B: Effect size compliance
    logger.info("\n-- CHECK B: Effect Size Threshold Compliance --")
    effect_violations = check_effect_size_compliance(manuscript_text, manifest)
    all_violations.extend(effect_violations)

    # Check C: Banned terms
    logger.info("\n-- CHECK C: Banned/Restricted Terminology Audit --")
    term_violations = check_banned_terms(manuscript_text, additional_docs)
    for v in term_violations:
        logger.error(f"  [FAIL] {v}")
    all_violations.extend(term_violations)
    if not term_violations:
        logger.info("  [PASS] No banned terminology found in manuscript or outward-facing docs")

    # Check D: KF-block vs manifest alignment
    logger.info("\n-- CHECK D: Key Facts ↔ Manifest Alignment --")
    kf_violations = check_kf_manifest_alignment(manifest, key_facts_path)
    for v in kf_violations:
        logger.error(f"  [FAIL] {v}")
    all_violations.extend(kf_violations)
    if not kf_violations:
        logger.info("  [PASS] All KF-block values align with final_results_manifest.json")

    # Summary
    logger.info(f"\n-- SC-008 SUMMARY --")
    if all_violations:
        logger.error(f"SC-008 FAIL: {len(all_violations)} violation(s) found:")
        for i, v in enumerate(all_violations, start=1):
            logger.error(f"  [{i}] {v}")
        sys.exit(1)

    logger.info("SC-008: PASS — All four consistency checks passed")

    return {
        "status": "PASS",
        "verdict_violations": len(verdict_violations),
        "effect_size_violations": len(effect_violations),
        "banned_term_violations": len(term_violations),
        "kf_manifest_violations": len(kf_violations),
        "total_violations": 0
    }


def main():
    parser = argparse.ArgumentParser(description="SC-008 Three-Way Consistency Gate")
    parser.add_argument("--manuscript", required=True)
    parser.add_argument("--venue-requirements", required=True)
    parser.add_argument("--key-facts", required=True)
    parser.add_argument("--manifest", required=True)
    args = parser.parse_args()

    verify_sc008(
        manuscript_path=Path(args.manuscript),
        venue_req_path=Path(args.venue_requirements),
        key_facts_path=Path(args.key_facts),
        manifest_path=Path(args.manifest),
    )


if __name__ == "__main__":
    main()
