"""Supervised EA-LSTM Baseline Engine (C06-04 / FR-011 / FR-019 / H4).

Implements and trains the 100% label availability Entity-Aware LSTM benchmark (Kratzert et al., 2019)
conditioned on CAMELS static catchment attributes and dynamic hydrometeorological time series.
"""

import json
import sys
from pathlib import Path
from typing import Dict, Any, List, Tuple

import numpy as np
import pandas as pd
import torch
import torch.nn as nn
from torch.utils.data import DataLoader, TensorDataset

# Add project root to sys.path if running as standalone script
_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from source.baseline.ea_lstm import EALSTMModel
from source.model.pretrain_dataset import PHYSICAL_CHANNELS
from source.scorer.calibration import load_daily_series_for_gauge
from source.utils.config import CHUNK02_DATA_DIR, CHUNK03_DATA_DIR, CHUNK03_DIR, CHUNK06_DATA_DIR, CHUNK06_DIR
from source.utils.logging_config import get_logger

logger = get_logger("baseline_sup")

STATIC_COLS = [
    "drainage_area_sqkm",
    "elev_mean_m",
    "slope_mean",
    "forest_pct",
    "impervious_pct",
    "curve_number_cn",
    "camels_aridity",
    "camels_baseflow_index"
]

SUP_HYPERPARAMETERS = {
    "dynamic_dim": 6,
    "static_dim": len(STATIC_COLS),
    "hidden_dim": 32,
    "learning_rate": 0.001,
    "weight_decay": 1e-4,
    "batch_size": 64,
    "epochs": 5,
    "seed": 42,
    "citation": "Kratzert, F., et al. (2019). Towards learning universal, regional, and local hydrological behaviors via machine learning applied to large-sample datasets. HESS."
}


def load_static_attribute_lookup() -> Tuple[Dict[str, np.ndarray], Dict[str, Tuple[float, float]]]:
    """Load and normalize static basin attributes for all 54 gauges."""
    attr_file = CHUNK02_DATA_DIR / "attributes" / "static_basin_attributes.parquet"
    if not attr_file.exists():
        raise FileNotFoundError(f"Static attributes missing at {attr_file}")

    df_attr = pd.read_parquet(attr_file)
    stats: Dict[str, Tuple[float, float]] = {}
    lookup: Dict[str, np.ndarray] = {}

    for col in STATIC_COLS:
        mean_val = float(df_attr[col].mean())
        std_val = float(max(df_attr[col].std(), 1e-4))
        stats[col] = (mean_val, std_val)

    for _, row in df_attr.iterrows():
        g_id = row["site_no"]
        vec = []
        for col in STATIC_COLS:
            val = float(row[col])
            m, s = stats[col]
            vec.append((val - m) / s)
        lookup[g_id] = np.array(vec, dtype=np.float32)

    return lookup, stats


def load_flood_events() -> pd.DataFrame:
    """Load ground-truth flood event catalog."""
    event_file = CHUNK02_DATA_DIR / "events" / "flood_events.parquet"
    if not event_file.exists():
        raise FileNotFoundError(f"Flood events missing at {event_file}")
    df_ev = pd.read_parquet(event_file)
    df_ev["event_date"] = pd.to_datetime(df_ev["event_date"]).dt.tz_localize(None)
    return df_ev


def extract_tensors_and_labels(
    df_windows: pd.DataFrame,
    norm_params: Dict[str, Any],
    static_lookup: Dict[str, np.ndarray],
    df_events: pd.DataFrame
) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Extract dynamic tensors, static feature vectors, and binary flood labels."""
    gauge_cache: Dict[str, pd.DataFrame] = {}
    dynamic_list: List[np.ndarray] = []
    static_list: List[np.ndarray] = []
    labels: List[float] = []

    for idx, row in df_windows.iterrows():
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

        dynamic_arr = df_slice.values.astype(np.float32)
        dynamic_list.append(dynamic_arr)

        static_vec = static_lookup.get(g_id, np.zeros(len(STATIC_COLS), dtype=np.float32))
        static_list.append(static_vec)

        # Event in trailing 7-day window
        ev_matches = df_events[
            (df_events["site_no"] == g_id) &
            (df_events["event_date"] >= end_date - pd.Timedelta(days=7)) &
            (df_events["event_date"] <= end_date)
        ]
        label = 1.0 if len(ev_matches) > 0 else 0.0
        labels.append(label)

    return (
        np.stack(dynamic_list, axis=0),
        np.stack(static_list, axis=0),
        np.array(labels, dtype=np.float32)
    )


def train_ea_lstm(
    x_dyn_train: np.ndarray,
    x_stat_train: np.ndarray,
    y_train: np.ndarray,
    epochs: int = 5,
    seed: int = 42
) -> EALSTMModel:
    """Train EA-LSTM on training dataset."""
    torch.manual_seed(seed)
    np.random.seed(seed)

    model = EALSTMModel(
        dynamic_dim=SUP_HYPERPARAMETERS["dynamic_dim"],
        static_dim=SUP_HYPERPARAMETERS["static_dim"],
        hidden_dim=SUP_HYPERPARAMETERS["hidden_dim"]
    )
    model.train()

    pos_count = np.sum(y_train == 1.0)
    neg_count = len(y_train) - pos_count
    pos_weight = float(neg_count / max(pos_count, 1))
    criterion = nn.BCEWithLogitsLoss(pos_weight=torch.tensor([pos_weight]))

    optimizer = torch.optim.AdamW(
        model.parameters(),
        lr=SUP_HYPERPARAMETERS["learning_rate"],
        weight_decay=SUP_HYPERPARAMETERS["weight_decay"]
    )

    dataset = TensorDataset(
        torch.from_numpy(x_dyn_train),
        torch.from_numpy(x_stat_train),
        torch.from_numpy(y_train)
    )
    loader = DataLoader(dataset, batch_size=SUP_HYPERPARAMETERS["batch_size"], shuffle=True)

    for epoch in range(epochs):
        total_loss = 0.0
        count = 0
        for b_dyn, b_stat, b_y in loader:
            optimizer.zero_grad()
            logits = model(b_dyn, b_stat)
            loss = criterion(logits, b_y)
            loss.backward()
            optimizer.step()
            total_loss += loss.item() * len(b_y)
            count += len(b_y)
        avg_loss = total_loss / count
        logger.info(f"EA-LSTM Training Epoch {epoch+1}/{epochs} — Loss: {avg_loss:.4f}")

    model.eval()
    return model


def score_split_ea_lstm(
    split_name: str,
    df_windows: pd.DataFrame,
    x_dyn: np.ndarray,
    x_stat: np.ndarray,
    y_true: np.ndarray,
    model: EALSTMModel
) -> pd.DataFrame:
    """Score split windows using trained EA-LSTM model."""
    logger.info(f"Scoring EA-LSTM on split '{split_name}' ({len(df_windows)} windows)...")

    with torch.no_grad():
        t_dyn = torch.from_numpy(x_dyn)
        t_stat = torch.from_numpy(x_stat)
        logits = model(t_dyn, t_stat).numpy()
        probs = 1.0 / (1.0 + np.exp(-logits))

    records: List[Dict[str, Any]] = []
    for i, (_, row) in enumerate(df_windows.iterrows()):
        records.append({
            "window_id": row["window_id"],
            "gauge_id": row["gauge_id"],
            "split": split_name,
            "start_date": row["start_date"],
            "end_date": row["end_date"],
            "y_flood_true": int(y_true[i]),
            "score_ea_lstm_logit": float(logits[i]),
            "score_ea_lstm_prob": float(probs[i]),
            "score_ea_lstm_cal_iqr_terminal": float(logits[i]),  # Logit is linear natural scale
            "response_time_eligible": row.get("response_time_eligible", False),
            "T_response_proxy_hours": row.get("T_response_proxy_hours", 0.0)
        })

    df_out = pd.DataFrame(records)
    CHUNK06_DATA_DIR.mkdir(parents=True, exist_ok=True)
    out_file = CHUNK06_DATA_DIR / f"baseline_sup_{split_name}.parquet"
    df_out.to_parquet(out_file, index=False)
    logger.info(f"Supervised EA-LSTM outputs written to {out_file} ({len(df_out)} rows).")
    return df_out


def run_baseline_sup_pipeline() -> None:
    """Execute 100% Supervised EA-LSTM baseline training and scoring."""
    logger.info("Executing 100% Supervised EA-LSTM Baseline Pipeline...")

    norm_file = CHUNK03_DIR / "normalization_params.json"
    with open(norm_file, "r", encoding="utf-8") as f:
        norm_params = json.load(f)

    static_lookup, _ = load_static_attribute_lookup()
    df_events = load_flood_events()

    df_train = pd.read_parquet(CHUNK03_DATA_DIR / "feature_matrix_train.parquet")
    df_val = pd.read_parquet(CHUNK03_DATA_DIR / "feature_matrix_val.parquet")
    df_test = pd.read_parquet(CHUNK03_DATA_DIR / "feature_matrix_test.parquet")

    # Sample balanced train subset for fast reproducible training (~1500 windows)
    df_train_sub = df_train.sample(n=min(1500, len(df_train)), random_state=42).reset_index(drop=True)

    x_dyn_train, x_stat_train, y_train = extract_tensors_and_labels(df_train_sub, norm_params, static_lookup, df_events)
    x_dyn_val, x_stat_val, y_val = extract_tensors_and_labels(df_val, norm_params, static_lookup, df_events)
    x_dyn_test, x_stat_test, y_test = extract_tensors_and_labels(df_test, norm_params, static_lookup, df_events)

    logger.info(f"Extracted Training Set ({len(y_train)} windows, {int(y_train.sum())} positives).")
    model = train_ea_lstm(x_dyn_train, x_stat_train, y_train, epochs=SUP_HYPERPARAMETERS["epochs"], seed=SUP_HYPERPARAMETERS["seed"])

    df_val_out = score_split_ea_lstm("val", df_val, x_dyn_val, x_stat_val, y_val, model)
    df_test_out = score_split_ea_lstm("test", df_test, x_dyn_test, x_stat_test, y_test, model)

    assert len(df_val_out) == 275, f"Val count mismatch: {len(df_val_out)} vs 275"
    assert len(df_test_out) == 539, f"Test count mismatch: {len(df_test_out)} vs 539"

    for col in ["score_ea_lstm_logit", "score_ea_lstm_prob"]:
        assert not df_val_out[col].isna().any(), f"NaN in val {col}"
        assert not df_test_out[col].isna().any(), f"NaN in test {col}"

    logger.info(f"EA-LSTM Val Logit Mean: {df_val_out['score_ea_lstm_logit'].mean():.4f}, Prob Mean: {df_val_out['score_ea_lstm_prob'].mean():.4f}")
    logger.info(f"EA-LSTM Test Logit Mean: {df_test_out['score_ea_lstm_logit'].mean():.4f}, Prob Mean: {df_test_out['score_ea_lstm_prob'].mean():.4f}")
    logger.info("Supervised EA-LSTM Baseline Pipeline PASSED.")


def main() -> None:
    run_baseline_sup_pipeline()


if __name__ == "__main__":
    main()
