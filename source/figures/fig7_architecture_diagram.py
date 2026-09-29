"""fig7_architecture_diagram.py -- Generate Figure 7: C-ENCODER Neural Architecture Diagram.

Outputs: project/chunks/chunk10/figures/architecture_diagram.svg
"""

import argparse
import sys
from pathlib import Path

# Add project root to sys.path
_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

import matplotlib
matplotlib.use("Agg")
import matplotlib.patches as patches
import matplotlib.pyplot as plt


def plot_architecture_diagram(out_path: Path):
    """Draw C-ENCODER hybrid causal neural architecture diagram."""
    fig, ax = plt.subplots(figsize=(11, 6.5), dpi=300)
    ax.set_xlim(0, 100)
    ax.set_ylim(0, 100)
    ax.axis("off")

    # Styling helper for rounded boxes
    def draw_box(x, y, w, h, title, subtitle, bg_color, border_color="#1e293b"):
        rect = patches.FancyBboxPatch(
            (x, y),
            w,
            h,
            boxstyle="round,pad=0.8,rounding_size=1.5",
            facecolor=bg_color,
            edgecolor=border_color,
            linewidth=1.4,
        )
        ax.add_patch(rect)
        ax.text(
            x + w / 2.0,
            y + h * 0.65,
            title,
            ha="center",
            va="center",
            fontsize=9.5,
            fontweight="bold",
            color="#0f172a",
        )
        if subtitle:
            ax.text(
                x + w / 2.0,
                y + h * 0.30,
                subtitle,
                ha="center",
                va="center",
                fontsize=8.0,
                color="#475569",
            )

    def draw_arrow(x1, y1, x2, y2, label=""):
        ax.annotate(
            "",
            xy=(x2, y2),
            xytext=(x1, y1),
            arrowprops=dict(facecolor="#334155", edgecolor="#334155", width=1.5, headwidth=6, headlength=7),
        )
        if label:
            ax.text(
                (x1 + x2) / 2.0,
                (y1 + y2) / 2.0 + 2.0,
                label,
                ha="center",
                va="center",
                fontsize=7.5,
                color="#1e293b",
                backgroundcolor="white",
            )

    # 1. Inputs Block
    draw_box(
        4,
        35,
        18,
        30,
        "Multi-Channel Inputs\n$X \\in \\mathbb{R}^{T \\times C}$",
        "• USGS Streamflow & Stage\n• gridMET Precip, Tmin, Tmax\n• SNODAS Snowpack (SWE)\n$T=365\\text{ days}, C=6$",
        "#f1f5f9",
    )

    # 2. Dilated Causal TCN
    draw_box(
        27,
        35,
        18,
        30,
        "Dilated Causal TCN\nResidual Blocks",
        "• Left-Sided Causal Padding\n• Dilation Rates: $d = 1, 2, 4, 8$\n• Multi-Scale Feature Extractor\n(104,966 Params)",
        "#e0f2fe",
        "#0284c7",
    )

    # 3. Causal Transformer Attention
    draw_box(
        50,
        35,
        18,
        30,
        "Causal Multi-Head\nSelf-Attention",
        "• Lower-Triangular Mask $M_{i,j}$\n• Zero Future Lookahead Leakage\n• Cross-Channel Temporal Dynamics\n(41,984 Params)",
        "#e0e7ff",
        "#4338ca",
    )

    # 4. Latent Bottleneck
    draw_box(
        73,
        55,
        22,
        22,
        "Latent Representation\n$Z \\in \\mathbb{R}^{T \\times 64}$",
        "64-Dim Temporal Sequence\n(Bottleneck State)",
        "#fef3c7",
        "#d97706",
    )

    # 5. Output Scoring Heads
    draw_box(
        73,
        15,
        22,
        32,
        "Precursor Scoring Heads",
        "• Score-A: Reconstruction MSE\n• Score-B: Latent Centroid Dist.\n• Score-C: State Transition Jump",
        "#fee2e2",
        "#dc2626",
    )

    # Connecting arrows
    draw_arrow(22, 50, 27, 50, "Causal Ingestion")
    draw_arrow(45, 50, 50, 50, "Temporal Maps")
    draw_arrow(68, 50, 73, 66, "Latent Projection")
    draw_arrow(68, 50, 73, 31, "Decoder / Scoring")
    draw_arrow(84, 55, 84, 47, "Latent Vectors")

    # Header title
    ax.text(
        50,
        92,
        "Flood Sentinel Hybrid Causal Neural Architecture (C-ENCODER, 146,950 Parameters)",
        ha="center",
        va="center",
        fontsize=12,
        fontweight="bold",
        color="#0f172a",
    )
    ax.text(
        50,
        86,
        "End-to-end self-supervised masked temporal pretraining with strict causal lower-triangular attention",
        ha="center",
        va="center",
        fontsize=9,
        color="#475569",
    )

    plt.tight_layout()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    plt.savefig(out_path, format="svg")
    plt.close()
    print(f"Saved Figure 7 to: {out_path}")


def main():
    parser = argparse.ArgumentParser(description="Generate Figure 7: Architecture Diagram")
    parser.add_argument("--out", required=True, help="Output SVG path")
    args = parser.parse_args()
    plot_architecture_diagram(Path(args.out))


if __name__ == "__main__":
    main()
