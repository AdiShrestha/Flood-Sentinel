"""Recompute current bytes, not stored PASS labels. Scientific scope stays explicit."""
import itertools
import ast
import re
import datetime
from collections import Counter, defaultdict
from pathlib import Path
from statistics import mean
from .io import read_json,read_csv,inside,sha,digest,inventory,merkle_root
from .metrics import binary_metrics,paired_inference,paired_group_inference,holm,number,quantile,EvidenceError
from .plan import validate,need,REVIEW_TOPICS
from .supervisor import verify_execution_record,verify_receipt_signature,validate_execution_ledger
from .contract import command_to_contract,validate_contract,contract_argv_template
from .schema import validate_training_trace,validate_split_support,validate_json_value

class Audit:
    def __init__(self,root,plan,epoch,freeze,engine_hash):
        self.root=Path(root).absolute();self.p=plan;self.epoch=epoch;self.freeze=freeze
        self.engine_hash=engine_hash;self.errors=[];self.diagnostics=[];self.computed={};self.bindings={};self.observed={};self.reports={};self.executed=[];self.receipts={};self.attempt_counts={};self.amendments=[];self.holdout_reused=False
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
        except (EvidenceError,ValueError,KeyError,TypeError,IndexError,OSError,OverflowError,AttributeError,UnicodeError) as e:self.error(name,e)
    def frozen(self):
        need(inventory(self.root,self.p['frozen_paths'])==self.freeze['files'],'frozen input changed, including added/deleted source files')
        need(sha(self.root/'project/research_plan.json')==self.freeze['plan_sha256'],'plan changed after freeze')
        need(self.engine_hash==self.freeze['engine_sha256'],'active factory code changed after freeze')
        need(merkle_root(self.freeze['files'])==self.freeze.get('snapshot_merkle_root'),'freeze inventory root mismatch')
        snapshot=self.epoch/'research_plan_snapshot.json'
        need(sha(snapshot)==self.freeze['plan_sha256'],'frozen plan snapshot changed or missing')
        self.bindings[str(snapshot.relative_to(self.root))]=sha(snapshot)
        self.bindings.update(self.freeze['files'])
        self.bindings['project/research_plan.json']=self.freeze['plan_sha256']
    def history(self):
        """Preserve amendment lineage and disclose any previously observed holdout."""
        epoch=self.freeze['epoch'];previous=None;reserved_nonces=set()
        current_groups=set(self.freeze.get('holdout_group_ids',[]))
        current_samples=set(self.freeze.get('holdout_sample_ids',[]))
        current_sources=set(self.freeze.get('holdout_source_ids',[]))
        for number in range(1,epoch+1):
            folder=inside(self.root,'project/.factory/epoch_'+str(number).zfill(4))
            f=self.j(str((folder/'freeze.json').relative_to(self.root)))
            need(isinstance(f,dict) and f.get('epoch')==number,'missing or invalid epoch lineage')
            need(f.get('previous_freeze_sha256')==previous,'prior epoch freeze changed or deleted')
            snapshot=self.file(str((folder/'research_plan_snapshot.json').relative_to(self.root)))
            need(sha(snapshot)==f['plan_sha256'],'prior epoch plan snapshot changed')
            old=read_json(snapshot);need(isinstance(old,dict),'prior plan must be an object')
            ledger=self.j(str((folder/'execution_ledger.json').relative_to(self.root)))
            verify_receipt_signature(ledger,public_key=f['supervisor_public_key'])
            nonces=validate_execution_ledger(ledger,project_id=old['project_id'],epoch=number,
                       freeze_sha256=sha(folder/'freeze.json'),run_prefix=str((folder/'runs').relative_to(self.root)),
                       experiment_ids=[experiment['id'] for experiment in old['experiments']])
            need(not reserved_nonces & nonces,'execution nonce reused across epochs')
            reserved_nonces.update(nonces)
            runs=list(folder.glob('runs/*/attempt*'))
            need({str(path.relative_to(self.root)) for path in runs}==
                 {entry['attempt_path'] for entry in ledger['attempts'].values()},'execution attempt membership differs from signed ledger')
            for entry in ledger['attempts'].values():
                if entry['execution_sha256'] is None:
                    need(number<epoch,'active execution interrupted before receipt commit; preserve evidence and amend')
                    self.diagnostic('INTERRUPTED_ATTEMPT',str(number)+': '+entry['attempt_path']+' reserved but not committed; no scientific evidence admitted')
                    continue
                record=self.file(entry['attempt_path']+'/execution.json')
                need(sha(record)==entry['execution_sha256'],'execution receipt changed/deleted or interrupted since ledger commit')
                need(read_json(record).get('run_nonce')==entry['run_nonce'],'execution nonce differs from signed reservation')
            reused=(current_groups & set(f.get('holdout_group_ids',[])) or
                    current_samples & set(f.get('holdout_sample_ids',[])) or
                    current_sources & set(f.get('holdout_source_ids',[])))
            if number<epoch and ledger['attempts'] and reused:
                self.holdout_reused=True
            if number>1:
                previous_folder=folder.parent/('epoch_'+str(number-1).zfill(4))
                need(inventory(self.root,[str(previous_folder.relative_to(self.root))],reject_dangerous_ext=False)==f.get('previous_epoch_evidence'),
                     'prior epoch evidence changed or deleted after amendment')
                predecessor=read_json(folder.parent/('epoch_'+str(number-1).zfill(4))/'research_plan_snapshot.json')
                changes=sorted(k for k in set(old)|set(predecessor) if old.get(k)!=predecessor.get(k))
                self.amendments.append({'epoch':number,'reason':f.get('amendment_reason'),
                                       'changed_plan_fields':changes,'prior_execution_observed':bool(list(
                                        (folder.parent/('epoch_'+str(number-1).zfill(4))).glob('runs/*/attempt*/execution.json')))})
            previous=sha(folder/'freeze.json')
        if self.holdout_reused:
            confirmatory=any(c.get('assertion') in ('superiority','inferiority') for c in self.p['comparisons'])
            confirmatory=confirmatory or any(c['kind']=='comparative' for c in self.p['claims'])
            need(not confirmatory,'HOLDOUT_REUSED: confirmatory comparisons require a fresh holdout after prior execution')
            self.diagnostic('HOLDOUT_REUSED','Prior epochs executed against overlapping heldout groups; conclusions remain exploratory')

    def static_scan(self):
        # Defense-in-depth scan applies to declared producer code. It is a diagnostic,
        # never a substitute for executing and recomputing outputs.
        for e in self.p['experiments']:
            if e['role'] not in ('benchmark','baseline','control','ablation','sensitivity','ood'):
                continue
            paths=[]
            for rel in e.get('code_paths',[]):
                declared=inside(self.root,rel)
                paths.extend(sorted(declared.rglob('*.py')) if declared.is_dir() else [declared])
            for p in paths:
                if p.suffix!='.py':continue
                rel=str(p.relative_to(self.root));txt=p.read_text(errors='replace')
                random_calls=re.findall(r'(?i)\b(?:rng|random|np\.random|numpy\.random)\.(?:normal|uniform|randn|random|choice)\b',txt)
                result_words=re.search(r'(?i)(?:result|metric|hypothesis|taxonomy|registry|prediction).{0,100}(?:json|csv|parquet|write_text|to_csv)',txt)
                fake_words=re.search(r'(?i)\b(?:mock|synthetic|fabricat|hardcoded substitute|fallback data)\b',txt)
                if random_calls and result_words:self.diagnostic('RNG_IN_RESULT_PRODUCER',f'{rel}: random sampling appears in a result-producing module; demonstrate training-only use')
                if fake_words and result_words:self.diagnostic('FABRICATION_LANGUAGE',f'{rel}: fabrication/mock language appears in a result-producing module')
                try: ast.parse(txt,filename=str(p))
                except SyntaxError as ex:self.error('SOURCE_SYNTAX',f'{rel}: {ex}')
    def cohort(self):
        if self.p.get('data_provenance'):
            provenance=self.j(self.p['data_provenance'])
            need(isinstance(provenance,dict),'data provenance must be an object')
            validate_json_value(provenance,'data_provenance')
            identifier=provenance.get('dataset_identifier')
            need(isinstance(identifier,str) and re.fullmatch(r'(?:https?://\S+|doi:10\.\S+)',identifier),'external dataset URL or DOI required')
            need(provenance.get('license')==self.p['license'],'dataset license differs from plan')
            need(provenance.get('provenance_basis')=='author_declared','local backend supports author_declared provenance only; external authenticity is not verified')
            try:datetime.date.fromisoformat(provenance['retrieval_date'])
            except (KeyError,TypeError,ValueError):need(False,'valid ISO retrieval_date required')
            for field,key in [('source_records_sha256','source_records'),('cohort_sha256','cohort')]:
                need(provenance.get(field)==sha(inside(self.root,self.p[key])),'data provenance digest mismatch: '+field)
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
            validate_split_support(counts,len({row['group_id'] for row in subset}),
                                   min_class_count=self.p['policy']['min_class_count'],
                                   min_test_groups=self.p['policy']['min_test_groups'] if split=='test' else 2,field=split)
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
        need([a.name for a in attempts]==[f'attempt{i:04d}' for i in range(1,len(attempts)+1)],
             eid+': execution attempt sequence missing or invalid')
        self.attempt_counts[eid]=len(attempts)
        need(len(attempts)==1,eid+': same-epoch retries are not admissible; preserve failures and amend prospectively')
        good=[]
        contract=e.get('execution_contract')
        if contract is None:contract,_=command_to_contract(e['command'],e['code_paths'])
        validate_contract(contract,self.root,e['code_paths'])
        for a in attempts:
            rel=str((a/'execution.json').relative_to(self.root));r=self.j(rel)
            need(isinstance(r,dict),eid+': execution record must be an object')
            signed=verify_execution_record(r,project_id=self.p['project_id'],epoch=self.freeze['epoch'],
                                           experiment=e,freeze=self.freeze,engine_hash=self.engine_hash)
            need(r.get('freeze_sha256')==sha(self.epoch/'freeze.json'),eid+': stale freeze binding')
            need(r.get('argv_template')==contract_argv_template(contract),eid+': executed command differs from frozen contract')
            need(r.get('execution_contract')==contract,eid+': executed contract differs from plan')
            need(r.get('dependency_lock_hash')==sha(inside(self.root,self.p['dependency_lock'])),eid+': dependency-lock binding mismatch')
            need(r.get('interpreter_hash')==r.get('runtime_attestation',{}).get('interpreter_hash'),eid+': runtime hash mismatch')
            outputs=inventory(self.root,[str(a.relative_to(self.root))],reject_dangerous_ext=False);outputs.pop(rel,None)
            need(outputs==r.get('outputs'),eid+': output hash/membership changed since execution')
            self.bindings.update(outputs);self.receipts[eid]=signed
            if r.get('exit_code')==0 and not r.get('record_error'):good.append(a)
            else:self.diagnostic('FAILED_ATTEMPT',f'{eid}: {a.name}, exit {r.get("exit_code")}; retained; no silent deletion')
        need(len(good)==1,eid+': needs exactly one successful attempt; duplicate successes are not independent evidence')
        need(good[0]==attempts[-1],eid+': latest attempt did not succeed; cannot select an earlier favorable run')
        a=good[0];r=self.j(str((a/'result.json').relative_to(self.root)))
        need(isinstance(r,dict),eid+': result must be an object')
        validate_json_value(r,'result')
        need(r.get('experiment_id')==eid and type(r.get('seed')) is int and r['seed']==e['seed'],eid+': result identity mismatch')
        need(r.get('config')==e['config'],eid+': reported runtime config differs from frozen config')
        predpath=inside(a,r['predictions']);rel=str(predpath.relative_to(self.root))
        preds=self.table(rel,{'sample_id','score'})
        data={}
        for pr in preds:
            sid=pr['sample_id'];need(sid not in data,eid+': duplicate prediction id')
            need(sid in self.coh,eid+': phantom prediction id '+sid)
            if 'label' in pr:
                need(pr['label']==self.coh[sid]['label'],eid+': prediction label disagrees with source cohort')
            pr={**pr,'label':self.coh[sid]['label']}
            number(pr['score']);data[sid]=pr
        expected={s for s,c in self.coh.items() if c['split'] in e['evaluation_splits']}
        need(set(data)==expected,eid+': missing/extra evaluation rows; do not select favorable test subsets')
        out={}
        for split in e['evaluation_splits']:
            ids=sorted(s for s in data if self.coh[s]['split']==split)
            y=[self.coh[s]['label'] for s in ids];scores=[data[s]['score'] for s in ids]
            need(min(y.count('0'),y.count('1'))>=self.p['policy']['min_class_count'],eid+': class count insufficient in '+split)
            metrics=binary_metrics(y,scores,e['threshold']);out[split]=metrics
            if 'reported_metrics' in r:
                need(isinstance(r['reported_metrics'],dict) and set(r['reported_metrics'])==set(e['evaluation_splits']),eid+': reported metric splits differ from evaluated splits')
                reported=r['reported_metrics'][split]
                need(isinstance(reported,dict) and set(reported)==set(metrics),eid+': must report all six defined metrics; AUPRC alias not accepted')
                for k,v in metrics.items():
                    need(type(reported[k]) in (int,float),eid+': reported metric must be a JSON number')
                    need(abs(number(reported[k])-v)<=self.p['policy']['metric_tolerance'],f'{eid}: {split}.{k} differs from independent recomputation ({v})')
            if len(set(scores))==1:self.diagnostic('CONSTANT_PREDICTION',eid+': '+split)
            if set(map(float,scores))<={0.,1.}:self.diagnostic('SATURATED_PREDICTION',eid+': '+split)
            if metrics['auroc']<.5:
                null_only=all(c['kind']=='descriptive' and c.get('result_interpretation')=='null_result' for c in self.p['claims'] if eid in c['experiment_ids'])
                need(null_only,eid+': '+split+' BELOW_CHANCE AUROC requires an explicit descriptive null-result claim')
                self.diagnostic('BELOW_CHANCE',eid+': '+split+' explicitly declared null result')
            if metrics['auroc']==1.:self.diagnostic('PERFECT_RANKING',eid+': '+split)
        self.training(e,r,a)
        self.computed[eid]={'metrics':out,'seed':e['seed'],'model':e['model'],'predictions_sha256':sha(predpath),'result_path':str((a/'result.json').relative_to(self.root)),
                            'receipt_verified':True,'execution_trust':'same_user_local',
                            'runtime_attestation':read_json(a/'execution.json')['runtime_attestation']}
        self.observed[eid]=data;self.reports[eid]=r
    def training(self,e,result,a):
        t=e['training'];eid=e['id']
        if t['mode']=='deterministic':
            # No invented epochs for a fixed algorithm. Semantic justification stays in review.
            p=inside(a,result['method_evidence']);self.file(str(p.relative_to(self.root)))
            return
        hist=inside(a,result['history']);rows=self.table(str(hist.relative_to(self.root)),{'epoch','train_loss','validation_loss'})
        validate_training_trace(t,rows,result.get('epochs_trained'),result.get('checkpoint_epoch'),field=eid)
        epochs=[int(row['epoch']) for row in rows]
        self.training_sufficiency(t,eid,rows,epochs)
        tr=[number(row['train_loss']) for row in rows]
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
            if c['sampling_unit']=='test_group':
                ids=sorted(s for s,row in self.coh.items() if row['split']=='test')
                labels=[self.coh[s]['label'] for s in ids]
                groups=[self.coh[s]['group_id'] for s in ids]
                scores=[([self.observed[ai][s]['score'] for s in ids],
                         [self.observed[bi][s]['score'] for s in ids]) for ai,bi in c['pairs']]
                thresholds=[(lookup[ai]['threshold'],lookup[bi]['threshold']) for ai,bi in c['pairs']]
                x=paired_group_inference(labels,scores,groups,c['metric'],thresholds=thresholds,alpha=c['alpha'],draws=c.get('inference_draws',2000))
            else:
                if c['metric'] in ('brier','log_loss'):a,b=b,a
                x=paired_inference(a,b,alpha=c['alpha'],draws=c.get('inference_draws',10000))
                x['inference_scope']='fixed_test_corpus'
            x.update({'id':c['id'],'sampling_unit':c['sampling_unit']});comp.append(x)
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
            need(r['warmup'] in ('0','1') and r['phase'] in ('train','inference'),'hardware phase/warmup invalid')
            for field in ('samples','batch_size'):
                value=number(r[field]);need(value>0 and value.is_integer(),'hardware counts must be positive integers')
            need(number(r['elapsed_sec'])>=0,'hardware elapsed time must be nonnegative')
        batch1=[number(r['duration_sec'])*1000 for r in measured if int(r['batch_size'])==1 and r['phase']=='inference']
        need(len(batch1)>=h['min_trials'],'batch-one latency trials below preregistered minimum')
        total_time=sum(number(r['duration_sec']) for r in measured if r['phase']=='inference')
        total_samples=sum(number(r['samples']) for r in measured if r['phase']=='inference')
        span=max(number(r['elapsed_sec']) for r in measured)-min(number(r['elapsed_sec']) for r in measured)
        need(span>=number(h['minimum_sustained_seconds']),'sustained measurement shorter than registered duration')
        self.hardware_results={'latency_ms':{str(q):quantile(batch1,q) for q in (.5,.9,.99)},'throughput_samples_sec':total_samples/total_time,'sustained_span_sec':span}
        if h.get('energy_claim'):
            need(all('energy_joules' in r for r in measured),'energy claim needs measured joules per trial')
            need(all(number(r['energy_joules'])>=0 for r in measured),'energy readings must be nonnegative')
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
            need({k:v for k,v in e['training'].items() if k!='rationale'}==
                 {k:v for k,v in ref_exp['training'].items() if k!='rationale'},'reproduction training policy differs')
            need(self.computed[e['id']]['runtime_attestation']==self.computed[ref]['runtime_attestation'],'reproduction runtime differs')
            a=self.observed[e['id']];b=self.observed[ref];need(set(a)==set(b),'reproduction ID mismatch')
            tol=self.p['policy']['metric_tolerance']
            need(all(abs(float(a[s]['score'])-float(b[s]['score']))<=tol for s in a),'prediction replay disagrees; report nondeterminism and preregister justified tolerance')
            reproduced.add(e['model'])
        need(needed<=reproduced,'missing fresh-process prediction replay for '+str(sorted(needed-reproduced)))
        for f in self.p['release_files']:self.file(f)
    def run(self):
        self.guard('PLAN',lambda:validate(self.root,self.p));self.guard('FREEZE',self.frozen);self.guard('HISTORY',self.history);self.guard('COHORT',self.cohort);self.guard('STATIC_SOURCE_SCAN',self.static_scan)
        if hasattr(self,'coh'):
            for e in self.p.get('experiments',[]):self.guard('RUN:'+e['id'],lambda e=e:self.experiment(e))
            self.guard('STATISTICS',self.comparisons);self.guard('DERIVED_ANALYSES',self.analyses);self.guard('HARDWARE',self.hardware);self.guard('CLAIMS',self.claims)
        payload={'schema_version':3,'status':'EVIDENCE_CHECKS_PASSED' if not self.errors else 'BLOCKED','errors':self.errors,'diagnostics':self.diagnostics,'computed_runs':self.computed,'comparisons':getattr(self,'comparison_results',[]),'derived_analyses':getattr(self,'analysis_results',{}),'hardware':getattr(self,'hardware_results',{}),'checks_executed':self.executed,'file_bindings':self.bindings,'verified_receipts':self.receipts,'attempts':self.attempt_counts,
                 'amendments':self.amendments,'holdout_reused':self.holdout_reused,
                 'test_label_isolation':'not_enforced_workspace_readable','not_automated':['source authenticity beyond observed execution and hashes','same-user signing key and verifier isolation','monotonic history under restoration of an earlier valid signed workspace state','test-label secrecy and unreported holdout access','dependency lock correspondence to imported libraries','independent reviewer identity','population representativeness and causal identification','truth of submitted training/device telemetry','theorem and operator semantics','novelty and venue suitability','unreported experiments outside this workspace','independence from colluding or mistaken agents']}
        payload['evidence_digest']=digest(payload)
        return payload

def _review_text(value,field,minimum=80):
    need(isinstance(value,str) and len(value.strip())>=minimum,field+': concrete reasoning required')
    words=re.findall(r'[a-z][a-z0-9_]+',value.lower())
    need(len(set(words))>=12,field+': repetitive or placeholder reasoning')
    need(not re.search(r'(?i)REPLACE_ME|TODO|at least 80 characters|specific objection (?:one|two|three)',value),field+': template not completed')
    return ' '.join(words)

def _review_evidence(root,audit,refs,reasoning):
    need(isinstance(refs,list) and bool(refs),'review needs artifact references')
    cited=False
    for ref in refs:
        need(isinstance(ref,dict) and isinstance(ref.get('path'),str),'invalid review evidence reference')
        path=ref['path'];f=inside(root,path)
        need(f.is_file() and sha(f)==ref.get('sha256'),'review evidence file missing or changed')
        need(path in audit['file_bindings'] or path=='project/audit_report.json','review evidence must belong to current audit')
        cited=cited or path in reasoning or Path(path).name in reasoning
    need(cited,'reasoning must cite at least one referenced evidence path or filename')

def verify_review(root,plan,audit):
    review=read_json(inside(root,'project/review.json'))
    need(isinstance(review,dict),'review must be an object')
    validate_json_value(review,'review')
    need(review.get('evidence_digest')==audit['evidence_digest'],'review stale: must bind current audit evidence_digest')
    need(review.get('reviewer_role')=='Architect','Architect owns review; no standing third role')
    need(review.get('review_mode') in ('same_session_self_review','fresh_session_review','different_model_review'),'review independence must be disclosed')
    for key in ('reviewer_model','session_id'):
        need(isinstance(review.get(key),str) and len(review[key].strip())>=3,'reviewer model/session disclosure required')
    checks=review.get('checks',[])
    need(isinstance(checks,list) and all(isinstance(c,dict) for c in checks),'review checks must be objects')
    need(len(checks)==len(REVIEW_TOPICS) and {c.get('topic') for c in checks}==REVIEW_TOPICS,'review topics missing or duplicated')
    normalized=[]
    for c in checks:
        need(c.get('verdict')=='acceptable','review has an unresolved adverse verdict')
        text=_review_text(c.get('reasoning'),c['topic']);normalized.append(text)
        _review_evidence(root,audit,c.get('evidence'),c['reasoning'])
    need(len(set(normalized))==len(normalized),'review duplicates the same reasoning across topics')
    resolutions=review.get('diagnostic_resolutions',[])
    need(isinstance(resolutions,list) and all(isinstance(x,dict) for x in resolutions),'diagnostic resolutions must be objects')
    need(len(resolutions)==len(audit['diagnostics']) and {x.get('id') for x in resolutions}=={x['id'] for x in audit['diagnostics']},'unresolved or duplicate audit diagnostics')
    for r in resolutions:
        _review_text(r.get('reasoning'),'diagnostic')
        _review_evidence(root,audit,r.get('evidence'),r['reasoning'])
    objections=review.get('objections',[])
    need(isinstance(objections,list) and len(objections)>=3,'three concrete adversarial objections required')
    for o in objections:
        need(isinstance(o,dict) and isinstance(o.get('objection'),str) and len(o['objection'].strip())>=20,'specific reviewer objection required')
        need(o.get('resolution') in ('fixed','claim_narrowed','disclosed_limitation'),'unresolved reviewer objection')
        _review_text(o.get('reasoning'),'objection')
    for field in ('limitations','venue_sources'):
        need(isinstance(review.get(field),list) and bool(review[field]) and
             all(isinstance(value,str) and len(value.strip())>=20 for value in review[field]),field+': specific entries required')
    need(any(re.search(r'https?://[^\s]+',value) for value in review['venue_sources']),'primary venue source URL required')
    need(review.get('unresolved_blockers')==[],'unresolved scientific blocker or missing blockers list')
    return review
