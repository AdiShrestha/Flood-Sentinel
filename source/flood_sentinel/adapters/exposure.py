"""Event and hydrological exposure adapter linking cohort issues to event intervals."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
import math
from typing import Mapping, Sequence
from flood_sentinel.temporal import OnsetInterval, utc
from flood_sentinel.evidence import label_issue
from flood_sentinel.identifiers import canonical_site, parse_sample_identity, require_identifier


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
        has_flood_event: Existential label for a definite onset in (t_issue, t_issue + horizon].
        lead_time_lower_hours: Infimum of the compatible earliest future-onset interval.
        lead_time_upper_hours: Upper bound of the compatible earliest future-onset interval.
        peak_stage_excess_m: Maximum stage above threshold observed during the event.
        censored: Whether the event interval was right-censored.
    """
    sample_id: str
    site_no: str
    issue_time_utc: datetime
    horizon_hours: float
    has_flood_event: bool | None
    lead_time_lower_hours: float | None = None
    lead_time_upper_hours: float | None = None
    peak_stage_excess_m: float | None = None
    censored: bool | None = None
    label_status: str = 'unknown'
    label_reason: str = 'missing_coverage_evidence'
    onset_intervals: tuple[OnsetInterval, ...] = ()
    first_onset_status: str = 'unknown'
    first_onset_event_ids: tuple[str, ...] = ()


class ExposureAdapter:
    """Adapter verifying and mapping hydrological exposure from the event intervals catalog."""

    @staticmethod
    def compute_sample_exposure(
        sample_id: str,
        site_no: str,
        issue_time_utc: datetime,
        event_intervals: Sequence[Mapping[str, str]],
        horizon_hours: float = 24.0,
        *, coverage_complete: bool = False, currently_below_threshold: bool | None = None,
        ongoing: bool | None = None,
    ) -> HydrologicExposure:
        """Compute hydrological exposure metrics for an issue against authentic event intervals."""
        sample_id = require_identifier(sample_id, field='sample_id')
        site_no = canonical_site(site_no, field='site_no')
        issue_time_utc = utc(issue_time_utc)
        sample_site, sample_timestamp = parse_sample_identity(sample_id)
        if sample_site != site_no:
            raise ValueError('Sample identifier site differs from exposure site')
        encoded_issue = datetime.strptime(sample_timestamp, '%Y%m%dT%H%M%SZ').replace(tzinfo=issue_time_utc.tzinfo)
        if encoded_issue != issue_time_utc:
            raise ValueError('Sample identifier issue time differs from exposure issue time')
        if not isinstance(horizon_hours, (int, float)) or not math.isfinite(horizon_hours) or horizon_hours <= 0:
            raise ValueError('A finite positive horizon is required')
        if not isinstance(event_intervals, Sequence):
            raise ValueError('Event interval sequence required')
        onsets = []
        seen_ids = set()
        for ev in event_intervals:
            if not isinstance(ev, Mapping):
                raise ValueError('Event catalog rows must be mappings')
            event_site = canonical_site(ev.get('site_no'), field='event site_no')
            event_id = require_identifier(ev.get('event_id'), field='event_id')
            if event_id in seen_ids:
                raise ValueError(f'Duplicate event catalog ID {event_id!r}')
            seen_ids.add(event_id)
            if not ev.get('onset_upper_utc'):
                raise ValueError('Missing onset bound; cannot silently omit event')
            onset = OnsetInterval(event_id,
                utc(datetime.fromisoformat(ev['onset_lower_utc'])) if ev.get('onset_lower_utc') else None,
                utc(datetime.fromisoformat(ev['onset_upper_utc'])))
            if event_site == site_no:
                onsets.append(onset)
        label = label_issue(issue_time_utc, timedelta(hours=horizon_hours), onsets,
                            current_below=currently_below_threshold,
                            coverage_complete=coverage_complete, ongoing=ongoing)
        # Existential label admission and first-onset timing answer different
        # questions. Compute earliest-onset uncertainty across every possible
        # future interval, regardless of the alert horizon or label state.
        future = [o for o in onsets if utc(o.upper) > issue_time_utc]
        first_status, first_ids = 'no_future_onset_in_catalog', ()
        lead_lower = lead_upper = None
        if future:
            if any(o.lower is None or utc(o.lower) < issue_time_utc for o in future):
                first_status = 'unknown_interval_may_precede_issue'
            else:
                earliest_upper = min(utc(o.upper) for o in future)
                first_candidates = tuple(sorted(o.event_id for o in future
                    if utc(o.lower) < earliest_upper or
                    (utc(o.lower) == earliest_upper and utc(o.upper) == earliest_upper)))
                if not first_candidates:
                    raise ValueError('No compatible first-onset interval in a nonempty future catalog')
                earliest_lower = min(utc(o.lower) for o in future if o.event_id in first_candidates)
                first_status, first_ids = 'bounded_interval_uncertainty', first_candidates
                lead_lower = (earliest_lower - issue_time_utc).total_seconds() / 3600
                lead_upper = (earliest_upper - issue_time_utc).total_seconds() / 3600
        return HydrologicExposure(sample_id, site_no, issue_time_utc, horizon_hours,
            None if label.label is None else bool(label.label),
            lead_time_lower_hours=lead_lower, lead_time_upper_hours=lead_upper,
            label_status=label.status, label_reason=label.reason, onset_intervals=tuple(onsets),
            first_onset_status=first_status, first_onset_event_ids=first_ids)

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
            sid = require_identifier(row.get("sample_id"), field='sample_id')
            cohort_label = require_identifier(row.get("label"), field='label')
            meta = sample_metadata.get(sid)
            if not meta:
                raise ValueError(f"Missing metadata (site_no, issue_time) for sample '{sid}'.")

            site_no, t_issue = meta
            exp = cls.compute_sample_exposure(sid, site_no, t_issue, event_intervals, horizon_hours)

            if exp.has_flood_event is None:
                raise LabelConsistencyError('Legacy cohort has no independently established coverage/current state')

            expected_label = "1" if exp.has_flood_event else "0"
            if cohort_label != expected_label:
                raise LabelConsistencyError(
                    f"Label inconsistency for sample '{sid}': cohort label is '{cohort_label}' "
                    f"but hydrological exposure has flood_event={exp.has_flood_event} (expected '{expected_label}')."
                )
            exposures[sid] = exp

        return exposures
