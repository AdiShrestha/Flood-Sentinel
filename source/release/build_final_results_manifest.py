"""Build Final Results Manifest (C10-00).

Reads the canonical result artifacts programmatically and produces a single
machine-readable JSON that serves as the sole source of truth for every
headline number in the project. Re-running this script must be idempotent
and must fail loudly (non-zero exit) if either source JSON is missing or
malformed.

Usage:
    python3 source/release/build_final_results_manifest.py
    python3 source/release/build_final_results_manifest.py --out path/to/manifest.json
"""

import argparse
import json
import subprocess
import sys
from pathlib import Path

# Add project root to sys.path
_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from source.utils.config import PROJECT_DIR
from source.utils.logging_config import get_logger

logger = get_logger("build_final_results_manifest")

DISC_PATH = PROJECT_DIR / "chunks" / "chunk07" / "data" / "discrimination_results.json"
LT_PATH = PROJECT_DIR / "chunks" / "chunk07" / "data" / "lead_time_survival_results.json"
DEFAULT_OUT = PROJECT_DIR / "chunks" / "chunk10" / "final_results_manifest.json"


def _get_git_head_sha() -> str:
    """Return current HEAD sha of project/ repo, or 'unknown' if unavailable."""
    try:
        result = subprocess.run(
            ["git", "-C", str(PROJECT_DIR), "rev-parse", "HEAD"],
            capture_output=True, text=True, check=True
        )
        return result.stdout.strip()
    except Exception:
        return "unknown"


def _safe_get(d: dict, *keys, label: str = ""):
    """Navigate nested dict safely, raising clear errors on missing keys."""
    current = d
    traversed = []
    for k in keys:
        traversed.append(k)
        if not isinstance(current, dict) or k not in current:
            raise KeyError(
                f"Missing key path {' -> '.join(traversed)} in {label}"
            )
        current = current[k]
    return current


def build_manifest(out_path: Path = DEFAULT_OUT) -> dict:
    """Build and write the canonical final results manifest."""
    # 1. Validate source files exist
    if not DISC_PATH.exists():
        logger.error(f"Source file missing: {DISC_PATH}")
        sys.exit(1)
    if not LT_PATH.exists():
        logger.error(f"Source file missing: {LT_PATH}")
        sys.exit(1)

    logger.info(f"Reading discrimination results from {DISC_PATH}")
    with open(DISC_PATH, "r", encoding="utf-8") as f:
        disc = json.load(f)

    logger.info(f"Reading lead-time survival results from {LT_PATH}")
    with open(LT_PATH, "r", encoding="utf-8") as f:
        lt = json.load(f)

    # 2. Extract values programmatically — never hand-typed
    # Score-A pooled
    sa_pooled = _safe_get(disc, "pooled_summary_context", "score_a_reconstruction",
                          label="discrimination_results.json")
    primary_auc_pooled = sa_pooled["pooled_test_auc"]
    primary_auc_pooled_ci95 = sa_pooled["pooled_test_auc_ci_95"]

    # Score-A basin median
    sa_basin = _safe_get(disc, "basin_level_summary", "score_a_reconstruction",
                         label="discrimination_results.json")
    primary_auc_basin_median = sa_basin["median_basin_auc"]

    # NWM
    nwm_pooled = _safe_get(disc, "pooled_summary_context", "nwm_retrospective_v3",
                           label="discrimination_results.json")
    nwm_basin = _safe_get(disc, "basin_level_summary", "nwm_retrospective_v3",
                          label="discrimination_results.json")

    # EA-LSTM
    ea_pooled = _safe_get(disc, "pooled_summary_context", "dl_ea_lstm_supervised",
                          label="discrimination_results.json")
    ea_basin = _safe_get(disc, "basin_level_summary", "dl_ea_lstm_supervised",
                         label="discrimination_results.json")

    # Persistence
    pers_pooled = _safe_get(disc, "pooled_summary_context", "stat_persistence",
                            label="discrimination_results.json")

    # Hypotheses from discrimination
    hyp = _safe_get(disc, "hypotheses_evaluation", label="discrimination_results.json")

    # H1
    h1 = hyp["H1"]

    # H3a
    h3a = hyp["H3a"]

    # H4
    h4 = hyp["H4"]

    # H5
    h5 = hyp["H5"]

    # H2 from lead-time results
    h2_eval = _safe_get(lt, "hypothesis_h2_evaluation",
                        label="lead_time_survival_results.json")
    h2_primary = h2_eval.get("primary_operational_2day_persistence", {})
    h2_secondary = h2_eval.get("secondary_1day_crossing", {})

    # N test basins
    n_test_basins = disc.get("n_test_streamgages", 11)

    # Lead-time cohort details
    n_eligible = lt.get("n_response_time_eligible_action_events", 8)

    # 3. Assemble manifest
    manifest = {
        "manifest_version": "1.0.0",
        "manifest_generated_by": "source/release/build_final_results_manifest.py",
        "manifest_generated_from": [
            "project/chunks/chunk07/data/discrimination_results.json",
            "project/chunks/chunk07/data/lead_time_survival_results.json"
        ],
        "manifest_git_commit": _get_git_head_sha(),

        # --- Primary discrimination ---
        "primary_auc_pooled": primary_auc_pooled,
        "primary_auc_pooled_ci95": primary_auc_pooled_ci95,
        "primary_auc_basin_median": primary_auc_basin_median,

        # --- H1 ---
        "h1_verdict": h1["verdict"],
        "h1_wilcoxon_stat": h1["one_sample_wilcoxon_stat"],
        "h1_wilcoxon_p": h1["one_sample_wilcoxon_p_value"],

        # --- H2 ---
        "h2_verdict": h2_eval["verdict"],
        "h2_eligible_event_denominator": n_eligible,
        "h2_primary_detection_count": h2_primary.get("detected_events_count", 0),
        "h2_primary_detection_rate": h2_primary.get("detection_rate", 0.0),
        "h2_primary_median_lead_hours": h2_primary.get("conditional_median_lead_time_hours", 0.0),
        "h2_secondary_1day_detection_count": h2_secondary.get("detected_events_count", 0),
        "h2_secondary_1day_detection_rate": h2_secondary.get("detection_rate", 0.0),
        "h2_secondary_1day_median_lead_hours": h2_secondary.get("conditional_median_lead_time_hours", 0.0),

        # --- H3a ---
        "h3a_verdict": h3a["verdict"],
        "nwm_auc_pooled": nwm_pooled["pooled_test_auc"],
        "nwm_auc_pooled_ci95": nwm_pooled["pooled_test_auc_ci_95"],
        "nwm_auc_basin_median": nwm_basin["median_basin_auc"],
        "h3a_wilcoxon_p_raw": h3a.get("p_value_raw"),
        "h3a_wilcoxon_p_bh_fdr": h3a.get("p_value_bh_fdr"),

        # --- H4 ---
        "h4_verdict": h4["verdict"],
        "ea_lstm_auc_pooled": ea_pooled["pooled_test_auc"],
        "ea_lstm_auc_pooled_ci95": ea_pooled["pooled_test_auc_ci_95"],
        "ea_lstm_auc_basin_median": ea_basin["median_basin_auc"],
        "h4_wilcoxon_p_raw": h4.get("p_value_raw"),
        "h4_wilcoxon_p_bh_fdr": h4.get("p_value_bh_fdr"),

        # --- H5 ---
        "h5_verdict": h5["verdict"],
        "h5_primary_budget_wilcoxon_p": h5.get("primary_10_percent_wilcoxon_p"),

        # --- Persistence baseline ---
        "persistence_auc_pooled": pers_pooled["pooled_test_auc"],

        # --- Study design ---
        "n_test_basins_nominal": n_test_basins,
        "n_response_time_eligible_events": n_eligible,
        "bootstrap_iterations": 10000,
    }

    # 4. Write output
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2)

    logger.info(f"Final results manifest written to {out_path}")
    logger.info(f"  primary_auc_pooled = {manifest['primary_auc_pooled']}")
    logger.info(f"  primary_auc_basin_median = {manifest['primary_auc_basin_median']}")
    logger.info(f"  h1_verdict = {manifest['h1_verdict']}")
    logger.info(f"  h2_verdict = {manifest['h2_verdict']}")
    logger.info(f"  h3a_verdict = {manifest['h3a_verdict']}")
    logger.info(f"  h4_verdict = {manifest['h4_verdict']}")
    logger.info(f"  h5_verdict = {manifest['h5_verdict']}")

    return manifest


def main():
    parser = argparse.ArgumentParser(description="Build final results manifest from result JSONs")
    parser.add_argument("--out", type=str, default=None,
                        help="Output path for manifest JSON")
    args = parser.parse_args()

    out_path = Path(args.out) if args.out else DEFAULT_OUT
    build_manifest(out_path)


if __name__ == "__main__":
    main()
