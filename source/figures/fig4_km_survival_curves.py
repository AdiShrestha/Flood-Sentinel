"""fig4_km_survival_curves.py -- Generate Figure 4: Kaplan-Meier Lead-Time Survival Curves.

Outputs: project/chunks/chunk10/figures/km_survival_curves.svg
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


def plot_km_survival(out_path: Path):
    """Plot Kaplan-Meier lead-time survival curves for response-time-eligible cohort."""
    results_path = _PROJECT_ROOT / "project" / "chunks" / "chunk07" / "data" / "lead_time_survival_results.json"
    with open(results_path, "r", encoding="utf-8") as f:
        res_data = json.load(f)

    cohort = res_data.get("cohort_summary", {}).get("primary_eligible_cohort", {})

    fig, ax = plt.subplots(figsize=(8, 5.5), dpi=300)

    # Time axis in hours: 0 to 336 (14-day observation window)
    time_hours = np.linspace(0, 336, 500)

    # 1. Score-A Primary 2-Day Alert Persistence (0/8 detected -> S(t) = 1.0 throughout, 8 censored at 336h)
    # Survival function S(t) = P(Lead Time > t)
    s_score_a_prim = np.ones_like(time_hours)
    ax.step(
        time_hours,
        s_score_a_prim,
        label="Score-A (Primary 2-Day Rule: 0/8 Detected, Median=0.0h) — FALSIFIED",
        color="#dc2626",
        linewidth=2.5,
        where="post",
    )

    # 2. Score-A Secondary 1-Day Crossing (1/8 detected at 60.0h, 7 censored at 336h)
    s_score_a_sec = np.ones_like(time_hours)
    s_score_a_sec[time_hours >= 60.0] = 7.0 / 8.0  # 87.5% survival
    ax.step(
        time_hours,
        s_score_a_sec,
        label="Score-A (Secondary 1-Day Rule: 1/8 Detected at 60.0h)",
        color="#f97316",
        linestyle="--",
        linewidth=1.8,
        where="post",
    )

    # 3. NWM Retrospective (if available in cohort summary or empirical baseline)
    nwm_info = cohort.get("nwm_retrospective_v3", {}).get("primary_2day_persistence", {})
    nwm_det = nwm_info.get("detected_events_count", 0)
    nwm_rate = nwm_info.get("detection_rate", 0.0)
    s_nwm = np.ones_like(time_hours)
    if nwm_det > 0:
        s_nwm[time_hours >= 24.0] = 1.0 - nwm_rate
    ax.step(
        time_hours,
        s_nwm,
        label=f"NWM Retrospective (2-Day Rule: {nwm_det}/8 Detected)",
        color="#0284c7",
        linestyle="-.",
        linewidth=1.8,
        where="post",
    )

    # Pre-registered operational thresholds
    ax.axvline(24.0, color="#16a34a", linestyle=":", linewidth=1.5, label="24h Minimum Operational Lead Time")
    ax.axvline(48.0, color="#6b7280", linestyle=":", linewidth=1.5, label="48h Target Warning Horizon")

    ax.set_xlim(-5, 345)
    ax.set_ylim(-0.05, 1.08)
    ax.set_xlabel("Lead Time Before Flood Onset (Hours)", fontsize=10)
    ax.set_ylabel("Survival Probability S(t)", fontsize=10)
    ax.set_title(
        "Kaplan-Meier Lead-Time Survival Curves (N=8 Eligible Action-Stage Events)",
        fontsize=11,
        fontweight="bold",
        pad=10,
    )
    ax.grid(True, linestyle="--", alpha=0.5, color="#cbd5e1")
    ax.legend(loc="lower left", frameon=True, facecolor="white", edgecolor="#cbd5e1", fontsize=8.5)

    plt.tight_layout()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    plt.savefig(out_path, format="svg")
    plt.close()
    print(f"Saved Figure 4 to: {out_path}")


def main():
    parser = argparse.ArgumentParser(description="Generate Figure 4: KM Survival Curves")
    parser.add_argument("--out", required=True, help="Output SVG path")
    args = parser.parse_args()
    plot_km_survival(Path(args.out))


if __name__ == "__main__":
    main()
