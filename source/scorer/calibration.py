"""Gauge Score Calibration Engine (C05-01 / INV-022 / FR-018).

Pre-registers calibration spans and computes robust basin-specific scaling parameters
(Median, IQR, Mean, Std) exclusively on pre-evaluation calibration windows for all 54 streamgages.
"""

import json
import sys
from pathlib import Path
from typing import Dict, Any, List, Tuple

import numpy as np
import pandas as pd
import torch

# Add project root to sys.path if running as standalone script
_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from source.model.c_encoder import CEncoderPretrainModel
from source.model.pretrain_dataset import PHYSICAL_CHANNELS
from source.utils.config import CHUNK02_DATA_DIR, CHUNK03_DIR, CHUNK04_DIR, CHUNK05_DIR
from source.utils.logging_config import get_logger

logger = get_logger("calibration")


def load_daily_series_for_gauge(gauge_id: str, norm_params: Dict[str, Any]) -> pd.DataFrame:
    """Load and normalize continuous daily observation series for a single streamgage."""
    # 1. USGS
    usgs_file = CHUNK02_DATA_DIR / "usgs" / gauge_id / "daily_streamflow.parquet"
    if usgs_file.exists():
        df_usgs = pd.read_parquet(usgs_file)[["datetime", "discharge_cfs", "gage_height_ft"]].copy()
        df_usgs["datetime"] = pd.to_datetime(df_usgs["datetime"]).dt.tz_localize(None)
    else:
        df_usgs = pd.DataFrame(columns=["datetime", "discharge_cfs", "gage_height_ft"])

    # 2. gridMET
    gridmet_file = CHUNK02_DATA_DIR / "gridmet" / gauge_id / "gridmet_daily.parquet"
    if gridmet_file.exists():
        df_gridmet = pd.read_parquet(gridmet_file)[["date", "precipitation_mm", "tmin_c", "tmax_c"]].copy()
        df_gridmet.rename(columns={"date": "datetime", "tmin_c": "temperature_min_degc", "tmax_c": "temperature_max_degc"}, inplace=True)
        df_gridmet["datetime"] = pd.to_datetime(df_gridmet["datetime"]).dt.tz_localize(None)
    else:
        df_gridmet = pd.DataFrame(columns=["datetime", "precipitation_mm", "temperature_min_degc", "temperature_max_degc"])

    # 3. SNODAS
    snodas_file = CHUNK02_DATA_DIR / "snodas" / gauge_id / "snodas_daily.parquet"
    if snodas_file.exists():
        df_snodas = pd.read_parquet(snodas_file)[["date", "swe_mm"]].copy()
        df_snodas.rename(columns={"date": "datetime"}, inplace=True)
        df_snodas["datetime"] = pd.to_datetime(df_snodas["datetime"]).dt.tz_localize(None)
    else:
        df_snodas = pd.DataFrame(columns=["datetime", "swe_mm"])

    # Merge
    df_merged = df_usgs.merge(df_gridmet, on="datetime", how="outer").merge(df_snodas, on="datetime", how="outer")
    df_merged = df_merged.sort_values("datetime").reset_index(drop=True)
    df_merged.set_index("datetime", inplace=True)

    channel_stats = {
        "discharge_cfs": (norm_params["channels"]["discharge_cfs_mean"]["mean"], norm_params["channels"]["discharge_cfs_mean"]["std"]),
        "gage_height_ft": (norm_params["channels"]["gage_height_ft_mean"]["mean"], norm_params["channels"]["gage_height_ft_mean"]["std"]),
        "precipitation_mm": (norm_params["channels"]["gridmet_pr_mm_mean"]["mean"], norm_params["channels"]["gridmet_pr_mm_mean"]["std"]),
        "temperature_min_degc": (norm_params["channels"]["gridmet_tmmn_degc_mean"]["mean"], norm_params["channels"]["gridmet_tmmn_degc_mean"]["std"]),
        "temperature_max_degc": (norm_params["channels"]["gridmet_tmmx_degc_mean"]["mean"], norm_params["channels"]["gridmet_tmmx_degc_mean"]["std"]),
        "swe_mm": (norm_params["channels"]["snodas_swe_mm_mean"]["mean"], norm_params["channels"]["snodas_swe_mm_mean"]["std"])
    }

    for col in PHYSICAL_CHANNELS:
        if col not in df_merged.columns:
            df_merged[col] = 0.0
        else:
            df_merged[col] = df_merged[col].fillna(0.0)

        mean, std = channel_stats[col]
        std_safe = std if std > 1e-6 else 1.0
        df_merged[col] = (df_merged[col] - mean) / std_safe

    return df_merged


def generate_calibration_parameters() -> Dict[str, Any]:
    """Compute and serialize calibration parameters for all 54 streamgages."""
    logger.info("Computing frozen calibration parameters for all 54 streamgages...")

    # Load split manifest
    split_manifest_path = CHUNK03_DIR / "split_manifest.json"
    with open(split_manifest_path, "r", encoding="utf-8") as f:
        split_manifest = json.load(f)

    # Load normalization params
    norm_params_path = CHUNK03_DIR / "normalization_params.json"
    with open(norm_params_path, "r", encoding="utf-8") as f:
        norm_params = json.load(f)

    # Load Pretrained C-ENCODER Checkpoint
    checkpoint_path = CHUNK04_DIR / "checkpoints" / "c_encoder_pretrained.pt"
    checkpoint = torch.load(checkpoint_path, map_location="cpu")
    model = CEncoderPretrainModel(
        in_channels=checkpoint["model_hyperparameters"]["in_channels"],
        d_model=checkpoint["model_hyperparameters"]["d_model"],
        tcn_layers=checkpoint["model_hyperparameters"]["tcn_layers"],
        transformer_layers=checkpoint["model_hyperparameters"]["transformer_layers"]
    )
    model.load_state_dict(checkpoint["model_state_dict"])
    model.eval()

    train_gauges = split_manifest["train_gauges"]
    val_gauges = split_manifest["val_gauges"]
    test_gauges = split_manifest["test_gauges"]
    all_gauges = train_gauges + val_gauges + test_gauges

    gauge_calibration_params: Dict[str, Any] = {}

    for gauge_id in all_gauges:
        # Determine calibration date window
        if gauge_id in train_gauges:
            split_type = "train"
            cal_start = pd.to_datetime("1990-01-01")
            cal_end = pd.to_datetime("2015-12-31")
        elif gauge_id in val_gauges:
            split_type = "val"
            cal_start = pd.to_datetime("2016-01-01")
            cal_end = pd.to_datetime("2016-12-31")  # First year of val period
        else:
            split_type = "test"
            cal_start = pd.to_datetime("2019-01-01")
            cal_end = pd.to_datetime("2019-12-31")  # First year of test period

        df_gauge = load_daily_series_for_gauge(gauge_id, norm_params)
        df_cal = df_gauge.loc[cal_start:cal_end, PHYSICAL_CHANNELS]

        # Extract sequence slices of length 365
        cal_days = len(df_cal)
        score_a_samples: List[float] = []
        score_b_samples: List[float] = []
        score_c_samples: List[float] = []

        # If calibration span >= 365, evaluate 365-day slices at 30-day stride
        if cal_days >= 365:
            for s_idx in range(0, cal_days - 365 + 1, 30):
                arr_slice = df_cal.iloc[s_idx:s_idx + 365].values.astype(np.float32)
                t_in = torch.from_numpy(arr_slice).unsqueeze(0)  # (1, 365, 6)
                with torch.no_grad():
                    z, x_hat = model(t_in)
                    # Score A: Reconstruction error (MSE across channels at last step)
                    rec_err = ((x_hat[0, -1] - t_in[0, -1]) ** 2).mean().item()
                    # Score B: Latent vector norm relative to origin / quiescent state
                    lat_dist = torch.norm(z[0, -1], p=2).item()
                    # Score C: Delta latent trajectory step
                    lat_delta = torch.norm(z[0, -1] - z[0, -2], p=2).item() if z.size(1) > 1 else 0.0

                    score_a_samples.append(rec_err)
                    score_b_samples.append(lat_dist)
                    score_c_samples.append(lat_delta)
        else:
            # Fallback if slice shorter than 365
            score_a_samples = [1.0]
            score_b_samples = [1.0]
            score_c_samples = [1.0]

        def compute_stats(vals: List[float]) -> Dict[str, float]:
            arr = np.array(vals, dtype=np.float64)
            q25 = float(np.percentile(arr, 25))
            median = float(np.median(arr))
            q75 = float(np.percentile(arr, 75))
            iqr = float(max(q75 - q25, 1e-4))
            mean = float(np.mean(arr))
            std = float(max(np.std(arr), 1e-4))
            return {
                "median": median,
                "iqr": iqr,
                "q25": q25,
                "q75": q75,
                "mean": mean,
                "std": std
            }

        gauge_calibration_params[gauge_id] = {
            "gauge_id": gauge_id,
            "split_type": split_type,
            "calibration_start_date": str(cal_start.date()),
            "calibration_end_date": str(cal_end.date()),
            "calibration_window_count": len(score_a_samples),
            "score_a": compute_stats(score_a_samples),
            "score_b": compute_stats(score_b_samples),
            "score_c": compute_stats(score_c_samples)
        }

    calibration_registry = {
        "calibration_protocol": "Pre-Registered Historical Calibration Span (§4c / INV-022)",
        "total_gauges_calibrated": len(gauge_calibration_params),
        "scaling_formula_iqr": "(S - median) / iqr",
        "scaling_formula_zscore": "(S - mean) / std",
        "gauges": gauge_calibration_params
    }

    CHUNK05_DIR.mkdir(parents=True, exist_ok=True)
    out_file = CHUNK05_DIR / "calibration_params.json"
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(calibration_registry, f, indent=2)

    logger.info(f"Calibration parameters for {len(gauge_calibration_params)} gauges written to {out_file}")
    return calibration_registry


def main() -> None:
    generate_calibration_parameters()


if __name__ == "__main__":
    main()
