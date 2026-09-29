"""fig2_roc_curves.py -- Generate Figure 2: Pooled Test ROC Curves.

Outputs: project/chunks/chunk10/figures/roc_curves.svg
"""

import argparse
import json
import sys
from pathlib import Path

# Add project root to sys.path
_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from sklearn.metrics import roc_curve, roc_auc_score


def plot_roc_curves(out_path: Path):
    """Plot multi-model pooled ROC curves."""
    results_path = _PROJECT_ROOT / "project" / "chunks" / "chunk07" / "data" / "discrimination_results.json"
    manifest_path = _PROJECT_ROOT / "project" / "chunks" / "chunk10" / "final_results_manifest.json"
    matrix_path = _PROJECT_ROOT / "project" / "chunks" / "chunk07" / "data" / "evaluation_event_matrix.parquet"

    df = pd.read_parquet(matrix_path)
    
    # Restrict to test split if needed, though discrimination is evaluated on test split
    # 'y_flood_true' is the label
    df_test = df[df['split'] == 'test']
    y_true = df_test['y_flood_true'].astype(float).values

    # Canonical AUCs from manifest or recalculated
    def get_auc_and_curve(score_col):
        y_score = df_test[score_col].astype(float).values
        # Handle NaNs if any
        valid = ~np.isnan(y_score) & ~np.isnan(y_true)
        if not valid.any():
            return 0.5, [0, 1], [0, 1]
        auc_val = roc_auc_score(y_true[valid], y_score[valid])
        fpr, tpr, _ = roc_curve(y_true[valid], y_score[valid])
        return auc_val, fpr, tpr

    auc_score_a, fpr_score_a, tpr_score_a = get_auc_and_curve("score_a_cal_iqr_max7d")
    auc_nwm, fpr_nwm, tpr_nwm = get_auc_and_curve("score_nwm_cal_iqr_max7d")
    auc_persist, fpr_persist, tpr_persist = get_auc_and_curve("score_persist_cal_iqr_max7d")
    auc_ea_lstm, fpr_ea_lstm, tpr_ea_lstm = get_auc_and_curve("score_ea_lstm_prob")
    auc_if, fpr_if, tpr_if = get_auc_and_curve("score_iforest_terminal")

    fig, ax = plt.subplots(figsize=(7, 6), dpi=300)

    models = [
        ("Persistence Baseline", auc_persist, fpr_persist, tpr_persist, "#64748b", "--", 1.5),
        ("NWM Retrospective v3.0", auc_nwm, fpr_nwm, tpr_nwm, "#0284c7", "-.", 1.8),
        ("Score-A Reconstruction (Proposed)", auc_score_a, fpr_score_a, tpr_score_a, "#dc2626", "-", 2.5),
        ("Supervised EA-LSTM (100% Labels)", auc_ea_lstm, fpr_ea_lstm, tpr_ea_lstm, "#16a34a", "-", 1.8),
        ("Isolation Forest", auc_if, fpr_if, tpr_if, "#9333ea", ":", 1.5),
    ]

    for name, auc_val, fpr, tpr, color, ls, lw in models:
        ax.plot(
            fpr,
            tpr,
            label=f"{name} (AUC = {auc_val:.4f})",
            color=color,
            linestyle=ls,
            linewidth=lw,
        )

    # Random chance diagonal
    ax.plot([0, 1], [0, 1], color="#94a3b8", linestyle=":", label="Random Chance (AUC = 0.5000)", linewidth=1.0)

    ax.set_xlim(-0.02, 1.02)
    ax.set_ylim(-0.02, 1.02)
    ax.set_xlabel("False Positive Rate (1 - Specificity)", fontsize=10)
    ax.set_ylabel("True Positive Rate (Sensitivity)", fontsize=10)
    ax.set_title("Pooled Test Set Discrimination (Held-Out Basins, N=520)", fontsize=11, fontweight="bold", pad=10)
    ax.grid(True, linestyle="--", alpha=0.5, color="#cbd5e1")
    ax.legend(loc="lower right", frameon=True, facecolor="white", edgecolor="#cbd5e1", fontsize=8.5)

    plt.tight_layout()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    plt.savefig(out_path, format="svg")
    plt.close()
    print(f"Saved Figure 2 to: {out_path}")


def main():
    parser = argparse.ArgumentParser(description="Generate Figure 2: ROC Curves")
    parser.add_argument("--out", required=True, help="Output SVG path")
    args = parser.parse_args()
    plot_roc_curves(Path(args.out))


if __name__ == "__main__":
    main()
