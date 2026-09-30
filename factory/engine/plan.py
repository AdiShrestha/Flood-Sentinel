"""One agent-authored plan. Strict executable contract; no hand-maintained registry family."""
import re
from .io import inside
from .metrics import EvidenceError, number

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

def validate(root,p):
    need(isinstance(p,dict),'plan must be object')
    need(p.get('schema_version')==3,'schema_version must be 3')
    need(p.get('factory_version') in ('3.0.0','3.0.1','3.1.0','3.1.1','3.2.0','3.3.0'),'factory_version must be 3.0.0, 3.0.1, 3.1.0, 3.1.1, 3.2.0, or 3.3.0')
    text(p.get('project_id'),'project_id')
    need(p.get('profile')=='binary_classification','UNSUPPORTED_PROFILE: use reviewed domain adapter; never reuse binary checks for another task')
    need(p.get('intent') in ('research','fixture'),'intent must be research or fixture')
    need(p.get('data_origin') in ('observational','simulation','fixture'),'data_origin must disclose observational, simulation, or fixture')
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
        need(not (f in ('.','project') or f.startswith(('project/.factory','TAKE_THIS','DROP_HERE','factory')) or f in generated),'frozen_paths cannot contain generated state or factory installation')
    policy=p.get('policy');need(isinstance(policy,dict),'policy object required')
    integer(policy.get('min_test_groups'),'min_test_groups',2)
    integer(policy.get('min_class_count'),'min_class_count',2)
    integer(policy.get('min_seeds'),'min_seeds',5)
    need(0<number(policy.get('metric_tolerance'))<=1e-4,'metric_tolerance must be >0 and <=1e-4')
    seq(p.get('experiments'),'experiments'); ids=set()
    for e in p['experiments']:
        need(isinstance(e,dict),'experiment must be object');eid=e.get('id')
        need(isinstance(eid,str) and re.fullmatch(r'[A-Za-z0-9_-]{1,80}',eid),'unsafe experiment id')
        need(eid not in ids,'duplicate experiment id');ids.add(eid)
        text(e.get('model'),'model');integer(e.get('seed'),'seed',0)
        need(e.get('role') in ('benchmark','baseline','control','ablation','sensitivity','ood','reproduction'),'unsupported role')
        seq(e.get('command'),'command')
        seq(e.get('code_paths'),'code_paths')
        for cp in e['code_paths']: inside(root,cp)
        need(all(str(cp).startswith('source/') for cp in e['code_paths']),'code_paths must be under source/')
        need(any(cp in arg for cp in e['code_paths'] for arg in e['command']),
             'command must name at least one declared frozen code_path')
        for arg in e['command']:text(arg,'command argument')
        need(any('{run_dir}' in x for x in e['command']),'command must receive {run_dir}')
        need(any('{seed}' in x for x in e['command']),'command must receive {seed}')
        need(isinstance(e.get('config'),dict),'config object required')
        need(0<=number(e.get('threshold'))<=1,'predeclared threshold required in [0,1]')
        seq(e.get('evaluation_splits'),'evaluation_splits')
        need('test' in e['evaluation_splits'],'test evaluation required')
        need(len(set(e['evaluation_splits']))==len(e['evaluation_splits']),'duplicate split')
        t=e.get('training');need(isinstance(t,dict),'training policy required')
        need(t.get('mode') in ('early_stopping','fixed','deterministic'),'unsupported training mode')
        if t['mode']!='deterministic':
            integer(t.get('min_epochs'),'min_epochs',2);integer(t.get('max_epochs'),'max_epochs',t['min_epochs'])
            if t['mode']=='early_stopping':
                integer(t.get('patience'),'patience',2);need(number(t.get('min_delta'))>=0,'min_delta cannot be negative')
            else:
                integer(t.get('tail_window'),'tail_window',2)
                need(t['max_epochs']>=2*t['tail_window'],'fixed training needs at least two tail windows')
                need(0<number(t.get('relative_tolerance'))<=.05,'fixed convergence tolerance must be <=.05')
        text(t.get('rationale'),'training rationale')
        if e['role']=='baseline':
            need(e.get('baseline_class') in ('trivial','historical','current','mechanism_matched'),'baseline_class invalid')
            text(e.get('reference'),'baseline reference')
    comparisons=p.get('comparisons');seq(comparisons,'comparisons',False);cids=set()
    for c in comparisons:
        text(c.get('id'),'comparison id');need(c['id'] not in cids,'duplicate comparison');cids.add(c['id'])
        seq(c.get('pairs'),'comparison pairs')
        need(len(c['pairs'])>=policy['min_seeds'],'comparisons need planned independent seed pairs')
        for pair in c['pairs']:need(isinstance(pair,list) and len(pair)==2 and set(pair)<=ids and pair[0]!=pair[1],'comparison pair IDs invalid')
        need(c.get('metric') in METRICS,'unknown metric; AUPRC is ambiguous: specify average_precision')
        need(c.get('sampling_unit')=='seed_fixed_test','built-in comparison inference is conditional on fixed test corpus across seeds')
        need(c.get('assertion') in ('superiority','inferiority','inconclusive','estimate'),'unsupported assertion; equivalence is not non-significance')
        need(0<number(c.get('alpha'))<=.1,'alpha invalid')
        need(number(c.get('minimum_effect'))>=0,'minimum_effect invalid')
        need(number(c.get('max_ci_width'))>0,'prospective precision target required')
    # A single multiplicity family is deliberate: agents cannot carve convenient subfamilies.
    need(len({c['alpha'] for c in comparisons})<=1,'all confirmatory comparisons share alpha and Holm family')
    seq(p.get('claims'),'claims'); claimids=set()
    for c in p['claims']:
        text(c.get('id'),'claim id');need(c['id'] not in claimids,'duplicate claim id');claimids.add(c['id'])
        for k in ('text','estimand','population','scope'):text(c.get(k),'claim '+k)
        need(c.get('kind') in ('descriptive','comparative','mechanistic','generalization','efficiency','simulation'),'unsupported claim kind')
        seq(c.get('experiment_ids'),'claim experiment_ids');need(set(c['experiment_ids'])<=ids,'orphan claim')
        if c['kind']=='comparative':need(c.get('comparison_id') in cids,'comparative claim needs comparison_id')
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
