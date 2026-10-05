#!/usr/bin/env python3
"""Reproducible inference simulations under stated synthetic assumptions.

Report interval coverage and decisions for null/unequal models across sizes.
These are experiments, not release thresholds or real-project error guarantees.
"""
import argparse
import datetime
import hashlib
import json
import random
from pathlib import Path
from engine.metrics import paired_inference,paired_group_inference
from run_seeded_fault_benchmark import binomial_interval


def _rate(count,total):
    return {'count':count,'trials':total,'fraction':count/total,
            'binomial_95_ci':binomial_interval(count,total)}


def run_simulations(*,studies=100,seed=20261003):
    if type(studies) is not int or not 20<=studies<=5000 or type(seed) is not int:
        raise ValueError('studies must be an integer in 20..5000; seed must be integer')
    import gatekeeper as g
    engine_before=g.engine_hash();validation_before=g.validation_hash()
    rng=random.Random(seed);rows=[]
    for n in (5,7,10,30):
        for true_effect in (0.,.3):
            covered=positive=negative=two_sided=0;raw=[]
            for study in range(studies):
                differences=[rng.gauss(true_effect,1.) for _ in range(n)]
                result=paired_inference(differences,[0.]*n,draws=1000,seed=seed+study)
                contains=result['ci'][0]<=true_effect<=result['ci'][1]
                significant=result['p_raw']<=.05
                covered+=contains;two_sided+=significant
                positive+=significant and result['ci'][0]>0
                negative+=significant and result['ci'][1]<0
                raw.append({'effect':result['effect'],'ci':result['ci'],'p_raw':result['p_raw']})
            rows.append({'generator':'iid normal paired differences, standard deviation 1',
                         'inference':'seed units conditional on a fixed corpus','n_units':n,
                         'true_effect':true_effect,'ci_coverage':_rate(covered,studies),
                         'two_sided_rejections':_rate(two_sided,studies),
                         'positive_decisions':_rate(positive,studies),'negative_decisions':_rate(negative,studies),
                         'minimum_exact_two_sided_p':2/2**n if n<=16 else None,'raw':raw})
    for n in (30,60):
        for unequal in (False,True):
            # Each independent group contains one case and one control. Fixed
            # model score = 0.35/0.65 + independent uniform noise. All scores
            # remain probabilities. Brier gain has an analytic population mean.
            width_a,width_b=(.15 if unequal else .30),.30
            truth=(width_b**2-width_a**2)/3
            covered=positive=negative=two_sided=degenerate=0;raw=[]
            labels=[0,1]*n;groups=[str(i//2) for i in range(2*n)]
            for study in range(studies):
                a=[(.65 if label else .35)+rng.uniform(-width_a,width_a) for label in labels]
                b=[(.65 if label else .35)+rng.uniform(-width_b,width_b) for label in labels]
                result=paired_group_inference(labels,[(a,b)],groups,'brier',draws=1000,seed=seed+study)
                contains=result['ci'][0]<=truth<=result['ci'][1]
                significant=result['p_raw']<=.05
                covered+=contains;two_sided+=significant;degenerate+=result['degenerate_variance']
                positive+=significant and result['ci'][0]>0
                negative+=significant and result['ci'][1]<0
                raw.append({'effect':result['effect'],'ci':result['ci'],'p_raw':result['p_raw'],
                            'degenerate_variance':result['degenerate_variance']})
            rows.append({'generator':'independent balanced two-row groups; bounded uniform score noise',
                         'inference':'test groups conditional on the supplied fixed model laws','metric':'brier',
                         'n_units':n,'true_effect':truth,'model_a_noise_halfwidth':width_a,
                         'model_b_noise_halfwidth':width_b,'ci_coverage':_rate(covered,studies),
                         'two_sided_rejections':_rate(two_sided,studies),
                         'positive_decisions':_rate(positive,studies),'negative_decisions':_rate(negative,studies),
                         'nonestimable_intervals':degenerate,'raw':raw})
    unchanged=engine_before==g.engine_hash() and validation_before==g.validation_hash()
    return {'schema_version':1,'factory_version':g.VERSION,'engine_sha256':engine_before,
            'validation_sha256':validation_before,'seed':seed,'studies_per_cell':studies,
            'created_at':datetime.datetime.now(datetime.timezone.utc).isoformat(),
            'status':'COMPLETED' if unchanged else 'SOURCE_CHANGED','source_unchanged_during_simulations':unchanged,
            'cells':rows,'script_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
            'limitations':['This is a synthetic Monte Carlo description, not a PASS threshold or representative scientific study.',
                           'Intervals assume independent repetitions within each generator; families/cells are not pooled.',
                           'Student-t coverage assumes normal independent differences; cluster BCa coverage is approximate.',
                           'At five seed units the minimum exact two-sided p is 0.0625, so a 0.05 test cannot reject.',
                           'Group model-assignment exchangeability holds for the equal-model generator, not generally for unequal models.',
                           'Training/split uncertainty, adaptive selection and heavy-tailed or dependent real data are not evaluated.']}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--studies',type=int,default=100);parser.add_argument('--seed',type=int,default=20261003)
    parser.add_argument('--report',type=Path,required=True)
    args=parser.parse_args()
    try:report=run_simulations(studies=args.studies,seed=args.seed)
    except ValueError as error:parser.error(str(error))
    args.report.parent.mkdir(parents=True,exist_ok=True)
    args.report.write_text(json.dumps(report,indent=2,sort_keys=True)+'\n')
    print(json.dumps({'status':report['status'],'cells':len(report['cells']),
                      'studies_per_cell':args.studies,'report':str(args.report)},indent=2))
    return 0 if report['status']=='COMPLETED' else 1


if __name__=='__main__':raise SystemExit(main())
