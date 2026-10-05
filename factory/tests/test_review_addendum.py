"""New review recommendations verified against the hardened implementation."""
import contextlib
import copy
import io
import os
from pathlib import Path
import sys
import tempfile
import unittest
import uuid
from unittest.mock import patch

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import gatekeeper as g
from engine.io import EvidenceError,read_json,write_json,sha
from engine.supervisor import sign_receipt,execution_binding,validate_run_nonce
from tests.test_v3 import fixture


class ExecutionNonceTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(prefix='review-nonce-')
        self.root=Path(self.temp.name);self.plan=fixture(self.root)
        self.plan['factory_version']=g.VERSION
        second=copy.deepcopy(self.plan['experiments'][0]);second.update(id='second',seed=43,model='second-model')
        self.plan['experiments'].append(second);write_json(self.root/g.ROOT_PLAN,self.plan)
        self.env=patch.dict(os.environ,{'FACTORY_SUPERVISOR_KEY':str(self.root/'keys/signing.key')});self.env.start()
        self.output=contextlib.redirect_stdout(io.StringIO());self.output.__enter__()
        g.freeze(self.root)

    def tearDown(self):
        self.output.__exit__(None,None,None);self.env.stop();self.temp.cleanup()

    def execute(self):
        self.assertEqual(g.run_exp(self.root,'known'),0);self.assertEqual(g.run_exp(self.root,'second'),0)
        _,self.epoch,self.freeze=g.active(self.root)

    def rewrite_nonce(self,epoch,eid,nonce):
        path=epoch/'runs'/eid/'attempt0001/execution.json';record=read_json(path)
        record['run_nonce']=nonce
        receipt={**record['supervisor_receipt'],'run_nonce':nonce,'execution_binding':execution_binding(record)}
        record['supervisor_receipt']=sign_receipt(receipt);write_json(path,record)
        ledger=read_json(epoch/'execution_ledger.json')
        ledger['attempts'][eid].update(run_nonce=nonce,execution_sha256=sha(path))
        write_json(epoch/'execution_ledger.json',sign_receipt(ledger))

    def test_distinct_executions_pass_with_valid_signed_reservations(self):
        self.execute();out=g.audit_snapshot(self.root,g.plan_at(self.root))
        self.assertEqual(out['errors'],[])
        ledger=read_json(self.epoch/'execution_ledger.json')
        self.assertEqual(len({entry['run_nonce'] for entry in ledger['attempts'].values()}),2)

    def test_repeated_generated_nonce_blocks_before_launch(self):
        nonce=uuid.uuid4()
        with patch.object(g.uuid,'uuid4',return_value=nonce):
            self.assertEqual(g.run_exp(self.root,'known'),0)
            with self.assertRaisesRegex(EvidenceError,'nonce already reserved'):g.run_exp(self.root,'second')
        _,epoch,_=g.active(self.root)
        self.assertFalse((epoch/'runs/second/attempt0001').exists())
        self.assertEqual(set(read_json(epoch/'execution_ledger.json')['attempts']),{'known'})

    def test_signed_duplicate_nonce_is_rejected_by_audit(self):
        self.execute();nonce=read_json(self.epoch/'runs/known/attempt0001/execution.json')['run_nonce']
        self.rewrite_nonce(self.epoch,'second',nonce)
        out=g.audit_snapshot(self.root,g.plan_at(self.root))
        self.assertTrue(any('nonce reused across reservations' in item['detail'] for item in out['errors']))

    def test_signed_ledger_nonce_must_match_record(self):
        self.execute();path=self.epoch/'execution_ledger.json';ledger=read_json(path)
        ledger['attempts']['known']['run_nonce']=str(uuid.uuid4());write_json(path,sign_receipt(ledger))
        out=g.audit_snapshot(self.root,g.plan_at(self.root))
        self.assertTrue(any('nonce differs from signed reservation' in item['detail'] for item in out['errors']))

    def test_generated_nonce_cannot_repeat_from_prior_epoch(self):
        self.execute();nonce=read_json(self.epoch/'runs/known/attempt0001/execution.json')['run_nonce']
        self.plan['experiments']=self.plan['experiments'][1:];self.plan['claims'][0]['experiment_ids']=['second']
        write_json(self.root/g.ROOT_PLAN,self.plan);g.freeze(self.root,'Disclosed descriptive fixture revision after prior execution.')
        with patch.object(g.uuid,'uuid4',return_value=uuid.UUID(nonce)):
            with self.assertRaisesRegex(EvidenceError,'nonce already reserved'):g.run_exp(self.root,'second')

    def test_signed_nonce_reuse_across_epochs_is_rejected(self):
        self.execute();nonce=read_json(self.epoch/'runs/known/attempt0001/execution.json')['run_nonce']
        self.plan['experiments']=self.plan['experiments'][1:];self.plan['claims'][0]['experiment_ids']=['second']
        write_json(self.root/g.ROOT_PLAN,self.plan);g.freeze(self.root,'Disclosed descriptive fixture revision after prior execution.')
        self.assertEqual(g.run_exp(self.root,'second'),0)
        _,epoch,_=g.active(self.root)
        self.assertEqual(g.audit_snapshot(self.root,g.plan_at(self.root))['errors'],[])
        self.rewrite_nonce(epoch,'second',nonce)
        self.assertTrue(any('nonce reused across epochs' in item['detail']
                            for item in g.audit_snapshot(self.root,g.plan_at(self.root))['errors']))

    def test_signed_reservation_path_cannot_change_identity(self):
        self.execute();path=self.epoch/'execution_ledger.json';ledger=read_json(path)
        ledger['attempts']['known']['attempt_path']=ledger['attempts']['second']['attempt_path']
        write_json(path,sign_receipt(ledger))
        self.assertTrue(any('reservation path differs' in item['detail']
                            for item in g.audit_snapshot(self.root,g.plan_at(self.root))['errors']))

    def test_receipt_error_blocks_even_with_valid_signature_and_binding(self):
        self.execute();path=self.epoch/'runs/known/attempt0001/execution.json';record=read_json(path)
        record['receipt_error']='simulated receipt generation failure'
        record['supervisor_receipt']=sign_receipt({**record['supervisor_receipt'],'execution_binding':execution_binding(record)})
        write_json(path,record);ledger=read_json(self.epoch/'execution_ledger.json')
        ledger['attempts']['known']['execution_sha256']=sha(path)
        write_json(self.epoch/'execution_ledger.json',sign_receipt(ledger))
        self.assertTrue(any('contains receipt_error' in item['detail']
                            for item in g.audit_snapshot(self.root,g.plan_at(self.root))['errors']))

    def test_nonce_format_is_strict(self):
        value=str(uuid.uuid4());self.assertEqual(validate_run_nonce(value),value)
        for invalid in (None,True,{},'missing',value.upper(),value.replace('-',''),'00000000-0000-1000-8000-000000000000'):
            with self.subTest(invalid=invalid):
                with self.assertRaises(EvidenceError):validate_run_nonce(invalid)


class IndependentFormulaTests(unittest.TestCase):
    def test_all_binary_metrics_match_independent_confusion_and_loss_oracles(self):
        import math,random
        from engine.metrics import binary_metrics
        rng=random.Random(20261003)
        for size in range(4,25):
            labels=[0,1]+[rng.randrange(2) for _ in range(size-2)]
            scores=[rng.choice((0.,.1,.25,.5,.75,.9,1.)) for _ in labels]
            for threshold in (0.,.25,.5,.75,1.):
                expected=[(int(label),int(score>=threshold)) for label,score in zip(labels,scores)]
                counts={(a,b):expected.count((a,b)) for a in (0,1) for b in (0,1)}
                tp,fp,fn=counts[1,1],counts[0,1],counts[1,0]
                result=binary_metrics(labels,scores,threshold)
                self.assertAlmostEqual(result['accuracy'],(counts[0,0]+tp)/size)
                self.assertAlmostEqual(result['f1'],2*tp/(2*tp+fp+fn) if 2*tp+fp+fn else 0)
                self.assertAlmostEqual(result['brier'],sum((label-score)**2 for label,score in zip(labels,scores))/size)
                loss=sum(-math.log(min(1-1e-15,max(1e-15,score if label else 1-score))) for label,score in zip(labels,scores))/size
                self.assertAlmostEqual(result['log_loss'],loss)

    def test_probability_domains_and_holm_upper_boundary(self):
        from engine.metrics import binary_metrics,holm,quantile
        for score in (-.001,1.001):
            with self.assertRaises(EvidenceError):binary_metrics([0,1],[.3,score])
        for threshold in (-.001,1.001):
            with self.assertRaises(EvidenceError):binary_metrics([0,1],[.3,.7],threshold)
        for pvalue in (-.001,1.001):
            with self.assertRaises(EvidenceError):holm([.01,pvalue])
        self.assertEqual(quantile([1,3,9,11],.25),2.5)
        self.assertEqual(quantile([1,3,9,11],.75),9.5)

class BenchmarkAccountingTests(unittest.TestCase):
    def test_exact_intervals_match_closed_form_boundary_cases(self):
        from run_seeded_fault_benchmark import binomial_interval
        self.assertEqual(binomial_interval(0,3)[0],0.)
        self.assertAlmostEqual(binomial_interval(0,3)[1],1-.025**(1/3))
        self.assertAlmostEqual(binomial_interval(3,3)[0],.025**(1/3))
        self.assertEqual(binomial_interval(3,3)[1],1.)
        self.assertAlmostEqual(binomial_interval(1,1)[0],.025)
        self.assertAlmostEqual(binomial_interval(0,1)[1],.975)
        for invalid in ((True,3),(1,False),(-1,3),(4,3),(0,0)):
            with self.assertRaises(ValueError):binomial_interval(*invalid)

    def test_setup_errors_have_no_detection_or_false_positive_rates(self):
        import run_seeded_fault_benchmark as benchmark
        with patch.object(benchmark,'_case',side_effect=RuntimeError('failed setup')):
            report=benchmark.run_benchmark(variants=1)
        self.assertEqual(report['status'],'FAIL')
        self.assertEqual(len(report['errors']),len(benchmark.FAMILIES))
        for result in report['families'].values():
            self.assertEqual(result['assessed_pairs'],0)
            for name in ('detection_fraction','detection_binomial_95_ci','false_positive_fraction','false_positive_binomial_95_ci'):
                self.assertIsNone(result[name])

    def test_large_simulation_counts_do_not_overflow(self):
        from run_seeded_fault_benchmark import binomial_interval
        lower,upper=binomial_interval(2500,5000)
        self.assertAlmostEqual(lower,1-upper,places=10)
        self.assertGreater(lower,.48);self.assertLess(upper,.52)
        self.assertAlmostEqual(binomial_interval(0,5000)[1],1-.025**(1/5000),places=10)
        self.assertAlmostEqual(binomial_interval(5000,5000)[0],.025**(1/5000),places=10)

    def test_expression_mutations_preserve_unicode_and_require_unique_exact_match(self):
        from run_mutation_checks import apply_mutation
        source='def check(a):\n    label="π"; return a == 0\n'
        spec={'function':'check','node_kind':'Compare','marker':'a == 0','replacement':'a == 1'}
        changed,location=apply_mutation(source,spec)
        self.assertEqual(changed,source.replace('a == 0','a == 1'))
        self.assertEqual(location['original_expression'],'a == 0')
        with self.assertRaisesRegex(ValueError,'found 2'):
            apply_mutation('def check(a):\n    return a == 0 or a == 0\n',spec)
        with self.assertRaisesRegex(ValueError,'found 0'):
            apply_mutation(source,{**spec,'marker':'a == 0 or a == 1'})


class CertificationPreflightTests(unittest.TestCase):
    """Synthetic, temporary research-labelled inputs test controller wiring only."""
    def setUp(self):
        import run_seeded_fault_benchmark as benchmark
        self.temp=tempfile.TemporaryDirectory(prefix='review-preflight-');self.root=Path(self.temp.name)/'workspace'
        self.env=patch.dict(os.environ,{'FACTORY_SUPERVISOR_KEY':str(Path(self.temp.name)/'keys/signing.key')});self.env.start()
        self.output=contextlib.redirect_stdout(io.StringIO());self.output.__enter__()
        plan=benchmark._project(self.root,'forged_receipt',20261003)
        # Deliberately author-declared synthetic acquisition; the gate makes no
        # authenticity claim. This is not research or validation of data origin.
        benchmark._before_freeze(self.root,'fabricated_origin',plan)
        g.freeze(self.root);self.assertEqual(g.run_exp(self.root,'fixed'),0);g.audit(self.root)
        audit=read_json(self.root/'project/audit_report.json');self.assertEqual(audit['errors'],[])
        benchmark._review(self.root,audit)

    def tearDown(self):
        self.output.__exit__(None,None,None);self.env.stop();self.temp.cleanup()

    def passing_stub(self,root):
        report={'status':'PASS','engine_sha256':g.engine_hash(),'validation_sha256':g.validation_hash(),
                'scope':'Unit-test stub only; no actual preflight result.'}
        write_json(root/'project/release_checks.json',report)
        return 0,report

    def test_ordinary_certify_runs_fresh_preflight_despite_persisted_pass(self):
        self.passing_stub(self.root)
        with patch.object(g,'release_preflight',side_effect=self.passing_stub) as preflight:
            self.assertEqual(g.certify(self.root),0)
        preflight.assert_called_once_with(self.root)
        certificate=read_json(self.root/'project/RELEASE_CERTIFICATION.json')
        self.assertEqual(certificate['release_checks_sha256'],sha(self.root/'project/release_checks.json'))
        self.assertEqual(certificate['validation_sha256'],g.validation_hash())
        audit=g.audit_snapshot(self.root,g.plan_at(self.root))
        self.assertTrue(g.certificate_current(self.root,g.plan_at(self.root),audit))
        report=read_json(self.root/'project/release_checks.json');report['status']='FAIL'
        write_json(self.root/'project/release_checks.json',report)
        self.assertFalse(g.certificate_current(self.root,g.plan_at(self.root),audit))

    def test_failed_preflight_removes_prior_certificate_and_blocks_new_one(self):
        write_json(self.root/'project/RELEASE_CERTIFICATION.json',{'status':'old certificate'})
        with patch.object(g,'release_preflight',return_value=(40,{'status':'FAIL'})) as preflight:
            self.assertEqual(g.certify(self.root),40)
        preflight.assert_called_once_with(self.root)
        self.assertFalse((self.root/'project/RELEASE_CERTIFICATION.json').exists())

    def test_project_edit_during_preflight_is_reaudited(self):
        def changed(root):
            result=self.passing_stub(root)
            (root/'project/methodology.md').write_text('Changed after the first audit.')
            return result
        with patch.object(g,'release_preflight',side_effect=changed):
            self.assertEqual(g.certify(self.root),g.EXIT_SCIENCE)
        self.assertFalse((self.root/'project/RELEASE_CERTIFICATION.json').exists())

    def test_changed_validation_corpus_invalidates_certificate(self):
        with patch.object(g,'release_preflight',side_effect=self.passing_stub):
            self.assertEqual(g.certify(self.root),0)
        audit=g.audit_snapshot(self.root,g.plan_at(self.root))
        with patch.object(g,'validation_hash',return_value='0'*64):
            self.assertFalse(g.certificate_current(self.root,g.plan_at(self.root),audit))

    def test_failed_preflight_status_cannot_be_reported_with_success_code(self):
        def failed(root):
            _,report=self.passing_stub(root);report['status']='FAIL'
            write_json(root/'project/release_checks.json',report)
            return 0,report
        with patch.object(g,'release_preflight',side_effect=failed):
            self.assertEqual(g.certify(self.root),40)
        self.assertFalse((self.root/'project/RELEASE_CERTIFICATION.json').exists())

    def test_each_failed_behavioral_stage_blocks_and_saves_failed_report(self):
        import engine.attacks,run_mutation_checks,run_seeded_fault_benchmark
        stages=['registered_attacks','mutation_benchmark','seeded_fault_benchmark']
        for failed in stages:
            with self.subTest(failed=failed), \
                    patch.object(engine.attacks,'run_registered_attacks',return_value={'status':'FAIL' if failed==stages[0] else 'PASS'}) as attacks, \
                    patch.object(run_mutation_checks,'run_benchmark',return_value={'status':'FAIL' if failed==stages[1] else 'PASS'}) as mutations, \
                    patch.object(run_seeded_fault_benchmark,'run_benchmark',return_value={'status':'FAIL' if failed==stages[2] else 'PASS'}) as seeded:
                code,report=g.release_preflight(self.root)
                self.assertEqual(code,40);self.assertEqual(report['status'],'FAIL')
                self.assertEqual(read_json(self.root/'project/release_checks.json'),report)
                attacks.assert_called_once()
                self.assertEqual(mutations.call_count,int(failed!=stages[0]))
                self.assertEqual(seeded.call_count,int(failed==stages[2]))


if __name__=='__main__':unittest.main()
