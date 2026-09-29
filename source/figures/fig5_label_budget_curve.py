"""fig5_label_budget_curve.py -- Generate Figure 5: Label-Budget Sample-Efficiency Curve.

Outputs: project/chunks/chunk10/figures/label_budget_curve.svg
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


def plot_label_budget_curve(out_path: Path):
    """Plot label-efficiency sweep curve comparing zero-label Score-A against 5-seed EA-LSTM."""
    results_path = _PROJECT_ROOT / "project" / "chunks" / "chunk07" / "data" / "discrimination_results.json"
    with open(results_path, "r", encoding="utf-8") as f:
        res_data = json.load(f)

    h5_info = res_data.get("hypotheses_evaluation", {}).get("H5", {})
    budgets_summary = h5_info.get("exploratory_training_window_budgets_summary", [])

    budgets = []
    ea_means = []
    ea_stds = []
    ssl_fixed = 0.82957

    for b in budgets_summary:
        frac = b["label_budget_fraction"] * 100.0
        budgets.append(frac)
        ea_means.append(b["ea_lstm_pooled_auc_mean"])
        ea_stds.append(b["ea_lstm_pooled_auc_std"])
        ssl_fixed = b.get("ssl_fixed_reference_pooled_auc", ssl_fixed)

    fig, ax = plt.subplots(figsize=(7.5, 5.5), dpi=300)

    # Score-A Zero-Label Fixed Reference Horizontal Line
    ax.axhline(
        ssl_fixed,
        color="#dc2626",
        linestyle="-",
        linewidth=2.2,
        label=f"Zero-Label Score-A Reference (AUC = {ssl_fixed:.4f})",
        zorder=3,
    )

    # EA-LSTM Supervised Mean +/- Std Error Bars
    ax.errorbar(
        budgets,
        ea_means,
        yerr=ea_stds,
        fmt="o-",
        color="#16a34a",
        linewidth=1.8,
        markersize=6,
        capsize=4,
        capthick=1.2,
        label="Supervised EA-LSTM (Mean ± 1 SD across 5 Seeds)",
        zorder=4,
    )

    # Highlight 10% Primary Confirmatory Budget
    idx_10 = budgets.index(10.0) if 10.0 in budgets else 2
    ax.scatter(
        [budgets[idx_10]],
        [ea_means[idx_10]],
        s=120,
        facecolors="none",
        edgecolors="#dc2626",
        linewidth=2.0,
        zorder=5,
        label=f"Primary 10% Confirmatory Budget (p = 0.03125)",
    )

    ax.set_xscale("log")
    ax.set_xticks([1, 5, 10, 25, 50, 100])
    ax.get_xaxis().set_major_formatter(matplotlib.ticker.ScalarFormatter())
    ax.set_xlabel("Training-Window Label Budget (% of 1,200 Labeled Training Pool)", fontsize=10)
    ax.set_ylabel("Pooled Test AUC-ROC", fontsize=10)
    ax.set_ylim(0.30, 0.95)
    ax.set_title(
        "Label Scarcity Benchmark: Zero-Label Score-A vs. Supervised EA-LSTM",
        fontsize=11,
        fontweight="bold",
        pad=10,
    )
    ax.grid(True, linestyle="--", alpha=0.5, color="#cbd5e1")
    ax.legend(loc="lower right", frameon=True, facecolor="white", edgecolor="#cbd5e1", fontsize=8.5)

    plt.tight_layout()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    plt.savefig(out_path, format="svg")
    plt.close()
    print(f"Saved Figure 5 to: {out_path}")


def main():
    parser = argparse.ArgumentParser(description="Generate Figure 5: Label Budget Curve")
    parser.add_argument("--out", required=True, help="Output SVG path")
    args = parser.parse_args()
    plot_label_budget_curve(Path(args.out))


if __name__ == "__main__":
    main()
