"""Verification script for Information-State Vintage Ledger (C03-08).

Validates:
1. `vintage_ledger.json` existence and schema completeness.
2. Zero untagged or ambiguous entries (default-never-valid discipline).
3. Separate reporting of operational-claim vs retrospective-claim exclusions.
4. Pre-2013 gridMET entries strictly tagged `vintage_valid: false` (KF-021).
5. Post-2013 gridMET entries tagged `vintage_valid: true` (KF-021).
"""

import json
import sys
from pathlib import Path

# Add project root to sys.path
_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from source.utils.logging_config import get_logger

logger = get_logger("verify_vintage_ledger")


def main() -> None:
    ledger_path = _PROJECT_ROOT / "project" / "chunks" / "chunk03" / "vintage_ledger.json"
    
    if not ledger_path.exists():
        logger.error(f"Missing vintage ledger at {ledger_path}")
        sys.exit(1)
        
    with open(ledger_path, "r", encoding="utf-8") as f:
        ledger = json.load(f)
        
    required_keys = [
        "ledger_version",
        "total_audited_entries",
        "retrospective_claim_eligible_count",
        "operational_claim_eligible_count",
        "vintage_exclusion_count",
        "entries",
    ]
    for k in required_keys:
        if k not in ledger:
            logger.error(f"Vintage ledger missing key '{k}'")
            sys.exit(1)
            
    entries = ledger.get("entries", [])
    if len(entries) == 0:
        logger.error("Vintage ledger contains zero entries")
        sys.exit(1)
        
    untagged_count = 0
    pre2013_gridmet_invalid_count = 0
    post2013_gridmet_valid_count = 0
    
    for entry in entries:
        v_id = entry.get("vintage_id")
        if not v_id or v_id == "unclassified":
            untagged_count += 1
            
        src = entry.get("source_channel")
        obs_date = entry.get("t_observation", "")[:10]
        
        if src in ("gridmet_pr", "gridmet_tmmn", "gridmet_tmmx"):
            if obs_date < "2013-01-01":
                if entry.get("vintage_valid") is not False or entry.get("vintage_id") != "pre_nrt_reanalysis_only":
                    pre2013_gridmet_invalid_count += 1
            else:
                if entry.get("vintage_valid") is not True or entry.get("vintage_id") != "nrt_proxy_available":
                    post2013_gridmet_valid_count += 1
                    
    if untagged_count > 0:
        logger.error(f"Default-Never-Valid violation: {untagged_count} entries lack explicit vintage_id")
        sys.exit(1)
        
    if pre2013_gridmet_invalid_count > 0:
        logger.error(f"KF-021 violation: {pre2013_gridmet_invalid_count} pre-2013 gridMET entries incorrectly marked valid")
        sys.exit(1)
        
    if post2013_gridmet_valid_count > 0:
        logger.error(f"KF-021 violation: {post2013_gridmet_valid_count} post-2013 gridMET entries incorrectly marked invalid")
        sys.exit(1)
        
    logger.info("Information-State Vintage Ledger Verification PASSED.")
    logger.info(
        f"Verified: {len(entries)} entries audited with 0 untagged items. "
        f"Operational Eligible={ledger['operational_claim_eligible_count']}, "
        f"Retrospective Eligible={ledger['retrospective_claim_eligible_count']}, "
        f"Vintage Exclusions for Operational Claims={ledger['vintage_exclusion_count']}."
    )
    sys.exit(0)


if __name__ == "__main__":
    main()
