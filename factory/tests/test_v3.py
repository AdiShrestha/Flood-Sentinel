"""Offline adversarial and lifecycle tests. Fixtures are explicitly not research evidence."""
import contextlib,csv,io,json,os,sys,tempfile,unittest
from pathlib import Path
FACTORY=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(FACTORY))
import gatekeeper as g
from engine.io import read_json,write_json,sha,inventory,inside
from engine.metrics import binary_metrics,paired_inference,holm,EvidenceError
from engine.plan import REVIEW_TOPICS
from engine.audit import Audit,verify_review

# A different expression path computes known fixture metrics. These are fixtures,
# intentionally unlike a real training script, and cannot receive research release.
SCRIPT='''import csv,json,sys,math
from pathlib import Path
root=Path.cwd();out=Path(sys.argv[1]);seed=int(sys.argv[2]);eid=sys.argv[3]
cohort=list(csv.DictReader(open(root/'data/cohort.csv')))
rows=[{'sample_id':x['sample_id'],'label':x['label'],'score':0.2 if x['label']=='0' else 0.8} for x in cohort if x['split'] in ('validation','test')]
with open(out/'predictions.csv','w',newline='') as f:
 w=csv.DictWriter(f,fieldnames=['sample_id','label','score']);w.writeheader();w.writerows(rows)
(out/'method.txt').write_text('TEST FIXTURE. This algorithm produces known synthetic scores; never research evidence.')
m={'auroc':1.,'average_precision':1.,'accuracy':1.,'f1':1.,'brier':0.04,'log_loss':-math.log(.8)}
(out/'result.json').write_text(json.dumps({'experiment_id':eid,'seed':seed,'config':{},'predictions':'predictions.csv','reported_metrics':{'validation':m,'test':m},'method_evidence':'method.txt'}))
'''

def fixture(r):
 for x in ('project','data','source'): (r/x).mkdir(parents=True)
 (r/'source/run.py').write_text(SCRIPT);(r/'source/requirements.lock').write_text('standard-library-only; fixture\n')
 (r/'project/methodology.md').write_text('TEST FIXTURE ONLY. Tests gate behavior with known rows; does not evaluate research quality.\n')
 (r/'data/source_records.csv').write_text('record_id,origin\n'+''.join(f'r{i},fixture\n' for i in range(12)))
 (r/'data/cohort.csv').write_text('sample_id,label,group_id,split,source_ids\n'+''.join(f's{i},{i%2},g{i},{["train","validation","test"][i//4]},r{i}\n' for i in range(12)))
 p={'schema_version':3,'factory_version':'3.0.0','project_id':'gate-test-fixture','profile':'binary_classification','intent':'fixture','data_origin':'fixture','population':'test fixture only','license':'CC0 fixture','independence_rationale':'Each row is a toy independent unit for gate testing only.','sampling_rationale':'Not statistical research; 12 fixture rows exercise parser behavior.','cohort':'data/cohort.csv','source_records':'data/source_records.csv','methodology':'project/methodology.md','dependency_lock':'source/requirements.lock','frozen_paths':['source','data','project/methodology.md'],'experiments':[{'id':'known','model':'toy','seed':42,'role':'benchmark','command':[sys.executable,'source/run.py','{run_dir}','{seed}','{experiment_id}'],'code_paths':['source/run.py'],'config':{},'threshold':.5,'evaluation_splits':['validation','test'],'training':{'mode':'deterministic','rationale':'Known-value gate fixture, no model training.'}}],'comparisons':[],'claims':[{'id':'fixture','text':'The fixture yields known metrics.','kind':'descriptive','estimand':'fixed fixture AP','population':'fixture','scope':'test fixture only','experiment_ids':['known']}],'analyses':{},'release_files':['project/methodology.md'],'policy':{'min_test_groups':2,'min_class_count':2,'min_seeds':5,'metric_tolerance':1e-8}}
 write_json(r/'project/research_plan.json',p);return p

def evaluate(r):
 p=g.plan_at(r);_,ep,f=g.active(r);return Audit(r,p,ep,f,g.engine_hash()).run()

def forged_output_rehash(r):
 _,ep,f=g.active(r);a=ep/'runs/known/attempt0001';rec=read_json(a/'execution.json')
 files=inventory(r,[str(a.relative_to(r))]);files.pop(str((a/'execution.json').relative_to(r)))
 rec['outputs']=files;write_json(a/'execution.json',rec)

class MetricTests(unittest.TestCase):
 def test_perfect_direction(self):self.assertEqual(binary_metrics([0,1],[.1,.9])['auroc'],1.)
 def test_reverse_direction(self):self.assertEqual(binary_metrics([0,1],[.9,.1])['auroc'],0.)
 def test_ties(self):self.assertEqual(binary_metrics([0,1],[.5,.5])['auroc'],.5)
 def test_ap_not_precision(self):
  m=binary_metrics([0,1],[.9,.1]);self.assertEqual(m['average_precision'],.5);self.assertEqual(m['f1'],0.)
 def test_tie_permutation_invariant(self):
  self.assertEqual(binary_metrics([0,1,1,0],[.2,.2,.8,.8]),binary_metrics([1,0,0,1],[.2,.2,.8,.8]))
 def test_single_class(self):
  with self.assertRaises(EvidenceError):binary_metrics([0,0],[.1,.2])
 def test_nan(self):
  with self.assertRaises(EvidenceError):binary_metrics([0,1],[float('nan'),.2])
 def test_infinity(self):
  with self.assertRaises(EvidenceError):binary_metrics([0,1],[float('inf'),.2])
 def test_out_of_range(self):
  with self.assertRaises(EvidenceError):binary_metrics([0,1],[-.1,.2])
 def test_boolean(self):
  with self.assertRaises(EvidenceError):binary_metrics([False,True],[.1,.2])
 def test_pair_count(self):
  with self.assertRaises(EvidenceError):paired_inference([1],[0])
 def test_exact_signflip_resolution(self):
  p=paired_inference([1]*5,[0]*5)['p_raw'];self.assertEqual(p,2/32)
 def test_holm(self):self.assertEqual(holm([.01,.02,.5]),[.03,.04,.5])
 def test_zero_variance_is_disclosed(self):self.assertTrue(paired_inference([1,1],[1,1])['degenerate_variance'])

class LifecycleTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.r=Path(self.tmp.name);self.p=fixture(self.r)
  self.redirect=contextlib.redirect_stdout(io.StringIO());self.redirect.__enter__()
 def tearDown(self):self.redirect.__exit__(None,None,None);self.tmp.cleanup()
 def execute(self):g.freeze(self.r);self.assertEqual(g.run_exp(self.r,'known'),0)
 def test_valid_evidence_path(self):self.execute();self.assertEqual(evaluate(self.r)['errors'],[])
 def test_missing_freeze(self):
  with self.assertRaises(EvidenceError):g.active(self.r)
 def test_empty_plan_rejected(self):
  self.p['experiments']=[];write_json(self.r/g.ROOT_PLAN,self.p)
  with self.assertRaises(EvidenceError):g.freeze(self.r)
 def test_unknown_profile_rejected(self):
  self.p['profile']='causal_inference';write_json(self.r/g.ROOT_PLAN,self.p)
  with self.assertRaises(EvidenceError):g.freeze(self.r)
 def test_added_source_invalidates_freeze(self):
  self.execute();(self.r/'source/new.py').write_text('x=1\n');self.assertTrue(evaluate(self.r)['errors'])
 def test_mutated_plan_invalidates_freeze(self):
  self.execute();self.p['population']='changed';write_json(self.r/g.ROOT_PLAN,self.p);self.assertTrue(evaluate(self.r)['errors'])
 def test_mutated_prediction_hash(self):
  self.execute();_,ep,_=g.active(self.r);p=ep/'runs/known/attempt0001/predictions.csv';p.write_text(p.read_text().replace('0.8','0.9'));self.assertTrue(evaluate(self.r)['errors'])
 def test_forged_metrics_even_after_rehash(self):
  self.execute();_,ep,_=g.active(self.r);p=ep/'runs/known/attempt0001/result.json';x=read_json(p);x['reported_metrics']['test']['auroc']=0.;write_json(p,x);forged_output_rehash(self.r)
  self.assertTrue(any('independent recomputation' in x['detail'] for x in evaluate(self.r)['errors']))
 def test_phantom_prediction_even_after_rehash(self):
  self.execute();_,ep,_=g.active(self.r);p=ep/'runs/known/attempt0001/predictions.csv';p.write_text(p.read_text().replace('s8,','phantom,'));forged_output_rehash(self.r);self.assertTrue(evaluate(self.r)['errors'])
 def test_label_mismatch_even_after_rehash(self):
  self.execute();_,ep,_=g.active(self.r);p=ep/'runs/known/attempt0001/predictions.csv';p.write_text(p.read_text().replace('s8,0,','s8,1,'));forged_output_rehash(self.r);self.assertTrue(evaluate(self.r)['errors'])
 def test_group_leakage(self):
  p=self.r/'data/cohort.csv';p.write_text(p.read_text().replace('s8,0,g8,','s8,0,g0,'));g.freeze(self.r)
  self.assertTrue(any(x['code']=='COHORT' for x in evaluate(self.r)['errors']))
 def test_source_leakage(self):
  p=self.r/'data/cohort.csv';p.write_text(p.read_text().replace('test,r8','test,r0'));g.freeze(self.r);self.assertTrue(evaluate(self.r)['errors'])
 def test_single_class_cohort(self):
  p=self.r/'data/cohort.csv';p.write_text(p.read_text().replace('s9,1,','s9,0,').replace('s11,1,','s11,0,'));g.freeze(self.r);self.assertTrue(evaluate(self.r)['errors'])
 def test_missing_source_ids(self):
  p=self.r/'data/cohort.csv';p.write_text(p.read_text().replace('test,r8','test,unknown'));g.freeze(self.r);self.assertTrue(evaluate(self.r)['errors'])
 def test_amendment_preserves_epoch(self):
  g.freeze(self.r);old=(self.r/g.STATE/'epoch_0001/freeze.json').read_bytes();g.freeze(self.r,'new hypothesis disclosed');self.assertEqual((self.r/g.STATE/'epoch_0001/freeze.json').read_bytes(),old)
 def test_freeze_not_overwritten(self):
  g.freeze(self.r)
  with self.assertRaises(EvidenceError):g.freeze(self.r)
 def test_failed_run_returns_failure_and_retains_attempt(self):
  (self.r/'source/run.py').write_text('raise RuntimeError("intentional fixture failure")');g.freeze(self.r);self.assertNotEqual(g.run_exp(self.r,'known'),0)
  _,ep,_=g.active(self.r);self.assertTrue((ep/'runs/known/attempt0001/execution.json').exists())
 def test_successful_run_is_rechecked_not_reexecuted(self):
  self.execute();self.assertEqual(g.run_exp(self.r,'known'),0);_,ep,_=g.active(self.r);self.assertEqual(len(list((ep/'runs/known').glob('attempt*'))),1)
 def test_record_rejects_attempt_outside_active_epoch(self):
  self.execute();_,ep,_=g.active(self.r);outside=self.r/'outside-attempt';outside.mkdir();(outside/'execution.json').write_text((ep/'runs/known/attempt0001/execution.json').read_text())
  with self.assertRaises(EvidenceError):g.record(self.r,'known','outside-attempt')

 def test_missing_review_withholds_release(self):self.execute();self.assertEqual(g.certify(self.r),g.EXIT_REVIEW)
 def test_stale_review_withholds_release(self):
  self.execute();write_json(self.r/'project/review.json',{'evidence_digest':'stale'});self.assertEqual(g.certify(self.r),g.EXIT_REVIEW)
 def test_duplicate_json(self):
  p=self.r/'dup.json';p.write_text('{"x":1,"x":2}')
  with self.assertRaises(EvidenceError):read_json(p)
 def test_path_traversal(self):
  with self.assertRaises(EvidenceError):inside(self.r,'../outside')
 def test_symlink(self):
  (self.r/'link').symlink_to(self.r/'data/cohort.csv')
  with self.assertRaises(EvidenceError):inside(self.r,'link')
 def test_handoff_contains_evidence(self):
  self.execute();self.assertEqual(g.handoff(self.r),0);self.assertTrue(list((self.r/'TAKE_THIS').glob('*.zip')))

if __name__=='__main__':unittest.main()
