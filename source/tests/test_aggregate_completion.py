"""Constructed aggregate/calendar fixtures; no provider observations are generated."""
from dataclasses import replace
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from fractions import Fraction
from zoneinfo import ZoneInfo

import pytest

from flood_sentinel.aggregate_completion import (
    DailyCalendarContract,
    DailyMean,
    build_state_trace,
    evaluate_issue_labels,
    last_admissible_persistence,
    map_local_day_window,
    reference_type8_threshold,
    type8_threshold,
    type8_threshold_fraction,
)


UTC = timezone.utc
THRESHOLD = Decimal("10")
BASIS = "constructed local-day fixture with explicit boundaries; not observational"
TEST_ZONE = "Etc/GMT-12"  # local midnight maps to 12:00 UTC for clear endpoint fixtures


def _row(i, value, *, quality="approved_unflagged", start=None, end=None,
         site="USGS-TEST", series="fixture-daily-series", zone=TEST_ZONE,
         record_id=None, basis=BASIS):
    day = date(2024, 1, 1) + timedelta(days=i)
    expected_start, expected_end = map_local_day_window(day, ZoneInfo(zone), basis=basis)
    start = expected_start if start is None else start
    end = expected_end if end is None else end
    if quality == "missing_date":
        row_id = None
    else:
        row_id = record_id if record_id is not None else f"fixture-row-{i}"
    return DailyMean(
        site_id=site, local_date=day, window_start_utc=start, window_end_utc=end,
        value=None if value is None else Decimal(str(value)), quality_status=quality,
        provider_record_id=row_id, series_id=series, window_basis=basis,
    )


def _contract(rows=(), *, zone=TEST_ZONE, site="USGS-TEST", series="fixture-daily-series",
              start=None, end=None, basis=BASIS):
    if rows:
        start = min(x.local_date for x in rows) if start is None else start
        end = max(x.local_date for x in rows) + timedelta(days=1) if end is None else end
        site = rows[0].site_id if site == "USGS-TEST" else site
        series = rows[0].series_id if series == "fixture-daily-series" else series
    else:
        start = date(2024, 1, 1) if start is None else start
        end = date(2024, 1, 6) if end is None else end
    return DailyCalendarContract(site, series, start, end, zone, basis)


def _eval(rows, issues, *, horizons=(24, 48, 72), estimates=True,
          threshold=THRESHOLD, contract=None, zone=TEST_ZONE):
    calendar = _contract(rows, zone=zone) if contract is None else contract
    return evaluate_issue_labels(rows, threshold, issues, calendar=calendar,
                                 horizons_hours=horizons, include_estimated=estimates)


def _issue(day_index, *, zone=TEST_ZONE):
    return datetime(2024, 1, 1, 12, tzinfo=UTC) + timedelta(days=day_index)


def test_type8_hand_computed_quantile_and_strict_threshold_boundary():
    assert type8_threshold([Decimal("1"), Decimal("2"), Decimal("3")], Decimal("0.5")) == Decimal("2")
    assert type8_threshold_fraction([Decimal("1"), Decimal("2"), Decimal("3")], Decimal("0.25")) == Fraction(7, 6)
    assert type8_threshold([Decimal("1"), Decimal("2"), Decimal("3")], Decimal("0.25")) == Decimal(
        "1.1666666666666666666666666666666666666666666666667"
    )
    rows = [_row(i, x) for i, x in enumerate([10, 10, 10, 11])]
    trace = build_state_trace(rows, THRESHOLD)
    assert [x.daily_class for x in trace] == ["below", "below", "below", "high"]
    assert trace[2].state_after == "armed"
    assert trace[3].transition == "qualifying_completion"
    assert trace[3].completion_time_utc == rows[3].window_end_utc
    assert trace[3].completion_key == "USGS-TEST:aggregate-completion:0001"
    assert trace[3].arming_record_ids == tuple(row.provider_record_id for row in rows[:3])


def test_initial_high_is_censored_and_does_not_create_an_episode():
    trace = build_state_trace([_row(i, x) for i, x in enumerate([11, 9, 9, 11])], THRESHOLD)
    assert trace[0].state_after == "unresolved"
    assert trace[0].censored_high
    assert trace[3].censored_high
    assert not any(row.transition == "qualifying_completion" for row in trace)


def test_three_below_days_separate_episodes_and_repeated_high_is_same_episode():
    trace = build_state_trace([_row(i, x) for i, x in enumerate([9, 9, 9, 11, 12, 9, 9, 9, 11])], THRESHOLD)
    events = [row for row in trace if row.transition == "qualifying_completion"]
    assert len(events) == 2
    assert trace[4].transition == "same_disarmed_episode"
    assert trace[5].state_after == "recovering"
    assert trace[6].state_after == "recovering"
    assert trace[7].state_after == "armed"
    assert events[0].completion_key != events[1].completion_key
    assert events[1].completion_time_utc == trace[8].completion_time_utc


def test_two_recovery_days_then_high_does_not_rearm_but_three_does():
    trace = build_state_trace([_row(i, x) for i, x in enumerate([9, 9, 9, 11, 9, 9, 12, 9, 9, 9, 12])], THRESHOLD)
    assert trace[6].transition == "same_disarmed_episode"
    assert trace[9].state_after == "armed"
    assert trace[10].transition == "qualifying_completion"
    assert len([row for row in trace if row.transition == "qualifying_completion"]) == 2


def test_missing_date_breaks_recovery_and_censored_high_stays_unknown_until_three_lows():
    rows = [_row(i, x, quality="missing_date" if x is None else "approved_unflagged")
            for i, x in enumerate([9, 9, 9, 11, 9, None, 9, 9, 11, 9, 9, 9, 11])]
    trace = build_state_trace(rows, THRESHOLD)
    assert trace[5].transition == "missing_or_unusable_break"
    assert trace[8].censored_high
    assert trace[11].state_after == "armed"
    assert trace[12].transition == "qualifying_completion"


def test_issue_state_uses_only_closures_at_or_before_issue_and_excludes_same_time_event():
    rows = [_row(i, x) for i, x in enumerate([9, 9, 9, 11, 9, 9, 9, 9])]
    issue = rows[3].window_end_utc
    label = _eval(rows, [issue], horizons=(24,))[0]
    assert label.issue_state == "active"
    assert not label.eligible
    assert label.label_status == "unknown"
    assert label.target_completion_times_utc == ()


def test_horizon_right_endpoint_is_inclusive_and_lead_is_verification_only():
    rows = [_row(i, x) for i, x in enumerate([9, 9, 9, 11, 9, 9, 9, 9])]
    issue = rows[2].window_end_utc
    result = _eval(rows, [issue], horizons=(24,))[0]
    assert result.issue_state == "armed"
    assert result.eligible
    assert result.label_status == "positive"
    assert result.target_completion_times_utc == (rows[3].window_end_utc,)
    assert result.verification_lead_hours == (Decimal("24"),)
    assert result.physical_current_state == "unknown"
    assert result.physical_onset_time_utc is None
    assert result.physical_warning_lead_hours is None


def test_partial_day_issue_overlap_is_seven_hours_and_closure_is_plus_17():
    zone = "America/New_York"
    days = [date(2024, 1, 1) + timedelta(days=i) for i in range(4)]
    rows = []
    for i, (day, value) in enumerate(zip(days, [9, 9, 9, 11])):
        start, end = map_local_day_window(day, ZoneInfo(zone), basis=BASIS)
        rows.append(replace(_row(i, value, zone=zone), local_date=day,
                            window_start_utc=start, window_end_utc=end))
    issue = datetime(2024, 1, 1, 12, tzinfo=UTC)
    result = _eval(rows, [issue], horizons=(24,), zone=zone)[0]
    assert result.issue_open_window_local_date == "2024-01-01"
    assert result.issue_open_window_overlap_hours == Decimal("7")
    assert result.label_status == "unknown"  # the process was not armed at issue
    assert rows[0].window_end_utc - issue == timedelta(hours=17)


def test_armed_noon_issue_can_be_completed_by_same_date_daily_mean_at_plus_17():
    zone = "America/New_York"
    days = [date(2023, 12, 29) + timedelta(days=i) for i in range(4)]
    rows = []
    for i, (day, value) in enumerate(zip(days, [9, 9, 9, 11])):
        start, end = map_local_day_window(day, ZoneInfo(zone), basis=BASIS)
        rows.append(replace(_row(i, value, zone=zone), local_date=day,
                            window_start_utc=start, window_end_utc=end))
    issue = datetime(2024, 1, 1, 12, tzinfo=UTC)
    labels = _eval(rows, [issue], zone=zone)
    trace = build_state_trace(rows, THRESHOLD)
    assert trace[2].state_after == "armed"
    assert trace[3].completion_time_utc - issue == timedelta(hours=17)
    assert all(x.label_status == "positive" for x in labels)
    assert all(x.verification_lead_hours == (Decimal("17"),) for x in labels)
    assert all(x.physical_warning_lead_hours is None for x in labels)


def test_missing_or_estimated_truth_cannot_become_a_negative_or_unflagged_positive():
    rows = [_row(i, 9) for i in range(5)]
    rows[3] = _row(3, None, quality="missing_date")
    issue = rows[2].window_end_utc
    result = _eval(rows, [issue], horizons=(24,))[0]
    assert result.issue_state == "armed"
    assert result.label_status == "unknown"
    assert result.missing_or_unusable_future_dates == (rows[3].local_date.isoformat(),)

    rows[3] = _row(3, 11, quality="estimated_flagged")
    primary = _eval(rows, [issue], horizons=(24,), estimates=True)[0]
    unflagged = _eval(rows, [issue], horizons=(24,), estimates=False)[0]
    assert primary.label_status == "positive"
    assert unflagged.label_status == "unknown"
    assert unflagged.target_record_ids == ()


def test_definite_positive_survives_later_unknown_only_with_recomputed_lineage():
    rows = [_row(i, x, quality="missing_date" if x is None else "approved_unflagged")
            for i, x in enumerate([9, 9, 9, 11, None, 9])]
    issue = rows[2].window_end_utc
    result = next(x for x in _eval(rows, [issue], horizons=(48,)) if x.horizon_hours == 48)
    assert result.label_status == "positive"
    assert result.reason.startswith("definite_qualifying")
    assert result.arming_record_ids_at_issue == tuple(row.provider_record_id for row in rows[:3])
    state = build_state_trace(rows, THRESHOLD)[3]
    assert state.arming_record_ids == tuple(row.provider_record_id for row in rows[:3])


def test_values_and_threshold_are_recomputed_without_accepting_a_stale_trace():
    rows = [_row(i, x) for i, x in enumerate([9, 9, 9, 11, 9])]
    issue = rows[2].window_end_utc
    old_trace = build_state_trace(rows, THRESHOLD)
    assert _eval(rows, [issue], horizons=(24,))[0].label_status == "positive"
    changed = list(rows)
    changed[3] = _row(3, 9)
    assert _eval(changed, [issue], horizons=(24,))[0].label_status == "negative"
    assert _eval(rows, [issue], horizons=(24,), threshold=Decimal("11"))[0].label_status == "negative"
    with pytest.raises(ValueError, match="threshold"):
        evaluate_issue_labels(rows, old_trace, [issue], calendar=_contract(rows))


def test_source_id_change_recomputes_arming_membership_and_duplicate_ids_fail():
    rows = [_row(i, x) for i, x in enumerate([9, 9, 9, 11])]
    issue = rows[2].window_end_utc
    expected = _eval(rows, [issue], horizons=(24,))[0]
    changed = list(rows)
    changed[1] = replace(changed[1], provider_record_id="new-source-row-1")
    changed_label = _eval(changed, [issue], horizons=(24,))[0]
    assert changed_label.label_status == expected.label_status == "positive"
    assert changed_label.arming_record_ids_at_issue == (rows[0].provider_record_id,
                                                        "new-source-row-1", rows[2].provider_record_id)
    changed[2] = replace(changed[2], provider_record_id="new-source-row-1")
    with pytest.raises(ValueError, match="unique"):
        _eval(changed, [issue], horizons=(24,))


def test_input_order_is_canonicalized_before_the_internal_recurrence():
    rows = [_row(i, x) for i, x in enumerate([9, 9, 9, 11, 9, 9, 9, 12])]
    issue = rows[2].window_end_utc
    forward = _eval(rows, [issue])
    shuffled = _eval([rows[i] for i in (7, 2, 4, 0, 6, 1, 5, 3)], [issue])
    assert forward == shuffled


@pytest.mark.parametrize("mutation", ["site", "series", "parameter", "statistic", "unit", "window", "basis"])
def test_row_identity_and_interval_mutations_are_rejected(mutation):
    rows = [_row(i, 9) for i in range(4)]
    issue = rows[2].window_end_utc
    changed = list(rows)
    row = changed[1]
    if mutation == "site":
        changed[1] = replace(row, site_id="USGS-OTHER")
    elif mutation == "series":
        changed[1] = replace(row, series_id="another-series")
    elif mutation == "parameter":
        with pytest.raises(ValueError, match="00060/00003"):
            replace(row, parameter_code="00065")
        return
    elif mutation == "statistic":
        with pytest.raises(ValueError, match="00060/00003"):
            replace(row, statistic_id="00001")
        return
    elif mutation == "unit":
        with pytest.raises(ValueError, match=r"ft\^3/s"):
            replace(row, unit="m^3/s")
        return
    elif mutation == "window":
        changed[1] = replace(row, window_start_utc=row.window_start_utc + timedelta(hours=1))
    else:
        changed[1] = replace(row, window_basis="different interval contract")
    with pytest.raises(ValueError):
        _eval(changed, [issue])


def test_empty_source_preserves_each_requested_issue_and_explicit_future_dates():
    contract = _contract((), start=date(2024, 1, 1), end=date(2024, 1, 6))
    issues = [_issue(1), _issue(2)]
    labels = _eval([], issues, contract=contract)
    assert len(labels) == len(issues) * 3
    assert [(x.issue_time_utc, x.horizon_hours) for x in labels] == [
        (issue, horizon) for issue in issues for horizon in (24, 48, 72)
    ]
    assert {x.label_status for x in labels} == {"unknown"}
    assert all(x.required_closed_dates for x in labels)


def test_missing_head_and_internal_calendar_dates_are_explicit_unknowns():
    # The first requested date is absent; only two usable days precede issue.
    rows = [_row(i, 9) for i in range(1, 4)]
    contract = _contract(rows, start=date(2024, 1, 1), end=date(2024, 1, 5))
    issue = datetime(2024, 1, 3, 12, tzinfo=UTC)
    label = _eval(rows, [issue], horizons=(24,), contract=contract)[0]
    assert label.issue_state == "unresolved"
    assert label.label_status == "unknown"
    assert label.required_closed_dates == ("2024-01-04",)

    internal = [_row(0, 9), _row(2, 9), _row(3, 9)]
    issue2 = internal[0].window_end_utc
    label2 = _eval(internal, [issue2], horizons=(24,))[0]
    assert label2.label_status == "unknown"
    assert "2024-01-02" in label2.missing_or_unusable_future_dates


def test_calendar_tail_truncation_keeps_24_negative_but_48_72_unknown():
    zone = "America/New_York"
    first = date(2024, 1, 1)
    last_returned = date(2024, 1, 31)
    rows = []
    day = first
    while day <= last_returned:
        i = (day - first).days
        start, end = map_local_day_window(day, ZoneInfo(zone), basis=BASIS)
        rows.append(replace(_row(i, 9, zone=zone), local_date=day,
                            window_start_utc=start, window_end_utc=end))
        day += timedelta(days=1)
    contract = _contract(rows, zone=zone, start=first, end=date(2024, 2, 4))
    issue = datetime(2024, 1, 31, 12, tzinfo=UTC)
    labels = {x.horizon_hours: x for x in _eval(rows, [issue], contract=contract, zone=zone)}
    assert labels[24].label_status == "negative"
    assert labels[24].required_closed_dates == ("2024-01-31",)
    assert labels[48].label_status == "unknown"
    assert labels[48].required_closed_dates == ("2024-01-31", "2024-02-01")
    assert labels[72].label_status == "unknown"
    assert labels[72].required_closed_dates == ("2024-01-31", "2024-02-01", "2024-02-02")
    assert labels[72].missing_or_unusable_future_dates == ("2024-02-01", "2024-02-02")


def test_dst_leap_day_boundaries_and_actual_hour_horizons():
    zone = ZoneInfo("America/New_York")
    spring_start, spring_end = map_local_day_window(date(2024, 3, 10), zone, basis=BASIS)
    fall_start, fall_end = map_local_day_window(date(2024, 11, 3), zone, basis=BASIS)
    leap_start, leap_end = map_local_day_window(date(2024, 2, 29), zone, basis=BASIS)
    assert spring_end - spring_start == timedelta(hours=23)
    assert fall_end - fall_start == timedelta(hours=25)
    assert leap_end - leap_start == timedelta(hours=24)

    dates = [date(2024, 3, 7) + timedelta(days=i) for i in range(9)]
    rows = []
    for i, day in enumerate(dates):
        start, end = map_local_day_window(day, zone, basis=BASIS)
        rows.append(replace(_row(i, 9, zone="America/New_York"), local_date=day,
                            window_start_utc=start, window_end_utc=end))
    issue = datetime(2024, 3, 10, 12, tzinfo=UTC)
    contract = _contract(rows, zone="America/New_York")
    result = {x.horizon_hours: x for x in _eval(rows, [issue], contract=contract,
                                                zone="America/New_York")}
    assert result[24].required_closed_dates == ("2024-03-10",)
    assert result[48].required_closed_dates == ("2024-03-10", "2024-03-11")
    assert result[72].required_closed_dates == ("2024-03-10", "2024-03-11", "2024-03-12")


def test_unresolved_daily_interval_stays_unknown():
    rows = [_row(i, x) for i, x in enumerate([9, 9, 9, 11, 9])]
    rows[3] = replace(rows[3], window_start_utc=None, window_end_utc=None,
                      window_basis="", interval_mapping_status="unresolved")
    issue = rows[2].window_end_utc
    result = _eval(rows, [issue], horizons=(24,))[0]
    assert result.label_status == "unknown"
    assert result.missing_or_unusable_future_dates == ("2024-01-04",)


def test_unresolved_latest_closed_day_replaces_older_armed_issue_state():
    rows = [_row(i, 9) for i in range(7)]
    issue = rows[3].window_end_utc
    rows[3] = replace(rows[3], window_start_utc=None, window_end_utc=None,
                      window_basis="", interval_mapping_status="unresolved")
    labels = _eval(rows, [issue])
    assert all(x.issue_state == "unresolved" and not x.eligible for x in labels)
    assert all(x.label_status == "unknown" for x in labels)
    # Only three newly usable below dates restore the evaluator's state.
    recovered = _eval([*rows, _row(7, 9)], [rows[6].window_end_utc], horizons=(24,))[0]
    assert recovered.issue_state == "armed"
    assert recovered.label_status == "negative"


@pytest.mark.parametrize("lane", ["False", "True", 0, 1, None])
def test_quality_lane_rejects_non_boolean_values(lane):
    rows = [_row(i, x) for i, x in enumerate([9, 9, 9, 11])]
    rows[3] = replace(rows[3], quality_status="estimated_flagged")
    with pytest.raises(ValueError, match="boolean quality lane"):
        _eval(rows, [rows[2].window_end_utc], estimates=lane)


def test_persistence_uses_latest_closed_unflagged_input_and_reports_assumption_and_age():
    rows = [_row(0, 9), _row(1, 11, quality="estimated_flagged"), _row(2, 8)]
    issue = rows[1].window_end_utc
    result = last_admissible_persistence(rows, issue)
    assert result["score"] == "9"
    assert result["source_record_id"] == rows[0].provider_record_id
    assert result["actual_release_status"] == "unknown"
    assert result["input_admissibility"] == "assumed_final_product_retrospective_replay"
    assert result["age_hours"] == "24"


def test_reference_window_excludes_future_mutation():
    rows = []
    for i, value in enumerate((1, 2, 3, 4)):
        day = date(2023, 1, 1) + timedelta(days=i)
        start, end = map_local_day_window(day, UTC, basis=BASIS)
        rows.append(DailyMean("USGS-TEST", day, start, end, Decimal(value),
                              "approved_unflagged", f"ref-{i}", "fixture-daily-series",
                              window_basis=BASIS))
    reference = reference_type8_threshold(rows, date(2023, 1, 1), date(2023, 1, 5))
    future_start, future_end = map_local_day_window(date(2024, 1, 1), UTC, basis=BASIS)
    future = DailyMean("USGS-TEST", date(2024, 1, 1), future_start, future_end,
                       Decimal("999999"), "approved_unflagged", "future",
                       "fixture-daily-series", window_basis=BASIS)
    assert reference_type8_threshold([*rows, future], date(2023, 1, 1), date(2023, 1, 5)) == reference
    assert type8_threshold_fraction([x.value for x in [*rows, future]]) != reference


def test_invalid_ids_calendar_identity_and_issue_contracts_are_rejected():
    valid = _row(0, 9)
    for bad in ("", "   ", None):
        with pytest.raises(ValueError, match="canonical site ID"):
            replace(valid, site_id=bad)
    for bad in ("", "  ", None):
        with pytest.raises(ValueError, match="series ID"):
            replace(valid, series_id=bad)
    for bad in ("", "  ", None):
        with pytest.raises(ValueError, match="record ID"):
            replace(valid, provider_record_id=bad)
    with pytest.raises(ValueError, match="nonempty site ID"):
        DailyCalendarContract(" ", "series", date(2024, 1, 1), date(2024, 1, 2), "UTC", BASIS)
    with pytest.raises(ValueError, match="selected daily mean"):
        DailyCalendarContract("site", "series", date(2024, 1, 1), date(2024, 1, 2),
                              "UTC", BASIS, statistic_id="00001")
    with pytest.raises(ValueError, match="12:00 UTC"):
        _eval([valid], [valid.window_end_utc + timedelta(seconds=1)], horizons=(24,))
    with pytest.raises(ValueError, match="24/48/72"):
        _eval([valid], [_issue(0)], horizons=(36,))


def test_duplicate_dates_and_missing_calendar_slots_are_not_silently_merged():
    rows = [_row(0, 9), _row(1, 9)]
    issue = rows[0].window_end_utc
    with pytest.raises(ValueError, match="duplicate"):
        _eval([rows[0], rows[0]], [issue], horizons=(24,))
    # An absent slot is expanded as missing truth rather than silently
    # compressing the recurrence or being interpreted as a negative.
    gap = [_row(0, 9), _row(2, 9)]
    result = _eval(gap, [issue], horizons=(24,))[0]
    assert result.label_status == "unknown"
    assert "2024-01-02" in result.missing_or_unusable_future_dates


def test_only_observed_quality_codes_are_accepted_as_truth():
    with pytest.raises(ValueError, match="registered source-quality"):
        replace(_row(0, 9), quality_status="maybe")
    with pytest.raises(ValueError, match="interval mapping"):
        replace(_row(0, 9), interval_mapping_status="guessed")
