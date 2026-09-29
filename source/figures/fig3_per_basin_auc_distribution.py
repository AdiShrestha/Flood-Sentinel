"""fig3_per_basin_auc_distribution.py -- Generate Figure 3: Per-Basin AUC Distribution.

Outputs: project/chunks/chunk10/figures/per_basin_auc_distribution.svg
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


def plot_per_basin_auc(out_path: Path):
    """Plot per-basin AUC box/strip plot distinguishing estimable from non-estimable basins."""
    results_path = _PROJECT_ROOT / "project" / "chunks" / "chunk07" / "data" / "discrimination_results.json"
    audit_path = _PROJECT_ROOT / "project" / "chunks" / "chunk10" / "effective_sample_audit.json"

    with open(results_path, "r", encoding="utf-8") as f:
        res_data = json.load(f)

    non_estimable_indices = {0, 5, 9, 10}
    if audit_path.exists():
        with open(audit_path, "r", encoding="utf-8") as f:
            aud_data = json.load(f)
        non_estimable_indices = set(aud_data.get("non_estimable_basin_indices", [0, 5, 9, 10]))

    methods = [
        ("Score-A (Proposed)", "score_a_reconstruction", "#dc2626"),
        ("NWM Retrospective", "nwm_retrospective_v3", "#0284c7"),
        ("EA-LSTM (100% Labels)", "dl_ea_lstm_supervised", "#16a34a"),
        ("Persistence", "stat_persistence", "#64748b"),
    ]

    fig, ax = plt.subplots(figsize=(8, 5.5), dpi=300)

    for pos, (name, key, color) in enumerate(methods):
        m_info = res_data["basin_level_summary"].get(key, {})
        aucs = m_info.get("basin_aucs_list", [0.5] * 11)

        # Separate estimable (N=7) from non-estimable (N=4)
        estimable_aucs = [aucs[i] for i in range(len(aucs)) if i not in non_estimable_indices]
        non_estimable_aucs = [aucs[i] for i in range(len(aucs)) if i in non_estimable_indices]

        # Box plot for estimable subset
        bp = ax.boxplot(
            [estimable_aucs],
            positions=[pos],
            widths=0.4,
            patch_artist=True,
            showmeans=True,
            meanline=True,
            boxprops=dict(facecolor=color, alpha=0.25, edgecolor=color, linewidth=1.2),
            medianprops=dict(color=color, linewidth=2.0),
            meanprops=dict(color="black", linestyle="--", linewidth=1.2),
            whiskerprops=dict(color=color, linewidth=1.2),
            capprops=dict(color=color, linewidth=1.2),
        )

        # Scatter estimable points (filled) with jitter
        jitter = np.linspace(-0.08, 0.08, len(estimable_aucs))
        ax.scatter(
            [pos + j for j in jitter],
            estimable_aucs,
            color=color,
            s=60,
            edgecolors="black",
            linewidth=0.8,
            zorder=4,
            label="Estimable Basins (N=7)" if pos == 0 else "",
        )

        # Scatter non-estimable points (open gray circles at 0.50)
        j_non = np.linspace(-0.12, 0.12, len(non_estimable_aucs))
        ax.scatter(
            [pos + j for j in j_non],
            non_estimable_aucs,
            facecolors="none",
            edgecolors="#94a3b8",
            linewidth=1.5,
            s=70,
            marker="o",
            zorder=4,
            label="Non-Estimable (Single-Class, N=4)" if pos == 0 else "",
        )

    # Reference chance line
    ax.axhline(0.5, color="#94a3b8", linestyle=":", linewidth=1.0, alpha=0.8)

    ax.set_xticks(range(len(methods)))
    ax.set_xticklabels([m[0] for m in methods], fontsize=9.5)
    ax.set_ylabel("Catchment Test ROC-AUC", fontsize=10)
    ax.set_ylim(0.42, 1.05)
    ax.set_title(
        "Per-Basin ROC-AUC Distribution Across Test Split (N=11 Nominal, N=7 Estimable)",
        fontsize=11,
        fontweight="bold",
        pad=10,
    )
    ax.grid(True, linestyle="--", alpha=0.5, color="#cbd5e1", axis="y")
    ax.legend(loc="lower right", frameon=True, facecolor="white", edgecolor="#cbd5e1", fontsize=8.5)

    plt.tight_layout()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    plt.savefig(out_path, format="svg")
    plt.close()
    print(f"Saved Figure 3 to: {out_path}")


def main():
    parser = argparse.ArgumentParser(description="Generate Figure 3: Per-Basin AUC Distribution")
    parser.add_argument("--out", required=True, help="Output SVG path")
    args = parser.parse_args()
    plot_per_basin_auc(Path(args.out))


if __name__ == "__main__":
    main()
