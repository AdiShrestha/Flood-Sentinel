"""Tests for gatekeeper.py v2.6.0 commands.

Exit codes tested:
    27 -- verify-statistical-protocol
    28 -- verify-sensitivity-analysis
    29 -- pre-submission-audit
    30 -- verify-failure-taxonomy
Plus v2.6.0 extensions to verify-hardware-profile (exit 24).
"""

import json
import os
import subprocess
import sys
import tempfile
import textwrap
from pathlib import Path

import pytest

GATEKEEPER = str(Path(__file__).resolve().parent.parent / "gatekeeper.py")
REPO_ROOT = str(Path(__file__).resolve().parent.parent.parent)


def _run(args, cwd=None):
    """Run gatekeeper.py with given args; return (returncode, stdout, stderr)."""
    result = subprocess.run(
        [sys.executable, GATEKEEPER] + args,
        capture_output=True,
        text=True,
        cwd=cwd or REPO_ROOT,
    )
    return result.returncode, result.stdout, result.stderr


# ============================================================================
# verify-statistical-protocol (exit 27)
# ============================================================================

class TestVerifyStatisticalProtocol:
    """Tests for v2.6.0 verify-statistical-protocol command."""

    def test_pass_with_complete_protocol(self, tmp_path):
        """Report with named test, effect size, and correction should PASS."""
        report = tmp_path / "report.md"
        report.write_text(textwrap.dedent("""\
            ## Evaluation Results
            We used a Wilcoxon signed-rank test across 5 seeds.
            The effect size (Cohen's d = 0.82) exceeded our minimum threshold.
            Results: p = 0.023, with Holm correction applied for 2 comparisons.
            Our model vs. baseline A showed significant improvement.
        """))
        rc, out, _ = _run(["verify-statistical-protocol", "--reports", str(report)])
        assert rc == 0, f"Expected PASS (0), got {rc}.\nOutput: {out}"
        assert "PASS" in out

    def test_fail_pvalue_without_named_test(self, tmp_path):
        """P-values reported without naming a test should FAIL (exit 27)."""
        report = tmp_path / "report.md"
        report.write_text(textwrap.dedent("""\
            ## Results
            Our method achieved p = 0.01 compared to the baseline.
            The improvement was statistically significant.
        """))
        rc, out, _ = _run(["verify-statistical-protocol", "--reports", str(report)])
        assert rc == 27, f"Expected exit 27, got {rc}.\nOutput: {out}"
        assert "named significance test" in out.lower() or "FAIL" in out

    def test_fail_pvalue_without_effect_size(self, tmp_path):
        """P-values without effect size should FAIL (exit 27)."""
        report = tmp_path / "report.md"
        report.write_text(textwrap.dedent("""\
            ## Results
            Using a paired t-test, we found p = 0.003.
            The result was significant.
        """))
        rc, out, _ = _run(["verify-statistical-protocol", "--reports", str(report)])
        assert rc == 27, f"Expected exit 27, got {rc}.\nOutput: {out}"
        assert "effect" in out.lower()

    def test_pass_no_pvalues_no_fail(self, tmp_path):
        """Report with no p-values at all should PASS (nothing to violate)."""
        report = tmp_path / "report.md"
        report.write_text(textwrap.dedent("""\
            ## Descriptive Results
            We computed accuracy across three configurations.
            Mean accuracy was 0.87 with standard deviation 0.02.
        """))
        rc, out, _ = _run(["verify-statistical-protocol", "--reports", str(report)])
        assert rc == 0, f"Expected PASS (0), got {rc}.\nOutput: {out}"

    def test_warn_novel_module_without_negative_control(self, tmp_path):
        """Novel module without negative control should produce a warning."""
        report = tmp_path / "report.md"
        report.write_text(textwrap.dedent("""\
            ## Method
            We propose a novel attention module for feature fusion.
            ## Ablation
            Removing the module reduces accuracy by 3%.
        """))
        rc, out, _ = _run(["verify-statistical-protocol", "--reports", str(report)])
        # Should PASS (no p-values) but with a warning about negative controls
        assert rc == 0, f"Expected PASS (0), got {rc}.\nOutput: {out}"
        assert "WARN" in out

    def test_no_files_exit_27(self, tmp_path):
        """No reports found should exit 27."""
        rc, out, _ = _run(["verify-statistical-protocol", "--reports", str(tmp_path / "nonexistent.md")])
        assert rc == 27, f"Expected exit 27, got {rc}.\nOutput: {out}"


# ============================================================================
# verify-sensitivity-analysis (exit 28)
# ============================================================================

class TestVerifySensitivityAnalysis:
    """Tests for v2.6.0 verify-sensitivity-analysis command."""

    def test_pass_complete_manifest(self, tmp_path):
        """Manifest with enough levels, curves, and arch variations should PASS."""
        manifest = tmp_path / "sensitivity.json"
        manifest.write_text(json.dumps({
            "hyperparameters": [
                {
                    "name": "learning_rate",
                    "scale": "log",
                    "levels": [0.0005, 0.00075, 0.001, 0.0015, 0.002],
                    "response_curve": True,
                },
                {
                    "name": "hidden_dim",
                    "scale": "linear",
                    "levels": [128, 192, 256, 320, 384, 448, 512],
                    "performance_at_levels": [0.81, 0.84, 0.87, 0.88, 0.88, 0.88, 0.87],
                },
            ],
            "architecture_variations": [
                {"axis": "backbone", "values": ["ResNet-50", "ViT-B"]},
            ],
        }))
        rc, out, _ = _run(["verify-sensitivity-analysis", "--manifest", str(manifest)])
        assert rc == 0, f"Expected PASS (0), got {rc}.\nOutput: {out}"
        assert "PASS" in out

    def test_fail_too_few_levels(self, tmp_path):
        """HP with fewer than 3 levels should FAIL (exit 28)."""
        manifest = tmp_path / "sensitivity.json"
        manifest.write_text(json.dumps({
            "hyperparameters": [
                {"name": "lr", "levels": [0.001, 0.01], "response_curve": True},
            ],
            "architecture_variations": [{"axis": "width", "values": ["small", "large"]}],
        }))
        rc, out, _ = _run(["verify-sensitivity-analysis", "--manifest", str(manifest)])
        assert rc == 28, f"Expected exit 28, got {rc}.\nOutput: {out}"
        assert "levels" in out.lower()

    def test_fail_no_response_curve(self, tmp_path):
        """HP without response curve should FAIL (exit 28)."""
        manifest = tmp_path / "sensitivity.json"
        manifest.write_text(json.dumps({
            "hyperparameters": [
                {"name": "lr", "levels": [0.001, 0.005, 0.01, 0.05, 0.1]},
            ],
            "architecture_variations": [{"axis": "width", "values": ["small", "large"]}],
        }))
        rc, out, _ = _run(["verify-sensitivity-analysis", "--manifest", str(manifest)])
        assert rc == 28, f"Expected exit 28, got {rc}.\nOutput: {out}"
        assert "response curve" in out.lower()

    def test_fail_no_arch_sensitivity(self, tmp_path):
        """Manifest without architecture variations should FAIL (exit 28)."""
        manifest = tmp_path / "sensitivity.json"
        manifest.write_text(json.dumps({
            "hyperparameters": [
                {"name": "lr", "levels": [0.001, 0.005, 0.01, 0.05, 0.1], "response_curve": True},
            ],
        }))
        rc, out, _ = _run(["verify-sensitivity-analysis", "--manifest", str(manifest)])
        assert rc == 28, f"Expected exit 28, got {rc}.\nOutput: {out}"
        assert "architecture" in out.lower()

    def test_fail_manifest_not_found(self, tmp_path):
        """Missing manifest without fallback should FAIL (exit 28)."""
        rc, out, _ = _run(["verify-sensitivity-analysis", "--manifest", str(tmp_path / "nonexistent.json")])
        assert rc == 28, f"Expected exit 28, got {rc}.\nOutput: {out}"

    def test_pass_heuristic_fallback(self, tmp_path):
        """Report with sensitivity analysis language should pass heuristically."""
        report = tmp_path / "report.md"
        report.write_text(textwrap.dedent("""\
            ## Sensitivity Analysis
            We performed a hyperparameter perturbation study with a response curve.
        """))
        rc, out, _ = _run(["verify-sensitivity-analysis",
                           "--manifest", str(tmp_path / "nonexistent.json"),
                           "--report", str(report)])
        assert rc == 0, f"Expected PASS (0), got {rc}.\nOutput: {out}"
        assert "heuristic" in out.lower()


# ============================================================================
# pre-submission-audit (exit 29)
# ============================================================================

class TestPreSubmissionAudit:
    """Tests for v2.6.0 pre-submission-audit command."""

    def test_pass_complete_project(self, tmp_path):
        """Project with all required artifacts should PASS."""
        venue_req = tmp_path / "project" / "venue_requirements.md"
        venue_req.parent.mkdir(parents=True, exist_ok=True)
        venue_req.write_text(textwrap.dedent("""\
            # Venue Requirements
            ## Target Venue
            NeurIPS 2026
            ## Baseline Parity Ledger
            | Model | Params | Compute |
            |---|---|---|
            | Ours | 10M | 5G |
            | Baseline | 10.1M | 5.2G |
            ## LLM Usage Declaration
            LLM usage: Claude 3.5 Sonnet for code assistance.
        """))

        manuscript = tmp_path / "manuscript.md"
        manuscript.write_text(textwrap.dedent("""\
            # A Novel Method for Testing
            ## Abstract
            We propose a novel method that demonstrates improvement.
            We evaluate extensively and benchmark results.
            ## Methodology
            Using a Wilcoxon signed-rank test, p = 0.02, Cohen's d = 0.85.
        """))

        freeze = tmp_path / "project" / "experiment_freeze_manifest.json"
        freeze.write_text(json.dumps({"seeds": [42, 123, 456]}))

        rc, out, _ = _run([
            "pre-submission-audit",
            "--manuscript", str(manuscript),
            "--venue-requirements", str(venue_req),
            "--freeze-manifest", str(freeze),
            "--out", str(tmp_path / "audit_report.md"),
        ], cwd=REPO_ROOT)
        assert rc == 0, f"Expected PASS (0), got {rc}.\nOutput: {out}"
        # Check report was generated
        assert (tmp_path / "audit_report.md").exists()

    def test_fail_missing_statistical_test(self, tmp_path):
        """Manuscript with p-values but no named test should FAIL step 3 → exit 29."""
        venue_req = tmp_path / "project" / "venue_requirements.md"
        venue_req.parent.mkdir(parents=True, exist_ok=True)
        venue_req.write_text(textwrap.dedent("""\
            # Venue Requirements
            ## Baseline Parity Ledger
            | Model | Params |
            |---|---|
        """))

        manuscript = tmp_path / "manuscript.md"
        manuscript.write_text(textwrap.dedent("""\
            # Testing Method
            ## Abstract
            Our method shows p = 0.001 improvement.
        """))

        rc, out, _ = _run([
            "pre-submission-audit",
            "--manuscript", str(manuscript),
            "--venue-requirements", str(venue_req),
            "--out", str(tmp_path / "audit_report.md"),
        ], cwd=REPO_ROOT)
        assert rc == 29, f"Expected exit 29, got {rc}.\nOutput: {out}"
        assert "CRITICAL" in out or "statistical" in out.lower()

    def test_no_sources_exit_29(self, tmp_path):
        """No sources found should exit 29."""
        rc, out, _ = _run([
            "pre-submission-audit",
            "--manuscript", str(tmp_path / "nonexistent.md"),
            "--venue-requirements", str(tmp_path / "nonexistent2.md"),
            "--out", str(tmp_path / "audit_report.md"),
        ])
        assert rc == 29, f"Expected exit 29, got {rc}.\nOutput: {out}"


# ============================================================================
# verify-failure-taxonomy (exit 30)
# ============================================================================

class TestVerifyFailureTaxonomy:
    """Tests for v2.6.0 verify-failure-taxonomy command."""

    def test_pass_complete_taxonomy(self, tmp_path):
        """Taxonomy with >=3 categories, prevalence, selection rules should PASS."""
        taxonomy = tmp_path / "failure_taxonomy.json"
        taxonomy.write_text(json.dumps({
            "overall_selection_rule": "Random sample from worst decile of predictions",
            "failure_categories": [
                {
                    "category": "occlusion",
                    "prevalence": 0.12,
                    "selection_rule": "random sample from worst decile",
                    "comparative_analysis": "baseline fails on 85% of same cases",
                },
                {
                    "category": "rare_class",
                    "prevalence": 0.08,
                    "selection_rule": "stratified by class frequency",
                    "comparative_analysis": "unique failure mode, baseline succeeds",
                },
                {
                    "category": "sensor_noise",
                    "prevalence": 0.05,
                    "selection_rule": "random sample from SNR < 10dB",
                    "comparative_analysis": "both methods fail at similar rates",
                },
            ],
        }))
        rc, out, _ = _run(["verify-failure-taxonomy", "--taxonomy", str(taxonomy)])
        assert rc == 0, f"Expected PASS (0), got {rc}.\nOutput: {out}"
        assert "PASS" in out

    def test_fail_too_few_categories(self, tmp_path):
        """Taxonomy with fewer than 3 categories should FAIL (exit 30)."""
        taxonomy = tmp_path / "failure_taxonomy.json"
        taxonomy.write_text(json.dumps({
            "failure_categories": [
                {"category": "occlusion", "prevalence": 0.12,
                 "selection_rule": "random", "comparative_analysis": "yes"},
                {"category": "noise", "prevalence": 0.05,
                 "selection_rule": "random", "comparative_analysis": "yes"},
            ],
        }))
        rc, out, _ = _run(["verify-failure-taxonomy", "--taxonomy", str(taxonomy)])
        assert rc == 30, f"Expected exit 30, got {rc}.\nOutput: {out}"
        assert "minimum 3" in out.lower()

    def test_fail_missing_prevalence(self, tmp_path):
        """Category without prevalence should FAIL (exit 30)."""
        taxonomy = tmp_path / "failure_taxonomy.json"
        taxonomy.write_text(json.dumps({
            "failure_categories": [
                {"category": "occlusion", "selection_rule": "random",
                 "comparative_analysis": "yes"},
                {"category": "noise", "prevalence": 0.05,
                 "selection_rule": "random", "comparative_analysis": "yes"},
                {"category": "domain_shift", "prevalence": 0.03,
                 "selection_rule": "random", "comparative_analysis": "yes"},
            ],
        }))
        rc, out, _ = _run(["verify-failure-taxonomy", "--taxonomy", str(taxonomy)])
        assert rc == 30, f"Expected exit 30, got {rc}.\nOutput: {out}"
        assert "prevalence" in out.lower()

    def test_fail_missing_selection_rule(self, tmp_path):
        """Category without selection rule should FAIL (exit 30)."""
        taxonomy = tmp_path / "failure_taxonomy.json"
        taxonomy.write_text(json.dumps({
            "failure_categories": [
                {"category": "occlusion", "prevalence": 0.12,
                 "comparative_analysis": "yes"},
                {"category": "noise", "prevalence": 0.05,
                 "selection_rule": "random", "comparative_analysis": "yes"},
                {"category": "domain_shift", "prevalence": 0.03,
                 "selection_rule": "random", "comparative_analysis": "yes"},
            ],
        }))
        rc, out, _ = _run(["verify-failure-taxonomy", "--taxonomy", str(taxonomy)])
        assert rc == 30, f"Expected exit 30, got {rc}.\nOutput: {out}"
        assert "selection rule" in out.lower()

    def test_fail_taxonomy_not_found(self, tmp_path):
        """Missing taxonomy should FAIL (exit 30)."""
        rc, out, _ = _run(["verify-failure-taxonomy",
                           "--taxonomy", str(tmp_path / "nonexistent.json")])
        assert rc == 30, f"Expected exit 30, got {rc}.\nOutput: {out}"

    def test_pass_heuristic_from_report(self, tmp_path):
        """Report with taxonomy language, prevalence, and selection rule should pass heuristically."""
        report = tmp_path / "report.md"
        report.write_text(textwrap.dedent("""\
            ## Failure Taxonomy
            We categorize errors by failure mechanism.
            The failure rate P(failure|occlusion) = 0.12.
            Selection rule: random sample from worst decile.
        """))
        rc, out, _ = _run(["verify-failure-taxonomy",
                           "--taxonomy", str(tmp_path / "nonexistent.json"),
                           "--report", str(report)])
        assert rc == 0, f"Expected PASS (0), got {rc}.\nOutput: {out}"
        assert "heuristic" in out.lower()


# ============================================================================
# Extended verify-hardware-profile (D-068, D-069)
# ============================================================================

class TestExtendedHardwareProfile:
    """Tests for v2.6.0 extensions to verify-hardware-profile."""

    def _base_manifest(self):
        """Return a valid base v2.5.0 hardware profile manifest."""
        return {
            "measurement_hardware": "NVIDIA A100-SXM4-80GB",
            "latency_ms": {"p50": 5.2, "p90": 7.1, "p99": 12.3},
            "warmup_steps_excluded": True,
            "peak_memory_mb": {"peak_train": 24000, "peak_inference": 8000},
        }

    def test_pass_base_manifest_no_claims(self, tmp_path):
        """Base manifest without efficiency claims should PASS (no energy required)."""
        manifest = tmp_path / "hw.json"
        manifest.write_text(json.dumps(self._base_manifest()))
        rc, out, _ = _run(["verify-hardware-profile", "--manifest", str(manifest)])
        assert rc == 0, f"Expected PASS (0), got {rc}.\nOutput: {out}"

    def test_fail_efficient_claim_no_energy(self, tmp_path):
        """Efficiency claim without energy measurement should FAIL (exit 24)."""
        data = self._base_manifest()
        data["efficiency_claims"] = ["efficient", "lightweight"]
        manifest = tmp_path / "hw.json"
        manifest.write_text(json.dumps(data))
        rc, out, _ = _run(["verify-hardware-profile", "--manifest", str(manifest)])
        assert rc == 24, f"Expected exit 24, got {rc}.\nOutput: {out}"
        assert "D-068" in out

    def test_pass_efficient_claim_with_energy(self, tmp_path):
        """Efficiency claim with complete energy data should PASS."""
        data = self._base_manifest()
        data["efficiency_claims"] = ["efficient"]
        data["energy_per_inference"] = 0.0035
        data["energy_measurement_method"] = "nvidia-smi power.draw"
        manifest = tmp_path / "hw.json"
        manifest.write_text(json.dumps(data))
        rc, out, _ = _run(["verify-hardware-profile", "--manifest", str(manifest)])
        assert rc == 0, f"Expected PASS (0), got {rc}.\nOutput: {out}"

    def test_fail_flops_without_latency_convention(self, tmp_path):
        """FLOPs reported without counting convention or tool should FAIL (exit 24)."""
        data = self._base_manifest()
        data["flops"] = 4500000000
        manifest = tmp_path / "hw.json"
        manifest.write_text(json.dumps(data))
        rc, out, _ = _run(["verify-hardware-profile", "--manifest", str(manifest)])
        assert rc == 24, f"Expected exit 24, got {rc}.\nOutput: {out}"
        assert "D-069" in out

    def test_pass_flops_with_convention_and_tool(self, tmp_path):
        """FLOPs with convention, tool, and latency should PASS."""
        data = self._base_manifest()
        data["flops"] = 4500000000
        data["flops_counting_convention"] = "1 MAC = 2 FLOPs, input shape 224x224"
        data["flops_counting_tool"] = "fvcore 0.1.5"
        manifest = tmp_path / "hw.json"
        manifest.write_text(json.dumps(data))
        rc, out, _ = _run(["verify-hardware-profile", "--manifest", str(manifest)])
        assert rc == 0, f"Expected PASS (0), got {rc}.\nOutput: {out}"

    def test_fail_edge_claim_no_thermal(self, tmp_path):
        """Edge claim without thermal sustained test should FAIL (exit 24)."""
        data = self._base_manifest()
        data["efficiency_claims"] = ["edge"]
        data["energy_per_inference"] = 0.002
        data["energy_measurement_method"] = "RAPL"
        manifest = tmp_path / "hw.json"
        manifest.write_text(json.dumps(data))
        rc, out, _ = _run(["verify-hardware-profile", "--manifest", str(manifest)])
        assert rc == 24, f"Expected exit 24, got {rc}.\nOutput: {out}"
        assert "thermal" in out.lower()
