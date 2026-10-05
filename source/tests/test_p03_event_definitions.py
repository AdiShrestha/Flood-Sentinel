"""Unit and regression tests for Work Package P03 event definitions and catalog.

Tests interval onsets, 24-hour hysteresis episode separation, left and right censoring,
independent multi-threshold detection, and authentic non-noon timestamp integrity.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path
import pytest

from flood_sentinel.events.thresholds import FloodThreshold, ThresholdRegistry
from flood_sentinel.events.detector import EventEpisode, detect_episodes
from flood_sentinel.events.catalog import (
    load_catalog_parquet,
    load_catalog_csv,
    CATALOG_COLUMNS,
)

WORKSPACE_ROOT = Path(__file__).resolve().parent.parent.parent
PARQUET_CATALOG = WORKSPACE_ROOT / "data/event_intervals.parquet"
CSV_CATALOG = WORKSPACE_ROOT / "data/event_intervals.csv"


# ==============================================================================
# 1. Interval Onset Precision & Non-Noon Verification
# ==============================================================================

def test_interval_onset_precision():
    """Verify that onset is bound by the exact last-below and first-above timestamps."""
    t0 = datetime(2026, 6, 1, 10, 0, tzinfo=timezone.utc)
    t1 = t0 + timedelta(minutes=15)
    t2 = t0 + timedelta(minutes=30)
    t3 = t0 + timedelta(minutes=45)
    t4 = t0 + timedelta(hours=30)

    # Threshold: 3.0 m
    # t0: 2.0m, t1: 2.8m, t2: 3.2m (crossing), t3: 2.5m (drop), t4: 2.0m (stay below > 24h)
    obs = [(t0, 2.0), (t1, 2.8), (t2, 3.2), (t3, 2.5), (t4, 2.0)]
    episodes = detect_episodes("TEST_01", obs, threshold_si=3.0, threshold_raw=10.0, category="minor")

    assert len(episodes) == 1
    ep = episodes[0]
    assert ep.onset_lower_utc == "2026-06-01T10:15:00Z"
    assert ep.onset_upper_utc == "2026-06-01T10:30:00Z"
    assert ep.peak_time_utc == "2026-06-01T10:30:00Z"
    assert ep.peak_value_si == 3.2
    assert not ep.is_left_censored
    assert not ep.is_right_censored


def test_rejection_of_fabricated_noon_onsets():
    """Verify that detected authentic catalog episodes do not have fabricated noon onsets."""
    episodes = load_catalog_csv(CSV_CATALOG)
    assert len(episodes) >= 4, "Expected at least 4 catalog episodes"

    for ep in episodes:
        onset_upper = ep["onset_upper_utc"]
        # Verify onset does not fall on synthetic 12:00:00Z default
        assert not onset_upper.endswith("T12:00:00Z"), (
            f"Event {ep['event_id']} has fabricated noon onset timestamp: {onset_upper}"
        )


# ==============================================================================
# 2. Hysteresis Merging & Inter-Event Separation
# ==============================================================================

def test_hysteresis_merges_secondary_surge_within_24h():
    """Verify that secondary surges within 24 hours are merged into a single multi-peak episode."""
    t0 = datetime(2026, 5, 1, 0, 0, tzinfo=timezone.utc)

    # Episode starts at t1 (1h, 3.2m), peaks at t2 (2h, 3.5m)
    # Dips below threshold (2.8m) at t4 (4h)
    # Surges back above threshold to higher peak (4.2m) at t12 (12h - dip was only 8h < 24h)
    # Dips below threshold at t16 (16h), stays below for > 24h until t45 (45h)
    obs = [
        (t0, 2.0),
        (t0 + timedelta(hours=1), 3.2),  # Onset
        (t0 + timedelta(hours=2), 3.5),  # First crest
        (t0 + timedelta(hours=4), 2.8),  # Transient dip below 3.0m
        (t0 + timedelta(hours=8), 2.7),
        (t0 + timedelta(hours=12), 4.2), # Secondary higher crest
        (t0 + timedelta(hours=16), 2.9), # Second dip below 3.0m
        (t0 + timedelta(hours=45), 2.0), # Stays below > 24h
    ]

    episodes = detect_episodes("TEST_01", obs, threshold_si=3.0, threshold_raw=10.0, category="minor")

    assert len(episodes) == 1, f"Expected 1 merged episode, got {len(episodes)}"
    ep = episodes[0]
    assert ep.onset_upper_utc == "2026-05-01T01:00:00Z"
    assert ep.peak_value_si == 4.2  # Higher secondary crest captured
    assert ep.peak_time_utc == "2026-05-01T12:00:00Z"
    assert ep.end_time_utc == "2026-05-01T12:00:00Z"  # Last observation above threshold
    assert not ep.is_left_censored
    assert not ep.is_right_censored


def test_hysteresis_separates_events_after_24h_quiescence():
    """Verify that a second rise after >= 24 hours below threshold forms a separate episode."""
    t0 = datetime(2026, 5, 1, 0, 0, tzinfo=timezone.utc)

    # First event: t1..t2
    # Quiescence: t4..t32 (28 hours below threshold > 24h)
    # Second event: t35..t38
    obs = [
        (t0, 2.0),
        (t0 + timedelta(hours=1), 3.2),
        (t0 + timedelta(hours=2), 3.5),
        (t0 + timedelta(hours=4), 2.5),
        (t0 + timedelta(hours=32), 2.5), # 28 hours later
        (t0 + timedelta(hours=35), 3.4), # Second distinct event starts
        (t0 + timedelta(hours=38), 3.8),
        (t0 + timedelta(hours=40), 2.5),
        (t0 + timedelta(hours=70), 2.0), # Stays below > 24h
    ]

    episodes = detect_episodes("TEST_01", obs, threshold_si=3.0, threshold_raw=10.0, category="minor")

    assert len(episodes) == 2, f"Expected 2 separate episodes, got {len(episodes)}"
    assert episodes[0].onset_upper_utc == "2026-05-01T01:00:00Z"
    assert episodes[1].onset_upper_utc == "2026-05-02T11:00:00Z"


# ==============================================================================
# 3. Censoring Semantics
# ==============================================================================

def test_left_censoring_when_series_starts_above_threshold():
    """Verify that if series starts above threshold, episode is marked left-censored with onset_lower=None."""
    t0 = datetime(2026, 4, 1, 0, 0, tzinfo=timezone.utc)
    obs = [
        (t0, 3.5),  # Initial observation already >= 3.0m
        (t0 + timedelta(hours=2), 4.0),
        (t0 + timedelta(hours=5), 2.5),
        (t0 + timedelta(hours=35), 2.0),
    ]

    episodes = detect_episodes("TEST_01", obs, threshold_si=3.0, threshold_raw=10.0, category="minor")

    assert len(episodes) == 1
    ep = episodes[0]
    assert ep.is_left_censored is True
    assert ep.onset_lower_utc is None
    assert ep.onset_upper_utc == "2026-04-01T00:00:00Z"
    assert ep.peak_value_si == 4.0


def test_right_censoring_when_series_ends_above_threshold():
    """Verify that if series ends while above threshold, episode is marked right-censored."""
    t0 = datetime(2026, 4, 1, 0, 0, tzinfo=timezone.utc)
    obs = [
        (t0, 2.0),
        (t0 + timedelta(hours=1), 3.2),
        (t0 + timedelta(hours=3), 4.5), # Series terminates at peak
    ]

    episodes = detect_episodes("TEST_01", obs, threshold_si=3.0, threshold_raw=10.0, category="minor")

    assert len(episodes) == 1
    ep = episodes[0]
    assert ep.is_right_censored is True
    assert ep.end_time_utc is None
    assert ep.duration_hours is None
    assert ep.peak_value_si == 4.5


# ==============================================================================
# 4. Multi-Threshold Independence
# ==============================================================================

def test_multi_threshold_independence():
    """Verify that when a flood reaches Major stage, Minor and Moderate episodes are both retained."""
    t0 = datetime(2026, 3, 1, 0, 0, tzinfo=timezone.utc)
    # Thresholds: Action=2.0m, Minor=3.0m, Moderate=4.0m, Major=5.0m
    # Hydrograph rises from 1.0m to 5.5m (Major flood) then recedes
    obs = [
        (t0, 1.0),
        (t0 + timedelta(hours=1), 2.2),  # Action crossed
        (t0 + timedelta(hours=2), 3.2),  # Minor crossed
        (t0 + timedelta(hours=3), 4.2),  # Moderate crossed
        (t0 + timedelta(hours=4), 5.5),  # Major crossed (Peak)
        (t0 + timedelta(hours=6), 4.5),
        (t0 + timedelta(hours=8), 3.5),
        (t0 + timedelta(hours=10), 2.5),
        (t0 + timedelta(hours=12), 1.5),
        (t0 + timedelta(hours=40), 1.0), # Quiescence
    ]

    thresh_map = {"action": 2.0, "minor": 3.0, "moderate": 4.0, "major": 5.0}

    eps_minor = detect_episodes("TEST_01", obs, threshold_si=3.0, threshold_raw=10.0, category="minor", all_thresholds_si=thresh_map)
    eps_mod = detect_episodes("TEST_01", obs, threshold_si=4.0, threshold_raw=13.0, category="moderate", all_thresholds_si=thresh_map)
    eps_maj = detect_episodes("TEST_01", obs, threshold_si=5.0, threshold_raw=16.5, category="major", all_thresholds_si=thresh_map)

    # All three thresholds must be detected independently
    assert len(eps_minor) == 1
    assert len(eps_mod) == 1
    assert len(eps_maj) == 1

    # Onsets must reflect true chronological progression
    assert eps_minor[0].onset_upper_utc == "2026-03-01T02:00:00Z"
    assert eps_mod[0].onset_upper_utc == "2026-03-01T03:00:00Z"
    assert eps_maj[0].onset_upper_utc == "2026-03-01T04:00:00Z"

    # Minor episode must record that peak reached Major
    assert eps_minor[0].max_category_attained == "major"
    assert eps_mod[0].max_category_attained == "major"


# ==============================================================================
# 5. Parquet and CSV Catalog Integrity
# ==============================================================================

def test_catalog_parquet_and_csv_consistency():
    """Verify that data/event_intervals.parquet and CSV exist and are fully consistent."""
    assert PARQUET_CATALOG.is_file(), f"Missing {PARQUET_CATALOG}"
    assert CSV_CATALOG.is_file(), f"Missing {CSV_CATALOG}"

    p_rows = load_catalog_parquet(PARQUET_CATALOG)
    c_rows = load_catalog_csv(CSV_CATALOG)

    assert len(p_rows) == len(c_rows)
    assert len(p_rows) >= 4

    for p_entry, c_entry in zip(p_rows, c_rows):
        assert p_entry["event_id"] == c_entry["event_id"]
        assert p_entry["site_no"] == c_entry["site_no"]
        assert p_entry["category"] == c_entry["category"]
        assert p_entry["onset_upper_utc"] == c_entry["onset_upper_utc"]
        assert p_entry["peak_value_si"] == pytest.approx(float(c_entry["peak_value_si"]), rel=1e-4)
