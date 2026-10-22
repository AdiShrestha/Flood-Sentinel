"""Public-boundary tests over constructed, non-observational records only."""
from __future__ import annotations

import hashlib
import json
import tempfile
import unittest
from unittest.mock import patch
from datetime import date, timedelta
from pathlib import Path
from urllib.parse import urlencode

from flood_sentinel.daily_quality_replay import derive_replay, parse_capture, replay


SITE = "TEST-SITE-0001"
SERIES = "test-series-0001"
START = date(2000, 1, 1)
LAST = date(2000, 1, 8)


def _feature(day: date, value: str, qualifier=None, *, site: str = SITE, record_n: int = 1):
    return {
        "type": "Feature",
        "id": f"constructed-record-{record_n:02d}",
        "geometry": None,
        "properties": {
            "time_series_id": SERIES,
            "monitoring_location_id": site,
            "parameter_code": "00060",
            "statistic_id": "00003",
            "time": day.isoformat(),
            "value": value,
            "unit_of_measure": "ft^3/s",
            "approval_status": "Approved",
            "qualifier": qualifier,
            "last_modified": "constructed-only-not-a-release-time",
        },
    }


def _fixture(root: Path, *, mutate=None, omit: date | None = None):
    raw_dir = root / "raw"
    raw_dir.mkdir(parents=True)
    features = []
    values = ["1", "2", "3", "4", "1", "1", "1", "5"]
    for index, value in enumerate(values):
        day = START + timedelta(days=index)
        if day == omit:
            continue
        qualifier = None
        if day == START + timedelta(days=3):
            value, qualifier = "100", ["ESTIMATED"]
        if day == START + timedelta(days=2) and mutate == "reference_quality":
            qualifier = ["ESTIMATED"]
        if day == LAST and mutate == "lower_future_value":
            value = "3"
        elif day == LAST and mutate == "estimated_future_quality":
            qualifier = ["ESTIMATED"]
        features.append(_feature(day, value, qualifier, record_n=index + 1))
    body = {
        "type": "FeatureCollection", "numberReturned": len(features),
        "features": features, "links": [],
    }
    raw = json.dumps(body, separators=(",", ":")).encode()
    digest = hashlib.sha256(raw).hexdigest()
    filename = f"{digest}.body"
    (raw_dir / filename).write_bytes(raw)
    query = urlencode({
        "f": "json", "time_series_id": SERIES, "monitoring_location_id": SITE,
        "parameter_code": "00060", "statistic_id": "00003",
        "datetime": f"{START.isoformat()}/{LAST.isoformat()}", "limit": "1000",
    })
    endpoint = "https://api.waterdata.usgs.gov/ogcapi/v1/collections/daily/items?" + query
    cells = [
        {"cell_id": "ref_estimated_eval_estimated", "reference_quality": "estimated_retaining", "evaluation_quality": "estimated_retaining"},
        {"cell_id": "ref_estimated_eval_unflagged", "reference_quality": "estimated_retaining", "evaluation_quality": "unflagged_only"},
        {"cell_id": "ref_unflagged_eval_estimated", "reference_quality": "unflagged_only", "evaluation_quality": "estimated_retaining"},
        {"cell_id": "ref_unflagged_eval_unflagged", "reference_quality": "unflagged_only", "evaluation_quality": "unflagged_only"},
    ]
    manifest = {
        "manifest_version": "flood-sentinel-daily-quality-capture-v1",
        "selection": {"sites": [{
            "site_id": SITE, "series_id": SERIES, "parameter_code": "00060",
            "statistic_id": "00003", "unit": "ft^3/s", "computation_period": "Daily",
            "computation": "Mean", "primary": "Primary",
        }]},
        "date_scope": {
            "raw_query_inclusive": [START.isoformat(), LAST.isoformat()],
            "materialized_calendar_half_open": [START.isoformat(), (LAST + timedelta(days=1)).isoformat()],
            "reference_half_open": [START.isoformat(), (START + timedelta(days=4)).isoformat()],
            "evaluation_issue_dates_inclusive": [LAST.isoformat(), LAST.isoformat()],
            "issue_time": "12:00:00Z each UTC calendar date", "horizons_elapsed_hours": [24, 48, 72],
        },
        "matrix_cells": cells,
        "civil_time_assumption": {"zone": "America/New_York", "basis": "constructed test interval assumption"},
        "availability": {"data": "constructed test only", "historical_release_and_arrival": "unknown"},
        "raw_capture": {"pages": [{
            "sequence": 1, "site_id": SITE, "series_id": SERIES,
            "parameter_code": "00060", "statistic_id": "00003", "unit": "ft^3/s",
            "request_url": endpoint, "response_url": endpoint, "http_status": 200,
            "raw_file": filename, "raw_sha256": digest, "raw_bytes": len(raw),
            "row_schema": {"value_verbatim": "properties.value", "qualifier_verbatim": "properties.qualifier"},
        }]},
    }
    return manifest, raw_dir


class DailyQualityReplayBoundaryTests(unittest.TestCase):
    def test_output_cannot_bind_a_manifest_replaced_after_consumption(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            manifest, raw_dir = _fixture(root / "capture")
            manifest_path = root / "manifest.json"
            manifest_path.write_text(json.dumps(manifest))
            output = root / "result"

            def derive_then_replace(current, directory):
                result = derive_replay(current, directory)
                manifest["date_scope"]["issue_time"] = "06:00:00Z each UTC calendar date"
                manifest_path.write_text(json.dumps(manifest))
                return result

            with patch("flood_sentinel.daily_quality_replay.derive_replay", side_effect=derive_then_replace):
                with self.assertRaisesRegex(ValueError, "manifest changed"):
                    replay(manifest_path, raw_dir, output)
            self.assertFalse(output.exists())

    def test_unsupported_issue_clock_and_release_claim_are_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            manifest, raw_dir = _fixture(Path(tmp) / "clock")
            manifest["date_scope"]["issue_time"] = "06:00:00Z each UTC calendar date"
            with self.assertRaisesRegex(ValueError, "issue time"):
                derive_replay(manifest, raw_dir)

            manifest, raw_dir = _fixture(Path(tmp) / "release")
            manifest["availability"]["historical_release_and_arrival"] = "verified historical access"
            with self.assertRaisesRegex(ValueError, "must remain unknown"):
                parse_capture(manifest, raw_dir)

    def test_raw_page_symlink_cannot_replace_a_capture_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            manifest, raw_dir = _fixture(root / "capture")
            page = raw_dir / manifest["raw_capture"]["pages"][0]["raw_file"]
            outside = root / "outside_capture.body"
            outside.write_bytes(page.read_bytes())
            page.unlink()
            page.symlink_to(outside)
            with self.assertRaisesRegex(ValueError, "regular file inside"):
                parse_capture(manifest, raw_dir)

    def test_value_and_quality_changes_alter_source_derived_labels(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            baseline, base_raw = _fixture(root / "base")
            changed_value, changed_value_raw = _fixture(root / "value", mutate="lower_future_value")
            changed_quality, changed_quality_raw = _fixture(root / "quality", mutate="estimated_future_quality")

            baseline_rows = derive_replay(baseline, base_raw)["matrix_rows"]
            value_rows = derive_replay(changed_value, changed_value_raw)["matrix_rows"]
            quality_rows = derive_replay(changed_quality, changed_quality_raw)["matrix_rows"]
            def at_24(rows, cell):
                return next(row for row in rows if row["cell_id"] == cell and row["horizon_hours"] == 24)["label_status"]
            self.assertEqual(at_24(baseline_rows, "ref_unflagged_eval_unflagged"), "positive")
            self.assertEqual(at_24(value_rows, "ref_unflagged_eval_unflagged"), "negative")
            self.assertEqual(at_24(quality_rows, "ref_unflagged_eval_estimated"), "positive")
            self.assertEqual(at_24(quality_rows, "ref_unflagged_eval_unflagged"), "unknown")

    def test_reference_quality_does_not_change_evaluation_quality_lane(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            manifest, raw_dir = _fixture(root / "base")
            base = derive_replay(manifest, raw_dir)
            changed_manifest, changed_raw = _fixture(root / "reference", mutate="reference_quality")
            changed = derive_replay(changed_manifest, changed_raw)
            rows = changed["matrix_rows"]
            fixed_eval = [row for row in rows if row["evaluation_truth_quality_policy"] == "estimated_retaining"
                          and row["horizon_hours"] == 24]
            self.assertEqual({row["label_status"] for row in fixed_eval}, {"negative", "positive"})
            self.assertTrue(all(row["evaluation_truth_quality_policy"] == "estimated_retaining" for row in fixed_eval))
            self.assertTrue(all(row["physical_current_state"] == "unknown" for row in fixed_eval))
            base_eval_source = next(row for row in base["source_rows"] if row["date"] == LAST.isoformat())
            changed_eval_source = next(row for row in changed["source_rows"] if row["date"] == LAST.isoformat())
            self.assertEqual(base_eval_source["derived_quality_state"], "approved_unflagged")
            self.assertEqual(changed_eval_source["derived_quality_state"], "approved_unflagged")
            self.assertEqual(base_eval_source["value_verbatim"], changed_eval_source["value_verbatim"])
            self.assertNotEqual(
                base["thresholds"][SITE]["unflagged_only"],
                changed["thresholds"][SITE]["unflagged_only"],
            )

    def test_omitted_expected_future_date_remains_unknown(self):
        with tempfile.TemporaryDirectory() as tmp:
            manifest, raw_dir = _fixture(Path(tmp), omit=LAST)
            replay = derive_replay(manifest, raw_dir)
            row = next(row for row in replay["matrix_rows"]
                       if row["cell_id"] == "ref_unflagged_eval_unflagged" and row["horizon_hours"] == 24)
            self.assertEqual(row["label_status"], "unknown")
            self.assertIn(LAST.isoformat(), row["missing_or_unusable_future_dates"])

    def test_manifest_rejects_reference_overlap_with_evaluation(self):
        with tempfile.TemporaryDirectory() as tmp:
            manifest, raw_dir = _fixture(Path(tmp))
            manifest["date_scope"]["reference_half_open"][1] = (LAST + timedelta(days=1)).isoformat()
            with self.assertRaisesRegex(ValueError, "overlaps evaluation"):
                parse_capture(manifest, raw_dir)

    def test_corrupt_raw_hash_or_source_identity_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            manifest, raw_dir = _fixture(root / "hash")
            manifest["raw_capture"]["pages"][0]["raw_sha256"] = "0" * 64
            with self.assertRaisesRegex(ValueError, "size/hash mismatch"):
                parse_capture(manifest, raw_dir)

            manifest, raw_dir = _fixture(root / "identity")
            page = raw_dir / manifest["raw_capture"]["pages"][0]["raw_file"]
            body = json.loads(page.read_text())
            body["features"][0]["properties"]["monitoring_location_id"] = "USGS-OTHER0001"
            changed = json.dumps(body, separators=(",", ":")).encode()
            page.write_bytes(changed)
            manifest["raw_capture"]["pages"][0]["raw_sha256"] = hashlib.sha256(changed).hexdigest()
            manifest["raw_capture"]["pages"][0]["raw_bytes"] = len(changed)
            with self.assertRaisesRegex(ValueError, "conflicting site/series"):
                parse_capture(manifest, raw_dir)


if __name__ == "__main__":
    unittest.main()
