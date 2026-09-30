#!/usr/bin/env python3
"""
factory/tests/test_gatekeeper_self_check.py

Unit tests for `gatekeeper.py self-check` (v1.3.4) against synthetic drift
scenarios -- a deliberately stale spec fixture for each of the four diff
targets. Per v1_3_4_candidate_spec.md section 3's stated evidence posture:
unit-tested against synthetic drift scenarios, not yet run against a real
project's document set beyond the audit that produced this release.

Run with: python3 -m pytest factory/tests/test_gatekeeper_self_check.py -v
      or: python3 -m unittest factory.tests.test_gatekeeper_self_check
"""

import importlib.util
import io
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


class SelfCheckTestCase(unittest.TestCase):
    """Each test builds a synthetic factory/ document set inside a temp
    repo root, with exactly one deliberate drift scenario planted, and
    checks that the corresponding diff target catches it."""

    def setUp(self):
        self._old_cwd = os.getcwd()
        self.tmp = tempfile.mkdtemp(prefix="gk_selfcheck_")
        os.chdir(self.tmp)
        self.gk = _load_gatekeeper()
        Path("factory").mkdir()

    def tearDown(self):
        os.chdir(self._old_cwd)
        shutil.rmtree(self.tmp, ignore_errors=True)

    def _write(self, name, content):
        self.gk.SELF_CHECK_FILES[name].write_text(content)

    def _run_self_check(self):
        buf = io.StringIO()
        with redirect_stdout(buf):
            try:
                self.gk.cmd_self_check(None)
            except SystemExit as e:
                exit_code = e.code
        return buf.getvalue(), exit_code


class TestImplementedVsSpecified(SelfCheckTestCase):
    def test_undisclosed_command_is_flagged(self):
        # A spec that never mentions "commit-project" at all -- a real
        # implemented command missing from Implementation Status.
        self._write("gatekeeper_spec", "# Implementation Status\n\nOnly snapshot is implemented.\n\n# Exit Codes\n0\n4\n6\n8\n9\n")
        findings = self.gk._self_check_implemented_vs_specified()
        joined = "\n".join(findings)
        self.assertIn("commit-project", joined)
        self.assertIn("UNDISCLOSED COMMAND", joined)

    def test_fully_disclosed_spec_produces_no_findings(self):
        text = "# Implementation Status\n\n" + "\n".join(
            f"- `{c}`" for c in self.gk.IMPLEMENTED_COMMANDS
        ) + "\n\n# Exit Codes\n" + "\n".join(str(c) for c in sorted(self.gk.IMPLEMENTED_EXIT_CODES)) + "\n"
        self._write("gatekeeper_spec", text)
        findings = self.gk._self_check_implemented_vs_specified()
        self.assertEqual(findings, [])

    def test_missing_spec_file_reported_not_crashed(self):
        # No gatekeeper_spec.md written at all.
        findings = self.gk._self_check_implemented_vs_specified()
        self.assertEqual(len(findings), 1)
        self.assertIn("CANNOT CHECK", findings[0])


class TestArtifactLifecycle(SelfCheckTestCase):
    def test_undocumented_producer_instruction_is_flagged(self):
        self._write("factory_spec", "| Artifact | Producer | Trigger | Mutability | Consumer |\n|---|---|---|---|---|\n| widget_report.md | Gemini | Phase 4 | Frozen | Claude |\n")
        self._write("gemini_spec", "This document never mentions the artifact by name.")
        self._write("claude_init", "Neither does this one.")
        findings = self.gk._self_check_artifact_lifecycle()
        joined = "\n".join(findings)
        self.assertIn("widget_report.md", joined)
        self.assertIn("NO OPERATIVE INSTRUCTION", joined)

    def test_documented_producer_instruction_is_not_flagged(self):
        self._write("factory_spec", "| Artifact | Producer | Trigger | Mutability | Consumer |\n|---|---|---|---|---|\n| widget_report.md | Gemini | Phase 4 | Frozen | Claude |\n")
        self._write("gemini_spec", "Write widget_report.md at the end of Phase 4.")
        self._write("claude_init", "")
        findings = self.gk._self_check_artifact_lifecycle()
        self.assertEqual(findings, [])


class TestVersionCurrency(SelfCheckTestCase):
    def test_stale_version_reference_is_flagged(self):
        self._write("version", "1.3.4")
        self._write("gatekeeper_spec", "Factory Version\n\n1.3.2\n")
        findings = self.gk._self_check_version_currency()
        joined = "\n".join(findings)
        self.assertIn("1.3.2", joined)
        self.assertIn("STALE VERSION REFERENCE", joined)

    def test_current_version_reference_is_not_flagged(self):
        self._write("version", "1.3.4")
        self._write("gatekeeper_spec", "Factory Version\n\n1.3.4\n")
        findings = self.gk._self_check_version_currency()
        self.assertEqual(findings, [])

    def test_missing_version_file_reported_not_crashed(self):
        findings = self.gk._self_check_version_currency()
        self.assertEqual(len(findings), 1)
        self.assertIn("CANNOT CHECK", findings[0])

    def test_constitution_and_dynamic_rules_are_monitored(self):
        # v1.4.1 -- these two were found to have drifted (stuck at 1.3.4
        # through two full release cycles) while this exact check ran
        # clean, because neither file was in SELF_CHECK_FILES at all.
        self.assertIn("constitution", self.gk.SELF_CHECK_FILES)
        self.assertIn("dynamic_rules", self.gk.SELF_CHECK_FILES)

    def test_stale_constitution_version_is_caught(self):
        self._write("version", "1.4.1")
        self._write("constitution", "**Version:** 1.3.4  \n**Status:** Active\n")
        findings = self.gk._self_check_version_currency()
        joined = "\n".join(findings)
        self.assertIn("1.3.4", joined)
        self.assertIn("STALE VERSION REFERENCE", joined)
        self.assertIn("constitution", joined)

    def test_stale_dynamic_rules_version_is_caught(self):
        self._write("version", "1.4.1")
        self._write("dynamic_rules", "# Dynamic Rules\n\nFactory Version\n\n1.3.4\n")
        findings = self.gk._self_check_version_currency()
        joined = "\n".join(findings)
        self.assertIn("1.3.4", joined)
        self.assertIn("dynamic_rules", joined)

    def test_current_constitution_version_is_not_flagged(self):
        self._write("version", "1.4.1")
        self._write("constitution", "**Version:** 1.4.1  \n**Status:** Active\n")
        findings = self.gk._self_check_version_currency()
        self.assertEqual(findings, [])


class TestNamingConventionLint(SelfCheckTestCase):
    def test_unpadded_id_in_worked_example_is_flagged(self):
        self._write("factory_spec", 'execution_order: ["C3-01", "C03-02"]\n')
        findings = self.gk._self_check_naming_convention()
        joined = "\n".join(findings)
        self.assertIn("C3-01", joined)
        self.assertIn("NAMING CONVENTION", joined)

    def test_fully_padded_ids_produce_no_findings(self):
        self._write("factory_spec", 'execution_order: ["C03-01", "C03-02"]\n')
        findings = self.gk._self_check_naming_convention()
        self.assertEqual(findings, [])


class TestSelfCheckCommandIntegration(SelfCheckTestCase):
    """End-to-end: cmd_self_check always exits 0 (diagnostic tool, never a
    gate) and prints every target's label even when a target has nothing
    to report."""

    def test_always_exits_zero_even_with_findings(self):
        self._write("gatekeeper_spec", "nothing relevant here")
        self._write("version", "0.0.1")
        output, exit_code = self._run_self_check()
        self.assertEqual(exit_code, 0, "self-check is diagnostic-only and must never fail the run.")
        self.assertIn("Total findings:", output)

    def test_prints_all_four_target_labels(self):
        output, exit_code = self._run_self_check()
        for label in [
            "Implemented vs. specified",
            "Artifact Lifecycle vs. operative instructions",
            "Version currency",
            "Naming-convention lint",
        ]:
            self.assertIn(label, output)


if __name__ == "__main__":
    unittest.main(verbosity=2)
