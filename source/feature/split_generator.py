"""Leakage-Safe Split Generator (C-SPLIT / C03-02).

Implements gauge-then-temporal partitioning per architecture.md §3c:
1. Disjoint gauge partitioning stratified by GAGES-II reference/non-reference classification (L3.2 closure).
2. Independent temporal boundary enforcement across splits (L3.1 closure).
3. Pre-windowing discipline: partitions created before sequence windowing or normalization (L1.2 closure).
4. Mechanical duplicate checks across splits (L1.4 closure).
"""

import json
import random
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

# Add project root to sys.path
_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from source.utils.logging_config import get_logger

logger = get_logger("split_generator")


DEFAULT_TRAIN_DATE_RANGE = ["1990-01-01", "2015-12-31"]
DEFAULT_VAL_DATE_RANGE = ["2016-01-01", "2018-12-31"]
DEFAULT_TEST_DATE_RANGE = ["2019-01-01", "2023-12-31"]


def verify_gauge_disjointness(
    train_gauges: List[str],
    val_gauges: List[str],
    test_gauges: List[str],
    all_gauges: Optional[List[str]] = None,
) -> Tuple[bool, List[str]]:
    """Verify that gauge sets are mutually disjoint and cover all expected gauges."""
    s_train = set(train_gauges)
    s_val = set(val_gauges)
    s_test = set(test_gauges)
    
    errors = []
    
    # Check internal set sizes vs list lengths (internal duplicates)
    if len(s_train) != len(train_gauges):
        errors.append(f"Train gauge list contains internal duplicates (len={len(train_gauges)}, unique={len(s_train)})")
    if len(s_val) != len(val_gauges):
        errors.append(f"Val gauge list contains internal duplicates (len={len(val_gauges)}, unique={len(s_val)})")
    if len(s_test) != len(test_gauges):
        errors.append(f"Test gauge list contains internal duplicates (len={len(test_gauges)}, unique={len(s_test)})")
        
    # Check pairwise overlaps
    train_val_overlap = s_train & s_val
    if train_val_overlap:
        errors.append(f"Cross-split duplicate gauges between train and val: {sorted(train_val_overlap)}")
        
    train_test_overlap = s_train & s_test
    if train_test_overlap:
        errors.append(f"Cross-split duplicate gauges between train and test: {sorted(train_test_overlap)}")
        
    val_test_overlap = s_val & s_test
    if val_test_overlap:
        errors.append(f"Cross-split duplicate gauges between val and test: {sorted(val_test_overlap)}")
        
    if all_gauges is not None:
        s_all = set(all_gauges)
        combined = s_train | s_val | s_test
        missing = s_all - combined
        if missing:
            errors.append(f"Gauges in panel but missing from splits: {sorted(missing)}")
        extra = combined - s_all
        if extra:
            errors.append(f"Gauges in splits but missing from panel: {sorted(extra)}")
            
    passed = (len(errors) == 0)
    return passed, errors


def verify_temporal_disjointness(
    train_dates: List[str],
    val_dates: List[str],
    test_dates: List[str],
) -> Tuple[bool, List[str]]:
    """Verify that temporal boundaries are non-overlapping and ordered."""
    errors = []
    if len(train_dates) != 2 or len(val_dates) != 2 or len(test_dates) != 2:
        errors.append("Date ranges must each contain exactly 2 ISO date strings [start, end]")
        return False, errors
        
    tr_start, tr_end = train_dates
    val_start, val_end = val_dates
    te_start, te_end = test_dates
    
    if tr_start > tr_end:
        errors.append(f"Train date range inverted: {tr_start} > {tr_end}")
    if val_start > val_end:
        errors.append(f"Val date range inverted: {val_start} > {val_end}")
    if te_start > te_end:
        errors.append(f"Test date range inverted: {te_start} > {te_end}")
        
    if tr_end >= val_start:
        errors.append(f"Train date range overlaps or touches Val range: train_end={tr_end} >= val_start={val_start}")
    if val_end >= te_start:
        errors.append(f"Val date range overlaps or touches Test range: val_end={val_end} >= test_start={te_start}")
        
    passed = (len(errors) == 0)
    return passed, errors


def build_split_partition(
    panel_data: Dict[str, Any],
    random_seed: int = 42,
    train_frac: float = 0.60,
    val_frac: float = 0.20,
    test_frac: float = 0.20,
    train_date_range: Optional[List[str]] = None,
    val_date_range: Optional[List[str]] = None,
    test_date_range: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """Construct a leakage-safe gauge-then-temporal split stratified by GAGES-II reference class."""
    gauges = panel_data.get("gauges", [])
    if not gauges:
        raise ValueError("Panel data contains no gauges")
        
    tr_dates = train_date_range or DEFAULT_TRAIN_DATE_RANGE
    val_dates = val_date_range or DEFAULT_VAL_DATE_RANGE
    te_dates = test_date_range or DEFAULT_TEST_DATE_RANGE
    
    # Verify temporal boundaries
    temp_passed, temp_errors = verify_temporal_disjointness(tr_dates, val_dates, te_dates)
    if not temp_passed:
        raise ValueError(f"Invalid temporal split ranges: {temp_errors}")
        
    # Separate by reference class
    ref_gauges = sorted([g["site_no"] for g in gauges if g.get("gagesii_class") == "Ref"])
    nonref_gauges = sorted([g["site_no"] for g in gauges if g.get("gagesii_class") == "Non-Ref"])
    
    other_gauges = sorted([g["site_no"] for g in gauges if g.get("gagesii_class") not in ("Ref", "Non-Ref")])
    if other_gauges:
        logger.warning(f"Gauges with unclassified reference status: {other_gauges}")
        
    rng = random.Random(random_seed)
    
    # Shuffle each stratum deterministically
    shuffled_ref = list(ref_gauges)
    rng.shuffle(shuffled_ref)
    
    shuffled_nonref = list(nonref_gauges)
    rng.shuffle(shuffled_nonref)
    
    # Calculate partition counts for Ref (e.g. 29 -> train=17, val=6, test=6)
    n_ref = len(shuffled_ref)
    n_ref_val = int(round(n_ref * val_frac))
    n_ref_test = int(round(n_ref * test_frac))
    n_ref_train = n_ref - n_ref_val - n_ref_test
    
    ref_train = shuffled_ref[:n_ref_train]
    ref_val = shuffled_ref[n_ref_train:n_ref_train + n_ref_val]
    ref_test = shuffled_ref[n_ref_train + n_ref_val:]
    
    # Calculate partition counts for Non-Ref (e.g. 25 -> train=15, val=5, test=5)
    n_nonref = len(shuffled_nonref)
    n_nonref_val = int(round(n_nonref * val_frac))
    n_nonref_test = int(round(n_nonref * test_frac))
    n_nonref_train = n_nonref - n_nonref_val - n_nonref_test
    
    nonref_train = shuffled_nonref[:n_nonref_train]
    nonref_val = shuffled_nonref[n_nonref_train:n_nonref_train + n_nonref_val]
    nonref_test = shuffled_nonref[n_nonref_train + n_nonref_val:]
    
    # Combine and sort for deterministic manifest
    train_gauges = sorted(ref_train + nonref_train)
    val_gauges = sorted(ref_val + nonref_val)
    test_gauges = sorted(ref_test + nonref_test)
    all_site_nos = sorted([g["site_no"] for g in gauges])
    
    # Verify gauge disjointness
    disjoint_passed, gauge_errors = verify_gauge_disjointness(train_gauges, val_gauges, test_gauges, all_site_nos)
    if not disjoint_passed:
        raise RuntimeError(f"Gauge disjointness validation failed: {gauge_errors}")
        
    manifest = {
        "split_id": "gauge_temporal_holdout_v1",
        "method": "gauge_then_temporal",
        "random_seed": random_seed,
        "stratification_variable": "gagesii_class",
        "train_gauges": train_gauges,
        "val_gauges": val_gauges,
        "test_gauges": test_gauges,
        "train_date_range": tr_dates,
        "val_date_range": val_dates,
        "test_date_range": te_dates,
        "generated_before_windowing": True,
        "duplicate_check_passed": True,
        "train_gauge_count": len(train_gauges),
        "val_gauge_count": len(val_gauges),
        "test_gauge_count": len(test_gauges),
        "train_ref_count": len(ref_train),
        "train_nonref_count": len(nonref_train),
        "val_ref_count": len(ref_val),
        "val_nonref_count": len(nonref_val),
        "test_ref_count": len(ref_test),
        "test_nonref_count": len(nonref_test),
        "total_gauges": len(gauges)
    }
    
    return manifest


def main() -> None:
    """CLI runner to construct and freeze split_manifest.json."""
    panel_path = _PROJECT_ROOT / "project" / "chunks" / "chunk02" / "full_panel.json"
    output_path = _PROJECT_ROOT / "project" / "chunks" / "chunk03" / "split_manifest.json"
    
    if len(sys.argv) > 1:
        panel_path = Path(sys.argv[1])
    if len(sys.argv) > 2:
        output_path = Path(sys.argv[2])
        
    logger.info(f"Loading full gauge panel from: {panel_path}")
    with open(panel_path, "r", encoding="utf-8") as f:
        panel_data = json.load(f)
        
    logger.info(f"Building leakage-safe split (seed=42)...")
    manifest = build_split_partition(panel_data, random_seed=42)
    
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2)
        
    logger.info(f"Split manifest successfully written to: {output_path}")
    logger.info(
        f"Split Summary: Train={manifest['train_gauge_count']} (Ref={manifest['train_ref_count']}, Non-Ref={manifest['train_nonref_count']}), "
        f"Val={manifest['val_gauge_count']} (Ref={manifest['val_ref_count']}, Non-Ref={manifest['val_nonref_count']}), "
        f"Test={manifest['test_gauge_count']} (Ref={manifest['test_ref_count']}, Non-Ref={manifest['test_nonref_count']}), "
        f"Total={manifest['total_gauges']}"
    )


if __name__ == "__main__":
    main()
