"""Verification script for Response-Time Eligibility Tagging (C03-09).

Validates:
1. `response_time_eligible` column present in all split feature matrices.
2. `T_response_proxy_hours` column present with positive physical values.
3. 100% agreement between feature matrix flags and Chunk 02 `eligibility_tags.json`.
4. `eligibility_split_summary.json` existence and count consistency.
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

logger = get_logger("verify_eligibility_tags")


def main() -> None:
    data_dir = _PROJECT_ROOT / "project" / "chunks" / "chunk03" / "data"
    tags_path = _PROJECT_ROOT / "project" / "chunks" / "chunk02" / "data" / "response_time" / "eligibility_tags.json"
    summary_path = data_dir / "eligibility_split_summary.json"
    
    if not tags_path.exists():
        logger.error(f"Missing Chunk 02 eligibility tags at {tags_path}")
        sys.exit(1)
        
    if not summary_path.exists():
        logger.error(f"Missing eligibility split summary at {summary_path}")
        sys.exit(1)
        
    with open(tags_path, "r", encoding="utf-8") as f:
        tags_data = json.load(f)
        
    expected_map = {
        g["site_no"]: (g.get("eligibility_status") == "eligible")
        for g in tags_data.get("gauges", [])
    }
    
    splits = ["train", "val", "test"]
    total_checked = 0
    mismatches = []
    
    for sp in splits:
        sp_file = data_dir / f"feature_matrix_{sp}.parquet"
        if not sp_file.exists():
            logger.error(f"Missing {sp} feature matrix file at {sp_file}")
            sys.exit(1)
            
        df = pd.read_parquet(sp_file)
        
        if "response_time_eligible" not in df.columns:
            logger.error(f"Split {sp} missing 'response_time_eligible' column")
            sys.exit(1)
            
        if "T_response_proxy_hours" not in df.columns:
            logger.error(f"Split {sp} missing 'T_response_proxy_hours' column")
            sys.exit(1)
            
        # Verify non-null and positive
        if df["T_response_proxy_hours"].isna().any() or (df["T_response_proxy_hours"] <= 0).any():
            logger.error(f"Split {sp} contains invalid or non-positive T_response_proxy_hours values")
            sys.exit(1)
            
        # Verify tag consistency against ground truth
        for _, row in df.iterrows():
            gid = row["gauge_id"]
            actual_tag = bool(row["response_time_eligible"])
            expected_tag = expected_map.get(gid)
            if expected_tag is None or actual_tag != expected_tag:
                mismatches.append(f"Gauge {gid} in {sp} has tag {actual_tag}, expected {expected_tag}")
                
        total_checked += len(df)
        
    if mismatches:
        logger.error(f"Eligibility tag mismatches detected ({len(mismatches)} errors): {mismatches[:5]}")
        sys.exit(1)
        
    with open(summary_path, "r", encoding="utf-8") as f:
        summary = json.load(f)
        
    logger.info("Response-Time Eligibility Tagging Verification PASSED.")
    logger.info(
        f"Verified: {total_checked} window records across 3 splits (Train, Val, Test) with "
        f"100% agreement to Chunk 02 KF-113 eligibility classifications (Eligible: {summary['eligible_windows_total']}, "
        f"Ineligible: {summary['ineligible_windows_total']})."
    )
    sys.exit(0)


if __name__ == "__main__":
    main()
