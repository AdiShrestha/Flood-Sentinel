"""T-COMP Correctness Validation Test Suite for Leakage-Safe Split (C-SPLIT / C03-03).

Constructs K deliberately-corrupted split configurations and proves that C-SPLIT
validation logic mechanically detects 100% of injected corruptions per INV-018:
1. Corruption 1: Cross-split gauge collision (Train-Val gauge overlap) -> FAIL.
2. Corruption 2: Cross-split gauge collision (Train-Test gauge overlap) -> FAIL.
3. Corruption 3: Internal partition duplicate (Repeated gauge in Train) -> FAIL.
4. Corruption 4: Temporal boundary overlap (Train end >= Val start) -> FAIL.
5. Corruption 5: Inverted temporal interval (Test start > Test end) -> FAIL.
6. Corruption 6: Record-level hash collision (Identical gauge-date record across splits) -> FAIL.
"""

import copy
import hashlib
import json
import sys
from pathlib import Path
from typing import Any, Dict, List, Tuple

# Add project root to sys.path
_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from source.feature.split_generator import (
    verify_gauge_disjointness,
    verify_temporal_disjointness,
)
from source.utils.logging_config import get_logger
import pytest

logger = get_logger("test_split_correctness")


@pytest.fixture
def base_manifest() -> Dict[str, Any]:
    manifest_path = _PROJECT_ROOT / "project" / "chunks" / "chunk03" / "split_manifest.json"
    with open(manifest_path, "r", encoding="utf-8") as f:
        return json.load(f)


def check_record_hash_collisions(
    train_records: List[Tuple[str, str]],
    val_records: List[Tuple[str, str]],
    test_records: List[Tuple[str, str]],
) -> Tuple[bool, List[str]]:
    """Check for identical (gauge, timestamp) records across split partitions."""
    def hash_records(records: List[Tuple[str, str]]) -> Dict[str, Tuple[str, str]]:
        hashes = {}
        for site_no, dt in records:
            key = f"{site_no}::{dt}".encode("utf-8")
            h = hashlib.sha256(key).hexdigest()
            hashes[h] = (site_no, dt)
        return hashes

    h_train = hash_records(train_records)
    h_val = hash_records(val_records)
    h_test = hash_records(test_records)

    errors = []
    tv_coll = set(h_train.keys()) & set(h_val.keys())
    if tv_coll:
        errors.append(f"Train-Val record collision: {[h_train[k] for k in sorted(tv_coll)]}")

    tt_coll = set(h_train.keys()) & set(h_test.keys())
    if tt_coll:
        errors.append(f"Train-Test record collision: {[h_train[k] for k in sorted(tt_coll)]}")

    vt_coll = set(h_val.keys()) & set(h_test.keys())
    if vt_coll:
        errors.append(f"Val-Test record collision: {[h_val[k] for k in sorted(vt_coll)]}")

    passed = (len(errors) == 0)
    return passed, errors


def test_corruption_1_train_val_overlap(base_manifest: Dict[str, Any]) -> bool:
    """Corruption 1: Inject a train gauge into the val gauge list."""
    train_g = list(base_manifest["train_gauges"])
    val_g = list(base_manifest["val_gauges"])
    test_g = list(base_manifest["test_gauges"])
    
    # Inject collision
    leaked_gauge = train_g[0]
    val_g.append(leaked_gauge)
    
    passed, errors = verify_gauge_disjointness(train_g, val_g, test_g)
    detected = (not passed) and any("Cross-split duplicate gauges between train and val" in e for e in errors)
    logger.info(f"Corruption 1 (Train-Val Gauge Collision): {'DETECTED (PASS)' if detected else 'MISSED (FAIL)'}")
    return detected


def test_corruption_2_train_test_overlap(base_manifest: Dict[str, Any]) -> bool:
    """Corruption 2: Inject a train gauge into the test gauge list."""
    train_g = list(base_manifest["train_gauges"])
    val_g = list(base_manifest["val_gauges"])
    test_g = list(base_manifest["test_gauges"])
    
    # Inject collision
    leaked_gauge = train_g[0]
    test_g.append(leaked_gauge)
    
    passed, errors = verify_gauge_disjointness(train_g, val_g, test_g)
    detected = (not passed) and any("Cross-split duplicate gauges between train and test" in e for e in errors)
    logger.info(f"Corruption 2 (Train-Test Gauge Collision): {'DETECTED (PASS)' if detected else 'MISSED (FAIL)'}")
    return detected


def test_corruption_3_internal_duplicate(base_manifest: Dict[str, Any]) -> bool:
    """Corruption 3: Inject an internal duplicate into the train gauge list."""
    train_g = list(base_manifest["train_gauges"])
    val_g = list(base_manifest["val_gauges"])
    test_g = list(base_manifest["test_gauges"])
    
    # Inject duplicate
    train_g.append(train_g[0])
    
    passed, errors = verify_gauge_disjointness(train_g, val_g, test_g)
    detected = (not passed) and any("Train gauge list contains internal duplicates" in e for e in errors)
    logger.info(f"Corruption 3 (Internal Partition Duplicate): {'DETECTED (PASS)' if detected else 'MISSED (FAIL)'}")
    return detected


def test_corruption_4_temporal_overlap() -> bool:
    """Corruption 4: Extend train date range into validation epoch."""
    tr_dates = ["1990-01-01", "2016-06-30"]  # Extends 6 months into 2016
    val_dates = ["2016-01-01", "2018-12-31"]
    test_dates = ["2019-01-01", "2023-12-31"]
    
    passed, errors = verify_temporal_disjointness(tr_dates, val_dates, test_dates)
    detected = (not passed) and any("Train date range overlaps or touches Val range" in e for e in errors)
    logger.info(f"Corruption 4 (Temporal Epoch Overlap): {'DETECTED (PASS)' if detected else 'MISSED (FAIL)'}")
    return detected


def test_corruption_5_inverted_temporal_range() -> bool:
    """Corruption 5: Inverted start/end dates for test split."""
    tr_dates = ["1990-01-01", "2015-12-31"]
    val_dates = ["2016-01-01", "2018-12-31"]
    test_dates = ["2023-12-31", "2019-01-01"]  # Inverted
    
    passed, errors = verify_temporal_disjointness(tr_dates, val_dates, test_dates)
    detected = (not passed) and any("Test date range inverted" in e for e in errors)
    logger.info(f"Corruption 5 (Inverted Temporal Interval): {'DETECTED (PASS)' if detected else 'MISSED (FAIL)'}")
    return detected


def test_corruption_6_record_hash_collision() -> bool:
    """Corruption 6: Inject identical gauge-timestamp observation record across splits."""
    clean_train = [("01034500", "2010-05-15"), ("01137500", "2010-05-15")]
    clean_val = [("01445500", "2017-06-10"), ("01541000", "2017-06-10")]
    clean_test = [("02085000", "2020-08-20"), ("02138500", "2020-08-20")]
    
    # 1. Verify clean passes
    p_clean, _ = check_record_hash_collisions(clean_train, clean_val, clean_test)
    
    # 2. Inject cross-split duplicate record into test
    corrupt_test = list(clean_test) + [("01034500", "2010-05-15")]  # Duplicate from train
    p_corrupt, errors = check_record_hash_collisions(clean_train, clean_val, corrupt_test)
    
    detected = p_clean and (not p_corrupt) and any("Train-Test record collision" in e for e in errors)
    logger.info(f"Corruption 6 (Cross-Split Record Hash Collision): {'DETECTED (PASS)' if detected else 'MISSED (FAIL)'}")
    return detected


def run_all_corruption_tests() -> bool:
    manifest_path = _PROJECT_ROOT / "project" / "chunks" / "chunk03" / "split_manifest.json"
    with open(manifest_path, "r", encoding="utf-8") as f:
        base_manifest = json.load(f)

    logger.info("Executing T-COMP C-SPLIT Correctness Validation Suite...")
    results = [
        test_corruption_1_train_val_overlap(base_manifest),
        test_corruption_2_train_test_overlap(base_manifest),
        test_corruption_3_internal_duplicate(base_manifest),
        test_corruption_4_temporal_overlap(),
        test_corruption_5_inverted_temporal_range(),
        test_corruption_6_record_hash_collision(),
    ]

    detected_count = sum(results)
    total_count = len(results)

    logger.info(f"C-SPLIT Corruptions Detected: {detected_count}/{total_count}")
    return detected_count == total_count


def main() -> None:
    success = run_all_corruption_tests()
    if success:
        logger.info("T-COMP Correctness Validation PASSED (6/6 corruptions correctly flagged).")
        sys.exit(0)
    else:
        logger.error("T-COMP Correctness Validation FAILED.")
        sys.exit(1)


if __name__ == "__main__":
    main()
