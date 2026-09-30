"""Recompute current bytes, not stored PASS labels. Scientific scope stays explicit."""
import itertools
import json
import ast
import re
import math
from collections import Counter, defaultdict
from pathlib import Path
from statistics import mean
from .io import read_json,read_csv,inside,sha,digest,inventory
from .metrics import binary_metrics,paired_inference,holm,number,quantile,EvidenceError
from .plan import validate,need,REVIEW_TOPICS

class Audit:
    def __init__(self,root,plan,epoch,freeze,engine_hash):
        self.root=Path(root).absolute();self.p=plan;self.epoch=epoch;self.freeze=freeze
        self.engine_hash=engine_hash;self.errors=[];self.diagnostics=[];self.computed={};self.bindings={};self.observed={};self.reports={};self.executed=[]
    def error(self,code,detail):self.errors.append({'code':code,'detail':str(detail)})
    def diagnostic(self,code,detail):
        self.diagnostics.append({'id':code+':'+digest(str(detail))[:12],'code':code,'detail':str(detail)})
    def file(self,relative):
        p=inside(self.root,relative);need(p.is_file(),'missing evidence file '+str(relative))
        self.bindings[str(relative)]=sha(p);return p
    def j(self,relative):return read_json(self.file(relative))
    def table(self,relative,cols):return read_csv(self.file(relative),cols)
    def guard(self,name,fn):
        try:fn();self.executed.append(name)
        except (EvidenceError,ValueError,KeyError,TypeError,IndexError,OSError,OverflowError) as e:self.error(name,e)
    def frozen(self):
        need(inventory(self.root,self.p['frozen_paths'])==self.freeze['files'],'frozen input changed, including added/deleted source files')
        need(sha(self.root/'project/research_plan.json')==self.freeze['plan_sha256'],'plan changed after freeze')
        need(self.engine_hash==self.freeze['engine_sha256'],'active factory code changed after freeze')
        self.bindings.update(self.freeze['files'])
        self.bindings['project/research_plan.json']=self.freeze['plan_sha256']
    def static_scan(self):
        # Defense-in-depth scan applies to declared producer code. It is a diagnostic,
        # never a substitute for executing and recomputing outputs.
        for e in self.p['experiments']:
            if e['role'] not in ('benchmark','baseline','control','ablation','sensitivity','ood'):
                continue
            for rel in e.get('code_paths',[]):
                p=inside(self.root,rel); txt=p.read_text(errors='replace')
                random_calls=re.findall(r'(?i)\b(?:rng|random|np\.random|numpy\.random)\.(?:normal|uniform|randn|random|choice)\b',txt)
                result_words=re.search(r'(?i)(?:result|metric|hypothesis|taxonomy|registry|prediction).{0,100}(?:json|csv|parquet|write_text|to_csv)',txt)
                fake_words=re.search(r'(?i)\b(?:mock|synthetic|fabricat|hardcoded substitute|fallback data)\b',txt)
                if random_calls and result_words:self.diagnostic('RNG_IN_RESULT_PRODUCER',f'{rel}: random sampling appears in a result-producing module; demonstrate training-only use')
                if fake_words and result_words:self.diagnostic('FABRICATION_LANGUAGE',f'{rel}: fabrication/mock language appears in a result-producing module')
                try: ast.parse(txt,filename=str(p))
                except SyntaxError as ex:self.error('SOURCE_SYNTAX',f'{rel}: {ex}')
    def cohort(self):
        rows=self.table(self.p['source_records'],{'record_id','origin'})
        origins={}
        for r in rows:
            need(r['record_id'] and r['record_id'] not in origins,'empty/duplicate source record_id')
            need(r['origin']==self.p['data_origin'],'source origin does not match declared population')
            origins[r['record_id']]=r['origin']
        rows=self.table(self.p['cohort'],{'sample_id','label','group_id','split','source_ids'})
        self.coh={};group_splits=defaultdict(set);source_splits=defaultdict(set);entities=defaultdict(set)
        for r in rows:
            need(r['sample_id'] and r['sample_id'] not in self.coh,'empty/duplicate sample_id')
            need(r['label'] in ('0','1'),'label must be exactly 0 or 1')
            need(bool(r['group_id']),'group_id missing')
            need(r['split'] in ('train','validation','test','ood'),'unsupported split')
            src=r['source_ids'].split('|')
            need(bool(r['source_ids']) and set(src)<=set(origins),'phantom source record or missing source IDs')
            group_splits[r['group_id']].add(r['split'])
            for s in src:source_splits[s].add(r['split'])
            for ent in filter(None,r.get('entity_ids','').split('|')):entities[ent].add(r['split'])
            self.coh[r['sample_id']]=r
        for name,items in [('group',group_splits),('source record',source_splits),('entity',entities)]:
            overlaps=[k for k,v in items.items() if len(v)>1]
            need(not overlaps,f'{name} leakage across splits: {overlaps[:8]}')
        for split in ('train','validation','test'):
            subset=[r for r in rows if r['split']==split]
            counts=Counter(r['label'] for r in subset)
            need(min(counts['0'],counts['1'])>=self.p['policy']['min_class_count'],f'{split}: absent/insufficient class support {dict(counts)}')
        ng=len({r['group_id'] for r in rows if r['split']=='test'})
        need(ng>=self.p['policy']['min_test_groups'],'test independent group count below frozen design')
        if ng<30:self.diagnostic('SMALL_GROUP_COUNT',f'{ng} distinct test groups; precision/population inference must be justified')
        if self.p.get('split_order')=='temporal':
            for r in rows:need('timestamp' in r,'temporal split needs numeric timestamp')
            train=[number(r['timestamp']) for r in rows if r['split']=='train']
            val=[number(r['timestamp']) for r in rows if r['split']=='validation']
            test=[number(r['timestamp']) for r in rows if r['split']=='test']
            need(max(train)<min(val) and max(val)<min(test),'temporal order violated; do not stratify away future/past constraints')
    def experiment(self,e):
        eid=e['id'];base=self.epoch/'runs'/eid
        attempts=sorted(base.glob('attempt*')) if base.exists() else []
        need(bool(attempts),eid+': no execution receipt')
        good=[]
        for a in attempts:
            rel=str((a/'execution.json').relative_to(self.root));r=self.j(rel)
            need(r.get('experiment_id')==eid and r.get('seed')==e['seed'],eid+': execution identity mismatch')
            need(r.get('freeze_sha256')==sha(self.epoch/'freeze.json'),eid+': stale freeze binding')
            need(r.get('inputs_before')==self.freeze['files'],eid+': pre-execution input binding mismatch')
            need(r.get('inputs_after')==self.freeze['files'],eid+': source/data changed during run')
            need(r.get('engine_sha256')==self.engine_hash,eid+': code binding mismatch')
            expected=[arg.replace('{run_dir}',str(a.resolve())).replace('{seed}',str(e['seed'])).replace('{experiment_id}',eid) for arg in e['command']]
            need(r.get('argv')==expected,eid+': executed command differs from plan')
            outputs=inventory(self.root,[str(a.relative_to(self.root))]);outputs.pop(rel,None)
            need(outputs==r.get('outputs'),eid+': output hash/membership changed since execution')
            self.bindings.update(outputs)
            if r.get('exit_code')==0 and not r.get('record_error'):good.append(a)
            else:self.diagnostic('FAILED_ATTEMPT',f'{eid}: {a.name}, exit {r.get("exit_code")}; retained; no silent deletion')
        need(len(good)==1,eid+': needs exactly one successful attempt; duplicate successes are not independent evidence')
        need(good[0]==attempts[-1],eid+': latest attempt did not succeed; cannot select an earlier favorable run')
        a=good[0];r=self.j(str((a/'result.json').relative_to(self.root)))
        need(r.get('experiment_id')==eid and r.get('seed')==e['seed'],eid+': result identity mismatch')
        need(r.get('config')==e['config'],eid+': reported runtime config differs from frozen config')
        predpath=inside(a,r['predictions']);rel=str(predpath.relative_to(self.root))
        preds=self.table(rel,{'sample_id','label','score'})
        data={}
        for pr in preds:
            sid=pr['sample_id'];need(sid not in data,eid+': duplicate prediction id')
            need(sid in self.coh,eid+': phantom prediction id '+sid)
            need(pr['label']==self.coh[sid]['label'],eid+': prediction label disagrees with source cohort')
            number(pr['score']);data[sid]=pr
        expected={s for s,c in self.coh.items() if c['split'] in e['evaluation_splits']}
        need(set(data)==expected,eid+': missing/extra evaluation rows; do not select favorable test subsets')
        out={}
        for split in e['evaluation_splits']:
            ids=sorted(s for s in data if self.coh[s]['split']==split)
            y=[self.coh[s]['label'] for s in ids];scores=[data[s]['score'] for s in ids]
            need(min(y.count('0'),y.count('1'))>=self.p['policy']['min_class_count'],eid+': class count insufficient in '+split)
            metrics=binary_metrics(y,scores,e['threshold']);out[split]=metrics
            reported=r['reported_metrics'][split]
            need(set(reported)==set(metrics),eid+': must report all six defined metrics; AUPRC alias not accepted')
            for k,v in metrics.items():need(abs(number(reported[k])-v)<=self.p['policy']['metric_tolerance'],f'{eid}: {split}.{k} differs from independent recomputation ({v})')
            if len(set(scores))==1:self.diagnostic('CONSTANT_PREDICTION',eid+': '+split)
            if set(map(float,scores))<={0.,1.}:self.diagnostic('SATURATED_PREDICTION',eid+': '+split)
            if metrics['auroc']<.5:self.diagnostic('BELOW_CHANCE',eid+': '+split)
            if metrics['auroc']==1.:self.diagnostic('PERFECT_RANKING',eid+': '+split)
        self.training(e,r,a)
        self.computed[eid]={'metrics':out,'seed':e['seed'],'model':e['model'],'predictions_sha256':sha(predpath),'result_path':str((a/'result.json').relative_to(self.root))}
        self.observed[eid]=data;self.reports[eid]=r
    def training(self,e,result,a):
        t=e['training'];eid=e['id']
        if t['mode']=='deterministic':
            # No invented epochs for a fixed algorithm. Semantic justification stays in review.
            p=inside(a,result['method_evidence']);self.file(str(p.relative_to(self.root)))
            return
        hist=inside(a,result['history']);rows=self.table(str(hist.relative_to(self.root)),{'epoch','train_loss','validation_loss'})
        epochs=[int(r['epoch']) for r in rows]
        self.training_sufficiency(t,eid,rows,epochs)
        tr=[number(r['train_loss']) for r in rows];va=[number(r['validation_loss']) for r in rows]
        need(all(x>=0 for x in tr+va),eid+': negative/nonfinite losses')
        need(result['epochs_trained']==len(rows),eid+': declared epochs differ from raw history')
        chosen=result['checkpoint_epoch'];need(type(chosen) is int and chosen in epochs,eid+': checkpoint epoch absent from history')
        if t['mode']=='early_stopping':
            best=float('inf');best_epoch=0;bad=0;stop=None
            for epoch,loss in zip(epochs,va):
                if loss<best-t['min_delta']:best=loss;best_epoch=epoch;bad=0
                else:bad+=1
                if epoch>=t['min_epochs'] and bad>=t['patience']:stop=epoch;break
            need(stop==len(rows),eid+': early-stop event not supported by validation trace; budget exhaustion is not convergence')
            need(chosen==best_epoch,eid+': selected checkpoint violates frozen validation selection')
        else:
            w=t['tail_window'];need(len(rows)==t['max_epochs'],eid+': fixed budget not completed')
            drift=abs(mean(va[-w:])-mean(va[-2*w:-w]))/max(abs(mean(va[-2*w:-w])),1e-12)
            need(drift<=t['relative_tolerance'],eid+': validation still changing at budget cap; extend prospectively')
            need(chosen==min(range(len(va)),key=lambda i:va[i])+1,eid+': fixed-budget best checkpoint mismatch')
        for key in ('checkpoint','initial_checkpoint'):
            p=inside(a,result[key]);need(self.file(str(p.relative_to(self.root))).stat().st_size>0,eid+': empty checkpoint')
        if sha(inside(a,result['checkpoint']))==sha(inside(a,result['initial_checkpoint'])):self.diagnostic('UNCHANGED_CHECKPOINT',eid)
        if tr[-1]>=tr[0]:self.diagnostic('NO_TRAIN_LOSS_IMPROVEMENT',eid)
    def training_sufficiency(self,t,eid,rows,epochs):
        """C72: preregistered convergence-budget sufficiency gate. Called from training()
        once the raw epoch history exists, so it is a real, argument-bound checkpoint
        rather than a marker invoked before there is anything to check."""
        need(epochs==list(range(1,len(rows)+1)),eid+': noncontiguous/duplicate training history')
        need(t['min_epochs']<=len(rows)<=t['max_epochs'],eid+': observed training budget violates frozen rule')
    def comparisons(self):
        comp=[];lookup={e['id']:e for e in self.p['experiments']}
        for c in self.p['comparisons']:
            a=[];b=[];seeds=[];models=set()
            for ai,bi in c['pairs']:
                need(ai in self.computed and bi in self.computed,'comparison run not validated')
                ea,eb=lookup[ai],lookup[bi]
                need(ea['seed']==eb['seed'],'paired seeds mismatch')
                need(ea['role']!='reproduction' and eb['role']!='reproduction','replay cannot count as independent evidence')
                seeds.append(ea['seed']);models.add((ea['model'],eb['model']))
                need(set(self.observed[ai])==set(self.observed[bi]),'paired evaluation IDs differ')
                a.append(self.computed[ai]['metrics']['test'][c['metric']]);b.append(self.computed[bi]['metrics']['test'][c['metric']])
            need(len(set(seeds))==len(seeds) and len(seeds)>=self.p['policy']['min_seeds'],'duplicate or missing independent seed units')
            need(len(models)==1,'cannot pool different model contrasts as independent seeds')
            # Orient effect so positive is improvement for the first method.
            if c['metric'] in ('brier','log_loss'):a,b=b,a
            x=paired_inference(a,b,alpha=c['alpha']);x.update({'id':c['id'],'sampling_unit':c['sampling_unit']});comp.append(x)
            need(x['ci'][1]-x['ci'][0]<=c['max_ci_width'],'precision target not met: '+c['id'])
            if x['degenerate_variance']:self.diagnostic('ZERO_SEED_VARIANCE',c['id'])
        ps=holm([x['p_raw'] for x in comp])
        for c,x,padj in zip(self.p['comparisons'],comp,ps):
            x['p_holm']=padj;x['multiplicity_family']='all_planned_comparisons'
            supported=padj<=c['alpha'] and x['effect']>c['minimum_effect'] and x['ci'][0]>c['minimum_effect']
            inferior=padj<=c['alpha'] and x['effect']< -c['minimum_effect'] and x['ci'][1]< -c['minimum_effect']
            if c['assertion']=='superiority':need(supported,'unsupported superiority assertion: '+c['id'])
            if c['assertion']=='inferiority':need(inferior,'unsupported inferiority assertion: '+c['id'])
            if c['assertion']=='inconclusive':need(not supported and not inferior,'inconclusive assertion contradicts registered decision rule')
            x['decision']='superiority' if supported else 'inferiority' if inferior else 'inconclusive'
        self.comparison_results=comp
    def analyses(self):
        self.analysis_results={};exps={e['id']:e for e in self.p['experiments']}
        for f in self.p['analyses'].get('failures',[]):
            eid,rows,ids=self.analyses_traceability(f,exps)
            threshold=exps[eid]['threshold'];bad=[s for s in ids if int(float(rows[s]['score'])>=threshold)!=int(rows[s]['label'])]
            self.analysis_results[f['id']]={'candidate_ids':ids,'error_ids':bad,'n':len(ids),'errors':len(bad),'error_rate':len(bad)/len(ids)}
        for f in self.p['analyses'].get('sensitivity',[]):
            ids=f['experiment_ids'];need(len(ids)>=3,'sensitivity needs at least three configurations')
            param=f['parameter'];levels=defaultdict(list);signatures=[]
            for eid in ids:
                need(eid in self.computed,'sensitivity run missing');e=exps[eid]
                value=number(e['config'][param]);levels[value].append(self.computed[eid]['metrics']['test'][f['metric']]);signatures.append(self.computed[eid]['predictions_sha256'])
            need(set(levels)==set(map(number,f['levels'])),'sensitivity grid incomplete or unexpected level')
            for level in levels:
                seeds=[exps[x]['seed'] for x in ids if number(exps[x]['config'][param])==level]
                need(len(set(seeds))==len(seeds) and len(seeds)>=self.p['policy']['min_seeds'],'sensitivity needs independent repeats per level')
            response={str(k):mean(v) for k,v in levels.items()};self.analysis_results[f['id']]={'response':response}
            if len(set(response.values()))==1:self.diagnostic('FLAT_SENSITIVITY',f['id']+': may be true invariance; investigate causal path and learning, do not force a nonflat outcome')
            if len(set(signatures))==1:self.diagnostic('IDENTICAL_PREDICTION_ARTIFACTS',f['id'])
        for f in self.p['analyses'].get('ablations',[]):
            components=f['components'];ids=f['experiment_ids'];need(bool(components),'empty component design')
            combos=defaultdict(set)
            for eid in ids:
                need(eid in self.computed,'ablation run missing')
                vals=tuple(exps[eid]['config'][c] for c in components)
                need(all(type(x) is bool for x in vals),'ablation components must be boolean')
                need(exps[eid]['seed'] not in combos[vals],'duplicate ablation seed')
                combos[vals].add(exps[eid]['seed'])
            self.analyses_ablation(components,combos,f)
            self.analysis_results[f['id']]={'cells':len(combos),'components':components,'interaction_estimation':'semantic/domain analysis required; coverage does not prove synergy'}
        if self.p.get('analysis_report'):
            reported=self.j(self.p['analysis_report'])
            need(reported==self.analysis_results,'derived analysis report differs from recomputed IDs/counts/curves')
    def analyses_traceability(self,f,exps):
        """C76: every failure-analysis denominator must trace to a verified run and the
        immutable cohort table, not to free-standing IDs. Called from analyses() before
        any error rate is computed, and its resolved IDs are what gets used downstream."""
        eid=f['experiment_id'];need(eid in self.observed,'failure analysis lacks verified run')
        col=f['condition']['column'];value=str(f['condition']['equals'])
        rows=self.observed[eid];split=f.get('split','test')
        need(all(col in self.coh[s] for s in rows),'condition column absent from immutable cohort')
        ids=sorted(s for s in rows if self.coh[s]['split']==split and self.coh[s][col]==value)
        need(bool(ids),'empty failure-analysis denominator')
        return eid,rows,ids
    def analyses_ablation(self,components,combos,f):
        """C84: full 2^N factorial coverage at or below the disclosure threshold, or a
        declared fractional design with alias structure above it; seed replication
        enforced either way. Called from analyses() after the observed cells are built."""
        if len(components)<=5:need(set(combos)==set(itertools.product((False,True),repeat=len(components))),'missing factorial cell')
        else:need(f.get('design')=='fractional' and bool(f.get('alias_structure')),'large design requires explicit alias structure and restricted interaction claims')
        need(all(len(s)>=self.p['policy']['min_seeds'] for s in combos.values()),'ablation replication incomplete')
    def hardware(self):
        h=self.p.get('hardware')
        if not h:return
        # Trial rows come from an executed experiment's already hashed output directory.
        eid=h['experiment_id'];need(eid in self.computed,'hardware run not validated')
        result=self.reports[eid];base=Path(self.computed[eid]['result_path']).parent
        rows=self.table(str(base/result['hardware_trials']),{'phase','warmup','duration_sec','samples','batch_size','elapsed_sec'})
        measured=[r for r in rows if r['warmup']=='0'];need(measured and any(r['warmup']=='1' for r in rows),'measured trials and excluded warmup needed')
        for r in rows:
            need(number(r['duration_sec'])>0 and number(r['samples'])>0,'invalid measured duration/sample count')
        batch1=[number(r['duration_sec'])*1000 for r in measured if int(r['batch_size'])==1 and r['phase']=='inference']
        need(len(batch1)>=h['min_trials'],'batch-one latency trials below preregistered minimum')
        total_time=sum(number(r['duration_sec']) for r in measured if r['phase']=='inference')
        total_samples=sum(number(r['samples']) for r in measured if r['phase']=='inference')
        span=max(number(r['elapsed_sec']) for r in measured)-min(number(r['elapsed_sec']) for r in measured)
        need(span>=number(h['minimum_sustained_seconds']),'sustained measurement shorter than registered duration')
        self.hardware_results={'latency_ms':{str(q):quantile(batch1,q) for q in (.5,.9,.99)},'throughput_samples_sec':total_samples/total_time,'sustained_span_sec':span}
        if h.get('energy_claim'):
            need(all('energy_joules' in r for r in measured),'energy claim needs measured joules per trial')
            self.hardware_results['joules_per_sample']=sum(number(r['energy_joules']) for r in measured)/sum(number(r['samples']) for r in measured)
        if h.get('memory_claim'):
            for phase in ('train','inference'):
                vals=[number(r['peak_memory_bytes']) for r in measured if r['phase']==phase]
                need(vals and min(vals)>0,'separate measured training/inference memory required')
                self.hardware_results['peak_'+phase+'_bytes']=max(vals)
        # Authenticity of device sensors, synchronization, memory scopes needs source review.
    def claims(self):
        for c in self.p['claims']:
            need(set(c['experiment_ids'])<=set(self.computed),'claim lacks validated experiments: '+c['id'])
        if any(c['kind']=='comparative' for c in self.p['claims']):
            classes={e.get('baseline_class') for e in self.p['experiments'] if e['role']=='baseline'}
            need({'trivial','historical','current','mechanism_matched'}<=classes,'comparative study lacks credible baseline classes')
        # Independent repeated execution required for at least one claimed learned model.
        replays=[e for e in self.p['experiments'] if e['role']=='reproduction']
        needed={e['model'] for e in self.p['experiments'] if e['role']=='benchmark' and e['training']['mode']!='deterministic'}
        reproduced=set()
        for e in replays:
            ref=e.get('reproduces');need(ref in self.observed and e['id'] in self.observed,'reproduction reference missing')
            need(e['seed']==self.computed[ref]['seed'],'reproduction seed mismatch')
            # v3.3.0: Reproduction identity binding — a reproduction cannot relabel
            # an easier baseline, change the model config, or use a different runtime.
            ref_exp=next((x for x in self.p['experiments'] if x['id']==ref),None)
            need(ref_exp is not None,'reproduction references unknown experiment')
            need(e['model']==ref_exp['model'],f'reproduction model identity mismatch: {e["model"]} != {ref_exp["model"]}')
            need(e['config']==ref_exp['config'],f'reproduction config differs from original; declare explicitly')
            need(e['training']['mode']==ref_exp['training']['mode'],'reproduction training mode differs')
            a=self.observed[e['id']];b=self.observed[ref];need(set(a)==set(b),'reproduction ID mismatch')
            tol=self.p['policy']['metric_tolerance']
            need(all(abs(float(a[s]['score'])-float(b[s]['score']))<=tol for s in a),'prediction replay disagrees; report nondeterminism and preregister justified tolerance')
            reproduced.add(e['model'])
        need(needed<=reproduced,'missing fresh-process prediction replay for '+str(sorted(needed-reproduced)))
        for f in self.p['release_files']:self.file(f)
    def run(self):
        self.guard('PLAN',lambda:validate(self.root,self.p));self.guard('FREEZE',self.frozen);self.guard('COHORT',self.cohort);self.guard('STATIC_SOURCE_SCAN',self.static_scan)
        if hasattr(self,'coh'):
            for e in self.p.get('experiments',[]):self.guard('RUN:'+e['id'],lambda e=e:self.experiment(e))
            self.guard('STATISTICS',self.comparisons);self.guard('DERIVED_ANALYSES',self.analyses);self.guard('HARDWARE',self.hardware);self.guard('CLAIMS',self.claims)
        payload={'schema_version':3,'status':'EVIDENCE_CHECKS_PASSED' if not self.errors else 'BLOCKED','errors':self.errors,'diagnostics':self.diagnostics,'computed_runs':self.computed,'comparisons':getattr(self,'comparison_results',[]),'derived_analyses':getattr(self,'analysis_results',{}),'hardware':getattr(self,'hardware_results',{}),'checks_executed':self.executed,'file_bindings':self.bindings,'not_automated':['source authenticity beyond observed execution and hashes','population representativeness and causal identification','truth of submitted training/device telemetry','theorem and operator semantics','novelty and venue suitability','unreported experiments outside this workspace','independence from colluding or mistaken agents']}
        payload['evidence_digest']=digest(payload)
        return payload

def verify_review(root,plan,audit):
    review=read_json(inside(root,'project/review.json'))
    need(review.get('evidence_digest')==audit['evidence_digest'],'review stale: must bind current audit evidence_digest')
    need(review.get('reviewer_role')=='Architect','Architect owns review; no standing third role')
    need(review.get('review_mode') in ('same_session_self_review','fresh_session_review','different_model_review'),'review independence must be disclosed')
    need(review.get('reviewer_model') and review.get('session_id'),'reviewer model/session disclosure required')
    checks=review.get('checks',[])
    need(len(checks)==len(REVIEW_TOPICS) and {c['topic'] for c in checks}==REVIEW_TOPICS,'review topics missing or duplicated')
    for c in checks:
        need(c.get('verdict')=='acceptable','review has an unresolved adverse verdict')
        need(len(c.get('reasoning','').strip())>=80,'review needs concrete reasoning, not an empty PASS')
        need(c.get('evidence'),'review needs actual artifact references')
        for ref in c['evidence']:
            f=inside(root,ref['path']);need(f.is_file() and sha(f)==ref['sha256'],'review evidence file missing or changed')
    resolutions=review.get('diagnostic_resolutions',[])
    need({x['id'] for x in resolutions}=={x['id'] for x in audit['diagnostics']},'unresolved audit diagnostics')
    for r in resolutions:
        need(len(r.get('reasoning',''))>=80 and r.get('evidence'),'diagnostic requires explanation and counterevidence, not a waiver')
        for ref in r['evidence']:need(sha(inside(root,ref['path']))==ref['sha256'],'diagnostic evidence changed')
    need(len(review.get('objections',[]))>=3,'three concrete adversarial objections required')
    for o in review['objections']:need(o.get('resolution') in ('fixed','claim_narrowed','disclosed_limitation') and len(o.get('reasoning',''))>=80,'unresolved reviewer objection')
    need(review.get('limitations') and review.get('venue_sources'),'specific limitations and verified venue sources required')
    need(not review.get('unresolved_blockers'),'unresolved scientific blocker')
    return review
