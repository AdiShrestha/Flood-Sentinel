"""Verification script for Leakage-Safe Split (C-SPLIT / C03-02).

Validates:
1. `split_manifest.json` existence and schema completeness.
2. All 54 gauges from `full_panel.json` accounted for across train/val/test.
3. Zero cross-split gauge collisions (mutual disjointness).
4. Reference and Non-Reference representation in all three partitions.
5. Non-overlapping temporal boundaries.
6. `generated_before_windowing` and `duplicate_check_passed` flags.
"""

import json
import sys
from pathlib import Path

# Add project root to sys.path
_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from source.feature.split_generator import verify_gauge_disjointness, verify_temporal_disjointness
from source.utils.logging_config import get_logger

logger = get_logger("verify_split")


def main() -> None:
    manifest_path = _PROJECT_ROOT / "project" / "chunks" / "chunk03" / "split_manifest.json"
    panel_path = _PROJECT_ROOT / "project" / "chunks" / "chunk02" / "full_panel.json"
    
    if not manifest_path.exists():
        logger.error(f"Missing split manifest: {manifest_path}")
        sys.exit(1)
        
    if not panel_path.exists():
        logger.error(f"Missing full panel file: {panel_path}")
        sys.exit(1)
        
    with open(manifest_path, "r", encoding="utf-8") as f:
        manifest = json.load(f)
        
    with open(panel_path, "r", encoding="utf-8") as f:
        panel = json.load(f)
        
    # Check top-level required fields
    required_keys = [
        "split_id", "method", "random_seed", "stratification_variable",
        "train_gauges", "val_gauges", "test_gauges",
        "train_date_range", "val_date_range", "test_date_range",
        "generated_before_windowing", "duplicate_check_passed",
        "train_gauge_count", "val_gauge_count", "test_gauge_count",
        "total_gauges"
    ]
    missing_keys = [k for k in required_keys if k not in manifest]
    if missing_keys:
        logger.error(f"Split manifest missing required keys: {missing_keys}")
        sys.exit(1)
        
    if not manifest.get("generated_before_windowing"):
        logger.error("Manifest must declare generated_before_windowing: true")
        sys.exit(1)
        
    if not manifest.get("duplicate_check_passed"):
        logger.error("Manifest must declare duplicate_check_passed: true")
        sys.exit(1)
        
    # Verify gauge counts
    panel_gauges = [g["site_no"] for g in panel.get("gauges", [])]
    expected_total = len(panel_gauges)
    if manifest["total_gauges"] != expected_total:
        logger.error(f"Total gauges in manifest ({manifest['total_gauges']}) != panel ({expected_total})")
        sys.exit(1)
        
    train_gauges = manifest["train_gauges"]
    val_gauges = manifest["val_gauges"]
    test_gauges = manifest["test_gauges"]
    
    if len(train_gauges) != manifest["train_gauge_count"]:
        logger.error("train_gauges list length does not match train_gauge_count")
        sys.exit(1)
    if len(val_gauges) != manifest["val_gauge_count"]:
        logger.error("val_gauges list length does not match val_gauge_count")
        sys.exit(1)
    if len(test_gauges) != manifest["test_gauge_count"]:
        logger.error("test_gauges list length does not match test_gauge_count")
        sys.exit(1)
        
    # Verify disjointness
    disjoint_passed, gauge_errors = verify_gauge_disjointness(
        train_gauges, val_gauges, test_gauges, panel_gauges
    )
    if not disjoint_passed:
        logger.error(f"Gauge disjointness check failed: {gauge_errors}")
        sys.exit(1)
        
    # Verify temporal disjointness
    temp_passed, temp_errors = verify_temporal_disjointness(
        manifest["train_date_range"],
        manifest["val_date_range"],
        manifest["test_date_range"],
    )
    if not temp_passed:
        logger.error(f"Temporal disjointness check failed: {temp_errors}")
        sys.exit(1)
        
    # Verify Ref / Non-Ref representation
    panel_ref_map = {g["site_no"]: g.get("gagesii_class") for g in panel.get("gauges", [])}
    for split_name, g_list in [("train", train_gauges), ("val", val_gauges), ("test", test_gauges)]:
        ref_count = sum(1 for g in g_list if panel_ref_map.get(g) == "Ref")
        nonref_count = sum(1 for g in g_list if panel_ref_map.get(g) == "Non-Ref")
        if ref_count == 0 or nonref_count == 0:
            logger.error(f"Split {split_name} lacks balanced representation (Ref={ref_count}, Non-Ref={nonref_count})")
            sys.exit(1)
            
    logger.info("Leakage-Safe Split Verification PASSED.")
    logger.info(
        f"Verified: 54 gauges partitioned into Train ({manifest['train_gauge_count']}), "
        f"Val ({manifest['val_gauge_count']}), Test ({manifest['test_gauge_count']}) with 0 cross-split collisions."
    )
    sys.exit(0)


if __name__ == "__main__":
    main()
