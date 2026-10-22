"""Strict date-only decoding for official USGS daily-value records.

The decoder binds every row to the expected site, time series, parameter,
statistic, native unit, and requested calendar interval. It preserves provider
strings and quality fields. It does not assign a UTC interval, infer release
time, create labels, or turn absent dates into zero-valued observations.
"""
from __future__ import annotations

import hashlib
import json
import math
import re
from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import date, timedelta
from decimal import Decimal, InvalidOperation
from fractions import Fraction
from typing import Any, Iterable, Mapping, Sequence


_ISO_DATE = re.compile(r"\d{4}-\d{2}-\d{2}\Z")
_MISSING = object()


class DailyDecodeError(ValueError):
    """A response page or record conflicts with the bound source contract."""


def _unique_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    value: dict[str, Any] = {}
    for key, item in pairs:
        if key in value:
            raise DailyDecodeError(f"duplicate JSON object key: {key!r}")
        value[key] = item
    return value


def _finite_json_float(token: str) -> float:
    value = float(token)
    if not math.isfinite(value):
        raise DailyDecodeError(f"JSON number exceeds finite float range: {token}")
    return value


def parse_feature_collection(raw: bytes) -> dict[str, Any]:
    """Parse UTF-8 JSON strictly, rejecting duplicate keys and non-finite values."""
    try:
        parsed = json.loads(
            raw.decode("utf-8"),
            object_pairs_hook=_unique_object,
            parse_float=_finite_json_float,
            parse_constant=lambda token: (_ for _ in ()).throw(
                DailyDecodeError(f"non-finite JSON token: {token}")
            ),
        )
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise DailyDecodeError(f"invalid UTF-8 JSON response: {exc}") from exc
    if type(parsed) is not dict or parsed.get("type") != "FeatureCollection":
        raise DailyDecodeError("response is not an OGC FeatureCollection")
    features = parsed.get("features")
    if type(features) is not list:
        raise DailyDecodeError("FeatureCollection.features must be a list")
    number_returned = parsed.get("numberReturned")
    if type(number_returned) is not int or number_returned != len(features):
        raise DailyDecodeError("numberReturned does not match the feature count")
    return parsed


def _identifier(value: Any, field: str) -> str:
    if type(value) is not str or not value.strip() or value != value.strip():
        raise DailyDecodeError(f"{field} must be a nonempty, unpadded string")
    return value


def _calendar_date(value: Any, field: str) -> date:
    if type(value) is not str or not _ISO_DATE.fullmatch(value):
        raise DailyDecodeError(f"{field} must be an ISO calendar date")
    try:
        parsed = date.fromisoformat(value)
    except ValueError as exc:
        raise DailyDecodeError(f"{field} is not a real calendar date") from exc
    if parsed.isoformat() != value:
        raise DailyDecodeError(f"{field} is not canonically encoded")
    return parsed


def classify_daily_quality(approval: Any, qualifier: Any = _MISSING) -> str:
    """Classify only the exact quality forms documented by this contract.

    Unknown status/qualifier shapes stay unknown. A missing value is handled
    separately and never enters a numeric quality lane.
    """
    approved = approval == "Approved" or approval == ["Approved"]
    if not approved:
        if approval is None or approval == "" or approval == []:
            return "unknown_approval"
        return "not_approved_or_unknown_status"
    if qualifier is None or qualifier == "" or qualifier == []:
        return "approved_unflagged"
    if qualifier == ["ESTIMATED"]:
        return "approved_estimated"
    return "approved_unknown_qualifier"


def _numeric_value(raw_value: Any) -> tuple[Decimal | None, str | None]:
    if raw_value is None:
        return None, "null_value"
    if type(raw_value) is not str:
        return None, "non_string_value"
    try:
        parsed = Decimal(raw_value)
    except (InvalidOperation, ValueError):
        return None, "invalid_decimal_value"
    if not parsed.is_finite():
        return None, "non_finite_value"
    return parsed, "negative_value_preserved" if parsed < 0 else None


@dataclass(frozen=True)
class DailyRecord:
    record_id: str
    site_id: str
    series_id: str
    parameter_code: str
    statistic_id: str
    date: date
    value_verbatim: Any
    unit_verbatim: str
    approval_verbatim: Any
    qualifier_verbatim: Any
    qualifier_present: bool
    last_modified_verbatim: Any
    numeric_value: Decimal | None
    value_state: str | None
    quality_state: str
    page_sha256: str
    feature_canonical_sha256: str


@dataclass(frozen=True)
class DateSlot:
    date: date
    records: tuple[DailyRecord, ...]
    status: str

    @property
    def unique_record(self) -> DailyRecord | None:
        return self.records[0] if self.status == "one_record" else None


@dataclass(frozen=True)
class DailyDecode:
    records: tuple[DailyRecord, ...]
    date_slots: tuple[DateSlot, ...]
    duplicate_record_ids: tuple[str, ...]
    conflicted_record_ids: tuple[str, ...]


def decode_pages(
    pages: Sequence[tuple[bytes, str]],
    *,
    site_id: str,
    series_id: str,
    parameter_code: str,
    statistic_id: str,
    native_unit: str,
    date_start: str,
    date_end: str,
) -> DailyDecode:
    """Decode complete raw response bodies for one exact source identity.

    `pages` contains (raw_body, sha256) pairs in captured pagination order.
    A duplicate row is retained and makes its date unresolved. Conflicting
    bytes under one provider record ID are a hard error; no version wins by
    dictionary insertion order.
    """
    expected_site = _identifier(site_id, "site_id")
    expected_series = _identifier(series_id, "series_id")
    expected_parameter = _identifier(parameter_code, "parameter_code")
    expected_statistic = _identifier(statistic_id, "statistic_id")
    expected_unit = _identifier(native_unit, "native_unit")
    first_date = _calendar_date(date_start, "date_start")
    last_date = _calendar_date(date_end, "date_end")
    if first_date > last_date:
        raise DailyDecodeError("date interval is reversed")
    if type(pages) not in (list, tuple) or not pages:
        raise DailyDecodeError("at least one complete response page is required")

    decoded: list[DailyRecord] = []
    for page_index, (raw, claimed_digest) in enumerate(pages, start=1):
        if type(raw) is not bytes:
            raise DailyDecodeError(f"page {page_index} body must be bytes")
        if type(claimed_digest) is not str or not re.fullmatch(r"[0-9a-f]{64}", claimed_digest):
            raise DailyDecodeError(f"page {page_index} digest must be lowercase SHA-256")
        actual_digest = hashlib.sha256(raw).hexdigest()
        if actual_digest != claimed_digest:
            raise DailyDecodeError(f"page {page_index} raw-body digest mismatch")
        collection = parse_feature_collection(raw)
        for feature_index, feature in enumerate(collection["features"], start=1):
            if (type(feature) is not dict or feature.get("type") != "Feature"
                    or type(feature.get("properties")) is not dict):
                raise DailyDecodeError(f"page {page_index} feature {feature_index} is malformed")
            properties = feature["properties"]
            record_id = _identifier(feature.get("id"), "feature.id")
            actual_identity = (
                _identifier(properties.get("monitoring_location_id"), "monitoring_location_id"),
                _identifier(properties.get("time_series_id"), "time_series_id"),
                _identifier(properties.get("parameter_code"), "parameter_code"),
                _identifier(properties.get("statistic_id"), "statistic_id"),
                _identifier(properties.get("unit_of_measure"), "unit_of_measure"),
            )
            expected_identity = (
                expected_site, expected_series, expected_parameter, expected_statistic, expected_unit
            )
            if actual_identity != expected_identity:
                raise DailyDecodeError(
                    f"feature {record_id} identity mismatch: {actual_identity!r} != {expected_identity!r}"
                )
            row_date = _calendar_date(properties.get("time"), "properties.time")
            if not first_date <= row_date <= last_date:
                raise DailyDecodeError(f"feature {record_id} lies outside the requested date interval")
            value, value_state = _numeric_value(properties.get("value"))
            quality_state = classify_daily_quality(
                properties.get("approval_status"), properties.get("qualifier", _MISSING)
            )
            feature_bytes = json.dumps(
                feature, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False
            ).encode("utf-8")
            decoded.append(
                DailyRecord(
                    record_id=record_id,
                    site_id=actual_identity[0],
                    series_id=actual_identity[1],
                    parameter_code=actual_identity[2],
                    statistic_id=actual_identity[3],
                    date=row_date,
                    value_verbatim=properties.get("value"),
                    unit_verbatim=actual_identity[4],
                    approval_verbatim=properties.get("approval_status"),
                    qualifier_verbatim=properties.get("qualifier"),
                    qualifier_present="qualifier" in properties,
                    last_modified_verbatim=properties.get("last_modified"),
                    numeric_value=value,
                    value_state=value_state,
                    quality_state=quality_state,
                    page_sha256=actual_digest,
                    feature_canonical_sha256=hashlib.sha256(feature_bytes).hexdigest(),
                )
            )

    ids: dict[str, set[str]] = defaultdict(set)
    for record in decoded:
        ids[record.record_id].add(record.feature_canonical_sha256)
    conflicted_ids = tuple(sorted(record_id for record_id, hashes in ids.items() if len(hashes) > 1))
    if conflicted_ids:
        raise DailyDecodeError(
            "conflicting source versions share provider record ID(s): " + ", ".join(conflicted_ids)
        )
    duplicate_ids = tuple(sorted(record_id for record_id, rows in Counter(r.record_id for r in decoded).items() if rows > 1))

    by_date: dict[date, list[DailyRecord]] = defaultdict(list)
    for record in decoded:
        by_date[record.date].append(record)
    slots: list[DateSlot] = []
    cursor = first_date
    while cursor <= last_date:
        rows = tuple(by_date.get(cursor, ()))
        if not rows:
            status = "absent"
        elif len(rows) > 1 or any(row.record_id in duplicate_ids for row in rows):
            status = "conflicting_or_duplicate_records"
        else:
            status = "one_record"
        slots.append(DateSlot(cursor, rows, status))
        cursor += timedelta(days=1)
    return DailyDecode(tuple(decoded), tuple(slots), duplicate_ids, conflicted_ids)


def type8_quantile(values: Iterable[Decimal], probability: Fraction) -> Fraction:
    """Exact rational Type-8 quantile for already quality-filtered Decimals.

    Return a Fraction because interpolation can repeat in base ten. Convert
    only for display; retain this value for threshold comparisons.
    """
    if type(probability) is not Fraction or not Fraction(0) <= probability <= Fraction(1):
        raise ValueError("probability must be a Fraction in [0, 1]")
    supplied = list(values)
    if not supplied or any(type(value) is not Decimal or not value.is_finite() for value in supplied):
        raise ValueError("Type-8 quantile requires at least one finite Decimal")
    ordered = sorted(Fraction(value) for value in supplied)
    if len(ordered) == 1:
        return ordered[0]
    h = probability * (Fraction(len(ordered), 1) + Fraction(1, 3)) + Fraction(1, 3)
    if h <= 1:
        return ordered[0]
    if h >= len(ordered):
        return ordered[-1]
    lower_index = h.numerator // h.denominator
    fraction = h - lower_index
    lower = ordered[lower_index - 1]
    upper = ordered[lower_index]
    return lower + fraction * (upper - lower)
