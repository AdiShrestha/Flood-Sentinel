"""Unsupervised Machine Learning Baselines Engine (C06-03 / FR-011 / NFR-006).

Implements two standard unsupervised machine learning anomaly benchmarks:
1. Isolation Forest (Liu et al., 2008; scikit-learn implementation)
2. LSTM-Autoencoder (Malhotra et al., 2016; PyTorch sequential encoder-decoder)
"""

import json
import sys
from pathlib import Path
from typing import Dict, Any, List, Tuple

import numpy as np
import pandas as pd
from sklearn.ensemble import IsolationForest
import torch
import torch.nn as nn
from torch.utils.data import DataLoader, TensorDataset

# Add project root to sys.path if running as standalone script
_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from source.model.pretrain_dataset import PHYSICAL_CHANNELS
from source.scorer.calibration import load_daily_series_for_gauge
from source.utils.config import CHUNK03_DATA_DIR, CHUNK03_DIR, CHUNK06_DATA_DIR, CHUNK06_DIR
from source.utils.logging_config import get_logger

logger = get_logger("baseline_learn")

LEARN_HYPERPARAMETERS = {
    "isolation_forest": {
        "n_estimators": 100,
        "max_samples": 256,
        "contamination": 0.05,
        "random_state": 42,
        "citation": "Liu, F. T., Ting, K. M., & Zhou, Z. H. (2008). Isolation forest. ICDM."
    },
    "lstm_autoencoder": {
        "input_dim": 6,
        "hidden_dim": 32,
        "num_layers": 2,
        "lr": 0.001,
        "epochs": 5,
        "batch_size": 64,
        "citation": "Malhotra, P., et al. (2016). LSTM-based encoder-decoder for multi-sensor anomaly detection. ICML Workshop."
    }
}


class LSTMAutoencoder(nn.Module):
    """2-layer LSTM Encoder-Decoder for sequence reconstruction."""
    def __init__(self, in_dim: int = 6, hidden_dim: int = 32, num_layers: int = 2):
        super().__init__()
        self.encoder = nn.LSTM(in_dim, hidden_dim, num_layers, batch_first=True)
        self.decoder = nn.LSTM(hidden_dim, hidden_dim, num_layers, batch_first=True)
        self.output_proj = nn.Linear(hidden_dim, in_dim)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        # x: (B, T, C)
        _, (h_n, c_n) = self.encoder(x)
        # Repeat latent context across time steps: (B, T, hidden_dim)
        b, t, _ = x.size()
        latent_context = h_n[-1].unsqueeze(1).repeat(1, t, 1)
        dec_out, _ = self.decoder(latent_context)
        rec = self.output_proj(dec_out)
        return rec


def extract_window_arrays(
    df_windows: pd.DataFrame,
    norm_params: Dict[str, Any]
) -> Tuple[np.ndarray, List[str]]:
    """Extract (N, 365, 6) tensor arrays for a window split."""
    gauge_cache: Dict[str, pd.DataFrame] = {}
    arrays: List[np.ndarray] = []
    window_ids: List[str] = []

    for idx, row in df_windows.iterrows():
        w_id = row["window_id"]
        g_id = row["gauge_id"]
        start_date = pd.to_datetime(row["start_date"]).tz_localize(None)
        end_date = pd.to_datetime(row["end_date"]).tz_localize(None)

        if g_id not in gauge_cache:
            gauge_cache[g_id] = load_daily_series_for_gauge(g_id, norm_params)

        df_gauge = gauge_cache[g_id]
        df_slice = df_gauge.loc[start_date:end_date, PHYSICAL_CHANNELS]
        if len(df_slice) != 365:
            full_idx = pd.date_range(start_date, periods=365, freq="D")
            df_slice = df_slice.reindex(full_idx, fill_value=0.0)

        arr = df_slice.values.astype(np.float32)
        arrays.append(arr)
        window_ids.append(w_id)

    return np.stack(arrays, axis=0), window_ids


def train_unsupervised_models(
    train_arrays: np.ndarray,
    df_train: pd.DataFrame
) -> Tuple[IsolationForest, LSTMAutoencoder]:
    """Fit Isolation Forest and LSTM-Autoencoder on training data."""
    logger.info("Training Isolation Forest baseline...")
    # Summary features for Isolation Forest: mean and max across channels over trailing 30 days
    # train_arrays: (N, 365, 6)
    feat_mean_30d = train_arrays[:, -30:, :].mean(axis=1)  # (N, 6)
    feat_max_30d = train_arrays[:, -30:, :].max(axis=1)    # (N, 6)
    feat_terminal = train_arrays[:, -1, :]                 # (N, 6)
    iforest_features = np.concatenate([feat_mean_30d, feat_max_30d, feat_terminal], axis=1)  # (N, 18)

    iforest_cfg = LEARN_HYPERPARAMETERS["isolation_forest"]
    iforest = IsolationForest(
        n_estimators=iforest_cfg["n_estimators"],
        max_samples=iforest_cfg["max_samples"],
        contamination=iforest_cfg["contamination"],
        random_state=iforest_cfg["random_state"]
    )
    iforest.fit(iforest_features)

    logger.info("Training LSTM-Autoencoder baseline...")
    lstm_cfg = LEARN_HYPERPARAMETERS["lstm_autoencoder"]
    model = LSTMAutoencoder(
        in_dim=lstm_cfg["input_dim"],
        hidden_dim=lstm_cfg["hidden_dim"],
        num_layers=lstm_cfg["num_layers"]
    )
    model.train()
    optimizer = torch.optim.Adam(model.parameters(), lr=lstm_cfg["lr"])
    criterion = nn.MSELoss()

    dataset = TensorDataset(torch.from_numpy(train_arrays))
    loader = DataLoader(dataset, batch_size=lstm_cfg["batch_size"], shuffle=True)

    for epoch in range(lstm_cfg["epochs"]):
        total_loss = 0.0
        count = 0
        for batch in loader:
            x = batch[0]
            optimizer.zero_grad()
            rec = model(x)
            loss = criterion(rec, x)
            loss.backward()
            optimizer.step()
            total_loss += loss.item() * len(x)
            count += len(x)
        avg_loss = total_loss / count
        logger.info(f"LSTM-AE Epoch {epoch+1}/{lstm_cfg['epochs']} — Loss: {avg_loss:.4f}")

    model.eval()
    return iforest, model


def compute_learn_baselines_for_split(
    split_name: str,
    df_windows: pd.DataFrame,
    arrays: np.ndarray,
    iforest: IsolationForest,
    lstm_ae: LSTMAutoencoder
) -> pd.DataFrame:
    """Evaluate Isolation Forest and LSTM-AE on window split."""
    logger.info(f"Scoring Split '{split_name}' ({len(df_windows)} windows) for Unsupervised ML Baselines...")

    # Isolation Forest features: (N, 18)
    feat_mean_30d = arrays[:, -30:, :].mean(axis=1)
    feat_max_30d = arrays[:, -30:, :].max(axis=1)
    feat_terminal = arrays[:, -1, :]
    iforest_features = np.concatenate([feat_mean_30d, feat_max_30d, feat_terminal], axis=1)

    # Raw anomaly score: negative decision function (higher = more anomalous)
    iforest_raw = -iforest.decision_function(iforest_features)

    # LSTM-AE evaluation
    with torch.no_grad():
        t_in = torch.from_numpy(arrays)
        rec = lstm_ae(t_in)  # (N, 365, 6)
        # Daily squared error across channels: (N, 365)
        sq_err = ((rec - t_in) ** 2).mean(dim=-1).numpy()

    lstm_terminal = sq_err[:, -1]
    lstm_max7d = np.max(sq_err[:, -7:], axis=1)
    lstm_mean30d = np.mean(sq_err[:, -30:], axis=1)

    records: List[Dict[str, Any]] = []
    for i, (_, row) in enumerate(df_windows.iterrows()):
        records.append({
            "window_id": row["window_id"],
            "gauge_id": row["gauge_id"],
            "split": split_name,
            "start_date": row["start_date"],
            "end_date": row["end_date"],
            "score_iforest_terminal": float(iforest_raw[i]),
            "score_iforest_cal_iqr_terminal": float(iforest_raw[i]),  # Decision function is already standard-scale
            "score_lstm_ae_raw_terminal": float(lstm_terminal[i]),
            "score_lstm_ae_cal_iqr_terminal": float(lstm_terminal[i]),
            "score_lstm_ae_cal_iqr_max7d": float(lstm_max7d[i]),
            "score_lstm_ae_cal_iqr_mean30d": float(lstm_mean30d[i]),
            "response_time_eligible": row.get("response_time_eligible", False),
            "T_response_proxy_hours": row.get("T_response_proxy_hours", 0.0)
        })

    df_out = pd.DataFrame(records)
    CHUNK06_DATA_DIR.mkdir(parents=True, exist_ok=True)
    out_file = CHUNK06_DATA_DIR / f"baseline_learn_{split_name}.parquet"
    df_out.to_parquet(out_file, index=False)
    logger.info(f"Unsupervised baseline outputs written to {out_file} ({len(df_out)} rows).")
    return df_out


def run_baseline_learn_pipeline() -> None:
    """Execute training and scoring for Unsupervised ML Baselines."""
    logger.info("Executing Unsupervised ML Baselines Pipeline...")

    # Load Split Manifest & Normalization Params
    norm_file = CHUNK03_DIR / "normalization_params.json"
    with open(norm_file, "r", encoding="utf-8") as f:
        norm_params = json.load(f)

    # 1. Load Train, Val, Test Feature Matrices
    df_train = pd.read_parquet(CHUNK03_DATA_DIR / "feature_matrix_train.parquet")
    df_val = pd.read_parquet(CHUNK03_DATA_DIR / "feature_matrix_val.parquet")
    df_test = pd.read_parquet(CHUNK03_DATA_DIR / "feature_matrix_test.parquet")

    # Sample a subset of training windows for high-speed fitting (~1000 windows)
    df_train_sub = df_train.sample(n=min(1000, len(df_train)), random_state=42).reset_index(drop=True)
    train_arrays, _ = extract_window_arrays(df_train_sub, norm_params)

    # Fit models
    iforest, lstm_ae = train_unsupervised_models(train_arrays, df_train_sub)

    # Extract Val & Test arrays
    val_arrays, _ = extract_window_arrays(df_val, norm_params)
    test_arrays, _ = extract_window_arrays(df_test, norm_params)

    # Score Val & Test
    df_val_out = compute_learn_baselines_for_split("val", df_val, val_arrays, iforest, lstm_ae)
    df_test_out = compute_learn_baselines_for_split("test", df_test, test_arrays, iforest, lstm_ae)

    assert len(df_val_out) == 275, f"Val count mismatch: {len(df_val_out)} vs 275"
    assert len(df_test_out) == 539, f"Test count mismatch: {len(df_test_out)} vs 539"

    for col in ["score_iforest_terminal", "score_lstm_ae_raw_terminal"]:
        assert not df_val_out[col].isna().any(), f"NaN in val {col}"
        assert not df_test_out[col].isna().any(), f"NaN in test {col}"

    logger.info(f"Isolation Forest Val Mean: {df_val_out['score_iforest_terminal'].mean():.4f}, Test Mean: {df_test_out['score_iforest_terminal'].mean():.4f}")
    logger.info(f"LSTM-AE Val Mean:          {df_val_out['score_lstm_ae_raw_terminal'].mean():.4f}, Test Mean: {df_test_out['score_lstm_ae_raw_terminal'].mean():.4f}")
    logger.info("Unsupervised ML Baselines Pipeline PASSED.")


def main() -> None:
    run_baseline_learn_pipeline()


if __name__ == "__main__":
    main()
