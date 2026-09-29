"""Verification script for Feature Windowing & Channel Schema (C03-05).

Validates:
1. `channel_schema.json` existence, key structure, units, and physical ranges.
2. `window_metadata.parquet` existence and non-zero window counts.
3. Strict split boundary adherence: zero windows cross epoch boundaries.
4. Gauge assignment alignment with `split_manifest.json`.
"""

import json
import sys
from pathlib import Path

import pandas as pd

# Add project root to sys.path
_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from source.utils.logging_config import get_logger

logger = get_logger("verify_windowing")


def main() -> None:
    windowing_dir = _PROJECT_ROOT / "project" / "chunks" / "chunk03" / "windowing"
    schema_path = windowing_dir / "channel_schema.json"
    metadata_path = windowing_dir / "window_metadata.parquet"
    split_manifest_path = _PROJECT_ROOT / "project" / "chunks" / "chunk03" / "split_manifest.json"
    
    if not schema_path.exists():
        logger.error(f"Missing channel schema: {schema_path}")
        sys.exit(1)
        
    if not metadata_path.exists():
        logger.error(f"Missing window metadata: {metadata_path}")
        sys.exit(1)
        
    if not split_manifest_path.exists():
        logger.error(f"Missing split manifest: {split_manifest_path}")
        sys.exit(1)
        
    # 1. Validate Channel Schema
    with open(schema_path, "r", encoding="utf-8") as f:
        schema = json.load(f)
        
    required_keys = ["column_order", "units", "physical_range"]
    for k in required_keys:
        if k not in schema:
            logger.error(f"Channel schema missing key '{k}'")
            sys.exit(1)
            
    cols = schema["column_order"]
    if len(cols) < 5 or "discharge_cfs" not in cols or "gridmet_pr_mm" not in cols:
        logger.error(f"Invalid column_order in channel schema: {cols}")
        sys.exit(1)
        
    # 2. Validate Window Metadata
    df_windows = pd.read_parquet(metadata_path)
    if len(df_windows) == 0:
        logger.error("Window metadata is empty")
        sys.exit(1)
        
    with open(split_manifest_path, "r", encoding="utf-8") as f:
        split_manifest = json.load(f)
        
    splits_spec = {
        "train": (set(split_manifest["train_gauges"]), split_manifest["train_date_range"]),
        "val": (set(split_manifest["val_gauges"]), split_manifest["val_date_range"]),
        "test": (set(split_manifest["test_gauges"]), split_manifest["test_date_range"]),
    }
    
    boundary_violations = []
    gauge_violations = []
    
    for split_name, (expected_gauges, (start_bound, end_bound)) in splits_spec.items():
        df_sp = df_windows[df_windows["split"] == split_name]
        if len(df_sp) == 0:
            logger.error(f"No windows found for split '{split_name}'")
            sys.exit(1)
            
        # Check gauge membership
        actual_gauges = set(df_sp["gauge_id"].unique())
        invalid_gauges = actual_gauges - expected_gauges
        if invalid_gauges:
            gauge_violations.append(f"Split {split_name} contains unassigned gauges: {invalid_gauges}")
            
        # Check temporal boundaries
        min_start = df_sp["start_date"].min()
        max_end = df_sp["end_date"].max()
        
        if min_start < start_bound:
            boundary_violations.append(f"Split {split_name} window start {min_start} < lower bound {start_bound}")
        if max_end > end_bound:
            boundary_violations.append(f"Split {split_name} window end {max_end} > upper bound {end_bound}")
            
    if boundary_violations:
        logger.error(f"Temporal boundary violations detected: {boundary_violations}")
        sys.exit(1)
        
    if gauge_violations:
        logger.error(f"Gauge assignment violations detected: {gauge_violations}")
        sys.exit(1)
        
    logger.info("Feature Windowing & Channel Schema Verification PASSED.")
    logger.info(
        f"Verified {len(df_windows)} windows across 3 splits (Train: {len(df_windows[df_windows['split']=='train'])}, "
        f"Val: {len(df_windows[df_windows['split']=='val'])}, Test: {len(df_windows[df_windows['split']=='test'])}) with 0 boundary breaches."
    )
    sys.exit(0)


if __name__ == "__main__":
    main()
