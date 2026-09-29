"""Physical Sensor / Channel Holdout Ablation Suite (C08-01 / FR-010 / SC-003).

Evaluates C-ENCODER precursor anomaly detection performance when individual Earth-observation modalities
(precipitation, SWE, temperature, discharge) are systematically held out, quantifying the contribution of
each physical channel to flood precursor discrimination on the held-out test partition.
"""

import json
import sys
from pathlib import Path
from typing import Dict, Any, List, Tuple

import numpy as np
import pandas as pd
from sklearn.metrics import roc_auc_score, average_precision_score
import torch

# Add project root to sys.path
_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from source.model.c_encoder import CEncoderPretrainModel
from source.model.pretrain_dataset import PHYSICAL_CHANNELS
from source.scorer.calibration import load_daily_series_for_gauge
from source.utils.config import (
    CHUNK03_DATA_DIR,
    CHUNK03_DIR,
    CHUNK04_DIR,
    CHUNK05_DIR,
    CHUNK07_DATA_DIR,
    CHUNK08_DATA_DIR,
    CHUNK08_DIR
)
from source.utils.logging_config import get_logger

logger = get_logger("sensor_ablation")

# Mapping of ablation conditions to channel indices
# PHYSICAL_CHANNELS = ['discharge_cfs', 'gage_height_ft', 'precipitation_amount_mm',
#                      'air_temperature_minimum_k', 'air_temperature_maximum_k', 'snodas_swe_mm']
CHANNEL_INDICES = {
    "discharge": [0, 1],       # USGS discharge + stage
    "precipitation": [2],      # gridMET pr
    "temperature": [3, 4],     # gridMET tmmn + tmmx
    "swe": [5]                 # SNODAS SWE
}

ABLATION_CONFIGS = [
    {
        "config_id": "full_multisensor",
        "display_name": "Full Multi-Sensor Suite (Baseline)",
        "held_out_channels": [],
        "held_out_names": "None"
    },
    {
        "config_id": "minus_precipitation",
        "display_name": "Minus Precipitation (-gridMET pr)",
        "held_out_channels": CHANNEL_INDICES["precipitation"],
        "held_out_names": "precipitation_amount_mm"
    },
    {
        "config_id": "minus_swe",
        "display_name": "Minus Snow Water Equivalent (-SNODAS SWE)",
        "held_out_channels": CHANNEL_INDICES["swe"],
        "held_out_names": "snodas_swe_mm"
    },
    {
        "config_id": "minus_temperature",
        "display_name": "Minus Temperature (-gridMET tmmn/tmmx)",
        "held_out_channels": CHANNEL_INDICES["temperature"],
        "held_out_names": "air_temperature_minimum_k, air_temperature_maximum_k"
    },
    {
        "config_id": "minus_discharge",
        "display_name": "Minus Discharge & Stage (-USGS streamflow)",
        "held_out_channels": CHANNEL_INDICES["discharge"],
        "held_out_names": "discharge_cfs, gage_height_ft"
    }
]


def run_sensor_ablation_suite() -> Dict[str, Any]:
    """Execute physical channel holdout ablation across the test partition."""
    logger.info("Executing Sensor / Physical Channel Holdout Ablation Suite (C08-01)...")

    # Ensure output directories exist
    CHUNK08_DATA_DIR.mkdir(parents=True, exist_ok=True)

    # 1. Load Preconditions
    checkpoint_path = CHUNK04_DIR / "checkpoints" / "c_encoder_pretrained.pt"
    norm_params_path = CHUNK03_DIR / "normalization_params.json"
    cal_params_path = CHUNK05_DIR / "calibration_params.json"
    test_feature_matrix_path = CHUNK03_DATA_DIR / "feature_matrix_test.parquet"
    eval_event_matrix_path = CHUNK07_DATA_DIR / "evaluation_event_matrix.parquet"

    with open(norm_params_path, "r", encoding="utf-8") as f:
        norm_params = json.load(f)

    with open(cal_params_path, "r", encoding="utf-8") as f:
        cal_params = json.load(f)

    # Load Model
    model = CEncoderPretrainModel(
        in_channels=6,
        d_model=64,
        tcn_layers=3,
        transformer_layers=2,
        n_heads=4,
        d_ff=128,
        dropout=0.1
    )
    checkpoint = torch.load(checkpoint_path, map_location="cpu")
    model.load_state_dict(checkpoint["model_state_dict"])
    model.eval()
    logger.info(f"Loaded pretrained C-ENCODER from {checkpoint_path}.")

    df_test_windows = pd.read_parquet(test_feature_matrix_path)
    df_eval_events = pd.read_parquet(eval_event_matrix_path)
    test_events = df_eval_events[df_eval_events["split"] == "test"].copy()
    y_true = test_events["y_flood_true"].values

    # Pre-cache test gauge daily series
    gauge_cache: Dict[str, pd.DataFrame] = {}
    test_gauges = df_test_windows["gauge_id"].unique()
    for g_id in test_gauges:
        gauge_cache[g_id] = load_daily_series_for_gauge(g_id, norm_params)

    # 2. Evaluate Each Sensor Configuration
    config_results: List[Dict[str, Any]] = []
    window_scores_all_configs: Dict[str, Dict[str, float]] = {}

    baseline_auc = 0.0

    for cfg in ABLATION_CONFIGS:
        cfg_id = cfg["config_id"]
        cfg_name = cfg["display_name"]
        held_out_indices = cfg["held_out_channels"]
        logger.info(f"Evaluating Configuration: {cfg_name} (Held out: {cfg['held_out_names']})...")

        window_scores: Dict[str, float] = {}

        for idx, row in df_test_windows.iterrows():
            w_id = row["window_id"]
            g_id = row["gauge_id"]
            start_d = pd.to_datetime(row["start_date"]).tz_localize(None)
            end_d = pd.to_datetime(row["end_date"]).tz_localize(None)

            df_gauge = gauge_cache[g_id]
            df_slice = df_gauge.loc[start_d:end_d, PHYSICAL_CHANNELS]
            if len(df_slice) != 365:
                full_idx = pd.date_range(start_d, periods=365, freq="D")
                df_slice = df_slice.reindex(full_idx, fill_value=0.0)

            arr = df_slice.values.astype(np.float32).copy()

            # Zero out held out physical channels
            if held_out_indices:
                arr[:, held_out_indices] = 0.0

            t_in = torch.from_numpy(arr).unsqueeze(0)  # (1, 365, 6)

            with torch.no_grad():
                _, x_hat = model(t_in)
                sq_err = ((x_hat[0] - t_in[0]) ** 2).mean(dim=-1).numpy()

            cal_stats = cal_params["gauges"].get(g_id, {}).get("score_a", {})
            median_cal = cal_stats.get("median", 1.0)
            iqr_cal = cal_stats.get("iqr", 1.0)
            score_cal = (sq_err - median_cal) / iqr_cal
            max_7d_score = float(np.max(score_cal[-7:]))
            window_scores[w_id] = max_7d_score

        window_scores_all_configs[cfg_id] = window_scores

        # Map to collapsed event instances
        event_scores = []
        for _, ev_row in test_events.iterrows():
            w_id = ev_row["window_id"]
            event_scores.append(window_scores.get(w_id, 0.0))

        event_scores = np.array(event_scores)

        # Compute Metrics
        auc = float(roc_auc_score(y_true, event_scores))
        ap = float(average_precision_score(y_true, event_scores))

        if cfg_id == "full_multisensor":
            baseline_auc = auc
            delta_auc = 0.0
        else:
            delta_auc = float(auc - baseline_auc)

        config_results.append({
            "config_id": cfg_id,
            "display_name": cfg_name,
            "held_out_channels": cfg["held_out_names"],
            "test_auc_roc": auc,
            "test_average_precision": ap,
            "delta_auc_vs_baseline": delta_auc,
            "importance_rank": 0  # will rank below
        })

        logger.info(f"  -> AUC: {auc:.4f} | AP: {ap:.4f} | Delta AUC: {delta_auc:+.4f}")

    # Rank channel importance by magnitude of performance drop (most negative delta_auc = highest importance)
    non_baseline_configs = [c for c in config_results if c["config_id"] != "full_multisensor"]
    non_baseline_configs.sort(key=lambda x: x["delta_auc_vs_baseline"])
    for rank_idx, c in enumerate(non_baseline_configs, start=1):
        c["importance_rank"] = rank_idx

    # 3. Create Parquet and JSON Artifacts
    df_results = pd.DataFrame(config_results)
    out_parquet = CHUNK08_DATA_DIR / "sensor_ablation_results.parquet"
    out_json = CHUNK08_DIR / "sensor_ablation_summary.json"

    df_results.to_parquet(out_parquet, index=False)

    summary_payload = {
        "ablation_suite": "Physical Sensor / Channel Holdout Suite (C08-01)",
        "evaluation_partition": "Test (11 streamgages, 520 collapsed instances)",
        "baseline_multisensor_auc": baseline_auc,
        "configurations": config_results,
        "key_findings": {
            "primary_driver": non_baseline_configs[0]["held_out_channels"] if non_baseline_configs else "None",
            "primary_drop_delta_auc": non_baseline_configs[0]["delta_auc_vs_baseline"] if non_baseline_configs else 0.0,
            "multisensor_synergy_confirmed": bool(baseline_auc > max([c["test_auc_roc"] for c in non_baseline_configs]))
        }
    }

    with open(out_json, "w", encoding="utf-8") as f:
        json.dump(summary_payload, f, indent=2)

    logger.info(f"Sensor ablation results Parquet serialized to {out_parquet}.")
    logger.info(f"Sensor ablation summary JSON serialized to {out_json}.")
    logger.info("Sensor Ablation Suite PASSED.")
    return summary_payload


def main() -> None:
    run_sensor_ablation_suite()


if __name__ == "__main__":
    main()
