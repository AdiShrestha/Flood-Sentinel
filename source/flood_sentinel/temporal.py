"""Issue-time filtering and uncertainty-preserving future-event labels."""
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
import math
import re
from typing import Iterable
from .validation import real_scalar


def utc(value: datetime) -> datetime:
    if not isinstance(value, datetime) or value.tzinfo is None or value.utcoffset() is None:
        raise ValueError('An explicit timezone-aware datetime is required; dates are not exact instants.')
    return value.astimezone(timezone.utc)


@dataclass(frozen=True)
class Observation:
    record_id: str
    provider: str
    variable: str
    value: float | None
    unit: str
    observation_start: datetime
    observation_end: datetime
    available_at: datetime | None
    availability_basis: str
    raw_sha256: str
    origin: str = 'observational'

    def __post_init__(self):
        if not all(isinstance(v, str) and v.strip() for v in (self.record_id, self.provider, self.variable, self.unit)):
            raise ValueError('Record identity, provider, variable and unit are required.')
        if not isinstance(self.raw_sha256,str) or not re.fullmatch(r'[a-f0-9]{64}', self.raw_sha256):
            raise ValueError('Record must identify an actual raw-byte SHA-256; a hash is not authentication.')
        if self.value is not None: real_scalar(self.value)
        if utc(self.observation_start) > utc(self.observation_end):
            raise ValueError('Observation interval is inverted.')
        if self.availability_basis not in {'observed', 'assumed', 'unknown'}:
            raise ValueError('Availability basis must be observed, assumed or unknown.')
        if self.origin not in {'observational', 'simulation'}:
            raise ValueError('Origin must distinguish observations and declared model output.')
        if self.availability_basis == 'unknown' and self.available_at is not None:
            raise ValueError('Unknown availability cannot carry an invented timestamp.')
        if self.availability_basis != 'unknown' and self.available_at is None:
            raise ValueError('Known/assumed availability requires a timestamp.')
        if self.available_at is not None and utc(self.available_at) < utc(self.observation_end):
            raise ValueError('An aggregate observation cannot be available before its interval ends.')


def as_of(records: Iterable[Observation], issue_time: datetime, *, allow_assumed: bool = False) -> list[Observation]:
    """Select observations available when a prediction is issued, never at its target time.

    Unknown vintages fail rather than silently becoming real-time evidence. Explicit
    assumed availability is allowed only for a separately disclosed retrospective study.
    """
    issue = utc(issue_time)
    if type(allow_assumed) is not bool: raise ValueError('allow_assumed requires an explicit boolean.')
    rows = list(records)
    if any(not isinstance(r,Observation) for r in rows): raise ValueError('Observation records required.')
    if len({r.record_id for r in rows}) != len(rows):
        raise ValueError('Duplicate source record IDs.')
    selected = []
    for r in rows:
        if r.availability_basis == 'unknown' or (r.availability_basis == 'assumed' and not allow_assumed):
            raise ValueError('Availability is unverified; do not present this stream as operational replay.')
        if utc(r.observation_end) <= issue and utc(r.available_at) <= issue:
            selected.append(r)
    return sorted(selected, key=lambda r: (utc(r.observation_end), r.record_id))


@dataclass(frozen=True)
class OnsetInterval:
    """Onset in (lower, upper], or an exact instant when lower == upper.

    lower=None denotes a left-censored crossing; it is not an exact onset.
    """
    event_id: str
    lower: datetime | None
    upper: datetime

    def __post_init__(self):
        if not isinstance(self.event_id,str) or not self.event_id.strip(): raise ValueError('An event ID is required.')
        utc(self.upper)
        if self.lower is not None and utc(self.lower) > utc(self.upper):
            raise ValueError('Onset interval is inverted.')


def future_event_label(issue_time: datetime, horizon: timedelta, onsets: Iterable[OnsetInterval], *,
                       coverage_complete: bool, currently_below_threshold: bool) -> int | None:
    """Label an onset strictly after issue and at/before the horizon; ambiguity is None.

    Coverage and current state must be established by the acquisition adapter.
    Unknown/gapped observation coverage cannot produce a negative label.
    """
    issue = utc(issue_time)
    if not isinstance(horizon,timedelta) or horizon <= timedelta(0): raise ValueError('Horizon must be a positive timedelta.')
    if type(coverage_complete) is not bool or type(currently_below_threshold) is not bool:
        raise ValueError('Coverage and current state require explicit boolean decisions.')
    if not currently_below_threshold: return None
    end = issue + horizon
    rows = list(onsets)
    if any(not isinstance(r,OnsetInterval) for r in rows): raise ValueError('OnsetInterval records required.')
    if len({r.event_id for r in rows}) != len(rows): raise ValueError('Duplicate event IDs.')
    ambiguous = False
    for event in rows:
        upper = utc(event.upper)
        lower = utc(event.lower) if event.lower is not None else None
        if upper <= issue or (lower is not None and lower >= end and lower != upper): continue
        if lower is not None and lower == upper:
            if issue < upper <= end: return 1
        elif lower is not None and lower >= issue and upper <= end:
            return 1
        elif (lower is None or lower < end) and upper > issue:
            ambiguous = True
    return None if ambiguous or not coverage_complete else 0


def first_persistent_alert(times: Iterable[datetime], scores: Iterable[float], *, threshold: float,
                           consecutive: int, cadence: timedelta) -> datetime | None:
    """Return the confirmation time of the first alert, not the first of its k observations."""
    ts = [utc(t) for t in times]; values = list(scores)
    threshold = real_scalar(threshold)
    values = [real_scalar(s) for s in values]
    if len(ts) != len(values): raise ValueError('Time and score lengths disagree.')
    if type(consecutive) is not int or consecutive < 1 or not isinstance(cadence,timedelta) or cadence <= timedelta(0):
        raise ValueError('A positive integer persistence length and positive cadence are required.')
    if not math.isfinite(threshold) or any(not math.isfinite(s) for s in values):
        raise ValueError('Alert scores and threshold must be finite; missing scores require a gap.')
    if any(b <= a for a, b in zip(ts, ts[1:])): raise ValueError('Alert timestamps must be unique and ordered.')
    run = 0
    for i, (t, value) in enumerate(zip(ts, values)):
        if i and t - ts[i-1] != cadence: run = 0
        run = run + 1 if value >= threshold else 0
        if run >= consecutive: return t
    return None
