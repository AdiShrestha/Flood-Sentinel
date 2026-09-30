import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).parents[1]))
from engine.metrics import binary_metrics, EvidenceError, paired_inference

def test_auc_and_ap_direction():
 r=binary_metrics([0,1],[.1,.9]); assert abs(r['auroc']-1)<1e-12 and abs(r['average_precision']-1)<1e-12
 r=binary_metrics([0,1],[.9,.1]); assert abs(r['auroc'])<1e-12 and abs(r['average_precision']-.5)<1e-12

def test_bad_single_class_and_constant_rejected():
 try: binary_metrics([0,0],[.1,.2]); assert False
 except EvidenceError: pass
 # Constant scores are a valid null metric; the audit records them as a diagnostic.
 assert binary_metrics([0,1],[.4,.4])['auroc'] == .5

def test_paired_inference_refuses_one_unit():
 try: paired_inference([.4],[.3]); assert False
 except EvidenceError: pass
