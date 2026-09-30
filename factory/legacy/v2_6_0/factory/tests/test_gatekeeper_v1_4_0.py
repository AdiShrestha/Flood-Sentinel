#!/usr/bin/env python3
"""
factory/tests/test_gatekeeper_v1_4_0.py

Regression tests for the v1.4.0 release, `gatekeeper.py release-check`.
Each test reproduces a specific, named finding from the GLOF IEEE TGRS
peer review that motivated this command (m6: local path leaked into
REPRODUCIBILITY.md; M3: fatality-count discrepancy between the manuscript
and project_knowledge.md), per the Factory's stated practice of writing
the failing case first (C14).

Run with: python3 -m pytest factory/tests/test_gatekeeper_v1_4_0.py -v
      or: python3 factory/tests/test_gatekeeper_v1_4_0.py
"""

import importlib.util
import io
import os
import shutil
import subprocess
import sys
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
        self.tmp = tempfile.mkdtemp(prefix="gk_v140_test_")
        os.chdir(self.tmp)
        Path("factory").mkdir()
        Path("factory/bootstrap_manifest.yaml").write_text("factory:\n  name: Software Factory\n")
        self.gk = _load_gatekeeper()

    def tearDown(self):
        os.chdir(self._old_cwd)
        shutil.rmtree(self.tmp, ignore_errors=True)

    def _run_release_check(self, manuscript, files=None, key_facts=None):
        buf = io.StringIO()
        args = self.gk.argparse.Namespace(
            manuscript=manuscript, files=files, key_facts=key_facts
        )
        with redirect_stdout(buf):
            try:
                self.gk.cmd_release_check(args)
            except SystemExit as e:
                exit_code = e.code
        return buf.getvalue(), exit_code


class TestLocalPathLeak(TempRepoTestCase):
    """Reproduces review finding m6: a personal machine path leaked into a
    release artifact."""

    def test_users_path_is_flagged_and_fails(self):
        Path("REPRODUCIBILITY.md").write_text(
            "Checkpoint at /Users/adi/Desktop/Computer_Vision/checkpoints/ts_mae_best.pt\n"
        )
        output, exit_code = self._run_release_check(
            manuscript="REPRODUCIBILITY.md"
        )
        self.assertEqual(exit_code, 10, "A local path leak must produce exit code 10 (Release Artifact Failure).")
        self.assertIn("LOCAL PATH LEAK", output)
        self.assertIn("/Users/adi", output)

    def test_repository_relative_path_is_not_flagged(self):
        Path("REPRODUCIBILITY.md").write_text(
            "Checkpoint at models/checkpoints/ts_mae_best.pt\n"
        )
        output, exit_code = self._run_release_check(manuscript="REPRODUCIBILITY.md")
        self.assertEqual(exit_code, 0)
        self.assertIn("No local paths found.", output)

    def test_additional_files_are_also_scanned(self):
        Path("manuscript.md").write_text("Clean manuscript, no paths.\n")
        Path("REPRODUCIBILITY.md").write_text("See /home/adi/models/ckpt.pt\n")
        output, exit_code = self._run_release_check(
            manuscript="manuscript.md", files=["REPRODUCIBILITY.md"]
        )
        self.assertEqual(exit_code, 10)
        self.assertIn("REPRODUCIBILITY.md", output)
        self.assertIn("LOCAL PATH LEAK", output)


class TestKeyFactConsistency(TempRepoTestCase):
    """Reproduces review finding M3: a 10x fatality-count discrepancy
    between the manuscript and the project's own knowledge base."""

    def test_mismatched_fact_is_flagged_as_warning_not_failure(self):
        Path("key_facts.md").write_text(
            "## Key Fact: South Lhonak fatality count\n"
            "anchor: fatalities\n"
            "expected_value: 55\n"
            "tolerance: 5\n"
        )
        Path("manuscript.md").write_text(
            "The 2023 South Lhonak GLOF resulted in 7 fatalities.\n"
        )
        output, exit_code = self._run_release_check(
            manuscript="manuscript.md", key_facts="key_facts.md"
        )
        self.assertEqual(
            exit_code, 0,
            "A key-fact mismatch is a WARNING per the Factory's Warning Policy, "
            "not a hard failure -- it requires human confirmation, since two "
            "genuinely distinct quantities can share an anchor word."
        )
        self.assertIn("KEY FACT MISMATCH", output)
        self.assertIn("'7'", output)
        self.assertIn("55.0", output)

    def test_matching_fact_within_tolerance_is_not_flagged(self):
        Path("key_facts.md").write_text(
            "## Key Fact: South Lhonak fatality count\n"
            "anchor: fatalities\n"
            "expected_value: 55\n"
            "tolerance: 5\n"
        )
        Path("manuscript.md").write_text(
            "Approximately 53 fatalities were reported.\n"
        )
        output, exit_code = self._run_release_check(
            manuscript="manuscript.md", key_facts="key_facts.md"
        )
        self.assertEqual(exit_code, 0)
        self.assertIn("No mismatches found", output)

    def test_anchor_not_mentioned_is_silently_fine(self):
        Path("key_facts.md").write_text(
            "## Key Fact: South Lhonak fatality count\n"
            "anchor: fatalities\n"
            "expected_value: 55\n"
            "tolerance: 5\n"
        )
        Path("manuscript.md").write_text("This manuscript never discusses casualties.\n")
        output, exit_code = self._run_release_check(
            manuscript="manuscript.md", key_facts="key_facts.md"
        )
        self.assertEqual(exit_code, 0)
        self.assertIn("No mismatches found", output)

    def test_malformed_key_fact_block_is_reported_not_silently_dropped(self):
        Path("key_facts.md").write_text(
            "## Key Fact: incomplete block\n"
            "anchor: something\n"
        )
        Path("manuscript.md").write_text("Irrelevant content.\n")
        output, exit_code = self._run_release_check(
            manuscript="manuscript.md", key_facts="key_facts.md"
        )
        self.assertIn("MALFORMED KEY FACT", output)

    def test_key_facts_omitted_skips_cleanly(self):
        Path("manuscript.md").write_text("Anything at all.\n")
        output, exit_code = self._run_release_check(manuscript="manuscript.md", key_facts=None)
        self.assertEqual(exit_code, 0)
        self.assertIn("SKIPPED: no --key-facts given.", output)


class TestMissingManuscript(TempRepoTestCase):
    def test_missing_manuscript_fails_fast_does_not_report_clean(self):
        output, exit_code = self._run_release_check(manuscript="does_not_exist.md")
        self.assertEqual(
            exit_code, 9,
            "A missing --manuscript must fail fast (exit 9), not silently "
            "report zero failures -- that would be indistinguishable from a "
            "genuine clean pass."
        )
        self.assertIn("does not exist", output)


class TestBothChecksTogether(TempRepoTestCase):
    """End-to-end: reproduces both GLOF findings (m6 + M3) in a single run,
    the way a real pre-submission release-check would encounter them."""

    def test_glof_review_findings_reproduced_together(self):
        Path("key_facts.md").write_text(
            "## Key Fact: South Lhonak fatality count\n"
            "anchor: fatalities\n"
            "expected_value: 55\n"
            "tolerance: 5\n"
        )
        Path("manuscript.md").write_text(
            "The disaster caused 7 fatalities.\n"
            "See /Users/adi/Desktop/Computer_Vision/checkpoints/ts_mae_best.pt\n"
        )
        output, exit_code = self._run_release_check(
            manuscript="manuscript.md", key_facts="key_facts.md"
        )
        self.assertEqual(exit_code, 10, "The local-path failure must dominate the exit code.")
        self.assertIn("LOCAL PATH LEAK", output)
        self.assertIn("KEY FACT MISMATCH", output)
        self.assertIn("Failures: 1", output)
        self.assertIn("Warnings: 1", output)


class TestReleaseCheckCLIIntegration(TempRepoTestCase):
    """End-to-end via subprocess, exercising the real argparse wiring."""

    def test_cli_invocation_matches_exit_code(self):
        Path("manuscript.md").write_text("/Users/adi/leak.txt\n")
        result = subprocess.run(
            [sys.executable, str(GATEKEEPER_PATH), "release-check", "--manuscript", "manuscript.md"],
            cwd=self.tmp, capture_output=True, text=True,
        )
        self.assertEqual(result.returncode, 10)
        self.assertIn("LOCAL PATH LEAK", result.stdout)


class TestAcquisitionAudit(TempRepoTestCase):
    """Reproduces the Chunk 07 incident (GLOF project rework): an
    acquisition script defining generate_fallback_timeseries, called when
    the target API was unreachable, whose report used the word
    'synthesize'."""

    def _run_acquisition_audit(self, scripts=None, reports=None):
        buf = io.StringIO()
        args = self.gk.argparse.Namespace(scripts=scripts, reports=reports)
        with redirect_stdout(buf):
            try:
                self.gk.cmd_acquisition_audit(args)
            except SystemExit as e:
                exit_code = e.code
        return buf.getvalue(), exit_code

    def test_generate_fallback_function_is_flagged_and_fails(self):
        Path("acquire.py").write_text(
            "import ee\n\n"
            "def acquire_backscatter(lake_id):\n"
            "    return ee.ImageCollection('COPERNICUS/S1_GRD')\n\n"
            "def generate_fallback_timeseries(lake_id):\n"
            "    return {'synthesized': True}\n"
        )
        output, exit_code = self._run_acquisition_audit(scripts=["acquire.py"])
        self.assertEqual(exit_code, 11, "A data-generation function definition must produce exit code 11.")
        self.assertIn("DATA-GENERATION FUNCTION", output)
        self.assertIn("generate_", output)
        self.assertIn("acquire.py:5", output)

    def test_clean_acquisition_script_passes(self):
        Path("acquire.py").write_text(
            "import ee\n\n"
            "def acquire_backscatter(lake_id):\n"
            "    return ee.ImageCollection('COPERNICUS/S1_GRD').filterBounds(lake_id)\n"
        )
        output, exit_code = self._run_acquisition_audit(scripts=["acquire.py"])
        self.assertEqual(exit_code, 0)
        self.assertIn("No data-generation function definitions found.", output)
        self.assertIn("No simulation-indicating language found.", output)

    def test_synthesize_in_report_is_warning_not_failure(self):
        Path("report.md").write_text(
            "## Evidence\nGEE API was unreachable, so we synthesize a fallback timeseries "
            "with realistic monsoon gap patterns.\n"
        )
        output, exit_code = self._run_acquisition_audit(reports=["report.md"])
        self.assertEqual(
            exit_code, 0,
            "Simulation-indicating text alone is a WARNING per the Warning Policy -- it "
            "requires human confirmation, since some matches are legitimate."
        )
        self.assertIn("SIMULATION-INDICATING LANGUAGE", output)
        self.assertIn("synthesize", output)

    def test_legitimate_word_use_is_still_reported_for_human_judgement(self):
        # "generated thumbnail" is a legitimate use -- the check still
        # surfaces it (heuristic, bounded), it just isn't a hard failure.
        Path("report.md").write_text("## Notes\nWe generated a thumbnail preview for the UI.\n")
        output, exit_code = self._run_acquisition_audit(reports=["report.md"])
        self.assertEqual(exit_code, 0)
        self.assertIn("SIMULATION-INDICATING LANGUAGE", output)

    def test_no_arguments_fails_fast(self):
        output, exit_code = self._run_acquisition_audit()
        self.assertEqual(exit_code, 9)
        self.assertIn("at least one of --scripts or --reports", output)

    def test_missing_script_reported_not_crashed(self):
        output, exit_code = self._run_acquisition_audit(scripts=["does_not_exist.py"])
        self.assertEqual(exit_code, 0)
        self.assertIn("CANNOT CHECK", output)

    def test_both_checks_together_reproduce_chunk_07(self):
        Path("acquire.py").write_text(
            "def generate_fallback_timeseries(lake_id):\n"
            "    return {'synthesized': True}\n"
        )
        Path("report.md").write_text(
            "## Evidence\nWe synthesize a fallback timeseries.\n"
        )
        output, exit_code = self._run_acquisition_audit(scripts=["acquire.py"], reports=["report.md"])
        self.assertEqual(exit_code, 11)
        self.assertIn("DATA-GENERATION FUNCTION", output)
        self.assertIn("SIMULATION-INDICATING LANGUAGE", output)
        self.assertIn("Failures: 1", output)


if __name__ == "__main__":
    unittest.main(verbosity=2)
