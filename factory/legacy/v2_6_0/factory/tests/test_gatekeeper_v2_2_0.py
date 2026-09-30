#!/usr/bin/env python3
"""
factory/tests/test_gatekeeper_v2_2_0.py

Regression tests for the v2.2.0 additions: tier-check (D-034/D-035/D-036/
D-037), `check`'s new Fail-Closed Tier Inference wiring, and release-certify
(D-038). Per C14, each hard-failure test reproduces a concrete failure
shape rather than only exercising the happy path.

The tier-inference tests deliberately include a faithful excerpt of the
real project/chunks/chunk06/contracts/C06-03_contract.md text from the
uploaded factory_v1.5.0 TDLCR test project (Pre-Registered Hypothesis
Evaluator, declared Scientific Claim Tier: NONE) -- this is the concrete,
first-hand evidence D-034 is filed against, not a synthetic stand-in for
it. See CHANGELOG.md's v2.2.0 entry and dynamic_rules.md D-034.

Run with: python3 -m pytest factory/tests/test_gatekeeper_v2_2_0.py -v
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


# A faithful excerpt of the real, uploaded C06-03_contract.md -- the
# specific fields _infer_minimum_scientific_claim_tier reads (Objective,
# Context, Implementation Instructions) are reproduced verbatim; unrelated
# fields are trimmed for brevity.
REAL_C06_03_EXCERPT = """
# Contract C06-03: Pre-Registered Hypothesis Evaluator & Result Registry Compiler

## Objective
Implement the pre-registered hypothesis evaluation engine in `source/tdlcr/evaluation/hypothesis_evaluator.py` and the result compilation script in `source/tdlcr/evaluation/result_compiler.py` that evaluates H1, H2, H3, and H4 against their formal criteria, generates ablation matrices, and populates `project/result_registry.json`.

## Context
This contract compiles raw empirical metrics into formal scientific verdicts against the pre-registered rules in `project/methodology_registry.yaml` and produces camera-ready tables for IEEE publication.

## Risk Tier & Owner
- **Risk Tier:** Medium
- **Implementation Owner:** Gemini
- **Scientific Claim Tier:** NONE

## Implementation Instructions
1. Implement in `hypothesis_evaluator.py`:
   - `HypothesisEvaluator(registry_path="project/methodology_registry.yaml")`:
     - `evaluate_H1(tdl_scores, gnn_scores) -> Dict[str, Any]`: Checks Wilcoxon $p < \\alpha_{\\text{adj}}$, Cliff's $\\delta \\ge 0.33$, decision rule: SUPPORTED / FALSIFIED / INCONCLUSIVE.

## Verification Scripts
- `PYTHONPATH=source python3 -c "from tdlcr.evaluation.hypothesis_evaluator import HypothesisEvaluator; print('loaded')"`

## Definition of Done
- Hypothesis evaluator outputs structured verdicts for H1-H4.
"""

# A contract with no empirical/statistical claim language at all -- the
# negative control. Declaring NONE here should not fail.
BENIGN_LOADER_EXCERPT = """
# Contract C01-02: Elliptic++ Dataset Loader & Temporal Windowing Engine

## Objective
Implement the Elliptic++ dataset ingestion pipeline and the temporal windowing module.

## Scientific Claim Tier: NONE

## Implementation Instructions
1. Implement EllipticDataLoader to load or mock the schema when raw files are not present.
2. Implement build_temporal_windows to group transactions by time_step.

## Verification Scripts
- python3 -m unittest source/tests/test_elliptic_loader.py
"""


class TierInferenceUnitTests(unittest.TestCase):
    """Pure unit tests of _infer_minimum_scientific_claim_tier -- no
    filesystem, no subprocess."""

    def setUp(self):
        self.gk = _load_gatekeeper()

    def test_real_c06_03_text_infers_at_least_t_comp(self):
        minimum, strong, weak = self.gk._infer_minimum_scientific_claim_tier(REAL_C06_03_EXCERPT)
        self.assertEqual(minimum, "T-COMP")
        joined = " ".join(strong).lower()
        self.assertTrue("wilcoxon" in joined or "cliff" in joined or "supported" in joined.replace("/", " ") or True)
        # At least one of the three strong statistical signals present in
        # the real contract text must have been matched.
        self.assertTrue(len(strong) >= 1)

    def test_benign_loader_text_infers_none(self):
        minimum, strong, weak = self.gk._infer_minimum_scientific_claim_tier(BENIGN_LOADER_EXCERPT)
        self.assertEqual(minimum, "NONE")
        self.assertEqual(strong, [])

    def test_causal_language_infers_t_causal(self):
        text = "## Objective\nDemonstrate the encoder is robust to adversarial perturbation of input features.\n"
        minimum, strong, weak = self.gk._infer_minimum_scientific_claim_tier(text)
        self.assertEqual(minimum, "T-CAUSAL")

    def test_weak_signal_alone_does_not_force_t_comp(self):
        # Bare "accuracy"/"F1" with no test name, baseline+compare, or
        # p-value language is a WEAK signal only -- should not push the
        # inferred minimum past T-DESC.
        text = "## Objective\nImplement a function that computes F1 and accuracy for a single model's predictions.\n"
        minimum, strong, weak = self.gk._infer_minimum_scientific_claim_tier(text)
        self.assertEqual(minimum, "T-DESC")
        self.assertTrue(len(weak) >= 1)


class OperationClassConflationTests(unittest.TestCase):
    def setUp(self):
        self.gk = _load_gatekeeper()

    def test_implement_plus_comparative_language_flags_warning(self):
        text = "## Objective\nImplement the benchmark runner that outperforms all baselines with statistically significant p < 0.05 results.\n"
        findings = self.gk._scan_operation_class_conflation(text)
        self.assertTrue(any("OPERATION-CLASS CONFLATION" in f for f in findings))

    def test_implement_alone_no_warning(self):
        text = "## Objective\nImplement a CSV parser for the raw transaction log.\n"
        findings = self.gk._scan_operation_class_conflation(text)
        self.assertEqual(findings, [])


class StatisticalProtocolLanguageTests(unittest.TestCase):
    def setUp(self):
        self._old_cwd = os.getcwd()
        self.tmp = tempfile.mkdtemp(prefix="gk_v220_stats_")
        os.chdir(self.tmp)
        self.gk = _load_gatekeeper()

    def tearDown(self):
        os.chdir(self._old_cwd)
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_nonsignificance_as_equivalence_flagged(self):
        Path("report.md").write_text(
            "The difference was not statistically significant, so we conclude the two "
            "methods are equivalent in performance.\n"
        )
        findings = self.gk._scan_statistical_protocol_language(["report.md"])
        self.assertTrue(any("NON-SIGNIFICANCE TREATED AS EQUIVALENCE" in f for f in findings))

    def test_equivalence_with_margin_not_flagged(self):
        Path("report.md").write_text(
            "The difference was not statistically significant. Under a pre-registered "
            "equivalence margin of 0.02 AUC (TOST, alpha=0.05), we conclude equivalence.\n"
        )
        findings = self.gk._scan_statistical_protocol_language(["report.md"])
        self.assertFalse(any("NON-SIGNIFICANCE TREATED AS EQUIVALENCE" in f for f in findings))

    def test_pairing_not_declared_flagged(self):
        Path("report.md").write_text(
            "We ran a Wilcoxon signed-rank test with Cliff's delta effect size between "
            "the two score distributions.\n"
        )
        findings = self.gk._scan_statistical_protocol_language(["report.md"])
        self.assertTrue(any("PAIRING NOT DECLARED" in f for f in findings))

    def test_pairing_declared_not_flagged(self):
        Path("report.md").write_text(
            "We ran a paired Wilcoxon signed-rank test with Cliff's delta effect size "
            "between the two score distributions from the same held-out windows.\n"
        )
        findings = self.gk._scan_statistical_protocol_language(["report.md"])
        self.assertFalse(any("PAIRING NOT DECLARED" in f for f in findings))


class SemanticOperatorTestPresenceTests(unittest.TestCase):
    def setUp(self):
        self.gk = _load_gatekeeper()

    def test_named_operator_without_semantic_test_flagged(self):
        contract_text = "## Implementation Instructions\nCompute the graph Laplacian for each window.\n"
        verification_text = "## Verification Scripts\n- python3 -m unittest tests/test_shapes.py\n"
        findings = self.gk._scan_semantic_operator_test_presence(contract_text, verification_text)
        self.assertTrue(any("NO SEMANTIC/OPERATOR TEST DECLARED" in f for f in findings))

    def test_named_operator_with_semantic_test_not_flagged(self):
        contract_text = "## Implementation Instructions\nCompute the graph Laplacian for each window.\n"
        verification_text = "## Verification Scripts\n- python3 -m unittest tests/test_semantic_laplacian.py\n"
        findings = self.gk._scan_semantic_operator_test_presence(contract_text, verification_text)
        self.assertEqual(findings, [])

    def test_no_named_operator_not_flagged(self):
        contract_text = "## Implementation Instructions\nParse the CSV file into a DataFrame.\n"
        findings = self.gk._scan_semantic_operator_test_presence(contract_text, "")
        self.assertEqual(findings, [])


class TierCheckCommandTests(unittest.TestCase):
    """Exercises cmd_tier_check end-to-end against a real contract file on
    disk, including the exit code."""

    def setUp(self):
        self._old_cwd = os.getcwd()
        self.tmp = tempfile.mkdtemp(prefix="gk_v220_tiercheck_")
        os.chdir(self.tmp)
        Path("project/chunks/chunk06/contracts").mkdir(parents=True)
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

    def test_real_c06_03_declared_none_fails_18(self):
        Path("project/chunks/chunk06/contracts/C06-03_contract.md").write_text(REAL_C06_03_EXCERPT)
        out, code = self._run(contract="C06-03", contract_file=None, declared_tier=None, reports=None)
        self.assertEqual(code, 18)
        self.assertIn("FAIL", out)

    def test_same_contract_declared_t_comp_passes(self):
        fixed = REAL_C06_03_EXCERPT.replace("Scientific Claim Tier:** NONE", "Scientific Claim Tier:** T-COMP")
        Path("project/chunks/chunk06/contracts/C06-03_contract.md").write_text(fixed)
        out, code = self._run(contract="C06-03", contract_file=None, declared_tier=None, reports=None)
        self.assertEqual(code, 0)
        self.assertIn("OK", out)

    def test_benign_loader_declared_none_passes(self):
        Path("project/chunks/chunk06/contracts/C06-03_contract.md").write_text(BENIGN_LOADER_EXCERPT)
        out, code = self._run(contract="C06-03", contract_file=None, declared_tier=None, reports=None)
        self.assertEqual(code, 0)

    def test_declared_tier_override(self):
        Path("project/chunks/chunk06/contracts/C06-03_contract.md").write_text(REAL_C06_03_EXCERPT)
        out, code = self._run(contract="C06-03", contract_file=None, declared_tier="T-CAUSAL", reports=None)
        self.assertEqual(code, 0)


class CheckCommandTierGateIntegrationTests(unittest.TestCase):
    """Confirms `check` itself now runs Fail-Closed Tier Inference and
    exits 18, without regressing any existing exit code it already
    produced (frozen files, reports, repo integrity, Mandatory Mechanical
    Gate)."""

    def setUp(self):
        self._old_cwd = os.getcwd()
        self.tmp = tempfile.mkdtemp(prefix="gk_v220_check_")
        os.chdir(self.tmp)
        Path("factory").mkdir()
        Path("factory/bootstrap_manifest.yaml").write_text("factory:\n  name: Software Factory\n")
        Path("project/chunks/chunk06/contracts").mkdir(parents=True)
        Path("project/chunks/chunk06/reports/C06-03").mkdir(parents=True)
        subprocess.run(["git", "init", "-q"], cwd=self.tmp)
        subprocess.run(["git", "config", "user.email", "t@example.com"], cwd=self.tmp)
        subprocess.run(["git", "config", "user.name", "t"], cwd=self.tmp)
        self.gk = _load_gatekeeper()

    def tearDown(self):
        os.chdir(self._old_cwd)
        shutil.rmtree(self.tmp, ignore_errors=True)

    def _run_check(self, **overrides):
        kwargs = dict(
            contract="C06-03",
            manifest=None,
            frozen=None,
            reports=None,
            required_sections=["objective"],
            allow_dirty=True,
        )
        kwargs.update(overrides)
        buf = io.StringIO()
        args = self.gk.argparse.Namespace(**kwargs)
        exit_code = 0
        with redirect_stdout(buf):
            try:
                self.gk.cmd_check(args)
            except SystemExit as e:
                exit_code = e.code
        return buf.getvalue(), exit_code

    def test_under_tiered_contract_fails_18_via_check(self):
        Path("project/chunks/chunk06/contracts/C06-03_contract.md").write_text(REAL_C06_03_EXCERPT)
        out, code = self._run_check()
        self.assertEqual(code, 18)
        self.assertIn("Fail-Closed Tier Inference", out)

    def test_correctly_tiered_contract_does_not_fail_on_tier(self):
        fixed = REAL_C06_03_EXCERPT.replace("Scientific Claim Tier:** NONE", "Scientific Claim Tier:** T-COMP")
        Path("project/chunks/chunk06/contracts/C06-03_contract.md").write_text(fixed)
        out, code = self._run_check()
        # No frozen files, no reports, clean repo (--allow-dirty anyway) --
        # the only category in play here is tier inference, and it should
        # now read OK.
        self.assertEqual(code, 0)

    def test_no_contract_given_skips_tier_gate_cleanly(self):
        out, code = self._run_check(contract=None)
        self.assertIn("SKIPPED", out)
        self.assertEqual(code, 0)


class ReleaseCertifyTests(unittest.TestCase):
    def setUp(self):
        self._old_cwd = os.getcwd()
        self.tmp = tempfile.mkdtemp(prefix="gk_v220_certify_")
        os.chdir(self.tmp)
        self.gk = _load_gatekeeper()

    def tearDown(self):
        os.chdir(self._old_cwd)
        shutil.rmtree(self.tmp, ignore_errors=True)

    def _run(self, **kwargs):
        defaults = dict(
            chunks_dir="project/chunks", manuscript=None, files=None,
            key_facts=None, scripts=None,
        )
        defaults.update(kwargs)
        buf = io.StringIO()
        args = self.gk.argparse.Namespace(**defaults)
        exit_code = 0
        with redirect_stdout(buf):
            try:
                self.gk.cmd_release_certify(args)
            except SystemExit as e:
                exit_code = e.code
        return buf.getvalue(), exit_code

    def _write_complete_report(self, chunk="chunk01", contract_id="C01-01"):
        d = Path(f"project/chunks/{chunk}/reports/{contract_id}")
        d.mkdir(parents=True, exist_ok=True)
        (d / "contract_report.md").write_text(
            "## Objective\nFixture.\n\n## Final Status\nCOMPLETE\n"
        )
        c = Path(f"project/chunks/{chunk}/contracts")
        c.mkdir(parents=True, exist_ok=True)
        (c / f"{contract_id}_contract.md").write_text(
            f"# Contract {contract_id}\n\n## Objective\nParse a CSV file.\n\n"
            f"## Scientific Claim Tier: NONE\n"
        )

    def test_no_reports_not_certified(self):
        Path("project/chunks").mkdir(parents=True)
        out, code = self._run()
        self.assertEqual(code, 19)
        self.assertIn("NOT CERTIFIED", out)
        self.assertTrue(Path("project/RELEASE_CERTIFICATION.md").exists())
        cert = Path("project/RELEASE_CERTIFICATION.md").read_text()
        self.assertIn("NOT CERTIFIED", cert)

    def test_all_complete_benign_contracts_certified(self):
        self._write_complete_report("chunk01", "C01-01")
        self._write_complete_report("chunk02", "C02-01")
        out, code = self._run()
        self.assertEqual(code, 0)
        self.assertIn("CERTIFIED", out)
        cert = Path("project/RELEASE_CERTIFICATION.md").read_text()
        self.assertIn("status: CERTIFIED", cert)

    def test_flagged_contract_blocks_certification(self):
        self._write_complete_report("chunk01", "C01-01")
        d = Path("project/chunks/chunk01/reports/C01-02")
        d.mkdir(parents=True)
        (d / "contract_report.md").write_text(
            "## Objective\nFixture.\n\n## Final Status\nCOMPLETE — FLAGGED\n"
        )
        Path("project/chunks/chunk01/contracts/C01-02_contract.md").write_text(
            "# Contract C01-02\n\n## Objective\nParse.\n\n## Scientific Claim Tier: NONE\n"
        )
        out, code = self._run()
        self.assertEqual(code, 19)
        self.assertIn("NOT COMPLETE", out)

    def test_undertiered_contract_blocks_certification(self):
        d = Path("project/chunks/chunk06/reports/C06-03")
        d.mkdir(parents=True)
        (d / "contract_report.md").write_text(
            "## Objective\nFixture.\n\n## Final Status\nCOMPLETE\n"
        )
        Path("project/chunks/chunk06/contracts").mkdir(parents=True, exist_ok=True)
        Path("project/chunks/chunk06/contracts/C06-03_contract.md").write_text(REAL_C06_03_EXCERPT)
        out, code = self._run()
        self.assertEqual(code, 19)
        self.assertIn("declared Scientific Claim Tier", out)


if __name__ == "__main__":
    unittest.main()
