"""Regression tests for v3.2.0 state, command, and transfer hardening."""
import json
import tempfile
import unittest
import zipfile
from unittest.mock import patch
from pathlib import Path

FACTORY = Path(__file__).resolve().parents[1]
import sys
sys.path.insert(0, str(FACTORY))
import gatekeeper as g
from engine.bundle import create_bundle, verify_bundle
from engine.io import EvidenceError, read_json
from tests.test_v3 import fixture


class V32HardeningTests(unittest.TestCase):
    def test_inline_interpreter_code_is_rejected(self):
        with self.assertRaises(EvidenceError):
            g.safe_args(['python3', '-c', 'print(1)'], Path('/tmp/run'), 1, 'x')
        with self.assertRaises(EvidenceError):
            g.safe_args(['env', 'python3', '-c', 'print(1)'], Path('/tmp/run'), 1, 'x')

    def test_code_loading_environment_is_rejected(self):
        with patch.dict(g.os.environ, {'PYTHONPATH': '/tmp/injected'}, clear=False):
            with self.assertRaises(EvidenceError):
                g.execution_env(7)

    def test_json_rejects_overflow_number(self):
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / 'overflow.json'
            p.write_text('{"value": 1e999}')
            with self.assertRaises(EvidenceError):
                read_json(p)

    def test_bundle_manifest_detects_byte_tampering(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td); source = root / 'evidence.txt'; source.write_text('original')
            archive = root / 'bundle.zip'
            create_bundle(archive, {'evidence.txt': source}, {'factory_version': '3.2.0'})
            self.assertEqual(len(verify_bundle(archive)['files']), 1)
            tampered = root / 'tampered.zip'
            with zipfile.ZipFile(archive) as old, zipfile.ZipFile(tampered, 'w') as new:
                for info in old.infolist():
                    new.writestr(info, b'changed' if info.filename == 'evidence.txt' else old.read(info.filename))
            with self.assertRaises(EvidenceError):
                verify_bundle(tampered)

    def test_generated_reports_cannot_be_frozen(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td); plan = fixture(root)
            plan['frozen_paths'].append('project/audit_report.json')
            from engine.io import write_json
            write_json(root / g.ROOT_PLAN, plan)
            with self.assertRaises(EvidenceError):
                g.freeze(root)

    def test_project_directory_cannot_be_frozen_as_a_wildcard(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td); plan = fixture(root)
            plan['frozen_paths'] = ['project', 'source', 'data']
            from engine.io import write_json
            write_json(root / g.ROOT_PLAN, plan)
            with self.assertRaises(EvidenceError):
                g.freeze(root)

    def test_command_must_reference_declared_code_path(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td); plan = fixture(root)
            plan['experiments'][0]['command'] = [sys.executable, '-m', 'json.tool',
                                                '{run_dir}', '{seed}', '{experiment_id}']
            from engine.io import write_json
            write_json(root / g.ROOT_PLAN, plan)
            with self.assertRaises(EvidenceError):
                g.freeze(root)

    def test_new_execution_revokes_old_certificate(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td); fixture(root); g.freeze(root); self.assertEqual(g.run_exp(root, 'known'), 0)
            cert = root / 'project/RELEASE_CERTIFICATION.json'; cert.write_text('{}')
            self.assertEqual(g.run_exp(root, 'known'), 0)
            self.assertFalse(cert.exists())


if __name__ == '__main__':
    unittest.main()
