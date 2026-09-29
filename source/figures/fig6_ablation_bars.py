"""fig6_ablation_bars.py -- Generate Figure 6: Ablation Studies Bar Chart.

Outputs: project/chunks/chunk10/figures/ablation_bars.svg
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


def plot_ablation_bars(out_path: Path):
    """Plot 3-panel ablation study summary bar charts."""
    fig, (ax1, ax2, ax3) = plt.subplots(1, 3, figsize=(13, 4.8), dpi=300)

    # Panel 1: Sensor Modality Holdout (Delta AUC vs Full Multi-Sensor Suite)
    sensor_labels = ["-Discharge\n& Stage", "-Precip.", "+Snowpack\n(SWE)", "+Temp.\n(Tmin/max)"]
    sensor_deltas = [-0.0231, -0.0072, 0.0067, 0.0075]
    colors_s = ["#dc2626" if d < 0 else "#16a34a" for d in sensor_deltas]

    bars1 = ax1.bar(sensor_labels, sensor_deltas, color=colors_s, edgecolor="black", linewidth=0.8, width=0.55)
    ax1.axhline(0, color="black", linewidth=0.8)
    ax1.set_ylabel("$\\Delta$ Test AUC vs. Full Suite", fontsize=9.5)
    ax1.set_title("A. Sensor Modality Holdout", fontsize=10.5, fontweight="bold", pad=8)
    ax1.set_ylim(-0.030, 0.015)
    ax1.grid(True, linestyle="--", alpha=0.4, axis="y")

    for bar, val in zip(bars1, sensor_deltas):
        offset = 0.001 if val >= 0 else -0.003
        ax1.text(
            bar.get_x() + bar.get_width() / 2.0,
            val + offset,
            f"{val:+.4f}",
            ha="center",
            va="bottom" if val >= 0 else "top",
            fontsize=8.5,
            fontweight="bold",
        )

    # Panel 2: Neural Architecture Trade-off (Delta AUC vs Hybrid C-ENCODER)
    arch_labels = ["Hybrid\nTCN-Trans.\n(Proposed)", "Pure\nCausal TCN", "Pure\nTransformer"]
    arch_deltas = [0.0000, -0.0025, -0.0097]
    colors_a = ["#2563eb", "#64748b", "#64748b"]

    bars2 = ax2.bar(arch_labels, arch_deltas, color=colors_a, edgecolor="black", linewidth=0.8, width=0.55)
    ax2.axhline(0, color="black", linewidth=0.8)
    ax2.set_ylabel("$\\Delta$ Test AUC vs. Hybrid", fontsize=9.5)
    ax2.set_title("B. Neural Architecture Trade-off", fontsize=10.5, fontweight="bold", pad=8)
    ax2.set_ylim(-0.014, 0.004)
    ax2.grid(True, linestyle="--", alpha=0.4, axis="y")

    for bar, val in zip(bars2, arch_deltas):
        offset = 0.0005 if val >= 0 else -0.0015
        ax2.text(
            bar.get_x() + bar.get_width() / 2.0,
            val + offset,
            f"{val:+.4f}",
            ha="center",
            va="bottom" if val >= 0 else "top",
            fontsize=8.5,
            fontweight="bold",
        )

    # Panel 3: Causal Masking Integrity (Causal vs Bidirectional)
    mask_labels = ["Strictly Causal\n(Lower-Tri)", "Bidirectional\n(Unmasked)"]
    mask_aucs = [0.6992, 0.6990]
    colors_m = ["#16a34a", "#94a3b8"]

    bars3 = ax3.bar(mask_labels, mask_aucs, color=colors_m, edgecolor="black", linewidth=0.8, width=0.5)
    ax3.set_ylabel("Test AUC-ROC", fontsize=9.5)
    ax3.set_title("C. Causal Masking Compliance", fontsize=10.5, fontweight="bold", pad=8)
    ax3.set_ylim(0.680, 0.710)
    ax3.grid(True, linestyle="--", alpha=0.4, axis="y")

    for bar, val in zip(bars3, mask_aucs):
        ax3.text(
            bar.get_x() + bar.get_width() / 2.0,
            val + 0.001,
            f"{val:.4f}",
            ha="center",
            va="bottom",
            fontsize=8.5,
            fontweight="bold",
        )

    plt.tight_layout()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    plt.savefig(out_path, format="svg")
    plt.close()
    print(f"Saved Figure 6 to: {out_path}")


def main():
    parser = argparse.ArgumentParser(description="Generate Figure 6: Ablation Bars")
    parser.add_argument("--out", required=True, help="Output SVG path")
    args = parser.parse_args()
    plot_ablation_bars(Path(args.out))


if __name__ == "__main__":
    main()
