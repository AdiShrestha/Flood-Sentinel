#!/usr/bin/env python3
"""Post-processing analysis runner for probability calibration, Brier decomposition, and lead-time analysis.

Executes post-processing evaluations across all verified supervisor run attempts
in the active epoch, evaluating calibration error (ECE, MCE), Murphy (1973)
Brier score decomposition (REL, RES, UNC), and advance warning lead times relative
to NOAA NWPS official flood stages.
"""
from __future__ import annotations

import argparse
import csv
from datetime import datetime, timezone
import json
import math
import os
from pathlib import Path
import sys
from typing import Any

# Ensure source is on sys.path
SOURCE_DIR = Path(__file__).resolve().parents[1]
if str(SOURCE_DIR) not in sys.path:
    sys.path.insert(0, str(SOURCE_DIR))

import numpy as np

from flood_sentinel.calibration import (
    compute_calibration_curve,
    decompose_brier_score,
)
from flood_sentinel.lead_time import evaluate_warning_lead_times


def find_latest_runs_dir(root: Path, explicit_runs_dir: Path | str | None = None) -> Path:
    """Locate the directory containing experiment run executions."""
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
        # Sort candidates to pick latest epoch or run session
        candidates.sort(key=lambda p: str(p))
        return candidates[-1]

    raise FileNotFoundError(f"No experiment run directories found under {root}")


def load_cohort_split_map(root: Path) -> dict[str, str]:
    """Map sample_id to its declared split (train, validation, test)."""
    cohort_path = root / "data/cohort.csv"
    mapping = {}
    with cohort_path.open(encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            mapping[row["sample_id"]] = row["split"]
    return mapping


def analyze_run(
    run_dir: Path,
    cohort_map: dict[str, str],
    event_intervals_path: Path,
    n_bins: int = 5,
    threshold: float = 0.5,
) -> dict[str, Any]:
    """Analyze a single executed run attempt."""
    pred_path = run_dir / "predictions.csv"
    if not pred_path.is_file():
        raise FileNotFoundError(f"Missing predictions.csv in {run_dir}")

    preds_all = []
    with pred_path.open(encoding="utf-8") as f:
        reader = csv.DictReader(f)
        preds_all = list(reader)

    # Separate by evaluation split
    val_preds = [p for p in preds_all if cohort_map.get(p["sample_id"]) == "validation"]
    test_preds = [p for p in preds_all if cohort_map.get(p["sample_id"]) == "test"]

    def evaluate_split(split_preds: list[dict[str, Any]]) -> dict[str, Any]:
        if not split_preds:
            return {}
        y_true = [float(p["label"]) for p in split_preds]
        y_prob = [float(p["score"]) for p in split_preds]

        # 1. Calibration Curve & Error
        cal_res = compute_calibration_curve(y_true, y_prob, n_bins=n_bins, strategy="uniform")

        # 2. Brier Decomposition
        brier_res = decompose_brier_score(y_true, y_prob, n_bins=n_bins, strategy="uniform")

        # 3. Lead Time Analysis
        lead_res = evaluate_warning_lead_times(
            split_preds,
            event_intervals_path,
            threshold=threshold,
            horizon_hours=24.0,
            cooldown_hours=12.0,
        )

        return {
            "n_samples": len(split_preds),
            "calibration": cal_res.to_dict(),
            "brier_decomposition": brier_res.to_dict(),
            "lead_time": lead_res.to_dict(),
        }

    return {
        "run_dir": str(run_dir),
        "validation": evaluate_split(val_preds),
        "test": evaluate_split(test_preds),
    }


def run_all_postprocessing(
    root: Path,
    runs_dir: Path | str | None = None,
    output_dir: Path | None = None,
    n_bins: int = 5,
    threshold: float = 0.5,
) -> dict[str, Any]:
    """Execute post-processing across all active runs and export summaries."""
    active_runs_dir = find_latest_runs_dir(root, runs_dir)
    cohort_map = load_cohort_split_map(root)
    event_intervals_path = root / "data/event_intervals.csv"
    out_dir = output_dir or (root / "project")

    # Discover runs
    run_folders = sorted(p for p in active_runs_dir.iterdir() if p.is_dir())
    all_results: dict[str, Any] = {}

    # Accumulators by model family for test split
    family_metrics: dict[str, dict[str, list[float]]] = {}

    for rf in run_folders:
        attempt_dir = rf / "attempt0001"
        if not attempt_dir.is_dir():
            continue
        exp_id = rf.name
        # Parse family: exp_{family}_s{seed} or exp_{family}_replay_s{seed}
        clean_name = exp_id.replace("exp_", "")
        parts = clean_name.split("_s")
        family = parts[0]
        if "_replay" in family:
            family = family.replace("_replay", "")

        res = analyze_run(
            attempt_dir,
            cohort_map,
            event_intervals_path,
            n_bins=n_bins,
            threshold=threshold,
        )
        all_results[exp_id] = {
            "family": family,
            "experiment_id": exp_id,
            "metrics": res,
        }

        # Aggregate test metrics
        test_m = res.get("test", {})
        if test_m:
            cal = test_m.get("calibration", {})
            br = test_m.get("brier_decomposition", {})
            lt = test_m.get("lead_time", {})

            if family not in family_metrics:
                family_metrics[family] = {
                    "ece": [],
                    "mce": [],
                    "rmsce": [],
                    "brier_raw": [],
                    "reliability": [],
                    "resolution": [],
                    "uncertainty": [],
                    "bss": [],
                    "mean_lead_hours": [],
                    "overall_recall": [],
                    "false_alert_rate": [],
                }

            family_metrics[family]["ece"].append(cal.get("expected_calibration_error", 0.0))
            family_metrics[family]["mce"].append(cal.get("maximum_calibration_error", 0.0))
            family_metrics[family]["rmsce"].append(cal.get("root_mean_squared_calibration_error", 0.0))
            family_metrics[family]["brier_raw"].append(br.get("brier_score_raw", 0.0))
            family_metrics[family]["reliability"].append(br.get("reliability", 0.0))
            family_metrics[family]["resolution"].append(br.get("resolution", 0.0))
            family_metrics[family]["uncertainty"].append(br.get("uncertainty", 0.0))
            family_metrics[family]["bss"].append(br.get("brier_skill_score", 0.0))
            family_metrics[family]["overall_recall"].append(lt.get("overall_event_recall", 0.0))
            family_metrics[family]["false_alert_rate"].append(lt.get("false_alert_rate", 0.0))

            mean_lead = lt.get("mean_lead_time_hours")
            if mean_lead is not None:
                family_metrics[family]["mean_lead_hours"].append(mean_lead)

    # Compute family summary statistics (mean, std)
    family_summary: dict[str, dict[str, Any]] = {}
    summary_rows: list[dict[str, Any]] = []

    for fam, metrics in sorted(family_metrics.items()):
        stats: dict[str, Any] = {"n_runs": len(metrics["ece"])}
        row: dict[str, Any] = {"model_family": fam, "n_runs": len(metrics["ece"])}

        for k, vals in metrics.items():
            if vals:
                mean_v = float(np.mean(vals))
                std_v = float(np.std(vals))
                stats[k] = {"mean": mean_v, "std": std_v}
                row[f"{k}_mean"] = round(mean_v, 4)
                row[f"{k}_std"] = round(std_v, 4)
            else:
                stats[k] = {"mean": None, "std": None}
                row[f"{k}_mean"] = None
                row[f"{k}_std"] = None

        family_summary[fam] = stats
        summary_rows.append(row)

    # Export JSON and CSV
    postproc_payload = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "n_runs_evaluated": len(all_results),
        "family_summary": family_summary,
        "runs": all_results,
    }

    cal_payload = {
        "description": "Probability calibration error and Murphy (1973) Brier score decomposition across all comparators.",
        "runs": {
            eid: {
                "family": d["family"],
                "validation_calibration": d["metrics"]["validation"].get("calibration"),
                "validation_brier": d["metrics"]["validation"].get("brier_decomposition"),
                "test_calibration": d["metrics"]["test"].get("calibration"),
                "test_brier": d["metrics"]["test"].get("brier_decomposition"),
            }
            for eid, d in all_results.items()
        },
    }

    lt_payload = {
        "description": "Advance warning lead-time and category-stratified recall relative to NOAA NWPS flood categories.",
        "runs": {
            eid: {
                "family": d["family"],
                "test_lead_time": d["metrics"]["test"].get("lead_time"),
            }
            for eid, d in all_results.items()
        },
    }

    (out_dir / "postprocessing_summary.json").write_text(json.dumps(postproc_payload, indent=2), encoding="utf-8")
    (out_dir / "calibration_report.json").write_text(json.dumps(cal_payload, indent=2), encoding="utf-8")
    (out_dir / "lead_time_report.json").write_text(json.dumps(lt_payload, indent=2), encoding="utf-8")

    # CSV summary
    if summary_rows:
        fieldnames = list(summary_rows[0].keys())
        with (out_dir / "comparator_postprocessing_summary.csv").open("w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=fieldnames)
            w.writeheader()
            w.writerows(summary_rows)

    return postproc_payload


def main() -> int:
    parser = argparse.ArgumentParser(description="Post-processing analysis runner")
    parser.add_argument("--root", default=".", help="Project root directory")
    parser.add_argument("--runs-dir", default=None, help="Directory containing experiment run folders")
    parser.add_argument("--n-bins", type=int, default=5, help="Number of calibration bins")
    parser.add_argument("--threshold", type=float, default=0.5, help="Decision threshold")
    args = parser.parse_args()

    root = Path(args.root).resolve()
    print(f"Executing post-processing analysis on {root}...")
    res = run_all_postprocessing(
        root,
        runs_dir=args.runs_dir,
        n_bins=args.n_bins,
        threshold=args.threshold,
    )
    print(f"Evaluated {res['n_runs_evaluated']} runs.")
    print("Family Summary (Test Split):")
    print(f"{'Model Family':<26} | {'ECE (mean±std)':<16} | {'Brier (mean±std)':<16} | {'REL (mean±std)':<16} | {'RES (mean±std)':<16} | {'Lead Time (h)':<14}")
    print("-" * 110)
    for fam, s in res["family_summary"].items():
        ece = f"{s['ece']['mean']:.4f}±{s['ece']['std']:.4f}"
        br = f"{s['brier_raw']['mean']:.4f}±{s['brier_raw']['std']:.4f}"
        rel = f"{s['reliability']['mean']:.4f}±{s['reliability']['std']:.4f}"
        res_v = f"{s['resolution']['mean']:.4f}±{s['resolution']['std']:.4f}"
        lt_m = s["mean_lead_hours"]["mean"]
        lt_str = f"{lt_m:.2f}h" if lt_m is not None else "N/A"
        print(f"{fam:<26} | {ece:<16} | {br:<16} | {rel:<16} | {res_v:<16} | {lt_str:<14}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
