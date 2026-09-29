"""T-COMP Correctness Validation Test Suite for Causal Feature Matrix (C-FEATURE / C03-07).

Constructs M deliberately-injected future-leaking feature configurations and proves
that C-FEATURE validation logic mechanically detects 100% of injected leaks per INV-018:
1. Scenario 1 (Future Observation Leak): t_obs = t_target + 1 day -> FLAGGED.
2. Scenario 2 (Unpublished at Forecast Time): t_avail = t_target + 14 hours -> FLAGGED.
3. Scenario 3 (Exact Boundary Condition): t_avail == t_target -> VALID (<= semantics).
4. Scenario 4 (Latency-Induced Leak): t_obs == t_target, latency=24h -> FLAGGED.
"""

import sys
from pathlib import Path

# Add project root to sys.path
_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from source.feature.causal_feature_matrix import evaluate_feature_causality
from source.utils.logging_config import get_logger

logger = get_logger("test_causal_correctness")


def test_scenario_1_future_observation() -> bool:
    """Scenario 1: Future observation timestamp postdating forecast target."""
    res = evaluate_feature_causality(
        t_observation_iso="2018-05-15T00:00:00Z",
        latency_hours=0,
        t_forecast_target_iso="2018-05-14T00:00:00Z",  # Target 1 day before observation
        feature_name="usgs_discharge_future",
        example_id="leak_001",
        source_channel="usgs_discharge",
    )
    detected = (res["causally_valid"] is False) and ("exceeds t_forecast_target" in str(res["violation_reason"]))
    logger.info(f"Scenario 1 (Future Observation): {'DETECTED (PASS)' if detected else 'MISSED (FAIL)'}")
    return detected


def test_scenario_2_unpublished_at_forecast() -> bool:
    """Scenario 2: Observation timestamp valid, but publication latency delays availability past target."""
    res = evaluate_feature_causality(
        t_observation_iso="2018-05-14T00:00:00Z",
        latency_hours=14,  # gridMET published 2018-05-14 14:00:00Z
        t_forecast_target_iso="2018-05-14T06:00:00Z",  # Target is 06:00:00Z on same day
        feature_name="gridmet_pr_delayed",
        example_id="leak_002",
        source_channel="gridmet_pr",
    )
    detected = (res["causally_valid"] is False) and ("exceeds t_forecast_target" in str(res["violation_reason"]))
    logger.info(f"Scenario 2 (Unpublished at Forecast Time): {'DETECTED (PASS)' if detected else 'MISSED (FAIL)'}")
    return detected


def test_scenario_3_exact_boundary_condition() -> bool:
    """Scenario 3: Exact equality boundary condition (t_availability == t_forecast_target)."""
    res = evaluate_feature_causality(
        t_observation_iso="2018-05-14T00:00:00Z",
        latency_hours=24,  # SNODAS published 2018-05-15 00:00:00Z
        t_forecast_target_iso="2018-05-15T00:00:00Z",  # Target is exactly 2018-05-15 00:00:00Z
        feature_name="snodas_swe_boundary",
        example_id="boundary_003",
        source_channel="snodas_swe",
    )
    # Must be valid under <= semantics
    detected = (res["causally_valid"] is True) and (res["violation_reason"] is None)
    logger.info(f"Scenario 3 (Exact Boundary Condition <= Semantics): {'VALID (PASS)' if detected else 'INVALID (FAIL)'}")
    return detected


def test_scenario_4_latency_induced_leak() -> bool:
    """Scenario 4: Observation timestamp equal to forecast origin, latency pushes availability into future."""
    res = evaluate_feature_causality(
        t_observation_iso="2018-05-14T12:00:00Z",
        latency_hours=24,  # SNODAS published 2018-05-15 12:00:00Z
        t_forecast_target_iso="2018-05-15T00:00:00Z",  # Target is 2018-05-15 00:00:00Z (12h lead time)
        feature_name="snodas_swe_latency_leak",
        example_id="leak_004",
        source_channel="snodas_swe",
    )
    detected = (res["causally_valid"] is False) and ("exceeds t_forecast_target" in str(res["violation_reason"]))
    logger.info(f"Scenario 4 (Latency-Induced Leak): {'DETECTED (PASS)' if detected else 'MISSED (FAIL)'}")
    return detected


def main() -> None:
    logger.info("Executing T-COMP C-FEATURE Correctness Validation Suite...")
    scenarios = [
        test_scenario_1_future_observation(),
        test_scenario_2_unpublished_at_forecast(),
        test_scenario_3_exact_boundary_condition(),
        test_scenario_4_latency_induced_leak(),
    ]
    
    passed_count = sum(scenarios)
    total_count = len(scenarios)
    
    logger.info(f"C-FEATURE Leakage Scenarios Validated: {passed_count}/{total_count}")
    if passed_count == total_count:
        logger.info("T-COMP Correctness Validation PASSED (4/4 leakage scenarios correctly evaluated).")
        sys.exit(0)
    else:
        logger.error("T-COMP Correctness Validation FAILED.")
        sys.exit(1)


if __name__ == "__main__":
    main()
