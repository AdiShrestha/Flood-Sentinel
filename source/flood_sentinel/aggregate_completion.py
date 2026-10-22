"""Daily-mean aggregate episode completion labels (not physical onset labels).

The evaluator accepts already decoded, source-linked daily mean rows.  It is
deliberately separate from the point-observation/physical-onset path: a daily
aggregate closes at a boundary, and that boundary is not a measured flood
onset or a source release time.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, time, timedelta, timezone, tzinfo
from decimal import Decimal
from fractions import Fraction
from decimal import localcontext
from typing import Iterable, Literal, Sequence
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError


UTC = timezone.utc
HORIZON_HOURS = (24, 48, 72)
QualityStatus = Literal[
    "approved_unflagged",
    "estimated_flagged",
    "unusable_quality",
    "missing_value",
    "missing_date",
]
StateStatus = Literal[
    "unarmed_initial",
    "armed",
    "active",
    "recovering",
    "unresolved",
]
LabelStatus = Literal["positive", "negative", "unknown"]


def _is_utc(value: datetime) -> bool:
    return value.tzinfo is not None and value.utcoffset() == timedelta(0)


def _hours_exact(delta: timedelta) -> Decimal:
    micros = (delta.days * 86_400 + delta.seconds) * 1_000_000 + delta.microseconds
    return Decimal(micros) / Decimal(3_600_000_000)


def map_local_day_window(local_date: date, zone: tzinfo, *, basis: str) -> tuple[datetime, datetime]:
    """Map one local civil date to UTC without silently resolving bad midnights.

    The caller supplies and records a versioned zone interpretation. This
    helper does not infer an IANA identifier from provider abbreviations.
    Ambiguous/nonexistent local midnight boundaries fail closed.
    """
    if type(local_date) is not date or not isinstance(zone, tzinfo):
        raise ValueError("A local date and explicitly supplied timezone rule are required")
    if type(basis) is not str or not basis.strip():
        raise ValueError("The interval's documentary/assumption basis must be retained")

    def boundary(day: date) -> datetime:
        naive = datetime.combine(day, time.min)
        first = naive.replace(tzinfo=zone, fold=0)
        second = naive.replace(tzinfo=zone, fold=1)
        if first.utcoffset() != second.utcoffset():
            raise ValueError(f"Ambiguous local midnight for {day}; retain interval as unresolved")
        round_trip = first.astimezone(UTC).astimezone(zone).replace(tzinfo=None)
        if round_trip != naive:
            raise ValueError(f"Nonexistent local midnight for {day}; retain interval as unresolved")
        return first.astimezone(UTC)

    start = boundary(local_date)
    end = boundary(local_date + timedelta(days=1))
    if end <= start:
        raise ValueError("Mapped local day must have positive duration")
    return start, end


@dataclass(frozen=True)
class DailyMean:
    """One provider daily-mean record or an explicit missing-calendar slot.

    `window_start_utc`/`window_end_utc` are interval assignments, not fields
    supplied by the date-only daily API. `window_basis` must name the evidence
    and any zone assumption used to derive them. Historical release remains
    unknown in this contract.
    """

    site_id: str
    local_date: date
    window_start_utc: datetime | None
    window_end_utc: datetime | None
    value: Decimal | None
    quality_status: QualityStatus
    provider_record_id: str | None
    series_id: str
    parameter_code: str = "00060"
    statistic_id: str = "00003"
    unit: str = "ft^3/s"
    window_basis: str = ""
    interval_mapping_status: Literal["mapped_assumption", "unresolved"] = "mapped_assumption"
    historical_release_status: Literal["unknown"] = "unknown"

    def __post_init__(self) -> None:
        if type(self.site_id) is not str or not self.site_id.strip():
            raise ValueError("A nonempty canonical site ID is required")
        if type(self.local_date) is not date:
            raise ValueError("local_date must be a date, not a string or datetime")
        if type(self.series_id) is not str or not self.series_id.strip():
            raise ValueError("A nonempty selected daily-series ID is required")
        if self.parameter_code != "00060" or self.statistic_id != "00003":
            raise ValueError("T1a-DV completion requires daily mean discharge 00060/00003")
        if self.unit != "ft^3/s":
            raise ValueError("This captured-source contract expects ft^3/s; convert explicitly")
        if self.quality_status not in (
            "approved_unflagged", "estimated_flagged", "unusable_quality",
            "missing_value", "missing_date",
        ):
            raise ValueError("Daily quality must use a registered source-quality state")
        if self.interval_mapping_status not in ("mapped_assumption", "unresolved"):
            raise ValueError("Daily interval mapping must be mapped_assumption or unresolved")
        if self.historical_release_status != "unknown":
            raise ValueError("This panel has no authenticated historical release evidence")
        if self.interval_mapping_status == "mapped_assumption":
            if self.window_start_utc is None or self.window_end_utc is None:
                raise ValueError("Mapped daily window requires both UTC endpoints")
            if not _is_utc(self.window_start_utc) or not _is_utc(self.window_end_utc):
                raise ValueError("Daily-window endpoints must be timezone-aware UTC")
            if self.window_end_utc <= self.window_start_utc:
                raise ValueError("Daily-window end must follow its start")
            if type(self.window_basis) is not str or not self.window_basis.strip():
                raise ValueError("Mapped interval requires an explicit evidence/assumption basis")
        elif self.window_start_utc is not None or self.window_end_utc is not None:
            raise ValueError("Unresolved interval must not carry guessed UTC endpoints")
        if self.quality_status in ("approved_unflagged", "estimated_flagged"):
            if type(self.value) is not Decimal or not self.value.is_finite() or self.value < 0:
                raise ValueError("Usable T1 truth requires a finite nonnegative Decimal value")
            if type(self.provider_record_id) is not str or not self.provider_record_id.strip():
                raise ValueError("Usable provider row requires a nonempty record ID")
        elif self.value is not None and (type(self.value) is not Decimal or not self.value.is_finite()):
            raise ValueError("Present diagnostic value must be a finite Decimal")
        if self.provider_record_id is not None and (
            type(self.provider_record_id) is not str or not self.provider_record_id.strip()
        ):
            raise ValueError("Provider record ID must be nonempty or explicitly absent")

    @property
    def truth_usable_primary(self) -> bool:
        return self.quality_status in ("approved_unflagged", "estimated_flagged")

    @property
    def truth_usable_unflagged(self) -> bool:
        return self.quality_status == "approved_unflagged"

    @property
    def input_usable(self) -> bool:
        # Estimated/reconstructed values may remain truth; they are masked as
        # autoregressive inputs under the project's input/truth separation.
        return self.quality_status == "approved_unflagged"


@dataclass(frozen=True)
class DailyCalendarContract:
    """Predeclared identity, extent and local-civil calendar for one series.

    The extent is an expected calendar, not a summary inferred from returned
    rows. Rows outside it are rejected; absent dates inside it become explicit
    missing slots. The IANA zone and basis remain an explicit scientific
    assumption/evidence record.
    """

    site_id: str
    series_id: str
    start_date: date
    end_date_exclusive: date
    zone_name: str
    window_basis: str
    parameter_code: str = "00060"
    statistic_id: str = "00003"
    unit: str = "ft^3/s"

    def __post_init__(self) -> None:
        for value, description in ((self.site_id, "site ID"), (self.series_id, "series ID"),
                                   (self.zone_name, "IANA timezone"),
                                   (self.window_basis, "interval basis")):
            if type(value) is not str or not value.strip():
                raise ValueError(f"A nonempty {description} is required")
        if type(self.start_date) is not date or type(self.end_date_exclusive) is not date:
            raise ValueError("Calendar extent must use date values, not strings or datetimes")
        if self.start_date >= self.end_date_exclusive:
            raise ValueError("Expected calendar extent must be nonempty")
        if (self.parameter_code, self.statistic_id, self.unit) != ("00060", "00003", "ft^3/s"):
            raise ValueError("T1a-DV completion requires the selected daily mean discharge identity")
        try:
            ZoneInfo(self.zone_name)
        except (ZoneInfoNotFoundError, ValueError) as exc:
            raise ValueError(f"Unknown IANA timezone: {self.zone_name!r}") from exc


@dataclass(frozen=True)
class DayState:
    site_id: str
    local_date: date
    state_before: StateStatus
    state_after: StateStatus
    daily_class: Literal["below", "high", "unknown"]
    transition: str
    below_run: int
    source_record_id: str | None
    arming_record_ids: tuple[str, ...]
    completion_key: str | None = None
    completion_record_id: str | None = None
    completion_time_utc: datetime | None = None
    completion_quality: str | None = None
    censored_high: bool = False


@dataclass(frozen=True)
class IssueLabel:
    site_id: str
    issue_time_utc: datetime
    horizon_hours: int
    issue_state: StateStatus
    eligible: bool
    label_status: LabelStatus
    reason: str
    target_completion_keys: tuple[str, ...]
    target_record_ids: tuple[str, ...]
    target_completion_times_utc: tuple[datetime, ...]
    verification_lead_hours: tuple[Decimal, ...]
    required_closed_dates: tuple[str, ...]
    missing_or_unusable_future_dates: tuple[str, ...]
    arming_record_ids_at_issue: tuple[str, ...]
    issue_open_window_local_date: str | None
    issue_open_window_overlap_hours: Decimal
    physical_current_state: Literal["unknown"] = "unknown"
    physical_onset_time_utc: None = None
    physical_warning_lead_hours: None = None


def type8_threshold_fraction(
    values: Iterable[Decimal], p: Decimal = Decimal("0.99")
) -> Fraction:
    """Return the exact rational Type-8 threshold for finite decimal inputs."""
    if type(p) is not Decimal or not p.is_finite() or not Decimal(0) < p < Decimal(1):
        raise ValueError("p must be a finite Decimal strictly between zero and one")
    xs = sorted(values)
    if len(xs) < 2 or any(type(x) is not Decimal or not x.is_finite() for x in xs):
        raise ValueError("Type-8 quantile requires at least two finite Decimal values")
    exact_xs = [Fraction(x) for x in xs]
    n = len(exact_xs)
    p_exact = Fraction(p)
    h_exact = (Fraction(n) + Fraction(1, 3)) * p_exact + Fraction(1, 3)
    if h_exact <= 1:
        return exact_xs[0]
    if h_exact >= n:
        return exact_xs[-1]
    j = h_exact.numerator // h_exact.denominator
    g_exact = h_exact - j
    return exact_xs[j - 1] + g_exact * (exact_xs[j] - exact_xs[j - 1])


def type8_threshold(values: Iterable[Decimal], p: Decimal = Decimal("0.99")) -> Decimal:
    """Hyndman-Fan Type 8 threshold, rounded only for display/persistence."""
    exact = type8_threshold_fraction(values, p)
    with localcontext() as context:
        context.prec = 50
        return Decimal(exact.numerator) / Decimal(exact.denominator)


def reference_type8_threshold(
    rows: Sequence[DailyMean],
    start: date,
    end_exclusive: date,
    *,
    include_estimated: bool = True,
    p: Decimal = Decimal("0.99"),
) -> Fraction:
    """Compute a Type-8 threshold from a fixed half-open calendar reference.

    Rows outside ``[start, end_exclusive)`` cannot affect the result, even if
    a future/evaluation value is mutated. Only the caller's declared truth
    lane contributes values.
    """
    if type(start) is not date or type(end_exclusive) is not date or start >= end_exclusive:
        raise ValueError("A nonempty half-open reference date range is required")
    members = [row.value for row in rows
               if start <= row.local_date < end_exclusive
               and _truth_usable(row, include_estimated)
               and row.interval_mapping_status == "mapped_assumption"]
    return type8_threshold_fraction(members, p)


def _truth_usable(row: DailyMean, include_estimated: bool) -> bool:
    if type(include_estimated) is not bool:
        raise ValueError("include_estimated must be an explicit boolean quality lane")
    return row.truth_usable_primary if include_estimated else row.truth_usable_unflagged


def build_state_trace(
    rows: Sequence[DailyMean], threshold: Decimal | Fraction, *, include_estimated: bool = True
) -> tuple[DayState, ...]:
    """Apply the declared 3-observed-day aggregate completion recurrence.

    A high aggregate completes only from `armed`. Initial/unresolved highs are
    censored. A missing/unusable date makes state unresolved; three subsequent
    usable below-threshold local-date aggregates restore armed state.
    """
    if type(threshold) is Decimal:
        if not threshold.is_finite() or threshold < 0:
            raise ValueError("A finite nonnegative Decimal threshold is required")
    elif type(threshold) is Fraction:
        if threshold.denominator <= 0 or threshold < 0:
            raise ValueError("A nonnegative exact rational threshold is required")
    else:
        raise ValueError("A finite Decimal or exact rational threshold is required")
    if not rows:
        return ()
    site = rows[0].site_id
    if any(row.site_id != site for row in rows):
        raise ValueError("A state trace may contain only one canonical site")
    ordered = tuple(rows)
    if any(ordered[i].local_date >= ordered[i + 1].local_date for i in range(len(ordered) - 1)):
        raise ValueError("Daily rows must be unique and ordered by local date")
    if any((ordered[i + 1].local_date - ordered[i].local_date).days != 1
           for i in range(len(ordered) - 1)):
        raise ValueError("Missing calendar dates must be retained as explicit missing slots")
    for left, right in zip(ordered, ordered[1:]):
        if (left.interval_mapping_status == "mapped_assumption"
                and right.interval_mapping_status == "mapped_assumption"
                and left.window_end_utc != right.window_start_utc):
            raise ValueError("Assigned daily windows must be contiguous; gaps/overlaps are not repaired")

    phase: StateStatus = "unarmed_initial"
    below_ids: list[str] = []
    completion_n = 0
    current_episode_key: str | None = None
    trace: list[DayState] = []
    for row in ordered:
        before = phase
        usable = _truth_usable(row, include_estimated) and row.interval_mapping_status == "mapped_assumption"
        if not usable:
            phase = "unresolved"
            below_ids = []
            current_episode_key = None
            trace.append(DayState(
                row.site_id, row.local_date, before, phase, "unknown",
                "missing_or_unusable_break", 0, row.provider_record_id, (),
            ))
            continue

        assert row.value is not None
        exact_threshold = threshold if isinstance(threshold, Fraction) else Fraction(threshold)
        high = Fraction(row.value) > exact_threshold
        if phase == "armed":
            if high:
                event_arm_ids = tuple(below_ids)
                completion_n += 1
                event_key = f"{site}:aggregate-completion:{completion_n:04d}"
                phase = "active"
                below_ids = []
                current_episode_key = event_key
                trace.append(DayState(
                    row.site_id, row.local_date, before, phase, "high",
                    "qualifying_completion", 0, row.provider_record_id, event_arm_ids,
                    event_key, row.provider_record_id, row.window_end_utc,
                    row.quality_status, False,
                ))
            else:
                if row.provider_record_id:
                    below_ids.append(row.provider_record_id)
                below_ids = below_ids[-3:]
                trace.append(DayState(
                    row.site_id, row.local_date, before, phase, "below",
                    "remain_armed", 3, row.provider_record_id, tuple(below_ids),
                    completion_key=current_episode_key,
                ))
            continue

        if phase in ("active", "recovering"):
            if high:
                phase = "active"
                below_ids = []
                trace.append(DayState(
                    row.site_id, row.local_date, before, phase, "high",
                    "same_disarmed_episode", 0, row.provider_record_id, (),
                    completion_key=current_episode_key,
                ))
            else:
                if row.provider_record_id:
                    below_ids.append(row.provider_record_id)
                below_ids = below_ids[-3:]
                if len(below_ids) == 3:
                    phase = "armed"
                    transition = "rearmed_after_three_below"
                    current_episode_key = None
                else:
                    phase = "recovering"
                    transition = "recovery_below_day"
                trace.append(DayState(
                    row.site_id, row.local_date, before, phase, "below",
                    transition, len(below_ids), row.provider_record_id, tuple(below_ids),
                ))
            continue

        # Initial or unresolved state: high is censored, while below days only
        # re-establish a known armed state after three consecutive records.
        if high:
            phase = "unresolved"
            below_ids = []
            trace.append(DayState(
                row.site_id, row.local_date, before, phase, "high",
                "censored_high_without_armed_predecessor", 0,
                row.provider_record_id, (), censored_high=True,
            ))
        else:
            if row.provider_record_id:
                below_ids.append(row.provider_record_id)
            below_ids = below_ids[-3:]
            if len(below_ids) == 3:
                phase = "armed"
                transition = "armed_after_three_below"
            else:
                transition = "initial_below_accumulation" if before == "unarmed_initial" else "unresolved_below_accumulation"
                phase = before
            trace.append(DayState(
                row.site_id, row.local_date, before, phase, "below",
                transition, len(below_ids), row.provider_record_id, tuple(below_ids),
            ))
    return tuple(trace)


def _calendarize_rows(
    rows: Sequence[DailyMean], contract: DailyCalendarContract
) -> tuple[DailyMean, ...]:
    """Validate and expand returned source rows onto a predeclared calendar."""
    supplied: dict[date, DailyMean] = {}
    record_ids: set[str] = set()
    for row in rows:
        if (row.site_id, row.series_id, row.parameter_code, row.statistic_id, row.unit) != (
            contract.site_id, contract.series_id, contract.parameter_code,
            contract.statistic_id, contract.unit,
        ):
            raise ValueError("Source row site/series/parameter/statistic/unit disagrees with calendar contract")
        if not contract.start_date <= row.local_date < contract.end_date_exclusive:
            raise ValueError("Source row falls outside the predeclared calendar extent")
        if row.local_date in supplied:
            raise ValueError(f"Conflicting or duplicate source rows for {row.local_date}")
        if row.provider_record_id is not None:
            if row.provider_record_id in record_ids:
                raise ValueError("Provider record IDs must be unique within the source calendar")
            record_ids.add(row.provider_record_id)
        if row.interval_mapping_status == "mapped_assumption":
            expected_start, expected_end = map_local_day_window(
                row.local_date, ZoneInfo(contract.zone_name), basis=contract.window_basis
            )
            if (row.window_start_utc, row.window_end_utc) != (expected_start, expected_end):
                raise ValueError(f"Source row interval conflicts with explicit local calendar for {row.local_date}")
            if row.window_basis != contract.window_basis:
                raise ValueError(f"Source row interval basis disagrees with calendar contract for {row.local_date}")
        supplied[row.local_date] = row

    result: list[DailyMean] = []
    day = contract.start_date
    zone = ZoneInfo(contract.zone_name)
    while day < contract.end_date_exclusive:
        row = supplied.get(day)
        if row is None:
            start, end = map_local_day_window(day, zone, basis=contract.window_basis)
            row = DailyMean(
                site_id=contract.site_id, local_date=day,
                window_start_utc=start, window_end_utc=end,
                value=None, quality_status="missing_date", provider_record_id=None,
                series_id=contract.series_id, parameter_code=contract.parameter_code,
                statistic_id=contract.statistic_id, unit=contract.unit,
                window_basis=contract.window_basis,
            )
        result.append(row)
        day += timedelta(days=1)
    return tuple(result)


def _expected_closed_dates(
    issue: datetime, horizon_hours: int, contract: DailyCalendarContract
) -> tuple[tuple[date, datetime], ...]:
    """Enumerate closures from issue time and the declared civil calendar."""
    zone = ZoneInfo(contract.zone_name)
    horizon_end = issue + timedelta(hours=horizon_hours)
    first = issue.astimezone(zone).date() - timedelta(days=2)
    last = horizon_end.astimezone(zone).date() + timedelta(days=2)
    closures: list[tuple[date, datetime]] = []
    day = first
    while day <= last:
        _, end = map_local_day_window(day, zone, basis=contract.window_basis)
        if issue < end <= horizon_end:
            closures.append((day, end))
        day += timedelta(days=1)
    if not closures:
        raise ValueError("Declared local calendar yields no closures inside a registered target horizon")
    return tuple(closures)


def _check_completion_lineage(
    rows: Sequence[DailyMean], trace: Sequence[DayState], threshold: Decimal | Fraction,
    include_estimated: bool,
) -> None:
    exact_threshold = threshold if isinstance(threshold, Fraction) else Fraction(threshold)
    for index, state in enumerate(trace):
        if state.transition != "qualifying_completion":
            continue
        if index < 3:
            raise ValueError("A completion has no three-date predecessor lineage")
        predecessors = rows[index - 3:index]
        expected_ids = tuple(row.provider_record_id for row in predecessors)
        if (len(expected_ids) != 3 or any(type(value) is not str or not value.strip() for value in expected_ids)
                or state.arming_record_ids != expected_ids):
            raise ValueError("A completion's arming IDs do not match its exact preceding source rows")
        if any(not _truth_usable(row, include_estimated)
               or row.interval_mapping_status != "mapped_assumption"
               or row.value is None or Fraction(row.value) > exact_threshold
               for row in predecessors):
            raise ValueError("A completion's three arming rows are not usable below-threshold truth")
        if (state.source_record_id != rows[index].provider_record_id
                or state.completion_record_id != rows[index].provider_record_id
                or state.completion_time_utc != rows[index].window_end_utc):
            raise ValueError("A completion's source ID or interval boundary is stale")


def evaluate_issue_labels(
    rows: Sequence[DailyMean],
    threshold: Decimal | Fraction,
    issue_times_utc: Sequence[datetime],
    *,
    calendar: DailyCalendarContract,
    horizons_hours: Sequence[int] = HORIZON_HOURS,
    include_estimated: bool = True,
) -> tuple[IssueLabel, ...]:
    """Build trace and labels coherently from rows, threshold, lane and calendar.

    No caller-supplied state trace is accepted. Every requested issue is
    retained, including when ``rows`` is empty; missing dates are expanded
    from the predeclared calendar and cannot become implicit negatives.
    """
    if not isinstance(calendar, DailyCalendarContract):
        raise ValueError("An explicit daily calendar contract is required")
    if type(threshold) is Decimal:
        if not threshold.is_finite() or threshold < 0:
            raise ValueError("A finite nonnegative Decimal threshold is required")
    elif type(threshold) is Fraction:
        if threshold.denominator <= 0 or threshold < 0:
            raise ValueError("A nonnegative exact rational threshold is required")
    else:
        raise ValueError("A finite Decimal or exact rational threshold is required")
    if any(type(h) is not int or h not in HORIZON_HOURS for h in horizons_hours):
        raise ValueError("Only real 24/48/72-hour target horizons are registered")
    if len(set(horizons_hours)) != len(horizons_hours):
        raise ValueError("Duplicate horizons are not allowed")
    if len(set(issue_times_utc)) != len(issue_times_utc):
        raise ValueError("Duplicate issue keys are not allowed")

    ordered = _calendarize_rows(rows, calendar)
    trace = build_state_trace(ordered, threshold, include_estimated=include_estimated)
    _check_completion_lineage(ordered, trace, threshold, include_estimated)
    by_date = {row.local_date: (row, state) for row, state in zip(ordered, trace)}
    scheduled_ends = tuple(map_local_day_window(
        row.local_date, ZoneInfo(calendar.zone_name), basis=calendar.window_basis,
    )[1] for row in ordered)
    output: list[IssueLabel] = []
    for issue in issue_times_utc:
        if not _is_utc(issue) or issue.hour != 12 or issue.minute or issue.second or issue.microsecond:
            raise ValueError("Issues must be timezone-aware 12:00 UTC instants")
        # Calendar order determines which evaluator states precede the issue.
        # An unresolved row has no observed endpoints, but its unknown state
        # must still replace an older armed state after its expected closure.
        closed_states = [state for end, state in zip(scheduled_ends, trace) if end <= issue]
        state_at_issue: StateStatus = closed_states[-1].state_after if closed_states else "unarmed_initial"
        arm_ids = closed_states[-1].arming_record_ids if closed_states else ()
        open_rows = [row for row in ordered
                     if row.window_start_utc is not None and row.window_end_utc is not None
                     and row.window_start_utc < issue < row.window_end_utc]
        if len(open_rows) > 1:
            raise ValueError("More than one daily aggregate window overlaps the issue")
        open_row = open_rows[0] if open_rows else None
        overlap = (_hours_exact(issue - open_row.window_start_utc)
                   if open_row is not None else Decimal(0))
        for horizon in horizons_hours:
            expected = _expected_closed_dates(issue, horizon, calendar)
            horizon_end = issue + timedelta(hours=horizon)
            required_dates = tuple(day for day, _ in expected)
            required_set = set(required_dates)
            needed = [(day, by_date.get(day)) for day in required_dates]
            future_completions = [state for day, pair in needed if pair is not None
                                  for state in (pair[1],)
                                  if state.transition == "qualifying_completion"
                                  and state.completion_time_utc is not None
                                  and issue < state.completion_time_utc <= horizon_end]
            eligible = state_at_issue == "armed"
            unusable_dates = [day.isoformat() for day, pair in needed
                              if pair is None
                              or not _truth_usable(pair[0], include_estimated)
                              or pair[1].daily_class == "unknown"
                              or pair[1].censored_high]
            if not eligible:
                label_status: LabelStatus = "unknown"
                reason = f"issue_state_not_armed:{state_at_issue}"
            elif future_completions:
                label_status = "positive"
                reason = "definite_qualifying_aggregate_completion_with_full_arm_lineage"
            elif unusable_dates:
                label_status = "unknown"
                reason = "future_truth_or_episode_state_incomplete"
            else:
                label_status = "negative"
                reason = "complete_required_closures_no_qualifying_completion"

            leads = tuple(_hours_exact(state.completion_time_utc - issue)
                          for state in future_completions if state.completion_time_utc is not None)
            output.append(IssueLabel(
                site_id=calendar.site_id,
                issue_time_utc=issue,
                horizon_hours=horizon,
                issue_state=state_at_issue,
                eligible=eligible,
                label_status=label_status,
                reason=reason,
                target_completion_keys=tuple(x.completion_key for x in future_completions if x.completion_key),
                target_record_ids=tuple(x.completion_record_id for x in future_completions if x.completion_record_id),
                target_completion_times_utc=tuple(x.completion_time_utc for x in future_completions if x.completion_time_utc),
                verification_lead_hours=leads,
                required_closed_dates=tuple(day.isoformat() for day in required_dates),
                missing_or_unusable_future_dates=tuple(unusable_dates),
                arming_record_ids_at_issue=tuple(arm_ids),
                issue_open_window_local_date=None if open_row is None else open_row.local_date.isoformat(),
                issue_open_window_overlap_hours=overlap,
            ))
    return tuple(output)


def last_admissible_persistence(
    rows: Sequence[DailyMean], issue_time_utc: datetime
) -> dict[str, object]:
    """Return the latest unflagged closed daily mean under an explicit replay assumption.

    This reports a raw persistence value and age only. It does not authenticate
    historical access, set a score threshold, or include evaluator state.
    """
    if not _is_utc(issue_time_utc):
        raise ValueError("Persistence issue time must be timezone-aware UTC")
    candidates = [row for row in rows if row.input_usable
                  and row.interval_mapping_status == "mapped_assumption"
                  and row.window_end_utc is not None and row.window_end_utc <= issue_time_utc]
    if not candidates:
        return {
            "score": None, "source_record_id": None, "source_local_date": None,
            "observation_end_utc": None, "age_hours": None,
            "actual_release_status": "unknown",
            "input_admissibility": "assumed_final_product_retrospective_replay",
        }
    latest = max(candidates, key=lambda row: (row.window_end_utc, row.local_date))
    assert latest.value is not None and latest.window_end_utc is not None
    return {
        "score": str(latest.value),
        "source_record_id": latest.provider_record_id,
        "source_local_date": latest.local_date.isoformat(),
        "observation_end_utc": latest.window_end_utc.isoformat().replace("+00:00", "Z"),
        "age_hours": str(_hours_exact(issue_time_utc - latest.window_end_utc)),
        "actual_release_status": "unknown",
        "input_admissibility": "assumed_final_product_retrospective_replay",
    }
