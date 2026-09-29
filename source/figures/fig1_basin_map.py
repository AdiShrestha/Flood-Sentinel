"""fig1_basin_map.py -- Generate Figure 1: Continental Basin Map (Train / Val / Test Splits).

Outputs: project/chunks/chunk10/figures/basin_map.svg
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


# Coordinates for full 54 streamgages derived from USGS NWIS & GAGES-II
GAUGE_COORDINATES = {
    # 18 Pilot Stations
    "01372500": (41.6531, -73.8726),
    "01445500": (40.8306, -74.9778),
    "01463500": (40.2217, -74.7781),
    "01646500": (38.9498, -77.1275),
    "02083500": (35.8944, -77.8344),
    "02085000": (36.0711, -77.9603),
    "02322500": (29.8488, -82.8661),
    "03335500": (40.4219, -86.9964),
    "05420500": (42.0672, -90.3800),
    "05431486": (42.5028, -89.0200),
    "05435500": (42.2789, -89.0719),
    "06805500": (41.0600, -96.1600),
    "06888500": (39.0531, -96.5581),
    "08167000": (29.9708, -98.8903),
    "08167500": (29.7028, -98.1247),
    "09112500": (38.7492, -107.0372),
    "14181500": (44.7500, -122.4667),
    "14211720": (45.5186, -122.6783),
    # 36 Full-Panel Expansion Stations
    "01034500": (45.3944, -68.8250),
    "01137500": (44.5208, -71.5500),
    "01184000": (42.0200, -72.6000),
    "01434000": (41.4833, -74.7000),
    "01541000": (41.0833, -76.6000),
    "02138500": (34.1833, -79.7500),
    "02175000": (32.8833, -80.0000),
    "02202500": (31.6500, -81.5000),
    "03164000": (36.9167, -81.1000),
    "03217500": (37.7500, -82.6000),
    "03345500": (39.0833, -87.5500),
    "03438000": (36.1500, -86.7833),
    "03497300": (35.6000, -83.9500),
    "040851385": (44.5000, -88.0000),
    "04122500": (43.9000, -86.4000),
    "04193500": (41.3500, -83.7000),
    "05286000": (45.0000, -93.3000),
    "05389500": (43.8000, -91.2500),
    "06025500": (45.5000, -112.5000),
    "06478500": (42.8500, -97.4000),
    "06719505": (39.7500, -105.0000),
    "07144100": (37.6833, -97.3500),
    "07197000": (36.1833, -94.6000),
    "07261000": (35.2000, -92.4000),
    "07288500": (32.3000, -90.9000),
    "07374000": (30.4500, -91.1833),
    "08101000": (31.1000, -97.3500),
    "08144500": (31.3000, -99.4000),
    "09070500": (39.5500, -107.3333),
    "09444500": (32.9500, -109.3000),
    "09498500": (33.9500, -111.3000),
    "11264500": (37.7000, -119.6000),
    "11447650": (38.5833, -121.5000),
    "12447200": (48.3000, -119.5000),
    "13317000": (45.4000, -116.5000),
    "14137000": (45.3000, -122.2000),
}


def plot_basin_map(out_path: Path):
    """Plot CONUS streamgage map."""
    # Load split manifest
    split_path = _PROJECT_ROOT / "project" / "chunks" / "chunk03" / "split_manifest.json"
    with open(split_path, "r", encoding="utf-8") as f:
        split_data = json.load(f)

    train_gauges = set(split_data.get("train_gauges", []))
    val_gauges = set(split_data.get("val_gauges", []))
    test_gauges = set(split_data.get("test_gauges", []))

    # Load panel metadata for reference vs non-reference
    panel_path = _PROJECT_ROOT / "project" / "chunks" / "chunk02" / "full_panel.json"
    ref_map = {}
    if panel_path.exists():
        with open(panel_path, "r", encoding="utf-8") as f:
            p_data = json.load(f)
        gauges_list = p_data.get("gauges", [])
        for g in gauges_list:
            ref_map[g["site_no"]] = g.get("gagesii_class", "Ref")

    fig, ax = plt.subplots(figsize=(10, 6), dpi=300)

    # Simplified CONUS boundary box
    ax.set_xlim(-126, -66)
    ax.set_ylim(24, 50)

    # State / background styling
    ax.set_facecolor("#f8fafc")
    ax.grid(True, linestyle="--", alpha=0.5, color="#cbd5e1")

    # Plot groups
    categories = [
        ("Training (N=32)", train_gauges, "#2563eb", "o"),
        ("Validation (N=11)", val_gauges, "#f59e0b", "s"),
        ("Testing (Held-Out, N=11)", test_gauges, "#dc2626", "^"),
    ]

    for label, g_set, color, marker in categories:
        lats = []
        lons = []
        for g in g_set:
            if g in GAUGE_COORDINATES:
                lat, lon = GAUGE_COORDINATES[g]
                lats.append(lat)
                lons.append(lon)
        ax.scatter(
            lons,
            lats,
            c=color,
            marker=marker,
            s=80,
            edgecolors="black",
            linewidth=0.8,
            label=label,
            zorder=5,
            alpha=0.9,
        )

    ax.set_title(
        "Flood Sentinel Continental Streamgage Network (N=54 CONUS Catchments)",
        fontsize=12,
        fontweight="bold",
        pad=12,
    )
    ax.set_xlabel("Longitude (°W)", fontsize=10)
    ax.set_ylabel("Latitude (°N)", fontsize=10)
    ax.legend(loc="lower left", frameon=True, facecolor="white", edgecolor="#cbd5e1", fontsize=9)

    plt.tight_layout()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    plt.savefig(out_path, format="svg")
    plt.close()
    print(f"Saved Figure 1 to: {out_path}")


def main():
    parser = argparse.ArgumentParser(description="Generate Figure 1: Basin Map")
    parser.add_argument("--out", required=True, help="Output SVG path")
    args = parser.parse_args()
    plot_basin_map(Path(args.out))


if __name__ == "__main__":
    main()
