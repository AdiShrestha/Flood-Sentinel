"""Reality Gate Implementation for flood-sentinel (C-GATE / C01-11 & C02-01).

Implements the factory_spec.md Reality Gate checks:
1. Check 1 — Gap Statistics: Missing observation rate vs. declared thresholds
2. Check 2 — Distribution Check: Non-uniformity, variance, and Shannon entropy (TD-001)
3. Check 3 — Temporal Coverage: Calendar range compliance
4. Check 4 — Sensor Coverage: Expected sensor/parameter codes presence
5. Check 5 — Provenance Chain (D-014): Undocumented step verification (SVI-001)
6. Check 6 — Data Consistency (TD-002): Independent data-level cross-check against actual Parquet files
"""

import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

import numpy as np
import pandas as pd

# Add project root to sys.path if running as standalone script
_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from source.utils.logging_config import get_logger
from source.utils.manifest import load_data_manifest, validate_data_manifest

logger = get_logger("reality_gate")

# Expected invariant date ranges and tolerances by source
SOURCE_EXPECTED_PROPERTIES: Dict[str, Dict[str, Any]] = {
    "usgs": {
        "max_gap_rate_pct": 5.0,
        "min_entropy": 0.5,
        "expected_start": "1990-01-01",
        "expected_end": "2023-12-31",
        "required_sensors": ["USGS_00060_discharge", "USGS_00065_gage_height"]
    },
    "gridmet": {
        "max_gap_rate_pct": 1.0,
        "min_entropy": 0.5,
        "expected_start": "1990-01-01",
        "expected_end": "2023-12-31",
        "required_sensors": ["gridMET_pr_precipitation", "gridMET_tmmn_minimum_temperature", "gridMET_tmmx_maximum_temperature"]
    },
    "snodas": {
        "max_gap_rate_pct": 5.0,
        "min_entropy": 0.0,
        "expected_start": "2003-10-01",
        "expected_end": "2023-12-31",
        "required_sensors": ["SNODAS_1034_SWE"]
    },
    "attributes": {
        "max_gap_rate_pct": 0.0,
        "min_entropy": 0.5,
        "expected_start": "static",
        "expected_end": "static",
        "required_sensors": ["USGS_GAGES_II", "CAMELS_US", "USGS_NHDPlus_HR", "USACE_NID"]
    },
    "thresholds": {
        "max_gap_rate_pct": 20.0,
        "min_entropy": 0.5,
        "expected_start": None,
        "expected_end": None,
        "required_sensors": []
    },
    "events": {
        "max_gap_rate_pct": 0.0,
        "min_entropy": 0.0,
        "expected_start": "1990-01-01",
        "expected_end": "2023-12-31",
        "required_sensors": ["NSSL_FLASH", "NOAA_NCEI_Storm_Events"]
    },
    "nwm_retro": {
        "max_gap_rate_pct": 5.0,
        "min_entropy": 0.5,
        "expected_start": "1990-01-01",
        "expected_end": "2023-12-31",
        "required_sensors": ["NOAA_NWM_v3_0_Retrospective_Simulation"]
    },
    "response_time": {
        "max_gap_rate_pct": 0.0,
        "min_entropy": 0.5,
        "expected_start": "static",
        "expected_end": "static",
        "required_sensors": ["KF_113_Composite_Estimator"]
    },
    "feature_matrix": {
        "max_gap_rate_pct": 0.0,
        "min_entropy": 0.5,
        "expected_start": "1990-01-01",
        "expected_end": "2023-12-31",
        "required_sensors": ["USGS_00060_discharge", "gridMET_pr_precipitation", "SNODAS_1034_SWE"]
    },
    "causal_ledger": {
        "max_gap_rate_pct": 0.0,
        "min_entropy": 0.0,
        "expected_start": "1990-01-01",
        "expected_end": "2023-12-31",
        "required_sensors": ["Causal_Availability_Audit_Engine"]
    },
    "vintage_ledger": {
        "max_gap_rate_pct": 0.0,
        "min_entropy": 0.0,
        "expected_start": "1990-01-01",
        "expected_end": "2023-12-31",
        "required_sensors": ["Information_State_Vintage_Isolation_Engine"]
    },
    "normalization": {
        "max_gap_rate_pct": 0.0,
        "min_entropy": 0.5,
        "expected_start": "1990-01-01",
        "expected_end": "2015-12-31",
        "required_sensors": ["Train_Split_Normalization_Scaler"]
    }
}


def evaluate_gap_statistics(manifest: Dict[str, Any], source_key: str) -> Dict[str, Any]:
    """Check 1 — Gap Statistics: Missing observation rate vs. declared limit."""
    expected = SOURCE_EXPECTED_PROPERTIES.get(source_key, {})
    max_gap = expected.get("max_gap_rate_pct", 5.0)

    gap_rate = manifest.get("gap_rate_pct")
    if gap_rate is None:
        return {"check": "gap_statistics", "verdict": "FAIL", "reason": "Missing gap_rate_pct in manifest", "value": None}

    if gap_rate > max_gap:
        return {
            "check": "gap_statistics",
            "verdict": "FAIL",
            "reason": f"Observed gap rate ({gap_rate:.2f}%) exceeds maximum allowed ({max_gap:.2f}%)",
            "value": gap_rate,
            "threshold": max_gap
        }

    return {
        "check": "gap_statistics",
        "verdict": "PASS",
        "reason": f"Gap rate ({gap_rate:.2f}%) within tolerance (<= {max_gap:.2f}%)",
        "value": gap_rate,
        "threshold": max_gap
    }


def evaluate_distribution_texture(manifest: Dict[str, Any], source_key: str) -> Dict[str, Any]:
    """Check 2 — Distribution Check: Variance and Shannon entropy of features (TD-001 resolved)."""
    expected = SOURCE_EXPECTED_PROPERTIES.get(source_key, {})
    min_entropy = expected.get("min_entropy", 0.1)

    dist_stats = manifest.get("distribution_stats", {})
    if not dist_stats:
        return {"check": "distribution_check", "verdict": "FAIL", "reason": "Missing distribution_stats in manifest"}

    # TD-001: Read declared exempt channels from manifest metadata rather than hardcoding
    exempt_channels: Set[str] = set(manifest.get("entropy_exempt_channels", []))

    warnings: List[str] = []

    for var_name, stats in dist_stats.items():
        if isinstance(stats, dict):
            var_val = stats.get("variance")
            entropy_val = stats.get("entropy")

            if var_val is not None and var_val == 0.0:
                warnings.append(f"Channel '{var_name}' has zero variance (suspicious uniformity)")

            if entropy_val is not None and entropy_val < min_entropy and var_name not in exempt_channels:
                warnings.append(f"Channel '{var_name}' entropy ({entropy_val:.3f}) below threshold ({min_entropy:.3f})")

    if warnings:
        return {
            "check": "distribution_check",
            "verdict": "WARNING",
            "reason": "; ".join(warnings),
            "warnings_count": len(warnings)
        }

    return {
        "check": "distribution_check",
        "verdict": "PASS",
        "reason": "All distribution variance and entropy metrics meet discriminative criteria"
    }


def evaluate_temporal_coverage(manifest: Dict[str, Any], source_key: str) -> Dict[str, Any]:
    """Check 3 — Temporal Coverage: Calendar range compliance against invariant bounds."""
    expected = SOURCE_EXPECTED_PROPERTIES.get(source_key, {})
    exp_start = expected.get("expected_start")
    exp_end = expected.get("expected_end")

    temp_range = manifest.get("temporal_range", {})
    act_start = temp_range.get("start")
    act_end = temp_range.get("end")

    if not act_start or not act_end:
        return {"check": "temporal_coverage", "verdict": "FAIL", "reason": "Missing start or end in temporal_range"}

    if exp_start is None:
        return {"check": "temporal_coverage", "verdict": "PASS", "reason": f"Temporal coverage [{act_start} .. {act_end}] recorded"}

    # Compare static datasets
    if exp_start == "static":
        if act_start == "static" and act_end == "static":
            return {"check": "temporal_coverage", "verdict": "PASS", "reason": "Static dataset correctly declared"}
        return {"check": "temporal_coverage", "verdict": "FAIL", "reason": f"Expected static, got {act_start}..{act_end}"}

    # Compare date boundaries
    if act_start > exp_start or (exp_end != "present" and act_end < exp_end):
        return {
            "check": "temporal_coverage",
            "verdict": "FAIL",
            "reason": f"Temporal span [{act_start} .. {act_end}] fails expected invariant [{exp_start} .. {exp_end}]",
            "actual": [act_start, act_end],
            "expected": [exp_start, exp_end]
        }

    return {
        "check": "temporal_coverage",
        "verdict": "PASS",
        "reason": f"Temporal coverage [{act_start} .. {act_end}] satisfies invariant requirements",
        "actual": [act_start, act_end],
        "expected": [exp_start, exp_end]
    }


def evaluate_sensor_coverage(manifest: Dict[str, Any], source_key: str) -> Dict[str, Any]:
    """Check 4 — Sensor Coverage: Expected sensor/parameter codes presence."""
    expected = SOURCE_EXPECTED_PROPERTIES.get(source_key, {})
    req_sensors = set(expected.get("required_sensors", []))

    actual_sensors = set(manifest.get("sensors_present", []))
    missing = req_sensors - actual_sensors

    if missing:
        return {
            "check": "sensor_coverage",
            "verdict": "FAIL",
            "reason": f"Missing required sensors/parameters: {sorted(missing)}",
            "missing": sorted(missing)
        }

    return {
        "check": "sensor_coverage",
        "verdict": "PASS",
        "reason": f"All {len(req_sensors)} required sensor codes present",
        "sensors_present": sorted(actual_sensors)
    }


def evaluate_provenance_chain(manifest: Dict[str, Any]) -> Dict[str, Any]:
    """Check 5 — Provenance Chain (D-014): Verify zero undocumented steps (SVI-001)."""
    provenance = manifest.get("provenance_chain", {})
    if not provenance or not isinstance(provenance, dict):
        return {"check": "provenance_chain", "verdict": "FAIL", "reason": "Missing or invalid provenance_chain block"}

    undocumented_channels = []
    missing_steps_channels = []

    for channel_name, info in provenance.items():
        if not isinstance(info, dict):
            undocumented_channels.append(channel_name)
            continue

        if info.get("undocumented_step") is True:
            undocumented_channels.append(channel_name)

        steps = info.get("transformation_steps", [])
        if not steps or not isinstance(steps, list) or len(steps) == 0:
            missing_steps_channels.append(channel_name)

    if undocumented_channels:
        return {
            "check": "provenance_chain",
            "verdict": "FAIL",
            "reason": f"Undocumented transformation steps detected for channel(s): {undocumented_channels} (SVI-001 violation)",
            "undocumented_channels": undocumented_channels
        }

    if missing_steps_channels:
        return {
            "check": "provenance_chain",
            "verdict": "FAIL",
            "reason": f"Empty transformation steps for channel(s): {missing_steps_channels}",
            "missing_steps_channels": missing_steps_channels
        }

    return {
        "check": "provenance_chain",
        "verdict": "PASS",
        "reason": f"All {len(provenance)} channels have documented end-to-end transformation provenance (0 undocumented steps)"
    }


def cross_check_manifest_against_data(
    manifest: Dict[str, Any],
    data_paths: List[Path],
    max_gap_diff_pct: float = 1.0,
    max_var_diff_pct: float = 15.0,
) -> Dict[str, Any]:
    """Check 6 (TD-002) — Data Consistency: Cross-check manifest self-reports against actual data files."""
    if not data_paths:
        return {
            "check": "data_consistency",
            "verdict": "PASS",
            "reason": "No data paths provided for cross-check (manifest-only validation mode)"
        }

    existing_paths = [p for p in data_paths if p.exists()]
    if not existing_paths:
        return {
            "check": "data_consistency",
            "verdict": "FAIL",
            "reason": f"None of the provided {len(data_paths)} data paths exist on disk"
        }

    # Read and aggregate actual data records
    total_records = 0
    missing_records = 0
    channel_values: Dict[str, List[float]] = {}
    dist_stats = manifest.get("distribution_stats", {})
    exempt_channels = set(manifest.get("entropy_exempt_channels", []))
    tracked_channels = [k for k in dist_stats.keys() if isinstance(dist_stats[k], dict)]

    for path in existing_paths:
        try:
            if path.suffix == ".parquet":
                df = pd.read_parquet(path)
            elif path.suffix == ".json":
                df = pd.read_json(path)
            else:
                continue

            total_records += len(df)
            numeric_cols = df.select_dtypes(include=[np.number]).columns
            cols_to_check = [c for c in tracked_channels if c in df.columns] if tracked_channels else list(numeric_cols)
            if not cols_to_check:
                cols_to_check = list(numeric_cols)

            for col in cols_to_check:
                vals = df[col].dropna().tolist()
                if col not in channel_values:
                    channel_values[col] = []
                channel_values[col].extend(vals)
                if col not in exempt_channels:
                    missing_records += int(df[col].isna().sum())

        except Exception as e:
            return {
                "check": "data_consistency",
                "verdict": "FAIL",
                "reason": f"Failed to read data file {path.name}: {e}"
            }

    if total_records == 0:
        return {
            "check": "data_consistency",
            "verdict": "FAIL",
            "reason": "Data files contained zero records"
        }

    # Compute actual gap rate
    non_exempt_cols_count = max(1, len([c for c in channel_values.keys() if c not in exempt_channels]))
    total_cells = total_records * non_exempt_cols_count
    actual_gap_pct = float((missing_records / max(1, total_cells)) * 100.0)
    reported_gap_pct = float(manifest.get("gap_rate_pct", 0.0))

    gap_diff = abs(actual_gap_pct - reported_gap_pct)
    if gap_diff > max_gap_diff_pct:
        return {
            "check": "data_consistency",
            "verdict": "FAIL",
            "reason": (
                f"Gap rate discrepancy: manifest claims {reported_gap_pct:.2f}%, "
                f"actual data computes {actual_gap_pct:.2f}% (diff {gap_diff:.2f}% > {max_gap_diff_pct:.2f}%)"
            ),
            "actual_gap_pct": actual_gap_pct,
            "reported_gap_pct": reported_gap_pct
        }

    # Compare variance for reported channels
    dist_stats = manifest.get("distribution_stats", {})
    var_discrepancies = []

    for var_name, stats in dist_stats.items():
        if isinstance(stats, dict) and "variance" in stats:
            rep_var = stats.get("variance")
            if var_name in channel_values and len(channel_values[var_name]) > 1 and rep_var is not None:
                act_var = float(np.var(channel_values[var_name]))
                if rep_var > 0.0:
                    pct_diff = abs(act_var - rep_var) / rep_var * 100.0
                    if pct_diff > max_var_diff_pct:
                        var_discrepancies.append(
                            f"Channel '{var_name}' variance discrepancy: manifest={rep_var:.2f}, actual={act_var:.2f} ({pct_diff:.1f}% diff)"
                        )

    if var_discrepancies:
        return {
            "check": "data_consistency",
            "verdict": "FAIL",
            "reason": "; ".join(var_discrepancies)
        }

    return {
        "check": "data_consistency",
        "verdict": "PASS",
        "reason": (
            f"Data consistency verified across {len(existing_paths)} files: "
            f"actual gap rate ({actual_gap_pct:.2f}%) and channel variances match manifest within tolerance"
        )
    }


def evaluate_source_manifest(
    manifest_path: Path,
    source_key: str,
    data_paths: Optional[List[Path]] = None,
) -> Dict[str, Any]:
    """Run Reality Gate checks (1-5 plus optional 6) on a single source data manifest."""
    try:
        manifest = load_data_manifest(manifest_path)
    except Exception as e:
        return {
            "source_key": source_key,
            "manifest_path": str(manifest_path),
            "status": "parse_error",
            "overall_verdict": "FAIL",
            "error": str(e),
            "checks": {}
        }

    c1 = evaluate_gap_statistics(manifest, source_key)
    c2 = evaluate_distribution_texture(manifest, source_key)
    c3 = evaluate_temporal_coverage(manifest, source_key)
    c4 = evaluate_sensor_coverage(manifest, source_key)
    c5 = evaluate_provenance_chain(manifest)

    checks = {
        "check1_gap_statistics": c1,
        "check2_distribution": c2,
        "check3_temporal_coverage": c3,
        "check4_sensor_coverage": c4,
        "check5_provenance_chain": c5
    }

    if data_paths is not None:
        c6 = cross_check_manifest_against_data(manifest, data_paths)
        checks["check6_data_consistency"] = c6

    # Hard failures: if any check (except C2 which yields WARNING) is FAIL
    hard_failures = [k for k, v in checks.items() if v["verdict"] == "FAIL"]
    warnings = [k for k, v in checks.items() if v["verdict"] == "WARNING"]

    overall = "FAIL" if hard_failures else ("WARNING" if warnings else "PASS")

    return {
        "source_key": source_key,
        "manifest_path": str(manifest_path),
        "overall_verdict": overall,
        "checks": checks
    }
