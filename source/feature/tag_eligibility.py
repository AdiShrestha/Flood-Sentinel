"""Response-Time Eligibility Tagger for Feature Matrix (C03-09 / INV-025).

Applies Chunk 02's frozen response-time eligibility tags to every windowed example
in the feature matrix per Invariant INV-025 and A-006:
- Eligible basins (T_response_proxy >= 24h) qualify for Lead-Time Hypothesis H2.
- Ineligible basins (T_response_proxy < 24h) are retained for H1/H3/H4 without lead-time confounding.
"""

import json
import sys
from pathlib import Path
from typing import Any, Dict

import pandas as pd

# Add project root to sys.path
_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from source.utils.logging_config import get_logger

logger = get_logger("tag_eligibility")


def tag_feature_datasets(
    data_dir: Path,
    tags_path: Path,
    window_metadata_path: Path,
) -> Dict[str, Any]:
    """Tag all feature matrices and window metadata with response-time eligibility flags."""
    with open(tags_path, "r", encoding="utf-8") as f:
        tags_data = json.load(f)
        
    gauge_tag_map = {}
    for g in tags_data.get("gauges", []):
        gauge_tag_map[g["site_no"]] = {
            "eligible": (g.get("eligibility_status") == "eligible"),
            "T_response_proxy_hours": float(g.get("T_response_proxy_hours", 0.0)),
            "status": g.get("eligibility_status"),
        }
        
    logger.info(f"Loaded eligibility tags for {len(gauge_tag_map)} streamgages from Chunk 02.")
    
    splits = ["train", "val", "test"]
    split_counts = {}
    total_eligible = 0
    total_ineligible = 0
    
    for sp in splits:
        sp_file = data_dir / f"feature_matrix_{sp}.parquet"
        if not sp_file.exists():
            raise FileNotFoundError(f"Missing split feature matrix: {sp_file}")
            
        df = pd.read_parquet(sp_file)
        
        df["response_time_eligible"] = df["gauge_id"].map(lambda gid: gauge_tag_map[gid]["eligible"])
        df["T_response_proxy_hours"] = df["gauge_id"].map(lambda gid: gauge_tag_map[gid]["T_response_proxy_hours"])
        
        df.to_parquet(sp_file, index=False)
        
        el_count = int(df["response_time_eligible"].sum())
        inel_count = len(df) - el_count
        total_eligible += el_count
        total_ineligible += inel_count
        
        split_counts[sp] = {
            "total_windows": len(df),
            "eligible_windows": el_count,
            "ineligible_windows": inel_count,
        }
        logger.info(f"Split '{sp}': {el_count} Eligible (H2 applicable), {inel_count} Ineligible (H1/H3/H4).")
        
    # Tag window metadata table
    if window_metadata_path.exists():
        df_meta = pd.read_parquet(window_metadata_path)
        df_meta["response_time_eligible"] = df_meta["gauge_id"].map(lambda gid: gauge_tag_map[gid]["eligible"])
        df_meta["T_response_proxy_hours"] = df_meta["gauge_id"].map(lambda gid: gauge_tag_map[gid]["T_response_proxy_hours"])
        df_meta.to_parquet(window_metadata_path, index=False)
        
    summary = {
        "total_windows": total_eligible + total_ineligible,
        "eligible_windows_total": total_eligible,
        "ineligible_windows_total": total_ineligible,
        "split_breakdown": split_counts,
        "gauge_classification_counts": {
            "eligible_gauges": sum(1 for v in gauge_tag_map.values() if v["eligible"]),
            "ineligible_gauges": sum(1 for v in gauge_tag_map.values() if not v["eligible"]),
            "total_gauges": len(gauge_tag_map),
        },
    }
    
    summary_path = data_dir / "eligibility_split_summary.json"
    with open(summary_path, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2)
        
    return summary


def main() -> None:
    data_dir = _PROJECT_ROOT / "project" / "chunks" / "chunk03" / "data"
    tags_path = _PROJECT_ROOT / "project" / "chunks" / "chunk02" / "data" / "response_time" / "eligibility_tags.json"
    window_metadata_path = _PROJECT_ROOT / "project" / "chunks" / "chunk03" / "windowing" / "window_metadata.parquet"
    
    logger.info("Executing Response-Time Eligibility Tagger on Feature Matrix...")
    summary = tag_feature_datasets(data_dir, tags_path, window_metadata_path)
    logger.info(
        f"Eligibility Tagging Complete: Total={summary['total_windows']} windows "
        f"(Eligible={summary['eligible_windows_total']}, Ineligible={summary['ineligible_windows_total']})."
    )


if __name__ == "__main__":
    main()
