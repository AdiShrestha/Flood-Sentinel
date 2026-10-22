"""Public raw-page replay for daily aggregate quality-support diagnostics.

This module consumes caller-supplied, hash-checked USGS daily response pages.
It does not fetch data, infer historical releases, or claim physical flood
onsets. Its evaluator is the separately tested aggregate completion primitive.
"""
from __future__ import annotations

import hashlib
import json
import platform
import re
from bisect import bisect_right
from collections import Counter, defaultdict
from dataclasses import asdict
from datetime import date, datetime, time, timedelta, timezone
from decimal import Decimal
from fractions import Fraction
from pathlib import Path
from statistics import median
from typing import Any
from urllib.parse import parse_qs, urljoin, urlsplit
from zoneinfo import ZoneInfo

from .aggregate_completion import (
    DailyCalendarContract,
    DailyMean,
    evaluate_issue_labels,
    map_local_day_window,
    previous_closed_day_persistence,
    reference_type8_threshold,
)


UTC = timezone.utc
DATE_RE = re.compile(r"\d{4}-\d{2}-\d{2}\Z")
CELLS = (
    ("ref_estimated_eval_estimated", "estimated_retaining", True),
    ("ref_estimated_eval_unflagged", "estimated_retaining", False),
    ("ref_unflagged_eval_estimated", "unflagged_only", True),
    ("ref_unflagged_eval_unflagged", "unflagged_only", False),
)
HORIZONS = (24, 48, 72)


def sha256_bytes(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _unique_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"duplicate JSON key: {key!r}")
        result[key] = value
    return result


def _strict_json(raw: bytes, context: str) -> Any:
    try:
        return json.loads(
            raw.decode("utf-8"),
            object_pairs_hook=_unique_object,
            parse_constant=lambda value: (_ for _ in ()).throw(ValueError(value)),
        )
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError(f"invalid UTF-8 JSON in {context}: {exc}") from exc


def read_manifest(path: Path) -> dict[str, Any]:
    obj = _strict_json(path.read_bytes(), str(path))
    validate_manifest(obj)
    return obj


def _nonempty_string(value: Any, field: str) -> str:
    if type(value) is not str or not value.strip():
        raise ValueError(f"{field} must be a nonempty string")
    return value


def _date(value: Any, field: str) -> date:
    if type(value) is not str or not DATE_RE.fullmatch(value):
        raise ValueError(f"{field} must be an ISO date string")
    try:
        return date.fromisoformat(value)
    except ValueError as exc:
        raise ValueError(f"{field} is not a valid date") from exc


def validate_manifest(manifest: dict[str, Any]) -> None:
    if not isinstance(manifest, dict) or manifest.get("manifest_version") != "flood-sentinel-daily-quality-capture-v1":
        raise ValueError("unsupported daily-quality source manifest")
    raw = manifest.get("raw_capture")
    pages = raw.get("pages") if isinstance(raw, dict) else None
    if not isinstance(pages, list) or not pages:
        raise ValueError("manifest must declare captured raw pages")
    sites = manifest.get("selection", {}).get("sites")
    if not isinstance(sites, list) or not sites:
        raise ValueError("manifest must declare selected series identities")
    site_map: dict[str, dict[str, Any]] = {}
    series_seen: set[str] = set()
    for entry in sites:
        site = _nonempty_string(entry.get("site_id"), "site_id")
        series = _nonempty_string(entry.get("series_id"), "series_id")
        if site in site_map:
            raise ValueError(f"conflicting duplicate catalog site ID: {site}")
        if series in series_seen:
            raise ValueError(f"duplicate series identity in catalog: {series}")
        expected = (entry.get("parameter_code"), entry.get("statistic_id"), entry.get("unit"),
                    entry.get("computation_period"), entry.get("computation"), entry.get("primary"))
        if expected != ("00060", "00003", "ft^3/s", "Daily", "Mean", "Primary"):
            raise ValueError(f"unsupported or conflicting selected series identity for {site}")
        site_map[site] = entry
        series_seen.add(series)
    expected_dates = manifest.get("date_scope", {})
    raw_start = _date(expected_dates.get("raw_query_inclusive", [None, None])[0], "raw start")
    raw_last = _date(expected_dates.get("raw_query_inclusive", [None, None])[1], "raw end")
    mat = expected_dates.get("materialized_calendar_half_open")
    ref = expected_dates.get("reference_half_open")
    issue_range = expected_dates.get("evaluation_issue_dates_inclusive")
    if not all(isinstance(x, list) and len(x) == 2 for x in (mat, ref, issue_range)):
        raise ValueError("manifest date windows must each have two endpoints")
    if raw_start > raw_last:
        raise ValueError("raw query date range is reversed")
    calendar_start, calendar_end = _date(mat[0], "calendar start"), _date(mat[1], "calendar end")
    ref_start, ref_end = _date(ref[0], "reference start"), _date(ref[1], "reference end")
    eval_start, eval_last = _date(issue_range[0], "evaluation issue start"), _date(issue_range[1], "evaluation issue end")
    if calendar_start != raw_start or calendar_end != raw_last + timedelta(days=1):
        raise ValueError("materialized calendar must exactly cover the raw query's inclusive dates")
    if not (calendar_start <= ref_start < ref_end <= calendar_end):
        raise ValueError("reference range must be a nonempty half-open interval")
    if not (calendar_start <= eval_start <= eval_last < calendar_end and eval_last <= raw_last):
        raise ValueError("evaluation issue dates must be ordered and covered by the captured calendar")
    if ref_end > eval_start:
        raise ValueError("reference window overlaps evaluation issue dates")
    if tuple(expected_dates.get("horizons_elapsed_hours", [])) != HORIZONS:
        raise ValueError("the declared 24/48/72-hour horizons are required")
    expected_cells = {
        (name, reference, "estimated_retaining" if evaluation else "unflagged_only")
        for name, reference, evaluation in CELLS
    }
    observed_cells = set()
    for cell in manifest.get("matrix_cells", []):
        observed_cells.add((cell.get("cell_id"), cell.get("reference_quality"), cell.get("evaluation_quality")))
    if observed_cells != expected_cells:
        raise ValueError("matrix cell identities or reference/evaluation separation are incomplete")
    if len(pages) != len({p.get("sequence") for p in pages}):
        raise ValueError("duplicate capture page sequence")
    page_by_site: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for page in sorted(pages, key=lambda item: item.get("sequence", -1)):
        seq = page.get("sequence")
        if type(seq) is not int or seq < 1:
            raise ValueError("capture sequence must be a positive integer")
        site = _nonempty_string(page.get("site_id"), "page site_id")
        identity = site_map.get(site)
        if identity is None:
            raise ValueError(f"capture page names an unselected site: {site}")
        if (page.get("series_id"), page.get("parameter_code"), page.get("statistic_id"), page.get("unit")) != (
                identity["series_id"], "00060", "00003", "ft^3/s"):
            raise ValueError(f"capture page identity conflicts with selected site: {site}")
        raw_file = _nonempty_string(page.get("raw_file"), "raw_file")
        if Path(raw_file).name != raw_file or raw_file in (".", ".."):
            raise ValueError("raw_file must be a basename inside the caller-provided directory")
        digest = page.get("raw_sha256")
        if type(digest) is not str or not re.fullmatch(r"[0-9a-f]{64}", digest):
            raise ValueError("raw page SHA-256 assertion must be 64 lowercase hex characters")
        if type(page.get("raw_bytes")) is not int or page["raw_bytes"] <= 0:
            raise ValueError("raw page byte count must be positive")
        for key in ("request_url", "response_url"):
            url = _nonempty_string(page.get(key), key)
            parts = urlsplit(url)
            if parts.scheme != "https" or parts.netloc != "api.waterdata.usgs.gov" or parts.path != "/ogcapi/v1/collections/daily/items":
                raise ValueError(f"{key} is not the selected official USGS daily endpoint")
            query = parse_qs(parts.query, keep_blank_values=True)
            expected_query = {
                "time_series_id": identity["series_id"],
                "monitoring_location_id": site,
                "parameter_code": "00060", "statistic_id": "00003",
                "datetime": f"{raw_start.isoformat()}/{raw_last.isoformat()}", "f": "json",
            }
            for qkey, qvalue in expected_query.items():
                if query.get(qkey) != [qvalue]:
                    raise ValueError(f"{key} query does not bind {qkey} for {site}")
        if page.get("http_status") != 200:
            raise ValueError(f"non-200 captured response for {site}")
        if page.get("row_schema", {}).get("value_verbatim") != "properties.value" or page.get("row_schema", {}).get("qualifier_verbatim") != "properties.qualifier":
            raise ValueError("manifest must bind verbatim provider value and qualifier fields")
        page_by_site[site].append(page)
    if set(page_by_site) != set(site_map):
        raise ValueError("each selected site must have captured pages")
    for site, site_pages in page_by_site.items():
        site_pages.sort(key=lambda item: item["sequence"])
        for left, right in zip(site_pages, site_pages[1:]):
            if left["sequence"] >= right["sequence"]:
                raise ValueError(f"page order is not increasing for {site}")
    time_contract = manifest.get("civil_time_assumption", {})
    if time_contract.get("zone") != "America/New_York" or not _nonempty_string(time_contract.get("basis"), "civil-time basis"):
        raise ValueError("daily interval mapping must retain the explicit conditional zone assumption")


def _quality(props: dict[str, Any]) -> str:
    approval = props.get("approval_status")
    approved = approval == "Approved" or approval == ["Approved"]
    qualifier = props.get("qualifier")
    if qualifier is None or qualifier == "" or qualifier == []:
        qualifiers: list[str] = []
        shape_ok = True
    elif isinstance(qualifier, str):
        qualifiers = [part.strip() for part in qualifier.split(",") if part.strip()]
        shape_ok = True
    elif isinstance(qualifier, list) and all(isinstance(item, str) for item in qualifier):
        qualifiers = list(qualifier)
        shape_ok = True
    else:
        qualifiers = []
        shape_ok = False
    if not approved or not shape_ok:
        return "unusable_quality"
    if not qualifiers:
        return "approved_unflagged"
    if qualifiers == ["ESTIMATED"]:
        return "estimated_flagged"
    return "unusable_quality"


def _value(raw: Any) -> tuple[Decimal | None, str | None]:
    if raw is None:
        return None, "missing_value"
    if type(raw) is not str:
        return None, "unusable_quality"
    try:
        parsed = Decimal(raw)
    except Exception:
        return None, "unusable_quality"
    if not parsed.is_finite() or parsed < 0:
        return None, "unusable_quality"
    return parsed, None


def parse_capture(manifest: dict[str, Any], raw_dir: Path) -> tuple[dict[str, dict[date, DailyMean]], list[dict[str, Any]], dict[str, Any]]:
    """Verify and decode every listed page, retaining verbatim source identity."""
    validate_manifest(manifest)
    raw_start, raw_last = [date.fromisoformat(x) for x in manifest["date_scope"]["raw_query_inclusive"]]
    end_exclusive = raw_last + timedelta(days=1)
    zone_name = manifest["civil_time_assumption"]["zone"]
    basis = manifest["civil_time_assumption"]["basis"]
    site_meta = {item["site_id"]: item for item in manifest["selection"]["sites"]}
    rows_by_site_date: dict[str, dict[date, DailyMean]] = {site: {} for site in site_meta}
    source_rows: list[dict[str, Any]] = []
    record_ids: set[str] = set()
    seen_page_names: set[str] = set()
    page_audit: list[dict[str, Any]] = []
    pages_by_site: dict[str, list[dict[str, Any]]] = defaultdict(list)

    for page in sorted(manifest["raw_capture"]["pages"], key=lambda item: item["sequence"]):
        name = page["raw_file"]
        if name in seen_page_names:
            raise ValueError(f"same raw page referenced twice: {name}")
        seen_page_names.add(name)
        path = raw_dir / name
        if not path.is_file():
            raise ValueError(f"missing caller-supplied raw page: {path}")
        raw = path.read_bytes()
        if len(raw) != page["raw_bytes"] or sha256_bytes(raw) != page["raw_sha256"]:
            raise ValueError(f"raw page size/hash mismatch: {name}")
        body = _strict_json(raw, name)
        features = body.get("features") if isinstance(body, dict) else None
        if body.get("type") != "FeatureCollection" or not isinstance(features, list):
            raise ValueError(f"not an OGC FeatureCollection: {name}")
        if body.get("numberReturned") != len(features):
            raise ValueError(f"numberReturned disagrees with features in {name}")
        site = page["site_id"]
        identity = site_meta[site]
        response_url = urlsplit(page["response_url"])
        query = parse_qs(response_url.query, keep_blank_values=True)
        raw_start_text, raw_last_text = manifest["date_scope"]["raw_query_inclusive"]
        expected_query = {
            "time_series_id": identity["series_id"], "monitoring_location_id": site,
            "parameter_code": "00060", "statistic_id": "00003",
            "datetime": f"{raw_start_text}/{raw_last_text}", "f": "json",
        }
        for key, value in expected_query.items():
            if query.get(key) != [value]:
                raise ValueError(f"captured response URL identity mismatch for {site}/{key}")
        for feature in features:
            if not isinstance(feature, dict):
                raise ValueError(f"non-object feature in {name}")
            props = feature.get("properties")
            if not isinstance(props, dict):
                raise ValueError(f"feature properties missing in {name}")
            rid = feature.get("id")
            if type(rid) is not str or not rid.strip():
                raise ValueError("provider record ID must be a nonempty string")
            if rid in record_ids:
                raise ValueError(f"duplicate raw provider record ID: {rid}")
            record_ids.add(rid)
            exact_identity = (
                props.get("monitoring_location_id"), props.get("time_series_id"),
                props.get("parameter_code"), props.get("statistic_id"), props.get("unit_of_measure"),
            )
            if exact_identity != (site, identity["series_id"], "00060", "00003", "ft^3/s"):
                raise ValueError(f"raw feature has conflicting site/series/parameter/statistic/unit: {rid}")
            day_text = props.get("time")
            day = _date(day_text, "provider time")
            if not raw_start <= day < end_exclusive:
                raise ValueError(f"provider date outside manifest extent: {day}")
            if day in rows_by_site_date[site]:
                raise ValueError(f"conflicting duplicate catalog/site-date row: {site}/{day}")
            value, value_problem = _value(props.get("value"))
            quality = _quality(props)
            if value_problem is not None:
                quality = value_problem
            start, end = map_local_day_window(day, ZoneInfo(zone_name), basis=basis)
            usable = quality in ("approved_unflagged", "estimated_flagged")
            material = DailyMean(
                site_id=site, local_date=day, window_start_utc=start, window_end_utc=end,
                value=value, quality_status=quality,
                provider_record_id=rid if usable else None,
                series_id=identity["series_id"], parameter_code="00060", statistic_id="00003",
                unit="ft^3/s", window_basis=basis,
            )
            rows_by_site_date[site][day] = material
            source_rows.append({
                "site_id": site, "series_id": identity["series_id"], "parameter_code": "00060",
                "statistic_id": "00003", "unit": "ft^3/s", "date": day.isoformat(),
                "provider_record_id": rid, "value_verbatim": props.get("value"),
                "approval_status_verbatim": props.get("approval_status"),
                "qualifier_verbatim": props.get("qualifier"),
                "last_modified_verbatim": props.get("last_modified"),
                "derived_quality_state": quality, "raw_page_sha256": page["raw_sha256"],
            })
        links = body.get("links", [])
        if not isinstance(links, list):
            raise ValueError(f"links is not an array in {name}")
        next_links = [link for link in links if isinstance(link, dict) and link.get("rel") == "next"]
        if len(next_links) > 1:
            raise ValueError(f"multiple next links in {name}")
        pages_by_site[site].append(page)
        page_audit.append({
            "sequence": page["sequence"], "site_id": site, "series_id": identity["series_id"],
            "request_url": page["request_url"], "response_url": page["response_url"],
            "http_status": page["http_status"], "raw_file": name,
            "raw_sha256": page["raw_sha256"], "raw_bytes": len(raw),
            "rows": len(features), "numberMatched_present": "numberMatched" in body,
            "next_link_present": bool(next_links),
        })
        page["_observed_next_url"] = (urljoin(page["response_url"], next_links[0].get("href", ""))
                                        if next_links else None)
    for site, pages in pages_by_site.items():
        pages.sort(key=lambda item: item["sequence"])
        for index, page in enumerate(pages):
            expected_next = pages[index + 1]["request_url"] if index + 1 < len(pages) else None
            if page.get("_observed_next_url") != expected_next:
                raise ValueError(f"captured pagination chain is incomplete or changed for {site} page {page['sequence']}")

    materialized: dict[str, dict[date, DailyMean]] = {}
    for site, identity in site_meta.items():
        current = dict(rows_by_site_date[site])
        day = raw_start
        while day < end_exclusive:
            if day not in current:
                start, end = map_local_day_window(day, ZoneInfo(zone_name), basis=basis)
                current[day] = DailyMean(
                    site_id=site, local_date=day, window_start_utc=start, window_end_utc=end,
                    value=None, quality_status="missing_date", provider_record_id=None,
                    series_id=identity["series_id"], parameter_code="00060", statistic_id="00003",
                    unit="ft^3/s", window_basis=basis,
                )
            day += timedelta(days=1)
        materialized[site] = current
    return materialized, source_rows, {"pages": page_audit, "raw_rows": len(source_rows), "unique_record_ids": len(record_ids)}


def _jsonable(value: Any) -> Any:
    if isinstance(value, datetime):
        return value.astimezone(UTC).isoformat().replace("+00:00", "Z")
    if isinstance(value, date):
        return value.isoformat()
    if isinstance(value, Decimal):
        return str(value)
    if isinstance(value, Fraction):
        return f"{value.numerator}/{value.denominator}"
    if isinstance(value, dict):
        return {str(key): _jsonable(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_jsonable(item) for item in value]
    return value


def _quarter(month: int) -> str:
    if month in (12, 1, 2):
        return "DJF"
    if month in (3, 4, 5):
        return "MAM"
    if month in (6, 7, 8):
        return "JJA"
    return "SON"


def _issue_times(manifest: dict[str, Any]) -> tuple[datetime, ...]:
    first, last = [date.fromisoformat(x) for x in manifest["date_scope"]["evaluation_issue_dates_inclusive"]]
    issues = []
    day = first
    while day <= last:
        issues.append(datetime.combine(day, time(12), tzinfo=UTC))
        day += timedelta(days=1)
    return tuple(issues)


def _last_unbounded_from_index(candidates: list[DailyMean], candidate_ends: list[datetime],
                              issue: datetime) -> dict[str, Any]:
    """Fast equivalent of the retained unbounded-age diagnostic lookup."""
    index = bisect_right(candidate_ends, issue) - 1
    if index < 0:
        return {"score": None, "source_record_id": None, "source_local_date": None,
                "observation_end_utc": None, "age_hours": None,
                "actual_release_status": "unknown",
                "input_admissibility": "assumed_final_product_retrospective_replay"}
    row = candidates[index]
    assert row.value is not None and row.window_end_utc is not None
    delta = issue - row.window_end_utc
    micros = (delta.days * 86_400 + delta.seconds) * 1_000_000 + delta.microseconds
    age = Decimal(micros) / Decimal(3_600_000_000)
    return {"score": str(row.value), "source_record_id": row.provider_record_id,
            "source_local_date": row.local_date.isoformat(),
            "observation_end_utc": row.window_end_utc.isoformat().replace("+00:00", "Z"),
            "age_hours": str(age), "actual_release_status": "unknown",
            "input_admissibility": "assumed_final_product_retrospective_replay"}


def _threshold_support(rows: list[DailyMean], threshold: Fraction, ref_start: date,
                       ref_end: date, policy: str) -> dict[str, Any]:
    refs = [row for row in rows if ref_start <= row.local_date < ref_end]
    if policy == "estimated_retaining":
        usable = [row for row in refs if row.truth_usable_primary]
    elif policy == "unflagged_only":
        usable = [row for row in refs if row.truth_usable_unflagged]
    else:
        raise ValueError(f"unsupported reference-quality policy: {policy}")
    return {
        "reference_window_half_open": [ref_start.isoformat(), ref_end.isoformat()],
        "reference_quality_policy": policy,
        "n_usable": len(usable),
        "n_unflagged": sum(row.quality_status == "approved_unflagged" for row in refs),
        "n_estimated_flagged": sum(row.quality_status == "estimated_flagged" for row in refs),
        "n_missing_or_otherwise_unusable": len(refs) - len(usable),
        "usable_dates_by_reference_year": {
            str(year): sum(row.local_date.year == year for row in usable)
            for year in range(ref_start.year, (ref_end - timedelta(days=1)).year + 1)
        },
        "all_20_reference_years_have_support": (
            (ref_end.year - ref_start.year) == 20
            and all(sum(row.local_date.year == year for row in usable) > 0
                    for year in range(ref_start.year, ref_end.year))
        ),
        "q99_exact_fraction": f"{threshold.numerator}/{threshold.denominator}",
        "q99_decimal_display": str(Decimal(threshold.numerator) / Decimal(threshold.denominator)),
        "strict_comparison": ">",
        "evaluation_rows_used_for_threshold": 0,
    }


def _transition(left_rows: list[dict[str, Any]], right_rows: list[dict[str, Any]],
                left_id: str, right_id: str, contrast: str) -> dict[str, Any]:
    left = {(row["site_id"], row["issue_time_utc"], row["horizon_hours"]): row for row in left_rows}
    right = {(row["site_id"], row["issue_time_utc"], row["horizon_hours"]): row for row in right_rows}
    if left.keys() != right.keys():
        raise ValueError(f"matrix key mismatch: {left_id} vs {right_id}")
    statuses = ("positive", "negative", "unknown")
    status = Counter((left[key]["label_status"], right[key]["label_status"]) for key in left)
    eligibility = Counter((left[key]["eligible"], right[key]["eligible"]) for key in left)
    states = Counter((left[key]["issue_state"], right[key]["issue_state"]) for key in left)
    common = [key for key in left if left[key]["label_status"] != "unknown" and right[key]["label_status"] != "unknown"]
    common_status = Counter((left[key]["label_status"], right[key]["label_status"]) for key in common)
    ev_left = {rid for row in left.values() for rid in row["target_record_ids"]}
    ev_right = {rid for row in right.values() for rid in row["target_record_ids"]}
    by_site_horizon = {}
    for site in sorted({key[0] for key in left}):
        for horizon in HORIZONS:
            keys = [key for key in left if key[0] == site and key[2] == horizon]
            subcommon = [key for key in keys if left[key]["label_status"] != "unknown" and right[key]["label_status"] != "unknown"]
            left_ids = {rid for key in keys for rid in left[key]["target_record_ids"]}
            right_ids = {rid for key in keys for rid in right[key]["target_record_ids"]}
            by_site_horizon[f"{site}|{horizon}"] = {
                "full_panel_issue_keys": len(keys),
                "status_transitions": {f"{a}->{b}": sum(left[key]["label_status"] == a and right[key]["label_status"] == b for key in keys) for a in statuses for b in statuses},
                "eligibility_transitions": {f"{a}->{b}": sum(left[key]["eligible"] is a and right[key]["eligible"] is b for key in keys) for a in (False, True) for b in (False, True)},
                "issue_state_transitions": {f"{a}->{b}": n for (a, b), n in Counter((left[key]["issue_state"], right[key]["issue_state"]) for key in keys).items()},
                "common_known_issue_keys": len(subcommon),
                "common_known_status_transitions": {f"{a}->{b}": sum(left[key]["label_status"] == a and right[key]["label_status"] == b for key in subcommon) for a in ("positive", "negative") for b in ("positive", "negative")},
                "positive_completion_record_ids_left": sorted(left_ids),
                "positive_completion_record_ids_right": sorted(right_ids),
                "completion_record_id_intersection": sorted(left_ids & right_ids),
                "completion_record_id_left_only": sorted(left_ids - right_ids),
                "completion_record_id_right_only": sorted(right_ids - left_ids),
            }
    return {
        "left_cell": left_id, "right_cell": right_id, "contrast": contrast,
        "panel_issue_horizon_keys": len(left),
        "status_transitions": {f"{a}->{b}": status[(a, b)] for a in statuses for b in statuses},
        "eligibility_transitions": {f"{a}->{b}": eligibility[(a, b)] for a in (False, True) for b in (False, True)},
        "issue_state_transitions": {f"{a}->{b}": n for (a, b), n in states.items()},
        "common_known_issue_horizon_keys": len(common),
        "common_known_status_transitions": {f"{a}->{b}": common_status[(a, b)] for a in ("positive", "negative") for b in ("positive", "negative")},
        "positive_completion_record_ids_left": sorted(ev_left),
        "positive_completion_record_ids_right": sorted(ev_right),
        "completion_record_id_intersection": sorted(ev_left & ev_right),
        "completion_record_id_left_only": sorted(ev_left - ev_right),
        "completion_record_id_right_only": sorted(ev_right - ev_left),
        "by_site_horizon": by_site_horizon,
    }


def derive_replay(manifest: dict[str, Any], raw_dir: Path) -> dict[str, Any]:
    """Compute all cells/support from source pages and the declared calendar."""
    source_by_site_date, source_rows, capture_audit = parse_capture(manifest, raw_dir)
    date_scope = manifest["date_scope"]
    calendar_start, calendar_end = [date.fromisoformat(x) for x in date_scope["materialized_calendar_half_open"]]
    ref_start, ref_end = [date.fromisoformat(x) for x in date_scope["reference_half_open"]]
    eval_start, eval_last = [date.fromisoformat(x) for x in date_scope["evaluation_issue_dates_inclusive"]]
    zone = manifest["civil_time_assumption"]["zone"]
    basis = manifest["civil_time_assumption"]["basis"]
    calendars: dict[str, DailyCalendarContract] = {}
    site_rows: dict[str, tuple[DailyMean, ...]] = {}
    for site, identity in ((item["site_id"], item) for item in manifest["selection"]["sites"]):
        calendar = DailyCalendarContract(
            site_id=site, series_id=identity["series_id"], start_date=calendar_start,
            end_date_exclusive=calendar_end, zone_name=zone, window_basis=basis,
        )
        calendars[site] = calendar
        site_rows[site] = tuple(source_by_site_date[site][calendar_start + timedelta(days=i)]
                                 for i in range((calendar_end - calendar_start).days))
    issues = _issue_times(manifest)
    # Build the source-derived issue ledger before labels so every cell is
    # crossed with the same fixed input policy and all unavailable reasons.
    input_ledger = []
    for site, by_date in source_by_site_date.items():
        rows = site_rows[site]
        old_candidates = [row for row in rows if row.input_usable
                          and row.interval_mapping_status == "mapped_assumption"
                          and row.window_end_utc is not None]
        old_ends = [row.window_end_utc for row in old_candidates]
        for issue in issues:
            strict = previous_closed_day_persistence(by_date, issue, calendars[site])
            old = _last_unbounded_from_index(old_candidates, old_ends, issue)
            input_ledger.append({
                "site_id": site, "issue_time_utc": issue.isoformat().replace("+00:00", "Z"),
                "new_policy": strict["policy"], "new_previous_closed_day_score": strict["score"],
                "new_previous_closed_day_record_id": strict["source_record_id"],
                "new_previous_closed_day_date": strict["source_local_date"],
                "new_previous_closed_day_end_utc": strict["observation_end_utc"],
                "new_previous_closed_day_age_hours": strict["age_hours"],
                "new_previous_closed_day_status": strict["status"],
                "new_release_status": strict["actual_release_status"],
                "new_input_admissibility": strict["input_admissibility"],
                "old_diagnostic_policy": "legacy_last_admissible_persistence_unbounded-age",
                "old_unbounded_score": old["score"], "old_unbounded_record_id": old["source_record_id"],
                "old_unbounded_date": old["source_local_date"], "old_unbounded_end_utc": old["observation_end_utc"],
                "old_unbounded_age_hours": old["age_hours"], "old_release_status": old["actual_release_status"],
            })
    input_by_key = {(row["site_id"], row["issue_time_utc"]): row for row in input_ledger}
    if len(input_by_key) != len(input_ledger):
        raise ValueError("duplicate derived site/issue input key")
    thresholds: dict[str, dict[str, Fraction]] = {}
    threshold_support: dict[str, dict[str, Any]] = {}
    for site, rows in site_rows.items():
        thresholds[site], threshold_support[site] = {}, {}
        for policy, include_estimated in (("estimated_retaining", True), ("unflagged_only", False)):
            q = reference_type8_threshold(rows, ref_start, ref_end, include_estimated=include_estimated)
            thresholds[site][policy] = q
            threshold_support[site][policy] = _threshold_support(rows, q, ref_start, ref_end, policy)

    matrix: list[dict[str, Any]] = []
    by_cell: dict[str, list[dict[str, Any]]] = {}
    cell_support: dict[str, Any] = {}
    for cell_id, ref_policy, eval_estimated in CELLS:
        cell_rows: list[dict[str, Any]] = []
        support_by_site_horizon: dict[str, Any] = {}
        event_inputs: dict[str, set[bool]] = defaultdict(set)
        event_ids: set[str] = set()
        for site, rows in site_rows.items():
            labels = evaluate_issue_labels(
                rows, thresholds[site][ref_policy], issues,
                calendar=calendars[site], horizons_hours=HORIZONS,
                include_estimated=eval_estimated,
            )
            for label in labels:
                item = _jsonable(asdict(label))
                item["cell_id"] = cell_id
                item["reference_quality_policy"] = ref_policy
                item["evaluation_truth_quality_policy"] = "estimated_retaining" if eval_estimated else "unflagged_only"
                item["issue_season"] = _quarter(datetime.fromisoformat(item["issue_time_utc"].replace("Z", "+00:00")).month)
                cell_rows.append(item)
                input_row = input_by_key[(site, item["issue_time_utc"])]
                has_input = input_row["new_previous_closed_day_score"] is not None
                for record_id in item["target_record_ids"]:
                    event_ids.add(record_id)
                    event_inputs[record_id].add(has_input)
            for horizon in HORIZONS:
                subset = [row for row in cell_rows if row["site_id"] == site and row["horizon_hours"] == horizon]
                counts = Counter(row["label_status"] for row in subset)
                states = Counter(row["issue_state"] for row in subset)
                reasons = Counter(row["reason"] for row in subset)
                target_ids = sorted({rid for row in subset for rid in row["target_record_ids"]})
                support_by_site_horizon[f"{site}|{horizon}"] = {
                    "full_panel_issue_horizon_keys": len(subset),
                    "eligible_issue_keys": sum(row["eligible"] for row in subset),
                    "known_target_keys": counts["positive"] + counts["negative"],
                    "unknown_target_keys": counts["unknown"],
                    "positive_target_keys": counts["positive"],
                    "negative_target_keys": counts["negative"],
                    "eligible_known_target_keys": sum(row["eligible"] and row["label_status"] in ("positive", "negative") for row in subset),
                    "status_counts": {name: counts[name] for name in ("positive", "negative", "unknown")},
                    "issue_state_counts": dict(sorted(states.items())),
                    "reason_counts": dict(sorted(reasons.items())),
                    "unique_positive_target_completion_record_ids": target_ids,
                    "unique_positive_target_completion_record_count": len(target_ids),
                }
        by_cell[cell_id] = cell_rows
        matrix.extend(cell_rows)
        cell_support[cell_id] = {
            "reference_quality_policy": ref_policy,
            "evaluation_truth_quality_policy": "estimated_retaining" if eval_estimated else "unflagged_only",
            "diagonal_source_lane": ("primary_including_estimated" if cell_id == CELLS[0][0] else "unflagged_sensitivity" if cell_id == CELLS[3][0] else None),
            "site_horizon_support": support_by_site_horizon,
            "unique_evaluation_trace_completion_record_ids_that_appear_as_targets": sorted(event_ids),
            "unique_evaluation_trace_completion_count_that_appear_as_targets": len(event_ids),
            "completion_ids_with_any_positive_issue_having_strict_input": sorted(record_id for record_id, flags in event_inputs.items() if True in flags),
            "completion_ids_with_any_positive_issue_lacking_strict_input": sorted(record_id for record_id, flags in event_inputs.items() if False in flags),
            "completion_ids_seen_with_both_input_states": sorted(record_id for record_id, flags in event_inputs.items() if len(flags) == 2),
            "completion_ids_without_any_positive_issue_in_input_ledger": sorted(event_ids - set(event_inputs)),
        }

    pair_rows = []
    for i in range(len(CELLS)):
        for j in range(i + 1, len(CELLS)):
            left_id, left_ref, left_eval = CELLS[i]
            right_id, right_ref, right_eval = CELLS[j]
            if left_ref == right_ref:
                contrast = "evaluation_truth_quality_change_with_fixed_reference_threshold"
            elif left_eval == right_eval:
                contrast = "reference_threshold_change_with_fixed_evaluation_truth_quality"
            else:
                contrast = "joint_reference_and_evaluation_quality_change"
            pair_rows.append(_transition(by_cell[left_id], by_cell[right_id], left_id, right_id, contrast))

    input_no_score: dict[str, Any] = {}
    input_age: dict[str, Any] = {}
    for site in sorted(source_by_site_date):
        rows_for_site = [row for row in input_ledger if row["site_id"] == site]
        input_no_score[site] = dict(sorted(Counter(
            row["new_previous_closed_day_status"] for row in rows_for_site
            if row["new_previous_closed_day_score"] is None).items()))
        strict_ages = [Decimal(row["new_previous_closed_day_age_hours"]) for row in rows_for_site if row["new_previous_closed_day_age_hours"] is not None]
        old_ages = [Decimal(row["old_unbounded_age_hours"]) for row in rows_for_site if row["old_unbounded_age_hours"] is not None]
        input_age[site] = {
            "strict_previous_closed_day": {"n": len(strict_ages), "min_hours": str(min(strict_ages)) if strict_ages else None,
                "median_hours": str(median(strict_ages)) if strict_ages else None, "max_hours": str(max(strict_ages)) if strict_ages else None},
            "legacy_unbounded_age_diagnostic_only": {"n": len(old_ages), "min_hours": str(min(old_ages)) if old_ages else None,
                "median_hours": str(median(old_ages)) if old_ages else None, "max_hours": str(max(old_ages)) if old_ages else None},
        }
    source_date_by_id = {row["provider_record_id"]: date.fromisoformat(row["date"]) for row in source_rows}
    input_by_key = {(row["site_id"], row["issue_time_utc"]): row for row in input_ledger}
    cross = Counter()
    target_cross = Counter()
    for cell_id, rows in by_cell.items():
        for row in rows:
            issue = datetime.fromisoformat(row["issue_time_utc"].replace("Z", "+00:00"))
            inp = input_by_key[(row["site_id"], row["issue_time_utc"])]
            available = inp["new_previous_closed_day_score"] is not None
            reason = "scored" if available else inp["new_previous_closed_day_status"]
            cross[(cell_id, row["site_id"], issue.year, row["issue_season"], row["horizon_hours"], row["label_status"], available, reason)] += 1
            for record_id in row["target_record_ids"]:
                target_day = source_date_by_id[record_id]
                target_cross[(cell_id, row["site_id"], issue.year, row["issue_season"], _quarter(target_day.month), row["horizon_hours"], available, reason, record_id)] += 1
    issue_cross = []
    for key, count in sorted(cross.items()):
        cell_id, site, year, issue_season, horizon, status, available, reason = key
        issue_cross.append({"cell_id": cell_id, "site_id": site, "issue_year": year,
            "issue_season": issue_season, "horizon_hours": horizon, "label_status": status,
            "strict_input_available": available, "input_status_or_no_score_reason": reason,
            "issue_horizon_key_count": count})
    target_groups: dict[tuple[Any, ...], dict[str, Any]] = {}
    for key, count in sorted(target_cross.items()):
        cell_id, site, year, issue_season, target_season, horizon, available, reason, record_id = key
        group = (cell_id, site, year, issue_season, target_season, horizon, available, reason)
        entry = target_groups.setdefault(group, {"positive_issue_horizon_key_count": 0, "unique_completion_record_ids": set()})
        entry["positive_issue_horizon_key_count"] += count
        entry["unique_completion_record_ids"].add(record_id)
    target_cross_rows = []
    for key, item in sorted(target_groups.items()):
        cell_id, site, year, issue_season, target_season, horizon, available, reason = key
        ids = sorted(item["unique_completion_record_ids"])
        target_cross_rows.append({"cell_id": cell_id, "site_id": site, "issue_year": year,
            "issue_season": issue_season, "target_aggregate_season": target_season,
            "horizon_hours": horizon, "strict_input_available": available,
            "input_status_or_no_score_reason": reason,
            "positive_issue_horizon_key_count": item["positive_issue_horizon_key_count"],
            "unique_completion_record_ids": ids, "unique_completion_record_count": len(ids)})

    return {
        "source_rows": source_rows,
        "capture_audit": capture_audit,
        "site_rows": site_rows,
        "calendars": calendars,
        "thresholds": thresholds,
        "threshold_support": {"sites": threshold_support},
        "matrix_rows": matrix,
        "cell_rows": by_cell,
        "cell_support": {"cells": cell_support, "input_ledger_rows": len(input_ledger),
                         "input_no_score_reasons_by_site": input_no_score,
                         "input_age_by_site": input_age,
                         "input_assumption": "final-product retrospective replay; release/arrival unknown",
                         "no_metrics": True},
        "paired_transitions": {"comparison_scope": "same site/issue/horizon keys; full denominators first; common-known conditional transitions separately",
                               "pairs": pair_rows},
        "input_ledger": input_ledger,
        "input_label_crosstabs": {"issue_panel_crosstabs": issue_cross,
                                  "target_aggregate_completion_crosstabs": target_cross_rows,
                                  "issue_panel_crosstab_row_count": len(issue_cross),
                                  "completion_event_cross_tab_row_count": len(target_cross_rows),
                                  "season_conventions": {
                                      "issue_season": "DJF/MAM/JJA/SON from 12 UTC issue date's UTC calendar month (December belongs to DJF of its calendar year for the issue-year cross-tab).",
                                      "target_aggregate_season": "DJF/MAM/JJA/SON from the local calendar date of the source daily aggregate whose provider row ID completes the episode; keep separate from issue season.",
                                  },
                                  "status_denominator_rule": "Every expected issue/horizon appears exactly once in issue_panel_crosstabs; unknown is not collapsed into any event outcome."},
        "diagonal_reproduction": {
            cell_id: {"rows": len(by_cell[cell_id]),
                      "canonical_rows_sha256": sha256_bytes(("\n".join(
                          json.dumps(row, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
                          for row in by_cell[cell_id]) + "\n").encode("utf-8"))}
            for cell_id in (CELLS[0][0], CELLS[3][0])
        },
    }


def _write_json(path: Path, obj: Any) -> None:
    path.write_text(json.dumps(obj, indent=2, sort_keys=True, ensure_ascii=False) + "\n", encoding="utf-8")


def _write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    with path.open("w", encoding="utf-8", newline="\n") as stream:
        for row in rows:
            stream.write(json.dumps(row, sort_keys=True, separators=(",", ":"), ensure_ascii=False) + "\n")


def write_replay(result: dict[str, Any], manifest: dict[str, Any], output_dir: Path,
                 manifest_path: Path) -> dict[str, Any]:
    if output_dir.exists():
        raise FileExistsError(f"refusing to overwrite replay destination: {output_dir}")
    output_dir.mkdir(parents=True)
    _write_jsonl(output_dir / "source_rows.jsonl", result["source_rows"])
    _write_jsonl(output_dir / "matrix_labels.jsonl", result["matrix_rows"])
    _write_jsonl(output_dir / "input_ledger.jsonl", result["input_ledger"])
    _write_json(output_dir / "diagonal_reproduction.json", result["diagonal_reproduction"])
    for filename, key in (("threshold_support.json", "threshold_support"),
                          ("cell_support.json", "cell_support"),
                          ("paired_transitions.json", "paired_transitions"),
                          ("input_label_crosstabs.json", "input_label_crosstabs"),
                          ("capture_audit.json", "capture_audit")):
        _write_json(output_dir / filename, result[key])
    output_hashes = {}
    for path in sorted(output_dir.iterdir()):
        output_hashes[path.name] = {"bytes": path.stat().st_size, "sha256": sha256_file(path)}
    counts = {
        "source_rows": len(result["source_rows"]),
        "matrix_rows": len(result["matrix_rows"]),
        "input_issue_keys": len(result["input_ledger"]),
        "cells": len(result["cell_rows"]),
        "support_rows": sum(len(cell["site_horizon_support"]) for cell in result["cell_support"]["cells"].values()),
    }
    out_manifest = {
        "manifest_version": "flood-sentinel-daily-quality-replay-output-v1",
        "input_manifest": {"name": manifest_path.name, "sha256": sha256_file(manifest_path)},
        "raw_pages": result["capture_audit"]["pages"],
        "counts_derived_from_consumed_pages": counts,
        "quality_thresholds_exact": {
            site: {policy: f"{q.numerator}/{q.denominator}" for policy, q in policies.items()}
            for site, policies in result["thresholds"].items()
        },
        "assumptions": {
            "civil_time": manifest["civil_time_assumption"],
            "availability": manifest["availability"],
            "physical_state_onset_warning_lead": "unknown",
            "methods_scope": "exposed development source-quality replay; no model or performance metrics",
        },
        "runtime": {"python": platform.python_version(), "platform": platform.platform()},
        "outputs": output_hashes,
    }
    _write_json(output_dir / "replay_manifest.json", out_manifest)
    return out_manifest


def replay(manifest_path: Path, raw_dir: Path, output_dir: Path) -> dict[str, Any]:
    manifest = read_manifest(manifest_path)
    result = derive_replay(manifest, raw_dir)
    return write_replay(result, manifest, output_dir, manifest_path)
