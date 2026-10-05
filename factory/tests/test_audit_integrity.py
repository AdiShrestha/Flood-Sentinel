"""Exercise release decisions with authentic receipts and adversarial evidence."""
import contextlib
import copy
import io
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

FACTORY=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(FACTORY))
import gatekeeper as g
from engine.audit import Audit,verify_review
from engine.io import EvidenceError,read_json,write_json,inventory,digest,sha,inside
from engine.supervisor import sign_receipt,execution_binding
from engine.plan import REVIEW_TOPICS
from tests.test_v3 import fixture,evaluate

class AuditIntegrityTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.root=Path(self.temp.name)/'project-root';self.root.mkdir()
        self.env=patch.dict(os.environ,{'FACTORY_SUPERVISOR_KEY':str(Path(self.temp.name)/'keys/supervisor.key')})
        self.env.start();self.output=contextlib.redirect_stdout(io.StringIO());self.output.__enter__()
        self.plan=fixture(self.root)
    def tearDown(self):
        self.output.__exit__(None,None,None);self.env.stop();self.temp.cleanup()
    def execute(self):
        g.freeze(self.root);self.assertEqual(g.run_exp(self.root,'known'),0)
        _,self.epoch,self.freeze=g.active(self.root);self.attempt=self.epoch/'runs/known/attempt0001'
    def record(self):return read_json(self.attempt/'execution.json')
    def trusted_resign(self,record):
        """Use the test signer's authority to exercise checks beyond signature failure."""
        files=inventory(self.root,[str(self.attempt.relative_to(self.root))],reject_dangerous_ext=False)
        files.pop(str((self.attempt/'execution.json').relative_to(self.root)))
        record['outputs']=files
        receipt={**record['supervisor_receipt'],'output_root':digest(files),
                 'inputs_after_root':digest(record['inputs_after']),
                 'execution_binding':execution_binding(record),'launch_spec':digest(record['argv_template'])}
        record['supervisor_receipt']=sign_receipt(receipt);write_json(self.attempt/'execution.json',record)
    def test_missing_receipt_cannot_pass(self):
        self.execute();record=self.record();record.pop('supervisor_receipt');write_json(self.attempt/'execution.json',record)
        self.assertTrue(evaluate(self.root)['errors'])
    def test_stale_freeze_binding_even_with_valid_signature(self):
        self.execute();record=self.record();record['freeze_sha256']='0'*64;self.trusted_resign(record)
        self.assertTrue(any('stale freeze binding' in error['detail'] for error in evaluate(self.root)['errors']))
    def test_recomputed_metrics_with_valid_signature(self):
        self.execute();result=read_json(self.attempt/'result.json');result['reported_metrics']['test']['auroc']=0
        write_json(self.attempt/'result.json',result);self.trusted_resign(self.record())
        self.assertTrue(any('independent recomputation' in error['detail'] for error in evaluate(self.root)['errors']))
    def test_duplicate_predictions_with_valid_signature(self):
        self.execute();predictions=self.attempt/'predictions.csv';predictions.write_text(predictions.read_text().replace('s9,','s8,'))
        self.trusted_resign(self.record());self.assertTrue(any('duplicate prediction' in error['detail'] for error in evaluate(self.root)['errors']))
    def test_extra_output_membership_blocks(self):
        self.execute();(self.attempt/'extra.dat').write_text('added after execution')
        self.assertTrue(any('membership changed' in error['detail'] for error in evaluate(self.root)['errors']))
    def test_attempt_gap_blocks(self):
        self.execute();self.attempt.rename(self.attempt.with_name('attempt0002'))
        self.assertTrue(any('attempt sequence' in error['detail'] for error in evaluate(self.root)['errors']))
    def test_duplicate_successes_block(self):
        self.execute();shutil.copytree(self.attempt,self.attempt.with_name('attempt0002'))
        self.assertTrue(any('same-epoch retries' in error['detail'] for error in evaluate(self.root)['errors']))
    def test_interrupted_supervisor_can_amend_with_disclosure(self):
        g.freeze(self.root)
        with patch.object(g,'build_receipt',side_effect=RuntimeError('supervisor interruption')):
            with self.assertRaises(RuntimeError):g.run_exp(self.root,'known')
        self.assertTrue(evaluate(self.root)['errors'])
        g.freeze(self.root,'Recover interrupted supervisor with prior possible holdout access disclosed')
        self.assertEqual(g.run_exp(self.root,'known'),0)
        report=evaluate(self.root)
        self.assertEqual(report['errors'],[])
        self.assertTrue(any(item['code']=='INTERRUPTED_ATTEMPT' for item in report['diagnostics']))
    def test_deleted_prior_attempts_cannot_erase_holdout_access(self):
        self.execute();old=self.epoch;g.freeze(self.root,'Descriptive follow-up with consumed holdout')
        self.assertEqual(g.run_exp(self.root,'known'),0);shutil.rmtree(old/'runs')
        self.assertTrue(evaluate(self.root)['errors'])
    def test_deleted_failed_attempt_cannot_be_rerun(self):
        (self.root/'source/run.py').write_text('raise RuntimeError("retained failure")')
        g.freeze(self.root);self.assertNotEqual(g.run_exp(self.root,'known'),0)
        _,epoch,_=g.active(self.root);shutil.rmtree(epoch/'runs/known/attempt0001')
        with self.assertRaises(EvidenceError):g.run_exp(self.root,'known')
    def test_group_renaming_does_not_restore_holdout(self):
        self.execute();cohort=self.root/'data/cohort.csv'
        import re
        cohort.write_text(re.sub(r',g(\d+),',r',renamedg\1,',cohort.read_text()))
        g.freeze(self.root,'Changed labels of group identifiers; cohort observations unchanged')
        self.assertEqual(g.run_exp(self.root,'known'),0);self.assertTrue(evaluate(self.root)['holdout_reused'])
    def test_deleted_ledger_blocks_audit_and_execution(self):
        self.execute();(self.epoch/'execution_ledger.json').unlink()
        self.assertTrue(evaluate(self.root)['errors'])
        with self.assertRaises(EvidenceError):g.run_exp(self.root,'known')
    def test_failure_cannot_be_retried(self):
        (self.root/'source/run.py').write_text('raise RuntimeError("infrastructure fixture")')
        g.freeze(self.root);self.assertNotEqual(g.run_exp(self.root,'known'),0)
        with self.assertRaises(EvidenceError):g.run_exp(self.root,'known')
    def test_consumed_holdout_disclosed_after_amendment(self):
        self.execute();g.freeze(self.root,'A descriptive follow-up with prior test access disclosed')
        self.assertEqual(g.run_exp(self.root,'known'),0);report=evaluate(self.root)
        self.assertTrue(report['holdout_reused']);self.assertEqual(len(report['amendments']),1)
    def test_prior_epoch_deletion_blocks(self):
        self.execute();g.freeze(self.root,'Documented follow-up');shutil.rmtree(self.epoch)
        self.assertTrue(evaluate(self.root)['errors'])
    def test_output_binary_and_bytecode_members_are_hashed(self):
        self.execute();(self.attempt/'weights.so').write_bytes(b'checkpoint artifact')
        inventory_before=inventory(self.root,[str(self.attempt.relative_to(self.root))],reject_dangerous_ext=False)
        self.assertIn(str((self.attempt/'weights.so').relative_to(self.root)),inventory_before)
    def test_private_signing_key_cannot_enter_frozen_bundle(self):
        from engine.supervisor import init_supervisor_keys
        with patch.dict(os.environ,{'FACTORY_SUPERVISOR_KEY':str(self.root/'source/signing.key')}):
            init_supervisor_keys()
            with self.assertRaises(EvidenceError):g.freeze(self.root)
    def test_frozen_bytecode_in_cache_is_rejected(self):
        cache=self.root/'source/__pycache__';cache.mkdir();(cache/'helper.cpython-312.pyc').write_bytes(b'bad code')
        with self.assertRaises(EvidenceError):g.freeze(self.root)
    def test_producer_needs_neither_labels_nor_metrics(self):
        script=(self.root/'source/run.py').read_text()
        script=script.replace("'label':x['label'],",'').replace("fieldnames=['sample_id','label','score']","fieldnames=['sample_id','score']")
        script=script.replace("'reported_metrics':{'validation':m,'test':m},",'')
        (self.root/'source/run.py').write_text(script);self.execute()
        self.assertEqual(evaluate(self.root)['errors'],[])
    def test_json_seed_bool_cannot_equal_integer_seed(self):
        self.plan['experiments'][0]['seed']=1;write_json(self.root/g.ROOT_PLAN,self.plan);self.execute()
        result=read_json(self.attempt/'result.json');result['seed']=True;write_json(self.attempt/'result.json',result)
        self.trusted_resign(self.record());self.assertTrue(evaluate(self.root)['errors'])
    def test_bundle_bytes_do_not_depend_on_file_mtime(self):
        from engine.bundle import create_bundle
        content=Path(self.temp.name)/'content';content.write_text('identical content')
        first=Path(self.temp.name)/'one.zip';second=Path(self.temp.name)/'two.zip'
        create_bundle(first,{'content':content},{'factory_version':'3.3.0'})
        os.utime(content,(1000000000,1000000000))
        create_bundle(second,{'content':content},{'factory_version':'3.3.0'})
        self.assertEqual(first.read_bytes(),second.read_bytes())
    def test_zip_declared_size_bomb_rejected_before_decompression(self):
        import zipfile,struct
        from engine.bundle import create_bundle,verify_bundle
        from verify_bundle_standalone import verify_bundle as standalone
        content=Path(self.temp.name)/'content';content.write_text('tiny')
        archive=Path(self.temp.name)/'bomb.zip'
        create_bundle(archive,{name:content for name in ('a','b','c')},{'factory_version':'3.3.0'})
        raw=bytearray(archive.read_bytes());cursor=0
        for unused in range(3):
            cursor=raw.index(b'PK\x01\x02',cursor)
            struct.pack_into('<I',raw,cursor+24,0xfffffffe);cursor+=4
        archive.write_bytes(raw)
        with self.assertRaises(EvidenceError):verify_bundle(archive)
        result=standalone(archive)
        self.assertEqual(result['status'],'FAIL')
    def test_bundle_project_reaudits_after_relocation(self):
        self.execute();self.assertEqual(g.handoff(self.root),0)
        destination=Path(self.temp.name)/'relocated';destination.mkdir()
        import zipfile
        archive=next((self.root/'TAKE_THIS').glob('*.zip'))
        with zipfile.ZipFile(archive) as bundle:bundle.extractall(destination)
        report=evaluate(destination);self.assertEqual(report['errors'],[])
    def test_run_all_stdout_is_one_json_document(self):
        g.freeze(self.root)
        result=subprocess.run([sys.executable,str(FACTORY/'gatekeeper.py'),'run',str(self.root),'all'],capture_output=True,text=True)
        self.assertEqual(result.returncode,0,result.stdout);payload=json.loads(result.stdout)
        self.assertEqual(payload['status'],'RECORDED');self.assertNotIn('metrics',payload)
    def test_freeze_option_before_path_locks_correct_workspace(self):
        g.freeze(self.root)
        elsewhere=Path(self.temp.name)/'elsewhere';elsewhere.mkdir()
        result=subprocess.run([sys.executable,str(FACTORY/'gatekeeper.py'),'freeze','--amendment','Documented amendment',str(self.root)],cwd=elsewhere,capture_output=True,text=True)
        self.assertEqual(result.returncode,0,result.stdout);json.loads(result.stdout)
        self.assertFalse((elsewhere/'project/.factory').exists())
    def test_malformed_execution_has_no_traceback(self):
        self.execute();write_json(self.attempt/'execution.json',[])
        result=subprocess.run([sys.executable,str(FACTORY/'gatekeeper.py'),'audit',str(self.root)],capture_output=True,text=True)
        self.assertNotEqual(result.returncode,0);self.assertNotIn('Traceback',result.stderr);self.assertTrue(json.loads(result.stdout)['errors'])
    def review(self,audit):
        evidence={'path':'project/methodology.md','sha256':sha(self.root/'project/methodology.md')}
        prose='project/methodology.md describes the fixed fixture algorithm and its intentionally synthetic observations; these checks establish evidence consistency within the declared scope'
        return {'reviewer_role':'Architect','reviewer_model':'test-reviewer','session_id':'test-session','review_mode':'same_session_self_review','evidence_digest':audit['evidence_digest'],
                'checks':[{'topic':topic,'verdict':'acceptable','reasoning':topic+' '+prose,'evidence':[evidence]} for topic in sorted(REVIEW_TOPICS)],
                'diagnostic_resolutions':[{'id':d['id'],'reasoning':d['code']+' '+prose,'evidence':[evidence]} for d in audit['diagnostics']],
                'objections':[{'objection':'Fixture scope restricts population conclusions '+str(i),'resolution':'disclosed_limitation','reasoning':prose+str(i)} for i in range(3)],
                'limitations':['Synthetic fixtures cannot establish performance in an observational population.'],
                'venue_sources':['https://example.org/venue/guidelines reviewed for the test fixture only'],'unresolved_blockers':[]}
    def test_specific_review_passes_but_never_attests_independence(self):
        self.execute();audit=evaluate(self.root);review=self.review(audit);write_json(self.root/'project/review.json',review)
        self.assertEqual(verify_review(self.root,self.plan,audit),review)
        self.assertEqual(g._assurance_with_review('STRUCTURALLY_VALIDATED',True),'STRUCTURALLY_VALIDATED')
    def test_padding_review_blocks(self):
        self.execute();audit=evaluate(self.root);review=self.review(audit)
        for check in review['checks']:check['reasoning']='n/a '*50
        write_json(self.root/'project/review.json',review)
        with self.assertRaises(EvidenceError):verify_review(self.root,self.plan,audit)
    def test_unrelated_review_evidence_blocks(self):
        self.execute();audit=evaluate(self.root);review=self.review(audit)
        unrelated=self.root/'unrelated.txt';unrelated.write_text('unrelated evidence')
        review['checks'][0]['evidence']=[{'path':'unrelated.txt','sha256':sha(unrelated)}]
        review['checks'][0]['reasoning']='unrelated.txt '+review['checks'][0]['reasoning']
        write_json(self.root/'project/review.json',review)
        with self.assertRaises(EvidenceError):verify_review(self.root,self.plan,audit)
    def test_training_fixed_trace_and_early_stop(self):
        self.execute();A=Audit(self.root,self.plan,self.epoch,self.freeze,g.engine_hash());e=copy.deepcopy(self.plan['experiments'][0])
        (self.attempt/'checkpoint.bin').write_bytes(b'trained');(self.attempt/'initial.bin').write_bytes(b'initial')
        result={'history':'history.csv','checkpoint':'checkpoint.bin','initial_checkpoint':'initial.bin','epochs_trained':4,'checkpoint_epoch':3}
        (self.attempt/'history.csv').write_text('epoch,train_loss,validation_loss\n1,2,1\n2,1,.5\n3,.5,.49\n4,.4,.49\n')
        e['training']={'mode':'fixed','min_epochs':2,'max_epochs':4,'tail_window':2,'relative_tolerance':.05}
        with self.assertRaises(EvidenceError):A.training(e,result,self.attempt)
        (self.attempt/'history.csv').write_text('epoch,train_loss,validation_loss\n1,2,.5\n2,1,.5\n3,.5,.49\n4,.4,.49\n')
        A.training(e,result,self.attempt)
        e['training']={'mode':'early_stopping','min_epochs':2,'max_epochs':6,'patience':2,'min_delta':.02}
        result['checkpoint_epoch']=1
        result['epochs_trained']=3
        (self.attempt/'history.csv').write_text('epoch,train_loss,validation_loss\n1,2,.5\n2,1,.5\n3,.5,.49\n')
        A.training(e,result,self.attempt)
        result['checkpoint_epoch']=3
        with self.assertRaises(EvidenceError):A.training(e,result,self.attempt)

if __name__=='__main__':unittest.main()
