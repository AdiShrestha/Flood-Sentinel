"""Test suite for Reality Gate Data-Level Cross-Checks (TD-002 / C02-01).

Validates that cross_check_manifest_against_data() correctly verifies physical
data properties (gap rate, feature variance) against manifest self-reports,
and catches deliberate discrepancies.
"""

import json
import sys
import tempfile
from pathlib import Path
from typing import Any, Dict, Tuple

import numpy as np
import pandas as pd

# Add project root to sys.path if running as standalone script
_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from source.gate.reality_gate import cross_check_manifest_against_data
from source.utils.logging_config import get_logger

logger = get_logger("test_data_level_checks")


def construct_test_dataset(tmp_dir: Path) -> Tuple[Path, Dict[str, Any]]:
    """Create a test Parquet file with exact known statistical properties."""
    # 100 observations: 90 valid, 10 NaNs (10% gap rate)
    np.random.seed(42)
    streamflow = np.random.normal(loc=100.0, scale=10.0, size=100)
    # Exact sample variance
    var_target = float(np.var(streamflow[:90]))

    streamflow_with_nans = list(streamflow[:90]) + [np.nan] * 10

    df = pd.DataFrame({
        "datetime": pd.date_range("2020-01-01", periods=100, freq="D").strftime("%Y-%m-%d"),
        "discharge_cfs": streamflow_with_nans
    })

    parquet_file = tmp_dir / "test_data.parquet"
    df.to_parquet(parquet_file, index=False)

    valid_manifest: Dict[str, Any] = {
        "gap_rate_pct": 10.0,
        "distribution_stats": {
            "discharge_cfs": {
                "variance": var_target,
                "entropy": 3.5
            }
        }
    }

    return parquet_file, valid_manifest


def test_matching_data_and_manifest() -> bool:
    """Case 1: Data and manifest match perfectly -> Expect PASS."""
    with tempfile.TemporaryDirectory() as tmp:
        tmp_dir = Path(tmp)
        parquet_file, manifest = construct_test_dataset(tmp_dir)

        res = cross_check_manifest_against_data(manifest, [parquet_file])
        passed = (res["verdict"] == "PASS")
        logger.info(f"Test Case 1 (Matching Data & Manifest): {'PASS' if passed else 'FAIL'}")
        return passed


def test_mismatched_gap_rate() -> bool:
    """Case 2: Manifest claims 0.0% gap rate but data has 10% gaps -> Expect FAIL."""
    with tempfile.TemporaryDirectory() as tmp:
        tmp_dir = Path(tmp)
        parquet_file, manifest = construct_test_dataset(tmp_dir)
        manifest["gap_rate_pct"] = 0.0  # Discrepancy

        res = cross_check_manifest_against_data(manifest, [parquet_file])
        detected = (res["verdict"] == "FAIL")
        logger.info(f"Test Case 2 (Mismatched Gap Rate): {'DETECTED (PASS)' if detected else 'MISSED (FAIL)'}")
        return detected


def test_mismatched_variance() -> bool:
    """Case 3: Manifest claims variance 5000.0 but data variance is ~100 -> Expect FAIL."""
    with tempfile.TemporaryDirectory() as tmp:
        tmp_dir = Path(tmp)
        parquet_file, manifest = construct_test_dataset(tmp_dir)
        manifest["distribution_stats"]["discharge_cfs"]["variance"] = 5000.0  # Discrepancy

        res = cross_check_manifest_against_data(manifest, [parquet_file])
        detected = (res["verdict"] == "FAIL")
        logger.info(f"Test Case 3 (Mismatched Variance): {'DETECTED (PASS)' if detected else 'MISSED (FAIL)'}")
        return detected


def test_missing_data_file() -> bool:
    """Case 4: Data path does not exist on disk -> Expect FAIL."""
    manifest = {"gap_rate_pct": 0.0, "distribution_stats": {}}
    non_existent = Path("/tmp/non_existent_streamflow_test_path.parquet")

    res = cross_check_manifest_against_data(manifest, [non_existent])
    detected = (res["verdict"] == "FAIL")
    logger.info(f"Test Case 4 (Missing Data File): {'DETECTED (PASS)' if detected else 'MISSED (FAIL)'}")
    return detected


def main() -> None:
    logger.info("Executing TD-002 Data-Level Cross-Check Verification Suite...")
    tests = [
        test_matching_data_and_manifest(),
        test_mismatched_gap_rate(),
        test_mismatched_variance(),
        test_missing_data_file()
    ]

    passed_count = sum(tests)
    total_count = len(tests)

    if passed_count == total_count:
        logger.info(f"Data-Level Cross-Check Test Suite PASSED ({passed_count}/{total_count}).")
        sys.exit(0)
    else:
        logger.error(f"Data-Level Cross-Check Test Suite FAILED ({passed_count}/{total_count}).")
        sys.exit(1)


if __name__ == "__main__":
    main()
