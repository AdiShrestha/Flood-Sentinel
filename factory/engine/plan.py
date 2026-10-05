"""One agent-authored plan. Strict executable contract; no hand-maintained registry family."""
import re
import math
from .io import inside, read_csv
from .metrics import EvidenceError
from .schema import (expect_bool, expect_dict, expect_enum, expect_float,
                     expect_id, expect_int, expect_list, expect_str,
                     validate_json_value)
from .contract import command_to_contract, contract_argv_template, validate_contract

# Plans are JSON contracts. CSV readers use metrics.number separately because
# CSV measurements arrive as strings; plans must never coerce numeric strings.
number = expect_float

METRICS={'auroc','average_precision','accuracy','f1','brier','log_loss'}
REVIEW_TOPICS={'method_identity','data_and_leakage','training_sufficiency','statistics','baseline_fairness','ablation_sensitivity','generalization_failures','reproducibility','claims_and_venue'}

def need(condition, message):
    if not condition: raise EvidenceError(message)

def text(x, name):
    need(isinstance(x,str) and bool(x.strip()) and x not in ('TODO','REPLACE_ME'),name+' must be meaningful text')

def seq(x,name,nonempty=True):
    need(isinstance(x,list) and (bool(x) or not nonempty),name+' must be a '+('nonempty ' if nonempty else '')+'list')

def integer(x,name,minimum):
    need(type(x) is int and x>=minimum,name+f' must be an integer >= {minimum}')

def _paths(root, values, field):
    seq(values, field)
    for value in values:
        text(value, field+'[]')
        inside(root, value)
        from pathlib import PurePosixPath
        need(str(PurePosixPath(value)) == value, field+' must use canonical relative paths')
    need(len(values)==len(set(values)),field+' contains duplicates')

def _ids(values, field, known):
    seq(values,field)
    for value in values:
        expect_id(value,field+'[]');need(value in known,field+' references unknown experiment')
    need(len(values)==len(set(values)),field+' contains duplicates')

def _shape(root,p):
    """Check containers and leaf types before membership, lookup or formatting."""
    expect_dict(p,'plan');validate_json_value(p,'plan')
    expect_int(p.get('schema_version'),'schema_version',minimum=3,maximum=3)
    for key in ('factory_version','profile','intent','data_origin'):
        expect_str(p.get(key),key)
    expect_id(p.get('project_id'),'project_id')
    _paths(root,p.get('frozen_paths'),'frozen_paths')
    _paths(root,p.get('release_files'),'release_files')
    expect_dict(p.get('policy'),'policy')
    seq(p.get('experiments'),'experiments')
    for i,e in enumerate(p['experiments']):
        field=f'experiments[{i}]';expect_dict(e,field)
        expect_id(e.get('id'),field+'.id')
        for key in ('model','role'):expect_str(e.get(key),field+'.'+key)
        need('command' in e or 'execution_contract' in e,field+' needs an execution_contract or legacy command')
        if 'command' in e:
            seq(e['command'],field+'.command')
            for arg in e['command']:text(arg,field+'.command[]')
        if 'execution_contract' in e:expect_dict(e['execution_contract'],field+'.execution_contract')
        _paths(root,e.get('code_paths'),field+'.code_paths')
        seq(e.get('evaluation_splits'),field+'.evaluation_splits')
        for split in e['evaluation_splits']:
            expect_enum(split,{'train','validation','test','ood'},field+'.evaluation_splits[]')
        expect_dict(e.get('training'),field+'.training')
        expect_str(e['training'].get('mode'),field+'.training.mode')
        expect_dict(e.get('config'),field+'.config')
        if e['role']=='baseline':expect_str(e.get('baseline_class'),field+'.baseline_class')
    known={e['id'] for e in p['experiments']}
    seq(p.get('comparisons'),'comparisons',False)
    for i,c in enumerate(p['comparisons']):
        field=f'comparisons[{i}]';expect_dict(c,field);expect_id(c.get('id'),field+'.id')
        for key in ('metric','sampling_unit','assertion'):expect_str(c.get(key),field+'.'+key)
        seq(c.get('pairs'),field+'.pairs')
        for pair in c['pairs']:
            expect_list(pair,field+'.pairs[]',min_len=2,max_len=2)
            for eid in pair:expect_id(eid,field+'.pairs[][]')
    seq(p.get('claims'),'claims')
    for i,c in enumerate(p['claims']):
        field=f'claims[{i}]';expect_dict(c,field);expect_id(c.get('id'),field+'.id')
        expect_str(c.get('kind'),field+'.kind');_ids(c.get('experiment_ids'),field+'.experiment_ids',known)
        if c['kind']=='comparative':expect_id(c.get('comparison_id'),field+'.comparison_id')
    analyses=expect_dict(p.get('analyses'),'analyses');analysis_ids=set()
    need(set(analyses)<={'failures','sensitivity','ablations'},'unsupported analysis kind')
    exps={e['id']:e for e in p['experiments']}
    for kind,entries in analyses.items():
        seq(entries,'analyses.'+kind,False)
        for i,entry in enumerate(entries):
            field=f'analyses.{kind}[{i}]';expect_dict(entry,field)
            expect_id(entry.get('id'),field+'.id',seen=analysis_ids)
            if kind=='failures':
                eid=expect_id(entry.get('experiment_id'),field+'.experiment_id')
                need(eid in known,field+' references unknown experiment')
                split=expect_enum(entry.get('split','test'),{'train','validation','test','ood'},field+'.split')
                need(split in exps[eid]['evaluation_splits'],field+' split is not evaluated')
                condition=expect_dict(entry.get('condition'),field+'.condition',required_keys={'column','equals'})
                text(condition['column'],field+'.condition.column')
                need(type(condition['equals']) in (str,int,float,bool),field+' condition.equals must be scalar')
            else:
                _ids(entry.get('experiment_ids'),field+'.experiment_ids',known)
                expected_role='sensitivity' if kind=='sensitivity' else 'ablation'
                need(all(exps[eid]['role']==expected_role for eid in entry['experiment_ids']),field+' roles differ from analysis')
                if kind=='sensitivity':
                    expect_enum(entry.get('metric'),METRICS,field+'.metric');text(entry.get('parameter'),field+'.parameter')
                    levels=expect_list(entry.get('levels'),field+'.levels',min_len=3)
                    for value in levels:expect_float(value,field+'.levels[]')
                    need(len(set(levels))==len(levels),field+' has duplicate levels')
                    for eid in entry['experiment_ids']:
                        expect_float(exps[eid]['config'].get(entry['parameter']),field+'.config.parameter')
                else:
                    components=seq(entry.get('components'),field+'.components')
                    for component in components:text(component,field+'.components[]')
                    need(len(set(components))==len(components),field+' duplicate components')
                    for eid in entry['experiment_ids']:
                        for component in components:expect_bool(exps[eid]['config'].get(component),field+'.config.'+component)
                    if len(components)>5:
                        need(entry.get('design')=='fractional',field+' requires fractional design')
                        text(entry.get('alias_structure'),field+'.alias_structure')
    if p.get('split_order') is not None:
        expect_enum(p['split_order'],{'temporal','random','group'},'split_order')
    if p.get('analysis_report') is not None:
        text(p['analysis_report'],'analysis_report');inside(root,p['analysis_report'])
    hardware=p.get('hardware')
    if hardware is not None:
        expect_dict(hardware,'hardware')
        expect_id(hardware.get('experiment_id'),'hardware.experiment_id')
        for key in ('energy_claim','memory_claim'):
            if key in hardware:expect_bool(hardware[key],'hardware.'+key)

def validate(root,p):
    _shape(root,p)
    need(isinstance(p,dict),'plan must be object')
    need(p.get('schema_version')==3,'schema_version must be 3')
    need(p.get('factory_version') in ('3.0.0','3.0.1','3.1.0','3.1.1','3.2.0','3.3.0'),'factory_version must be 3.0.0, 3.0.1, 3.1.0, 3.1.1, 3.2.0, or 3.3.0')
    text(p.get('project_id'),'project_id')
    need(p.get('profile')=='binary_classification','UNSUPPORTED_PROFILE: use reviewed domain adapter; never reuse binary checks for another task')
    need(p.get('intent') in ('research','fixture'),'intent must be research or fixture')
    need(p.get('data_origin') in ('observational','simulation','fixture'),'data_origin must disclose observational, simulation, or fixture')
    need(p['intent']=='fixture' or p['data_origin']!='fixture','fixture-origin data cannot support research intent')
    for key in ('population','license','independence_rationale','sampling_rationale'):
        text(p.get(key),key)
    for key in ('cohort','source_records','methodology','dependency_lock'):
        text(p.get(key),key);inside(root,p[key])
    seq(p.get('frozen_paths'),'frozen_paths')
    for x in p['frozen_paths']:inside(root,x)
    need('source' in p['frozen_paths'],'freeze the whole source directory, including added files')
    for x in (p['cohort'],p['source_records'],p['methodology'],p['dependency_lock']):
        need(any(x==f or x.startswith(f.rstrip('/')+'/') for f in p['frozen_paths']),f'{x} must be inside frozen_paths')
    generated = {'project/audit_report.json','project/review.json','project/RELEASE_CERTIFICATION.json'}
    for f in p['frozen_paths']:
        # Generated reports and bundles are mutable outputs. Freezing them would
        # let a stale/hand-edited report become part of the evidence baseline.
        need(not (f in ('.','project') or f.split('/')[0] in ('TAKE_THIS','DROP_HERE','factory')
                  or f=='project/.factory' or f.startswith('project/.factory/') or f in generated),
             'frozen_paths cannot contain generated state or factory installation')
    policy=p.get('policy');need(isinstance(policy,dict),'policy object required')
    # Conservative policy minima, not universal scientific sample-size proofs.
    research=p['intent']=='research'
    integer(policy.get('min_test_groups'),'min_test_groups',30 if research else 2)
    integer(policy.get('min_class_count'),'min_class_count',10 if research else 2)
    integer(policy.get('min_seeds'),'min_seeds',5)
    need(0<number(policy.get('metric_tolerance'))<=1e-4,'metric_tolerance must be >0 and <=1e-4')
    if research or p.get('data_provenance') is not None:
        provenance=p.get('data_provenance');text(provenance,'data_provenance');inside(root,provenance)
        need(any(provenance==f or provenance.startswith(f+'/') for f in p['frozen_paths']),
             'data_provenance must be inside frozen_paths')
    seq(p.get('experiments'),'experiments'); ids=set()
    for e in p['experiments']:
        need(isinstance(e,dict),'experiment must be object');eid=e.get('id')
        need(isinstance(eid,str) and re.fullmatch(r'[A-Za-z0-9_-]{1,80}',eid),'unsafe experiment id')
        need(eid not in ids,'duplicate experiment id');ids.add(eid)
        text(e.get('model'),'model');integer(e.get('seed'),'seed',0)
        need(e.get('role') in ('benchmark','baseline','control','ablation','sensitivity','ood','reproduction'),'unsupported role')
        seq(e.get('code_paths'),'code_paths')
        for cp in e['code_paths']: inside(root,cp)
        need(all(cp=='source' or cp.startswith('source/') for cp in e['code_paths']),'code_paths must be under source/')
        contract=e.get('execution_contract')
        if contract is None:contract,_=command_to_contract(e['command'],e['code_paths'])
        validate_contract(contract,root,e['code_paths'])
        launch=contract_argv_template(contract)
        if 'command' in e and 'execution_contract' in e:
            legacy,_=command_to_contract(e['command'],e['code_paths'])
            need(contract_argv_template(legacy)==launch,'legacy command disagrees with execution_contract')
        need(any('{run_dir}' in x for x in launch),'execution contract must receive {run_dir}')
        need(any('{seed}' in x for x in launch),'execution contract must receive {seed}')
        need(isinstance(e.get('config'),dict),'config object required')
        need(0<=number(e.get('threshold'))<=1,'predeclared threshold required in [0,1]')
        seq(e.get('evaluation_splits'),'evaluation_splits')
        need('test' in e['evaluation_splits'],'test evaluation required')
        if e['role']=='ood':need('ood' in e['evaluation_splits'],'OOD role requires OOD evaluation rows')
        need(len(set(e['evaluation_splits']))==len(e['evaluation_splits']),'duplicate split')
        t=e.get('training');need(isinstance(t,dict),'training policy required')
        need(t.get('mode') in ('early_stopping','fixed','deterministic'),'unsupported training mode')
        if t['mode']!='deterministic':
            integer(t.get('min_epochs'),'min_epochs',2);integer(t.get('max_epochs'),'max_epochs',t['min_epochs'])
            if t['mode']=='early_stopping':
                integer(t.get('patience'),'patience',2);need(number(t.get('min_delta'))>=0,'min_delta cannot be negative')
                need(t['max_epochs']>=t['patience']+1,'early-stop event infeasible within maximum epochs')
            else:
                integer(t.get('tail_window'),'tail_window',2)
                need(t['max_epochs']>=2*t['tail_window'],'fixed training needs at least two tail windows')
                need(0<number(t.get('relative_tolerance'))<=.05,'fixed convergence tolerance must be <=.05')
        text(t.get('rationale'),'training rationale')
        if e['role']=='baseline':
            need(e.get('baseline_class') in ('trivial','historical','current','mechanism_matched'),'baseline_class invalid')
            text(e.get('reference'),'baseline reference')
    lookup={e['id']:e for e in p['experiments']}
    for e in p['experiments']:
        if e['role']=='reproduction':
            ref=expect_id(e.get('reproduces'),e['id']+'.reproduces')
            need(ref in lookup and lookup[ref]['role']!='reproduction','reproduction must reference original experiment')
            for key in ('model','config','seed','threshold','evaluation_splits','code_paths'):
                need(e[key]==lookup[ref][key],'reproduction '+key+' differs from original')
            need({k:v for k,v in e['training'].items() if k!='rationale'}==
                 {k:v for k,v in lookup[ref]['training'].items() if k!='rationale'},
                 'reproduction training policy differs from original')
    comparisons=p.get('comparisons');seq(comparisons,'comparisons',False);cids=set()
    for c in comparisons:
        text(c.get('id'),'comparison id');need(c['id'] not in cids,'duplicate comparison');cids.add(c['id'])
        seq(c.get('pairs'),'comparison pairs')
        need(len(c['pairs'])>=policy['min_seeds'],'comparisons need planned independent seed pairs')
        used=set();seeds=set();models=set()
        for pair in c['pairs']:
            need(set(pair)<=ids and pair[0]!=pair[1],'comparison pair IDs invalid')
            need(not set(pair)&used,'comparison reuses an experiment');used.update(pair)
            a,b=(lookup[eid] for eid in pair)
            need(a['seed']==b['seed'] and a['seed'] not in seeds,'paired seeds mismatch or duplicate');seeds.add(a['seed'])
            need(a['role']!='reproduction' and b['role']!='reproduction','replay cannot count as independent evidence')
            models.add((a['model'],b['model']))
        need(len(models)==1,'cannot pool different model contrasts as independent seeds')
        need(c.get('metric') in METRICS,'unknown metric; AUPRC is ambiguous: specify average_precision')
        need(c.get('sampling_unit') in ('seed_fixed_test','test_group'),'comparison sampling_unit must be test_group or seed_fixed_test')
        if c['sampling_unit']=='seed_fixed_test':
            need(c.get('inference_scope')=='fixed_test_corpus','seed inference requires explicit inference_scope=fixed_test_corpus')
        else:
            need(c.get('inference_scope','test_population_conditional_on_trained_models')=='test_population_conditional_on_trained_models','test-group inference is conditional on trained models')
        need(c.get('assertion') in ('superiority','inferiority','inconclusive','estimate'),'unsupported assertion; equivalence is not non-significance')
        need(0<number(c.get('alpha'))<=.1,'alpha invalid')
        need(number(c.get('minimum_effect'))>=0,'minimum_effect invalid')
        if c['metric']!='log_loss':need(c['minimum_effect']<=1,'minimum_effect exceeds bounded metric range')
        need(number(c.get('max_ci_width'))>0,'prospective precision target required')
        draws=c.get('inference_draws',2000 if c['sampling_unit']=='test_group' else 10000)
        expect_int(draws,'inference_draws',minimum=1000,maximum=1000000)
        if c['assertion'] in ('superiority','inferiority'):
            if c['sampling_unit']=='seed_fixed_test':units=len(c['pairs'])
            else:
                rows=read_csv(inside(root,p['cohort']),{'group_id','split'})
                units=len({r['group_id'] for r in rows if r['split']=='test' and r['group_id']})
            need(units>=math.ceil(math.log2(2*len(comparisons))-math.log2(c['alpha'])),
                 'infeasible two-sided sign-flip resolution for Holm family: '+c['id'])
            exact_limit=12 if c['sampling_unit']=='test_group' else 16
            if units>exact_limit:
                need(1/(draws+1)<=c['alpha']/len(comparisons),
                     'infeasible Monte Carlo p-value resolution for Holm family: '+c['id'])
    # A single multiplicity family is deliberate: agents cannot carve convenient subfamilies.
    need(len({c['alpha'] for c in comparisons})<=1,'all confirmatory comparisons share alpha and Holm family')
    seq(p.get('claims'),'claims'); claimids=set()
    for c in p['claims']:
        text(c.get('id'),'claim id');need(c['id'] not in claimids,'duplicate claim id');claimids.add(c['id'])
        for k in ('text','estimand','population','scope'):text(c.get(k),'claim '+k)
        need(c.get('kind') in ('descriptive','comparative','mechanistic','generalization','efficiency','simulation'),'unsupported claim kind')
        seq(c.get('experiment_ids'),'claim experiment_ids');need(set(c['experiment_ids'])<=ids,'orphan claim')
        if c['kind']=='comparative':
            need(c.get('comparison_id') in cids,'comparative claim needs comparison_id')
            contrast=next(x for x in comparisons if x['id']==c['comparison_id'])
            need({eid for pair in contrast['pairs'] for eid in pair}<=set(c['experiment_ids']),'comparative claim must bind all compared experiments')
            if contrast['sampling_unit']=='seed_fixed_test':
                need(c.get('inference_scope')=='fixed_test_corpus' and c['population']=='fixed_test_corpus',
                     'seed-only comparative claim must restrict population and inference_scope to fixed_test_corpus')
            elif c.get('inference_scope') is not None:
                need(c['inference_scope']=='test_population_conditional_on_trained_models','comparative claim inference_scope mismatch')
        if c['kind']=='generalization':need(any(e['id'] in c['experiment_ids'] and e['role']=='ood' for e in p['experiments']),'generalization requires OOD experiments')
        if c['kind']=='efficiency':need(bool(p.get('hardware')),'efficiency claim needs hardware observations')
        if p['data_origin']=='simulation':need(c['kind']=='simulation' or 'simulation' in c['scope'].lower(),'simulation must be visible in claim scope')
    seq(p.get('release_files'),'release_files')
    for f in p['release_files']:inside(root,f)
    need(isinstance(p.get('analyses'),dict),'analyses object required (empty allowed)')
    if p.get('hardware'):
        h=p['hardware']; need(isinstance(h,dict),'hardware must be an object')
        for k in ('experiment_id','min_trials','minimum_sustained_seconds'): need(k in h,'hardware missing '+k)
        need(h['experiment_id'] in ids,'hardware experiment unknown'); integer(h['min_trials'],'hardware.min_trials',5); need(number(h['minimum_sustained_seconds'])>=30,'hardware sustained duration must be >=30 seconds')
    # Unknown analysis kinds are not silently ignored.
    need(set(p['analyses'])<={'failures','sensitivity','ablations'},'unsupported analysis kind')
    for kind,items in p['analyses'].items():seq(items,kind,False)
    return p
