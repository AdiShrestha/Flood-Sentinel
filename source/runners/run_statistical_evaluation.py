#!/usr/bin/env python3
"""Statistical evaluation and scientific failure analysis runner.

Executes independent statistical inference, multiplicity adjustment,
Brier score partitioning, and failure taxonomy across all runs in the
active epoch.
"""
from __future__ import annotations

import csv
import json
import math
from pathlib import Path
import sys
from typing import Any

SOURCE_DIR = Path(__file__).resolve().parents[1]
if str(SOURCE_DIR) not in sys.path:
    sys.path.insert(0, str(SOURCE_DIR))

import numpy as np

from flood_sentinel.adapters.recompute import recompute_binary_metrics
from flood_sentinel.calibration import compute_calibration_curve, decompose_brier_score
from flood_sentinel.lead_time import evaluate_warning_lead_times
from flood_sentinel.statistical_analysis import (
    apply_holm_stepdown,
    compute_paired_contrast,
    evaluate_model_failures,
)


import os


def find_active_runs_dir(root: Path, explicit_runs_dir: Path | str | None = None) -> Path:
    """Find active experiment runs directory."""
    if explicit_runs_dir is not None:
        p = Path(explicit_runs_dir).resolve()
        if p.is_dir():
            return p
        raise FileNotFoundError(f"Specified runs-dir does not exist: {p}")

    env_dir = os.environ.get("RUNS_DIR")
    if env_dir:
        p = Path(env_dir).resolve()
        if p.is_dir():
            return p

    candidates: list[Path] = []
    for cand_name in ["outputs", "runs", "project"]:
        cand = root / cand_name
        if cand.is_dir():
            for sub in cand.rglob("runs"):
                if sub.is_dir() and any(sub.iterdir()):
                    candidates.append(sub)

    if candidates:
        candidates.sort(key=lambda p: str(p))
        return candidates[-1]

    raise FileNotFoundError("Could not locate execution runs directory. Specify via RUNS_DIR.")


def run_statistical_evaluation(root_dir: Path | None = None) -> dict[str, Any]:
    root = (root_dir or Path.cwd()).resolve()
    runs_dir = find_active_runs_dir(root)
    cohort_path = root / "data/cohort.csv"
    events_path = root / "data/event_intervals.csv"

    # 1. Load cohort metadata
    with cohort_path.open(encoding="utf-8") as f:
        cohort_rows = list(csv.DictReader(f))
    cohort_by_id = {r["sample_id"]: r for r in cohort_rows}
    test_sample_ids = [r["sample_id"] for r in cohort_rows if r["split"] == "test"]
    val_sample_ids = [r["sample_id"] for r in cohort_rows if r["split"] == "validation"]
    eval_sample_ids = val_sample_ids + test_sample_ids

    # 2. Discover all runs and parse predictions
    run_folders = sorted(runs_dir.glob("exp_*"))
    if not run_folders:
        raise FileNotFoundError(f"No experiment folders found in {runs_dir}")

    all_runs_data: list[dict[str, Any]] = []
    matrix_rows: list[dict[str, Any]] = []

    for run_folder in run_folders:
        exp_id = run_folder.name
        attempt_dirs = sorted(run_folder.glob("attempt*"))
        if not attempt_dirs:
            continue
        attempt_dir = attempt_dirs[-1]
        pred_file = attempt_dir / "predictions.csv"
        result_file = attempt_dir / "result.json"
        if not pred_file.is_file() or not result_file.is_file():
            continue

        result_meta = json.loads(result_file.read_text(encoding="utf-8"))
        with pred_file.open(encoding="utf-8") as f:
            preds_raw = list(csv.DictReader(f))

        pred_dict = {r["sample_id"]: float(r["score"]) for r in preds_raw}
        split_dict = {r["sample_id"]: cohort_by_id[r["sample_id"]]["split"] for r in preds_raw}
        label_dict = {r["sample_id"]: int(r["label"]) for r in preds_raw}

        # Test set predictions
        test_y = [label_dict[sid] for sid in test_sample_ids]
        test_p = [pred_dict[sid] for sid in test_sample_ids]

        # Discrimination metrics
        discrim = recompute_binary_metrics(test_y, test_p, threshold=0.5)

        # Calibration metrics
        brier = decompose_brier_score(test_y, test_p, n_bins=5)
        curve = compute_calibration_curve(test_y, test_p, n_bins=5)

        # Lead time analysis
        lead_summary = evaluate_warning_lead_times(preds_raw, events_path, threshold=0.5)

        model_family = result_meta.get("config", {}).get("family", exp_id.split("_s")[0].replace("exp_", ""))
        seed = int(result_meta.get("seed", 42))

        run_info = {
            "experiment_id": exp_id,
            "model_family": model_family,
            "seed": seed,
            "discrimination": discrim,
            "brier_decomposition": brier.to_dict(),
            "calibration_error": {
                "ece": curve.expected_calibration_error,
                "mce": curve.maximum_calibration_error,
                "rmsce": curve.root_mean_squared_calibration_error,
            },
            "lead_time": lead_summary.to_dict(),
            "test_predictions": {sid: pred_dict[sid] for sid in test_sample_ids},
        }
        all_runs_data.append(run_info)

        # Add to sample-level matrix
        for sid in eval_sample_ids:
            matrix_rows.append({
                "experiment_id": exp_id,
                "model_family": model_family,
                "seed": seed,
                "sample_id": sid,
                "split": split_dict.get(sid, cohort_by_id[sid]["split"]),
                "group_id": cohort_by_id[sid]["group_id"],
                "ground_truth": label_dict.get(sid, int(cohort_by_id[sid]["label"])),
                "predicted_probability": pred_dict[sid],
                "predicted_binary": 1 if pred_dict[sid] >= 0.5 else 0,
            })

    # 3. Model family aggregation
    families = sorted(list({r["model_family"] for r in all_runs_data}))
    family_aggregates: dict[str, Any] = {}

    for fam in families:
        fam_runs = [r for r in all_runs_data if r["model_family"] == fam]
        n_fam = len(fam_runs)

        ap_list = [r["discrimination"]["average_precision"] for r in fam_runs]
        auroc_list = [r["discrimination"]["auroc"] for r in fam_runs]
        brier_list = [r["discrimination"]["brier"] for r in fam_runs]
        bss_list = [r["brier_decomposition"]["brier_skill_score"] for r in fam_runs]
        rel_list = [r["brier_decomposition"]["reliability"] for r in fam_runs]
        res_list = [r["brier_decomposition"]["resolution"] for r in fam_runs]
        ece_list = [r["calibration_error"]["ece"] for r in fam_runs]
        mce_list = [r["calibration_error"]["mce"] for r in fam_runs]
        lead_list = [r["lead_time"]["mean_lead_time_hours"] for r in fam_runs if r["lead_time"]["mean_lead_time_hours"] is not None]
        false_alert_list = [r["lead_time"]["false_alert_rate"] for r in fam_runs]

        family_aggregates[fam] = {
            "n_runs": n_fam,
            "average_precision": {"mean": float(np.mean(ap_list)), "std": float(np.std(ap_list, ddof=1)) if n_fam > 1 else 0.0},
            "auroc": {"mean": float(np.mean(auroc_list)), "std": float(np.std(auroc_list, ddof=1)) if n_fam > 1 else 0.0},
            "brier_score": {"mean": float(np.mean(brier_list)), "std": float(np.std(brier_list, ddof=1)) if n_fam > 1 else 0.0},
            "brier_skill_score": {"mean": float(np.mean(bss_list)), "std": float(np.std(bss_list, ddof=1)) if n_fam > 1 else 0.0},
            "reliability_rel": {"mean": float(np.mean(rel_list)), "std": float(np.std(rel_list, ddof=1)) if n_fam > 1 else 0.0},
            "resolution_res": {"mean": float(np.mean(res_list)), "std": float(np.std(res_list, ddof=1)) if n_fam > 1 else 0.0},
            "expected_calibration_error": {"mean": float(np.mean(ece_list)), "std": float(np.std(ece_list, ddof=1)) if n_fam > 1 else 0.0},
            "maximum_calibration_error": {"mean": float(np.mean(mce_list)), "std": float(np.std(mce_list, ddof=1)) if n_fam > 1 else 0.0},
            "mean_advance_lead_hours": {"mean": float(np.mean(lead_list)) if lead_list else None, "std": float(np.std(lead_list, ddof=1)) if len(lead_list) > 1 else 0.0},
            "false_alert_rate": {"mean": float(np.mean(false_alert_list)), "std": float(np.std(false_alert_list, ddof=1)) if n_fam > 1 else 0.0},
        }

    # 4. Paired Seed Contrasts vs Baselines (Holm Family Multiplicity)
    # We compare causal_forecasting_head against the 4 recognized baseline families across common seeds
    common_seeds = [42, 100, 2026, 31415, 99999]
    baseline_targets = ["persistence", "ewma_cusum", "tabular_ridge", "ea_lstm"]
    contrasts: list[Any] = []

    causal_by_seed = {r["seed"]: r for r in all_runs_data if r["model_family"] == "causal_forecasting_head" and r["seed"] in common_seeds}

    for b_target in baseline_targets:
        base_by_seed = {r["seed"]: r for r in all_runs_data if r["model_family"] == b_target and r["seed"] in common_seeds}
        if len(causal_by_seed) == 5 and len(base_by_seed) == 5:
            scores_c = [causal_by_seed[s]["discrimination"]["average_precision"] for s in common_seeds]
            scores_b = [base_by_seed[s]["discrimination"]["average_precision"] for s in common_seeds]
            cid = f"cmp_causal_vs_{b_target}"
            contrast = compute_paired_contrast(
                comparison_id=cid,
                model_a="causal_forecasting_head",
                model_b=b_target,
                scores_a=scores_c,
                scores_b=scores_b,
                metric_name="average_precision",
                alpha=0.05,
                inference_scope="fixed_test_corpus",
            )
            contrasts.append(contrast)

    # Apply Holm step-down correction
    holm_adjusted_contrasts = apply_holm_stepdown(contrasts, alpha=0.05)

    # 5. Failure Taxonomy and Error Categorization
    failure_summaries: dict[str, Any] = {}
    for fam in families:
        fam_sample_preds: dict[str, list[float]] = {}
        fam_runs = [r for r in all_runs_data if r["model_family"] == fam]
        for sid in test_sample_ids:
            fam_sample_preds[sid] = [r["test_predictions"][sid] for r in fam_runs]

        # Use mean probability across seeds for canonical failure summary
        mean_probs = [float(np.mean(fam_sample_preds[sid])) for sid in test_sample_ids]
        test_labels = [int(cohort_by_id[sid]["label"]) for sid in test_sample_ids]
        test_groups = [cohort_by_id[sid]["group_id"] for sid in test_sample_ids]
        test_splits = ["test"] * len(test_sample_ids)

        fail_summary = evaluate_model_failures(
            model_family=fam,
            sample_ids=test_sample_ids,
            group_ids=test_groups,
            splits=test_splits,
            labels=test_labels,
            probabilities=mean_probs,
            threshold=0.5,
        )
        failure_summaries[fam] = fail_summary.to_dict()

    # 6. Materialize Outputs
    statistical_summary = {
        "schema_version": 3,
        "n_evaluated_runs": len(all_runs_data),
        "evaluation_cohort": "data/cohort.csv",
        "evaluation_split": "test",
        "n_test_samples": len(test_sample_ids),
        "climatology_uncertainty_unc": 0.2400,
        "family_aggregates": family_aggregates,
        "paired_contrasts": [c.to_dict() for c in holm_adjusted_contrasts],
    }
    (root / "project/statistical_summary.json").write_text(json.dumps(statistical_summary, indent=2), encoding="utf-8")

    failure_taxonomy_data = {
        "schema_version": 3,
        "description": "Empirical failure taxonomy and sample-level classification on fixed test split",
        "models": failure_summaries,
    }
    (root / "project/failure_taxonomy.json").write_text(json.dumps(failure_taxonomy_data, indent=2), encoding="utf-8")

    # Write sample-level CSV
    with (root / "project/sample_level_predictions.csv").open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=[
                "experiment_id",
                "model_family",
                "seed",
                "sample_id",
                "split",
                "group_id",
                "ground_truth",
                "predicted_probability",
                "predicted_binary",
            ],
        )
        writer.writeheader()
        writer.writerows(matrix_rows)

    # Figures data coordinates
    figures_data = {
        "calibration_curves": {
            fam: {
                "bin_centers": [0.1, 0.3, 0.5, 0.7, 0.9],
                "ece": family_aggregates[fam]["expected_calibration_error"]["mean"],
                "mce": family_aggregates[fam]["maximum_calibration_error"]["mean"],
                "brier_skill_score": family_aggregates[fam]["brier_skill_score"]["mean"],
            }
            for fam in families
        },
        "paired_contrast_forest_plot": [
            {
                "contrast": c.comparison_id,
                "mean_diff": c.mean_difference,
                "ci_lower": c.ci_lower,
                "ci_upper": c.ci_upper,
                "p_raw": c.p_raw,
                "p_holm": c.p_holm,
                "decision": c.decision,
            }
            for c in holm_adjusted_contrasts
        ],
        "lead_time_distributions": {
            fam: {
                "mean_lead_hours": family_aggregates[fam]["mean_advance_lead_hours"]["mean"],
                "false_alert_rate": family_aggregates[fam]["false_alert_rate"]["mean"],
            }
            for fam in families
        },
    }
    (root / "project/figures_data.json").write_text(json.dumps(figures_data, indent=2), encoding="utf-8")

    return statistical_summary


def main() -> int:
    summary = run_statistical_evaluation()
    print("Statistical evaluation completed successfully.")
    print(f"Total runs analyzed: {summary['n_evaluated_runs']}")
    print(f"Total paired contrasts: {len(summary['paired_contrasts'])}")
    for c in summary["paired_contrasts"]:
        print(f"  {c['comparison_id']}: Mean diff = {c['mean_difference']:.4f} [95% CI: {c['ci_lower']:.4f}, {c['ci_upper']:.4f}], p_raw = {c['p_raw']:.4f}, p_holm = {c['p_holm']:.4f}, decision = {c['decision']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
