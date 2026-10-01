"""Local hardening regressions; all studies/receipts below are disclosed fixtures."""
import base64
import contextlib
import hashlib
import hmac
import io
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import gatekeeper as g
from engine import supervisor as sup
from engine.io import canonical, inventory, read_json, write_json, EvidenceError
from engine.schema import validate_training_manifest, validate_split_manifest
from engine.contract import _build_preexec, validate_contract
from test_v3 import fixture, evaluate


class ReceiptBoundaryTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.env=patch.dict(os.environ,{'FACTORY_SUPERVISOR_KEY':str(Path(self.tmp.name)/'keys/test.key')})
        self.env.start()
    def tearDown(self):
        self.env.stop(); self.tmp.cleanup()

    def test_public_ed25519_material_cannot_forge_an_hmac_receipt(self):
        if not sup._try_ed25519(): self.skipTest('cryptography unavailable; HMAC exercised separately')
        sup.init_supervisor_keys()
        _,public,_=sup._load_keys(); payload={'fixture':'not a real run'}
        fake={**payload,'signature_scheme':'hmac-sha256','public_key_id':hashlib.sha256(public).hexdigest()[:16],
              'supervisor_signature':base64.b64encode(hmac.new(public,canonical(payload),hashlib.sha256).digest()).decode()}
        with self.assertRaises(EvidenceError): sup.verify_receipt_signature(fake)

    def test_hmac_public_metadata_cannot_sign_and_old_exposed_format_is_rejected(self):
        with patch.object(sup,'_try_ed25519',return_value=False):
            priv,pub,scheme=sup.init_supervisor_keys()
            self.assertNotIn(base64.b64encode(priv.read_bytes()).decode(),pub.read_text())
            signed=sup.sign_receipt({'fixture':'hmac'}); self.assertTrue(sup.verify_receipt_signature(signed))
            _,public,_=sup._load_keys()
            fake={**signed,'supervisor_signature':base64.b64encode(hmac.new(public,canonical({'fixture':'hmac'}),hashlib.sha256).digest()).decode()}
            with self.assertRaises(EvidenceError): sup.verify_receipt_signature(fake)
            pub.write_text('# hmac-sha256\n'+base64.b64encode(priv.read_bytes()).decode()+'\n')
            with self.assertRaisesRegex(EvidenceError,'rotate'): sup.sign_receipt({'fixture':'old'})

    def run_fixture(self):
        r=Path(self.tmp.name)/'study'; r.mkdir(); fixture(r)
        with contextlib.redirect_stdout(io.StringIO()): g.freeze(r); g.run_exp(r,'known')
        _,ep,_=g.active(r)
        return r,ep/'runs/known/attempt0001/execution.json'

    def test_audit_rejects_bad_signature_even_when_outer_hashes_are_current(self):
        r,path=self.run_fixture(); rec=read_json(path)
        rec['supervisor_receipt']['supervisor_signature']='AA=='
        write_json(path,rec)
        self.assertTrue(any('signature' in x['detail'] for x in evaluate(r)['errors']))

    def test_audit_binds_valid_signature_to_the_actual_run(self):
        r,path=self.run_fixture(); rec=read_json(path)
        altered={**rec['supervisor_receipt'],'seed':rec['seed']+1}
        rec['supervisor_receipt']=sup.sign_receipt(altered); write_json(path,rec)
        self.assertTrue(any('binding mismatch: seed' in x['detail'] for x in evaluate(r)['errors']))

    def test_unmeasured_resources_are_unknown_and_wall_time_is_named_correctly(self):
        r,path=self.run_fixture(); rec=read_json(path)
        resource=rec['supervisor_receipt']['resource_observations']
        self.assertIsNone(resource['cpu_time_seconds']); self.assertIsNone(resource['memory_peak_bytes'])
        self.assertEqual(resource['wall_time_seconds'],rec['duration_sec'])
        self.assertEqual(g._compute_assurance_level(evaluate(r)),'STRUCTURALLY_VALIDATED')


class NumericalAndScopeTests(unittest.TestCase):
    def test_output_inventory_includes_binary_and_bytecode_outputs(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td); (root/'outputs/__pycache__').mkdir(parents=True)
            (root/'outputs/a.so').write_bytes(b'fixture binary'); (root/'outputs/__pycache__/a.pyc').write_bytes(b'fixture cache')
            files=inventory(root,['outputs'],reject_dangerous_ext=False)
            self.assertEqual(set(files),{'outputs/a.so','outputs/__pycache__/a.pyc'})
            with self.assertRaises(EvidenceError): inventory(root,['outputs'])

    def test_python_source_inside_cache_directory_is_still_frozen(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td); (root/'source/__pycache__').mkdir(parents=True)
            (root/'source/__pycache__/runner.py').write_text('# constructed fixture\n')
            self.assertIn('source/__pycache__/runner.py',inventory(root,['source']))

    def test_requested_resource_limits_do_not_silently_fail(self):
        for policy in ({'memory_bytes':100},{'process_limit':1}):
            with patch('resource.setrlimit',side_effect=OSError('fixture unsupported limit')):
                with self.assertRaises(EvidenceError): _build_preexec(policy)()

    def test_contract_entrypoint_cannot_escape_through_an_absolute_path(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td); entry=root/'fixture.py'; entry.write_text('# fixture\n')
            with self.assertRaises(EvidenceError):
                validate_contract({'runtime_id':'python-cpu-v1','entrypoint':str(entry)},root,[str(entry)])

    def test_fractional_counts_and_epochs_are_rejected(self):
        with self.assertRaises(EvidenceError): validate_split_manifest({'test_label_distribution':{'0':20.5,'1':30}})
        with self.assertRaises(EvidenceError): validate_training_manifest({'epochs_trained':3.5})

    def test_low_event_f1_is_not_a_universal_below_chance_result(self):
        for metric in ('f1','precision','recall','accuracy'):
            self.assertEqual(g._result_findings_single({'metric':metric,'value':.1}),[])
        self.assertEqual(g._result_findings_single({'metric':'auroc','value':.5}),[])
        self.assertIn('below_chance',[x[0] for x in g._result_findings_single({'metric':'auroc','value':.1})])

    def test_p_values_and_intervals_reject_nonfinite_out_of_range_and_coercion(self):
        for p in (float('nan'),float('inf'),-1.,2.,True,'0.5'):
            with contextlib.redirect_stdout(io.StringIO()):
                self.assertNotEqual(g.verify_result_plausibility({'p_value':p}),0)
        with contextlib.redirect_stdout(io.StringIO()):
            self.assertNotEqual(g.verify_result_plausibility({'ci':[2.,1.]}),0)

    def test_unsupported_verdicts_are_not_all_supported(self):
        entries=[{'verdict':'NOT_SUPPORTED'} for _ in range(3)]
        self.assertEqual(g._result_findings({'entries':entries}),[])

    def test_statistical_values_are_not_boolean_or_nonfinite(self):
        base={'primary_metric':'fixture score','sampling_unit':'fixture cluster','test':'fixture test','alpha':.05,
              'effect_size':.1,'confidence_interval':[0.,.2],'multiplicity_correction':'none; one test'}
        with tempfile.TemporaryDirectory() as td:
            path=Path(td)/'protocol.json'
            for field,value in (('alpha',True),('effect_size','0.1'),('confidence_interval',[False,.2]),('p_values',[2.])):
                write_json(path,{**base,field:value})
                with contextlib.redirect_stdout(io.StringIO()): self.assertNotEqual(g.verify_statistical_protocol(path),0)

    def test_observed_flat_sensitivity_can_be_reported_after_investigation(self):
        obj={'sweeps':[{'parameter':'fixture parameter','values':[.5,.5,.5]}],
             'investigation_note':'Fixture illustrates unchanged output; no performance result is claimed.'}
        with tempfile.TemporaryDirectory() as td:
            path=Path(td)/'sensitivity.json'; write_json(path,obj)
            with contextlib.redirect_stdout(io.StringIO()): self.assertEqual(g.verify_sensitivity_analysis(path),0)
            obj['sweeps'][0]['expected_flat']='false'; write_json(path,obj)
            with contextlib.redirect_stdout(io.StringIO()): self.assertNotEqual(g.verify_sensitivity_analysis(path),0)
