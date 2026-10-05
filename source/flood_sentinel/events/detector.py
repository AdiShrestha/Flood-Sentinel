"""Event episode detection state machine with interval onsets, hysteresis, and censoring.

Implements strict hydrological crossing detection:
1. Interval onsets: (onset_lower, onset_upper] with last-below and first-above timestamps.
2. Hysteresis: 24-hour inter-event separation rule merging transient dips into single multi-peak episodes.
3. Censoring: Explicit flags for left-censored and right-censored observation windows.
4. Multi-threshold independence: Preserves lower threshold crossings when peaks attain higher categories.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
import math
from typing import Sequence

from flood_sentinel.temporal import utc


@dataclass(frozen=True)
class EventEpisode:
    """Detected flood exceedance episode with physical and temporal attribution."""
    event_id: str
    site_no: str
    category: str
    threshold_si: float
    threshold_raw: float
    vertical_datum: str
    onset_lower_utc: str | None
    onset_upper_utc: str
    peak_time_utc: str
    peak_value_si: float
    end_time_utc: str | None
    duration_hours: float | None
    is_left_censored: bool
    is_right_censored: bool
    max_category_attained: str

    def __post_init__(self):
        if not self.event_id or not isinstance(self.event_id, str):
            raise ValueError("event_id must be a non-empty string")
        if not self.site_no or not self.category:
            raise ValueError("site_no and category are required")
        if not isinstance(self.threshold_si, (int, float)) or self.threshold_si <= 0.0:
            raise ValueError(f"threshold_si must be positive float, got {self.threshold_si}")
        if self.onset_lower_utc is not None:
            lower_dt = datetime.fromisoformat(self.onset_lower_utc.replace("Z", "+00:00"))
            upper_dt = datetime.fromisoformat(self.onset_upper_utc.replace("Z", "+00:00"))
            if lower_dt >= upper_dt:
                raise ValueError(f"onset_lower ({self.onset_lower_utc}) must be strictly before onset_upper ({self.onset_upper_utc})")


def detect_episodes(
    site_no: str,
    observations: Sequence[tuple[datetime, float]],
    threshold_si: float,
    threshold_raw: float,
    category: str = "minor",
    vertical_datum: str = "NAVD88",
    separation_hours: float = 24.0,
    all_thresholds_si: dict[str, float] | None = None,
) -> list[EventEpisode]:
    """Detect event episodes over chronological observations using 24h hysteresis.

    Parameters:
        site_no: Station identifier.
        observations: Sequence of (datetime, float) tuples, sorted chronologically.
        threshold_si: Target crossing threshold in SI units (e.g. meters).
        threshold_raw: Target crossing threshold in original units (e.g. feet).
        category: Category name (e.g. 'minor', 'moderate', 'major', 'action').
        vertical_datum: Vertical reference datum.
        separation_hours: Minimum consecutive hours below threshold before a new episode starts.
        all_thresholds_si: Optional mapping of category -> SI threshold to evaluate max_category_attained.

    Returns:
        List of EventEpisode dataclasses.
    """
    if not observations:
        return []

    # Verify chronological ordering and timezone awareness
    clean_obs: list[tuple[datetime, float]] = []
    for t, v in observations:
        t_utc = utc(t)
        if not isinstance(v, (int, float)) or not math.isfinite(v):
            continue
        clean_obs.append((t_utc, float(v)))

    clean_obs.sort(key=lambda x: x[0])
    if not clean_obs:
        return []

    # Sort hierarchy for determining max_category_attained
    hierarchy = []
    if all_thresholds_si:
        hierarchy = sorted(all_thresholds_si.items(), key=lambda kv: kv[1], reverse=True)

    def determine_max_category(peak_val: float) -> str:
        for cat, thresh in hierarchy:
            if peak_val >= thresh:
                return cat
        return category

    episodes: list[EventEpisode] = []
    sep_delta = timedelta(hours=separation_hours)

    # State tracking variables for the active episode
    in_episode = False
    is_left_censored = False
    onset_lower: datetime | None = None
    onset_upper: datetime | None = None
    peak_time: datetime | None = None
    peak_val: float = -float("inf")
    receding_start: datetime | None = None
    last_exceedance_time: datetime | None = None

    for i, (t, v) in enumerate(clean_obs):
        exceeds = v >= threshold_si

        if not in_episode:
            if exceeds:
                # Event onset detected
                in_episode = True
                if i == 0:
                    # Series starts above threshold: left-censored
                    is_left_censored = True
                    onset_lower = None
                    onset_upper = t
                else:
                    is_left_censored = False
                    onset_lower = clean_obs[i - 1][0]
                    onset_upper = t

                peak_time = t
                peak_val = v
                receding_start = None
                last_exceedance_time = t
        else:
            # Currently in an episode
            if exceeds:
                # Stage is above threshold: update peak and reset any pending recession
                if v >= peak_val:
                    peak_val = v
                    peak_time = t
                last_exceedance_time = t
                receding_start = None
            else:
                # Stage has dipped below threshold
                if receding_start is None:
                    receding_start = t

                # Check if separation duration has elapsed
                if t - receding_start >= sep_delta:
                    # Episode confirmed terminated at last_exceedance_time
                    assert onset_upper is not None and peak_time is not None
                    end_time = last_exceedance_time
                    assert end_time is not None
                    duration = (end_time - onset_upper).total_seconds() / 3600.0

                    compact_upper = onset_upper.strftime("%Y%m%dT%H%M%SZ")
                    event_id = f"{site_no}_{category}_{compact_upper}"
                    max_cat = determine_max_category(peak_val)

                    episodes.append(
                        EventEpisode(
                            event_id=event_id,
                            site_no=site_no,
                            category=category,
                            threshold_si=threshold_si,
                            threshold_raw=threshold_raw,
                            vertical_datum=vertical_datum,
                            onset_lower_utc=onset_lower.strftime("%Y-%m-%dT%H:%M:%SZ") if onset_lower else None,
                            onset_upper_utc=onset_upper.strftime("%Y-%m-%dT%H:%M:%SZ"),
                            peak_time_utc=peak_time.strftime("%Y-%m-%dT%H:%M:%SZ"),
                            peak_value_si=round(peak_val, 4),
                            end_time_utc=end_time.strftime("%Y-%m-%dT%H:%M:%SZ"),
                            duration_hours=round(duration, 2),
                            is_left_censored=is_left_censored,
                            is_right_censored=False,
                            max_category_attained=max_cat,
                        )
                    )

                    # Reset episode state
                    in_episode = False
                    onset_lower = None
                    onset_upper = None
                    peak_time = None
                    peak_val = -float("inf")
                    receding_start = None
                    last_exceedance_time = None

    # Series ended: check if an active episode remains unclosed (right-censored)
    if in_episode and onset_upper is not None and peak_time is not None:
        compact_upper = onset_upper.strftime("%Y%m%dT%H%M%SZ")
        event_id = f"{site_no}_{category}_{compact_upper}"
        max_cat = determine_max_category(peak_val)

        episodes.append(
            EventEpisode(
                event_id=event_id,
                site_no=site_no,
                category=category,
                threshold_si=threshold_si,
                threshold_raw=threshold_raw,
                vertical_datum=vertical_datum,
                onset_lower_utc=onset_lower.strftime("%Y-%m-%dT%H:%M:%SZ") if onset_lower else None,
                onset_upper_utc=onset_upper.strftime("%Y-%m-%dT%H:%M:%SZ"),
                peak_time_utc=peak_time.strftime("%Y-%m-%dT%H:%M:%SZ"),
                peak_value_si=round(peak_val, 4),
                end_time_utc=None,
                duration_hours=None,
                is_left_censored=is_left_censored,
                is_right_censored=True,
                max_category_attained=max_cat,
            )
        )

    return episodes
