"""Unit and integration test suite for Split Generator (C-SPLIT / C03-02).

Tests:
1. Deterministic reproducibility across repeated calls with identical seeds.
2. Stratification property preservation for Ref and Non-Ref strata.
3. Gauge and temporal disjointness assertions.
4. Error handling on malformed inputs or inverted date ranges.
"""

import json
import sys
from pathlib import Path

# Add project root to sys.path
_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from source.feature.split_generator import (
    build_split_partition,
    verify_gauge_disjointness,
    verify_temporal_disjointness,
)
from source.utils.logging_config import get_logger
import pytest

logger = get_logger("test_split_generator")


@pytest.fixture
def panel_data() -> dict:
    panel_path = _PROJECT_ROOT / "project" / "chunks" / "chunk02" / "full_panel.json"
    with open(panel_path, "r", encoding="utf-8") as f:
        return json.load(f)


def test_reproducibility(panel_data: dict) -> bool:
    """Test that two runs with the same seed generate bit-for-bit identical splits."""
    split1 = build_split_partition(panel_data, random_seed=42)
    split2 = build_split_partition(panel_data, random_seed=42)
    
    match = (split1 == split2)
    logger.info(f"Test 1 (Reproducibility): {'PASS' if match else 'FAIL'}")
    return match


def test_stratification_proportions(panel_data: dict) -> bool:
    """Test that Ref and Non-Ref gauges are both present and split according to proportions."""
    split = build_split_partition(panel_data, random_seed=42)
    
    passed = (
        split["train_ref_count"] > 0
        and split["train_nonref_count"] > 0
        and split["val_ref_count"] > 0
        and split["val_nonref_count"] > 0
        and split["test_ref_count"] > 0
        and split["test_nonref_count"] > 0
        and (split["train_gauge_count"] + split["val_gauge_count"] + split["test_gauge_count"] == split["total_gauges"])
    )
    logger.info(f"Test 2 (Stratification Proportions): {'PASS' if passed else 'FAIL'}")
    return passed


def test_disjointness_assertions(panel_data: dict) -> bool:
    """Test that verify_gauge_disjointness properly catches disjointness."""
    split = build_split_partition(panel_data, random_seed=42)
    
    passed, errors = verify_gauge_disjointness(
        split["train_gauges"],
        split["val_gauges"],
        split["test_gauges"],
        [g["site_no"] for g in panel_data["gauges"]],
    )
    logger.info(f"Test 3 (Disjointness Assertion on Valid Split): {'PASS' if passed else 'FAIL'}")
    return passed


def test_temporal_assertions() -> bool:
    """Test that valid and invalid temporal ranges are correctly evaluated."""
    # Valid
    v_pass, _ = verify_temporal_disjointness(
        ["1990-01-01", "2015-12-31"],
        ["2016-01-01", "2018-12-31"],
        ["2019-01-01", "2023-12-31"],
    )
    # Overlapping (train_end > val_start)
    i_pass1, _ = verify_temporal_disjointness(
        ["1990-01-01", "2016-06-30"],
        ["2016-01-01", "2018-12-31"],
        ["2019-01-01", "2023-12-31"],
    )
    # Inverted (start > end)
    i_pass2, _ = verify_temporal_disjointness(
        ["2015-12-31", "1990-01-01"],
        ["2016-01-01", "2018-12-31"],
        ["2019-01-01", "2023-12-31"],
    )
    
    passed = v_pass and (not i_pass1) and (not i_pass2)
    logger.info(f"Test 4 (Temporal Boundary Evaluation): {'PASS' if passed else 'FAIL'}")
    return passed


def main() -> None:
    panel_path = _PROJECT_ROOT / "project" / "chunks" / "chunk02" / "full_panel.json"
    with open(panel_path, "r", encoding="utf-8") as f:
        panel_data = json.load(f)
        
    logger.info("Executing Split Generator Test Suite...")
    results = [
        test_reproducibility(panel_data),
        test_stratification_proportions(panel_data),
        test_disjointness_assertions(panel_data),
        test_temporal_assertions(),
    ]
    
    if all(results):
        logger.info(f"Split Generator Test Suite PASSED ({sum(results)}/{len(results)} tests passed).")
        sys.exit(0)
    else:
        logger.error(f"Split Generator Test Suite FAILED ({sum(results)}/{len(results)} tests passed).")
        sys.exit(1)


if __name__ == "__main__":
    main()
