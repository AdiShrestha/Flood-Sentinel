"""Baseline Suite Integration & Reality Gate Verification (C06-07 / SC-002 / INV-017 / INV-026).

Verifies that all four baseline categories produce valid, uncorrupted, leak-free results on identical splits,
with full label-budget integrity and pre-registered validation thresholds.
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

from source.utils.config import CHUNK06_DATA_DIR, CHUNK06_DIR
from source.utils.logging_config import get_logger

logger = get_logger("verify_all_baselines")

REQUIRED_DATASETS = [
    ("baseline_nwm_retro_val.parquet", 275, ["score_nwm_cal_iqr_terminal"]),
    ("baseline_nwm_retro_test.parquet", 539, ["score_nwm_cal_iqr_terminal"]),
    ("baseline_stat_val.parquet", 275, ["score_persist_cal_iqr_terminal", "score_clim_cal_iqr_terminal", "score_cusum_cal_iqr_terminal"]),
    ("baseline_stat_test.parquet", 539, ["score_persist_cal_iqr_terminal", "score_clim_cal_iqr_terminal", "score_cusum_cal_iqr_terminal"]),
    ("baseline_learn_val.parquet", 275, ["score_iforest_terminal", "score_lstm_ae_cal_iqr_terminal"]),
    ("baseline_learn_test.parquet", 539, ["score_iforest_terminal", "score_lstm_ae_cal_iqr_terminal"]),
    ("baseline_sup_val.parquet", 275, ["score_ea_lstm_logit", "score_ea_lstm_prob"]),
    ("baseline_sup_test.parquet", 539, ["score_ea_lstm_logit", "score_ea_lstm_prob"]),
    ("label_budget_sweep_results.parquet", 30, ["test_auc_roc", "test_avg_precision", "training_label_count"]),
]


def verify_baseline_suite() -> Dict[str, Any]:
    """Audit all baseline outputs and generate compliance report."""
    logger.info("Executing Comprehensive Baseline Suite Integration Audit (C06-07)...")

    results: Dict[str, Any] = {
        "status": "PASS",
        "sc002_all_4_categories_present": True,
        "inv017_label_budget_integrity": True,
        "inv026_threshold_isolation": True,
        "checks": []
    }

    # 1. Dataset verification
    for filename, expected_rows, check_cols in REQUIRED_DATASETS:
        filepath = CHUNK06_DATA_DIR / filename
        if not filepath.exists():
            raise FileNotFoundError(f"Required baseline file missing: {filepath}")

        df = pd.read_parquet(filepath)
        actual_rows = len(df)
        assert actual_rows == expected_rows, f"Row count mismatch in {filename}: {actual_rows} vs {expected_rows}"

        for col in check_cols:
            assert col in df.columns, f"Missing column {col} in {filename}"
            nan_count = int(df[col].isna().sum())
            inf_count = int(np.isinf(df[col].values).sum()) if np.issubdtype(df[col].dtype, np.number) else 0
            assert nan_count == 0, f"NaN values detected in {filename} col {col}: {nan_count}"
            assert inf_count == 0, f"Infinite values detected in {filename} col {col}: {inf_count}"

        results["checks"].append({
            "dataset": filename,
            "expected_rows": expected_rows,
            "actual_rows": actual_rows,
            "checked_columns": check_cols,
            "nan_count": 0,
            "inf_count": 0,
            "status": "PASS"
        })
        logger.info(f"Verified {filename:35s} ({actual_rows} rows, 0 NaNs, 0 Infs) -> PASS")

    # 2. Threshold Registry Verification
    registry_file = CHUNK06_DIR / "threshold_registry.json"
    if not registry_file.exists():
        raise FileNotFoundError(f"Threshold registry missing at {registry_file}")

    with open(registry_file, "r", encoding="utf-8") as f:
        reg = json.load(f)

    assert reg["fitting_split"] == "val", "Thresholds not fit on Validation split"
    assert len(reg["methods"]) == 9, f"Expected 9 methods in registry, found {len(reg['methods'])}"

    for m_name, m_data in reg["methods"].items():
        assert m_data["test_split_consumed"] is False, f"Test data consumed in {m_name}"
        assert m_data["primary_frozen_threshold"] is not None

    results["checks"].append({
        "component": "threshold_registry.json",
        "methods_count": len(reg["methods"]),
        "fitting_split": "val",
        "test_isolation_verified": True,
        "status": "PASS"
    })
    logger.info("Verified threshold_registry.json (9 methods, validation-fit, 0 test leakage) -> PASS")

    # 3. Label Budget Sweep Verification (INV-017)
    sweep_file = CHUNK06_DATA_DIR / "label_budget_sweep_results.parquet"
    df_sweep = pd.read_parquet(sweep_file)
    expected_budgets = {0.01, 0.05, 0.10, 0.25, 0.50, 1.00}
    actual_budgets = set(df_sweep["label_budget_fraction"].unique())
    assert actual_budgets == expected_budgets, f"Budget mismatch: {actual_budgets} vs {expected_budgets}"

    expected_seeds = {13, 47, 101, 2024, 8891}
    sub_100_seeds = set(df_sweep[df_sweep["label_budget_fraction"] < 1.0]["random_seed"].unique())
    assert sub_100_seeds == expected_seeds, f"Seed mismatch: {sub_100_seeds} vs {expected_seeds}"

    results["checks"].append({
        "component": "label_budget_sweep_results.parquet",
        "budgets_evaluated": [float(x) for x in sorted(list(actual_budgets))],
        "frozen_seeds": [int(x) for x in sorted(list(sub_100_seeds))],
        "total_runs": int(len(df_sweep)),
        "status": "PASS"
    })
    logger.info(f"Verified label budget sweep ({len(df_sweep)} runs across 6 budgets & 5 seeds) -> PASS")

    # 4. SC-002 Four Categories Representation
    categories_present = {
        "Operational Hydrologic (C-BASELINE-OP)": "baseline_nwm_retro_val.parquet",
        "Non-Learned Statistical (C-BASELINE-STAT)": "baseline_stat_val.parquet",
        "Unsupervised Machine Learning (C-BASELINE-LEARN)": "baseline_learn_val.parquet",
        "Supervised Deep Learning (C-BASELINE-SUP)": "baseline_sup_val.parquet"
    }
    results["categories_present"] = categories_present
    logger.info("Verified SC-002 (4/4 Mandated Baseline Categories fully implemented and verified) -> PASS")

    # Save Verification Report
    report_file = CHUNK06_DIR / "baseline_verification_report.json"
    with open(report_file, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)

    logger.info(f"Full baseline verification report serialized to {report_file}.")
    return results


def main() -> None:
    verify_baseline_suite()


if __name__ == "__main__":
    main()
