#!/usr/bin/env python3
"""
factory/tests/test_gatekeeper_v1_4_2_mandatory_gate.py

Regression tests for the v1.4.2 amendment (D-032/D-033): a T-COMP/
T-CAUSAL contract's `check` now mechanically requires Required
Verification Commands, verify-contract, lint-contract, a passing
Recompute Declaration, and an intact stamp -- not merely documentation
that the four v1.4.2 guards exist. Per C14, each hard-failure test
reproduces a concrete failure shape and was confirmed failing before the
corresponding gate logic was added.

This file is additive to test_gatekeeper_v1_4_2_mechanical_guards.py --
that file tests verify-contract/lint-contract/recompute/stamp-report as
standalone subcommands; this file tests `check`'s new tier-aware wiring
of those same underlying functions.

Run with: python3 -m pytest factory/tests/test_gatekeeper_v1_4_2_mandatory_gate.py -v
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
        self.tmp = tempfile.mkdtemp(prefix="gk_v142_gate_")
        os.chdir(self.tmp)
        Path("factory").mkdir()
        Path("factory/bootstrap_manifest.yaml").write_text("factory:\n  name: Software Factory\n")
        subprocess.run(["git", "init", "-q"], cwd=self.tmp)
        subprocess.run(["git", "config", "user.email", "t@example.com"], cwd=self.tmp)
        subprocess.run(["git", "config", "user.name", "t"], cwd=self.tmp)
        self.gk = _load_gatekeeper()

    def tearDown(self):
        os.chdir(self._old_cwd)
        shutil.rmtree(self.tmp, ignore_errors=True)

    def _run(self, func, **kwargs):
        buf = io.StringIO()
        args = self.gk.argparse.Namespace(**kwargs)
        exit_code = 0
        with redirect_stdout(buf):
            try:
                func(args)
            except SystemExit as e:
                exit_code = e.code
        return buf.getvalue(), exit_code

    def _write_manifest(self, tier, required_commands=None, contract_id="C01-01"):
        contract = {
            "id": contract_id,
            "scientific_claim_tier": tier,
        }
        if required_commands is not None:
            contract["required_verification_commands"] = required_commands
        import yaml
        data = {
            "contracts": [
                {
                    "id": contract_id,
                    "scientific_claim_tier": tier,
                    **({"required_verification_commands": required_commands}
                       if required_commands is not None else {}),
                }
            ]
        }
        Path("execution_manifest.yaml").write_text(yaml.safe_dump(data))

    def _base_check_kwargs(self, contract_id="C01-01", reports=None):
        # required_sections deliberately set to a section every fixture
        # report in this file actually has ('## Verification' or
        # '## Objective' as a bare marker) -- these tests are about the
        # v1.4.2 Mandatory Mechanical Gate, not Report Validation, so we
        # avoid DEFAULT_REQUIRED_SECTIONS (which would require
        # '## Evidence' too) tripping exit 6 and masking gate-specific
        # (exit 17) assertions. An empty list is falsy in cmd_check's
        # `args.required_sections or DEFAULT_REQUIRED_SECTIONS`, so it
        # would NOT bypass the default -- a non-empty, always-satisfied
        # override is used instead.
        return dict(
            contract=contract_id,
            manifest="execution_manifest.yaml",
            frozen=None,
            reports=reports,
            required_sections=["objective"],
            allow_dirty=True,
        )

    def _write_passing_stamped_report(self, path="contract_report.md"):
        """A report that satisfies all five gate sub-checks on its own,
        for tests that only want to flip one thing to a failure."""
        Path("indep.py").write_text('import json; print(json.dumps({"auc_roc_mean": 0.9}))\n')
        Path("orig.py").write_text("# original\nprint('0.9')\n")
        Path("artifact.json").write_text(json.dumps({"metrics": {"auc_roc_mean": 0.9}}))
        text = (
            "## Objective\n"
            "Fixture report for the Mandatory Mechanical Gate.\n\n"
            "## Verification\n"
            "- **Command**: `python3 -c \"exit(0)\"`\n\n"
            "## Recompute Declaration\n"
            "original_script: orig.py\n"
            "independent_script: indep.py\n"
            "artifact: artifact.json\n"
            "artifact_key: metrics.auc_roc_mean\n"
            "tolerance: 0.01\n"
            "independent_command: python3 indep.py\n"
            "independent_output_key: auc_roc_mean\n"
        )
        Path(path).write_text(text)
        # Stamp it for real via the actual stamping code path, so the
        # stamp's hash is genuinely valid rather than hand-authored.
        stamp_args = self.gk.argparse.Namespace(report=path, contract="C01-01")
        buf = io.StringIO()
        with redirect_stdout(buf):
            try:
                self.gk.cmd_stamp_report(stamp_args)
            except SystemExit:
                pass
        return path


class TestGateAppliesOnlyToHighTiers(TempRepoTestCase):
    def test_t_desc_contract_skips_gate_entirely(self):
        self._write_manifest("T-DESC")
        Path("contract_report.md").write_text("## Final Status\nCOMPLETE\n")
        out, code = self._run(
            self.gk.cmd_check,
            **self._base_check_kwargs(reports=["contract_report.md"]),
        )
        self.assertNotEqual(code, 17)
        self.assertIn("SKIPPED", out)

    def test_no_tier_declared_skips_gate_entirely(self):
        Path("execution_manifest.yaml").write_text(
            "contracts:\n  - id: \"C01-01\"\n"
        )
        Path("contract_report.md").write_text("## Final Status\nCOMPLETE\n")
        out, code = self._run(
            self.gk.cmd_check,
            **self._base_check_kwargs(reports=["contract_report.md"]),
        )
        self.assertNotEqual(code, 17)
        self.assertNotIn("Mandatory Mechanical Gate]", out.split("SKIPPED")[0] if "SKIPPED" in out else out)


class TestGateBlocksHighTiersWithoutEvidence(TempRepoTestCase):
    def test_t_comp_with_no_report_fails_gate(self):
        self._write_manifest("T-COMP")
        out, code = self._run(self.gk.cmd_check, **self._base_check_kwargs(reports=None))
        self.assertEqual(code, 17)
        self.assertIn("no report given", out)

    def test_t_causal_with_report_but_no_recompute_block_fails_gate(self):
        self._write_manifest("T-CAUSAL")
        Path("contract_report.md").write_text(
            "## Objective\nFixture.\n\n"
            "## Verification\n- **Command**: `python3 -c \"exit(0)\"`\n"
        )
        out, code = self._run(
            self.gk.cmd_check,
            **self._base_check_kwargs(reports=["contract_report.md"]),
        )
        self.assertEqual(code, 17)
        self.assertIn("no Recompute Declaration block present", out)

    def test_t_comp_with_no_verification_commands_fails_gate(self):
        self._write_manifest("T-COMP")
        Path("contract_report.md").write_text("## Objective\nNothing declared under Verification.\n")
        out, code = self._run(
            self.gk.cmd_check,
            **self._base_check_kwargs(reports=["contract_report.md"]),
        )
        self.assertEqual(code, 17)
        self.assertIn("no '## Verification' commands declared", out)

    def test_t_comp_with_unstamped_otherwise_complete_report_fails_gate(self):
        self._write_manifest("T-COMP")
        # Complete on everything except the stamp -- write directly rather
        # than via the stamping helper.
        Path("indep.py").write_text('import json; print(json.dumps({"auc_roc_mean": 0.9}))\n')
        Path("orig.py").write_text("# original\nprint('0.9')\n")
        Path("artifact.json").write_text(json.dumps({"metrics": {"auc_roc_mean": 0.9}}))
        Path("contract_report.md").write_text(
            "## Objective\nFixture.\n\n"
            "## Verification\n"
            "- **Command**: `python3 -c \"exit(0)\"`\n\n"
            "## Recompute Declaration\n"
            "original_script: orig.py\n"
            "independent_script: indep.py\n"
            "artifact: artifact.json\n"
            "artifact_key: metrics.auc_roc_mean\n"
            "tolerance: 0.01\n"
            "independent_command: python3 indep.py\n"
            "independent_output_key: auc_roc_mean\n"
        )
        out, code = self._run(
            self.gk.cmd_check,
            **self._base_check_kwargs(reports=["contract_report.md"]),
        )
        self.assertEqual(code, 17)
        self.assertIn("no Gatekeeper Verification Stamp present", out)


class TestGatePassesWithFullEvidence(TempRepoTestCase):
    def test_t_comp_with_full_evidence_and_stamp_passes_gate(self):
        self._write_manifest("T-COMP")
        path = self._write_passing_stamped_report()
        out, code = self._run(
            self.gk.cmd_check,
            **self._base_check_kwargs(reports=[path]),
        )
        self.assertEqual(code, 0, out)
        self.assertIn("OK", out)


class TestRequiredVerificationCommands(TempRepoTestCase):
    """D-033: the report's declared commands must include every command
    the contract froze at generation time -- verify-contract alone only
    proves *a* declared command exited 0, not that it was *the* required
    one."""

    def test_report_substituting_a_different_command_fails_gate(self):
        self._write_manifest(
            "T-COMP",
            required_commands=["pytest project/chunks/chunk01/tests/ -q"],
        )
        # Report declares a trivially-passing but different command --
        # exactly the evasion independent review raised.
        self._write_passing_stamped_report()  # sets up recompute+stamp scaffolding
        out, code = self._run(
            self.gk.cmd_check,
            **self._base_check_kwargs(reports=["contract_report.md"]),
        )
        self.assertEqual(code, 17)
        self.assertIn("Required Verification Commands", out)
        self.assertIn("missing", out)

    def test_report_declaring_the_required_command_passes_that_sub_check(self):
        required_cmd = 'python3 -c "exit(0)"'
        self._write_manifest("T-COMP", required_commands=[required_cmd])
        path = self._write_passing_stamped_report()
        out, code = self._run(
            self.gk.cmd_check,
            **self._base_check_kwargs(reports=[path]),
        )
        self.assertEqual(code, 0, out)
        self.assertIn("Required Verification Command(s) present", out)

    def test_t_comp_with_no_required_commands_declared_warns_but_does_not_hard_fail_that_subcheck(self):
        self._write_manifest("T-COMP", required_commands=[])
        path = self._write_passing_stamped_report()
        out, code = self._run(
            self.gk.cmd_check,
            **self._base_check_kwargs(reports=[path]),
        )
        # The other four sub-checks still pass, so overall gate passes,
        # but the gap is disclosed rather than silently clean.
        self.assertEqual(code, 0, out)
        self.assertIn("WARNING", out)
        self.assertIn("no Required Verification Commands", out)


class TestGateExitCodeRegistered(unittest.TestCase):
    """Exit code 17 must be in the self-check-monitored set, or self-check
    would report this release's own new exit code as undisclosed -- the
    exact class of gap D-032/D-033 exists to close for the *previous*
    review, not to reopen for this one."""

    def test_17_is_in_implemented_exit_codes(self):
        gk = _load_gatekeeper()
        self.assertIn(17, gk.IMPLEMENTED_EXIT_CODES)


if __name__ == "__main__":
    unittest.main()
