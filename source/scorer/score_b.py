"""Score-B: Latent Embedding Distance Engine (C05-03 / FR-010 / INV-005 / INV-022).

Computes raw and robustly calibrated latent space representation distance precursor scores across
Validation and Testing partitions using pretrained C-ENCODER representations and frozen calibration parameters.
"""

import json
import sys
from pathlib import Path
from typing import Dict, Any, List

import numpy as np
import pandas as pd
import torch

# Add project root to sys.path if running as standalone script
_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from source.model.c_encoder import CEncoderPretrainModel
from source.model.pretrain_dataset import PHYSICAL_CHANNELS
from source.scorer.calibration import load_daily_series_for_gauge
from source.utils.config import CHUNK03_DATA_DIR, CHUNK03_DIR, CHUNK04_DIR, CHUNK05_DATA_DIR, CHUNK05_DIR
from source.utils.logging_config import get_logger

logger = get_logger("score_b")


def compute_score_b_for_split(
    split_name: str,
    model: CEncoderPretrainModel,
    calibration_params: Dict[str, Any],
    norm_params: Dict[str, Any]
) -> pd.DataFrame:
    """Compute raw and calibrated Score-B time series and summary metrics for a split."""
    feature_matrix_file = CHUNK03_DATA_DIR / f"feature_matrix_{split_name}.parquet"
    if not feature_matrix_file.exists():
        raise FileNotFoundError(f"Feature matrix file missing at {feature_matrix_file}")

    df_windows = pd.read_parquet(feature_matrix_file)
    logger.info(f"Scoring Split '{split_name}' for Score-B with {len(df_windows)} windows...")

    gauge_cache: Dict[str, pd.DataFrame] = {}
    records: List[Dict[str, Any]] = []

    for idx, row in df_windows.iterrows():
        window_id = row["window_id"]
        gauge_id = row["gauge_id"]
        start_date = pd.to_datetime(row["start_date"]).tz_localize(None)
        end_date = pd.to_datetime(row["end_date"]).tz_localize(None)

        if gauge_id not in gauge_cache:
            gauge_cache[gauge_id] = load_daily_series_for_gauge(gauge_id, norm_params)

        df_gauge = gauge_cache[gauge_id]
        df_slice = df_gauge.loc[start_date:end_date, PHYSICAL_CHANNELS]
        if len(df_slice) != 365:
            full_idx = pd.date_range(start_date, periods=365, freq="D")
            df_slice = df_slice.reindex(full_idx, fill_value=0.0)

        arr = df_slice.values.astype(np.float32)
        t_in = torch.from_numpy(arr).unsqueeze(0)  # (1, 365, 6)

        with torch.no_grad():
            z = model.encoder(t_in)  # (1, 365, D)
            # Daily Euclidean embedding norm distance: (365,)
            lat_dist = torch.norm(z[0], p=2, dim=-1).numpy()

        # Calibration parameters
        cal_stats = calibration_params["gauges"].get(gauge_id, {}).get("score_b", {})
        median_cal = cal_stats.get("median", 1.0)
        iqr_cal = cal_stats.get("iqr", 1.0)
        mean_cal = cal_stats.get("mean", 1.0)
        std_cal = cal_stats.get("std", 1.0)

        # Robust IQR calibrated score sequence
        score_b_cal = (lat_dist - median_cal) / iqr_cal
        # Z-score calibrated sequence
        score_b_z = (lat_dist - mean_cal) / std_cal

        terminal_raw = float(lat_dist[-1])
        terminal_cal_iqr = float(score_b_cal[-1])
        terminal_cal_z = float(score_b_z[-1])

        max_7d_raw = float(np.max(lat_dist[-7:]))
        max_7d_cal_iqr = float(np.max(score_b_cal[-7:]))
        mean_30d_cal_iqr = float(np.mean(score_b_cal[-30:]))

        records.append({
            "window_id": window_id,
            "gauge_id": gauge_id,
            "split": split_name,
            "start_date": row["start_date"],
            "end_date": row["end_date"],
            "score_b_raw_terminal": terminal_raw,
            "score_b_cal_iqr_terminal": terminal_cal_iqr,
            "score_b_cal_z_terminal": terminal_cal_z,
            "score_b_raw_max7d": max_7d_raw,
            "score_b_cal_iqr_max7d": max_7d_cal_iqr,
            "score_b_cal_iqr_mean30d": mean_30d_cal_iqr,
            "cal_median": median_cal,
            "cal_iqr": iqr_cal,
            "response_time_eligible": row.get("response_time_eligible", False),
            "T_response_proxy_hours": row.get("T_response_proxy_hours", 0.0)
        })

    df_out = pd.DataFrame(records)
    CHUNK05_DATA_DIR.mkdir(parents=True, exist_ok=True)
    out_file = CHUNK05_DATA_DIR / f"score_b_{split_name}.parquet"
    df_out.to_parquet(out_file, index=False)
    logger.info(f"Score-B outputs written to {out_file} ({len(df_out)} rows).")
    return df_out


def run_score_b_pipeline() -> None:
    """Execute Score-B computation across Validation and Test sets."""
    logger.info("Initiating Score-B Latent Embedding Distance Pipeline...")

    # 1. Load Pretrained C-ENCODER
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

    # 2. Load Calibration Params
    cal_file = CHUNK05_DIR / "calibration_params.json"
    with open(cal_file, "r", encoding="utf-8") as f:
        cal_params = json.load(f)

    # 3. Load Normalization Params
    norm_file = CHUNK03_DIR / "normalization_params.json"
    with open(norm_file, "r", encoding="utf-8") as f:
        norm_params = json.load(f)

    # 4. Compute Val & Test
    df_val = compute_score_b_for_split("val", model, cal_params, norm_params)
    df_test = compute_score_b_for_split("test", model, cal_params, norm_params)

    # Assert non-empty and zero NaN
    assert len(df_val) == 275, f"Validation row mismatch: {len(df_val)} vs 275"
    assert len(df_test) == 539, f"Test row mismatch: {len(df_test)} vs 539"
    assert not df_val["score_b_cal_iqr_terminal"].isna().any(), "NaN found in val Score-B"
    assert not df_test["score_b_cal_iqr_terminal"].isna().any(), "NaN found in test Score-B"

    logger.info(f"Validation Score-B IQR Terminal Mean: {df_val['score_b_cal_iqr_terminal'].mean():.4f}, Std: {df_val['score_b_cal_iqr_terminal'].std():.4f}")
    logger.info(f"Test Score-B IQR Terminal Mean:       {df_test['score_b_cal_iqr_terminal'].mean():.4f}, Std: {df_test['score_b_cal_iqr_terminal'].std():.4f}")
    logger.info("Score-B Latent Embedding Distance Pipeline PASSED.")


def main() -> None:
    run_score_b_pipeline()


if __name__ == "__main__":
    main()
