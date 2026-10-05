"""Independent regression probes for execution, key and portable bundle boundaries."""
import base64
import importlib.util
import io
import json
import os
import subprocess
import sys
import tempfile
import unittest
import zipfile
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import patch

FACTORY = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(FACTORY))
from engine.bundle import MANIFEST, create_bundle, verify_bundle
from engine.contract import command_to_contract, contract_argv_template, resolve_contract, validate_contract
from engine.io import EvidenceError, digest, merkle_root
from engine.supervisor import (build_receipt, execution_binding, init_supervisor_keys,
                               sign_receipt, supervisor_public_key, verify_execution_record,
                               verify_receipt_signature)

spec = importlib.util.spec_from_file_location('independent_bundle_verifier', FACTORY / 'verify_bundle_standalone.py')
independent = importlib.util.module_from_spec(spec)
spec.loader.exec_module(independent)


class ExecutionIntegrityTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.key = self.root / 'keys' / 'supervisor.key'
        self.environment = patch.dict(os.environ, {'FACTORY_SUPERVISOR_KEY': str(self.key)})
        self.environment.start()
        init_supervisor_keys()

    def tearDown(self):
        self.environment.stop()
        self.temp.cleanup()

    def _record(self):
        inputs = {'source/run.py': 'a' * 64}
        freeze = {'files': inputs, 'snapshot_merkle_root': merkle_root(inputs),
                  'supervisor_public_key': supervisor_public_key()['public_key'],
                  'supervisor_public_key_id': supervisor_public_key()['public_key_id']}
        record = {'factory_version': '3.3.0', 'epoch': 1, 'experiment_id': 'probe', 'seed': 42,
                  'run_nonce': '00000000-0000-4000-8000-000000000001', 'inputs_before': inputs, 'inputs_after': inputs,
                  'outputs': {}, 'argv': [sys.executable, 'source/run.py', '/host/run'],
                  'argv_template': ['runtime:python-cpu-v1', 'source/run.py', '{run_dir}'],
                  'engine_sha256': 'b' * 64, 'interpreter_hash': 'c' * 64,
                  'dependency_lock_hash': 'd' * 64, 'snapshot_merkle_root': freeze['snapshot_merkle_root'],
                  'runtime_id': 'python-cpu-v1', 'exit_code': 0,
                  'started_at': '2026-10-02T00:00:00Z', 'finished_at': '2026-10-02T00:00:01Z'}
        record['supervisor_receipt'] = build_receipt(
            run_nonce=record['run_nonce'], project_id='test-project', epoch=1, experiment_id='probe',
            snapshot_merkle_root=freeze['snapshot_merkle_root'], input_root=digest(inputs),
            runtime_id='python-cpu-v1', interpreter_hash=record['interpreter_hash'],
            dependency_lock_hash=record['dependency_lock_hash'], launch_spec=digest(record['argv_template']),
            seed=42, output_root=digest(record['outputs']), exit_status=0, cpu_time=.1, memory_peak=1024,
            started_at=record['started_at'], finished_at=record['finished_at'], supervisor_version='3.3.0',
            policy_version='3', execution_binding=execution_binding(record),
            engine_sha256=record['engine_sha256'], inputs_after_root=digest(inputs))
        return record, freeze

    def _verify_record(self, record, freeze):
        return verify_execution_record(record, project_id='test-project', epoch=1,
                                       experiment={'id': 'probe', 'seed': 42}, freeze=freeze,
                                       engine_hash='b' * 64)

    def test_verification_never_creates_private_key(self):
        signed = sign_receipt({'message': 'valid'})
        self.key.unlink()
        self.assertTrue(verify_receipt_signature(signed))
        self.assertFalse(self.key.exists())
        self.key.with_suffix('.pub').unlink()
        with self.assertRaises(EvidenceError):
            verify_receipt_signature(signed)
        self.assertFalse(self.key.exists())

    def test_missing_crypto_does_not_publish_symmetric_secret(self):
        other = self.root / 'missing' / 'secret.key'
        with patch.dict(os.environ, {'FACTORY_SUPERVISOR_KEY': str(other)}), patch('engine.supervisor._try_ed25519', return_value=False):
            with self.assertRaises(EvidenceError):
                init_supervisor_keys()
        self.assertFalse(other.exists())
        self.assertFalse(other.with_suffix('.pub').exists())

    def test_secret_is_not_public_material(self):
        public = base64.b64decode(self.key.with_suffix('.pub').read_text().splitlines()[1])
        self.assertNotEqual(public, self.key.read_bytes())
        self.assertEqual(self.key.stat().st_mode & 0o777, 0o600)

    def test_hmac_and_malformed_signature_rejected(self):
        original = sign_receipt({'message': 'valid'})
        for mutation in ({'signature_scheme': 'hmac-sha256'},
                         {'supervisor_signature': original['supervisor_signature'] + '!'},
                         {'public_key_id': '0' * 16}):
            with self.subTest(mutation=mutation):
                with self.assertRaises(EvidenceError):
                    verify_receipt_signature(dict(original, **mutation))

    def test_mismatched_keypair_rejected_at_signing(self):
        self.key.with_suffix('.pub').write_text('# ed25519\n' + base64.b64encode(b'x' * 32).decode() + '\n')
        with self.assertRaises(EvidenceError):
            sign_receipt({'message': 'valid'})

    def test_entire_execution_wrapper_is_bound(self):
        original, freeze = self._record()
        self._verify_record(original, freeze)
        mutations = {'inputs_after': {}, 'argv': ['evil'], 'engine_sha256': 'e' * 64,
                     'runtime_attestation': {'forged': True}, 'exit_code': 1,
                     'record_error': 'hidden failure', 'dependency_lock_hash': 'e' * 64}
        for field, value in mutations.items():
            with self.subTest(field=field):
                with self.assertRaises(EvidenceError):
                    self._verify_record(dict(original, **{field: value}), freeze)

    def test_signed_execution_identity_and_exit_status_reject_type_confusion(self):
        original,freeze=self._record()
        for field,values in {'epoch':(True,1.,'1'),'seed':(42.,'42',None),'exit_code':(False,0.,'0')}.items():
            for value in values:
                with self.subTest(field=field,value=value):
                    record=dict(original,**{field:value})
                    receipt=dict(original['supervisor_receipt'],execution_binding=execution_binding(record))
                    receipt['exit_status' if field=='exit_code' else field]=value
                    record['supervisor_receipt']=sign_receipt(receipt)
                    with self.assertRaisesRegex(EvidenceError,'JSON integers'):self._verify_record(record,freeze)
        for field,value in (('epoch',True),('seed',42.),('exit_status',False)):
            with self.subTest(receipt_only=field):
                record=dict(original,supervisor_receipt=sign_receipt({**original['supervisor_receipt'],field:value}))
                with self.assertRaisesRegex(EvidenceError,'binding mismatch'):self._verify_record(record,freeze)

    def test_receipt_cannot_replay_into_another_project(self):
        record, freeze = self._record()
        with self.assertRaises(EvidenceError):
            verify_execution_record(record, project_id='different-project', epoch=1,
                                    experiment={'id': 'probe', 'seed': 42}, freeze=freeze,
                                    engine_hash='b' * 64)

    def test_portable_pinned_verification_needs_no_home_key(self):
        record, freeze = self._record()
        self.key.unlink()
        self.key.with_suffix('.pub').unlink()
        self._verify_record(record, freeze)

    def test_contract_preserves_order_literals_and_numpy_sibling_imports(self):
        (self.root / 'source').mkdir()
        (self.root / 'source/helper.py').write_text('VALUE = 7\n')
        (self.root / 'source/run.py').write_text('import helper, sys, cryptography\nprint(helper.VALUE, sys.argv[1:])\n')
        command = [sys.executable, 'source/run.py', '--output={run_dir}', '{seed}', '{experiment_id}', 'literal']
        contract, _ = command_to_contract(command, ['source'])
        validate_contract(contract, self.root, ['source'])
        argv, preexec, env = resolve_contract(contract, self.root / 'run', 42, 'probe')
        self.assertEqual(argv[-3:], ['42', 'probe', 'literal'])
        # A frozen sibling import must work; dependency startup is retained rather than disabled with -S.
        result = subprocess.run(argv, cwd=self.root, capture_output=True, text=True,
                                env={'PATH': os.environ.get('PATH', ''), **env}, preexec_fn=preexec)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('7', result.stdout)
        self.assertNotIn('-S', argv)
        try:
            import numpy
        except ImportError:
            return
        (self.root / 'source/run.py').write_text('import numpy, helper\nprint(numpy.arange(helper.VALUE).size)\n')
        result = subprocess.run(argv, cwd=self.root, capture_output=True, text=True,
                                env={'PATH': os.environ.get('PATH', ''), **env}, preexec_fn=preexec)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout.strip(), '7')

    def test_contract_mapping_order_and_invalid_argument_values(self):
        contract = {'runtime_id': 'python-cpu-v1', 'entrypoint': 'source/run.py',
                    'arguments': {'experiment_id': 'plan_id', 'seed': 'plan_seed', 'run_dir': 'supervisor_bound'}}
        self.assertEqual(contract_argv_template(contract)[-3:], ['{run_dir}', '{seed}', '{experiment_id}'])
        contract['arguments'] = {'run_dir': 'untrusted'}
        with self.assertRaises(EvidenceError):
            resolve_contract(contract, self.root, 1, 'probe')

    def test_external_payload_module_and_interpreter_paths_rejected(self):
        for command in ([sys.executable, '/tmp/outside.py', 'source/run.py'],
                        [sys.executable, '-m', 'module', 'source/run.py'],
                        ['/tmp/python3', 'source/run.py'],
                        ['env', 'python3', 'source/run.py'],
                        [sys.executable, 'source/../outside.py']):
            with self.subTest(command=command):
                if '..' in command[1]:
                    contract, _ = command_to_contract(command, ['source'])
                    with self.assertRaises(EvidenceError):
                        validate_contract(contract, self.root, ['source'])
                else:
                    with self.assertRaises(EvidenceError):
                        command_to_contract(command, ['source'])

    def test_disabled_network_and_unsupported_resources_fail_closed(self):
        (self.root / 'source').mkdir()
        (self.root / 'source/run.py').write_text('pass\n')
        contract = {'runtime_id': 'python-cpu-v1', 'entrypoint': 'source/run.py', 'network': 'disabled'}
        with self.assertRaises(EvidenceError):
            validate_contract(contract, self.root, ['source'])
        contract.update(network='unrestricted', memory_bytes=4096)
        with patch('engine.contract.sys.platform', 'darwin'):
            with self.assertRaises(EvidenceError):
                validate_contract(contract, self.root, ['source'])

    def test_requested_cpu_limit_is_enforced_by_child(self):
        (self.root / 'source').mkdir()
        (self.root / 'source/run.py').write_text('while True: pass\n')
        contract = {'runtime_id': 'python-cpu-v1', 'entrypoint': 'source/run.py',
                    'arguments': [], 'cpu_seconds': 1, 'network': 'unrestricted'}
        validate_contract(contract, self.root, ['source'])
        argv, preexec, env = resolve_contract(contract, self.root / 'run', 42, 'probe')
        result = subprocess.run(argv, cwd=self.root, capture_output=True, timeout=5,
                                env={'PATH': os.environ.get('PATH', ''), **env}, preexec_fn=preexec)
        self.assertLess(result.returncode, 0)

    def test_lifecycle_wall_timeout_retains_a_signed_failure(self):
        import gatekeeper as gate
        from test_v3 import fixture
        from engine.io import read_json, write_json
        fixture(self.root)
        (self.root / 'source/run.py').write_text('import time\ntime.sleep(30)\n')
        plan = read_json(self.root / 'project/research_plan.json')
        contract, _ = command_to_contract(plan['experiments'][0]['command'], ['source/run.py'])
        contract['wall_seconds'] = 1
        plan['experiments'][0]['execution_contract'] = contract
        write_json(self.root / 'project/research_plan.json', plan)
        with redirect_stdout(io.StringIO()):
            gate.freeze(self.root)
            self.assertNotEqual(gate.run_exp(self.root, 'known'), 0)
        _, epoch, freeze = gate.active(self.root)
        record = read_json(epoch / 'runs/known/attempt0001/execution.json')
        self.assertEqual(record['exit_code'], 124)
        self.assertEqual(record['record_error'], 'wall-clock timeout')
        verify_execution_record(record, project_id=plan['project_id'], epoch=freeze['epoch'],
                                experiment=plan['experiments'][0], freeze=freeze, engine_hash=gate.engine_hash())
        tampered = dict(record)
        tampered.pop('record_error')
        with self.assertRaises(EvidenceError):
            verify_execution_record(tampered, project_id=plan['project_id'], epoch=freeze['epoch'],
                                    experiment=plan['experiments'][0], freeze=freeze, engine_hash=gate.engine_hash())

    def _rewrite(self, source, target, updates):
        with zipfile.ZipFile(source) as archive:
            members = {name: archive.read(name) for name in archive.namelist()}
        manifest = json.loads(members[MANIFEST])
        manifest.update(updates)
        members[MANIFEST] = json.dumps(manifest).encode()
        with zipfile.ZipFile(target, 'w') as archive:
            for name, data in members.items():
                archive.writestr(name, data)

    def test_signed_manifest_detects_metadata_forgery_and_signature_removal(self):
        evidence = self.root / 'evidence.txt'
        evidence.write_text('evidence')
        archive = self.root / 'review.zip'
        create_bundle(archive, {'evidence.txt': evidence}, {'factory_version': '3.3.0', 'release_status': 'NOT_CERTIFIED'}, sign_manifest=True)
        pub = self.key.with_suffix('.pub')
        good = independent.verify_bundle(archive, pub, require_manifest_signature=True)
        self.assertEqual(good['status'], 'PASS', good)
        self.assertTrue(good['metadata_trusted'])
        self.assertTrue(verify_bundle(archive, pub)['manifest_signature_verified'])
        forged = self.root / 'forged.zip'
        for updates in ({'release_status': 'READY_FOR_HUMAN_SUBMISSION_REVIEW'}, {'supervisor_signature': ''}):
            self._rewrite(archive, forged, updates)
            with self.assertRaises(EvidenceError):
                verify_bundle(forged, pub)
            self.assertEqual(independent.verify_bundle(forged, pub, require_manifest_signature=True)['status'], 'FAIL')

    def test_nested_execution_record_verifies_after_archive_relocation(self):
        record, _ = self._record()
        receipt_file = self.root / 'execution.json'
        receipt_file.write_text(json.dumps(record))
        archive = self.root / 'review.zip'
        create_bundle(archive, {'project/.factory/epoch_0001/runs/probe/attempt0001/execution.json': receipt_file},
                      {'factory_version': '3.3.0'}, sign_manifest=True)
        relocated = self.root / 'different_location.zip'
        archive.rename(relocated)
        result = independent.verify_bundle(relocated, self.key.with_suffix('.pub'), require_manifest_signature=True)
        self.assertEqual(result['status'], 'PASS', result)
        self.assertEqual(result['signatures_verified'], 1)

    def test_unsigned_manifest_cannot_advertise_trusted_release_metadata(self):
        evidence = self.root / 'evidence.txt'
        evidence.write_text('evidence')
        archive = self.root / 'review.zip'
        create_bundle(archive, {'evidence.txt': evidence}, {'release_status': 'READY_FOR_HUMAN_SUBMISSION_REVIEW'})
        result = independent.verify_bundle(archive)
        self.assertEqual(result['status'], 'PASS')
        self.assertFalse(result['metadata_trusted'])
        self.assertEqual(result['release_status'], 'UNVERIFIED_METADATA')
        self.assertEqual(independent.verify_bundle(archive, self.key.with_suffix('.pub'), require_manifest_signature=True)['status'], 'FAIL')

    def test_real_lifecycle_bundle_verifies_and_reaudits_after_relocation(self):
        import gatekeeper as gate
        from test_v3 import fixture
        fixture(self.root)
        with redirect_stdout(io.StringIO()):
            gate.freeze(self.root)
            self.assertEqual(gate.run_exp(self.root, 'known'), 0)
            self.assertEqual(gate.handoff(self.root), 0)
        archive = next((self.root / 'TAKE_THIS').glob('review_bundle_*.zip'))
        result = independent.verify_bundle(archive, self.key.with_suffix('.pub'), require_manifest_signature=True)
        self.assertEqual(result['status'], 'PASS', result)
        self.assertEqual(result['signatures_verified'], 1)
        with tempfile.TemporaryDirectory() as moved:
            relocated = Path(moved)
            with zipfile.ZipFile(archive) as package:
                package.extractall(relocated)
            # The relocated checker revalidates its public-key pin without the original key files.
            self.key.unlink()
            self.key.with_suffix('.pub').unlink()
            env = {'PATH': os.environ.get('PATH', ''), 'PYTHONDONTWRITEBYTECODE': '1'}
            audit = subprocess.run([sys.executable, str(relocated / 'factory/gatekeeper.py'),
                                    'audit', str(relocated)], capture_output=True, text=True, env=env)
            evidence = json.loads(audit.stdout)
            self.assertEqual(audit.returncode, 0, evidence)
            self.assertEqual(evidence['errors'], [])

    def test_nonobject_manifests_fail_cleanly(self):
        for value in ('[]', 'null', 'false', '1', '"text"'):
            archive = self.root / 'bad_manifest.zip'
            with zipfile.ZipFile(archive, 'w') as output:
                output.writestr(MANIFEST, value)
            self.assertEqual(independent.verify_bundle(archive)['status'], 'FAIL')
            with self.assertRaises(EvidenceError):
                verify_bundle(archive)

    def test_duplicate_keys_nan_and_dot_segment_names_rejected_by_both_verifiers(self):
        for name, manifest in (('evidence.txt', b'{"schema_version":1,"schema_version":1,"files":{}}'),
                               ('evidence.txt', b'{"schema_version":1,"files":{},"value":NaN}'),
                               ('evidence/./item.txt', b'{"schema_version":1,"files":{}}')):
            with self.subTest(name=name, manifest=manifest):
                archive = self.root / 'bad.zip'
                with zipfile.ZipFile(archive, 'w') as output:
                    output.writestr(name, 'bad')
                    output.writestr(MANIFEST, manifest)
                with self.assertRaises(EvidenceError):
                    verify_bundle(archive)
                self.assertEqual(independent.verify_bundle(archive)['status'], 'FAIL')


if __name__ == '__main__':
    unittest.main()
