"""Verification script for Causal Feature Matrix Constructor (C03-06).

Validates:
1. `causal_ledger.json` existence, schema completeness, and C19 zero-exclusion audit.
2. Per-split feature matrix Parquet datasets existence and schema integrity.
3. 100% of records in usable feature matrix have `causally_valid == True`.
4. Feature matrix row count consistency across Train, Val, and Test splits.
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

logger = get_logger("verify_feature_matrix")


def main() -> None:
    data_dir = _PROJECT_ROOT / "project" / "chunks" / "chunk03" / "data"
    ledger_path = _PROJECT_ROOT / "project" / "chunks" / "chunk03" / "causal_ledger.json"
    summary_path = data_dir / "feature_matrix_summary.json"
    
    if not ledger_path.exists():
        logger.error(f"Missing causal ledger at {ledger_path}")
        sys.exit(1)
        
    if not summary_path.exists():
        logger.error(f"Missing feature matrix summary at {summary_path}")
        sys.exit(1)
        
    # 1. Validate Causal Ledger
    with open(ledger_path, "r", encoding="utf-8") as f:
        ledger = json.load(f)
        
    required_ledger_keys = [
        "ledger_version",
        "total_windows_evaluated",
        "total_feature_example_pairs",
        "causally_valid_count",
        "exclusion_count",
        "exclusion_rate_pct",
        "entries",
    ]
    for k in required_ledger_keys:
        if k not in ledger:
            logger.error(f"Causal ledger missing key '{k}'")
            sys.exit(1)
            
    if ledger["exclusion_count"] == 0:
        inv = ledger.get("zero_exclusion_investigation")
        if not inv or len(inv.strip()) == 0:
            logger.error("C19 violation: Zero exclusion count must include explicit zero_exclusion_investigation")
            sys.exit(1)
        logger.info(f"C19 Investigation Verified: {inv[:120]}...")
        
    # 2. Validate Per-Split Feature Datasets
    splits = ["train", "val", "test"]
    total_rows = 0
    
    for sp in splits:
        sp_file = data_dir / f"feature_matrix_{sp}.parquet"
        if not sp_file.exists():
            logger.error(f"Missing {sp} feature matrix file at {sp_file}")
            sys.exit(1)
            
        df = pd.read_parquet(sp_file)
        if len(df) == 0:
            logger.error(f"Feature matrix for {sp} is empty")
            sys.exit(1)
            
        # Check causally_valid flag
        if "causally_valid" not in df.columns:
            logger.error(f"Split {sp} missing 'causally_valid' column")
            sys.exit(1)
            
        invalid_count = (df["causally_valid"] != True).sum()
        if invalid_count > 0:
            logger.error(f"Split {sp} contains {invalid_count} causally invalid records")
            sys.exit(1)
            
        total_rows += len(df)
        
    if total_rows != ledger["total_windows_evaluated"]:
        logger.error(
            f"Total feature rows ({total_rows}) != evaluated windows in ledger ({ledger['total_windows_evaluated']})"
        )
        sys.exit(1)
        
    logger.info("Causal Feature Matrix Verification PASSED.")
    logger.info(
        f"Verified: {total_rows} windows across 3 splits (Train, Val, Test) with "
        f"{ledger['total_feature_example_pairs']} audited feature-example pairs and 0 leakage violations."
    )
    sys.exit(0)


if __name__ == "__main__":
    main()
