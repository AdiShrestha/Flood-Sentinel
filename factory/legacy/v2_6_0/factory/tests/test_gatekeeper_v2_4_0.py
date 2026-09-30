#!/usr/bin/env python3
"""
factory/tests/test_gatekeeper_v2_4_0.py

Regression tests for the v2.4.0 additions: two new WARNING-only heuristics
bundled into `tier-check` per C46 (no new subcommands) -- ablation-row
covariance (D-054, candidate) and efficiency-claim measurement language
(D-055, candidate). Both are PROPOSED, not ACTIVE, per dynamic_rules.md's
v2.4.0 entries: their evidence is a single repo-grounded third-party gap
analysis (comparing this Factory against an external pre-submission audit
manual), not this Factory's own field use across completed projects. Per
C14, each flagged-case test also has a matching not-flagged-case test so
the heuristic's actual discrimination is exercised, not just its trigger.

Run with: python3 -m pytest factory/tests/test_gatekeeper_v2_4_0.py -v
(from the repository root -- see TierCheckCommandV24Tests below for why.)
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


class AblationRowCovarianceTests(unittest.TestCase):
    """D-054 (candidate): an ablation mentioned alongside language that
    could describe a covarying factor, with no held-fixed/parameter-matched
    declaration anywhere in the text, should flag. Any of the three
    ingredients missing should not."""

    def setUp(self):
        self.gk = _load_gatekeeper()

    def test_ablation_with_covarying_factor_and_no_mitigation_flagged(self):
        text = (
            "## Objective\nRun an ablation removing the topological feature "
            "branch and report accuracy.\n\n## Context\nThis reduces the "
            "number of parameters in the model since the branch is gone.\n"
        )
        findings = self.gk._scan_ablation_row_covariance(text)
        self.assertTrue(any("ABLATION FACTOR COVARIANCE NOT ADDRESSED" in f for f in findings))

    def test_ablation_with_held_fixed_declaration_not_flagged(self):
        text = (
            "## Objective\nRun an ablation removing the topological feature "
            "branch, holding parameter count fixed by padding the remaining "
            "branch, and report accuracy.\n\n## Context\nParameter count is "
            "held fixed between the baseline and ablated variant.\n"
        )
        findings = self.gk._scan_ablation_row_covariance(text)
        self.assertEqual(findings, [])

    def test_ablation_with_no_covarying_factor_language_not_flagged(self):
        text = (
            "## Objective\nRun an ablation removing the topological feature "
            "branch and report accuracy on the held-out test set.\n"
        )
        findings = self.gk._scan_ablation_row_covariance(text)
        self.assertEqual(findings, [])

    def test_covarying_factor_language_without_any_ablation_not_flagged(self):
        text = (
            "## Objective\nTrain the model and report the final parameter "
            "count and training steps used.\n"
        )
        findings = self.gk._scan_ablation_row_covariance(text)
        self.assertEqual(findings, [])

    def test_no_ablation_and_no_covariance_language_not_flagged(self):
        text = "## Objective\nImplement a CSV parser for the raw transaction log.\n"
        findings = self.gk._scan_ablation_row_covariance(text)
        self.assertEqual(findings, [])


class EfficiencyClaimMeasurementTests(unittest.TestCase):
    """D-055 (candidate): an efficiency/real-time/latency claim reported
    with mean-only latency language and no percentile language anywhere
    should flag. Percentile language present, or no efficiency claim at
    all, should not."""

    def setUp(self):
        self.gk = _load_gatekeeper()

    def test_realtime_claim_with_mean_only_latency_flagged(self):
        text = (
            "## Objective\nDemonstrate the real-time latency of the "
            "backpressure pipeline under load.\n\n## Context\nWe report the "
            "average latency of the pipeline across all test runs.\n"
        )
        findings = self.gk._scan_efficiency_claim_measurement(text)
        self.assertTrue(any("MEAN-ONLY LATENCY FOR AN EFFICIENCY CLAIM" in f for f in findings))

    def test_realtime_claim_with_percentile_latency_not_flagged(self):
        text = (
            "## Objective\nDemonstrate the real-time latency of the "
            "backpressure pipeline under load.\n\n## Context\nWe report "
            "p50/p90/p99 latency percentiles across all test runs.\n"
        )
        findings = self.gk._scan_efficiency_claim_measurement(text)
        self.assertEqual(findings, [])

    def test_realtime_claim_with_both_mean_and_percentile_not_flagged(self):
        # Reporting a mean alongside a percentile distribution is exactly
        # what domain_checklists.md asks for -- the mean is not itself the
        # problem, an unaccompanied mean is.
        text = (
            "## Context\nAverage latency was 12ms; the full distribution "
            "(p50/p90/p99) is reported in Table 3.\n"
        )
        findings = self.gk._scan_efficiency_claim_measurement(text)
        self.assertEqual(findings, [])

    def test_no_efficiency_claim_language_not_flagged(self):
        text = "## Context\nWe report the average accuracy across five folds.\n"
        findings = self.gk._scan_efficiency_claim_measurement(text)
        self.assertEqual(findings, [])

    def test_efficiency_claim_with_neither_mean_nor_percentile_not_flagged(self):
        # Presence-only heuristic (like D-037): silence is not itself a
        # violation of this specific pattern -- there is nothing here to
        # contradict, only nothing to confirm. See domain_checklists.md.
        text = "## Objective\nBuild a lightweight real-time monitoring dashboard.\n"
        findings = self.gk._scan_efficiency_claim_measurement(text)
        self.assertEqual(findings, [])


class TierCheckCommandV24Tests(unittest.TestCase):
    """Exercises cmd_tier_check end-to-end: confirms the two new sections
    appear in output and, critically, that neither can affect the exit
    code -- D-054/D-055 are WARNING-only by design (factory_spec.md's
    Fail-Closed Tier Inference section), so a contract that would otherwise
    pass tier-check must still exit 0 even when both heuristics fire."""

    def setUp(self):
        self._old_cwd = os.getcwd()
        self.tmp = tempfile.mkdtemp(prefix="gk_v240_tiercheck_")
        os.chdir(self.tmp)
        Path("project/chunks/chunk09/contracts").mkdir(parents=True)
        self.gk = _load_gatekeeper()

    def tearDown(self):
        os.chdir(self._old_cwd)
        shutil.rmtree(self.tmp, ignore_errors=True)

    def _run(self, **kwargs):
        buf = io.StringIO()
        args = self.gk.argparse.Namespace(**kwargs)
        exit_code = 0
        with redirect_stdout(buf):
            try:
                self.gk.cmd_tier_check(args)
            except SystemExit as e:
                exit_code = e.code
        return buf.getvalue(), exit_code

    def test_both_heuristics_fire_but_correctly_tiered_contract_still_exits_0(self):
        contract = (
            "# Contract C09-02\n\n"
            "Scientific Claim Tier: T-COMP\n\n"
            "## Objective\n"
            "Run an ablation removing the topological feature branch "
            "(reducing the number of parameters) and demonstrate real-time "
            "latency, reporting average latency, alongside baseline "
            "comparisons and accuracy.\n"
        )
        Path("project/chunks/chunk09/contracts/C09-02_contract.md").write_text(contract)
        out, code = self._run(contract="C09-02", contract_file=None, declared_tier=None, reports=None)
        self.assertEqual(code, 0, msg=f"D-054/D-055 must never affect exit code. Output:\n{out}")
        self.assertIn("Ablation-Row Covariance -- D-054, candidate", out)
        self.assertIn("ABLATION FACTOR COVARIANCE NOT ADDRESSED", out)
        self.assertIn("Efficiency-Claim Measurement Language -- D-055, candidate", out)
        self.assertIn("MEAN-ONLY LATENCY FOR AN EFFICIENCY CLAIM", out)

    def test_neither_heuristic_fires_on_a_clean_contract(self):
        contract = (
            "# Contract C09-03\n\n"
            "Scientific Claim Tier: NONE\n\n"
            "## Objective\n"
            "Implement the CSV ingestion pipeline for the raw transaction log.\n"
        )
        Path("project/chunks/chunk09/contracts/C09-03_contract.md").write_text(contract)
        out, code = self._run(contract="C09-03", contract_file=None, declared_tier=None, reports=None)
        self.assertEqual(code, 0)
        self.assertIn("No ablation-covariance pattern matched.", out)
        self.assertIn("No mean-only-latency-with-efficiency-claim pattern matched.", out)


if __name__ == "__main__":
    unittest.main()
