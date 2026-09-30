#!/usr/bin/env python3
"""Read-only forensic audit. Requires numpy, scikit-learn, pyarrow; never imports project models."""
import argparse, ast, collections, hashlib, json
from pathlib import Path
import numpy as np
import pyarrow.parquet as pq
from sklearn.metrics import roc_auc_score, average_precision_score, precision_score

def main():
 ap=argparse.ArgumentParser();ap.add_argument('project');ap.add_argument('--output',required=True);a=ap.parse_args();root=Path(a.project)
 runs=[]; ids=set(); counts=collections.Counter(); errors=[]
 for p in sorted((root/'runs').glob('*/run_manifest.json')):
  m=json.loads(p.read_text()); pred=p.parent/m['predictions_parquet']; df=pq.read_table(pred).to_pandas()
  y=df["true_label" if "true_label" in df.columns else "ground_truth"].to_numpy();s=df.predicted_prob.to_numpy(); ids.update(df.candidate_id)
  vals={'auroc':float(roc_auc_score(y,s)),'average_precision':float(average_precision_score(y,s)), 'precision_at_0_5':float(precision_score(y,s>=.5,zero_division=0))}
  runs.append({'run_id':m['run_id'],'epochs':m.get('epochs'),'n':len(df),'unique_scores':int(len(set(s))),'recorded_metrics':m['metrics'],'independent_metrics':vals,'hash_matches':hashlib.sha256(pred.read_bytes()).hexdigest()==m['predictions_parquet_sha256']})
  counts['runs']+=1;counts['two_epochs']+=m.get('epochs')==2;counts['n_12']+=len(df)==12
  counts['auroc_disagrees']+=abs(vals['auroc']-m['metrics']['auroc'])>5e-5
  counts['auprc_disagrees_with_AP']+=abs(vals['average_precision']-m['metrics']['auprc'])>5e-5
  counts['corrected_below_chance']+=vals['auroc']<.5;counts['reported_below_chance']+=m['metrics']['auroc']<.5
  counts['binary_only_probabilities']+=set(s)<={0.,1.}
 # Demonstrate the exact project metric function without importing torch/model modules.
 tree=ast.parse((root/'source/scripts/run_amlworld_benchmark.py').read_text())
 f=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='compute_binary_metrics')
 f.returns=None
 for arg in f.args.args:arg.annotation=None
 env={'np':np};exec(compile(ast.fix_missing_locations(ast.Module(body=[f],type_ignores=[])),'extracted_metric','exec'),env)
 oracle_cases=[]
 for y,s in [([0,1],[.1,.9]),([0,1],[.9,.1]),([0,1],[.5,.5])]:
  oracle_cases.append({'labels':y,'scores':s,'original':env['compute_binary_metrics'](np.array(y),np.array(s)),'correct_auroc':float(roc_auc_score(y,s)),'correct_AP':float(average_precision_score(y,s))})
 taxonomy=json.loads((root/'project/failure_taxonomy.json').read_text())
 def candidate_ids(obj):
  if isinstance(obj,dict):
   for k,v in obj.items():
    if isinstance(v,str) and v.startswith(('cand_','audit_cand_')):yield v
    else:yield from candidate_ids(v)
  elif isinstance(obj,list):
   for x in obj:yield from candidate_ids(x)
 named=set(candidate_ids(taxonomy)); missing=sorted(named-ids)
 inputs={str(p.relative_to(root)):hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted((root/'source').rglob('*.py'))}
 out={'counts':dict(counts),'unique_prediction_ids':len(ids),'taxonomy_ids':sorted(named),'phantom_taxonomy_ids':missing,'metric_oracles':oracle_cases,'runs':runs,'source_sha256':inputs,'not_executed':['model training','M3 timing/energy','whole project test suite','historical data acquisition']}
 Path(a.output).write_text(json.dumps(out,indent=2)+'\n');print(json.dumps({'counts':dict(counts),'unique_prediction_ids':len(ids),'phantom_taxonomy_ids':missing,'metric_oracles':oracle_cases},indent=2))
if __name__=='__main__':main()
