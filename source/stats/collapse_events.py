"""Event-Level Window Collapse & Evaluation Matrix Consolidation (C07-01 / INV-023 / §4a).

Consolidates all precursor and baseline scores across Validation and Test sets,
matches ground-truth flood event episodes, collapses contiguous evaluation windows
overlapping the same physical event to eliminate pseudoreplication, and logs multi-source corroboration status.
"""

import json
import sys
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple

import numpy as np
import pandas as pd

# Add project root to sys.path if running as standalone script
_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from source.utils.config import (
    CHUNK02_DATA_DIR,
    CHUNK05_DATA_DIR,
    CHUNK06_DATA_DIR,
    CHUNK07_DATA_DIR,
    CHUNK07_DIR
)
from source.utils.logging_config import get_logger

logger = get_logger("collapse_events")


def load_and_merge_split_scores(split_name: str) -> pd.DataFrame:
    """Load and merge all score tables for a single split by window_id."""
    df_sa = pd.read_parquet(CHUNK05_DATA_DIR / f"score_a_{split_name}.parquet")
    df_sb = pd.read_parquet(CHUNK05_DATA_DIR / f"score_b_{split_name}.parquet")
    df_sc = pd.read_parquet(CHUNK05_DATA_DIR / f"score_c_{split_name}.parquet")
    df_nwm = pd.read_parquet(CHUNK06_DATA_DIR / f"baseline_nwm_retro_{split_name}.parquet")
    df_stat = pd.read_parquet(CHUNK06_DATA_DIR / f"baseline_stat_{split_name}.parquet")
    df_learn = pd.read_parquet(CHUNK06_DATA_DIR / f"baseline_learn_{split_name}.parquet")
    df_sup = pd.read_parquet(CHUNK06_DATA_DIR / f"baseline_sup_{split_name}.parquet")

    # Base on df_sa
    df_merged = df_sa[[
        "window_id", "gauge_id", "split", "start_date", "end_date",
        "score_a_raw_terminal", "score_a_cal_iqr_terminal", "score_a_cal_iqr_max7d",
        "response_time_eligible", "T_response_proxy_hours"
    ]].copy()

    # Merge Score-B
    df_merged = df_merged.merge(
        df_sb[["window_id", "score_b_raw_terminal", "score_b_cal_iqr_terminal", "score_b_cal_iqr_max7d"]],
        on="window_id"
    )

    # Merge Score-C
    df_merged = df_merged.merge(
        df_sc[["window_id", "score_c_raw_terminal", "score_c_cal_iqr_terminal", "score_c_cal_iqr_max7d"]],
        on="window_id"
    )

    # Merge NWM
    df_merged = df_merged.merge(
        df_nwm[["window_id", "score_nwm_raw_terminal", "score_nwm_cal_iqr_terminal", "score_nwm_cal_iqr_max7d"]],
        on="window_id"
    )

    # Merge Statistical
    df_merged = df_merged.merge(
        df_stat[[
            "window_id", "score_persist_terminal", "score_persist_cal_iqr_terminal", "score_persist_cal_iqr_max7d",
            "score_clim_terminal", "score_clim_cal_iqr_terminal", "score_clim_cal_iqr_max7d",
            "score_cusum_terminal", "score_cusum_cal_iqr_terminal", "score_cusum_cal_iqr_max7d"
        ]],
        on="window_id"
    )

    # Merge Unsupervised Learn
    df_merged = df_merged.merge(
        df_learn[[
            "window_id", "score_iforest_terminal", "score_iforest_cal_iqr_terminal",
            "score_lstm_ae_raw_terminal", "score_lstm_ae_cal_iqr_terminal", "score_lstm_ae_cal_iqr_max7d"
        ]],
        on="window_id"
    )

    # Merge Supervised EA-LSTM
    df_merged = df_merged.merge(
        df_sup[["window_id", "score_ea_lstm_logit", "score_ea_lstm_prob", "y_flood_true"]],
        on="window_id"
    )

    return df_merged


def match_flood_events(df_merged: pd.DataFrame, df_events: pd.DataFrame) -> Tuple[pd.DataFrame, Dict[str, int]]:
    """Match physical flood events to windows and compute corroboration stats (INV-023)."""
    df_merged = df_merged.copy()
    df_merged["start_dt"] = pd.to_datetime(df_merged["start_date"]).dt.tz_localize(None)
    df_merged["end_dt"] = pd.to_datetime(df_merged["end_date"]).dt.tz_localize(None)
    df_events["event_dt"] = pd.to_datetime(df_events["event_date"]).dt.tz_localize(None)

    event_ids: List[Optional[str]] = []
    episode_ids: List[Optional[str]] = []
    threshold_levels: List[Optional[str]] = []
    corroborations: List[Optional[str]] = []

    corrob_stats = {
        "total_windows": len(df_merged),
        "primary_event_windows": 0,
        "flash_corroborated": 0,
        "storm_events_corroborated": 0,
        "unmatched_windows": 0
    }

    for _, row in df_merged.iterrows():
        g_id = row["gauge_id"]
        end_d = row["end_dt"]

        # Matches within trailing 7 days
        matches = df_events[
            (df_events["site_no"] == g_id) &
            (df_events["event_dt"] >= end_d - pd.Timedelta(days=7)) &
            (df_events["event_dt"] <= end_d)
        ]

        if len(matches) > 0:
            m = matches.iloc[-1]
            event_ids.append(str(m["event_id"]))
            episode_ids.append(str(m.get("episode_id", m["event_id"])))
            threshold_levels.append(str(m.get("threshold_level", "Action")))
            corrob = str(m.get("corroboration", "PRIMARY_ONLY"))
            corroborations.append(corrob)

            corrob_stats["primary_event_windows"] += 1
            if "FLASH" in corrob:
                corrob_stats["flash_corroborated"] += 1
            if "STORM" in corrob:
                corrob_stats["storm_events_corroborated"] += 1
        else:
            event_ids.append(None)
            episode_ids.append(None)
            threshold_levels.append(None)
            corroborations.append(None)
            corrob_stats["unmatched_windows"] += 1

    df_merged["event_id"] = event_ids
    df_merged["episode_id"] = episode_ids
    df_merged["threshold_level"] = threshold_levels
    df_merged["corroboration"] = corroborations
    df_merged.drop(columns=["start_dt", "end_dt"], inplace=True)
    return df_merged, corrob_stats


def collapse_event_windows(df_windows: pd.DataFrame) -> pd.DataFrame:
    """Collapse contiguous evaluation windows belonging to the same flood event (INV-023 / §4a)."""
    score_cols = [
        "score_a_raw_terminal", "score_a_cal_iqr_terminal", "score_a_cal_iqr_max7d",
        "score_b_raw_terminal", "score_b_cal_iqr_terminal", "score_b_cal_iqr_max7d",
        "score_c_raw_terminal", "score_c_cal_iqr_terminal", "score_c_cal_iqr_max7d",
        "score_nwm_raw_terminal", "score_nwm_cal_iqr_terminal", "score_nwm_cal_iqr_max7d",
        "score_persist_terminal", "score_persist_cal_iqr_terminal", "score_persist_cal_iqr_max7d",
        "score_clim_terminal", "score_clim_cal_iqr_terminal", "score_clim_cal_iqr_max7d",
        "score_cusum_terminal", "score_cusum_cal_iqr_terminal", "score_cusum_cal_iqr_max7d",
        "score_iforest_terminal", "score_iforest_cal_iqr_terminal",
        "score_lstm_ae_raw_terminal", "score_lstm_ae_cal_iqr_terminal", "score_lstm_ae_cal_iqr_max7d",
        "score_ea_lstm_logit", "score_ea_lstm_prob"
    ]

    # Non-event rows remain individual observations
    non_event_df = df_windows[df_windows["y_flood_true"] == 0].copy()
    non_event_df["collapsed_instance_type"] = "quiescent_window"
    non_event_df["collapsed_windows_count"] = 1

    # Group event windows by (gauge_id, split, episode_id)
    event_df = df_windows[df_windows["y_flood_true"] == 1].copy()
    collapsed_event_records: List[Dict[str, Any]] = []

    for (g_id, split, ep_id), group in event_df.groupby(["gauge_id", "split", "episode_id"]):
        rep_row = group.iloc[-1].to_dict()
        rep_row["collapsed_instance_type"] = "collapsed_flood_event"
        rep_row["collapsed_windows_count"] = len(group)

        # Max anomaly score across contiguous windows in episode
        for col in score_cols:
            if "prob" in col:
                rep_row[col] = float(group[col].max())
            elif "logit" in col:
                rep_row[col] = float(group[col].max())
            else:
                rep_row[col] = float(group[col].max())

        collapsed_event_records.append(rep_row)

    df_collapsed_events = pd.DataFrame(collapsed_event_records)
    df_out = pd.concat([non_event_df, df_collapsed_events], ignore_index=True)
    df_out.sort_values(["split", "gauge_id", "end_date"], inplace=True)
    df_out.reset_index(drop=True, inplace=True)
    return df_out


def run_collapse_events_pipeline() -> None:
    """Consolidate scores, collapse events, and write evaluation matrices."""
    logger.info("Executing Event-Level Window Collapse Pipeline (C07-01)...")

    # 1. Load Events
    df_events = pd.read_parquet(CHUNK02_DATA_DIR / "events" / "flood_events.parquet")

    # 2. Merge validation and test splits
    df_val_merged = load_and_merge_split_scores("val")
    df_test_merged = load_and_merge_split_scores("test")

    df_val_matched, val_corrob = match_flood_events(df_val_merged, df_events)
    df_test_matched, test_corrob = match_flood_events(df_test_merged, df_events)

    df_all_windows = pd.concat([df_val_matched, df_test_matched], ignore_index=True)

    # 3. Collapse contiguous event windows
    df_collapsed = collapse_event_windows(df_all_windows)

    # Save outputs
    CHUNK07_DATA_DIR.mkdir(parents=True, exist_ok=True)
    window_matrix_file = CHUNK07_DATA_DIR / "evaluation_window_matrix.parquet"
    event_matrix_file = CHUNK07_DATA_DIR / "evaluation_event_matrix.parquet"

    df_all_windows.to_parquet(window_matrix_file, index=False)
    df_collapsed.to_parquet(event_matrix_file, index=False)

    # Summary JSON
    summary_payload = {
        "total_windows_val": len(df_val_matched),
        "total_windows_test": len(df_test_matched),
        "total_windows_combined": len(df_all_windows),
        "total_collapsed_instances": len(df_collapsed),
        "validation_corroboration": val_corrob,
        "testing_corroboration": test_corrob,
        "collapsed_event_counts": {
            "val_positive_events": int(((df_collapsed["split"] == "val") & (df_collapsed["y_flood_true"] == 1)).sum()),
            "val_negative_windows": int(((df_collapsed["split"] == "val") & (df_collapsed["y_flood_true"] == 0)).sum()),
            "test_positive_events": int(((df_collapsed["split"] == "test") & (df_collapsed["y_flood_true"] == 1)).sum()),
            "test_negative_windows": int(((df_collapsed["split"] == "test") & (df_collapsed["y_flood_true"] == 0)).sum()),
        }
    }

    summary_file = CHUNK07_DIR / "evaluation_matrix_summary.json"
    with open(summary_file, "w", encoding="utf-8") as f:
        json.dump(summary_payload, f, indent=2)

    logger.info(f"Evaluation Window Matrix serialized to {window_matrix_file} ({len(df_all_windows)} rows).")
    logger.info(f"Evaluation Event Matrix serialized to {event_matrix_file} ({len(df_collapsed)} rows).")
    logger.info(f"Summary JSON serialized to {summary_file}.")
    logger.info("Event-Level Window Collapse Pipeline PASSED.")


def main() -> None:
    run_collapse_events_pipeline()


if __name__ == "__main__":
    main()
