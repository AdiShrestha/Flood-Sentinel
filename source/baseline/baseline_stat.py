"""Non-Learned Statistical Baselines Engine (C06-02 / FR-011 / NFR-006).

Implements three non-learned comparative hydrological statistical benchmarks:
1. Persistence Rate-of-Change Benchmark (Daily discharge velocity / acceleration)
2. Seasonal Day-of-Year (DOY) Climatology 95th Percentile Exceedance Benchmark
3. Page-CUSUM & EWMA Statistical Changepoint Detection (Page, 1954; Montgomery, 2009)
"""

import json
import sys
from pathlib import Path
from typing import Dict, Any, List, Tuple

import numpy as np
import pandas as pd

# Add project root to sys.path if running as standalone script
_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from source.utils.config import CHUNK02_DATA_DIR, CHUNK03_DATA_DIR, CHUNK03_DIR, CHUNK06_DATA_DIR, CHUNK06_DIR
from source.utils.logging_config import get_logger

logger = get_logger("baseline_stat")

# Statistical Hyperparameter Registry (NFR-006)
STAT_HYPERPARAMETERS = {
    "persistence": {
        "description": "Standardized 1-day rate of change in observed streamflow",
        "formula": "S_persist(t) = (Q(t) - Q(t-1)) / std(Q_cal)",
        "citation": "Standard hydrological persistence benchmark (Kroll & Vogel, 2002)"
    },
    "seasonal_climatology": {
        "description": "Day-of-year 15-day rolling window 95th percentile streamflow exceedance",
        "window_days": 15,
        "quantile": 0.95,
        "citation": "Hydrological DOY climatology exceedance (Wilks, 2011; Villarini et al., 2009)"
    },
    "cusum_ewma": {
        "description": "Page-CUSUM sequential cumulative sum with EWMA pre-filtering",
        "ewma_alpha": 0.2,
        "cusum_slack_k": 0.5,
        "citation": "Page, E. S. (1954). Continuous inspection schemes. Biometrika; Montgomery, D. C. (2009). Statistical Quality Control."
    }
}


def load_usgs_daily_discharge(gauge_id: str) -> pd.DataFrame:
    """Load continuous daily USGS discharge time series."""
    usgs_file = CHUNK02_DATA_DIR / "usgs" / gauge_id / "daily_streamflow.parquet"
    if not usgs_file.exists():
        raise FileNotFoundError(f"USGS streamflow file missing for gauge {gauge_id} at {usgs_file}")

    df = pd.read_parquet(usgs_file)[["datetime", "discharge_cfs"]].copy()
    df["datetime"] = pd.to_datetime(df["datetime"]).dt.tz_localize(None)
    df = df.sort_values("datetime").reset_index(drop=True)
    df.set_index("datetime", inplace=True)
    return df


def fit_gauge_climatology(df_cal: pd.DataFrame) -> Dict[int, float]:
    """Fit day-of-year (1-366) 95th percentile climatology using a 15-day rolling window."""
    doy_95: Dict[int, float] = {}
    df_cal = df_cal.copy()
    df_cal["doy"] = df_cal.index.dayofyear

    for doy in range(1, 367):
        # 15-day rolling window around doy
        window_doys = [(doy + offset - 1) % 366 + 1 for offset in range(-7, 8)]
        subset = df_cal[df_cal["doy"].isin(window_doys)]["discharge_cfs"].dropna()
        if len(subset) > 0:
            doy_95[doy] = float(np.percentile(subset, 95))
        else:
            doy_95[doy] = float(df_cal["discharge_cfs"].quantile(0.95))
    return doy_95


def compute_statistical_baselines_for_split(
    split_name: str,
    split_manifest: Dict[str, Any]
) -> pd.DataFrame:
    """Compute statistical baselines (Persistence, Climatology, CUSUM/EWMA) for all windows in split."""
    feature_matrix_file = CHUNK03_DATA_DIR / f"feature_matrix_{split_name}.parquet"
    if not feature_matrix_file.exists():
        raise FileNotFoundError(f"Feature matrix file missing at {feature_matrix_file}")

    df_windows = pd.read_parquet(feature_matrix_file)
    logger.info(f"Computing Statistical Baselines for split '{split_name}' ({len(df_windows)} windows)...")

    gauge_cache: Dict[str, pd.DataFrame] = {}
    clim_cache: Dict[str, Dict[int, float]] = {}
    cal_stats_cache: Dict[str, Dict[str, float]] = {}
    records: List[Dict[str, Any]] = []

    train_gauges = split_manifest["train_gauges"]
    val_gauges = split_manifest["val_gauges"]

    for idx, row in df_windows.iterrows():
        window_id = row["window_id"]
        gauge_id = row["gauge_id"]
        start_date = pd.to_datetime(row["start_date"]).tz_localize(None)
        end_date = pd.to_datetime(row["end_date"]).tz_localize(None)

        if gauge_id not in gauge_cache:
            df_full = load_usgs_daily_discharge(gauge_id)
            gauge_cache[gauge_id] = df_full

            if gauge_id in train_gauges:
                cal_s, cal_e = pd.to_datetime("1990-01-01"), pd.to_datetime("2015-12-31")
            elif gauge_id in val_gauges:
                cal_s, cal_e = pd.to_datetime("2016-01-01"), pd.to_datetime("2016-12-31")
            else:
                cal_s, cal_e = pd.to_datetime("2019-01-01"), pd.to_datetime("2019-12-31")

            df_cal = df_full.loc[cal_s:cal_e]
            clim_cache[gauge_id] = fit_gauge_climatology(df_cal)

            q_cal_vals = df_cal["discharge_cfs"].dropna().values
            cal_stats_cache[gauge_id] = {
                "median": float(np.median(q_cal_vals)) if len(q_cal_vals) > 0 else 1.0,
                "iqr": float(max(np.percentile(q_cal_vals, 75) - np.percentile(q_cal_vals, 25), 1e-4)) if len(q_cal_vals) > 0 else 1.0,
                "mean": float(np.mean(q_cal_vals)) if len(q_cal_vals) > 0 else 1.0,
                "std": float(max(np.std(q_cal_vals), 1e-4)) if len(q_cal_vals) > 0 else 1.0,
            }

        df_gauge = gauge_cache[gauge_id]
        doy_95 = clim_cache[gauge_id]
        c_stats = cal_stats_cache[gauge_id]

        # Extract 365-day slice
        df_slice = df_gauge.loc[start_date:end_date, ["discharge_cfs"]]
        if len(df_slice) != 365:
            full_idx = pd.date_range(start_date, periods=365, freq="D")
            df_slice = df_slice.reindex(full_idx)
        df_slice = df_slice.ffill().bfill().fillna(c_stats["median"])

        q = df_slice["discharge_cfs"].values.astype(np.float64)
        doys = df_slice.index.dayofyear.values

        # 1. Persistence baseline: 1-day change normalized by calibration std
        q_prev = np.roll(q, 1)
        q_prev[0] = q[0]
        s_persist = (q - q_prev) / c_stats["std"]
        s_persist_cal_iqr = (s_persist - 0.0) / (c_stats["iqr"] / c_stats["std"])

        # 2. Climatology baseline: Exceedance over DOY 95th percentile
        clim_thresh = np.array([doy_95.get(d, c_stats["median"] * 2.0) for d in doys], dtype=np.float64)
        s_clim = (q - clim_thresh) / c_stats["std"]
        s_clim_cal_iqr = s_clim  # Already centered around 95th threshold in sigma units

        # 3. Page-CUSUM with EWMA filtering (alpha=0.2, k=0.5 sigma)
        ewma_alpha = STAT_HYPERPARAMETERS["cusum_ewma"]["ewma_alpha"]
        k_slack = STAT_HYPERPARAMETERS["cusum_ewma"]["cusum_slack_k"] * c_stats["std"]

        # EWMA filter
        q_ewma = np.zeros_like(q)
        q_ewma[0] = q[0]
        for t in range(1, len(q)):
            q_ewma[t] = ewma_alpha * q[t] + (1.0 - ewma_alpha) * q_ewma[t - 1]

        # CUSUM accumulation
        cusum_pos = np.zeros_like(q)
        for t in range(1, len(q)):
            cusum_pos[t] = max(0.0, cusum_pos[t - 1] + (q_ewma[t] - c_stats["mean"]) - k_slack)
        s_cusum_cal_iqr = cusum_pos / c_stats["iqr"]

        records.append({
            "window_id": window_id,
            "gauge_id": gauge_id,
            "split": split_name,
            "start_date": row["start_date"],
            "end_date": row["end_date"],
            "score_persist_terminal": float(s_persist[-1]),
            "score_persist_cal_iqr_terminal": float(s_persist_cal_iqr[-1]),
            "score_persist_cal_iqr_max7d": float(np.max(s_persist_cal_iqr[-7:])),
            "score_clim_terminal": float(s_clim[-1]),
            "score_clim_cal_iqr_terminal": float(s_clim_cal_iqr[-1]),
            "score_clim_cal_iqr_max7d": float(np.max(s_clim_cal_iqr[-7:])),
            "score_cusum_terminal": float(cusum_pos[-1]),
            "score_cusum_cal_iqr_terminal": float(s_cusum_cal_iqr[-1]),
            "score_cusum_cal_iqr_max7d": float(np.max(s_cusum_cal_iqr[-7:])),
            "response_time_eligible": row.get("response_time_eligible", False),
            "T_response_proxy_hours": row.get("T_response_proxy_hours", 0.0)
        })

    df_out = pd.DataFrame(records)
    CHUNK06_DATA_DIR.mkdir(parents=True, exist_ok=True)
    out_file = CHUNK06_DATA_DIR / f"baseline_stat_{split_name}.parquet"
    df_out.to_parquet(out_file, index=False)
    logger.info(f"Statistical baseline outputs written to {out_file} ({len(df_out)} rows).")
    return df_out


def run_baseline_stat_pipeline() -> None:
    """Execute statistical baselines pipeline across Validation and Test sets."""
    logger.info("Executing Non-Learned Statistical Baselines Pipeline...")

    split_manifest_path = CHUNK03_DIR / "split_manifest.json"
    with open(split_manifest_path, "r", encoding="utf-8") as f:
        split_manifest = json.load(f)

    df_val = compute_statistical_baselines_for_split("val", split_manifest)
    df_test = compute_statistical_baselines_for_split("test", split_manifest)

    assert len(df_val) == 275, f"Validation row mismatch: {len(df_val)} vs 275"
    assert len(df_test) == 539, f"Test row mismatch: {len(df_test)} vs 539"

    for col in ["score_persist_cal_iqr_terminal", "score_clim_cal_iqr_terminal", "score_cusum_cal_iqr_terminal"]:
        assert not df_val[col].isna().any(), f"NaN in val {col}"
        assert not df_test[col].isna().any(), f"NaN in test {col}"

    logger.info(f"Persistence Val Mean: {df_val['score_persist_cal_iqr_terminal'].mean():.4f}, Test Mean: {df_test['score_persist_cal_iqr_terminal'].mean():.4f}")
    logger.info(f"Climatology Val Mean: {df_val['score_clim_cal_iqr_terminal'].mean():.4f}, Test Mean: {df_test['score_clim_cal_iqr_terminal'].mean():.4f}")
    logger.info(f"CUSUM/EWMA Val Mean:  {df_val['score_cusum_cal_iqr_terminal'].mean():.4f}, Test Mean: {df_test['score_cusum_cal_iqr_terminal'].mean():.4f}")
    logger.info("Non-Learned Statistical Baselines Pipeline PASSED.")


def main() -> None:
    run_baseline_stat_pipeline()


if __name__ == "__main__":
    main()
