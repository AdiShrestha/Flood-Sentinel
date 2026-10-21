"""Constructed mutation and boundary checks for source identities and onset bounds.

These checks test software contracts only; they are not hydrological evidence.
"""
from __future__ import annotations

import csv
from dataclasses import replace
from datetime import datetime, timedelta, timezone
from itertools import product

import pytest

from flood_sentinel.adapters.availability import AvailabilityAdapter, CausalLeakageError
from flood_sentinel.adapters.exposure import ExposureAdapter
from flood_sentinel.dataset import CausalHydroDataset
from flood_sentinel.evidence import HydroRow, label_issue
from flood_sentinel.identifiers import SourceIdentityError, require_identifier, split_source_ids
from flood_sentinel.temporal import OnsetInterval


ISSUE = datetime(2023, 1, 2, 12, tzinfo=timezone.utc)
SITE = "fixture-A"
SAMPLE = "fixture-A_20230102T120000Z"


def record(**changes):
    row = {
        "record_id": "fixture-rec-1", "site_no": SITE, "parameter": "discharge_cms",
        "series_id": "fixture-series-A-q", "provider_record_id": "version-1",
        "provider": "fixture-provider", "origin": "observational", "unit_si": "m3/s",
        "timestamp_utc": "2023-01-02T11:00:00Z", "value_si": "12.5",
        "observation_start_utc": "2023-01-02T11:00:00Z",
        "observation_end_utc": "2023-01-02T11:00:00Z",
        "availability_basis": "observed", "available_utc": "2023-01-02T11:00:00Z",
        "raw_sha256": "a" * 64,
    }
    row.update(changes)
    return row


def write_catalogs(tmp_path, source_rows, *, site=SITE, sample_id=SAMPLE, source_ids=None):
    cohort = tmp_path / "cohort.csv"
    sources = tmp_path / "sources.csv"
    with cohort.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=["sample_id", "site_no", "label", "group_id", "split", "source_ids"])
        writer.writeheader()
        writer.writerow({"sample_id": sample_id, "site_no": site, "label": "0", "group_id": "fixture-group",
                         "split": "train", "source_ids": source_ids or "|".join(r["record_id"] for r in source_rows)})
    with sources.open("w", newline="", encoding="utf-8") as stream:
        fields = list(source_rows[0])
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        writer.writerows(source_rows)
    return cohort, sources


def dataset(tmp_path, rows, **kwargs):
    cohort, sources = write_catalogs(tmp_path, rows)
    return CausalHydroDataset(cohort, sources, split="train", lookback_hours=1,
        series_by_site={SITE: {"discharge_cms": "fixture-series-A-q"}}, **kwargs)


@pytest.mark.parametrize("value", ["", "  ", " id", "id ", 7, None])
def test_empty_nonstring_or_whitespace_identifiers_are_rejected(value):
    with pytest.raises(SourceIdentityError):
        require_identifier(value, field="record_id")


@pytest.mark.parametrize("value", ["", "a||b", " a", "a ", None, 9])
def test_source_id_lists_reject_empty_nonstring_and_whitespace_entries(value):
    with pytest.raises(SourceIdentityError):
        split_source_ids(value)


@pytest.mark.parametrize("event_id", ["", "  ", "bad event", 3, None])
def test_event_catalog_ids_are_strict(event_id):
    with pytest.raises(SourceIdentityError):
        OnsetInterval(event_id, ISSUE, ISSUE + timedelta(hours=1))


def test_source_to_label_rows_and_evidence_ids_are_strict():
    row = HydroRow("record-1", "provider-version-1", "a" * 64, 0, SITE, "series-1", ISSUE,
                   "1.0", "m3/s", 1.0, "Approved", (), None, True, True, None)
    with pytest.raises(SourceIdentityError):
        replace(row, record_id=" ")
    with pytest.raises(SourceIdentityError):
        replace(row, provider_id=None)
    with pytest.raises(SourceIdentityError):
        label_issue(ISSUE, timedelta(hours=1), [], current_below=True,
                    coverage_complete=True, evidence_ids=[""])


def test_cross_site_source_cannot_materialize_for_another_sample(tmp_path):
    row = record(site_no="fixture-B", value_si="999")
    with pytest.raises(SourceIdentityError, match="Cross-site"):
        dataset(tmp_path, [row])


@pytest.mark.parametrize("mutation,match", [
    ({"series_id": "fixture-series-B-q"}, "Series mismatch"),
    ({"unit_si": "ft3/s"}, "Unit mismatch"),
    ({"provider_record_id": ""}, "provider_record_id"),
    ({"observation_start_utc": "2023-01-02T10:45:00Z"}, "point-observation"),
    ({"timestamp_utc": "2023-01-02T11:07:00Z", "observation_start_utc": "2023-01-02T11:07:00Z",
      "observation_end_utc": "2023-01-02T11:07:00Z", "available_utc": "2023-01-02T11:07:00Z"}, "outside sample grid"),
    ({"timestamp_utc": "2023-01-02T12:15:00Z", "observation_start_utc": "2023-01-02T12:15:00Z",
      "observation_end_utc": "2023-01-02T12:15:00Z", "available_utc": "2023-01-02T12:15:00Z"}, "observation timestamp"),
])
def test_identity_interval_unit_and_release_mutations_fail_closed(tmp_path, mutation, match):
    with pytest.raises((SourceIdentityError, CausalLeakageError), match=match):
        dataset(tmp_path, [record(**mutation)])


def test_unresolved_historical_availability_does_not_become_a_release(tmp_path):
    with pytest.raises(CausalLeakageError, match="actual release/vintage"):
        dataset(tmp_path, [record(availability_basis="unknown", available_utc="")])


def test_conflicting_duplicate_catalog_ids_are_rejected(tmp_path):
    first = record()
    second = record(value_si="999")
    with pytest.raises(SourceIdentityError, match="Conflicting duplicate"):
        dataset(tmp_path, [first, second])


def test_multiple_provider_versions_for_one_grid_identity_are_rejected(tmp_path):
    first = record()
    second = record(record_id="fixture-rec-2", provider_record_id="version-2")
    with pytest.raises(SourceIdentityError, match="Unresolved versions"):
        dataset(tmp_path, [first, second])


def test_valid_explicitly_bound_record_reaches_only_its_grid_channel(tmp_path):
    loaded = dataset(tmp_path, [record()])
    sample = loaded[0]
    assert sample.site_no == SITE
    assert sample.source_record_ids == ("fixture-rec-1",)
    assert sample.values.shape == (5, 2)
    assert sample.values[0, 1].item() == pytest.approx(12.5)
    assert sample.observed[0, 1].item() is True
    assert not sample.observed[:, 0].any()


def test_lookup_key_must_equal_record_id():
    row = record()
    cohort = [{"sample_id": SAMPLE, "source_ids": row["record_id"]}]
    with pytest.raises(SourceIdentityError, match="differs from record_id"):
        AvailabilityAdapter.audit_cohort_causality(cohort, {SAMPLE: ISSUE}, {"different-key": row})


def test_availability_flag_is_a_claim_not_historical_authenticity():
    result = AvailabilityAdapter.audit_sample_causality(
        SAMPLE, ISSUE, [record()], lookback_hours=1)
    assert result.is_causally_valid is True
    assert result.availability_evidence_status == "unverified_caller_claim"


def event(event_id, lower_h, upper_h):
    lower = ISSUE + timedelta(hours=lower_h) if lower_h is not None else None
    upper = ISSUE + timedelta(hours=upper_h)
    return {"site_no": SITE, "event_id": event_id,
            "onset_lower_utc": None if lower is None else lower.isoformat(),
            "onset_upper_utc": upper.isoformat()}


def exposure(events, **kwargs):
    return ExposureAdapter.compute_sample_exposure(SAMPLE, SITE, ISSUE, events, horizon_hours=24,
        currently_below_threshold=True, coverage_complete=True, ongoing=False, **kwargs)


def test_overlapping_first_onset_bounds_match_independent_assignment_enumeration():
    # Independent finite enumeration of compatible 0.5-hour onset assignments.
    a = [ISSUE + timedelta(hours=h) for h in (1.5, 2, 2.5, 3, 3.5, 4, 4.5, 5)]
    b = [ISSUE + timedelta(hours=h) for h in (2.5, 3)]
    earliest = [(min(x, y) - ISSUE).total_seconds() / 3600 for x, y in product(a, b)]
    assert min(earliest) == 1.5 and max(earliest) == 3
    out = exposure([event("event-a", 1, 5), event("event-b", 2, 3)])
    assert out.has_flood_event is True  # existential horizon label
    assert (out.lead_time_lower_hours, out.lead_time_upper_hours) == (1, 3)
    assert out.first_onset_event_ids == ("event-a", "event-b")
    assert out.first_onset_status == "bounded_interval_uncertainty"


def test_multiple_separated_episodes_keep_first_episode_as_lead():
    out = exposure([event("first", 1, 2), event("later", 5, 7)])
    assert out.has_flood_event is True
    assert (out.lead_time_lower_hours, out.lead_time_upper_hours) == (1, 2)
    assert out.first_onset_event_ids == ("first",)


def test_sample_site_and_issue_are_bound_to_exposure():
    with pytest.raises(ValueError, match="site differs"):
        ExposureAdapter.compute_sample_exposure(SAMPLE, "fixture-B", ISSUE, [])
    with pytest.raises(ValueError, match="issue time differs"):
        ExposureAdapter.compute_sample_exposure(SAMPLE, SITE, ISSUE + timedelta(minutes=1), [])


def test_existential_label_can_be_positive_while_first_lead_is_unknown():
    out = exposure([event("straddles-issue", -1, 0.5), event("definite", 1, 2)])
    assert out.has_flood_event is True
    assert out.lead_time_lower_hours is None and out.lead_time_upper_hours is None
    assert out.first_onset_status == "unknown_interval_may_precede_issue"


def test_issue_horizon_boundary_and_censoring_cases_remain_distinct():
    exact_issue = {"site_no": SITE, "event_id": "at-issue",
                   "onset_lower_utc": ISSUE.isoformat(), "onset_upper_utc": ISSUE.isoformat()}
    out = ExposureAdapter.compute_sample_exposure(SAMPLE, SITE, ISSUE, [exact_issue], 24,
        currently_below_threshold=True, coverage_complete=True, ongoing=False)
    assert out.has_flood_event is False

    exact_horizon = exposure([event("at-horizon", 23, 24)])
    assert exact_horizon.has_flood_event is True
    ambiguous = exposure([event("straddles-horizon", 23, 25)])
    assert ambiguous.has_flood_event is None
    assert ambiguous.label_reason == "onset_boundary_ambiguous"

    incomplete = ExposureAdapter.compute_sample_exposure(SAMPLE, SITE, ISSUE, [], 24,
        currently_below_threshold=True, coverage_complete=False, ongoing=False)
    censored = ExposureAdapter.compute_sample_exposure(SAMPLE, SITE, ISSUE, [], 24,
        currently_below_threshold=True, coverage_complete=True, ongoing=True)
    assert incomplete.has_flood_event is None and censored.has_flood_event is None

    left_censored = ExposureAdapter.compute_sample_exposure(
        SAMPLE, SITE, ISSUE, [event("left-censored", None, 2)], 24,
        currently_below_threshold=True, coverage_complete=True, ongoing=False)
    assert left_censored.has_flood_event is None
    assert left_censored.lead_time_lower_hours is None and left_censored.lead_time_upper_hours is None
