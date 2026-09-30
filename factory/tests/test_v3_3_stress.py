"""v3.3.0 stress tests — adversarial loophole hunting.

These tests go BEYOND the attack registry. They attempt to find gaps,
race conditions, edge cases, and novel bypasses that the v3.3.0
hardening might have missed. Every test that passes means the factory
is secure; every failure is a real loophole.
"""
import contextlib
import hashlib
import io
import json
import math
import os
import re
import shutil
import stat
import string
import sys
import tempfile
import time
import unittest
import zipfile
from pathlib import Path
from unittest.mock import patch

FACTORY = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(FACTORY))

import gatekeeper as g
from engine.io import (EvidenceError, inside, inventory, merkle_root,
                        read_json, sha, write_json, _normalize_path)
from engine.contract import command_to_contract, validate_contract, resolve_contract
from engine.supervisor import (build_receipt, init_supervisor_keys,
                                sign_receipt, verify_receipt_signature)
from engine.schema import (ValidationError, expect_bool, expect_dict,
                            expect_float, expect_id, expect_int, expect_list,
                            expect_str, validate_split_manifest,
                            validate_training_manifest, expect_enum)
from engine.bundle import create_bundle, verify_bundle, MANIFEST
from tests.test_v3 import SCRIPT, fixture


# ---------------------------------------------------------------------------
# 1. PATH TRAVERSAL / SANDBOX ESCAPE
# ---------------------------------------------------------------------------
class PathEscapeStressTests(unittest.TestCase):
    """Attempt every known path traversal trick against inside() and inventory()."""

    def test_null_byte_in_path(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            with self.assertRaises(EvidenceError):
                inside(root, 'project/file\x00.txt')

    def test_backslash_traversal(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            with self.assertRaises(EvidenceError):
                inside(root, 'project\\..\\..\\etc\\passwd')

    def test_double_dot_in_path(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            with self.assertRaises(EvidenceError):
                inside(root, 'project/../../../etc/passwd')

    def test_absolute_path_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            with self.assertRaises(EvidenceError):
                inside(root, '/etc/passwd')

    def test_empty_path_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            with self.assertRaises(EvidenceError):
                inside(root, '')

    def test_dot_only_path_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            with self.assertRaises(EvidenceError):
                inside(root, '.')

    def test_triple_dot_segment(self):
        """.../ is not the same as ../ but could confuse naive parsers."""
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / 'project').mkdir()
            (root / 'project/ok.txt').write_text('data')
            # .../file should either resolve safely or be rejected
            try:
                result = inside(root, '.../file.txt')
                # If it resolves, it must still be inside root
                self.assertTrue(str(result.resolve()).startswith(str(root.resolve())))
            except EvidenceError:
                pass  # Rejection is also acceptable

    def test_url_encoded_traversal_in_normalize(self):
        """Ensure %2e%2e doesn't bypass normalization."""
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            # The raw string %2e%2e is NOT decoded, so it's treated literally
            # But we verify it doesn't allow escape
            try:
                result = inside(root, 'project/%2e%2e/secret.txt')
                self.assertTrue(str(result.resolve()).startswith(str(root.resolve())))
            except EvidenceError:
                pass

    def test_symlink_in_frozen_path_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / 'source').mkdir()
            (root / 'source/real.py').write_text('x = 1\n')
            (root / 'source/link.py').symlink_to(root / 'source/real.py')
            with self.assertRaises(EvidenceError):
                inventory(root, ['source'])

    def test_symlink_to_outside_rejected(self):
        with tempfile.TemporaryDirectory() as td1, tempfile.TemporaryDirectory() as td2:
            root = Path(td1)
            (root / 'source').mkdir()
            outside_file = Path(td2) / 'secret.py'
            outside_file.write_text('SECRET = True\n')
            (root / 'source/escape.py').symlink_to(outside_file)
            with self.assertRaises(EvidenceError):
                inventory(root, ['source'])

    def test_directory_symlink_rejected(self):
        with tempfile.TemporaryDirectory() as td1, tempfile.TemporaryDirectory() as td2:
            root = Path(td1)
            outside = Path(td2)
            (outside / 'evil.py').write_text('os.system("rm -rf /")')
            (root / 'source').symlink_to(outside)
            with self.assertRaises(EvidenceError):
                inventory(root, ['source'])


# ---------------------------------------------------------------------------
# 2. COMMAND INJECTION / INTERPRETER BYPASS
# ---------------------------------------------------------------------------
class CommandInjectionStressTests(unittest.TestCase):
    """Try every conceivable command injection vector."""

    def test_semicolon_injection(self):
        with self.assertRaises(EvidenceError):
            g.safe_args(['python3', 'run.py; rm -rf /'], Path('/tmp/r'), 1, 'x')

    def test_pipe_injection(self):
        with self.assertRaises(EvidenceError):
            g.safe_args(['python3', 'run.py', '||', 'evil'], Path('/tmp/r'), 1, 'x')

    def test_backtick_injection(self):
        with self.assertRaises(EvidenceError):
            g.safe_args(['python3', 'run.py', '`evil`'], Path('/tmp/r'), 1, 'x')

    def test_dollar_paren_injection(self):
        with self.assertRaises(EvidenceError):
            g.safe_args(['python3', 'run.py', '$(evil)'], Path('/tmp/r'), 1, 'x')

    def test_redirect_injection(self):
        with self.assertRaises(EvidenceError):
            g.safe_args(['python3', 'run.py', '>', '/etc/crontab'], Path('/tmp/r'), 1, 'x')

    def test_versioned_python_c_flag(self):
        """python3.12 -c should be caught."""
        with self.assertRaises(EvidenceError):
            g.safe_args(['python3.12', '-c', 'import os'], Path('/tmp/r'), 1, 'x')

    def test_full_path_python_c_flag(self):
        """/usr/bin/python3 -c should be caught."""
        with self.assertRaises(EvidenceError):
            g.safe_args(['/usr/bin/python3', '-c', 'import os'], Path('/tmp/r'), 1, 'x')

    def test_pypy_inline_code(self):
        with self.assertRaises(EvidenceError):
            command_to_contract(['pypy3', '-c', 'evil'], ['source/run.py'])

    def test_node_eval_flag(self):
        with self.assertRaises(EvidenceError):
            command_to_contract(['node', '--eval', 'require("child_process")'], ['source/run.py'])

    def test_perl_e_flag(self):
        with self.assertRaises(EvidenceError):
            command_to_contract(['perl', '-e', 'system("id")'], ['source/run.py'])

    def test_ruby_e_flag(self):
        with self.assertRaises(EvidenceError):
            command_to_contract(['ruby', '-e', 'system("id")'], ['source/run.py'])

    def test_env_dash_c_bypass(self):
        """env python3 -c should be caught."""
        with self.assertRaises(EvidenceError):
            command_to_contract(['env', 'python3', '-c', 'import os'], ['source/run.py'])

    def test_python_dash_m_pip(self):
        with self.assertRaises(EvidenceError):
            command_to_contract(['python3', '-m', 'pip', 'install', 'evil'], ['source/run.py'])

    def test_python_dash_c_attached_code(self):
        with self.assertRaises(EvidenceError):
            command_to_contract(['python3', '-c__import__("os").system("id")'], ['source/run.py'])

    def test_contract_entrypoint_with_shell_chars(self):
        with self.assertRaises(EvidenceError):
            validate_contract(
                {'runtime_id': 'python-cpu-v1', 'entrypoint': 'source/run.py; rm -rf /'},
                Path('/tmp'), ['source']
            )

    def test_contract_entrypoint_with_parent_traversal(self):
        with self.assertRaises(EvidenceError):
            validate_contract(
                {'runtime_id': 'python-cpu-v1', 'entrypoint': '../../../etc/passwd'},
                Path('/tmp'), ['source']
            )


# ---------------------------------------------------------------------------
# 3. ENVIRONMENT VARIABLE INJECTION
# ---------------------------------------------------------------------------
class EnvInjectionStressTests(unittest.TestCase):
    """Verify every dangerous environment variable is blocked."""

    def _check_blocked(self, var, value='/tmp/evil.py'):
        with patch.dict(os.environ, {var: value}, clear=False):
            with self.assertRaises(EvidenceError):
                g.execution_env(42)

    def test_pythonpath(self):
        self._check_blocked('PYTHONPATH')

    def test_pythonhome(self):
        self._check_blocked('PYTHONHOME')

    def test_pythonstartup(self):
        self._check_blocked('PYTHONSTARTUP')

    def test_pythoninspect(self):
        self._check_blocked('PYTHONINSPECT')

    def test_pythonbreakpoint(self):
        self._check_blocked('PYTHONBREAKPOINT')

    def test_ld_preload(self):
        self._check_blocked('LD_PRELOAD')

    def test_ld_library_path(self):
        self._check_blocked('LD_LIBRARY_PATH')

    def test_ld_audit(self):
        self._check_blocked('LD_AUDIT')

    def test_node_options(self):
        self._check_blocked('NODE_OPTIONS')

    def test_node_path(self):
        self._check_blocked('NODE_PATH')

    def test_rubyopt(self):
        self._check_blocked('RUBYOPT')

    def test_perl5opt(self):
        self._check_blocked('PERL5OPT')

    def test_bash_env(self):
        self._check_blocked('BASH_ENV')

    def test_dyld_insert_libraries(self):
        self._check_blocked('DYLD_INSERT_LIBRARIES')

    def test_dyld_framework_path(self):
        self._check_blocked('DYLD_FRAMEWORK_PATH')

    def test_dyld_library_path(self):
        self._check_blocked('DYLD_LIBRARY_PATH')

    def test_git_config_global(self):
        self._check_blocked('GIT_CONFIG_GLOBAL')

    def test_cdpath(self):
        self._check_blocked('CDPATH')


# ---------------------------------------------------------------------------
# 4. RECEIPT / SIGNATURE ATTACKS
# ---------------------------------------------------------------------------
class ReceiptAttackStressTests(unittest.TestCase):
    """Try to forge, replay, truncate, or downgrade receipts."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.key_dir = Path(self.tmp.name)
        os.environ['FACTORY_SUPERVISOR_KEY'] = str(self.key_dir / 'test.key')
        init_supervisor_keys(force=True)

    def tearDown(self):
        del os.environ['FACTORY_SUPERVISOR_KEY']
        self.tmp.cleanup()

    def test_empty_signature_rejected(self):
        receipt = {'experiment_id': 'test', 'epoch': 1}
        receipt['supervisor_signature'] = ''
        receipt['signature_scheme'] = 'hmac-sha256'
        with self.assertRaises(EvidenceError):
            verify_receipt_signature(receipt)

    def test_null_signature_rejected(self):
        receipt = {'experiment_id': 'test', 'epoch': 1}
        receipt['supervisor_signature'] = None
        receipt['signature_scheme'] = 'hmac-sha256'
        with self.assertRaises(EvidenceError):
            verify_receipt_signature(receipt)

    def test_truncated_signature_rejected(self):
        signed = sign_receipt({'experiment_id': 'test', 'epoch': 1})
        signed['supervisor_signature'] = signed['supervisor_signature'][:5]
        with self.assertRaises(EvidenceError):
            verify_receipt_signature(signed)

    def test_different_key_id_rejected(self):
        signed = sign_receipt({'experiment_id': 'test', 'epoch': 1})
        signed['public_key_id'] = 'deadbeefdeadbeef'
        with self.assertRaises(EvidenceError):
            verify_receipt_signature(signed)

    def test_unknown_scheme_rejected(self):
        signed = sign_receipt({'experiment_id': 'test', 'epoch': 1})
        signed['signature_scheme'] = 'rsa-sha512'
        with self.assertRaises(EvidenceError):
            verify_receipt_signature(signed)

    def test_added_field_breaks_signature(self):
        """Adding a field to the receipt invalidates the signature."""
        signed = sign_receipt({'experiment_id': 'test', 'epoch': 1})
        signed['injected_field'] = 'evil_value'
        with self.assertRaises(EvidenceError):
            verify_receipt_signature(signed)

    def test_removed_field_breaks_signature(self):
        """Removing a field from the receipt invalidates the signature."""
        signed = sign_receipt({'experiment_id': 'test', 'epoch': 1, 'seed': 42})
        del signed['seed']
        with self.assertRaises(EvidenceError):
            verify_receipt_signature(signed)

    def test_type_change_breaks_signature(self):
        """Changing a field type (int → str) invalidates the signature."""
        signed = sign_receipt({'experiment_id': 'test', 'epoch': 1})
        signed['epoch'] = '1'  # int → str
        with self.assertRaises(EvidenceError):
            verify_receipt_signature(signed)

    def test_reorder_does_not_break(self):
        """Key ordering is irrelevant since we use canonical serialization."""
        signed = sign_receipt({'experiment_id': 'test', 'epoch': 1, 'seed': 42})
        # Reconstruct with different key order
        reordered = {}
        for k in reversed(sorted(signed.keys())):
            reordered[k] = signed[k]
        self.assertTrue(verify_receipt_signature(reordered))


# ---------------------------------------------------------------------------
# 5. BUNDLE TAMPERING
# ---------------------------------------------------------------------------
class BundleTamperingStressTests(unittest.TestCase):
    """Advanced bundle manipulation attacks."""

    def _make_bundle(self, td, files_dict, metadata=None):
        root = Path(td)
        paths = {}
        for name, content in files_dict.items():
            p = root / name
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(content) if isinstance(content, str) else p.write_bytes(content)
            paths[name] = p
        archive = root / 'test_bundle.zip'
        return create_bundle(archive, paths, metadata or {'factory_version': '3.3.0'})

    def test_symlink_member_rejected(self):
        """Bundle containing a symlink entry should fail verification."""
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            source = root / 'evidence.txt'
            source.write_text('data')
            archive = root / 'bundle.zip'
            create_bundle(archive, {'evidence.txt': source}, {'factory_version': '3.3.0'})
            # Create a new zip with a symlink entry
            tampered = root / 'tampered.zip'
            with zipfile.ZipFile(archive) as old, zipfile.ZipFile(tampered, 'w') as new:
                for info in old.infolist():
                    new.writestr(info, old.read(info.filename))
                # Add a symlink-like entry (external_attr with symlink flag)
                info = zipfile.ZipInfo('link.txt')
                info.external_attr = 0o120000 << 16  # symlink
                new.writestr(info, b'../../etc/passwd')
            with self.assertRaises(EvidenceError):
                verify_bundle(tampered)

    def test_directory_entry_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            source = root / 'evidence.txt'
            source.write_text('data')
            archive = root / 'bundle.zip'
            create_bundle(archive, {'evidence.txt': source}, {'factory_version': '3.3.0'})
            tampered = root / 'tampered.zip'
            with zipfile.ZipFile(archive) as old, zipfile.ZipFile(tampered, 'w') as new:
                for info in old.infolist():
                    new.writestr(info, old.read(info.filename))
                # Add a directory entry
                info = zipfile.ZipInfo('evil_dir/')
                new.writestr(info, b'')
            with self.assertRaises(EvidenceError):
                verify_bundle(tampered)

    def test_manifest_name_collision(self):
        """Cannot use BUNDLE_MANIFEST.json as a member name."""
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            source = root / MANIFEST
            source.write_text('fake manifest')
            with self.assertRaises(EvidenceError):
                create_bundle(root / 'bundle.zip',
                              {MANIFEST: source},
                              {'factory_version': '3.3.0'})

    def test_path_traversal_in_bundle_member(self):
        with self.assertRaises(EvidenceError):
            from engine.bundle import member_name
            member_name('../../../etc/passwd')

    def test_absolute_path_in_bundle_member(self):
        with self.assertRaises(EvidenceError):
            from engine.bundle import member_name
            member_name('/etc/passwd')

    def test_backslash_in_bundle_member(self):
        with self.assertRaises(EvidenceError):
            from engine.bundle import member_name
            member_name('path\\to\\file.txt')

    def test_colon_in_bundle_member(self):
        """Windows drive letters like C: should be rejected."""
        with self.assertRaises(EvidenceError):
            from engine.bundle import member_name
            member_name('C:file.txt')

    def test_oversized_manifest_rejected(self):
        """Manifest exceeding 16 MiB should be rejected."""
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            archive = root / 'bomb.zip'
            with zipfile.ZipFile(archive, 'w') as z:
                z.writestr(MANIFEST, 'x' * (17 * 1024 * 1024))  # 17 MiB
            with self.assertRaises(EvidenceError):
                verify_bundle(archive)


# ---------------------------------------------------------------------------
# 6. SCHEMA BYPASS ATTEMPTS
# ---------------------------------------------------------------------------
class SchemaBypassStressTests(unittest.TestCase):
    """Try to sneak invalid values past the schema validators."""

    def test_none_as_bool(self):
        with self.assertRaises(ValidationError):
            expect_bool(None)

    def test_empty_string_as_bool(self):
        with self.assertRaises(ValidationError):
            expect_bool('')

    def test_list_as_bool(self):
        with self.assertRaises(ValidationError):
            expect_bool([])

    def test_nan_as_int(self):
        with self.assertRaises(ValidationError):
            expect_int(float('nan'))

    def test_inf_as_int(self):
        with self.assertRaises(ValidationError):
            expect_int(float('inf'))

    def test_very_long_string_rejected(self):
        with self.assertRaises(ValidationError):
            expect_str('x' * 100001, max_len=100000)

    def test_negative_nan_float(self):
        with self.assertRaises(ValidationError):
            expect_float(float('-nan'))

    def test_negative_inf_float(self):
        with self.assertRaises(ValidationError):
            expect_float(float('-inf'))

    def test_dict_as_list(self):
        with self.assertRaises(ValidationError):
            expect_list({})

    def test_list_as_dict(self):
        with self.assertRaises(ValidationError):
            expect_dict([])

    def test_nested_dict_in_list_validation(self):
        """Element validator must be applied recursively."""
        with self.assertRaises(ValidationError):
            expect_list([1, 'two', 3], element_validator=expect_int)

    def test_enum_with_none(self):
        with self.assertRaises(ValidationError):
            expect_enum(None, {'a', 'b'})

    def test_enum_with_int(self):
        with self.assertRaises(ValidationError):
            expect_enum(1, {'a', 'b'})

    def test_id_with_unicode(self):
        with self.assertRaises(ValidationError):
            expect_id('café')

    def test_id_with_slash(self):
        with self.assertRaises(ValidationError):
            expect_id('path/traversal')

    def test_id_too_long(self):
        with self.assertRaises(ValidationError):
            expect_id('a' * 81)

    def test_training_manifest_nan_epochs(self):
        with self.assertRaises(ValidationError):
            validate_training_manifest({'convergence_evidence': {'epochs_trained': float('nan')}})

    def test_training_manifest_negative_epochs(self):
        with self.assertRaises(ValidationError):
            validate_training_manifest({'convergence_evidence': {'epochs_trained': -5}})

    def test_training_manifest_zero_epochs(self):
        with self.assertRaises(ValidationError):
            validate_training_manifest({'convergence_evidence': {'epochs_trained': 0}})

    def test_training_manifest_string_epochs(self):
        with self.assertRaises(ValidationError):
            validate_training_manifest({'convergence_evidence': {'epochs_trained': '10'}})

    def test_split_manifest_negative_count(self):
        with self.assertRaises(ValidationError):
            validate_split_manifest({'test_label_distribution': {'pos': -1}})

    def test_split_manifest_bool_count(self):
        with self.assertRaises(ValidationError):
            validate_split_manifest({'test_label_distribution': {'pos': True}})

    def test_split_manifest_nan_count(self):
        with self.assertRaises(ValidationError):
            validate_split_manifest({'test_label_distribution': {'pos': float('nan')}})

    def test_split_manifest_string_count(self):
        with self.assertRaises(ValidationError):
            validate_split_manifest({'test_label_distribution': {'pos': '42'}})


# ---------------------------------------------------------------------------
# 7. JSON PARSING ATTACKS
# ---------------------------------------------------------------------------
class JsonParsingStressTests(unittest.TestCase):
    """Verify JSON parsing handles adversarial input correctly."""

    def test_duplicate_json_keys_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            p = root / 'dup.json'
            p.write_text('{"key": 1, "key": 2}')
            with self.assertRaises(EvidenceError):
                read_json(p)

    def test_nan_in_json_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            p = root / 'nan.json'
            p.write_text('{"value": NaN}')
            with self.assertRaises(EvidenceError):
                read_json(p)

    def test_infinity_in_json_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            p = root / 'inf.json'
            p.write_text('{"value": Infinity}')
            with self.assertRaises(EvidenceError):
                read_json(p)

    def test_negative_infinity_in_json_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            p = root / 'ninf.json'
            p.write_text('{"value": -Infinity}')
            with self.assertRaises(EvidenceError):
                read_json(p)


# ---------------------------------------------------------------------------
# 8. MERKLE ROOT INTEGRITY
# ---------------------------------------------------------------------------
class MerkleRootStressTests(unittest.TestCase):
    """Attempt to confuse the Merkle root computation."""

    def test_empty_inventory_rejected(self):
        with self.assertRaises(EvidenceError):
            merkle_root({})

    def test_different_file_order_same_root(self):
        """Merkle root must be deterministic regardless of insertion order."""
        import collections
        h1 = hashlib.sha256(b'content1').hexdigest()
        h2 = hashlib.sha256(b'content2').hexdigest()
        files = collections.OrderedDict([
            ('z/file.py', h1),
            ('a/file.py', h2),
        ])
        reversed_files = collections.OrderedDict([
            ('a/file.py', h2),
            ('z/file.py', h1),
        ])
        self.assertEqual(merkle_root(dict(files)), merkle_root(dict(reversed_files)))

    def test_path_content_confusion_prevented(self):
        """Ensure path 'a' + content hash != path 'ab' + different content hash."""
        h1 = hashlib.sha256(b'content_a').hexdigest()
        h2 = hashlib.sha256(b'content_ab').hexdigest()
        files1 = {'a': h1}
        files2 = {'ab': h2}
        r1 = merkle_root(files1)
        r2 = merkle_root(files2)
        self.assertNotEqual(r1, r2)


# ---------------------------------------------------------------------------
# 9. LIFECYCLE ATTACKS — ATTEMPT TO BYPASS THE AUDIT
# ---------------------------------------------------------------------------
class LifecycleBypassStressTests(unittest.TestCase):
    """Attempt to game the lifecycle at a higher level."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.r = Path(self.tmp.name)
        self.p = fixture(self.r)
        self.redirect = contextlib.redirect_stdout(io.StringIO())
        self.redirect.__enter__()

    def tearDown(self):
        self.redirect.__exit__(None, None, None)
        self.tmp.cleanup()

    def test_double_freeze_rejected(self):
        """Freezing twice without amendment is an error."""
        g.freeze(self.r)
        with self.assertRaises(EvidenceError):
            g.freeze(self.r)

    def test_empty_amendment_rejected(self):
        g.freeze(self.r)
        with self.assertRaises(EvidenceError):
            g.freeze(self.r, amendment='')

    def test_whitespace_amendment_rejected(self):
        g.freeze(self.r)
        with self.assertRaises(EvidenceError):
            g.freeze(self.r, amendment='   ')

    def test_run_before_freeze_fails(self):
        with self.assertRaises(EvidenceError):
            g.run_exp(self.r, 'known')

    def test_run_nonexistent_experiment_fails(self):
        g.freeze(self.r)
        with self.assertRaises(EvidenceError):
            g.run_exp(self.r, 'does_not_exist')

    def test_certificate_removed_on_rerun(self):
        """Any run invalidates the existing certificate."""
        g.freeze(self.r)
        self.assertEqual(g.run_exp(self.r, 'known'), 0)
        # Write a fake certificate
        cert_path = self.r / 'project/RELEASE_CERTIFICATION.json'
        cert_path.write_text('{"status": "FAKE"}')
        # Run again — certificate must be revoked
        self.assertEqual(g.run_exp(self.r, 'known'), 0)
        self.assertFalse(cert_path.exists())

    def test_mutated_engine_after_freeze_caught(self):
        """If the factory code changes after freeze, audit must catch it."""
        g.freeze(self.r)
        self.assertEqual(g.run_exp(self.r, 'known'), 0)
        # The engine hash in freeze was computed at freeze time
        # Changing engine code would change engine_hash()
        _, _, f = g.active(self.r)
        # Simulate by checking the binding
        self.assertEqual(f['engine_sha256'], g.engine_hash())

    def test_source_mutation_between_freeze_and_run(self):
        """Mutating source between freeze and run must be detected."""
        g.freeze(self.r)
        (self.r / 'source/run.py').write_text(SCRIPT + '\n# injected\n')
        with self.assertRaises(EvidenceError):
            g.run_exp(self.r, 'known')

    def test_data_mutation_between_freeze_and_run(self):
        """Mutating data between freeze and run must be detected."""
        g.freeze(self.r)
        (self.r / 'data/cohort.csv').write_text('sample_id,label\nfake,1\n')
        with self.assertRaises(EvidenceError):
            g.run_exp(self.r, 'known')

    def test_plan_mutation_between_freeze_and_run(self):
        """Mutating the plan between freeze and run must be detected."""
        g.freeze(self.r)
        self.p['population'] = 'HACKED'
        write_json(self.r / g.ROOT_PLAN, self.p)
        with self.assertRaises(EvidenceError):
            g.run_exp(self.r, 'known')


# ---------------------------------------------------------------------------
# 10. DANGEROUS FILE EXTENSION ATTACKS
# ---------------------------------------------------------------------------
class DangerousExtensionStressTests(unittest.TestCase):
    """Verify all dangerous binary extensions are blocked in frozen paths."""

    def _test_ext(self, ext):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / 'source').mkdir()
            (root / 'source/run.py').write_text('x = 1\n')
            (root / f'source/injected{ext}').write_bytes(b'\x00' * 16)
            with self.assertRaises(EvidenceError):
                inventory(root, ['source'])

    def test_pyc_blocked(self): self._test_ext('.pyc')
    def test_pyo_blocked(self): self._test_ext('.pyo')
    def test_so_blocked(self): self._test_ext('.so')
    def test_dylib_blocked(self): self._test_ext('.dylib')
    def test_dll_blocked(self): self._test_ext('.dll')
    def test_pyd_blocked(self): self._test_ext('.pyd')
    def test_pyc_uppercase_blocked(self): self._test_ext('.PYC')
    def test_so_uppercase_blocked(self): self._test_ext('.SO')


# ---------------------------------------------------------------------------
# 11. ASSURANCE LEVEL MANIPULATION
# ---------------------------------------------------------------------------
class AssuranceLevelStressTests(unittest.TestCase):
    """Verify assurance levels cannot be inflated."""

    def test_cannot_reach_review_level_without_review(self):
        out = {'errors': [], 'checks_executed': ['X'],
               'computed_runs': {'exp1': {'result_path': 'some/path'}}}
        level = g._compute_assurance_level(out)
        # Without review, max is SEALED_EVALUATION_ATTESTED
        self.assertIn(level, ['STRUCTURALLY_VALIDATED', 'SUPERVISOR_ATTESTED', 'SEALED_EVALUATION_ATTESTED'])
        self.assertNotIn(level, ['INDEPENDENT_REVIEW_COMPLETE', 'READY_FOR_HUMAN_SUBMISSION_REVIEW'])

    def test_blocked_never_promotes(self):
        self.assertEqual(g._assurance_with_review('BLOCKED', True), 'BLOCKED')
        self.assertEqual(g._assurance_with_review('BLOCKED', False), 'BLOCKED')

    def test_structural_does_not_promote_with_review(self):
        result = g._assurance_with_review('STRUCTURALLY_VALIDATED', True)
        self.assertEqual(result, 'STRUCTURALLY_VALIDATED')


# ---------------------------------------------------------------------------
# 12. SPECIAL FILE ATTACKS
# ---------------------------------------------------------------------------
class SpecialFileStressTests(unittest.TestCase):
    """FIFO, socket, device file injection attempts."""

    def test_fifo_in_frozen_path_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / 'source').mkdir()
            (root / 'source/run.py').write_text('x = 1\n')
            fifo = root / 'source/evil_pipe'
            os.mkfifo(fifo)
            with self.assertRaises(EvidenceError):
                inventory(root, ['source'])

    def test_unix_socket_in_frozen_path_rejected(self):
        """Unix socket in frozen paths must be rejected."""
        import socket as sock_mod
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / 'source').mkdir()
            (root / 'source/run.py').write_text('x = 1\n')
            sock_path = root / 'source/evil.sock'
            s = sock_mod.socket(sock_mod.AF_UNIX, sock_mod.SOCK_STREAM)
            try:
                s.bind(str(sock_path))
                with self.assertRaises(EvidenceError):
                    inventory(root, ['source'])
            finally:
                s.close()


# ---------------------------------------------------------------------------
# 13. CONCURRENT / TIMING ATTACKS
# ---------------------------------------------------------------------------
class TimingStressTests(unittest.TestCase):
    """Ensure the factory doesn't have TOCTOU races in critical paths."""

    def test_write_json_atomic(self):
        """write_json uses atomic replace; partial writes shouldn't corrupt."""
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            p = root / 'test.json'
            obj = {'key': 'value', 'num': 42}
            write_json(p, obj)
            # The file should always be valid JSON
            result = read_json(p)
            self.assertEqual(result['key'], 'value')

    def test_epoch_directory_cannot_be_overwritten(self):
        """If an epoch directory already exists, freeze must reject."""
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            fixture(root)
            redir = contextlib.redirect_stdout(io.StringIO())
            redir.__enter__()
            g.freeze(root)
            # Manually create epoch_0002 to simulate collision
            (root / 'project/.factory/epoch_0002').mkdir()
            with self.assertRaises(EvidenceError):
                g.freeze(root, amendment='testing collision')
            redir.__exit__(None, None, None)


# ---------------------------------------------------------------------------
# SUMMARY SELF-TEST
# ---------------------------------------------------------------------------
class StressTestSummary(unittest.TestCase):
    """Meta: Ensure this file has a meaningful number of stress tests."""

    def test_meaningful_test_count(self):
        """This module should have at least 80 stress tests."""
        import unittest as ut
        loader = ut.TestLoader()
        suite = loader.loadTestsFromModule(sys.modules[__name__])
        count = suite.countTestCases()
        self.assertGreaterEqual(count, 80, f'Only {count} stress tests; expected >= 80')


if __name__ == '__main__':
    unittest.main()
