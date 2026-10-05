"""Unit and regression tests for Work Package P02 acquisition, decoding, and provenance.

Tests exact SI unit conversion factors, strict timezone-aware parsing,
fail-closed error handling on corrupted payloads, and cryptographic provenance bindings.
"""
from __future__ import annotations

import csv
import hashlib
import json
import math
from pathlib import Path
import pytest

from flood_sentinel.acquisition.units import (
    FEET_TO_METERS,
    CFS_TO_CMS,
    CELSIUS_TO_KELVIN_OFFSET,
    feet_to_meters,
    meters_to_feet,
    cfs_to_cms,
    cms_to_cfs,
    celsius_to_kelvin,
    kelvin_to_celsius,
    convert_units,
)
from flood_sentinel.acquisition.decoder import (
    parse_iso_utc,
    parse_usgs_iv_json,
    parse_noaa_nwps_json,
    parse_daymet_json,
    NormalizedRecord,
)
from flood_sentinel.acquisition.provenance import (
    build_source_records_from_samples,
    load_source_records_csv,
    SOURCE_RECORDS_COLUMNS,
)

WORKSPACE_ROOT = Path(__file__).resolve().parent.parent.parent
MANIFEST_PATH = WORKSPACE_ROOT / "data/manifests/provider_manifest.jsonl"
SOURCE_RECORDS_PATH = WORKSPACE_ROOT / "data/source_records.csv"


# ==============================================================================
# 1. Deterministic Physical Unit Conversions
# ==============================================================================

def test_exact_conversion_constants():
    """Verify physical conversion constants against international standards."""
    assert FEET_TO_METERS == 0.3048
    assert CFS_TO_CMS == 0.028316846592
    assert CELSIUS_TO_KELVIN_OFFSET == 273.15


def test_length_conversions():
    """Verify feet to meters and inverse conversions."""
    assert feet_to_meters(1.0) == 0.3048
    assert feet_to_meters(10.0) == 3.048
    assert meters_to_feet(0.3048) == pytest.approx(1.0, rel=1e-12)

    # Invertibility over a range of positive stages
    for ft in [0.5, 3.42, 10.0, 25.5, 100.0]:
        m = feet_to_meters(ft)
        reconstructed = meters_to_feet(m)
        assert reconstructed == pytest.approx(ft, rel=1e-12)


def test_discharge_conversions():
    """Verify cfs to cms and inverse conversions."""
    assert cfs_to_cms(1.0) == 0.028316846592
    assert cms_to_cfs(0.028316846592) == pytest.approx(1.0, rel=1e-12)

    # Invertibility over a range of flow rates
    for flow_cfs in [1.0, 100.0, 2160.0, 50000.0]:
        cms = cfs_to_cms(flow_cfs)
        reconstructed = cms_to_cfs(cms)
        assert reconstructed == pytest.approx(flow_cfs, rel=1e-12)


def test_temperature_conversions():
    """Verify temperature conversions and absolute zero floor."""
    assert celsius_to_kelvin(0.0) == 273.15
    assert celsius_to_kelvin(100.0) == 373.15
    assert kelvin_to_celsius(273.15) == pytest.approx(0.0, abs=1e-12)

    # Sub-zero Kelvin rejection
    with pytest.raises(ValueError, match="below absolute zero"):
        kelvin_to_celsius(-1.0)


def test_non_finite_unit_conversion_rejections():
    """Verify that non-finite values (NaN, inf) are rejected."""
    for bad_val in [float("nan"), float("inf"), float("-inf"), "string", None]:
        with pytest.raises(ValueError):
            feet_to_meters(bad_val)
        with pytest.raises(ValueError):
            cfs_to_cms(bad_val)
        with pytest.raises(ValueError):
            celsius_to_kelvin(bad_val)


def test_convert_units_dispatcher():
    """Verify convert_units general interface and unsupported pair rejection."""
    assert convert_units(10.0, "ft", "m") == 3.048
    assert convert_units(100.0, "cfs", "m3/s") == 2.8316846592
    assert convert_units(5.0, "m", "m") == 5.0

    with pytest.raises(ValueError, match="Unsupported unit conversion pair"):
        convert_units(1.0, "parsec", "furlong")


# ==============================================================================
# 2. Strict Timezone-Aware UTC Timestamp Parsing
# ==============================================================================

def test_parse_iso_utc_offsets():
    """Verify timezone offset normalization to canonical UTC."""
    # US Eastern Daylight Time (-04:00)
    assert parse_iso_utc("2026-10-04T08:55:00.000-04:00") == "2026-10-04T12:55:00Z"
    # US Eastern Standard Time (-05:00)
    assert parse_iso_utc("2026-01-15T12:00:00-05:00") == "2026-01-15T17:00:00Z"
    # Already UTC (Z)
    assert parse_iso_utc("2026-10-05T00:00:00Z") == "2026-10-05T00:00:00Z"
    # Positive offset (+05:45)
    assert parse_iso_utc("2026-10-05T05:45:00+05:45") == "2026-10-05T00:00:00Z"


def test_parse_iso_utc_rejects_naive_timestamps():
    """Verify that naive datetimes without timezone offset fail closed."""
    for naive in ["2026-10-04T08:55:00", "2026-10-04 08:55:00", "2026-10-04"]:
        with pytest.raises(ValueError, match="explicit timezone offset"):
            parse_iso_utc(naive)

    with pytest.raises(ValueError, match="non-empty string"):
        parse_iso_utc("")


# ==============================================================================
# 3. Payload Decoders and Fail-Closed Behavior
# ==============================================================================

def test_usgs_iv_decoder_sample():
    """Verify USGS NWIS decoder extracts both stage and discharge."""
    sample_file = WORKSPACE_ROOT / "data/raw/samples/usgs_nwis_01646500_iv.json"
    raw_bytes = sample_file.read_bytes()
    raw_sha = hashlib.sha256(raw_bytes).hexdigest()

    records = parse_usgs_iv_json(raw_bytes, raw_sha)
    assert len(records) > 0

    params = {r.parameter for r in records}
    assert "gage_height_m" in params
    assert "discharge_cms" in params

    for r in records:
        assert r.origin == "observational"
        assert r.provider == "USGS-NWIS"
        assert r.site_no == "01646500"
        assert r.raw_sha256 == raw_sha
        assert r.timestamp_utc.endswith("Z")
        assert math.isfinite(r.value_si)
        assert r.value_si >= 0.0


def test_usgs_decoder_corrupted_payload():
    """Verify USGS decoder rejects corrupted or empty JSON."""
    with pytest.raises(ValueError, match="Malformed USGS NWIS JSON"):
        parse_usgs_iv_json(b"not a json", "a" * 64)

    with pytest.raises(ValueError, match="missing valid 'value.timeSeries'"):
        parse_usgs_iv_json(b"{}", "a" * 64)


def test_noaa_nwps_decoder_sample():
    """Verify NOAA NWPS decoder extracts valid flood category stages."""
    sample_file = WORKSPACE_ROOT / "data/raw/samples/noaa_nwps_01646500_nwps.json"
    raw_bytes = sample_file.read_bytes()
    raw_sha = hashlib.sha256(raw_bytes).hexdigest()

    records = parse_noaa_nwps_json(raw_bytes, raw_sha)
    assert len(records) >= 3  # minor, moderate, major

    stage_names = {r.parameter for r in records}
    assert "flood_stage_minor_m" in stage_names

    # Check Little Falls minor flood stage: 10.0 ft -> 3.048 m
    minor_rec = next(r for r in records if r.parameter == "flood_stage_minor_m")
    assert minor_rec.value_si == pytest.approx(3.048, abs=1e-4)
    assert minor_rec.unit_si == "m"


def test_daymet_decoder_sample():
    """Verify NASA Daymet decoder extracts meteorological daily series."""
    sample_file = WORKSPACE_ROOT / "data/raw/samples/nasa_daymet_01646500_daymet.json"
    raw_bytes = sample_file.read_bytes()
    raw_sha = hashlib.sha256(raw_bytes).hexdigest()

    records = parse_daymet_json(raw_bytes, raw_sha, "01646500")
    assert len(records) == 20  # 5 days x 4 parameters (prcp, tmax, tmin, swe)

    params = {r.parameter for r in records}
    assert "precipitation_mm_day" in params
    assert "temperature_max_c" in params
    assert "temperature_min_c" in params
    assert "snow_water_equivalent_kg_m2" in params


# ==============================================================================
# 4. Cryptographic Provenance and Source Records Catalog
# ==============================================================================

def test_source_records_csv_schema_and_integrity():
    """Verify that data/source_records.csv exists and conforms strictly to contract schema."""
    assert SOURCE_RECORDS_PATH.is_file(), f"Missing {SOURCE_RECORDS_PATH}"
    rows = load_source_records_csv(SOURCE_RECORDS_PATH)
    assert len(rows) >= 900, f"Expected at least 900 records, got {len(rows)}"

    manifest_shas = set()
    with MANIFEST_PATH.open("r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                manifest_shas.add(json.loads(line)["sha256"])

    seen_ids = set()
    for row in rows:
        # 1. Uniqueness
        rid = row["record_id"]
        assert rid not in seen_ids, f"Duplicate record_id: {rid}"
        seen_ids.add(rid)

        # 2. Strict origin
        assert row["origin"] == "observational"

        # 3. Provider membership
        assert row["provider"] in {"USGS-NWIS", "NOAA-NWPS", "NASA-Daymet"}

        # 4. Site numbers in feasible sampling frame
        assert row["site_no"] in {"01646500", "01463500", "01434000"}

        # 5. Non-empty SI values
        val_si = float(row["value_si"])
        assert math.isfinite(val_si)

        # 6. Cryptographic binding to manifest
        assert row["raw_sha256"] in manifest_shas, f"Unverified raw_sha256 in row: {row}"


def test_tamper_detection_in_raw_bytes(tmp_path):
    """Verify that tampering with raw payload bytes fails closed immediately."""
    # Create a corrupted manifest pointing to tampered bytes
    tampered_raw = tmp_path / "tampered.json"
    tampered_raw.write_bytes(b'{"value": "corrupted"}')

    fake_manifest = tmp_path / "manifest.jsonl"
    fake_manifest.write_text(
        json.dumps(
            {
                "provider": "USGS-NWIS",
                "site_no": "01646500",
                "sha256": "0" * 64,  # Expected hash does not match tampered bytes
                "raw_path": str(tampered_raw.relative_to(tmp_path)),
            }
        )
        + "\n"
    )

    out_csv = tmp_path / "out.csv"
    with pytest.raises(ValueError, match="Cryptographic hash mismatch"):
        build_source_records_from_samples(fake_manifest, tmp_path, out_csv)
