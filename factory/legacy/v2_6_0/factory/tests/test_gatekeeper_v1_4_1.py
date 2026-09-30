#!/usr/bin/env python3
"""
factory/tests/test_gatekeeper_v1_4_1.py

Regression tests for the v1.4.1 release, `gatekeeper.py evidence-check`.
Reproduces the Chunks 08-09 incident (GLOF project rework): a contract
report claimed "Verdict: SUCCESS" while its own backing JSON artifact
recorded FAILURE, and its own reported count (0 windows flagged)
logically satisfied the pre-registered FAILURE criterion, not the SUCCESS
one it claimed. Neither was caught by any verification script or by
Gatekeeper -- only by a later adversarial audit. Per the Factory's stated
practice (C14), each test reproduces the exact failure mode before the
corresponding fix landed.

Run with: python3 -m pytest factory/tests/test_gatekeeper_v1_4_1.py -v
      or: python3 factory/tests/test_gatekeeper_v1_4_1.py
"""

import importlib.util
import io
import json
import os
import shutil
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path

GATEKEEPER_PATH = Path(__file__).resolve().parent.parent / "gatekeeper.py"


def _load_gatekeeper():
    spec = importlib.util.spec_from_file_location("gatekeeper", GATEKEEPER_PATH)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


class TempRepoTestCase(unittest.TestCase):
    def setUp(self):
        self._old_cwd = os.getcwd()
        self.tmp = tempfile.mkdtemp(prefix="gk_v141_test_")
        os.chdir(self.tmp)
        Path("factory").mkdir()
        Path("factory/bootstrap_manifest.yaml").write_text("factory:\n  name: Software Factory\n")
        self.gk = _load_gatekeeper()

    def tearDown(self):
        os.chdir(self._old_cwd)
        shutil.rmtree(self.tmp, ignore_errors=True)


class TestEvidenceCheck(TempRepoTestCase):
    """Reproduces the Chunks 08-09 incident (GLOF project rework)."""

    def _run_evidence_check(self, reports=None):
        buf = io.StringIO()
        args = self.gk.argparse.Namespace(reports=reports)
        with redirect_stdout(buf):
            try:
                self.gk.cmd_evidence_check(args)
            except SystemExit as e:
                exit_code = e.code
        return buf.getvalue(), exit_code

    def _write_c08_08_fixture(self, verdict_word="SUCCESS", artifact_verdict="FAILURE",
                               windows_flagged=0, threshold=2, extra_metrics=None):
        metrics = [{"name": "Score-C AUC-ROC, 0-20% bin", "value": 1.0, "sample_count": 4}]
        if extra_metrics:
            metrics += extra_metrics
        Path("artifact.json").write_text(json.dumps({
            "f3_falsification_verdict": artifact_verdict,
            "pre_event_windows_flagged": windows_flagged,
            "metrics": metrics,
        }))
        Path("report.md").write_text(
            "## Evidence\n"
            f"Verdict: {verdict_word}\n\n"
            "## Verdict Cross-Check\n"
            f"verdict_word: {verdict_word}\n"
            "artifact: artifact.json\n"
            "artifact_key: f3_falsification_verdict\n"
            "criterion: count_gte\n"
            "criterion_field: pre_event_windows_flagged\n"
            f"criterion_threshold: {threshold}\n"
        )

    def test_verdict_mismatch_against_artifact_is_flagged(self):
        self._write_c08_08_fixture(verdict_word="SUCCESS", artifact_verdict="FAILURE")
        output, exit_code = self._run_evidence_check(reports=["report.md"])
        self.assertEqual(exit_code, 12, "A verdict/artifact mismatch must produce exit code 12.")
        self.assertIn("VERDICT MISMATCH", output)

    def test_logical_inconsistency_zero_windows_success_is_flagged(self):
        self._write_c08_08_fixture(verdict_word="SUCCESS", artifact_verdict="SUCCESS",
                                    windows_flagged=0, threshold=2)
        output, exit_code = self._run_evidence_check(reports=["report.md"])
        self.assertEqual(exit_code, 12)
        self.assertIn("LOGICAL INCONSISTENCY", output)
        self.assertIn("NOT SATISFIED", output)

    def test_consistent_failure_verdict_passes_both_checks(self):
        self._write_c08_08_fixture(verdict_word="FAILURE", artifact_verdict="FAILURE",
                                    windows_flagged=0, threshold=2)
        output, exit_code = self._run_evidence_check(reports=["report.md"])
        self.assertEqual(exit_code, 0)
        self.assertIn("No mismatches found.", output)

    def test_consistent_success_with_sufficient_windows_passes(self):
        self._write_c08_08_fixture(verdict_word="SUCCESS", artifact_verdict="SUCCESS",
                                    windows_flagged=3, threshold=2)
        output, exit_code = self._run_evidence_check(reports=["report.md"])
        self.assertEqual(exit_code, 0)

    def test_degenerate_metric_on_small_sample_is_warning_not_failure(self):
        self._write_c08_08_fixture(verdict_word="FAILURE", artifact_verdict="FAILURE",
                                    windows_flagged=0, threshold=2)
        output, exit_code = self._run_evidence_check(reports=["report.md"])
        self.assertEqual(
            exit_code, 0,
            "A degenerate metric is a WARNING, not a hard failure -- it may still be genuine."
        )
        self.assertIn("DEGENERATE METRIC", output)
        self.assertIn("4 samples", output)

    def test_same_boundary_value_on_large_sample_is_not_flagged(self):
        self._write_c08_08_fixture(
            verdict_word="FAILURE", artifact_verdict="FAILURE", windows_flagged=0, threshold=2,
            extra_metrics=[{"name": "Score-C AUC-ROC, large bin", "value": 1.0, "sample_count": 200}],
        )
        output, exit_code = self._run_evidence_check(reports=["report.md"])
        # only the small-sample metric (4 samples) should be flagged, not the 200-sample one
        self.assertEqual(output.count("DEGENERATE METRIC"), 1)

    def test_report_with_no_verdict_block_is_silently_skipped_not_passed(self):
        Path("report.md").write_text("## Evidence\nNothing structured here.\n")
        output, exit_code = self._run_evidence_check(reports=["report.md"])
        self.assertEqual(exit_code, 0)
        self.assertIn("No mismatches found.", output)

    def test_malformed_verdict_block_is_reported(self):
        Path("report.md").write_text(
            "## Verdict Cross-Check\nverdict_word: SUCCESS\n"  # missing artifact, artifact_key
        )
        output, exit_code = self._run_evidence_check(reports=["report.md"])
        self.assertEqual(exit_code, 12)
        self.assertIn("MALFORMED VERDICT BLOCK", output)

    def test_no_reports_argument_fails_fast(self):
        output, exit_code = self._run_evidence_check(reports=None)
        self.assertEqual(exit_code, 9)

    def test_missing_artifact_reported_not_crashed(self):
        Path("report.md").write_text(
            "## Verdict Cross-Check\n"
            "verdict_word: SUCCESS\n"
            "artifact: does_not_exist.json\n"
            "artifact_key: verdict\n"
        )
        output, exit_code = self._run_evidence_check(reports=["report.md"])
        self.assertIn("CANNOT CHECK", output)

    def test_missing_artifact_key_reported_not_crashed(self):
        Path("artifact.json").write_text(json.dumps({"unrelated_key": "value"}))
        Path("report.md").write_text(
            "## Verdict Cross-Check\n"
            "verdict_word: SUCCESS\n"
            "artifact: artifact.json\n"
            "artifact_key: verdict\n"
        )
        output, exit_code = self._run_evidence_check(reports=["report.md"])
        self.assertIn("CANNOT CHECK", output)

    def test_bool_true_criterion_kind(self):
        Path("artifact.json").write_text(json.dumps({
            "verdict": "SUCCESS", "detected": True, "metrics": [],
        }))
        Path("report.md").write_text(
            "## Verdict Cross-Check\n"
            "verdict_word: SUCCESS\n"
            "artifact: artifact.json\n"
            "artifact_key: verdict\n"
            "criterion: bool_true\n"
            "criterion_field: detected\n"
            "criterion_threshold: 0\n"
        )
        output, exit_code = self._run_evidence_check(reports=["report.md"])
        self.assertEqual(exit_code, 0)

    def test_multiple_reports_in_one_run(self):
        os.mkdir("c1")
        os.mkdir("c2")
        Path("c1/artifact.json").write_text(json.dumps({"verdict": "SUCCESS", "metrics": []}))
        Path("c1/report.md").write_text(
            "## Verdict Cross-Check\nverdict_word: SUCCESS\nartifact: c1/artifact.json\nartifact_key: verdict\n"
        )
        Path("c2/artifact.json").write_text(json.dumps({"verdict": "FAILURE", "metrics": []}))
        Path("c2/report.md").write_text(
            "## Verdict Cross-Check\nverdict_word: SUCCESS\nartifact: c2/artifact.json\nartifact_key: verdict\n"
        )
        output, exit_code = self._run_evidence_check(reports=["c1/report.md", "c2/report.md"])
        self.assertEqual(exit_code, 12)
        self.assertIn("c2/report.md", output)


if __name__ == "__main__":
    unittest.main(verbosity=2)
