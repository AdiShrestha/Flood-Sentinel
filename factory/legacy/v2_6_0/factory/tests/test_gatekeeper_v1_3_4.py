#!/usr/bin/env python3
"""
factory/tests/test_gatekeeper_v1_3_4.py

Regression tests for the v1.3.4 patch release. Each test reproduces the
exact failure mode described in v1_3_4_candidate_spec.md section 1, and
was committed failing (red) before the corresponding fix landed, per the
Factory's stated practice of writing the failing case first (C14).

Run with: python3 -m pytest factory/tests/test_gatekeeper_v1_3_4.py -v
      or: python3 factory/tests/test_gatekeeper_v1_3_4.py
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
    """Runs each test inside a fresh temp directory acting as repo root,
    so path-relative gatekeeper.py behavior (DROP_HERE/, project/, etc.)
    doesn't collide across tests or touch the real filesystem."""

    def setUp(self):
        self._old_cwd = os.getcwd()
        self.tmp = tempfile.mkdtemp(prefix="gk_test_")
        os.chdir(self.tmp)
        self.gk = _load_gatekeeper()

    def tearDown(self):
        os.chdir(self._old_cwd)
        shutil.rmtree(self.tmp, ignore_errors=True)


class TestBug1ParserScope(TempRepoTestCase):
    """BUG-1a/1b: parse_contract_status must not read past the Final
    Status section, and must not match "COMPLETE" as a substring of
    "INCOMPLETE"."""

    def test_status_word_in_remaining_risks_not_matched(self):
        report = Path("contract_report.md")
        report.write_text(
            "## Final Status\n"
            "COMPLETE\n\n"
            "## Remaining Risks\n"
            "None known. Earlier in the chunk one contract was reported as "
            "BLOCKED — CARRIED FORWARD in prose here, but that was resolved.\n"
        )
        status = self.gk.parse_contract_status(report)
        self.assertEqual(
            status, "complete",
            "Final Status was COMPLETE; a later section merely mentioning "
            "'BLOCKED — CARRIED FORWARD' in prose must not override it."
        )

    def test_incomplete_not_matched_as_complete(self):
        report = Path("contract_report.md")
        report.write_text("## Final Status\nINCOMPLETE\n")
        status = self.gk.parse_contract_status(report)
        self.assertEqual(
            status, "unknown",
            "'INCOMPLETE' must not be matched by the bare 'COMPLETE' substring pattern."
        )


class TestBug2ContractIdPadding(TempRepoTestCase):
    """BUG-2: cmd_next's report-path lookup and cmd_check's required_reports
    resolution must fall back between padded and as-given contract IDs,
    the same way _find_contract_file already does."""

    def test_shared_helper_generates_padded_and_asgiven_candidates(self):
        # After the fix, a shared helper should exist and be usable
        # independently of _find_contract_file.
        self.assertTrue(
            hasattr(self.gk, "_contract_id_candidates"),
            "Expected a shared _contract_id_candidates(contract_id) helper "
            "factored out of _find_contract_file, per v1.3.4 spec section 1.2."
        )
        _, _, candidates = self.gk._contract_id_candidates("C1-3")
        candidates = set(candidates)
        self.assertIn("C1-3", candidates)
        self.assertIn("C01-03", candidates)

    def test_next_finds_unpadded_report_path_via_fallback(self):
        # Manifest uses unpadded id "C1-3"; report is filed at the unpadded
        # path. cmd_next must still find it instead of reporting
        # not_started forever.
        manifest = Path("execution_manifest.yaml")
        manifest.write_text(
            "contracts:\n"
            "  - id: \"C1-3\"\n"
            "    risk_tier: Low\n"
            "execution_order:\n"
            "  - \"C1-3\"\n"
        )
        reports_dir = Path("reports")
        report_dir = reports_dir / "C1-3"
        report_dir.mkdir(parents=True)
        (report_dir / "contract_report.md").write_text("## Final Status\nCOMPLETE\n")

        buf = io.StringIO()
        args = self.gk.argparse.Namespace(
            manifest=str(manifest), reports_dir=str(reports_dir)
        )
        with redirect_stdout(buf):
            try:
                self.gk.cmd_next(args)
            except SystemExit as e:
                exit_code = e.code
        self.assertEqual(exit_code, 0)
        self.assertIn("complete", buf.getvalue())


class TestBug3ReportHeaderCheck(TempRepoTestCase):
    """BUG-3: Report Validation must match required sections as exact
    header lines, not as raw substrings anywhere in the file."""

    def test_prose_mention_does_not_satisfy_header_requirement(self):
        report = Path("contract_report.md")
        report.write_text(
            "## Objective\nDo the thing.\n\n"
            "## Notes\n"
            "No verification was possible in this environment.\n\n"
            "## Evidence\nSee attached.\n"
        )
        ok, details = self.gk.check_reports(
            [str(report)], ["objective", "verification", "evidence"]
        )
        self.assertFalse(
            ok,
            "A report with no '## Verification' header must fail even "
            "though the word 'verification' appears in prose."
        )

    def test_real_header_satisfies_requirement(self):
        report = Path("contract_report.md")
        report.write_text(
            "## Objective\nDo the thing.\n\n"
            "## Verification Summary\nAll checks passed.\n\n"
            "## Evidence\nSee attached.\n"
        )
        ok, details = self.gk.check_reports(
            [str(report)], ["objective", "verification", "evidence"]
        )
        self.assertTrue(ok, f"Expected PASS with real headers present. Details: {details}")


class TestBug4DroppedDirectoriesVisible(TempRepoTestCase):
    """BUG-4: a directory dropped into DROP_HERE/ must be reported, not
    silently excluded from every category."""

    def test_directory_in_dropbox_is_reported(self):
        dropbox = Path("DROP_HERE")
        dropbox.mkdir()
        (dropbox / "dropbox_manifest.json").write_text(json.dumps({
            "rules": [{"pattern": r"^chunk(\d+)\.md$", "destination": "project/chunks/chunk{1}/chunk{1}.md"}],
            "entries": [],
        }))
        (dropbox / "some_folder").mkdir()

        buf = io.StringIO()
        args = self.gk.argparse.Namespace(force=False, manifest=None)
        with redirect_stdout(buf):
            try:
                self.gk.cmd_sort_dropbox(args)
            except SystemExit:
                pass
        output = buf.getvalue()
        self.assertIn(
            "some_folder", output,
            "A dropped directory must appear somewhere in sort-dropbox's output, "
            "not vanish silently."
        )
        self.assertIn(
            "SKIPPED - NOT A FILE", output,
            "Dropped directories should be reported under a distinct "
            "[SKIPPED - NOT A FILE] category per v1.3.4 spec section 1.4."
        )


class TestBug6CompositeFailureCategories(TempRepoTestCase):
    """BUG-6: when more than one check category fails, the exit code stays
    the first-failing code (documented contract, unchanged), but a summary
    line must list every failing category."""

    def test_multiple_failure_categories_all_listed(self):
        # Frozen file check fails (missing snapshot file still passes-by-
        # omission per existing behavior, so force a real hash mismatch)
        # and report check fails (missing report) simultaneously.
        frozen_file = Path("src/frozen.py")
        frozen_file.parent.mkdir(parents=True)
        frozen_file.write_text("v1")

        self.gk.SNAPSHOT_DIR.mkdir(parents=True, exist_ok=True)
        snap = {"contract": "C01-01", "files": {"src/frozen.py": "0" * 64}}
        (self.gk.SNAPSHOT_DIR / "C01-01.json").write_text(json.dumps(snap))

        buf = io.StringIO()
        args = self.gk.argparse.Namespace(
            contract="C01-01",
            manifest=None,
            frozen=["src/frozen.py"],
            reports=["reports/does_not_exist.md"],
            required_sections=None,
            allow_dirty=True,
        )
        with redirect_stdout(buf):
            try:
                self.gk.cmd_check(args)
            except SystemExit as e:
                exit_code = e.code

        output = buf.getvalue()
        self.assertNotEqual(exit_code, 0)
        self.assertIn(
            "Failure categories:", output,
            "Composite failures across more than one category must print a "
            "summary line naming every failing category, per v1.3.4 spec section 1.5."
        )
        self.assertIn("frozen_file", output)
        self.assertIn("report", output)


class TestBug7RepoRootResolution(TempRepoTestCase):
    """BUG-7: running gatekeeper.py from the wrong directory must fail
    fast with a clear error instead of silently resolving paths wrong.
    Checks for factory/bootstrap_manifest.yaml specifically -- that is
    where the file actually lives in a real bootstrapped repo (per
    bootstrap_manifest.yaml's own copy_factory_files list), not at the
    repo root directly. A v1.4.0 fix: the original v1.3.4 check looked
    for a bare bootstrap_manifest.yaml at cwd, which does not exist in
    any real bootstrapped project and would have failed this check
    permanently."""

    def test_main_rejects_wrong_directory(self):
        # No factory/bootstrap_manifest.yaml in this tmp dir -- simulates
        # running from the wrong cwd.
        result = subprocess.run(
            [sys.executable, str(GATEKEEPER_PATH), "sort-dropbox"],
            cwd=self.tmp,
            capture_output=True,
            text=True,
        )
        self.assertEqual(result.returncode, 9)
        self.assertIn("repository root", (result.stdout + result.stderr).lower())

    def test_main_proceeds_when_bootstrap_manifest_present(self):
        Path("factory").mkdir()
        Path("factory/bootstrap_manifest.yaml").write_text("factory:\n  name: Software Factory\n")
        result = subprocess.run(
            [sys.executable, str(GATEKEEPER_PATH), "sort-dropbox"],
            cwd=self.tmp,
            capture_output=True,
            text=True,
        )
        # Should get past the root check and fail for a *different* reason
        # (no DROP_HERE/), not the root-resolution error.
        self.assertNotIn("must be run from the repository root", result.stdout + result.stderr)

    def test_bare_root_level_manifest_is_not_sufficient(self):
        # A bootstrap_manifest.yaml sitting at cwd root directly (the old,
        # wrong v1.3.4 check's target) must NOT satisfy the check -- that
        # is not where a real bootstrapped repo puts it.
        Path("bootstrap_manifest.yaml").write_text("factory:\n  name: Software Factory\n")
        result = subprocess.run(
            [sys.executable, str(GATEKEEPER_PATH), "sort-dropbox"],
            cwd=self.tmp,
            capture_output=True,
            text=True,
        )
        self.assertEqual(result.returncode, 9)
        self.assertIn("repository root", (result.stdout + result.stderr).lower())


if __name__ == "__main__":
    unittest.main(verbosity=2)
