"""Regression fixtures for v3 scientific verification mechanisms."""
import json, tempfile, unittest
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import gatekeeper as g

class V3ScientificTests(unittest.TestCase):
    def setUp(self): self.t=tempfile.TemporaryDirectory(); self.d=Path(self.t.name)
    def tearDown(self): self.t.cleanup()
    def write(self,name,text): p=self.d/name; p.write_text(text); return p
    def test_tier_paraphrase(self):
        p=self.write('c.md','T-DESC; confidence intervals; SUPPORTED, NOT_SUPPORTED, or INCONCLUSIVE')
        self.assertEqual(g.tier_check(p),18)
    def test_phantom_input_hard_fail(self):
        p=self.write('x.py','def evaluate_results(data=None):\n    return {"a":1,"b":2,"c":3,"d":4,"e":5,"f":6,"g":7,"h":8,"i":9,"j":10,"k":11,"l":12,"m":13,"n":14,"o":15}\n')
        f=g._scan_phantom_input_fabrication([p]); self.assertTrue(any(x['severity']=='HARD_FAIL' for x in f))
    def test_fallback_hard_fail(self):
        p=self.write('x.py','import random\ndef evaluate(data=None):\n    if data is None:\n        return random.normal(0,1)\n')
        f=g._scan_undisclosed_synthetic_fallback([p]); self.assertTrue(any(x['severity']=='HARD_FAIL' for x in f))
    def test_result_note_required(self):
        p=self.write('r.json',json.dumps({'entries':[{'metric':'AUROC','value':0.5,'verdict':'SUPPORTED'}]})); self.assertEqual(g.verify_result_plausibility(p),34)
    def test_result_note_allows_investigation(self):
        p=self.write('r.json',json.dumps({'entries':[{'metric':'AUROC','value':0.5,'verdict':'SUPPORTED'}],'investigation_note':'checked'})); self.assertEqual(g.verify_result_plausibility(p),0)
    def test_training_floor(self):
        p=self.write('m.json',json.dumps({'convergence_evidence':{'epochs_trained':3}})); self.assertEqual(g.verify_training_sufficiency(p),32)
    def test_training_justification(self):
        p=self.write('m.json',json.dumps({'convergence_evidence':{'epochs_trained':3,'justification':'fixed analytic solver'}})); self.assertEqual(g.verify_training_sufficiency(p),0)
    def test_split_floor(self):
        p=self.write('m.json',json.dumps({'test_label_distribution':{'0':5,'1':5}})); self.assertEqual(g.verify_split_integrity(p),33)
    def test_traceability(self):
        a=self.write('a.md','sample: S9999'); s=self.write('s.json',json.dumps({'id':'S0001'})); self.assertEqual(g.verify_cross_artifact_traceability(a,[s]),35)
    def test_reproducibility(self):
        p=self.write('m.json',json.dumps({'original':{'score':1},'replay':{'score':0}})); self.assertEqual(g.verify_reproducibility(p),36)
    def test_coverage(self): self.assertEqual(g.verify_constitution_coverage(self.d),0)

if __name__=='__main__': unittest.main()
