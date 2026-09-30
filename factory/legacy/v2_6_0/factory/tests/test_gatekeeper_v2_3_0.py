#!/usr/bin/env python3
"""
factory/tests/test_gatekeeper_v2_3_0.py

Regression tests for the v2.3.0 additions (D-039 through D-053). Each test
reproduces a concrete failure shape drawn from one of the four field
reports (Sentinel-GL, KLStream, the AML/collusion-ring project, CoreMesh)
or from a defect found directly by cross-checking gatekeeper.py against
this Factory's own spec documents (D-046, D-047) -- see CHANGELOG.md's
v2.3.0 entry and dynamic_rules.md's v2.3.0 section for the full evidence
behind each rule this file verifies.

Run with: python3 -m pytest factory/tests/test_gatekeeper_v2_3_0.py -v
"""

import importlib.util
import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

GATEKEEPER_PATH = Path(__file__).resolve().parent.parent / "gatekeeper.py"


def _load_gatekeeper():
    spec = importlib.util.spec_from_file_location("gatekeeper_v230", GATEKEEPER_PATH)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


class TestD039VerificationParsing(unittest.TestCase):
    """D-039: the aggregate verifier must not silently read zero declared
    commands as a clean pass when a report genuinely declared some."""

    def setUp(self):
        self.gk = _load_gatekeeper()

    def test_legacy_command_block_style_is_parsed(self):
        # Faithful reproduction of the Sentinel-GL C01-01..C01-08 report
        # shape: a literal "Command:" label, no bullet, no bold, no
        # backticks -- exactly what the ORIGINAL v2.2.0 single-pattern
        # parser found zero matches against.
        report_text = (
            "## Verification\n\n"
            "Command:\n"
            "```\n"
            "python3 -m pytest source/tests/test_acquisition.py -v\n"
            "```\n"
            "Output: 10 passed, 0 failed.\n"
        )
        commands = self.gk._extract_declared_commands(report_text)
        self.assertIn("python3 -m pytest source/tests/test_acquisition.py -v", commands)

    def test_structured_yaml_block_is_parsed(self):
        report_text = (
            "## Verification\n\n"
            "```yaml\n"
            "verification:\n"
            "  - command: python3 -m pytest source/tests/test_foo.py\n"
            "  - python3 -m pytest source/tests/test_bar.py\n"
            "```\n"
        )
        commands = self.gk._extract_declared_commands(report_text)
        self.assertIn("python3 -m pytest source/tests/test_foo.py", commands)
        self.assertIn("python3 -m pytest source/tests/test_bar.py", commands)

    def test_original_bullet_style_still_works_unchanged(self):
        report_text = "## Verification\n- **Verification Command**: `pytest -v`\n"
        commands = self.gk._extract_declared_commands(report_text)
        self.assertEqual(commands, ["pytest -v"])

    def test_zero_parsed_but_manifest_expects_commands_fails_loudly(self):
        # This is the exact bug: a report with a Verification-shaped
        # section but an unparseable command must never be reported the
        # same way as "nothing was ever meant to be checked here."
        report_text = "## Verification\nWe ran the tests and they passed.\n"
        ok, findings = self.gk._check_verification_presence(report_text, ["some_script.py"])
        self.assertFalse(ok)
        self.assertTrue(any("UNPARSEABLE" in f for f in findings))

    def test_zero_parsed_and_nothing_expected_is_a_clean_pass(self):
        report_text = "## Definition of Done\nAll items checked.\n"
        ok, findings = self.gk._check_verification_presence(report_text, [])
        self.assertTrue(ok)
        self.assertEqual(findings, [])


class TestD046RequiredSectionsVsTemplate(unittest.TestCase):
    """D-046: DEFAULT_REQUIRED_SECTIONS must match headings that actually
    exist in implementor_spec.md's own contract_report.md template -- this
    is the exact root cause of the reported CoreMesh C13-01 rejection."""

    def setUp(self):
        self.gk = _load_gatekeeper()

    def test_default_required_sections_all_match_real_template_headings(self):
        findings = self.gk._self_check_required_sections_vs_template()
        self.assertEqual(findings, [], msg=f"DEFAULT_REQUIRED_SECTIONS drifted from the "
                                            f"real template again: {findings}")

    def test_default_no_longer_contains_the_never_matching_old_entries(self):
        self.assertNotIn("objective", self.gk.DEFAULT_REQUIRED_SECTIONS)
        self.assertNotIn("evidence", self.gk.DEFAULT_REQUIRED_SECTIONS)


class _TempProjectTestCase(unittest.TestCase):
    """Shared fixture: a real git repo with a nested project/ repo, one
    chunk, one contract -- used by the begin/finalize/preflight/
    delegation/clear-takethis lifecycle tests below."""

    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="gk_v230_test_")
        self.root = Path(self.tmp)
        self.factory_dir = self.root / "factory"
        shutil.copytree(GATEKEEPER_PATH.parent, self.factory_dir)
        self._run(["git", "init", "-q"], cwd=self.root)
        self._run(["git", "config", "user.email", "t@t.local"], cwd=self.root)
        self._run(["git", "config", "user.name", "T"], cwd=self.root)
        (self.root / "project").mkdir()
        self._run(["git", "init", "-q"], cwd=self.root / "project")
        self._run(["git", "config", "user.email", "t@t.local"], cwd=self.root / "project")
        self._run(["git", "config", "user.name", "T"], cwd=self.root / "project")
        (self.root / "source" / "tests").mkdir(parents=True)
        (self.root / "source" / "hello.py").write_text("def add(a, b):\n    return a + b\n")
        (self.root / "source" / "tests" / "test_hello.py").write_text(
            "from source.hello import add\ndef test_add():\n    assert add(2, 2) == 4\n"
        )
        (self.root / "project" / "chunks" / "chunk01").mkdir(parents=True)
        manifest = self.root / "project" / "chunks" / "chunk01" / "execution_manifest.yaml"
        manifest.write_text(
            "chunk: chunk01\n"
            "contracts:\n"
            "  - id: C01-01\n"
            "    risk_tier: medium\n"
            "    scientific_claim_tier: NONE\n"
            "    implementation_owner: implementor\n"
            "    allowed_files: [source/hello.py, source/tests/test_hello.py]\n"
            "    frozen_files: []\n"
            "    verification_scripts: [source/tests/test_hello.py]\n"
            "    dependencies: []\n"
            "repository_preconditions: {clean_worktree_required: false, previous_chunk_approved: false}\n"
            "completion_dependencies: {chunk_report_required: true, gatekeeper_pass_required: true}\n"
        )
        self.manifest_path = manifest
        (self.root / ".gitignore").write_text("project/\n__pycache__/\n*.pyc\n")
        self._run(["git", "add", "-A"], cwd=self.root)
        self._run(["git", "commit", "-q", "-m", "initial"], cwd=self.root)

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def _run(self, argv, cwd=None):
        r = subprocess.run(argv, cwd=cwd or self.root, capture_output=True, text=True, timeout=30)
        return r

    def _gk(self, args, cwd=None):
        return subprocess.run(
            [sys.executable, str(self.factory_dir / "gatekeeper.py")] + args,
            cwd=cwd or self.root, capture_output=True, text=True, timeout=60,
        )


class TestD041BeginFinalizeLifecycle(unittest.TestCase):
    """D-041: begin/finalize as a transactional, ceremony-collapsing
    lifecycle -- reproduces the KLStream C10-01 shape (a report/telemetry
    claiming COMPLETE while check's own gate would actually fail)."""

    def setUp(self):
        self.case = _TempProjectTestCase()
        self.case.setUp()

    def tearDown(self):
        self.case.tearDown()

    def test_begin_writes_skeleton_with_all_required_headings(self):
        r = self.case._gk(["begin", "--contract", "C01-01", "--manifest",
                            str(self.case.manifest_path)])
        self.assertEqual(r.returncode, 0, msg=r.stdout + r.stderr)
        report = (self.case.manifest_path.parent / "reports" / "C01-01" / "contract_report.md")
        self.assertTrue(report.exists())
        text = report.read_text()
        for heading in ("Verification Summary", "Definition of Done", "Final Status"):
            self.assertIn(heading, text)

    def test_finalize_refuses_a_report_that_never_ran_check_successfully(self):
        self.case._gk(["begin", "--contract", "C01-01", "--manifest", str(self.case.manifest_path)])
        report = (self.case.manifest_path.parent / "reports" / "C01-01" / "contract_report.md")
        # Leave the skeleton exactly as begin wrote it -- still all TODOs,
        # Final Status is not COMPLETE.
        r = self.case._gk(["finalize", "--contract", "C01-01", "--manifest",
                            str(self.case.manifest_path), "--no-commit"])
        self.assertEqual(r.returncode, 20)
        self.assertIn("not COMPLETE", r.stdout)

    def test_finalize_writes_a_completion_receipt_on_a_real_pass(self):
        self.case._gk(["begin", "--contract", "C01-01", "--manifest", str(self.case.manifest_path)])
        report = (self.case.manifest_path.parent / "reports" / "C01-01" / "contract_report.md")
        report.write_text(
            "# Contract Report: C01-01\n\n"
            "## Contract Information\nContract ID: C01-01\n\n"
            "## Verification Summary\n"
            "- **Verification Command**: `python3 -m pytest source/tests/test_hello.py -v`\n"
            "1 passed.\n\n"
            "## Definition of Done\nDone.\n\n"
            "## Final Status\nCOMPLETE\n"
        )
        r = self.case._gk(["finalize", "--contract", "C01-01", "--manifest",
                            str(self.case.manifest_path)])
        self.assertEqual(r.returncode, 0, msg=r.stdout + r.stderr)
        receipt = (self.case.root / "project" / ".gatekeeper" / "state" / "C01-01.complete.json")
        self.assertTrue(receipt.exists())
        data = json.loads(receipt.read_text())
        self.assertEqual(data["contract"], "C01-01")
        self.assertIsNotNone(data["report_sha256"])

    def test_finalize_detects_an_unexpected_out_of_scope_change(self):
        # D-041's scoped delta: a file changed during the contract that is
        # NOT in allowed_files must be caught, replacing the old blanket
        # --allow-dirty bypass that could not distinguish this from a
        # pre-existing dirty file.
        self.case._gk(["begin", "--contract", "C01-01", "--manifest", str(self.case.manifest_path)])
        (self.case.root / "source" / "unrelated.py").write_text("x = 1\n")
        report = (self.case.manifest_path.parent / "reports" / "C01-01" / "contract_report.md")
        report.write_text(
            "# Contract Report: C01-01\n\n## Verification Summary\n"
            "- **Verification Command**: `python3 -m pytest source/tests/test_hello.py -v`\n"
            "1 passed.\n\n## Definition of Done\nDone.\n\n## Final Status\nCOMPLETE\n"
        )
        r = self.case._gk(["finalize", "--contract", "C01-01", "--manifest",
                            str(self.case.manifest_path), "--no-commit"])
        self.assertEqual(r.returncode, 20)
        self.assertIn("unrelated.py", r.stdout)

    def test_finalize_never_flags_project_dir_itself_as_unexpected(self):
        # C60: project/ is Factory-governance territory by construction,
        # never counted against outer-repo allowed_files, regardless of
        # .gitignore state (this test's outer repo has no .gitignore for
        # project/ at all).
        self.case._gk(["begin", "--contract", "C01-01", "--manifest", str(self.case.manifest_path)])
        report = (self.case.manifest_path.parent / "reports" / "C01-01" / "contract_report.md")
        report.write_text(
            "# Contract Report: C01-01\n\n## Verification Summary\n"
            "- **Verification Command**: `python3 -m pytest source/tests/test_hello.py -v`\n"
            "1 passed.\n\n## Definition of Done\nDone.\n\n## Final Status\nCOMPLETE\n"
        )
        r = self.case._gk(["finalize", "--contract", "C01-01", "--manifest",
                            str(self.case.manifest_path), "--no-commit"])
        self.assertEqual(r.returncode, 0, msg=r.stdout + r.stderr)


class TestD039D040ContractPreflight(unittest.TestCase):
    """D-039/D-040: reproduces the Sentinel-GL C01-03 shape -- a
    verification/acquisition glob matching a file outside allowed_files,
    caught before implementation begins instead of discovered mid-contract."""

    def setUp(self):
        self.case = _TempProjectTestCase()
        self.case.setUp()
        # A second, out-of-scope acquisition module the contract does NOT
        # list in allowed_files, but which a wildcard scan would still match.
        (self.case.root / "source" / "legacy_acquisition.py").write_text("# legacy\n")

    def tearDown(self):
        self.case.tearDown()

    def test_wildcard_reach_outside_allowed_files_fails_preflight(self):
        r = self.case._gk([
            "contract-preflight", "--contract", "C01-01", "--manifest",
            str(self.case.manifest_path), "--acquisition-scripts", "source/*.py",
        ])
        self.assertEqual(r.returncode, 3)
        self.assertIn("legacy_acquisition.py", r.stdout)

    def test_readonly_verification_flag_downgrades_to_warning(self):
        r = self.case._gk([
            "contract-preflight", "--contract", "C01-01", "--manifest",
            str(self.case.manifest_path), "--acquisition-scripts", "source/*.py",
            "--readonly-verification",
        ])
        self.assertEqual(r.returncode, 0)


class TestD044Delegation(unittest.TestCase):
    """D-044: reproduces the Sentinel-GL Architect-outage shape -- a
    High-risk, Architect-owned contract executed by the Implementor
    requires an active, matching, explicitly-recorded delegation."""

    def setUp(self):
        self.case = _TempProjectTestCase()
        self.case.setUp()
        manifest = self.case.manifest_path
        manifest.write_text(manifest.read_text().replace(
            "risk_tier: medium\n    scientific_claim_tier: NONE\n    implementation_owner: implementor",
            "risk_tier: high\n    scientific_claim_tier: NONE\n    implementation_owner: architect",
        ))

    def tearDown(self):
        self.case.tearDown()

    def test_owner_executor_mismatch_without_delegation_fails(self):
        r = self.case._gk([
            "contract-preflight", "--contract", "C01-01", "--manifest",
            str(self.case.manifest_path), "--executor", "implementor",
        ])
        self.assertEqual(r.returncode, 21)

    def test_matching_delegation_record_allows_it(self):
        d = self.case._gk([
            "delegate", "--chunk", "chunk01", "--original-owner", "architect",
            "--executor", "implementor", "--contracts", "C01-01",
            "--authorized-by", "Human, test: Architect unreachable, proceed with Implementor.",
        ])
        self.assertEqual(d.returncode, 0, msg=d.stdout + d.stderr)
        r = self.case._gk([
            "contract-preflight", "--contract", "C01-01", "--manifest",
            str(self.case.manifest_path), "--executor", "implementor",
        ])
        self.assertEqual(r.returncode, 0, msg=r.stdout + r.stderr)


class TestD043ClearTakethisArchives(unittest.TestCase):
    """D-043: clear-takethis must archive, not delete, by default --
    reproduces exactly the assumption Sentinel-GL's report named
    ('the Human already retrieved the prior bundle') as unverifiable."""

    def setUp(self):
        self.case = _TempProjectTestCase()
        self.case.setUp()
        (self.case.root / "TAKE_THIS").mkdir()
        (self.case.root / "TAKE_THIS" / "chunk01_report.md").write_text("hello")

    def tearDown(self):
        self.case.tearDown()

    def test_default_behavior_archives_not_deletes(self):
        r = self.case._gk(["clear-takethis", "--chunk", "chunk01"])
        self.assertEqual(r.returncode, 0, msg=r.stdout + r.stderr)
        self.assertFalse((self.case.root / "TAKE_THIS" / "chunk01_report.md").exists())
        archived = list((self.case.root / "TAKE_THIS_ARCHIVE").rglob("chunk01_report.md"))
        self.assertEqual(len(archived), 1)

    def test_purge_flag_restores_old_delete_behavior(self):
        r = self.case._gk(["clear-takethis", "--purge"])
        self.assertEqual(r.returncode, 0, msg=r.stdout + r.stderr)
        self.assertFalse((self.case.root / "TAKE_THIS" / "chunk01_report.md").exists())
        self.assertFalse((self.case.root / "TAKE_THIS_ARCHIVE").exists())


class TestD047ManifestPreconditions(unittest.TestCase):
    """D-047: repository_preconditions.previous_chunk_approved, declared
    in the schema since it was written, is now actually enforced."""

    def setUp(self):
        self.case = _TempProjectTestCase()
        self.case.setUp()
        manifest = self.case.manifest_path
        manifest.write_text(manifest.read_text().replace(
            "previous_chunk_approved: false", "previous_chunk_approved: true"))

    def tearDown(self):
        self.case.tearDown()

    def test_missing_previous_chunk_report_fails(self):
        r = self.case._gk(["contract-preflight", "--contract", "C01-01",
                            "--manifest", str(self.case.manifest_path)])
        self.assertEqual(r.returncode, 3)
        self.assertIn("PREVIOUS CHUNK NOT APPROVED", r.stdout)

    def test_approved_previous_chunk_report_passes(self):
        prev = self.case.manifest_path.parent.parent / "chunk00"
        prev.mkdir()
        (prev / "chunk_report.md").write_text("Final Recommendation: APPROVED\n")
        r = self.case._gk(["contract-preflight", "--contract", "C01-01",
                            "--manifest", str(self.case.manifest_path)])
        self.assertEqual(r.returncode, 0, msg=r.stdout + r.stderr)


class TestD048TelemetryAndDecisionLog(unittest.TestCase):
    """D-048: telemetry/decision-log automation -- auto-incrementing
    decision IDs, and self_review_attempts auto-counted from real
    finalize attempts rather than hand-typed 1 regardless of what
    actually happened (CoreMesh: reported trivial across 65 contracts)."""

    def setUp(self):
        self.case = _TempProjectTestCase()
        self.case.setUp()

    def tearDown(self):
        self.case.tearDown()

    def test_log_decision_auto_increments_across_calls(self):
        r1 = self.case._gk(["log-decision", "--role", "architect", "--decision", "First",
                             "--reason", "r", "--benefit", "b"])
        r2 = self.case._gk(["log-decision", "--role", "architect", "--decision", "Second",
                             "--reason", "r", "--benefit", "b"])
        self.assertEqual(r1.returncode, 0)
        self.assertEqual(r2.returncode, 0)
        log = (self.case.root / "project" / "evolution" / "decision_log.md").read_text()
        self.assertIn("## D-001", log)
        self.assertIn("## D-002", log)

    def test_self_review_attempts_reflects_real_attempt_count(self):
        self.case._gk(["begin", "--contract", "C01-01", "--manifest", str(self.case.manifest_path)])
        report = (self.case.manifest_path.parent / "reports" / "C01-01" / "contract_report.md")
        # Attempt 1: deliberately incomplete -- fails.
        self.case._gk(["finalize", "--contract", "C01-01", "--manifest",
                        str(self.case.manifest_path), "--no-commit"])
        # Attempt 2: now fix it and pass.
        report.write_text(
            "# Contract Report: C01-01\n\n## Verification Summary\n"
            "- **Verification Command**: `python3 -m pytest source/tests/test_hello.py -v`\n"
            "1 passed.\n\n## Definition of Done\nDone.\n\n## Final Status\nCOMPLETE\n"
        )
        self.case._gk(["finalize", "--contract", "C01-01", "--manifest",
                        str(self.case.manifest_path), "--no-commit"])
        telemetry_path = self.case.root / "project" / "evolution" / "telemetry.jsonl"
        events = [json.loads(l) for l in telemetry_path.read_text().splitlines() if l.strip()]
        complete_events = [e for e in events if e.get("event") == "contract_complete"]
        self.assertEqual(len(complete_events), 1)
        self.assertEqual(complete_events[0]["self_review_attempts"], 2)


class TestD049OutboundSecrecyScan(unittest.TestCase):
    """D-049: Factory-internal identifiers leaking into a release-bound
    artifact -- reproduces the AML/collusion-ring project's explicit request."""

    def setUp(self):
        self.gk = _load_gatekeeper()
        self.tmp = tempfile.mkdtemp(prefix="gk_v230_secrecy_")

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_chunk_and_contract_ids_are_flagged(self):
        p = Path(self.tmp) / "manuscript.md"
        p.write_text("As shown in chunk19, contract C19-02 confirmed the result.\n")
        findings = self.gk._scan_factory_identifiers([str(p)])
        self.assertTrue(any("chunk identifier" in f for f in findings))
        self.assertTrue(any("contract ID" in f for f in findings))

    def test_clean_manuscript_produces_no_findings(self):
        p = Path(self.tmp) / "manuscript.md"
        p.write_text("This paper studies topological deep learning for AML detection.\n")
        findings = self.gk._scan_factory_identifiers([str(p)])
        self.assertEqual(findings, [])


class TestD050Supersession(unittest.TestCase):
    """D-050: reproduces the AML/collusion-ring project's Chunk 19
    superseding stale Chunk 18 claims -- a superseded report must not
    block release certification."""

    def setUp(self):
        self.case = _TempProjectTestCase()
        self.case.setUp()

    def tearDown(self):
        self.case.tearDown()

    def test_superseded_report_moves_to_historical_not_hard_findings(self):
        r1 = (self.case.manifest_path.parent / "reports" / "C01-01")
        r1.mkdir(parents=True)
        (r1 / "contract_report.md").write_text(
            "# Contract Report: C01-01\n\n## Final Status\nFLAGGED\n"
        )
        (self.case.manifest_path.parent / "chunk02").mkdir(parents=True, exist_ok=True)
        r2_dir = self.case.manifest_path.parent.parent / "chunk02" / "reports" / "C02-01"
        r2_dir.mkdir(parents=True)
        (r2_dir / "contract_report.md").write_text(
            "# Contract Report: C02-01\n\nSuperseded-By: C02-01\n\n## Final Status\nCOMPLETE\n"
        )
        r = self.case._gk(["release-certify", "--chunks-dir",
                            str(self.case.manifest_path.parent.parent)])
        self.assertIn("Historical", r.stdout)
        self.assertNotIn("NOT COMPLETE: ", r.stdout.split("Historical")[0].split(
            f"{r1}")[-1] if str(r1) in r.stdout else "")


class TestD053ReleaseStatus(unittest.TestCase):
    """D-053: release-status must distinguish fresh-and-certified from
    stale/missing/not-certified -- the direct fix for the reported
    cross-session readiness-verdict inconsistency."""

    def setUp(self):
        self.case = _TempProjectTestCase()
        self.case.setUp()

    def tearDown(self):
        self.case.tearDown()

    def test_no_certificate_yet_is_not_ready(self):
        r = self.case._gk(["release-status", "--chunks-dir",
                            str(self.case.manifest_path.parent.parent)])
        self.assertEqual(r.returncode, 19)

    def test_fresh_certificate_reports_ready(self):
        chunks_dir = self.case.manifest_path.parent.parent
        reports_dir = self.case.manifest_path.parent / "reports" / "C01-01"
        reports_dir.mkdir(parents=True)
        (reports_dir / "contract_report.md").write_text(
            "# Contract Report: C01-01\n\n## Final Status\nCOMPLETE\n"
        )
        self.case._gk(["release-certify", "--chunks-dir", str(chunks_dir)])
        r = self.case._gk(["release-status", "--chunks-dir", str(chunks_dir)])
        self.assertEqual(r.returncode, 0, msg=r.stdout + r.stderr)
        self.assertIn("FRESH", r.stdout)


if __name__ == "__main__":
    unittest.main()
