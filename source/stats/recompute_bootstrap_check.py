"""Independent Recompute Script for C-STATS Moving-Block Bootstrap Engine (C07-02 / T-COMP / INV-018).

Independently loads evaluation data and runs B=10,000 moving-block bootstrap estimation over held-out
streamgages per architecture.md §4a (block length = floor(g^(1/3))) without importing production modules.
Outputs single-line JSON matching gatekeeper recompute specification.
"""

import json
import sys
from pathlib import Path
from typing import Dict, Any

import numpy as np
import pandas as pd
from sklearn.metrics import roc_auc_score

# Add project root to sys.path
_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from source.utils.config import CHUNK07_DATA_DIR


def run_independent_recompute() -> None:
    event_matrix_path = CHUNK07_DATA_DIR / "evaluation_event_matrix.parquet"
    if not event_matrix_path.exists():
        print(json.dumps({"metric_dispatch_valid": False, "bootstrap_check_valid": False, "error": "file_missing"}))
        sys.exit(1)

    df = pd.read_parquet(event_matrix_path)
    df_test = df[df["split"] == "test"].copy()
    y_true = df_test["y_flood_true"].values
    y_score = df_test["score_a_cal_iqr_max7d"].values
    gauge_ids = df_test["gauge_id"].values

    n_resamples = 10000
    seed = 42
    rng = np.random.default_rng(seed)

    unique_gauges = np.array(sorted(np.unique(gauge_ids)))
    g = len(unique_gauges)
    block_len = max(1, int(np.floor(g ** (1.0 / 3.0))))
    n_blocks_needed = int(np.ceil(g / block_len))
    gauge_row_idx = {gid: np.where(gauge_ids == gid)[0] for gid in unique_gauges}

    base_auc = float(roc_auc_score(y_true, y_score))
    boot_aucs, n_degenerate = [], 0

    for _ in range(n_resamples):
        starts = rng.integers(0, g, size=n_blocks_needed)
        selected = []
        for s in starts:
            selected.extend(unique_gauges[(s + j) % g] for j in range(block_len))
        selected = selected[:g]
        idx = np.concatenate([gauge_row_idx[gid] for gid in selected])
        y_t, y_s = y_true[idx], y_score[idx]
        if len(np.unique(y_t)) < 2:
            n_degenerate += 1
            continue
        boot_aucs.append(roc_auc_score(y_t, y_s))

    boot_aucs = np.array(boot_aucs)
    effective_n = len(boot_aucs)
    ci_low = float(np.percentile(boot_aucs, 2.5)) if effective_n > 0 else 0.5
    ci_high = float(np.percentile(boot_aucs, 97.5)) if effective_n > 0 else 0.5

    valid = bool((ci_low <= base_auc <= ci_high) and (ci_high - ci_low > 0.0) and effective_n > 0)

    result = {
        "bootstrap_method": "moving_block_bootstrap_over_gauges",
        "bootstrap_block_length": block_len,
        "bootstrap_degenerate_count": n_degenerate,
        "bootstrap_effective_n": effective_n,
        "base_auc": round(base_auc, 4),
        "ci_low": round(ci_low, 4),
        "ci_high": round(ci_high, 4),
        "resamples": n_resamples,
        "metric_dispatch_valid": valid,
        "bootstrap_check_valid": valid
    }

    print(json.dumps(result))
    if valid:
        sys.exit(0)
    else:
        sys.exit(1)


if __name__ == "__main__":
    run_independent_recompute()
