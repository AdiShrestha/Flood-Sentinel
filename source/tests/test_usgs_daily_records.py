from __future__ import annotations

import hashlib
import json
import unittest
from decimal import Decimal, localcontext
from fractions import Fraction

from flood_sentinel.usgs_daily_records import (
    DailyDecodeError, decode_pages, parse_feature_collection, type8_quantile,
)


SITE = "USGS-02046000"
SERIES = "series-1"
UNIT = "ft^3/s"


def feature(record_id: str = "record-1", **overrides):
    properties = {
        "time_series_id": SERIES,
        "monitoring_location_id": SITE,
        "parameter_code": "00060",
        "statistic_id": "00003",
        "time": "1990-01-01",
        "value": "1.25",
        "unit_of_measure": UNIT,
        "approval_status": "Approved",
        "qualifier": None,
        "last_modified": "2025-01-02T03:04:05Z",
    }
    properties.update(overrides)
    return {"type": "Feature", "id": record_id, "properties": properties}


def page(*features_, number_returned=None):
    obj = {"type": "FeatureCollection", "features": list(features_)}
    obj["numberReturned"] = len(features_) if number_returned is None else number_returned
    raw = json.dumps(obj, separators=(",", ":")).encode()
    return raw, hashlib.sha256(raw).hexdigest()


def decode(raw_pages, start="1990-01-01", end="1990-01-02", **expected):
    values = {"site_id": SITE, "series_id": SERIES, "parameter_code": "00060",
              "statistic_id": "00003", "native_unit": UNIT,
              "date_start": start, "date_end": end}
    values.update(expected)
    return decode_pages(raw_pages, **values)


class DailyRecordDecodeTests(unittest.TestCase):
    def test_binds_exact_site_series_parameter_statistic_unit_and_date(self):
        raw = page(feature())
        result = decode([raw], end="1990-01-01")
        row = result.records[0]
        self.assertEqual((row.site_id, row.series_id, row.parameter_code,
                          row.statistic_id, row.unit_verbatim),
                         (SITE, SERIES, "00060", "00003", UNIT))
        self.assertEqual(row.value_verbatim, "1.25")
        self.assertEqual(row.numeric_value, Decimal("1.25"))
        self.assertEqual(result.date_slots[0].status, "one_record")

    def test_rejects_each_wrong_identity_dimension_and_unit(self):
        mutations = [
            {"monitoring_location_id": "USGS-02046001"},
            {"time_series_id": "series-2"},
            {"parameter_code": "00065"},
            {"statistic_id": "00001"},
            {"unit_of_measure": "m^3/s"},
        ]
        for change in mutations:
            with self.subTest(change=change), self.assertRaises(DailyDecodeError):
                decode([page(feature(**change))], end="1990-01-01")

    def test_rejects_empty_or_whitespace_record_ids_and_wrong_date_extent(self):
        for bad_id in ("", " ", "record-1 ", None):
            with self.subTest(bad_id=bad_id), self.assertRaises(DailyDecodeError):
                decode([page(feature(record_id=bad_id))], end="1990-01-01")
        with self.assertRaises(DailyDecodeError):
            decode([page(feature(time="1990-01-03"))])

    def test_missing_unknown_and_estimated_quality_are_distinct(self):
        raw = page(
            feature("unflagged", time="1990-01-01", value="0", qualifier=None),
            feature("estimated", time="1990-01-02", value="2", qualifier=["ESTIMATED"]),
        )
        result = decode([raw], end="1990-01-03")
        self.assertEqual([r.quality_state for r in result.records],
                         ["approved_unflagged", "approved_estimated"])
        self.assertEqual(result.date_slots[1].unique_record.record_id, "estimated")
        self.assertEqual(result.date_slots[1].unique_record.quality_state, "approved_estimated")
        self.assertEqual(result.date_slots[2].status, "absent")
        self.assertIsNone(result.date_slots[2].unique_record)
        unknown = decode([page(feature(qualifier=["ICE"]))], end="1990-01-01")
        self.assertEqual(unknown.records[0].quality_state, "approved_unknown_qualifier")
        unapproved = decode([page(feature(approval_status="Working"))], end="1990-01-01")
        self.assertEqual(unapproved.records[0].quality_state, "not_approved_or_unknown_status")

    def test_null_and_invalid_values_never_become_zero(self):
        result = decode([page(feature(value=None))], end="1990-01-01")
        self.assertIsNone(result.records[0].numeric_value)
        self.assertEqual(result.records[0].value_state, "null_value")
        self.assertIsNone(result.records[0].value_verbatim)
        invalid = decode([page(feature(value="NaN"))], end="1990-01-01")
        self.assertIsNone(invalid.records[0].numeric_value)
        self.assertEqual(invalid.records[0].value_state, "non_finite_value")
        negative = decode([page(feature(value="-0.25"))], end="1990-01-01")
        self.assertEqual(negative.records[0].numeric_value, Decimal("-0.25"))
        self.assertEqual(negative.records[0].value_state, "negative_value_preserved")

    def test_conflicting_versions_under_one_provider_id_are_rejected(self):
        raw = page(feature(value="1"), feature(value="2"))
        with self.assertRaisesRegex(DailyDecodeError, "conflicting source versions"):
            decode([raw], end="1990-01-01")

    def test_distinct_same_date_records_are_preserved_and_date_is_ambiguous(self):
        result = decode([page(feature("r1"), feature("r2", value="9"))], end="1990-01-01")
        self.assertEqual(len(result.records), 2)
        self.assertEqual(result.date_slots[0].status, "conflicting_or_duplicate_records")
        self.assertIsNone(result.date_slots[0].unique_record)

    def test_exact_duplicate_id_is_retained_and_marks_date_unusable(self):
        row = feature("same")
        result = decode([page(row), page(row)], end="1990-01-01")
        self.assertEqual(result.duplicate_record_ids, ("same",))
        self.assertEqual(len(result.records), 2)
        self.assertEqual(result.date_slots[0].status, "conflicting_or_duplicate_records")

    def test_bad_page_count_and_duplicate_json_keys_fail(self):
        with self.assertRaisesRegex(DailyDecodeError, "numberReturned"):
            decode([page(feature(), number_returned=2)], end="1990-01-01")
        missing_count = json.dumps({"type":"FeatureCollection","features":[feature()]}, separators=(",", ":")).encode()
        with self.assertRaisesRegex(DailyDecodeError, "numberReturned"):
            decode([(missing_count, hashlib.sha256(missing_count).hexdigest())], end="1990-01-01")
        raw = b'{"type":"FeatureCollection","type":"FeatureCollection","features":[]}'
        with self.assertRaisesRegex(DailyDecodeError, "duplicate JSON"):
            decode([(raw, hashlib.sha256(raw).hexdigest())], end="1990-01-01")

    def test_absent_calendar_date_is_an_explicit_slot(self):
        result = decode([page(feature())])
        self.assertEqual([slot.status for slot in result.date_slots], ["one_record", "absent"])
        self.assertIsNone(result.date_slots[1].unique_record)

    def test_type8_q99_is_exact_on_small_rational_example(self):
        values = [Decimal("1"), Decimal("2"), Decimal("4"), Decimal("8")]
        # n=4: h=.99*(4+1/3)+1/3=4.62, clamped to the maximum.
        self.assertEqual(type8_quantile(values, Fraction(99, 100)), Decimal("8"))
        self.assertEqual(type8_quantile(values, Fraction(1, 2)), Decimal("3"))

    def test_absent_qualifier_is_not_a_documented_null(self):
        row = feature()
        del row["properties"]["qualifier"]
        decoded = decode([page(row)], end="1990-01-01").records[0]
        self.assertEqual(decoded.quality_state, "approved_unknown_qualifier")
        self.assertFalse(decoded.qualifier_present)
        explicit_null = decode([page(feature())], end="1990-01-01").records[0]
        self.assertTrue(explicit_null.qualifier_present)
        self.assertEqual(explicit_null.quality_state, "approved_unflagged")

    def test_type8_interpolation_preserves_repeating_rationals(self):
        values = [Decimal("0"), Decimal("1")]
        with localcontext() as context:
            context.prec = 6
            result = type8_quantile(values, Fraction(3, 7))
        self.assertIs(type(result), Fraction)
        self.assertEqual(result, Fraction(1, 3))

    def test_type8_interpolation_preserves_large_exponent_separation(self):
        values = [Decimal("1e-100"), Decimal("1e100")]
        expected = (Fraction(values[0]) + Fraction(values[1])) / 2
        self.assertEqual(type8_quantile(values, Fraction(1, 2)), expected)

    def test_overflowing_json_numbers_are_rejected_everywhere(self):
        for name in ("metadata", "geometry"):
            raw = (b'{"type":"FeatureCollection","features":[],"numberReturned":0,"'
                   + name.encode() + b'":1e999}')
            with self.subTest(name=name), self.assertRaises(DailyDecodeError):
                parse_feature_collection(raw)

    def test_records_must_be_geojson_features(self):
        for kind in (None, "FeatureCollection", "Point"):
            row = feature()
            if kind is None:
                del row["type"]
            else:
                row["type"] = kind
            with self.subTest(kind=kind), self.assertRaises(DailyDecodeError):
                decode([page(row)], end="1990-01-01")


if __name__ == "__main__":
    unittest.main()
