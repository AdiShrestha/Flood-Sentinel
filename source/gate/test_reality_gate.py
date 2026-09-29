"""T-COMP Correctness Validation Test Suite for Reality Gate (C-GATE / C01-11).

Constructs 4 deliberately corrupted manifests and verifies that Reality Gate
mechanically catches all 4 corruptions per INV-018:
1. Corruption 1 (Excessive gap rate > tolerance) -> flags as FAIL.
2. Corruption 2 (Zero variance / suspicious uniformity) -> flags as WARNING.
3. Corruption 3 (Shortened / incomplete temporal coverage) -> flags as FAIL.
4. Corruption 4 (Undocumented transformation step / SVI-001) -> flags as FAIL.
"""

import json
import shutil
import sys
import tempfile
from pathlib import Path
from typing import Any, Dict, List

# Add project root to sys.path if running as standalone script
_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from source.gate.reality_gate import (
    evaluate_distribution_texture,
    evaluate_gap_statistics,
    evaluate_provenance_chain,
    evaluate_source_manifest,
    evaluate_temporal_coverage,
)
from source.utils.logging_config import get_logger

logger = get_logger("test_reality_gate")


def construct_base_valid_manifest() -> Dict[str, Any]:
    """Construct a clean, 100% valid test USGS manifest."""
    return {
        "gap_rate_pct": 0.02,
        "distribution_stats": {
            "discharge_cfs": {
                "variance": 1245000.0,
                "entropy": 4.85
            },
            "gage_height_ft": {
                "variance": 18.2,
                "entropy": 3.12
            }
        },
        "temporal_range": {
            "start": "1990-01-01",
            "end": "2023-12-31"
        },
        "sensors_present": [
            "USGS_00060_discharge",
            "USGS_00065_gage_height"
        ],
        "channel_schema": {
            "column_order": ["datetime", "discharge_cfs", "gage_height_ft"],
            "units": {"discharge_cfs": "cfs", "gage_height_ft": "ft"},
            "physical_range": {"discharge_cfs": {"min": 0.0, "max": 150000.0}}
        },
        "provenance_chain": {
            "discharge_cfs": {
                "raw_product": "USGS NWIS Instantaneous and Daily Values (DV/IV)",
                "transformation_steps": [
                    "Fetch JSON from waterservices.usgs.gov",
                    "Parse parameter 00060 and qualifier flags",
                    "Serialize to columnar Parquet"
                ],
                "undocumented_step": False
            },
            "gage_height_ft": {
                "raw_product": "USGS NWIS Instantaneous and Daily Values (DV/IV)",
                "transformation_steps": [
                    "Fetch JSON from waterservices.usgs.gov",
                    "Parse parameter 00065 and qualifier flags",
                    "Serialize to columnar Parquet"
                ],
                "undocumented_step": False
            }
        }
    }


def test_corruption_1_gap_rate() -> bool:
    """Corruption 1: Excessive gap rate (35% > 5% max tolerance)."""
    manifest = construct_base_valid_manifest()
    manifest["gap_rate_pct"] = 35.0  # Deliberate corruption

    with tempfile.NamedTemporaryFile("w", suffix="_data_manifest.json", delete=False) as tmp:
        json.dump(manifest, tmp)
        tmp_path = Path(tmp.name)

    try:
        res = evaluate_source_manifest(tmp_path, "usgs")
        c1 = res["checks"]["check1_gap_statistics"]
        detected = (c1["verdict"] == "FAIL") and (res["overall_verdict"] == "FAIL")
        logger.info(f"Test Corruption 1 (Excessive Gaps): {'DETECTED (PASS)' if detected else 'MISSED (FAIL)'}")
        return detected
    finally:
        tmp_path.unlink()


def test_corruption_2_suspicious_uniformity() -> bool:
    """Corruption 2: Suspicious uniformity (zero variance on discharge)."""
    manifest = construct_base_valid_manifest()
    manifest["distribution_stats"]["discharge_cfs"]["variance"] = 0.0  # Zero variance
    manifest["distribution_stats"]["discharge_cfs"]["entropy"] = 0.0

    with tempfile.NamedTemporaryFile("w", suffix="_data_manifest.json", delete=False) as tmp:
        json.dump(manifest, tmp)
        tmp_path = Path(tmp.name)

    try:
        res = evaluate_source_manifest(tmp_path, "usgs")
        c2 = res["checks"]["check2_distribution"]
        detected = (c2["verdict"] == "WARNING")
        logger.info(f"Test Corruption 2 (Zero Variance Uniformity): {'DETECTED (PASS)' if detected else 'MISSED (FAIL)'}")
        return detected
    finally:
        tmp_path.unlink()


def test_corruption_3_truncated_temporal_coverage() -> bool:
    """Corruption 3: Missing temporal coverage (starts 2020 instead of 1990)."""
    manifest = construct_base_valid_manifest()
    manifest["temporal_range"] = {"start": "2020-01-01", "end": "2023-12-31"}  # Missing 30 years

    with tempfile.NamedTemporaryFile("w", suffix="_data_manifest.json", delete=False) as tmp:
        json.dump(manifest, tmp)
        tmp_path = Path(tmp.name)

    try:
        res = evaluate_source_manifest(tmp_path, "usgs")
        c3 = res["checks"]["check3_temporal_coverage"]
        detected = (c3["verdict"] == "FAIL") and (res["overall_verdict"] == "FAIL")
        logger.info(f"Test Corruption 3 (Truncated Temporal Span): {'DETECTED (PASS)' if detected else 'MISSED (FAIL)'}")
        return detected
    finally:
        tmp_path.unlink()


def test_corruption_4_undocumented_provenance_step() -> bool:
    """Corruption 4: Undocumented step in provenance chain (SVI-001 violation)."""
    manifest = construct_base_valid_manifest()
    manifest["provenance_chain"]["discharge_cfs"]["undocumented_step"] = True  # SVI-001 violation

    with tempfile.NamedTemporaryFile("w", suffix="_data_manifest.json", delete=False) as tmp:
        json.dump(manifest, tmp)
        tmp_path = Path(tmp.name)

    try:
        res = evaluate_source_manifest(tmp_path, "usgs")
        c5 = res["checks"]["check5_provenance_chain"]
        detected = (c5["verdict"] == "FAIL") and (res["overall_verdict"] == "FAIL")
        logger.info(f"Test Corruption 4 (Undocumented Provenance Step): {'DETECTED (PASS)' if detected else 'MISSED (FAIL)'}")
        return detected
    finally:
        tmp_path.unlink()


def run_all_corruption_tests() -> bool:
    """Run all 4 corruption tests and assert 4/4 detection."""
    logger.info("Executing T-COMP Reality Gate Correctness Validation Suite...")

    results = [
        test_corruption_1_gap_rate(),
        test_corruption_2_suspicious_uniformity(),
        test_corruption_3_truncated_temporal_coverage(),
        test_corruption_4_undocumented_provenance_step()
    ]

    detected_count = sum(results)
    total_count = len(results)

    logger.info(f"Reality Gate Corruptions Detected: {detected_count}/{total_count}")
    return detected_count == total_count


def main() -> None:
    success = run_all_corruption_tests()
    if success:
        logger.info("T-COMP Correctness Validation PASSED (4/4 corruptions correctly flagged).")
        sys.exit(0)
    else:
        logger.error("T-COMP Correctness Validation FAILED.")
        sys.exit(1)


if __name__ == "__main__":
    main()
