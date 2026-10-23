"""Independent boundary checks for replay metric reporting."""

import unittest

from flood_sentinel.replay import _compare_metric_records, _metric


class ReplayMetricBoundaryTests(unittest.TestCase):
    def test_constant_probability_uses_noninterpolated_ap_and_locked_pr_trapezoid(self):
        result = _metric([1, 0, 0, 0], [0.25, 0.25, 0.25, 0.25], 0.25)
        self.assertAlmostEqual(result["average_precision"], 0.25)
        self.assertAlmostEqual(result["auroc"], 0.5)
        self.assertAlmostEqual(result["pr_auc_trapezoid"], 0.625)
        self.assertEqual(result["alerts"], 4)
        self.assertEqual((result["tp"], result["fp"], result["tn"], result["fn"]), (1, 3, 0, 0))

    def test_multiple_thresholds_integrate_precision_against_ascending_recall(self):
        # Precision-recall points are (0, 1), (0.5, 1), (0.5, 0.5),
        # (1, 2/3), and (1, 0.5); trapezoid area is 19/24.
        result = _metric([1, 0, 1, 0], [0.9, 0.8, 0.7, 0.1], 0.5)
        self.assertAlmostEqual(result["average_precision"], 5.0 / 6.0)
        self.assertAlmostEqual(result["pr_auc_trapezoid"], 19.0 / 24.0)

    def test_one_class_support_keeps_ranking_metrics_undefined(self):
        result = _metric([0, 0, 0], [0.1, 0.2, 0.3], 0.4)
        self.assertIsNone(result["average_precision"])
        self.assertIsNone(result["pr_auc_trapezoid"])
        self.assertIsNone(result["auroc"])
        self.assertIsNone(result["precision"])
        self.assertIsNone(result["recall"])
        self.assertEqual(result["f1"], 0.0)

    def test_exact_endpoint_log_loss_is_reported_as_infinite_and_clipped_separately(self):
        result = _metric([1, 0], [0.0, 1.0], 0.5)
        self.assertIsNone(result["log_loss_exact"])
        self.assertEqual(result["log_loss_exact_status"], "infinite")
        self.assertEqual(result["log_loss_exact_infinite_count"], 2)
        self.assertGreater(result["log_loss_clipped_1e-7"], 0.0)

    def test_empty_support_does_not_create_zero_skill_values(self):
        result = _metric([], [], 0.5)
        self.assertEqual(result["n"], 0)
        self.assertIsNone(result["average_precision"])
        self.assertIsNone(result["auroc"])
        self.assertIsNone(result["brier"])
        self.assertEqual(result["log_loss_exact_status"], "undefined_empty_support")

    def test_metric_comparison_rejects_changed_expected_denominator(self):
        actual = _metric([1, 0, 0], [0.9, 0.2, 0.1], 0.5)
        expected = dict(actual)
        expected["n"] += 1

        _, mismatches = _compare_metric_records(actual, expected, atol=1e-10)

        self.assertTrue(any(item.startswith("n:") for item in mismatches))

    def test_metric_comparison_rejects_changed_confusion_count(self):
        actual = _metric([1, 0, 0], [0.9, 0.8, 0.1], 0.5)
        expected = dict(actual)
        expected["fp"] += 1

        _, mismatches = _compare_metric_records(actual, expected, atol=1e-10)

        self.assertTrue(any(item.startswith("fp:") for item in mismatches))

    def test_metric_comparison_distinguishes_infinite_from_undefined_loss(self):
        actual = _metric([1], [0.0], 0.5)
        expected = dict(actual)
        expected["log_loss_exact_status"] = "undefined_empty_support"
        expected["log_loss_exact_infinite_count"] = 0
        self.assertIsNone(actual["log_loss_exact"])
        self.assertIsNone(expected["log_loss_exact"])

        _, mismatches = _compare_metric_records(actual, expected, atol=1e-10)

        self.assertTrue(
            any(item.startswith("log_loss_exact_status:") for item in mismatches)
        )
        self.assertTrue(
            any(item.startswith("log_loss_exact_infinite_count:") for item in mismatches)
        )


if __name__ == "__main__":
    unittest.main()
