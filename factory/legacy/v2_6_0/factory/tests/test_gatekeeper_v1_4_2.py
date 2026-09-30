#!/usr/bin/env python3
"""
factory/tests/test_gatekeeper_v1_4_2.py

Regression tests for the v1.4.2 release: closes a real, currently-existing
gap in `_self_check_version_currency`'s own target list. As of v1.4.1,
SELF_CHECK_FILES covers eight documents but omits two files that carry a
live, driftable version reference: `gatekeeper.py` itself (module
docstring: "STATUS (Factory vX.Y.Z)") and `bootstrap_manifest.yaml`
(`factory.version`). This is the same failure class the v1.4.1 fix already
names in its own code comment -- constitution.md and dynamic_rules.md
drifted for two release cycles undetected because neither was in the dict.
Found by direct inspection, not by self-check itself, exactly as before.

Per the Factory's stated practice (C14), each test below reproduces the
exact gap and was confirmed failing against the unpatched v1.4.1 script
before the corresponding fix landed.

Run with: python3 -m pytest factory/tests/test_gatekeeper_v1_4_2.py -v
      or: python3 factory/tests/test_gatekeeper_v1_4_2.py
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


class TempRepoTestCase(unittest.TestCase):
    def setUp(self):
        self._old_cwd = os.getcwd()
        self.tmp = tempfile.mkdtemp(prefix="gk_v142_test_")
        os.chdir(self.tmp)
        self.gk = _load_gatekeeper()
        Path("factory").mkdir()

    def tearDown(self):
        os.chdir(self._old_cwd)
        shutil.rmtree(self.tmp, ignore_errors=True)

    def _write(self, name, content):
        self.gk.SELF_CHECK_FILES[name].write_text(content)


class TestGatekeeperOwnFileIsMonitored(TempRepoTestCase):
    """gatekeeper.py carries its own 'Factory vX.Y.Z' status line and must
    be in SELF_CHECK_FILES, the same way constitution/dynamic_rules were
    added in v1.4.1 after being found missing."""

    def test_gatekeeper_key_present_in_self_check_files(self):
        self.assertIn(
            "gatekeeper", self.gk.SELF_CHECK_FILES,
            "gatekeeper.py's own 'STATUS (Factory vX.Y.Z)' docstring line is "
            "a live version reference and must be monitored by "
            "_self_check_version_currency, the same class of gap that let "
            "constitution.md/dynamic_rules.md drift undetected before v1.4.1."
        )

    def test_stale_gatekeeper_status_line_is_caught(self):
        self._write("version", "1.4.2")
        self._write("gatekeeper", '"""\nSTATUS (Factory v1.4.1): PARTIAL IMPLEMENTATION.\n"""\n')
        findings = self.gk._self_check_version_currency()
        joined = "\n".join(findings)
        self.assertIn("1.4.1", joined)
        self.assertIn("STALE VERSION REFERENCE", joined)

    def test_current_gatekeeper_status_line_is_not_flagged(self):
        self._write("version", "1.4.2")
        self._write("gatekeeper", '"""\nSTATUS (Factory v1.4.2): PARTIAL IMPLEMENTATION.\n"""\n')
        findings = self.gk._self_check_version_currency()
        self.assertEqual(findings, [])


class TestBootstrapManifestIsMonitored(TempRepoTestCase):
    """bootstrap_manifest.yaml's `factory.version` field is a live version
    reference read by nothing today. Its sibling field,
    `bootstrap_manifest_version`, is explicitly documented as versioning
    the manifest *schema* independently of the Factory version, and must
    never be flagged just because it differs from VERSION."""

    def test_bootstrap_manifest_key_present_in_self_check_files(self):
        self.assertIn("bootstrap_manifest", self.gk.SELF_CHECK_FILES)

    def test_stale_factory_version_field_is_caught(self):
        self._write("version", "1.4.2")
        self._write(
            "bootstrap_manifest",
            'factory:\n  name: "Software Factory"\n  version: "1.4.1"\n'
            '  bootstrap_manifest_version: "1.4.1"\n',
        )
        findings = self.gk._self_check_version_currency()
        joined = "\n".join(findings)
        self.assertIn("1.4.1", joined)
        self.assertIn("STALE VERSION REFERENCE", joined)

    def test_current_factory_version_field_is_not_flagged(self):
        self._write("version", "1.4.2")
        self._write(
            "bootstrap_manifest",
            'factory:\n  name: "Software Factory"\n  version: "1.4.2"\n'
            '  bootstrap_manifest_version: "1.4.2"\n',
        )
        findings = self.gk._self_check_version_currency()
        self.assertEqual(findings, [])

    def test_independently_versioned_manifest_schema_field_is_never_flagged(self):
        # bootstrap_manifest_version is allowed to legitimately differ from
        # VERSION by design (bootstrap_manifest.yaml's own notes: "versions
        # this manifest schema independently from the Factory itself").
        # factory.version matches current; only bootstrap_manifest_version
        # differs -- this must NOT produce a finding.
        self._write("version", "1.4.2")
        self._write(
            "bootstrap_manifest",
            'factory:\n  name: "Software Factory"\n  version: "1.4.2"\n'
            '  bootstrap_manifest_version: "1.3.0"\n',
        )
        findings = self.gk._self_check_version_currency()
        self.assertEqual(
            findings, [],
            "bootstrap_manifest_version is independently-versioned by design "
            "and must never be treated as a stale Factory-version reference."
        )


class TestFabricatedStatisticalInput(TempRepoTestCase):
    """Reproduces a real incident (GLOF project rework, Chunk 08, contract
    C08-06): `run_bootstrap_ci.py` was supposed to compute lake-level
    bootstrap CIs and DeLong significance tests from real per-window model
    predictions. Instead it read only the already-aggregated scalar
    auc_roc from evaluation_summary_real_data.json and fabricated
    per-window scores via `rng.normal(...)`, shaped to approximate that
    AUC, then bootstrapped and significance-tested the fabricated values.
    Reproduced independently: running the real script against the real
    input with its own documented seed (4096) produced a byte-identical
    statistical_significance.json to the one that shipped and was cited
    in the manuscript (CL-16 through CL-21). Neither `check_reports`,
    `evidence-check`, nor `release-check` catches this -- all three
    operate on the artifact's own declared values, never on whether the
    computation that produced them used real observations. Unlike
    D-022/D-023 (data-*acquisition* scripts fabricating data because an
    external API was unreachable), this is a data*-computation* script
    fabricating its own intermediate inputs with no external constraint
    at all -- a distinct trigger for the same underlying C01 concern, so
    it extends `acquisition-audit`'s existing structural check rather
    than duplicating a new command (C46)."""

    # A distilled but structurally faithful excerpt of the real
    # run_bootstrap_ci.py -- same fabrication shape (assign from a
    # distribution sampler, later pass into a metric function), trimmed
    # for test speed rather than reproducing the full 2000-resample loop.
    _REAL_INCIDENT_SHAPE = (
        "import numpy as np\n"
        "from sklearn.metrics import roc_auc_score\n\n"
        "def run_bootstrap_ci(summary_path, n_resamples=2000, seed=4096):\n"
        "    rng = np.random.default_rng(seed)\n"
        "    # Create synthetic score profile consistent with method's AUC\n"
        "    base_s = rng.normal(loc=0.0, scale=0.5, size=102)\n"
        "    scores_sample = np.concatenate([base_s])\n"
        "    roc_v = float(roc_auc_score(y_true_sample, scores_sample))\n"
        "    return roc_v\n"
    )

    _CLEAN_SHAPE = (
        "import numpy as np\n"
        "from sklearn.metrics import roc_auc_score\n\n"
        "def run_bootstrap_ci(predictions_path, n_resamples=2000, seed=4096):\n"
        "    rng = np.random.default_rng(seed)\n"
        "    # Load real per-window predictions written by run_evaluation.py\n"
        "    y_scores = np.load(predictions_path)['scores']\n"
        "    y_true = np.load(predictions_path)['labels']\n"
        "    sampled_indices = rng.choice(len(y_scores), size=len(y_scores), replace=True)\n"
        "    roc_v = float(roc_auc_score(y_true[sampled_indices], y_scores[sampled_indices]))\n"
        "    return roc_v\n"
    )

    def test_real_incident_shape_is_flagged_and_fails(self):
        Path("run_bootstrap_ci.py").write_text(self._REAL_INCIDENT_SHAPE)
        findings = self.gk._scan_fabricated_statistical_input(["run_bootstrap_ci.py"])
        joined = "\n".join(findings)
        self.assertTrue(findings, "the real C08-06 fabrication pattern must be caught.")
        self.assertIn("FABRICATED STATISTICAL INPUT", joined)
        self.assertIn("run_bootstrap_ci.py", joined)

    def test_real_evaluation_summary_reproduction_confirms_pattern(self):
        # Same check against the actual uploaded script content (not the
        # distilled shape) -- confirms the regex-level check fires against
        # the real file, not just a hand-shaped test fixture.
        real_script = (
            "rng = np.random.default_rng(seed)\n"
            "base_s = rng.normal(loc=0.0, scale=0.5, size=n_windows)\n"
            "per_method_scores[m].append(base_s)\n"
            "scores_sample = np.concatenate([per_method_scores[m][i] for i in sampled_indices])\n"
            "roc_v = float(roc_auc_score(y_true_sample, scores_sample))\n"
        )
        Path("real_shape.py").write_text(real_script)
        findings = self.gk._scan_fabricated_statistical_input(["real_shape.py"])
        self.assertTrue(any("FABRICATED STATISTICAL INPUT" in f for f in findings))

    def test_clean_script_loading_real_predictions_passes(self):
        Path("clean_bootstrap.py").write_text(self._CLEAN_SHAPE)
        findings = self.gk._scan_fabricated_statistical_input(["clean_bootstrap.py"])
        self.assertEqual(findings, [])

    def test_distribution_sampling_alone_without_metric_call_is_not_flagged(self):
        # rng.normal() used for something unrelated to a metric computation
        # (e.g. synthetic unit-test fixtures in a file that never calls a
        # metric function) must not be flagged -- co-occurrence, not bare
        # presence, is the signal.
        Path("unrelated.py").write_text(
            "import numpy as np\n"
            "rng = np.random.default_rng(1)\n"
            "noise = rng.normal(size=10)  # unrelated to any metric\n"
        )
        findings = self.gk._scan_fabricated_statistical_input(["unrelated.py"])
        self.assertEqual(findings, [])

    def test_acquisition_audit_command_surfaces_the_new_check_as_exit_11(self):
        # End-to-end: cmd_acquisition_audit already exits 11 for structural
        # findings (D-022); this new check is a second structural finding
        # type under the same command and exit code, not a new command
        # (C46 -- improve an existing component before adding one).
        Path("run_bootstrap_ci.py").write_text(self._REAL_INCIDENT_SHAPE)
        buf = io.StringIO()
        args = self.gk.argparse.Namespace(scripts=["run_bootstrap_ci.py"], reports=None)
        with redirect_stdout(buf):
            try:
                self.gk.cmd_acquisition_audit(args)
            except SystemExit as e:
                exit_code = e.code
        self.assertEqual(exit_code, 11)
        self.assertIn("FABRICATED STATISTICAL INPUT", buf.getvalue())

    def test_existing_text_scan_also_catches_synthetic_language_in_same_file(self):
        # Confirms the ALREADY-SHIPPED v1.4.1 text scan (D-023) independently
        # catches this file too, as a warning -- it was simply never pointed
        # at statistical-computation scripts by any contract or process
        # instruction. No code change needed for this half; disclosed in
        # CHANGELOG as a process gap, not a tooling gap.
        Path("run_bootstrap_ci.py").write_text(self._REAL_INCIDENT_SHAPE)
        findings = self.gk._scan_acquisition_text(["run_bootstrap_ci.py"])
        joined = "\n".join(findings)
        self.assertIn("SIMULATION-INDICATING LANGUAGE", joined)
        self.assertIn("synthetic", joined)


if __name__ == "__main__":
    unittest.main(verbosity=2)
