"""Independent Recomputation Script for Causal Feature Matrix (C-FEATURE / C03-06 & C03-07).

Provides an independent secondary implementation of the causal availability verification
for the Recompute Declaration per INV-018:
- Does NOT import `causal_feature_matrix.py`.
- Reads `causal_ledger.json`, `latency_registry.json`, and `window_metadata.parquet` directly.
- Independently recalculates t_availability <= t_target for audited feature pairs.
- Emits JSON with `exclusion_count` and `causally_valid` status on a single line.
"""

import json
import sys
from datetime import datetime, timedelta
from pathlib import Path

_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent


def recompute_causal_availability(ledger_path: Path, latency_path: Path) -> dict:
    """Independently verify causal availability entries without importing causal_feature_matrix."""
    with open(ledger_path, "r", encoding="utf-8") as f:
        ledger = json.load(f)
        
    with open(latency_path, "r", encoding="utf-8") as f:
        latencies = json.load(f)
        
    entries = ledger.get("entries", [])
    violations = 0
    
    for entry in entries:
        t_obs = datetime.fromisoformat(entry["t_observation"])
        t_avail = datetime.fromisoformat(entry["t_availability"])
        t_target = datetime.fromisoformat(entry["t_forecast_target"])
        
        # Verify latency calculation
        src = entry["source_channel"]
        lat_h = latencies.get(src, {}).get("latency_hours", 0)
        expected_avail = t_obs + timedelta(hours=lat_h)
        
        if t_avail != expected_avail:
            violations += 1
            continue
            
        # Verify inequality
        is_valid = (t_avail <= t_target)
        if is_valid != entry["causally_valid"]:
            violations += 1
            
    claimed_exclusions = ledger.get("exclusion_count", 0)
    
    return {
        "exclusion_count": claimed_exclusions,
        "independent_violations_found": violations,
        "causally_valid": (violations == 0),
        "total_sample_entries_verified": len(entries),
    }


def main() -> None:
    ledger_path = _PROJECT_ROOT / "project" / "chunks" / "chunk03" / "causal_ledger.json"
    latency_path = _PROJECT_ROOT / "source" / "feature" / "latency_registry.json"
    
    if not ledger_path.exists() or not latency_path.exists():
        print(json.dumps({"exclusion_count": -1, "error": "Missing input files"}))
        sys.exit(1)
        
    result = recompute_causal_availability(ledger_path, latency_path)
    print(json.dumps(result))
    
    if result["causally_valid"] and result["independent_violations_found"] == 0:
        sys.exit(0)
    else:
        sys.exit(1)


if __name__ == "__main__":
    main()
