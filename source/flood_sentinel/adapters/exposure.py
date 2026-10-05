"""Event and hydrological exposure adapter linking cohort issues to event intervals."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Mapping, Sequence


class LabelConsistencyError(ValueError):
    """Raised when cohort classification label diverges from authentic hydrologic event evidence."""
    pass


@dataclass(frozen=True)
class HydrologicExposure:
    """Hydrological exposure metrics for a forecast issue and target lead horizon.

    Attributes:
        sample_id: Cohort issue identifier.
        site_no: USGS gage number.
        issue_time_utc: Timestamp when forecast was issued.
        horizon_hours: Lead time horizon duration in hours (e.g. 24.0).
        has_flood_event: Whether an authentic flood onset occurs in (t_issue, t_issue + horizon].
        lead_time_lower_hours: Hours from issue to event onset interval lower bound.
        lead_time_upper_hours: Hours from issue to event onset interval upper bound.
        peak_stage_excess_m: Maximum stage above threshold observed during the event.
        censored: Whether the event interval was right-censored.
    """
    sample_id: str
    site_no: str
    issue_time_utc: datetime
    horizon_hours: float
    has_flood_event: bool
    lead_time_lower_hours: float | None = None
    lead_time_upper_hours: float | None = None
    peak_stage_excess_m: float = 0.0
    censored: bool = False


class ExposureAdapter:
    """Adapter verifying and mapping hydrological exposure from the event intervals catalog."""

    @staticmethod
    def compute_sample_exposure(
        sample_id: str,
        site_no: str,
        issue_time_utc: datetime,
        event_intervals: Sequence[Mapping[str, str]],
        horizon_hours: float = 24.0,
    ) -> HydrologicExposure:
        """Compute hydrological exposure metrics for an issue against authentic event intervals."""
        if issue_time_utc.tzinfo is None:
            issue_time_utc = issue_time_utc.replace(tzinfo=timezone.utc)

        t_horizon_end = issue_time_utc + timedelta(hours=horizon_hours)

        matching_events: list[Mapping[str, str]] = []
        for ev in event_intervals:
            if ev.get("site_no") != site_no:
                continue

            # Check onset interval
            t_lower_str = ev.get("onset_lower_utc")
            t_upper_str = ev.get("onset_upper_utc")
            if not t_lower_str or not t_upper_str:
                continue

            t_lower = datetime.fromisoformat(t_lower_str)
            t_upper = datetime.fromisoformat(t_upper_str)
            if t_lower.tzinfo is None:
                t_lower = t_lower.replace(tzinfo=timezone.utc)
            if t_upper.tzinfo is None:
                t_upper = t_upper.replace(tzinfo=timezone.utc)

            # An event onset is in target horizon if its onset interval intersects (t_issue, t_horizon_end]
            if t_upper > issue_time_utc and t_lower < t_horizon_end:
                matching_events.append(ev)

        if not matching_events:
            return HydrologicExposure(
                sample_id=sample_id,
                site_no=site_no,
                issue_time_utc=issue_time_utc,
                horizon_hours=horizon_hours,
                has_flood_event=False,
            )

        # Take earliest intersecting event
        ev = matching_events[0]
        t_lower = datetime.fromisoformat(ev["onset_lower_utc"]).replace(tzinfo=timezone.utc)
        t_upper = datetime.fromisoformat(ev["onset_upper_utc"]).replace(tzinfo=timezone.utc)

        lead_lower = (t_lower - issue_time_utc).total_seconds() / 3600.0
        lead_upper = (t_upper - issue_time_utc).total_seconds() / 3600.0

        peak_v = float(ev.get("peak_value_si", 0.0))
        thresh_v = float(ev.get("threshold_si", 0.0))
        excess = max(peak_v - thresh_v, 0.0)

        censored = ev.get("censored", "false").lower() in ("true", "1", "yes")

        return HydrologicExposure(
            sample_id=sample_id,
            site_no=site_no,
            issue_time_utc=issue_time_utc,
            horizon_hours=horizon_hours,
            has_flood_event=True,
            lead_time_lower_hours=lead_lower,
            lead_time_upper_hours=lead_upper,
            peak_stage_excess_m=excess,
            censored=censored,
        )

    @classmethod
    def validate_cohort_exposure(
        cls,
        cohort_rows: Sequence[Mapping[str, str]],
        sample_metadata: Mapping[str, tuple[str, datetime]],
        event_intervals: Sequence[Mapping[str, str]],
        horizon_hours: float = 24.0,
    ) -> dict[str, HydrologicExposure]:
        """Validate that all cohort labels strictly correspond to hydrological event exposure."""
        exposures: dict[str, HydrologicExposure] = {}
        for row in cohort_rows:
            sid = row["sample_id"]
            cohort_label = row["label"].strip()
            meta = sample_metadata.get(sid)
            if not meta:
                raise ValueError(f"Missing metadata (site_no, issue_time) for sample '{sid}'.")

            site_no, t_issue = meta
            exp = cls.compute_sample_exposure(sid, site_no, t_issue, event_intervals, horizon_hours)

            expected_label = "1" if exp.has_flood_event else "0"
            if cohort_label != expected_label:
                raise LabelConsistencyError(
                    f"Label inconsistency for sample '{sid}': cohort label is '{cohort_label}' "
                    f"but hydrological exposure has flood_event={exp.has_flood_event} (expected '{expected_label}')."
                )
            exposures[sid] = exp

        return exposures
