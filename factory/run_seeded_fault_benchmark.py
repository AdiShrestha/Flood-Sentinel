#!/usr/bin/env python3
"""Paired synthetic QA projects exercising the real CLI; never research evidence.

The default creates 36 faulted projects and 36 matched clean controls. Detection
is counted only for the intended check, never for setup errors or an unrelated
failure. Known same-user limitations remain visible as undetected faults.
"""
import argparse
import copy
import csv
import datetime
import hashlib
import json
import math
import os
from pathlib import Path
import random
import re
import subprocess
import sys
import tempfile

FACTORY=Path(__file__).resolve().parent
FAMILIES={
    'group_leakage':(True,'leakage across splits'),
    'entity_leakage':(True,'leakage across splits'),
    'temporal_leakage':(True,'temporal order violated'),
    'label_peeking':(False,'label secrecy is not enforced by the same-user backend'),
    'fabricated_origin':(False,'author-declared provenance does not authenticate acquisition'),
    'test_tuned_threshold':(True,'plan changed after freeze'),
    'favorable_attempt_selection':(True,'attempt membership differs|same-epoch retries'),
    'unfrozen_payload':(True,'frozen source|source Python script|Python script under frozen source'),
    'forged_receipt':(True,'signature'),
    'padded_review':(True,'repetitive or placeholder reasoning'),
    'below_chance_result':(True,'BELOW_CHANCE AUROC requires an explicit descriptive null-result claim'),
    'wrong_inference_unit':(True,'inference_scope=fixed_test_corpus'),
}
SCRIPT='''import argparse,csv,json
from pathlib import Path
parser=argparse.ArgumentParser()
parser.add_argument('--output-dir',type=Path,required=True)
parser.add_argument('--seed',type=int,required=True)
parser.add_argument('--experiment-id',required=True)
args=parser.parse_args()
rows=list(csv.DictReader(open('data/cohort.csv')))
with open(args.output_dir/'predictions.csv','w',newline='') as stream:
 writer=csv.DictWriter(stream,fieldnames=['sample_id','score']);writer.writeheader()
 for row in rows:
  if row['split'] in ('validation','test'):
   score=float(row['feature_score'])
   writer.writerow({'sample_id':row['sample_id'],'score':score})
(args.output_dir/'method.txt').write_text('Fixed feature-score mapping for explicitly synthetic QA inputs, without learned parameters.')
(args.output_dir/'result.json').write_text(json.dumps({'experiment_id':args.experiment_id,'seed':args.seed,'config':{},'predictions':'predictions.csv','method_evidence':'method.txt'}))
'''


def binomial_interval(successes,total,alpha=.05):
    """Exact equal-tail Clopper-Pearson inversion, conditional on iid trials."""
    if type(successes) is not int or type(total) is not int or not 0<=successes<=total or total<1:
        raise ValueError('invalid binomial counts')
    if not 0<alpha<1:raise ValueError('invalid alpha')
    log_coefficients=[math.lgamma(total+1)-math.lgamma(k+1)-math.lgamma(total-k+1) for k in range(total+1)]
    def probability(p,first,last):
        if p==0:return float(first<=0<=last)
        if p==1:return float(first<=total<=last)
        log_p,log_q=math.log(p),math.log1p(-p)
        # Evaluate the entire mass in log space. Computing a huge binomial
        # coefficient before multiplying small powers overflows at valid
        # simulation counts, even though every final probability is bounded.
        return math.fsum(math.exp(log_coefficients[k]+k*log_p+(total-k)*log_q) for k in range(first,last+1))
    def solve(first,last,increasing):
        low,high=0.,1.
        for _ in range(80):
            midpoint=(low+high)/2;value=probability(midpoint,first,last)
            if (value<alpha/2)==increasing:low=midpoint
            else:high=midpoint
        return (low+high)/2
    return [0. if successes==0 else solve(successes,total,True),
            1. if successes==total else solve(0,successes,False)]


def _write(path,value):
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(value,indent=2,sort_keys=True)+'\n')


def _project(root,family,seed):
    for folder in ('source','data','project'): (root/folder).mkdir(parents=True)
    rng=random.Random(seed);rows=[]
    for i in range(90):
        label=i%2
        rows.append({'sample_id':f's{i}','label':str(label),'group_id':f'g{i}','entity_ids':f'e{i}',
                     'split':('train','validation','test')[i//30],'source_ids':f'r{i}',
                     'timestamp':str(i),'feature_score':str(rng.uniform(.56,.89) if label else rng.uniform(.11,.44))})
    with (root/'data/cohort.csv').open('w',newline='') as stream:
        writer=csv.DictWriter(stream,fieldnames=list(rows[0]));writer.writeheader();writer.writerows(rows)
    (root/'data/source_records.csv').write_text('record_id,origin\n'+''.join(f'r{i},fixture\n' for i in range(90)))
    (root/'source/run.py').write_text(SCRIPT)
    (root/'source/requirements.lock').write_text('standard-library-only; synthetic QA fixture\n')
    (root/'project/methodology.md').write_text(
        'Synthetic QA fixture only. Ninety constructed rows form separate train, validation and test groups. '
        'A preregistered deterministic feature mapping tests evidence consistency; it cannot establish research performance. '
        'No learned optimization, real population, external acquisition or independent reviewer is claimed.\n')
    experiment={'id':'fixed','model':'fixed-feature-map','seed':seed,'role':'benchmark',
                'execution_contract':{'runtime_id':'python-cpu-v1','entrypoint':'source/run.py',
                    'arguments':['--output-dir','{run_dir}','--seed','{seed}','--experiment-id','{experiment_id}'],
                    'network':'unrestricted','wall_seconds':30},
                'code_paths':['source'],'config':{},'threshold':.5,'evaluation_splits':['validation','test'],
                'training':{'mode':'deterministic','rationale':'The declared fixed input-feature map has no learned parameters; this project is a synthetic QA fixture.'}}
    plan={'schema_version':3,'factory_version':'3.3.0','project_id':f'qa-{family}-{seed}',
          'profile':'binary_classification','intent':'fixture','data_origin':'fixture','population':'Constructed QA inputs only.',
          'license':'CC0 synthetic QA fixtures','independence_rationale':'Distinct constructed sample, source, group and entity IDs across splits.',
          'sampling_rationale':'Seeded synthetic inputs exercise the selected structural mechanisms, without population claims.',
          'cohort':'data/cohort.csv','source_records':'data/source_records.csv','methodology':'project/methodology.md',
          'dependency_lock':'source/requirements.lock','frozen_paths':['source','data','project/methodology.md'],
          'experiments':[experiment],'comparisons':[],
          'claims':[{'id':'fixture','text':'The declared fixed mapping produces its specified QA outputs.',
                     'kind':'descriptive','estimand':'Fixed synthetic corpus behavior','population':'Constructed QA inputs only.',
                     'scope':'Synthetic QA only; no research conclusion.','experiment_ids':['fixed']}],
          'analyses':{},'release_files':['project/methodology.md'],
          'policy':{'min_test_groups':30,'min_class_count':10,'min_seeds':5,'metric_tolerance':1e-8}}
    if family=='temporal_leakage':plan['split_order']='temporal'
    if family=='wrong_inference_unit':
        script=SCRIPT.replace('import argparse,csv,json','import argparse,csv,json,random')
        script=script.replace("rows=list(csv.DictReader(open('data/cohort.csv')))",
                              "rng=random.Random(args.seed+(1000 if args.experiment_id.startswith('b') else 0))\nrows=list(csv.DictReader(open('data/cohort.csv')))")
        script=script.replace("score=float(row['feature_score'])", "score=max(.01,min(.99,float(row['feature_score'])+rng.uniform(-.4,.4)))")
        (root/'source/run.py').write_text(script)
        plan['experiments']=[];pairs=[]
        for i in range(6):
            pair=[]
            for model in ('a','b'):
                item=copy.deepcopy(experiment);item.update(id=f'{model}{i}',model=model,seed=i,role='control')
                plan['experiments'].append(item);pair.append(item['id'])
            pairs.append(pair)
        plan['claims'][0]['experiment_ids']=['a0']
        plan['comparisons']=[{'id':'null-contrast','pairs':pairs,'metric':'accuracy',
                             'sampling_unit':'seed_fixed_test','inference_scope':'fixed_test_corpus',
                             'assertion':'estimate','alpha':.05,'minimum_effect':0.,'max_ci_width':2.}]
    _write(root/'project/research_plan.json',plan)
    return plan


def _before_freeze(root,family,plan):
    if family in ('group_leakage','entity_leakage','temporal_leakage'):
        path=root/'data/cohort.csv';rows=list(csv.DictReader(path.open()))
        if family=='group_leakage':rows[60]['group_id']=rows[0]['group_id']
        elif family=='entity_leakage':rows[60]['entity_ids']=rows[0]['entity_ids']
        else:rows[60]['timestamp']='15'
        with path.open('w',newline='') as stream:
            writer=csv.DictWriter(stream,fieldnames=list(rows[0]));writer.writeheader();writer.writerows(rows)
    elif family=='label_peeking':
        path=root/'source/run.py';path.write_text(path.read_text().replace("score=float(row['feature_score'])","score=.8 if row['label']=='1' else .2"))
    elif family=='below_chance_result':
        path=root/'source/run.py';path.write_text(path.read_text().replace("score=float(row['feature_score'])","score=1-float(row['feature_score'])"))
    elif family=='fabricated_origin':
        plan.update(intent='research',data_origin='observational',data_provenance='data/provenance.json')
        path=root/'data/source_records.csv';path.write_text(path.read_text().replace(',fixture',',observational'))
        _write(root/'data/provenance.json',{'dataset_identifier':'https://example.invalid/constructed-qa-data',
            'license':plan['license'],'provenance_basis':'author_declared','retrieval_date':'2026-10-03',
            'source_records_sha256':hashlib.sha256(path.read_bytes()).hexdigest(),
            'cohort_sha256':hashlib.sha256((root/'data/cohort.csv').read_bytes()).hexdigest()})
    elif family=='unfrozen_payload':
        (root/'payload.py').write_text(SCRIPT);plan['experiments'][0]['execution_contract']['entrypoint']='payload.py'
    elif family=='wrong_inference_unit':plan['comparisons'][0]['inference_scope']='test_population'
    _write(root/'project/research_plan.json',plan)


def _review(root,audit):
    from engine.plan import REVIEW_TOPICS
    evidence={'path':'project/methodology.md','sha256':hashlib.sha256((root/'project/methodology.md').read_bytes()).hexdigest()}
    prose=('project/methodology.md declares constructed QA rows, disjoint identifiers, and a fixed feature mapping. '
           'This specific review checks fixture consistency while acknowledging readable labels and self-reported acquisition; no research evidence is claimed.')
    review={'reviewer_role':'Architect','reviewer_model':'synthetic-qa-review','session_id':'synthetic-qa-session',
            'review_mode':'same_session_self_review','evidence_digest':audit['evidence_digest'],
            'checks':[{'topic':topic,'verdict':'acceptable','reasoning':topic+' '+prose,'evidence':[evidence]} for topic in sorted(REVIEW_TOPICS)],
            'diagnostic_resolutions':[{'id':item['id'],'reasoning':item['code']+' '+prose,'evidence':[evidence]} for item in audit['diagnostics']],
            'objections':[{'objection':'Synthetic fixture cannot establish population performance '+str(i),
                           'resolution':'disclosed_limitation','reasoning':prose+str(i)} for i in range(3)],
            'limitations':['Synthetic fixtures and self-reported reviews do not establish trustworthy scientific research.'],
            'venue_sources':['https://example.invalid/qa-only fixture URL, no actual venue evaluation.'],'unresolved_blockers':[]}
    _write(root/'project/review.json',review)
    return review


def _case(root,family,seed,faulted,timeout):
    import shutil
    plan=_project(root,family,seed)
    if faulted:_before_freeze(root,family,plan)
    environment=dict(os.environ);environment.update(FACTORY_SUPERVISOR_KEY=str(root.parent/'keys'/('fault.key' if faulted else 'clean.key')),
                                                   PYTHONDONTWRITEBYTECODE='1')
    for key in ('PYTHONPATH','PYTHONHOME'):environment.pop(key,None)
    transitions=[]
    def cli(command,*extra):
        process=subprocess.run([sys.executable,'-B',str(FACTORY/'gatekeeper.py'),command,str(root),*extra],
                               env=environment,cwd=FACTORY,capture_output=True,text=True,timeout=timeout)
        try:response=json.loads(process.stdout)
        except ValueError:raise RuntimeError('CLI returned invalid JSON: '+process.stderr[-500:])
        def summary(value):
            kept={key:value[key] for key in ('status','error','error_type','reason','code','errors','evidence_digest','checks_executed') if key in value}
            if 'results' in value:kept['results']=[summary(item) for item in value['results']]
            return kept
        transitions.append({'stage':command,'exit_code':process.returncode,'response':summary(response),
                            'stdout_sha256':hashlib.sha256(process.stdout.encode()).hexdigest()})
        return process.returncode,response
    code,response=cli('freeze')
    if not code:code,response=cli('run','all')
    if not code and faulted and family in ('test_tuned_threshold','favorable_attempt_selection','forged_receipt'):
        if family=='test_tuned_threshold':
            plan['experiments'][0]['threshold']=.4;_write(root/'project/research_plan.json',plan)
        elif family=='favorable_attempt_selection':
            attempt=root/'project/.factory/epoch_0001/runs/fixed/attempt0001'
            shutil.copytree(attempt,attempt.with_name('attempt0002'))
        else:
            path=root/'project/.factory/epoch_0001/runs/fixed/attempt0001/execution.json'
            record=json.loads(path.read_text());record['supervisor_receipt']['supervisor_signature']='A'*88;_write(path,record)
    if not code:code,response=cli('audit')
    if not code and family=='padded_review':
        review=_review(root,response)
        if faulted:
            for check in review['checks']:check['reasoning']='n/a '*50
            _write(root/'project/review.json',review)
        code,response=cli('certify')
        if code==43 and response.get('status')=='FIXTURE_ONLY':code=0
    # A fixture-only refusal is the expected clean review result. Every other
    # clean failure is a false positive; no malformed/setup output is a kill.
    text=json.dumps(transitions).replace(str(root),'<project>')
    failures=json.dumps([item['response'] for item in transitions if item['exit_code']!=0])
    matched=bool(re.search(FAMILIES[family][1],failures,re.I)) if FAMILIES[family][0] else False
    return {'accepted':code==0,'blocked':code!=0,'intended_check_observed':matched,
            'transitions':json.loads(text)}


def run_benchmark(*,variants=3,seed=20261003,timeout=60):
    if (type(variants) is not int or not 1<=variants<=50 or type(seed) is not int
            or type(timeout) is not int or timeout<1):
        raise ValueError('variants must be 1..50; seed integer; timeout positive integer')
    import gatekeeper as g
    rows=[];family_results={}
    with tempfile.TemporaryDirectory(prefix='factory-seeded-qa-') as temporary:
        base=Path(temporary)
        for family_index,(family,(supported,limit)) in enumerate(FAMILIES.items()):
            for variant in range(variants):
                case_seed=seed+family_index*1000+variant;folder=base/f'{family}-{variant}';folder.mkdir()
                row={'family':family,'variant':variant,'seed':case_seed,'supported_guard':supported}
                try:
                    clean=_case(folder/'clean',family,case_seed,False,timeout)
                    faulty=_case(folder/'fault',family,case_seed,True,timeout)
                    row.update(clean=clean,fault=faulty,detected=faulty['blocked'] and faulty['intended_check_observed'])
                    row['status']='PASS' if clean['accepted'] and (row['detected'] if supported else faulty['accepted']) else 'FAIL'
                except (OSError,ValueError,RuntimeError,subprocess.TimeoutExpired) as error:
                    row.update(status='ERROR',detail=str(error).replace(str(base),'<benchmark>'))
                rows.append(row)
    for family,(supported,limit) in FAMILIES.items():
        selected=[row for row in rows if row['family']==family]
        assessed=[row for row in selected if row['status']!='ERROR']
        detected=sum(bool(row.get('detected')) for row in selected)
        false_positives=sum(bool(row.get('clean',{}).get('blocked')) for row in selected)
        complete=len(assessed)==variants
        family_results[family]={'supported_guard':supported,'cases':variants,'assessed_pairs':len(assessed),'detected':detected,
            'detection_fraction':detected/variants if complete else None,
            'detection_binomial_95_ci':binomial_interval(detected,variants) if complete else None,
            'clean_false_positives':false_positives,
            'false_positive_fraction':false_positives/variants if complete else None,
            'false_positive_binomial_95_ci':binomial_interval(false_positives,variants) if complete else None,
            'known_limit':None if supported else limit}
    errors=[row['family']+':'+str(row['variant']) for row in rows if row['status']=='ERROR']
    failures=[row['family']+':'+str(row['variant']) for row in rows if row['status']=='FAIL']
    return {'schema_version':1,'factory_version':g.VERSION,'engine_sha256':g.engine_hash(),
            'created_at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'seed':seed,'variants_per_family':variants,
            'status':'PASS' if not failures and not errors else 'FAIL','fault_projects':len(rows),'clean_projects':len(rows),
            'detected_faults':sum(bool(row.get('detected')) for row in rows),
            'supported_faults':sum(row['supported_guard'] for row in rows),
            'supported_faults_detected':sum(bool(row.get('detected')) and row['supported_guard'] for row in rows),
            'clean_false_positives':sum(bool(row.get('clean',{}).get('blocked')) for row in rows),
            'known_limits_observed':sum(not row['supported_guard'] and row.get('fault',{}).get('accepted',False) for row in rows),
            'families':family_results,'failures':failures,'errors':errors,'cases':rows,
            'scope':'matched synthetic QA fixtures through real CLI; PASS means supported guards and clean controls behave as registered, not all flaws detected',
            'interval_scope':'exact binomial 95% intervals per family assume independent cases from that synthetic generator; no pooled iid interval or real-project detection-rate claim',
            'limitations':['Constructed fixture variants are not independent real research projects or a representative benchmark.',
                           'Known unsupported label secrecy and acquisition authenticity are counted as undetected, not security successes.',
                           'Post-freeze threshold mutation tests frozen-plan integrity, not every form of adaptive test use.',
                           'Tiny per-family samples yield wide conditional intervals; no universal detection or false-positive guarantee.'],
            'benchmark_script_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest()}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--variants',type=int,default=3);parser.add_argument('--seed',type=int,default=20261003)
    parser.add_argument('--timeout',type=int,default=60);parser.add_argument('--report',type=Path)
    args=parser.parse_args()
    try:report=run_benchmark(variants=args.variants,seed=args.seed,timeout=args.timeout)
    except ValueError as error:parser.error(str(error))
    if args.report:_write(args.report,report)
    print(json.dumps({key:report[key] for key in ('status','fault_projects','clean_projects','detected_faults',
           'supported_faults_detected','clean_false_positives','known_limits_observed','failures','errors')},indent=2))
    return 0 if report['status']=='PASS' else 1

if __name__=='__main__':raise SystemExit(main())
