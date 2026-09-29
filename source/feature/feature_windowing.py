"""Feature Windowing and Channel Schema Definition (C-FEATURE / C03-05).

Extracts fixed-length sliding windows over daily joined multi-source physical data
for all 54 streamgages, strictly enforcing partition boundaries per architecture.md §3c:
1. Disjoint gauge splits (train/val/test) are windowed independently.
2. Temporal boundaries are strictly respected: no window crosses epoch boundaries.
3. Standard channel schema declared with physical units and plausible physical ranges.
"""

import json
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd

# Add project root to sys.path
_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from source.utils.logging_config import get_logger

logger = get_logger("feature_windowing")

CHANNEL_SCHEMA: Dict[str, Any] = {
    "column_order": [
        "datetime",
        "discharge_cfs",
        "gage_height_ft",
        "gridmet_pr_mm",
        "gridmet_tmmn_degc",
        "gridmet_tmmx_degc",
        "snodas_swe_mm",
    ],
    "units": {
        "discharge_cfs": "cubic feet per second",
        "gage_height_ft": "feet",
        "gridmet_pr_mm": "millimeters/day",
        "gridmet_tmmn_degc": "degrees Celsius",
        "gridmet_tmmx_degc": "degrees Celsius",
        "snodas_swe_mm": "millimeters",
    },
    "physical_range": {
        "discharge_cfs": {"min": 0.0, "max": 500000.0},
        "gage_height_ft": {"min": -10.0, "max": 100.0},
        "gridmet_pr_mm": {"min": 0.0, "max": 500.0},
        "snodas_swe_mm": {"min": 0.0, "max": 3000.0},
    },
}


def load_gauge_timeseries(gauge_id: str, data_dir: Path) -> pd.DataFrame:
    """Load and join all physical daily observations for a single gauge."""
    usgs_file = data_dir / "usgs" / gauge_id / "daily_streamflow.parquet"
    gridmet_file = data_dir / "gridmet" / gauge_id / "gridmet_daily.parquet"
    snodas_file = data_dir / "snodas" / gauge_id / "snodas_daily.parquet"
    nwm_file = data_dir / "nwm_retro" / gauge_id / "nwm_retro_daily.parquet"
    
    if not usgs_file.exists() or not gridmet_file.exists():
        raise FileNotFoundError(f"Missing required primary datasets for gauge {gauge_id}")
        
    df_usgs = pd.read_parquet(usgs_file)
    df_usgs["datetime"] = pd.to_datetime(df_usgs["datetime"]).dt.strftime("%Y-%m-%d")
    
    df_gridmet = pd.read_parquet(gridmet_file)
    df_gridmet["datetime"] = pd.to_datetime(df_gridmet["date"]).dt.strftime("%Y-%m-%d")
    df_gridmet = df_gridmet.rename(columns={
        "precipitation_mm": "gridmet_pr_mm",
        "tmin_c": "gridmet_tmmn_degc",
        "tmax_c": "gridmet_tmmx_degc",
        "vintage_id": "gridmet_vintage_id",
    })
    
    # Merge USGS and gridMET
    df = pd.merge(
        df_usgs[["datetime", "site_no", "discharge_cfs", "gage_height_ft", "quality_flag"]],
        df_gridmet[["datetime", "gridmet_pr_mm", "gridmet_tmmn_degc", "gridmet_tmmx_degc", "gridmet_vintage_id"]],
        on="datetime",
        how="inner"
    )
    
    # Merge SNODAS if exists
    if snodas_file.exists():
        df_snodas = pd.read_parquet(snodas_file)
        df_snodas["datetime"] = pd.to_datetime(df_snodas["date"]).dt.strftime("%Y-%m-%d")
        df_snodas = df_snodas.rename(columns={"swe_mm": "snodas_swe_mm"})
        df = pd.merge(df, df_snodas[["datetime", "snodas_swe_mm"]], on="datetime", how="left")
        df["snodas_swe_mm"] = df["snodas_swe_mm"].fillna(0.0)
    else:
        df["snodas_swe_mm"] = 0.0
        
    # Merge NWM Retrospective if exists
    if nwm_file.exists():
        df_nwm = pd.read_parquet(nwm_file)
        df_nwm["datetime"] = pd.to_datetime(df_nwm["datetime"]).dt.strftime("%Y-%m-%d")
        df = pd.merge(df, df_nwm[["datetime", "nwm_discharge_cms"]], on="datetime", how="left")
    else:
        df["nwm_discharge_cms"] = np.nan
        
    df = df.sort_values("datetime").reset_index(drop=True)
    return df


def extract_split_windows(
    df: pd.DataFrame,
    gauge_id: str,
    split_name: str,
    date_range: List[str],
    window_length: int = 365,
    stride: int = 30,
) -> List[Dict[str, Any]]:
    """Extract fixed-length sliding windows strictly within the split's date boundaries."""
    start_date, end_date = date_range
    df_split = df[(df["datetime"] >= start_date) & (df["datetime"] <= end_date)].reset_index(drop=True)
    
    n_rows = len(df_split)
    if n_rows < window_length:
        logger.warning(
            f"Gauge {gauge_id} split {split_name} has {n_rows} rows < window length {window_length}; skipping"
        )
        return []
        
    windows = []
    window_idx = 0
    
    for start_idx in range(0, n_rows - window_length + 1, stride):
        end_idx = start_idx + window_length
        sub_df = df_split.iloc[start_idx:end_idx]
        
        w_start = sub_df["datetime"].iloc[0]
        w_end = sub_df["datetime"].iloc[-1]
        
        # Verify boundary
        if w_start < start_date or w_end > end_date:
            continue
            
        windows.append({
            "window_id": f"{gauge_id}_{split_name}_{window_idx:04d}",
            "gauge_id": gauge_id,
            "split": split_name,
            "window_idx": window_idx,
            "start_date": w_start,
            "end_date": w_end,
            "num_timesteps": len(sub_df),
            "start_row": start_idx,
            "end_row": end_idx,
        })
        window_idx += 1
        
    return windows


def build_windowed_dataset(
    data_dir: Path,
    split_manifest_path: Path,
    output_dir: Path,
    window_length: int = 365,
    stride: int = 30,
) -> Dict[str, Any]:
    """Process all gauges across splits and save windowing metadata and channel schema."""
    with open(split_manifest_path, "r", encoding="utf-8") as f:
        split_manifest = json.load(f)
        
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Save channel schema
    schema_path = output_dir / "channel_schema.json"
    with open(schema_path, "w", encoding="utf-8") as f:
        json.dump(CHANNEL_SCHEMA, f, indent=2)
    logger.info(f"Channel schema saved to: {schema_path}")
    
    splits_spec = [
        ("train", split_manifest["train_gauges"], split_manifest["train_date_range"]),
        ("val", split_manifest["val_gauges"], split_manifest["val_date_range"]),
        ("test", split_manifest["test_gauges"], split_manifest["test_date_range"]),
    ]
    
    all_windows: List[Dict[str, Any]] = []
    per_split_counts: Dict[str, int] = {"train": 0, "val": 0, "test": 0}
    per_gauge_window_counts: Dict[str, int] = {}
    
    for split_name, gauge_list, date_range in splits_spec:
        logger.info(f"Processing split '{split_name}' ({len(gauge_list)} gauges, {date_range[0]} to {date_range[1]})...")
        for gid in gauge_list:
            try:
                df = load_gauge_timeseries(gid, data_dir)
                w_list = extract_split_windows(
                    df, gid, split_name, date_range, window_length=window_length, stride=stride
                )
                all_windows.extend(w_list)
                per_split_counts[split_name] += len(w_list)
                per_gauge_window_counts[gid] = len(w_list)
            except Exception as e:
                logger.error(f"Error windowing gauge {gid}: {e}")
                raise
                
    df_windows = pd.DataFrame(all_windows)
    metadata_parquet_path = output_dir / "window_metadata.parquet"
    df_windows.to_parquet(metadata_parquet_path, index=False)
    logger.info(f"Window metadata saved to: {metadata_parquet_path} ({len(df_windows)} windows)")
    
    summary = {
        "window_length_days": window_length,
        "stride_days": stride,
        "total_windows": len(all_windows),
        "split_window_counts": per_split_counts,
        "total_gauges_processed": len(per_gauge_window_counts),
        "channel_schema": CHANNEL_SCHEMA,
    }
    
    summary_path = output_dir / "windowing_summary.json"
    with open(summary_path, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2)
        
    return summary


def main() -> None:
    data_dir = _PROJECT_ROOT / "project" / "chunks" / "chunk02" / "data"
    split_manifest_path = _PROJECT_ROOT / "project" / "chunks" / "chunk03" / "split_manifest.json"
    output_dir = _PROJECT_ROOT / "project" / "chunks" / "chunk03" / "windowing"
    
    logger.info("Executing Feature Windowing & Channel Schema Builder...")
    summary = build_windowed_dataset(data_dir, split_manifest_path, output_dir)
    logger.info(
        f"Windowing Complete: Total={summary['total_windows']} windows "
        f"(Train={summary['split_window_counts']['train']}, "
        f"Val={summary['split_window_counts']['val']}, "
        f"Test={summary['split_window_counts']['test']})"
    )


if __name__ == "__main__":
    main()
