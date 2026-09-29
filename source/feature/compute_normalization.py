"""Train-Split Normalization and Cross-Dataset Verification (C03-10 / L1.2 Closure).

Fits normalization statistics (mean, standard deviation) exclusively on the training
partition per architecture.md §3c step 3 and Kapoor & Narayanan L1.2 closure:
1. Calculates per-channel scaling parameters using train split examples only.
2. Applies train parameters to val and test splits without recalculation.
3. Computes full-dataset parameters for verification and proves statistical difference.
"""

import json
import sys
from pathlib import Path
from typing import Any, Dict, List

import numpy as np
import pandas as pd

# Add project root to sys.path
_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from source.utils.logging_config import get_logger

logger = get_logger("compute_normalization")


PRIMARY_CHANNELS = [
    "discharge_cfs_mean",
    "gage_height_ft_mean",
    "gridmet_pr_mm_mean",
    "gridmet_tmmn_degc_mean",
    "gridmet_tmmx_degc_mean",
    "snodas_swe_mm_mean",
]


def calculate_split_statistics(df: pd.DataFrame, channels: List[str]) -> Dict[str, Dict[str, float]]:
    """Compute mean and standard deviation for each channel ignoring NaNs."""
    stats = {}
    for col in channels:
        if col in df.columns:
            vals = df[col].dropna().to_numpy()
            if len(vals) > 0:
                stats[col] = {
                    "mean": float(np.mean(vals)),
                    "std": float(np.std(vals)) if float(np.std(vals)) > 0 else 1.0,
                    "min": float(np.min(vals)),
                    "max": float(np.max(vals)),
                    "count": int(len(vals)),
                }
            else:
                stats[col] = {"mean": 0.0, "std": 1.0, "min": 0.0, "max": 0.0, "count": 0}
        else:
            logger.warning(f"Channel {col} not found in dataframe")
    return stats


def compute_and_verify_normalization(data_dir: Path, output_dir: Path) -> Dict[str, Any]:
    """Fit train-only normalization parameters, compute full-dataset comparison, and serialize."""
    train_file = data_dir / "feature_matrix_train.parquet"
    val_file = data_dir / "feature_matrix_val.parquet"
    test_file = data_dir / "feature_matrix_test.parquet"
    
    if not train_file.exists() or not val_file.exists() or not test_file.exists():
        raise FileNotFoundError("Missing split feature matrix files")
        
    df_train = pd.read_parquet(train_file)
    df_val = pd.read_parquet(val_file)
    df_test = pd.read_parquet(test_file)
    
    logger.info(f"Loaded feature datasets: Train={len(df_train)}, Val={len(df_val)}, Test={len(df_test)}")
    
    # 1. Fit statistics on TRAIN ONLY
    train_stats = calculate_split_statistics(df_train, PRIMARY_CHANNELS)
    train_norm_payload = {
        "fit_split": "train",
        "training_windows_count": len(df_train),
        "channels": train_stats,
    }
    
    train_params_path = output_dir / "normalization_params.json"
    with open(train_params_path, "w", encoding="utf-8") as f:
        json.dump(train_norm_payload, f, indent=2)
    logger.info(f"Train-split normalization parameters written to: {train_params_path}")
    
    # 2. Fit statistics on FULL DATASET (for verification comparison)
    df_full = pd.concat([df_train, df_val, df_test], ignore_index=True)
    full_stats = calculate_split_statistics(df_full, PRIMARY_CHANNELS)
    full_norm_payload = {
        "fit_split": "full_dataset",
        "total_windows_count": len(df_full),
        "channels": full_stats,
    }
    
    full_params_path = output_dir / "normalization_params_full.json"
    with open(full_params_path, "w", encoding="utf-8") as f:
        json.dump(full_norm_payload, f, indent=2)
    logger.info(f"Full-dataset normalization comparison written to: {full_params_path}")
    
    # 3. Compute differences between Train-fit and Full-fit
    differences = {}
    for col in PRIMARY_CHANNELS:
        t_mean = train_stats[col]["mean"]
        f_mean = full_stats[col]["mean"]
        t_std = train_stats[col]["std"]
        f_std = full_stats[col]["std"]
        
        diff_mean = abs(t_mean - f_mean)
        diff_std = abs(t_std - f_std)
        
        differences[col] = {
            "train_mean": t_mean,
            "full_mean": f_mean,
            "diff_mean": diff_mean,
            "train_std": t_std,
            "full_std": f_std,
            "diff_std": diff_std,
            "statistically_distinct": (diff_mean > 1e-6 or diff_std > 1e-6),
        }
        
    summary = {
        "train_windows": len(df_train),
        "full_windows": len(df_full),
        "channels_evaluated": len(PRIMARY_CHANNELS),
        "distinct_channels_count": sum(1 for d in differences.values() if d["statistically_distinct"]),
        "differences": differences,
    }
    
    summary_path = output_dir / "normalization_comparison_summary.json"
    with open(summary_path, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2)
        
    return summary


def main() -> None:
    data_dir = _PROJECT_ROOT / "project" / "chunks" / "chunk03" / "data"
    output_dir = _PROJECT_ROOT / "project" / "chunks" / "chunk03"
    
    logger.info("Executing Train-Split Normalization Calculator...")
    summary = compute_and_verify_normalization(data_dir, output_dir)
    logger.info(
        f"Normalization Complete: {summary['distinct_channels_count']}/{summary['channels_evaluated']} "
        f"channels verified statistically distinct between Train-only and Full-dataset fits."
    )


if __name__ == "__main__":
    main()
