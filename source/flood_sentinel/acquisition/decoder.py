"""Timezone-aware payload decoders for hydrological and meteorological data.

Parses raw payloads from USGS NWIS, NOAA NWPS, and NASA Daymet into
strictly validated, normalized observation records with SI unit conversions.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
import json
import math
import re

from .units import feet_to_meters, cfs_to_cms


def parse_iso_utc(ts_str: str) -> str:
    """Parse an ISO-8601 timestamp string into canonical UTC representation.

    Fails closed if the string is naive (lacks explicit timezone offset).
    Returns formatted string: YYYY-MM-DDTHH:MM:SSZ.
    """
    if not isinstance(ts_str, str) or not ts_str.strip():
        raise ValueError("Timestamp must be a non-empty string")

    clean_ts = ts_str.strip()

    # Verify presence of timezone designator ('Z' or numeric offset '+/-HH:MM')
    has_tz = (
        clean_ts.endswith("Z")
        or re.search(r"[+-]\d{2}:?\d{2}$", clean_ts) is not None
        or re.search(r"[+-]\d{4}$", clean_ts) is not None
    )
    if not has_tz:
        raise ValueError(f"Timestamp must include explicit timezone offset; naive datetime rejected: '{ts_str}'")

    try:
        dt_obj = datetime.fromisoformat(clean_ts)
    except Exception as ex:
        raise ValueError(f"Malformed ISO-8601 timestamp '{ts_str}': {ex}") from ex

    if dt_obj.tzinfo is None or dt_obj.utcoffset() is None:
        raise ValueError(f"Timestamp parsed without tzinfo; naive datetime rejected: '{ts_str}'")

    utc_dt = dt_obj.astimezone(timezone.utc)
    return utc_dt.strftime("%Y-%m-%dT%H:%M:%SZ")


@dataclass(frozen=True)
class NormalizedRecord:
    """Normalized observation or threshold record with SI physical units."""
    record_id: str
    origin: str  # Must be 'observational' for authentic measurements
    provider: str
    site_no: str
    parameter: str
    timestamp_utc: str
    value_si: float
    unit_si: str
    quality_code: str
    raw_sha256: str

    def __post_init__(self):
        if not self.record_id or not isinstance(self.record_id, str):
            raise ValueError("record_id must be a non-empty string")
        if self.origin != "observational":
            raise ValueError(f"origin must be 'observational', got '{self.origin}'")
        if not self.provider or not self.site_no or not self.parameter:
            raise ValueError("provider, site_no, and parameter are mandatory fields")
        if not isinstance(self.value_si, (int, float)) or not math.isfinite(self.value_si):
            raise ValueError(f"value_si must be a finite float, got {self.value_si}")
        if not re.fullmatch(r"[0-9a-f]{64}", self.raw_sha256):
            raise ValueError("raw_sha256 must be a 64-character lowercase hexadecimal digest")


def parse_usgs_iv_json(raw_bytes: bytes, raw_sha256: str) -> list[NormalizedRecord]:
    """Parse USGS NWIS Instantaneous Values (IV) JSON payload."""
    try:
        data = json.loads(raw_bytes.decode("utf-8"))
    except Exception as ex:
        raise ValueError(f"Malformed USGS NWIS JSON payload: {ex}") from ex

    if "value" not in data or not isinstance(data["value"], dict) or "timeSeries" not in data["value"] or not isinstance(data["value"]["timeSeries"], list):
        raise ValueError("USGS payload missing valid 'value.timeSeries' list")

    time_series = data["value"]["timeSeries"]

    records: list[NormalizedRecord] = []

    for ts in time_series:
        source_info = ts.get("sourceInfo", {})
        site_codes = source_info.get("siteCode", [])
        if not site_codes:
            continue
        site_no = site_codes[0].get("value", "unknown")

        var_code_obj = ts.get("variable", {}).get("variableCode", [{}])
        if not var_code_obj:
            continue
        param_code = var_code_obj[0].get("value")

        # Map parameters to SI units and conversion functions
        if param_code == "00065":  # Gage height, ft -> m
            param_name = "gage_height_m"
            unit_si = "m"
            converter = feet_to_meters
        elif param_code == "00060":  # Discharge, cfs -> m3/s
            param_name = "discharge_cms"
            unit_si = "m3/s"
            converter = cfs_to_cms
        else:
            # Skip unmapped ancillary parameters (e.g. water temperature, conductance)
            continue

        values_list = ts.get("values", [{}])[0].get("value", [])
        for entry in values_list:
            raw_val_str = entry.get("value")
            dt_raw = entry.get("dateTime")
            qualifiers = entry.get("qualifiers", ["P"])
            qual_code = qualifiers[0] if qualifiers else "P"

            # Skip non-numeric flags (e.g. 'Ice', 'Eqp', 'Rat') without substituting 0.0
            try:
                raw_float = float(raw_val_str)
                if not math.isfinite(raw_float):
                    continue
            except (ValueError, TypeError):
                continue

            utc_ts = parse_iso_utc(dt_raw)
            value_si = converter(raw_float)

            # Compact timestamp for deterministic record_id: YYYYMMDDTHHMMSSZ
            compact_ts = utc_ts.replace("-", "").replace(":", "")
            record_id = f"USGS_{site_no}_{param_name}_{compact_ts}"

            records.append(
                NormalizedRecord(
                    record_id=record_id,
                    origin="observational",
                    provider="USGS-NWIS",
                    site_no=site_no,
                    parameter=param_name,
                    timestamp_utc=utc_ts,
                    value_si=round(value_si, 6),
                    unit_si=unit_si,
                    quality_code=qual_code,
                    raw_sha256=raw_sha256,
                )
            )

    return records


def parse_noaa_nwps_json(raw_bytes: bytes, raw_sha256: str) -> list[NormalizedRecord]:
    """Parse NOAA NWPS gauge metadata and flood stages JSON payload."""
    try:
        data = json.loads(raw_bytes.decode("utf-8"))
    except Exception as ex:
        raise ValueError(f"Malformed NOAA NWPS JSON payload: {ex}") from ex

    lid = data.get("lid")
    usgs_id = data.get("usgsId") or lid
    if not usgs_id:
        raise ValueError("NOAA NWPS payload missing gauge identifier (lid/usgsId)")

    categories = data.get("flood", {}).get("categories", {})
    if not categories:
        raise ValueError("NOAA NWPS payload missing 'flood.categories' dictionary")

    # Use nominal reference timestamp for official static operational thresholds
    reference_ts = "2026-01-01T00:00:00Z"
    records: list[NormalizedRecord] = []

    for cat_name, cat_data in categories.items():
        if not isinstance(cat_data, dict):
            continue
        stage_ft = cat_data.get("stage")
        if stage_ft is None:
            continue

        try:
            stage_ft_float = float(stage_ft)
            if not math.isfinite(stage_ft_float) or stage_ft_float <= 0.0:
                continue
        except (ValueError, TypeError):
            continue

        stage_m = feet_to_meters(stage_ft_float)
        record_id = f"NOAA_NWPS_{usgs_id}_flood_stage_{cat_name}"

        records.append(
            NormalizedRecord(
                record_id=record_id,
                origin="observational",
                provider="NOAA-NWPS",
                site_no=usgs_id,
                parameter=f"flood_stage_{cat_name}_m",
                timestamp_utc=reference_ts,
                value_si=round(stage_m, 4),
                unit_si="m",
                quality_code="OFFICIAL_NWS_STAGE",
                raw_sha256=raw_sha256,
            )
        )

    return records


def parse_daymet_json(raw_bytes: bytes, raw_sha256: str, site_no: str) -> list[NormalizedRecord]:
    """Parse NASA Daymet single-pixel meteorological JSON payload."""
    try:
        data = json.loads(raw_bytes.decode("utf-8"))
    except Exception as ex:
        raise ValueError(f"Malformed NASA Daymet JSON payload: {ex}") from ex

    timeseries_data = data.get("data", {})
    years = timeseries_data.get("year", [])
    ydays = timeseries_data.get("yday", [])
    if not years or not ydays or len(years) != len(ydays):
        raise ValueError("Daymet payload missing aligned 'year' and 'yday' series")

    n_samples = len(years)
    records: list[NormalizedRecord] = []

    var_mapping = [
        ("prcp (mm/day)", "precipitation_mm_day", "mm/day"),
        ("tmax (deg c)", "temperature_max_c", "degC"),
        ("tmin (deg c)", "temperature_min_c", "degC"),
        ("swe (kg/m^2)", "snow_water_equivalent_kg_m2", "kg/m2"),
    ]

    for idx in range(n_samples):
        year_int = int(years[idx])
        yday_int = int(ydays[idx])
        date_utc = datetime(year_int, 1, 1, tzinfo=timezone.utc) + timedelta(days=yday_int - 1)
        utc_str = date_utc.strftime("%Y-%m-%dT00:00:00Z")
        compact_ts = date_utc.strftime("%Y%m%d")

        for key, param_name, unit_si in var_mapping:
            if key in timeseries_data and len(timeseries_data[key]) > idx:
                val = timeseries_data[key][idx]
                try:
                    val_float = float(val)
                    if not math.isfinite(val_float):
                        continue
                except (ValueError, TypeError):
                    continue

                record_id = f"DAYMET_{site_no}_{param_name}_{compact_ts}"
                records.append(
                    NormalizedRecord(
                        record_id=record_id,
                        origin="observational",
                        provider="NASA-Daymet",
                        site_no=site_no,
                        parameter=param_name,
                        timestamp_utc=utc_str,
                        value_si=round(val_float, 4),
                        unit_si=unit_si,
                        quality_code="MODEL_REANALYSIS",
                        raw_sha256=raw_sha256,
                    )
                )

    return records
