"""Information-State Vintage Ledger Builder (C-FEATURE / C03-08).

Implements the Forecast Origin Contract and Information-State Vintage Ledger
per architecture.md §3d and Invariant INV-021 (Information-State Vintage Isolation):
1. Delineates retrospective-analytic validity from operational-real-time validity.
2. Applies pre-/post-2013 vintage tags for gridMET (KF-021).
3. Tags USGS provisional/approved rating-curve revision status (KF-022).
4. Emits vintage_ledger.json with separate exclusion counts for operational vs retrospective claims.
"""

import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import pandas as pd

# Add project root to sys.path
_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from source.utils.logging_config import get_logger

logger = get_logger("vintage_ledger")

GRIDMET_NRT_BOUNDARY = "2013-01-01"


def evaluate_feature_vintage(
    source_channel: str,
    t_observation_iso: str,
    t_availability_iso: str,
    causally_valid: bool = True,
    feature_name: str = "feature",
    example_id: str = "ex_001",
) -> Dict[str, Any]:
    """Evaluate information-state vintage classification for a single feature observation."""
    obs_date_str = t_observation_iso[:10]
    
    if source_channel in ("usgs_discharge", "usgs_gage_height"):
        vintage_id = "provisional_at_acquisition_unknown"
        vintage_valid = False
        violation_reason = (
            f"Value retrieved via Water Data API in 2026 reflects current approved status; "
            f"USGS approval/revision history for site-date {obs_date_str} not independently confirmed "
            f"to match real-time operational rating curve state (KF-022)."
        )
        info_cutoff = t_observation_iso
        
    elif source_channel in ("gridmet_pr", "gridmet_tmmn", "gridmet_tmmx"):
        if obs_date_str < GRIDMET_NRT_BOUNDARY:
            vintage_id = "pre_nrt_reanalysis_only"
            vintage_valid = False
            violation_reason = (
                f"Observation date {obs_date_str} precedes gridMET near-real-time proxy inception "
                f"({GRIDMET_NRT_BOUNDARY}); value reflects retrospective reanalysis-blended product only (KF-021)."
            )
            info_cutoff = t_observation_iso
        else:
            vintage_id = "nrt_proxy_available"
            vintage_valid = True
            violation_reason = None
            info_cutoff = t_availability_iso
            
    elif source_channel == "snodas_swe":
        vintage_id = "same_day_production"
        vintage_valid = True
        violation_reason = None
        info_cutoff = t_availability_iso
        
    elif source_channel == "basin_attributes":
        vintage_id = "time_invariant"
        vintage_valid = True
        violation_reason = None
        info_cutoff = "1990-01-01T00:00:00+00:00"
        
    elif source_channel == "nwm_retro_discharge":
        vintage_id = "retrospective_only"
        vintage_valid = False
        violation_reason = "Retrospective reanalysis model simulation — unavailable in operational real time."
        info_cutoff = t_observation_iso
        
    else:
        vintage_id = "unclassified"
        vintage_valid = False
        violation_reason = f"Unknown source channel: {source_channel}"
        info_cutoff = t_observation_iso

    return {
        "feature_name": feature_name,
        "source_channel": source_channel,
        "example_id": example_id,
        "t_observation": t_observation_iso,
        "t_availability": t_availability_iso,
        "information_cutoff": info_cutoff,
        "causally_valid": causally_valid,
        "vintage_id": vintage_id,
        "vintage_valid": vintage_valid,
        "vintage_violation_reason": violation_reason,
        "retrospective_claim_eligible": causally_valid,
        "operational_claim_eligible": (causally_valid and vintage_valid),
    }


def construct_vintage_ledger(causal_ledger_path: Path, output_path: Path) -> Dict[str, Any]:
    """Construct the full Information-State Vintage Ledger based on the causal ledger."""
    with open(causal_ledger_path, "r", encoding="utf-8") as f:
        causal_ledger = json.load(f)
        
    entries = causal_ledger.get("entries", [])
    logger.info(f"Evaluating information-state vintages across {len(entries)} sample entries...")
    
    vintage_entries = []
    
    total_entries = len(entries)
    retrospective_eligible = 0
    operational_eligible = 0
    vintage_exclusions = 0
    
    for entry in entries:
        v_res = evaluate_feature_vintage(
            source_channel=entry["source_channel"],
            t_observation_iso=entry["t_observation"],
            t_availability_iso=entry["t_availability"],
            causally_valid=entry["causally_valid"],
            feature_name=entry.get("feature_name", "feature"),
            example_id=entry.get("example_id", "ex"),
        )
        vintage_entries.append(v_res)
        
        if v_res["retrospective_claim_eligible"]:
            retrospective_eligible += 1
            
        if v_res["operational_claim_eligible"]:
            operational_eligible += 1
        elif v_res["retrospective_claim_eligible"] and not v_res["operational_claim_eligible"]:
            vintage_exclusions += 1
            
    ledger = {
        "ledger_version": "v1.0",
        "total_audited_entries": total_entries,
        "retrospective_claim_eligible_count": retrospective_eligible,
        "operational_claim_eligible_count": operational_eligible,
        "vintage_exclusion_count": vintage_exclusions,
        "vintage_classification_rules": {
            "usgs": "provisional_at_acquisition_unknown (retrospective only, KF-022)",
            "gridmet_pre_2013": "pre_nrt_reanalysis_only (retrospective only, KF-021)",
            "gridmet_post_2013": "nrt_proxy_available (operational and retrospective, KF-021)",
            "snodas": "same_day_production (operational and retrospective)",
            "attributes": "time_invariant (operational and retrospective)",
            "nwm_retro": "retrospective_only (retrospective comparison only)",
        },
        "entries": vintage_entries,
    }
    
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(ledger, f, indent=2)
        
    logger.info(f"Vintage ledger written to: {output_path}")
    logger.info(
        f"Vintage Summary: Total={total_entries}, Retrospective Eligible={retrospective_eligible}, "
        f"Operational Eligible={operational_eligible}, Vintage Exclusions={vintage_exclusions}"
    )
    
    return ledger


def main() -> None:
    causal_ledger_path = _PROJECT_ROOT / "project" / "chunks" / "chunk03" / "causal_ledger.json"
    output_path = _PROJECT_ROOT / "project" / "chunks" / "chunk03" / "vintage_ledger.json"
    
    logger.info("Executing Information-State Vintage Ledger Builder...")
    construct_vintage_ledger(causal_ledger_path, output_path)


if __name__ == "__main__":
    main()
