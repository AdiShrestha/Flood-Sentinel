"""Independent Recomputation Script for Leakage-Safe Split (C-SPLIT / C03-02).

Provides an independent secondary implementation of the duplicate check
for the Recompute Declaration per INV-018:
- Does NOT import `split_generator.py`.
- Reads `split_manifest.json` and `full_panel.json` directly.
- Independently re-computes set intersections and coverage across splits.
- Emits JSON with `duplicate_check_passed` key on a single line for gatekeeper parsing.
"""

import json
import sys
from pathlib import Path

_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent


def recompute_duplicate_check(manifest_path: Path, panel_path: Path) -> dict:
    """Independently re-verify gauge disjointness and completeness without importing split_generator."""
    with open(manifest_path, "r", encoding="utf-8") as f:
        manifest = json.load(f)
        
    with open(panel_path, "r", encoding="utf-8") as f:
        panel = json.load(f)
        
    train_gauges = manifest.get("train_gauges", [])
    val_gauges = manifest.get("val_gauges", [])
    test_gauges = manifest.get("test_gauges", [])
    
    s_train = set(train_gauges)
    s_val = set(val_gauges)
    s_test = set(test_gauges)
    
    # Check internal duplicates
    has_internal_dups = (
        len(s_train) != len(train_gauges)
        or len(s_val) != len(val_gauges)
        or len(s_test) != len(test_gauges)
    )
    
    # Check cross-split overlaps
    tv_overlap = s_train & s_val
    tt_overlap = s_train & s_test
    vt_overlap = s_val & s_test
    has_cross_dups = bool(tv_overlap or tt_overlap or vt_overlap)
    
    # Check completeness
    panel_gauges = {g["site_no"] for g in panel.get("gauges", [])}
    split_gauges = s_train | s_val | s_test
    is_complete = (panel_gauges == split_gauges)
    
    passed = (not has_internal_dups) and (not has_cross_dups) and is_complete
    
    return {
        "duplicate_check_passed": passed,
        "internal_duplicates": has_internal_dups,
        "cross_split_overlap": has_cross_dups,
        "completeness_verified": is_complete,
        "total_gauges_checked": len(split_gauges),
        "expected_gauges_checked": len(panel_gauges)
    }


def main() -> None:
    manifest_path = _PROJECT_ROOT / "project" / "chunks" / "chunk03" / "split_manifest.json"
    panel_path = _PROJECT_ROOT / "project" / "chunks" / "chunk02" / "full_panel.json"
    
    if not manifest_path.exists():
        print(json.dumps({"duplicate_check_passed": False, "error": f"Missing {manifest_path}"}))
        sys.exit(1)
        
    if not panel_path.exists():
        print(json.dumps({"duplicate_check_passed": False, "error": f"Missing {panel_path}"}))
        sys.exit(1)
        
    result = recompute_duplicate_check(manifest_path, panel_path)
    print(json.dumps(result))
    
    if result["duplicate_check_passed"]:
        sys.exit(0)
    else:
        sys.exit(1)


if __name__ == "__main__":
    main()
