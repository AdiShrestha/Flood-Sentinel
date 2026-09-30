#!/usr/bin/env python3
"""
factory/tests/test_gatekeeper_v2_5_0.py

Regression and verification tests for Factory v2.5.0 publication-rigor mechanical gates:
1. Baseline Parity Verification (MAR-2, D-059, exit 23)
2. Hardware Profile Sufficiency (MAR-8, D-056, exit 24)
3. Experiment Pre-Registration Freeze & Seed-Lottery Firewall (MAR-7, C63, D-060, exit 25)
4. Foundation Model Benchmark Contamination Check (MAR-6, D-061, exit 26)

Run with: python3 -m unittest discover -s factory/tests -p "test_*.py"
(from the repository root).
"""

import argparse
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


class BaselineParityTests(unittest.TestCase):
    """MAR-2, D-059: Enforce parameter parity (+/-2%), compute parity (+/-5%),
    and baseline classification diversity."""

    def setUp(self):
        self.gk = _load_gatekeeper()
        self.tmpdir = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_baseline_parity_passing_case(self):
        venue_md = Path(self.tmpdir) / "venue_requirements.md"
        venue_md.write_text(
            "# Venue Requirements\n\n"
            "## Baseline Parity Ledger\n\n"
            "| Model / Baseline | Class | Parameters | Training Compute / FLOPs | Parity Status | Divergence Justification |\n"
            "|---|---|---|---|---|---|\n"
            "| Proposed Arch (Ours) | Proposed | 125M | 1.0e18 FLOPs | REFERENCE | Target method |\n"
            "| Constant Predictor | Trivial/Sanity | 0 | 0 FLOPs | SANITY | Trivial zero-parameter baseline |\n"
            "| Standard Transformer | Canonical Historical | 125M | 1.02e18 FLOPs | PARITY_MATCHED | Matched layers and width |\n"
            "| Modern Mamba-2 | Contemporary SOTA | 126M | 0.98e18 FLOPs | PARITY_MATCHED | Modernized recurrent SOTA |\n"
            "| Dense Transformer-Matched | Mechanism-Matched | 124M | 1.01e18 FLOPs | PARITY_MATCHED | Isolated routing mechanism |\n"
        )
        args = argparse.Namespace(
            venue_requirements=str(venue_md),
            contract_report=None,
            ledger=None,
            param_tolerance=0.02,
            compute_tolerance=0.05,
        )
        buf = io.StringIO()
        with redirect_stdout(buf):
            with self.assertRaises(SystemExit) as cm:
                self.gk.cmd_verify_baseline_parity(args)
        self.assertEqual(cm.exception.code, 0)
        self.assertIn("PASS: All baselines satisfy parameter parity", buf.getvalue())

    def test_baseline_parity_param_mismatch_fails_exit_23(self):
        venue_md = Path(self.tmpdir) / "venue_requirements.md"
        venue_md.write_text(
            "## Baseline Parity Ledger\n\n"
            "| Model / Baseline | Class | Parameters | Training Compute / FLOPs | Parity Status | Divergence Justification |\n"
            "|---|---|---|---|---|---|\n"
            "| Proposed Arch (Ours) | Proposed | 125M | 1.0e18 FLOPs | REFERENCE | Target method |\n"
            "| Canonical Transformer | Canonical Historical | 85M | 1.0e18 FLOPs | PARITY_MATCHED | None |\n"
            "| SOTA Model | Contemporary SOTA | 125M | 1.0e18 FLOPs | PARITY_MATCHED | Matched |\n"
            "| Ablated Kernel | Mechanism-Matched | 125M | 1.0e18 FLOPs | PARITY_MATCHED | Matched |\n"
        )
        args = argparse.Namespace(
            venue_requirements=str(venue_md),
            contract_report=None,
            ledger=None,
            param_tolerance=0.02,
            compute_tolerance=0.05,
        )
        buf = io.StringIO()
        with redirect_stdout(buf):
            with self.assertRaises(SystemExit) as cm:
                self.gk.cmd_verify_baseline_parity(args)
        self.assertEqual(cm.exception.code, 23)
        self.assertIn("Parameter count mismatch", buf.getvalue())

    def test_baseline_parity_compute_mismatch_fails_exit_23(self):
        venue_md = Path(self.tmpdir) / "venue_requirements.md"
        venue_md.write_text(
            "## Baseline Parity Ledger\n\n"
            "| Model / Baseline | Class | Parameters | Training Compute / FLOPs | Parity Status | Divergence Justification |\n"
            "|---|---|---|---|---|---|\n"
            "| Proposed Arch (Ours) | Proposed | 125M | 1.0e18 FLOPs | REFERENCE | Target method |\n"
            "| Baseline Model | Contemporary SOTA | 125M | 3.5e18 FLOPs | PARITY_MATCHED | - |\n"
            "| Matched Kernel | Mechanism-Matched | 125M | 1.0e18 FLOPs | PARITY_MATCHED | Matched |\n"
        )
        args = argparse.Namespace(
            venue_requirements=str(venue_md),
            contract_report=None,
            ledger=None,
            param_tolerance=0.02,
            compute_tolerance=0.05,
        )
        buf = io.StringIO()
        with redirect_stdout(buf):
            with self.assertRaises(SystemExit) as cm:
                self.gk.cmd_verify_baseline_parity(args)
        self.assertEqual(cm.exception.code, 23)
        self.assertIn("Training compute mismatch", buf.getvalue())

    def test_baseline_parity_justified_divergence_passes(self):
        venue_md = Path(self.tmpdir) / "venue_requirements.md"
        venue_md.write_text(
            "## Baseline Parity Ledger\n\n"
            "| Model / Baseline | Class | Parameters | Training Compute / FLOPs | Parity Status | Divergence Justification |\n"
            "|---|---|---|---|---|---|\n"
            "| Proposed Arch (Ours) | Proposed | 125M | 1.0e18 FLOPs | REFERENCE | Target method |\n"
            "| Standard Transformer | Canonical Historical | 125M | 1.0e18 FLOPs | PARITY_MATCHED | Matched |\n"
            "| Ultra-Large SOTA | Contemporary SOTA | 1.5B | 1.2e19 FLOPs | DIVERGENT | Pretrained external checkpoint provided by foundation lab |\n"
            "| Mechanism Match | Mechanism-Matched | 125M | 1.0e18 FLOPs | PARITY_MATCHED | Matched |\n"
        )
        args = argparse.Namespace(
            venue_requirements=str(venue_md),
            contract_report=None,
            ledger=None,
            param_tolerance=0.02,
            compute_tolerance=0.05,
        )
        buf = io.StringIO()
        with redirect_stdout(buf):
            with self.assertRaises(SystemExit) as cm:
                self.gk.cmd_verify_baseline_parity(args)
        self.assertEqual(cm.exception.code, 0)

    def test_missing_mandatory_class_fails_exit_23(self):
        venue_md = Path(self.tmpdir) / "venue_requirements.md"
        venue_md.write_text(
            "## Baseline Parity Ledger\n\n"
            "| Model / Baseline | Class | Parameters | Training Compute / FLOPs | Parity Status | Divergence Justification |\n"
            "|---|---|---|---|---|---|\n"
            "| Proposed Arch (Ours) | Proposed | 125M | 1.0e18 FLOPs | REFERENCE | Target method |\n"
            "| Baseline 1 | Canonical Historical | 125M | 1.0e18 FLOPs | PARITY_MATCHED | Matched |\n"
        )
        args = argparse.Namespace(
            venue_requirements=str(venue_md),
            contract_report=None,
            ledger=None,
            param_tolerance=0.02,
            compute_tolerance=0.05,
        )
        buf = io.StringIO()
        with redirect_stdout(buf):
            with self.assertRaises(SystemExit) as cm:
                self.gk.cmd_verify_baseline_parity(args)
        self.assertEqual(cm.exception.code, 23)
        self.assertIn("Missing mandatory baseline class", buf.getvalue())


class HardwareProfileTests(unittest.TestCase):
    """MAR-8, D-056: Verify latency distribution, warmup exclusion, and
    separate peak training and peak inference memory tracking."""

    def setUp(self):
        self.gk = _load_gatekeeper()
        self.tmpdir = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_hardware_profile_valid_passes(self):
        manifest = Path(self.tmpdir) / "hardware_profile_manifest.json"
        manifest.write_text(
            json.dumps({
                "measurement_hardware": "NVIDIA A100-SXM4-80GB",
                "batch_size": 32,
                "warmup_steps_excluded": True,
                "latency_ms": {
                    "p50": 14.2,
                    "p90": 15.1,
                    "p99": 16.8
                },
                "peak_memory_mb": {
                    "peak_train": 18240,
                    "peak_inference": 4320
                }
            })
        )
        args = argparse.Namespace(manifest=str(manifest))
        buf = io.StringIO()
        with redirect_stdout(buf):
            with self.assertRaises(SystemExit) as cm:
                self.gk.cmd_verify_hardware_profile(args)
        self.assertEqual(cm.exception.code, 0)
        self.assertIn("PASS: Hardware profile satisfies empirical distribution", buf.getvalue())

    def test_hardware_profile_missing_p99_fails_exit_24(self):
        manifest = Path(self.tmpdir) / "hardware_profile_manifest.json"
        manifest.write_text(
            json.dumps({
                "measurement_hardware": "NVIDIA A100-SXM4-80GB",
                "warmup_steps_excluded": True,
                "latency_ms": {
                    "p50": 14.2,
                    "p90": 15.1
                },
                "peak_memory_mb": {
                    "peak_train": 18240,
                    "peak_inference": 4320
                }
            })
        )
        args = argparse.Namespace(manifest=str(manifest))
        buf = io.StringIO()
        with redirect_stdout(buf):
            with self.assertRaises(SystemExit) as cm:
                self.gk.cmd_verify_hardware_profile(args)
        self.assertEqual(cm.exception.code, 24)
        self.assertIn("Latency percentile 'p99' missing", buf.getvalue())

    def test_hardware_profile_warmup_not_excluded_fails_exit_24(self):
        manifest = Path(self.tmpdir) / "hardware_profile_manifest.json"
        manifest.write_text(
            json.dumps({
                "measurement_hardware": "NVIDIA A100-SXM4-80GB",
                "warmup_steps_excluded": False,
                "latency_ms": {
                    "p50": 14.2,
                    "p90": 15.1,
                    "p99": 16.8
                },
                "peak_memory_mb": {
                    "peak_train": 18240,
                    "peak_inference": 4320
                }
            })
        )
        args = argparse.Namespace(manifest=str(manifest))
        buf = io.StringIO()
        with redirect_stdout(buf):
            with self.assertRaises(SystemExit) as cm:
                self.gk.cmd_verify_hardware_profile(args)
        self.assertEqual(cm.exception.code, 24)
        self.assertIn("Warmup steps not excluded", buf.getvalue())

    def test_hardware_profile_missing_inference_memory_fails_exit_24(self):
        manifest = Path(self.tmpdir) / "hardware_profile_manifest.json"
        manifest.write_text(
            json.dumps({
                "measurement_hardware": "NVIDIA A100-SXM4-80GB",
                "warmup_steps_excluded": True,
                "latency_ms": {
                    "p50": 14.2,
                    "p90": 15.1,
                    "p99": 16.8
                },
                "peak_memory_mb": {
                    "peak_train": 18240
                }
            })
        )
        args = argparse.Namespace(manifest=str(manifest))
        buf = io.StringIO()
        with redirect_stdout(buf):
            with self.assertRaises(SystemExit) as cm:
                self.gk.cmd_verify_hardware_profile(args)
        self.assertEqual(cm.exception.code, 24)
        self.assertIn("Peak inference memory ('peak_inference') missing", buf.getvalue())


class ExperimentFreezeTests(unittest.TestCase):
    """MAR-7, C63, D-060: Pre-registration and Seed-Lottery Firewall."""

    def setUp(self):
        self.gk = _load_gatekeeper()
        self.tmpdir = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_freeze_and_verify_passes(self):
        freeze_json = Path(self.tmpdir) / "experiment_freeze_manifest.json"
        report_md = Path(self.tmpdir) / "contract_report.md"

        # 1. Freeze experiment
        freeze_args = argparse.Namespace(
            out=str(freeze_json),
            manifest=None,
            seeds=[42, 1337, 2024],
            split_files=None,
            lockfile=None,
            force=True,
        )
        buf = io.StringIO()
        with redirect_stdout(buf):
            with self.assertRaises(SystemExit) as cm:
                self.gk.cmd_freeze_experiment(freeze_args)
        self.assertEqual(cm.exception.code, 0)
        self.assertTrue(freeze_json.exists())

        # 2. Write matching report
        report_md.write_text(
            "# Contract Report\n\n"
            "## Verification Summary\n"
            "Evaluation completed.\n\n"
            "## Pre-Registration & Seed Audit\n"
            "| Seed | Accuracy | F1 Score |\n"
            "|---|---|---|\n"
            "| 42 | 0.924 | 0.918 |\n"
            "| 1337 | 0.928 | 0.921 |\n"
            "| 2024 | 0.921 | 0.915 |\n"
        )

        verify_args = argparse.Namespace(
            freeze_manifest=str(freeze_json),
            report=str(report_md),
        )
        buf2 = io.StringIO()
        with redirect_stdout(buf2):
            with self.assertRaises(SystemExit) as cm:
                self.gk.cmd_verify_experiment_freeze(verify_args)
        self.assertEqual(cm.exception.code, 0)
        self.assertIn("PASS: All pre-registered seeds executed", buf2.getvalue())

    def test_verify_freeze_seed_omission_fails_exit_25(self):
        freeze_json = Path(self.tmpdir) / "experiment_freeze_manifest.json"
        report_md = Path(self.tmpdir) / "contract_report.md"

        freeze_json.write_text(
            json.dumps({
                "factory_version": "2.5.0",
                "pre_registered_seeds": [42, 1337, 2024],
            })
        )

        # Report only contains seeds 42 and 1337 (omits 2024)
        report_md.write_text(
            "# Contract Report\n\n"
            "## Pre-Registration & Seed Audit\n"
            "| Seed | Accuracy |\n"
            "|---|---|\n"
            "| 42 | 0.924 |\n"
            "| 1337 | 0.928 |\n"
        )

        verify_args = argparse.Namespace(
            freeze_manifest=str(freeze_json),
            report=str(report_md),
        )
        buf = io.StringIO()
        with redirect_stdout(buf):
            with self.assertRaises(SystemExit) as cm:
                self.gk.cmd_verify_experiment_freeze(verify_args)
        self.assertEqual(cm.exception.code, 25)
        self.assertIn("Selective reporting / seed omission detected", buf.getvalue())

    def test_verify_freeze_unregistered_seed_fails_exit_25(self):
        freeze_json = Path(self.tmpdir) / "experiment_freeze_manifest.json"
        report_md = Path(self.tmpdir) / "contract_report.md"

        freeze_json.write_text(
            json.dumps({
                "factory_version": "2.5.0",
                "pre_registered_seeds": [42, 1337, 2024],
            })
        )

        # Report introduces seed 999 post-hoc
        report_md.write_text(
            "# Contract Report\n\n"
            "## Pre-Registration & Seed Audit\n"
            "| Seed | Accuracy |\n"
            "|---|---|\n"
            "| 42 | 0.924 |\n"
            "| 1337 | 0.928 |\n"
            "| 2024 | 0.921 |\n"
            "| 999 | 0.985 |\n"
        )

        verify_args = argparse.Namespace(
            freeze_manifest=str(freeze_json),
            report=str(report_md),
        )
        buf = io.StringIO()
        with redirect_stdout(buf):
            with self.assertRaises(SystemExit) as cm:
                self.gk.cmd_verify_experiment_freeze(verify_args)
        self.assertEqual(cm.exception.code, 25)
        self.assertIn("Post-hoc unregistered seeds detected", buf.getvalue())


class ContaminationCheckTests(unittest.TestCase):
    """MAR-6, D-061: Audit benchmark evaluation splits against training
    pre-training corpora or cutoff dates."""

    def setUp(self):
        self.gk = _load_gatekeeper()
        self.tmpdir = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_contamination_audit_json_passes(self):
        audit_file = Path(self.tmpdir) / "contamination_audit.json"
        audit_file.write_text(
            json.dumps({
                "benchmark_name": "GSM8K-Evaluation",
                "model_identifier": "Transformer-Pro-v1",
                "model_cutoff_date": "2023-09",
                "benchmark_release_date": "2024-03",
                "contamination_detected": False,
                "exact_n_gram_matches": 0,
                "decontamination_verified": True
            })
        )
        args = argparse.Namespace(
            audit_json=str(audit_file),
            benchmark=None,
            training_corpus=None,
            n_gram=13,
            model_cutoff=None,
            benchmark_release_date=None,
        )
        buf = io.StringIO()
        with redirect_stdout(buf):
            with self.assertRaises(SystemExit) as cm:
                self.gk.cmd_contamination_check(args)
        self.assertEqual(cm.exception.code, 0)
        self.assertIn("PASS: No 13-gram contamination", buf.getvalue())

    def test_contamination_detected_fails_exit_26(self):
        audit_file = Path(self.tmpdir) / "contamination_audit.json"
        audit_file.write_text(
            json.dumps({
                "benchmark_name": "HumanEval-Evaluation",
                "contamination_detected": True,
                "exact_n_gram_matches": 142
            })
        )
        args = argparse.Namespace(
            audit_json=str(audit_file),
            benchmark=None,
            training_corpus=None,
            n_gram=13,
            model_cutoff=None,
            benchmark_release_date=None,
        )
        buf = io.StringIO()
        with redirect_stdout(buf):
            with self.assertRaises(SystemExit) as cm:
                self.gk.cmd_contamination_check(args)
        self.assertEqual(cm.exception.code, 26)
        self.assertIn("contamination detected", buf.getvalue())

    def test_temporal_leakage_fails_exit_26(self):
        audit_file = Path(self.tmpdir) / "contamination_audit.json"
        audit_file.write_text(
            json.dumps({
                "benchmark_name": "Recent-Benchmark-2024",
                "model_cutoff_date": "2025-01",
                "benchmark_release_date": "2024-05",
                "contamination_detected": False,
                "decontamination_verified": False
            })
        )
        args = argparse.Namespace(
            audit_json=str(audit_file),
            benchmark=None,
            training_corpus=None,
            n_gram=13,
            model_cutoff=None,
            benchmark_release_date=None,
        )
        buf = io.StringIO()
        with redirect_stdout(buf):
            with self.assertRaises(SystemExit) as cm:
                self.gk.cmd_contamination_check(args)
        self.assertEqual(cm.exception.code, 26)
        self.assertIn("Temporal leakage: model cutoff", buf.getvalue())

    def test_corpus_exact_13gram_overlap_fails_exit_26(self):
        bench_file = Path(self.tmpdir) / "bench.txt"
        train_file = Path(self.tmpdir) / "train.txt"

        phrase = "the quick brown fox jumps over the lazy dog and runs through the forest"
        bench_file.write_text(f"Prompt: {phrase} question here?")
        train_file.write_text(f"Document archive: some intro text {phrase} more text.")

        args = argparse.Namespace(
            audit_json=None,
            benchmark=str(bench_file),
            training_corpus=str(train_file),
            n_gram=13,
            model_cutoff=None,
            benchmark_release_date=None,
        )
        buf = io.StringIO()
        with redirect_stdout(buf):
            with self.assertRaises(SystemExit) as cm:
                self.gk.cmd_contamination_check(args)
        self.assertEqual(cm.exception.code, 26)
        self.assertIn("matching 13-grams", buf.getvalue())


if __name__ == "__main__":
    unittest.main()
