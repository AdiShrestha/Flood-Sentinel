"""Unit test suite for Causal Feature Matrix Constructor (C-FEATURE / C03-06).

Tests:
1. Feature causality evaluation under valid antecedent observations (t_avail <= t_target).
2. Future-leaking observation detection (t_avail > t_target) -> causally_valid: false.
3. Exact boundary condition (t_avail == t_target) -> causally_valid: true.
4. Latency-induced lag violation detection.
"""

import sys
from pathlib import Path

# Add project root to sys.path
_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from source.feature.causal_feature_matrix import evaluate_feature_causality
from source.utils.logging_config import get_logger

logger = get_logger("test_causal_feature_matrix")


def test_valid_antecedent_feature() -> bool:
    """Test standard valid antecedent feature with observation well before target."""
    res = evaluate_feature_causality(
        t_observation_iso="2015-06-01T00:00:00Z",
        latency_hours=14,  # Available 2015-06-01 14:00
        t_forecast_target_iso="2015-06-02T00:00:00Z",
    )
    passed = (res["causally_valid"] is True) and (res["violation_reason"] is None)
    logger.info(f"Test 1 (Valid Antecedent Observation): {'PASS' if passed else 'FAIL'}")
    return passed


def test_future_observation_leak() -> bool:
    """Test future observation whose observation date postdates forecast target."""
    res = evaluate_feature_causality(
        t_observation_iso="2015-06-03T00:00:00Z",
        latency_hours=0,
        t_forecast_target_iso="2015-06-02T00:00:00Z",
    )
    passed = (res["causally_valid"] is False) and ("exceeds t_forecast_target" in res["violation_reason"])
    logger.info(f"Test 2 (Future Observation Leak Detection): {'PASS' if passed else 'FAIL'}")
    return passed


def test_exact_boundary_condition() -> bool:
    """Test exact equality boundary condition (t_avail == t_target)."""
    res = evaluate_feature_causality(
        t_observation_iso="2015-06-01T10:00:00Z",
        latency_hours=14,  # Available exactly 2015-06-02 00:00:00Z
        t_forecast_target_iso="2015-06-02T00:00:00Z",
    )
    passed = (res["causally_valid"] is True) and (res["violation_reason"] is None)
    logger.info(f"Test 3 (Exact Availability Boundary): {'PASS' if passed else 'FAIL'}")
    return passed


def test_latency_induced_violation() -> bool:
    """Test observation dated on target day whose publication latency delays availability past target."""
    res = evaluate_feature_causality(
        t_observation_iso="2015-06-02T00:00:00Z",
        latency_hours=24,  # SNODAS available 2015-06-03 00:00:00Z
        t_forecast_target_iso="2015-06-02T12:00:00Z",  # Target is noon on June 2nd
    )
    passed = (res["causally_valid"] is False) and ("exceeds t_forecast_target" in res["violation_reason"])
    logger.info(f"Test 4 (Latency-Induced Leak Detection): {'PASS' if passed else 'FAIL'}")
    return passed


def main() -> None:
    logger.info("Executing Causal Feature Matrix Test Suite...")
    tests = [
        test_valid_antecedent_feature(),
        test_future_observation_leak(),
        test_exact_boundary_condition(),
        test_latency_induced_violation(),
    ]
    
    if all(tests):
        logger.info(f"Causal Feature Matrix Test Suite PASSED ({sum(tests)}/{len(tests)} tests passed).")
        sys.exit(0)
    else:
        logger.error("Causal Feature Matrix Test Suite FAILED.")
        sys.exit(1)


if __name__ == "__main__":
    main()
