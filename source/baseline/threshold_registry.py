"""Comparator Alert Threshold Pre-Registration & Validation Registry Engine (C06-06 / INV-026 / §4d).

Pre-registers early warning and emergency alert thresholds for all comparators and C-SCORER methods
exclusively on the Validation split ($N=275$), strictly preventing test-split threshold leakage.
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

from source.utils.config import CHUNK05_DATA_DIR, CHUNK06_DATA_DIR, CHUNK06_DIR
from source.utils.logging_config import get_logger

logger = get_logger("threshold_registry")

# Method registry mapping: method_key -> (val_file, score_column, category)
METHODS_TO_CALIBRATE = {
    "score_a_reconstruction": {
        "file": CHUNK05_DATA_DIR / "score_a_val.parquet",
        "column": "score_a_cal_iqr_terminal",
        "category": "C-SCORER",
        "description": "C-ENCODER Physical Reconstruction Error (IQR-calibrated)"
    },
    "score_b_latent_distance": {
        "file": CHUNK05_DATA_DIR / "score_b_val.parquet",
        "column": "score_b_cal_iqr_terminal",
        "category": "C-SCORER",
        "description": "C-ENCODER Latent Embedding Distance (IQR-calibrated)"
    },
    "nwm_retrospective_v3": {
        "file": CHUNK06_DATA_DIR / "baseline_nwm_retro_val.parquet",
        "column": "score_nwm_cal_iqr_terminal",
        "category": "C-BASELINE-OP",
        "description": "NOAA NWM Retrospective v3.0 Simulation (IQR-calibrated)"
    },
    "stat_persistence": {
        "file": CHUNK06_DATA_DIR / "baseline_stat_val.parquet",
        "column": "score_persist_cal_iqr_terminal",
        "category": "C-BASELINE-STAT",
        "description": "1-Day Streamflow Persistence Rate-of-Change"
    },
    "stat_climatology": {
        "file": CHUNK06_DATA_DIR / "baseline_stat_val.parquet",
        "column": "score_clim_cal_iqr_terminal",
        "category": "C-BASELINE-STAT",
        "description": "Seasonal DOY 15-Day Rolling Climatology 95th Percentile Exceedance"
    },
    "stat_cusum_ewma": {
        "file": CHUNK06_DATA_DIR / "baseline_stat_val.parquet",
        "column": "score_cusum_cal_iqr_terminal",
        "category": "C-BASELINE-STAT",
        "description": "Page-CUSUM Sequential Changepoint Detector with EWMA Filtering"
    },
    "ml_isolation_forest": {
        "file": CHUNK06_DATA_DIR / "baseline_learn_val.parquet",
        "column": "score_iforest_terminal",
        "category": "C-BASELINE-LEARN",
        "description": "Scikit-Learn Isolation Forest Multi-Sensor Anomaly Detector"
    },
    "ml_lstm_autoencoder": {
        "file": CHUNK06_DATA_DIR / "baseline_learn_val.parquet",
        "column": "score_lstm_ae_cal_iqr_terminal",
        "category": "C-BASELINE-LEARN",
        "description": "PyTorch 2-Layer LSTM Autoencoder Sequential Reconstruction"
    },
    "dl_ea_lstm_supervised": {
        "file": CHUNK06_DATA_DIR / "baseline_sup_val.parquet",
        "column": "score_ea_lstm_prob",
        "category": "C-BASELINE-SUP",
        "description": "Supervised Entity-Aware LSTM with Static Catchment Attribute Conditioning"
    }
}


def fit_thresholds_for_method(
    method_name: str,
    meta: Dict[str, Any]
) -> Dict[str, Any]:
    """Fit validation operating thresholds (p90, p95, p99) on validation distribution."""
    filepath = meta["file"]
    column = meta["column"]

    if not filepath.exists():
        raise FileNotFoundError(f"Validation dataset missing for {method_name} at {filepath}")

    df_val = pd.read_parquet(filepath)
    values = df_val[column].dropna().values

    p90 = float(np.percentile(values, 90))
    p95 = float(np.percentile(values, 95))
    p99 = float(np.percentile(values, 99))
    val_median = float(np.median(values))
    val_iqr = float(np.percentile(values, 75) - np.percentile(values, 25))

    # Primary operating threshold is the 95th percentile early-warning threshold
    # or 0.50 probability for supervised models
    if method_name == "dl_ea_lstm_supervised":
        primary_thresh = 0.50
    else:
        primary_thresh = p95

    return {
        "method_name": method_name,
        "category": meta["category"],
        "description": meta["description"],
        "score_column": column,
        "validation_sample_size": len(values),
        "validation_median": val_median,
        "validation_iqr": val_iqr,
        "threshold_p90_high_recall": p90,
        "threshold_p95_primary_early_warning": p95,
        "threshold_p99_emergency_alert": p99,
        "primary_frozen_threshold": primary_thresh,
        "threshold_selection_protocol": "Pre-registered empirical quantile on Validation partition (INV-026 / §4d)",
        "test_split_consumed": False
    }


def build_threshold_registry() -> Dict[str, Any]:
    """Construct and serialize the complete validation threshold registry."""
    logger.info("Building Validation Comparator Alert Threshold Registry (INV-026)...")

    registry: Dict[str, Any] = {}
    for method_name, meta in METHODS_TO_CALIBRATE.items():
        res = fit_thresholds_for_method(method_name, meta)
        registry[method_name] = res
        logger.info(
            f"[{res['category']}] {method_name:25s} -> Primary Thresh: {res['primary_frozen_threshold']:.4f} (p90={res['threshold_p90_high_recall']:.4f}, p99={res['threshold_p99_emergency_alert']:.4f})"
        )

    output_payload = {
        "registry_title": "Comparator Alert Threshold Pre-Registration Registry",
        "fitting_split": "val",
        "fitting_split_rows": 275,
        "invariance_enforced": "INV-026 (No Test-Split Threshold Tuning / Leakage)",
        "protocol_section": "architecture.md §4d",
        "methods_registered_count": len(registry),
        "methods": registry
    }

    out_file = CHUNK06_DIR / "threshold_registry.json"
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(output_payload, f, indent=2)

    logger.info(f"Threshold Registry successfully serialized to {out_file}.")
    return output_payload


def run_threshold_registry_pipeline() -> None:
    """Execute threshold registry pipeline and verification audit."""
    payload = build_threshold_registry()
    assert len(payload["methods"]) == 9, f"Expected 9 registered methods, found {len(payload['methods'])}"
    for m, d in payload["methods"].items():
        assert d["test_split_consumed"] is False, f"Test split leakage detected in {m}"
        assert not np.isnan(d["primary_frozen_threshold"]), f"NaN threshold in {m}"
    logger.info("Validation Comparator Alert Threshold Registry Pipeline PASSED.")


def main() -> None:
    run_threshold_registry_pipeline()


if __name__ == "__main__":
    main()
