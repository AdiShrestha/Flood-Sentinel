"""EA-LSTM Label-Budget Efficiency Sweep Engine (C06-05 / FR-019 / INV-017 / H5).

Evaluates Supervised EA-LSTM across six training label budgets ({1%, 5%, 10%, 25%, 50%, 100%})
with all budgets drawn across the five frozen seeds: {13, 47, 101, 2024, 8891} (30 runs total).
Uses SUP_HYPERPARAMETERS["epochs"] (5 epochs) matching the standalone supervised benchmark.
Evaluates EA-LSTM on the EXACT frozen test partition of `evaluation_event_matrix.parquet`
(N=520 collapsed events across 11 held-out basins) using identical `y_flood_true` targets.
The fixed self-supervised Score-A reference is stored once in the summary payload.
"""

import json
import sys
from pathlib import Path
from typing import Dict, Any, List, Tuple

import numpy as np
import pandas as pd
from sklearn.metrics import roc_auc_score, average_precision_score, f1_score, brier_score_loss
import torch
import torch.nn as nn
from torch.utils.data import DataLoader, TensorDataset

# Add project root to sys.path if running as standalone script
_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from source.baseline.baseline_sup import (
    load_static_attribute_lookup,
    load_flood_events,
    extract_tensors_and_labels,
    train_ea_lstm,
    SUP_HYPERPARAMETERS
)
from source.baseline.ea_lstm import EALSTMModel
from source.utils.config import (
    CHUNK03_DATA_DIR,
    CHUNK03_DIR,
    CHUNK06_DATA_DIR,
    CHUNK06_DIR,
    CHUNK07_DATA_DIR
)
from source.utils.logging_config import get_logger

logger = get_logger("label_budget_sweep")

LABEL_BUDGETS = [0.01, 0.05, 0.10, 0.25, 0.50, 1.00]
FROZEN_SEEDS = [13, 47, 101, 2024, 8891]


def evaluate_model_on_test_matrix(
    model: EALSTMModel,
    x_dyn_test: np.ndarray,
    x_stat_test: np.ndarray,
    y_test_true: np.ndarray,
    df_eval_test: pd.DataFrame
) -> Dict[str, Any]:
    """Compute classification metrics and per-basin AUC on exact evaluation matrix."""
    model.eval()
    with torch.no_grad():
        t_dyn = torch.from_numpy(x_dyn_test)
        t_stat = torch.from_numpy(x_stat_test)
        logits = model(t_dyn, t_stat).numpy()
        probs = 1.0 / (1.0 + np.exp(-logits))

    # Pooled metrics
    if len(np.unique(y_test_true)) > 1:
        pooled_auc = float(roc_auc_score(y_test_true, probs))
        pooled_ap = float(average_precision_score(y_test_true, probs))
    else:
        pooled_auc = 0.5
        pooled_ap = float(np.mean(y_test_true))

    preds = (probs >= 0.5).astype(int)
    f1 = float(f1_score(y_test_true, preds, zero_division=0))
    brier = float(brier_score_loss(y_test_true, probs))

    # Per-basin AUC across the 11 test streamgages
    df_eval_test_copy = df_eval_test.copy()
    df_eval_test_copy["ea_prob"] = probs

    basin_aucs = []
    for g_id in df_eval_test_copy["gauge_id"].unique():
        df_g = df_eval_test_copy[df_eval_test_copy["gauge_id"] == g_id]
        y_g = df_g["y_flood_true"].values
        p_g = df_g["ea_prob"].values
        if len(np.unique(y_g)) > 1:
            auc_g = float(roc_auc_score(y_g, p_g))
        else:
            auc_g = 0.5
        basin_aucs.append(auc_g)

    return {
        "pooled_auc_roc": pooled_auc,
        "basin_median_auc": float(np.median(basin_aucs)),
        "basin_mean_auc": float(np.mean(basin_aucs)),
        "avg_precision": pooled_ap,
        "f1_score": f1,
        "brier_score": brier,
        "basin_aucs": basin_aucs
    }


def run_label_budget_sweep() -> None:
    """Execute complete 30-run label budget sweep across all 6 budgets and 5 frozen seeds."""
    logger.info("Executing EA-LSTM Label-Budget Efficiency Sweep on Frozen Eval Matrix (H5)...")

    norm_file = CHUNK03_DIR / "normalization_params.json"
    with open(norm_file, "r", encoding="utf-8") as f:
        norm_params = json.load(f)

    static_lookup, _ = load_static_attribute_lookup()
    df_events = load_flood_events()

    df_train = pd.read_parquet(CHUNK03_DATA_DIR / "feature_matrix_train.parquet")
    df_val = pd.read_parquet(CHUNK03_DATA_DIR / "feature_matrix_val.parquet")
    df_feat_test = pd.read_parquet(CHUNK03_DATA_DIR / "feature_matrix_test.parquet")

    # Load EXACT frozen evaluation matrix test split (N=520)
    df_eval = pd.read_parquet(CHUNK07_DATA_DIR / "evaluation_event_matrix.parquet")
    df_eval_test = df_eval[df_eval["split"] == "test"].copy().reset_index(drop=True)
    y_test_true = df_eval_test["y_flood_true"].values

    # Align feature rows strictly to evaluation event matrix test windows
    df_feat_test_aligned = df_eval_test[["window_id"]].merge(df_feat_test, on="window_id", how="left")

    # Extract test tensors strictly for the 520 evaluation windows
    x_dyn_test, x_stat_test, _ = extract_tensors_and_labels(df_feat_test_aligned, norm_params, static_lookup, df_events)

    # Calculate fixed SSL Score-A reference metrics on the exact same 520 evaluation windows
    ssl_score_arr = df_eval_test["score_a_cal_iqr_max7d"].values
    ssl_pooled_auc = float(roc_auc_score(y_test_true, ssl_score_arr))

    ssl_basin_aucs = []
    for g_id in df_eval_test["gauge_id"].unique():
        df_g = df_eval_test[df_eval_test["gauge_id"] == g_id]
        y_g = df_g["y_flood_true"].values
        s_g = df_g["score_a_cal_iqr_max7d"].values
        if len(np.unique(y_g)) > 1:
            auc_g = float(roc_auc_score(y_g, s_g))
        else:
            auc_g = 0.5
        ssl_basin_aucs.append(auc_g)
    ssl_basin_med_auc = float(np.median(ssl_basin_aucs))
    ssl_basin_mean_auc = float(np.mean(ssl_basin_aucs))

    logger.info(
        f"Fixed Score-A Reference Baseline: Pooled AUC = {ssl_pooled_auc:.4f}, Basin Median AUC = {ssl_basin_med_auc:.4f}"
    )

    # Sample base training pool (~1200 windows)
    df_train_pool = df_train.sample(n=min(1200, len(df_train)), random_state=42).reset_index(drop=True)
    x_dyn_pool, x_stat_pool, y_pool = extract_tensors_and_labels(df_train_pool, norm_params, static_lookup, df_events)
    x_dyn_val, x_stat_val, y_val = extract_tensors_and_labels(df_val, norm_params, static_lookup, df_events)

    total_pool_count = len(y_pool)
    sweep_records: List[Dict[str, Any]] = []

    condition_count = 0
    for budget_frac in LABEL_BUDGETS:
        for seed in FROZEN_SEEDS:
            condition_count += 1
            sample_size = max(int(np.round(total_pool_count * budget_frac)), 10)

            # Deterministic subset sampling using frozen seed
            rng = np.random.RandomState(seed)
            sub_indices = rng.choice(total_pool_count, size=sample_size, replace=False)

            x_dyn_sub = x_dyn_pool[sub_indices]
            x_stat_sub = x_stat_pool[sub_indices]
            y_sub = y_pool[sub_indices]
            pos_count = int(np.sum(y_sub == 1.0))

            logger.info(
                f"Run {condition_count}/30 — Budget: {budget_frac*100:.0f}% (N={sample_size}, Pos={pos_count}), Seed: {seed}"
            )

            # Train EA-LSTM for 5 epochs matching canonical SUP_HYPERPARAMETERS
            model = train_ea_lstm(x_dyn_sub, x_stat_sub, y_sub, epochs=SUP_HYPERPARAMETERS["epochs"], seed=seed)

            # Evaluate on Validation
            model.eval()
            with torch.no_grad():
                v_logits = model(torch.from_numpy(x_dyn_val), torch.from_numpy(x_stat_val)).numpy()
                v_probs = 1.0 / (1.0 + np.exp(-v_logits))
            val_auc = float(roc_auc_score(y_val, v_probs)) if len(np.unique(y_val)) > 1 else 0.5

            # Evaluate on exact test evaluation matrix
            test_metrics = evaluate_model_on_test_matrix(model, x_dyn_test, x_stat_test, y_test_true, df_eval_test)

            record = {
                "condition_id": f"budget_{int(budget_frac*100):03d}_seed_{seed}",
                "label_budget_fraction": budget_frac,
                "training_label_count": sample_size,
                "training_positive_count": pos_count,
                "random_seed": seed,
                "val_auc_roc": val_auc,
                "ea_lstm_test_auc_roc": test_metrics["pooled_auc_roc"],
                "test_auc_roc": test_metrics["pooled_auc_roc"],
                "ea_lstm_basin_median_auc": test_metrics["basin_median_auc"],
                "test_avg_precision": test_metrics["avg_precision"],
                "test_f1_score": test_metrics["f1_score"],
                "test_brier_score": test_metrics["brier_score"],
                "basin_aucs": test_metrics["basin_aucs"]
            }
            sweep_records.append(record)

    df_sweep = pd.DataFrame(sweep_records)
    CHUNK06_DATA_DIR.mkdir(parents=True, exist_ok=True)
    out_parquet = CHUNK06_DATA_DIR / "label_budget_sweep_results.parquet"
    df_sweep.to_parquet(out_parquet, index=False)

    # Compute aggregate summary statistics across seeds
    summary_by_budget: Dict[str, Any] = {}
    for budget_frac in LABEL_BUDGETS:
        subset = df_sweep[df_sweep["label_budget_fraction"] == budget_frac]
        ea_pooled_aucs = subset["ea_lstm_test_auc_roc"].values
        ea_basin_meds = subset["ea_lstm_basin_median_auc"].values

        summary_by_budget[f"{int(budget_frac*100)}pct"] = {
            "label_budget_fraction": budget_frac,
            "training_label_count": int(subset["training_label_count"].mean()),
            "runs_count": len(subset),
            "ea_lstm_pooled_auc_mean": float(np.mean(ea_pooled_aucs)),
            "ea_lstm_pooled_auc_std": float(np.std(ea_pooled_aucs, ddof=1)),
            "ea_lstm_pooled_aucs": ea_pooled_aucs.tolist(),
            "ea_lstm_basin_median_auc_mean": float(np.mean(ea_basin_meds)),
            "ea_lstm_basin_median_auc_std": float(np.std(ea_basin_meds, ddof=1)),
            "ea_lstm_basin_median_aucs": ea_basin_meds.tolist(),
            "test_avg_precision_mean": float(subset["test_avg_precision"].mean()),
            "test_f1_score_mean": float(subset["test_f1_score"].mean())
        }

    summary_payload = {
        "sweep_title": "EA-LSTM Label-Budget Efficiency Sweep across 5 Frozen Seeds",
        "fixed_reference_benchmark": {
            "method": "Score-A Reconstruction (Zero-Label SSL Reference)",
            "ssl_pooled_test_auc": ssl_pooled_auc,
            "ssl_basin_median_auc": ssl_basin_med_auc,
            "ssl_basin_mean_auc": ssl_basin_mean_auc
        },
        "budgets_evaluated": LABEL_BUDGETS,
        "frozen_seeds": FROZEN_SEEDS,
        "total_conditions_evaluated": len(df_sweep),
        "results_by_budget": summary_by_budget
    }

    summary_json = CHUNK06_DIR / "label_budget_summary.json"
    with open(summary_json, "w", encoding="utf-8") as f:
        json.dump(summary_payload, f, indent=2)

    logger.info(f"Sweep results serialized to {out_parquet} ({len(df_sweep)} runs).")
    logger.info(f"Summary JSON serialized to {summary_json}.")
    logger.info("EA-LSTM Label-Budget Efficiency Sweep on Frozen Eval Matrix PASSED.")


def main() -> None:
    run_label_budget_sweep()


if __name__ == "__main__":
    main()
