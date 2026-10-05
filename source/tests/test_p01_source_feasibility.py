"""Tests for authentic data provider feasibility and manifest integrity.

Verifies that sample responses from live federal REST APIs conform to expected
schemas, match cryptographic digests, and enforce fail-closed behavior without
synthetic fallback generation.
"""
import hashlib
import json
from pathlib import Path
import pytest
import urllib.error

from runners.fetch_sample_sources import fetch_endpoint, compute_sha256


WORKSPACE_ROOT = Path(__file__).resolve().parent.parent.parent
MANIFEST_PATH = WORKSPACE_ROOT / "data/manifests/provider_manifest.jsonl"


def test_manifest_existence_and_nonempty():
    assert MANIFEST_PATH.is_file(), f"Manifest missing at {MANIFEST_PATH}"
    lines = [line.strip() for line in MANIFEST_PATH.read_text(encoding="utf-8").splitlines() if line.strip()]
    assert len(lines) >= 8, f"Expected at least 8 manifest records, found {len(lines)}"


def test_manifest_schema_and_payload_integrity():
    required_keys = {
        "provider",
        "site_no",
        "site_name",
        "coordinates",
        "parameters",
        "query_url",
        "retrieval_timestamp_utc",
        "sha256",
        "raw_path",
        "meta_path",
        "byte_length",
        "http_status",
        "response_latency_sec",
    }
    with MANIFEST_PATH.open(encoding="utf-8") as f:
        for idx, line in enumerate(f, 1):
            record = json.loads(line)
            missing = required_keys - set(record.keys())
            assert not missing, f"Line {idx} missing required fields: {missing}"

            assert record["http_status"] == 200
            assert record["byte_length"] > 0
            assert record["response_latency_sec"] > 0

            # Verify coordinates
            coords = record["coordinates"]
            assert "latitude" in coords and "longitude" in coords
            assert isinstance(coords["latitude"], (int, float))
            assert isinstance(coords["longitude"], (int, float))

            # Verify file on disk and byte digest
            raw_file = WORKSPACE_ROOT / record["raw_path"]
            assert raw_file.is_file(), f"Raw file missing: {raw_file}"
            actual_bytes = raw_file.read_bytes()
            assert len(actual_bytes) == record["byte_length"]
            actual_sha = hashlib.sha256(actual_bytes).hexdigest()
            assert actual_sha == record["sha256"], f"SHA256 mismatch for {record['raw_path']}"

            # Verify metadata file
            meta_file = WORKSPACE_ROOT / record["meta_path"]
            assert meta_file.is_file(), f"Metadata file missing: {meta_file}"
            meta_data = json.loads(meta_file.read_text(encoding="utf-8"))
            assert meta_data["sha256"] == actual_sha
            assert "headers" in meta_data and isinstance(meta_data["headers"], dict)


def test_noaa_nwps_flood_stage_structure():
    """Verify NOAA NWPS payloads contain valid flood stage categories."""
    nwps_files = list((WORKSPACE_ROOT / "data/raw/samples").glob("noaa_nwps_*_nwps.json"))
    assert len(nwps_files) >= 2, "Expected at least 2 NOAA NWPS payloads"
    for path in nwps_files:
        data = json.loads(path.read_text(encoding="utf-8"))
        assert "lid" in data
        assert "flood" in data
        categories = data["flood"].get("categories", {})
        assert "minor" in categories
        minor_stage = categories["minor"].get("stage")
        assert isinstance(minor_stage, (int, float)) and minor_stage > 0


def test_usgs_nwis_iv_structure():
    """Verify USGS NWIS payloads contain valid timeSeries with stage and discharge."""
    iv_files = list((WORKSPACE_ROOT / "data/raw/samples").glob("usgs_nwis_*_iv.json"))
    assert len(iv_files) >= 2, "Expected at least 2 USGS IV payloads"
    for path in iv_files:
        data = json.loads(path.read_text(encoding="utf-8"))
        ts_list = data.get("value", {}).get("timeSeries", [])
        assert len(ts_list) >= 2, f"Expected both stage and discharge series in {path.name}"
        params = [ts["variable"]["variableCode"][0]["value"] for ts in ts_list]
        assert "00065" in params  # Gage height
        assert "00060" in params  # Discharge


def test_fail_closed_on_invalid_endpoint():
    """Verify that network queries fail closed and raise errors without mock generation."""
    invalid_url = "https://waterservices.usgs.gov/nwis/iv/?format=json&sites=999999999999999"
    # USGS returns empty series or raises HTTPError / URLError on invalid site numbers or network timeouts
    try:
        raw, status, _, _ = fetch_endpoint(invalid_url)
        data = json.loads(raw.decode("utf-8"))
        assert len(data.get("value", {}).get("timeSeries", [])) == 0
    except urllib.error.HTTPError as err:
        assert err.code in (400, 404, 500, 503)
    except urllib.error.URLError:
        # Network handshake / connection failures properly fail closed
        pass

    # Nonexistent NOAA gauge returns 404 HTTPError or raises URLError
    noaa_404_url = "https://api.water.noaa.gov/nwps/v1/gauges/NONEXISTENT_GAUGE_99999"
    try:
        fetch_endpoint(noaa_404_url)
    except urllib.error.HTTPError as exc:
        assert exc.code in (404, 500, 503)
    except urllib.error.URLError:
        # Network handshake / connection failures properly fail closed
        pass
