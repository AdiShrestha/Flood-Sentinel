#!/usr/bin/env python3
"""
factory/tests/test_gatekeeper_v1_4_2_mechanical_guards.py

Regression tests for the four v1.4.2 mechanical guards added on top of
D-028: verify-contract, lint-contract, recompute, and stamp-report/
verify-stamps. Per C14, each hard-failure test reproduces a concrete
failure shape and was confirmed failing (or crashing, for the def-main
orphan bug caught while building this) before the corresponding fix.

Run with: python3 -m pytest factory/tests/test_gatekeeper_v1_4_2_mechanical_guards.py -v
"""

import importlib.util
import io
import json
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
        self.tmp = tempfile.mkdtemp(prefix="gk_v142_mech_")
        os.chdir(self.tmp)
        Path("factory").mkdir()
        Path("factory/bootstrap_manifest.yaml").write_text("factory:\n  name: Software Factory\n")
        self.gk = _load_gatekeeper()

    def tearDown(self):
        os.chdir(self._old_cwd)
        shutil.rmtree(self.tmp, ignore_errors=True)

    def _run(self, func, **kwargs):
        buf = io.StringIO()
        args = self.gk.argparse.Namespace(**kwargs)
        exit_code = 0  # cmd_snapshot and others return normally (implicit success) on the happy path
        with redirect_stdout(buf):
            try:
                func(args)
            except SystemExit as e:
                exit_code = e.code
        return buf.getvalue(), exit_code


class TestMainIsCallable(TempRepoTestCase):
    """The orphaned-repo-root-check bug (found while building this release)
    made every subcommand run without the BUG-7 guard at all -- confirmed
    here at the subprocess/CLI level, not just the unit level, since that
    is exactly the layer the bug was invisible at when only import-time
    syntax was checked."""

    def test_main_rejects_wrong_directory_at_cli_level(self):
        empty = tempfile.mkdtemp(prefix="gk_nodir_")
        try:
            result = subprocess.run(
                [sys.executable, str(GATEKEEPER_PATH), "sort-dropbox"],
                cwd=empty, capture_output=True, text=True,
            )
            self.assertEqual(result.returncode, 9)
            self.assertIn("repository root", (result.stdout + result.stderr).lower())
        finally:
            shutil.rmtree(empty, ignore_errors=True)

    def test_verify_stamps_cli_help_does_not_crash(self):
        result = subprocess.run(
            [sys.executable, str(GATEKEEPER_PATH), "verify-stamps", "--help"],
            cwd=self.tmp, capture_output=True, text=True,
        )
        self.assertEqual(result.returncode, 0)


class TestVerifyContract(TempRepoTestCase):
    def test_passing_declared_command_exits_zero(self):
        Path("report.md").write_text(
            "## Verification\n- **Command**: `python3 -c \"exit(0)\"`\n"
        )
        out, code = self._run(self.gk.cmd_verify_contract, reports=["report.md"])
        self.assertEqual(code, 0)
        self.assertIn("PASS", out)

    def test_failing_declared_command_is_not_trusted_and_fails(self):
        # The report CLAIMS success in prose; Gatekeeper re-runs the real
        # command regardless and finds it actually fails.
        Path("report.md").write_text(
            "## Verification\n- **Command**: `python3 -c \"exit(1)\"`\n"
            "- **Output**: 236/236 passed.\n"  # the claim -- irrelevant to the real rerun
        )
        out, code = self._run(self.gk.cmd_verify_contract, reports=["report.md"])
        self.assertEqual(code, 13)
        self.assertIn("FAIL", out)

    def test_no_declared_commands_is_not_an_error(self):
        Path("report.md").write_text("## Objective\nNothing declared here.\n")
        out, code = self._run(self.gk.cmd_verify_contract, reports=["report.md"])
        self.assertEqual(code, 0)

    def test_missing_reports_argument_fails_fast(self):
        out, code = self._run(self.gk.cmd_verify_contract, reports=None)
        self.assertEqual(code, 9)


class TestLintContract(TempRepoTestCase):
    def test_swallowed_exception_is_hard_failure(self):
        Path("bad.py").write_text(
            "def f():\n"
            "    try:\n"
            "        risky()\n"
            "    except Exception:\n"
            "        return None\n"
        )
        out, code = self._run(self.gk.cmd_lint_contract, scripts=["bad.py"], contract=None)
        self.assertEqual(code, 14)
        self.assertIn("SWALLOWED EXCEPTION", out)

    def test_reraise_is_not_flagged(self):
        Path("ok.py").write_text(
            "def f():\n"
            "    try:\n"
            "        risky()\n"
            "    except Exception:\n"
            "        raise\n"
        )
        out, code = self._run(self.gk.cmd_lint_contract, scripts=["ok.py"], contract=None)
        self.assertEqual(code, 0)

    def test_logging_call_is_not_flagged(self):
        Path("ok2.py").write_text(
            "import logging\n"
            "def f():\n"
            "    try:\n"
            "        risky()\n"
            "    except Exception as e:\n"
            "        logging.exception('failed')\n"
            "        return None\n"
        )
        out, code = self._run(self.gk.cmd_lint_contract, scripts=["ok2.py"], contract=None)
        self.assertEqual(code, 0)

    def test_exemption_comment_downgrades_to_warning_not_silent_pass(self):
        Path("exempt.py").write_text(
            "def f():\n"
            "    try:\n"
            "        risky()\n"
            "    except Exception:\n"
            "        # GATEKEEPER-EXEMPT: legacy path, reviewed in C07-02\n"
            "        return None\n"
        )
        out, code = self._run(self.gk.cmd_lint_contract, scripts=["exempt.py"], contract=None)
        self.assertEqual(code, 0, "an exemption is a warning, not a hard failure")
        self.assertIn("EXEMPTED SWALLOWED EXCEPTION", out)

    def test_frozen_verification_machinery_tampering_is_caught(self):
        Path("source/tests").mkdir(parents=True)
        test_file = Path("source/tests/test_x.py")
        test_file.write_text("def test_a(): assert True\n")
        self.gk.SNAPSHOT_DIR.mkdir(parents=True, exist_ok=True)
        snap = {"contract": "C01-01", "files": {str(test_file): self.gk.sha256_of(test_file)}}
        (self.gk.SNAPSHOT_DIR / "C01-01.json").write_text(json.dumps(snap))
        test_file.write_text("def test_a(): assert False  # tampered after snapshot\n")
        out, code = self._run(self.gk.cmd_lint_contract, scripts=[], contract="C01-01")
        self.assertEqual(code, 14)

    def test_no_scripts_argument_fails_fast(self):
        out, code = self._run(self.gk.cmd_lint_contract, scripts=None, contract=None)
        self.assertEqual(code, 9)


class TestSnapshotAutoFreezesVerificationMachinery(TempRepoTestCase):
    """Confirms 'freeze all verification machinery automatically' actually
    works end-to-end: a contract never has to declare source/tests/ in
    --frozen for it to be snapshotted and later checked."""

    def test_snapshot_includes_auto_frozen_paths_without_declaring_them(self):
        Path("source/tests").mkdir(parents=True)
        Path("source/tests/test_x.py").write_text("def test_a(): assert True\n")
        out, code = self._run(self.gk.cmd_snapshot, contract="C01-01", frozen=[], force=False)
        snap = json.loads((self.gk.SNAPSHOT_DIR / "C01-01.json").read_text())
        self.assertIn("source/tests/test_x.py", snap["files"])


class TestRecompute(TempRepoTestCase):
    def _write_artifact_and_report(self, claimed_value, tolerance="0.01", indep_body=None, indep_is_copy_of_orig=False):
        Path("original.py").write_text("# original computation\nprint('{}')\n")
        if indep_is_copy_of_orig:
            shutil.copy("original.py", "independent.py")
        elif indep_body is not None:
            Path("independent.py").write_text(indep_body)
        Path("artifact.json").write_text(json.dumps({"metrics": {"auc_roc_mean": claimed_value}}))
        Path("report.md").write_text(
            "## Recompute Declaration\n"
            "original_script: original.py\n"
            "independent_script: independent.py\n"
            "artifact: artifact.json\n"
            "artifact_key: metrics.auc_roc_mean\n"
            f"tolerance: {tolerance}\n"
            "independent_command: python3 independent.py\n"
            "independent_output_key: auc_roc_mean\n"
        )

    def test_matching_independent_recomputation_passes(self):
        self._write_artifact_and_report(
            claimed_value=0.826,
            indep_body='import json; print(json.dumps({"auc_roc_mean": 0.826}))',
        )
        out, code = self._run(self.gk.cmd_recompute, reports=["report.md"])
        self.assertEqual(code, 0)
        self.assertIn("PASS", out)

    def test_mismatched_independent_recomputation_fails(self):
        self._write_artifact_and_report(
            claimed_value=0.826,
            indep_body='import json; print(json.dumps({"auc_roc_mean": 0.65}))',
        )
        out, code = self._run(self.gk.cmd_recompute, reports=["report.md"])
        self.assertEqual(code, 15)
        self.assertIn("RECOMPUTE MISMATCH", out)

    def test_identical_script_is_rejected_as_not_independent(self):
        self._write_artifact_and_report(claimed_value=0.826, indep_is_copy_of_orig=True)
        out, code = self._run(self.gk.cmd_recompute, reports=["report.md"])
        self.assertEqual(code, 15)
        self.assertIn("not independent verification", out)

    def test_missing_independent_script_fails(self):
        Path("artifact.json").write_text(json.dumps({"metrics": {"auc_roc_mean": 0.5}}))
        Path("report.md").write_text(
            "## Recompute Declaration\n"
            "original_script: original.py\n"
            "independent_script: does_not_exist.py\n"
            "artifact: artifact.json\n"
            "artifact_key: metrics.auc_roc_mean\n"
            "tolerance: 0.01\n"
            "independent_command: python3 does_not_exist.py\n"
            "independent_output_key: auc_roc_mean\n"
        )
        out, code = self._run(self.gk.cmd_recompute, reports=["report.md"])
        self.assertEqual(code, 15)

    def test_no_block_present_is_not_a_failure(self):
        Path("report.md").write_text("## Objective\nNo recompute block here.\n")
        out, code = self._run(self.gk.cmd_recompute, reports=["report.md"])
        self.assertEqual(code, 0)

    def test_missing_reports_argument_fails_fast(self):
        out, code = self._run(self.gk.cmd_recompute, reports=None)
        self.assertEqual(code, 9)


class TestStampReport(TempRepoTestCase):
    def test_first_stamp_is_appended_and_records_content_hash(self):
        Path("report.md").write_text("# Contract Report\nSome content.\n")
        out, code = self._run(self.gk.cmd_stamp_report, report="report.md", contract=None)
        text = Path("report.md").read_text()
        self.assertIn("## Gatekeeper Verification Stamp #1", text)
        self.assertIn("content_hash_sha256:", text)

    def test_tampering_above_a_stamp_is_detected_on_next_stamp_attempt(self):
        Path("report.md").write_text("# Contract Report\nOriginal content.\n")
        self._run(self.gk.cmd_stamp_report, report="report.md", contract=None)
        text = Path("report.md").read_text()
        tampered = text.replace("Original content.", "Tampered content, verdict silently changed.")
        Path("report.md").write_text(tampered)
        out, code = self._run(self.gk.cmd_stamp_report, report="report.md", contract=None)
        self.assertEqual(code, 16)
        self.assertIn("TAMPERING DETECTED", out)

    def test_untampered_report_can_be_stamped_a_second_time(self):
        Path("report.md").write_text("# Contract Report\nOriginal content.\n")
        self._run(self.gk.cmd_stamp_report, report="report.md", contract=None)
        # Legitimate amendment appended below the first stamp, exactly as
        # specified: amendments go below a stamp, not edits above it.
        with open("report.md", "a") as f:
            f.write("\n## Report Amendment\nAdditional context found after review.\n")
        out, code = self._run(self.gk.cmd_stamp_report, report="report.md", contract=None)
        self.assertEqual(code, 0)
        text = Path("report.md").read_text()
        self.assertIn("## Gatekeeper Verification Stamp #2", text)

    def test_verify_stamps_standalone_check_matches_stamp_report(self):
        Path("report.md").write_text("# Contract Report\nOriginal content.\n")
        self._run(self.gk.cmd_stamp_report, report="report.md", contract=None)
        text = Path("report.md").read_text()
        tampered = text.replace("Original content.", "Tampered.")
        Path("report.md").write_text(tampered)
        out, code = self._run(self.gk.cmd_verify_stamps, reports=["report.md"])
        self.assertEqual(code, 16)
        # verify-stamps must not itself modify the file (no side effects).
        self.assertEqual(Path("report.md").read_text(), tampered)

    def test_clean_unstamped_report_passes_verify_stamps(self):
        Path("report.md").write_text("# Contract Report\nNever stamped.\n")
        out, code = self._run(self.gk.cmd_verify_stamps, reports=["report.md"])
        self.assertEqual(code, 0)

    def test_stamp_includes_real_verify_contract_and_lint_results(self):
        # End-to-end: a report with a genuinely failing declared command
        # AND a real swallowed exception in a git-changed file must show
        # up in the stamp and the exit code, not just be silently stamped
        # over as clean.
        subprocess.run(["git", "init", "-q"], cwd=self.tmp)
        subprocess.run(["git", "config", "user.email", "a@b.c"], cwd=self.tmp)
        subprocess.run(["git", "config", "user.name", "t"], cwd=self.tmp)
        Path("bad.py").write_text(
            "def f():\n    try:\n        risky()\n    except Exception:\n        return None\n"
        )
        subprocess.run(["git", "add", "-A"], cwd=self.tmp)
        subprocess.run(["git", "commit", "-q", "-m", "init"], cwd=self.tmp)
        Path("bad.py").write_text(
            "def f():\n    try:\n        risky()\n    except Exception:\n        return None\n    # touched\n"
        )
        Path("report.md").write_text(
            "# Contract Report\n## Verification\n- **Command**: `python3 -c \"exit(1)\"`\n"
        )
        out, code = self._run(self.gk.cmd_stamp_report, report="report.md", contract=None)
        self.assertEqual(code, 14)
        text = Path("report.md").read_text()
        self.assertIn("exit code 1", text)
        self.assertIn("SWALLOWED EXCEPTION", text)


if __name__ == "__main__":
    unittest.main(verbosity=2)
