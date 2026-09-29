"""Operational Hydrologic Baseline Engine (C06-01 / FR-011 / FR-020 / H3a / H3b).

Computes NWM Retrospective v3.0 unassimilated streamflow baseline scores across
Validation ($N=275$) and Testing ($N=539$) partitions, and records formal H3b N/A status declaration.
"""

import json
import sys
from pathlib import Path
from typing import Dict, Any, List

import numpy as np
import pandas as pd

# Add project root to sys.path if running as standalone script
_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from source.utils.config import CHUNK02_DATA_DIR, CHUNK03_DATA_DIR, CHUNK03_DIR, CHUNK06_DATA_DIR, CHUNK06_DIR
from source.utils.logging_config import get_logger

logger = get_logger("baseline_op")

H3B_DECLARATION = {
    "h3a_status": "COMMITTED_EXECUTED",
    "h3a_description": "NOAA NWM Retrospective v3.0 unassimilated physical channel routing simulations (1990-2023)",
    "h3b_status": "NOT_ATTEMPTED_ARCHIVE_UNAVAILABLE",
    "h3b_description": "Operational real-time NWPS/NWM multi-decade forecast archive unavailable with frozen origin timestamps",
    "h3b_citation": "NOAA public NWPS forecast retention limit (48h-4wk rolling window, C01-10)"
}


def load_nwm_retro_for_gauge(gauge_id: str) -> pd.DataFrame:
    """Load continuous daily NWM Retrospective v3.0 streamflow simulations."""
    nwm_file = CHUNK02_DATA_DIR / "nwm_retro" / gauge_id / "nwm_retro_daily.parquet"
    if not nwm_file.exists():
        raise FileNotFoundError(f"NWM retro file missing for gauge {gauge_id} at {nwm_file}")

    df = pd.read_parquet(nwm_file)[["datetime", "nwm_discharge_cms"]].copy()
    df.rename(columns={"nwm_discharge_cms": "streamflow_cms"}, inplace=True)
    df["datetime"] = pd.to_datetime(df["datetime"]).dt.tz_localize(None)
    df = df.sort_values("datetime").reset_index(drop=True)
    df.set_index("datetime", inplace=True)
    return df


def compute_nwm_calibration_stats(gauge_id: str, split_manifest: Dict[str, Any]) -> Dict[str, float]:
    """Compute robust calibration statistics on historical pre-evaluation spans."""
    train_gauges = split_manifest["train_gauges"]
    val_gauges = split_manifest["val_gauges"]

    if gauge_id in train_gauges:
        cal_start, cal_end = pd.to_datetime("1990-01-01"), pd.to_datetime("2015-12-31")
    elif gauge_id in val_gauges:
        cal_start, cal_end = pd.to_datetime("2016-01-01"), pd.to_datetime("2016-12-31")
    else:
        cal_start, cal_end = pd.to_datetime("2019-01-01"), pd.to_datetime("2019-12-31")

    df_gauge = load_nwm_retro_for_gauge(gauge_id)
    cal_series = df_gauge.loc[cal_start:cal_end, "streamflow_cms"].dropna().values

    if len(cal_series) == 0:
        return {"median": 1.0, "iqr": 1.0, "mean": 1.0, "std": 1.0}

    q25 = float(np.percentile(cal_series, 25))
    median = float(np.median(cal_series))
    q75 = float(np.percentile(cal_series, 75))
    iqr = float(max(q75 - q25, 1e-4))
    mean = float(np.mean(cal_series))
    std = float(max(np.std(cal_series), 1e-4))

    return {
        "median": median,
        "iqr": iqr,
        "mean": mean,
        "std": std
    }


def compute_nwm_retro_for_split(
    split_name: str,
    split_manifest: Dict[str, Any]
) -> pd.DataFrame:
    """Compute NWM Retrospective baseline scores across all windows in a split."""
    feature_matrix_file = CHUNK03_DATA_DIR / f"feature_matrix_{split_name}.parquet"
    if not feature_matrix_file.exists():
        raise FileNotFoundError(f"Feature matrix file missing at {feature_matrix_file}")

    df_windows = pd.read_parquet(feature_matrix_file)
    logger.info(f"Computing NWM Retrospective baseline for split '{split_name}' ({len(df_windows)} windows)...")

    gauge_cache: Dict[str, pd.DataFrame] = {}
    cal_cache: Dict[str, Dict[str, float]] = {}
    records: List[Dict[str, Any]] = []

    for idx, row in df_windows.iterrows():
        window_id = row["window_id"]
        gauge_id = row["gauge_id"]
        start_date = pd.to_datetime(row["start_date"]).tz_localize(None)
        end_date = pd.to_datetime(row["end_date"]).tz_localize(None)

        if gauge_id not in gauge_cache:
            gauge_cache[gauge_id] = load_nwm_retro_for_gauge(gauge_id)
            cal_cache[gauge_id] = compute_nwm_calibration_stats(gauge_id, split_manifest)

        df_gauge = gauge_cache[gauge_id]
        cal_stats = cal_cache[gauge_id]

        df_slice = df_gauge.loc[start_date:end_date, "streamflow_cms"]
        if len(df_slice) != 365:
            full_idx = pd.date_range(start_date, periods=365, freq="D")
            df_slice = df_slice.reindex(full_idx)
        df_slice = df_slice.ffill().bfill().fillna(cal_stats["median"])

        q_nwm = df_slice.values.astype(np.float32)

        # Calibrated anomaly score sequence
        s_nwm_cal = (q_nwm - cal_stats["median"]) / cal_stats["iqr"]

        terminal_raw = float(q_nwm[-1])
        terminal_cal_iqr = float(s_nwm_cal[-1])
        max_7d_cal_iqr = float(np.max(s_nwm_cal[-7:]))
        mean_30d_cal_iqr = float(np.mean(s_nwm_cal[-30:]))

        records.append({
            "window_id": window_id,
            "gauge_id": gauge_id,
            "split": split_name,
            "start_date": row["start_date"],
            "end_date": row["end_date"],
            "baseline_type": "operational_hydrologic_nwm_retro_v3",
            "score_nwm_raw_terminal": terminal_raw,
            "score_nwm_cal_iqr_terminal": terminal_cal_iqr,
            "score_nwm_cal_iqr_max7d": max_7d_cal_iqr,
            "score_nwm_cal_iqr_mean30d": mean_30d_cal_iqr,
            "cal_median": cal_stats["median"],
            "cal_iqr": cal_stats["iqr"],
            "response_time_eligible": row.get("response_time_eligible", False),
            "T_response_proxy_hours": row.get("T_response_proxy_hours", 0.0),
            "h3b_status": H3B_DECLARATION["h3b_status"]
        })

    df_out = pd.DataFrame(records)
    CHUNK06_DATA_DIR.mkdir(parents=True, exist_ok=True)
    out_file = CHUNK06_DATA_DIR / f"baseline_nwm_retro_{split_name}.parquet"
    df_out.to_parquet(out_file, index=False)
    logger.info(f"NWM Retrospective outputs written to {out_file} ({len(df_out)} rows).")
    return df_out


def run_baseline_op_pipeline() -> None:
    """Execute NWM Retrospective baseline generation across Validation and Test sets."""
    logger.info("Executing Operational Hydrologic Baseline Pipeline...")

    split_manifest_path = CHUNK03_DIR / "split_manifest.json"
    with open(split_manifest_path, "r", encoding="utf-8") as f:
        split_manifest = json.load(f)

    df_val = compute_nwm_retro_for_split("val", split_manifest)
    df_test = compute_nwm_retro_for_split("test", split_manifest)

    assert len(df_val) == 275, f"Validation row mismatch: {len(df_val)} vs 275"
    assert len(df_test) == 539, f"Test row mismatch: {len(df_test)} vs 539"
    assert not df_val["score_nwm_cal_iqr_terminal"].isna().any(), "NaN in val NWM scores"
    assert not df_test["score_nwm_cal_iqr_terminal"].isna().any(), "NaN in test NWM scores"

    logger.info(f"Validation NWM IQR Terminal Mean: {df_val['score_nwm_cal_iqr_terminal'].mean():.4f}, Std: {df_val['score_nwm_cal_iqr_terminal'].std():.4f}")
    logger.info(f"Test NWM IQR Terminal Mean:       {df_test['score_nwm_cal_iqr_terminal'].mean():.4f}, Std: {df_test['score_nwm_cal_iqr_terminal'].std():.4f}")
    logger.info(f"H3b Status Declaration: {H3B_DECLARATION['h3b_status']} ({H3B_DECLARATION['h3b_citation']})")
    logger.info("Operational Hydrologic Baseline Pipeline PASSED.")


def main() -> None:
    run_baseline_op_pipeline()


if __name__ == "__main__":
    main()
