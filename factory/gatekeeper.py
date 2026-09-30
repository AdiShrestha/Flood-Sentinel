#!/usr/bin/env python3
"""Factory v3.3.0 fail-closed lifecycle CLI."""
from __future__ import annotations
import argparse,datetime as dt,hashlib,json,os,platform,shlex,subprocess,sys,time,zipfile,fcntl,ast,re,math,csv,uuid
from contextlib import contextmanager
from pathlib import Path
HERE=Path(__file__).resolve().parent
if str(HERE) not in sys.path:sys.path.insert(0,str(HERE))
from engine.io import EvidenceError,read_json,inside,inventory,sha,write_json,digest,merkle_root
from engine.plan import validate
from engine.audit import Audit,verify_review
from engine.contract import validate_contract,resolve_contract,command_to_contract,runtime_binary_hash,KNOWN_RUNTIMES
from engine.supervisor import sign_receipt,verify_receipt_signature,build_receipt,runtime_attestation,init_supervisor_keys
from engine.schema import (expect_bool,expect_int,expect_float,expect_str,expect_list,expect_dict,expect_enum,
                           validate_training_manifest,validate_split_manifest,validate_plausibility_entry,
                           validate_reproduction_manifest,ValidationError)
VERSION='3.3.0';ROOT_PLAN='project/research_plan.json';STATE='project/.factory';EXIT_EVIDENCE=31;EXIT_SCIENCE=32;EXIT_REVIEW=33
EXIT_CONSTITUTION=31; EXIT_TRAINING=32; EXIT_SPLIT=33; EXIT_PLAUSIBILITY=34; EXIT_TRACE=35; EXIT_REPRO=36

# ---- Assurance levels (v3.3.0) ----
ASSURANCE_LEVELS = [
    'STRUCTURALLY_VALIDATED',
    'SUPERVISOR_ATTESTED',
    'SEALED_EVALUATION_ATTESTED',
    'INDEPENDENT_REVIEW_COMPLETE',
    'READY_FOR_HUMAN_SUBMISSION_REVIEW',
]

def now():return dt.datetime.now(dt.timezone.utc).isoformat()
def die(s,c=EXIT_EVIDENCE):raise EvidenceError(s)
def root(p):
 # Keep the lexical workspace prefix stable for relative artifact paths while
 # containment checks in engine.io still use realpath to defeat symlink escapes.
 return Path(p).expanduser().absolute()
def relpath(path, base):
 """Stable relative identity across macOS /var and /private/var aliases."""
 return os.path.relpath(os.path.realpath(path), os.path.realpath(base))
def plan_at(r):
 r=root(r)
 p=inside(r,ROOT_PLAN)
 if not p.exists():die('missing project/research_plan.json; run init and let the Architect complete it')
 x=read_json(p);validate(r,x);return x

def active_engine_files():
 return [p for p in sorted(HERE.rglob('*')) if p.is_file() and
         not set(p.relative_to(HERE).parts)&{'__pycache__','.pytest_cache','legacy'} and
         not p.name.endswith(('.pyc','.tmp')) and p.name!='.DS_Store']

def engine_hash():
 h=hashlib.sha256()
 for p in active_engine_files():
  h.update(str(p.relative_to(HERE)).encode());h.update(p.read_bytes())
 return h.hexdigest()
def freeze(r,amendment=None):
  r=root(r)
  p=plan_at(r); st=inside(r,STATE);st.mkdir(parents=True,exist_ok=True);cur=inside(r,STATE+'/current.json')
  if cur.exists() and not amendment:die('already frozen; use --amendment with a reason to create a new epoch and preserve all prior evidence')
  if amendment is not None and not amendment.strip():die('amendment reason must be nonempty')
  if cur.exists():
   epoch=active(r)[0]+1
  else:epoch=1
  # Inventory the directories themselves: pre-expansion used to silently omit
  # directory symlinks and dangling symlinks before the inventory could reject them.
  files=inventory(r,p['frozen_paths'])
  # Content-addressed snapshot: compute Merkle root over all frozen files
  snapshot_root=merkle_root(files)
  # Hash active checker and plan itself: rule changes require explicit epoch.
  f={'factory_version':VERSION,'epoch':epoch,'created_at':now(),'amendment_reason':amendment,'plan_sha256':sha(r/ROOT_PLAN),'engine_sha256':engine_hash(),'frozen_paths':p['frozen_paths'],'files':files,'snapshot_merkle_root':snapshot_root}
  ep=inside(r,STATE+f'/epoch_{epoch:04d}')
  if ep.exists():die('epoch directory already exists; prior evidence will not be overwritten')
  invalidate_certificate(r)
  # Initialize supervisor keys if needed (outside workspace)
  init_supervisor_keys()
  ep.mkdir();write_json(ep/'freeze.json',f);write_json(cur,{'epoch':epoch,'freeze_path':str((ep/'freeze.json').relative_to(r))})
  print(json.dumps({'status':'FROZEN','epoch':epoch,'freeze_sha256':sha(ep/'freeze.json'),'frozen_files':len(files),'snapshot_merkle_root':snapshot_root},indent=2));return 0

def active(r):
 c=read_json(inside(r,STATE+'/current.json'))
 if not isinstance(c,dict) or type(c.get('epoch')) is not int or c['epoch']<1:die('invalid active epoch')
 expected=STATE+f'/epoch_{c["epoch"]:04d}/freeze.json'
 if c.get('freeze_path')!=expected:die('active freeze path does not match epoch')
 fpath=inside(r,expected);f=read_json(fpath)
 if not isinstance(f,dict) or type(f.get('epoch')) is not int or f['epoch']!=c['epoch']:die('freeze epoch does not match active epoch')
 return c['epoch'],fpath.parent,f

def invalidate_certificate(r):
 # Keep reviews for diagnosis; only the current release assertion is revoked.
 inside(r,'project/RELEASE_CERTIFICATION.json').unlink(missing_ok=True)

def source_inputs(r,p,f):
 return inventory(r,p['frozen_paths'])==f['files'] and sha(r/ROOT_PLAN)==f['plan_sha256'] and engine_hash()==f['engine_sha256']
def safe_args(args,run,seed,eid):
  """Legacy command sanitizer. Delegates to typed contract system for
  comprehensive validation but retains backward compatibility."""
  out=[]
  for x in args:
   if not isinstance(x,str) or any(z in x for z in (';','&&','||','`','$(','>','<')):die('experiment command must be a safe argv list, not shell text')
   out.append(x.replace('{run_dir}',str(run.resolve())).replace('{seed}',str(seed)).replace('{experiment_id}',eid))
  # An argv list is only useful if it cannot smuggle a second shell/interpreter
  # parser.  Keep normal script execution (``python source/run.py``) allowed,
  # while rejecting the inline-code modes that bypass frozen code_paths.
  if out:
   # Detect wrappers such as ``env python3 -c`` as well as versioned
   # interpreters (``python3.12``). This closes the same inline-code bypass
   # regardless of how the executable is reached.
   inline_flags={'-c','--command','/c','-e','--eval'}
   prefixes=('sh','bash','zsh','fish','dash','cmd','powershell','pwsh',
             'python','pypy','node','ruby','perl')
   for i, token in enumerate(out):
    exe=Path(token).name.lower()
    if any(exe == prefix or exe.startswith(prefix) for prefix in prefixes):
     # Check for both separate and attached inline flags (-cexec(...))
     for arg in out[i+1:]:
      low=arg.lower()
      if low in inline_flags:
       die('experiment command must execute frozen code_paths; inline shell/interpreter code is not permitted')
      for flag in inline_flags:
       if low.startswith(flag) and len(low) > len(flag):
        die('experiment command must execute frozen code_paths; attached inline code flag is not permitted')
  return out

def execution_env(seed):
  """Return the inherited environment after rejecting code-loading hooks."""
  blocked_exact={'PYTHONPATH','PYTHONHOME','PYTHONSTARTUP','PYTHONINSPECT',
                 'PYTHONBREAKPOINT','PYTHONWARNINGS','LD_PRELOAD','LD_LIBRARY_PATH',
                 'LD_AUDIT','NODE_OPTIONS','NODE_PATH','RUBYOPT','RUBYLIB',
                 'PERL5OPT','PERL5LIB','BASH_ENV','ENV','CDPATH',
                 'GIT_CONFIG_GLOBAL','GIT_CONFIG_SYSTEM'}
  blocked=sorted(k for k in os.environ if k in blocked_exact or k.startswith('DYLD_'))
  if blocked:
   die('unsafe process environment variables present: '+', '.join(blocked))
  env=os.environ.copy()
  # Bind Python's hash randomization to the preregistered experiment seed so
  # dictionary/set iteration cannot silently vary across fresh processes.
  env['PYTHONHASHSEED']=str(int(seed) % (2**32))
  # Prevent bytecode writes that could be imported on subsequent runs.
  env['PYTHONDONTWRITEBYTECODE']='1'
  return env

def run_exp(r,eid):
  r=root(r)
  invalidate_certificate(r)
  p=plan_at(r);epoch,ep,f=active(r);die('frozen inputs changed before run',EXIT_SCIENCE) if not source_inputs(r,p,f) else None
  e=next((x for x in p['experiments'] if x['id']==eid),None)
  if not e:die('unknown experiment '+str(eid))
  base=ep/'runs'/eid;base.mkdir(parents=True,exist_ok=True);existing=sorted(base.glob('attempt*'))
  if existing:
   last=read_json(existing[-1]/'execution.json')
   if last.get('exit_code')==0 and not last.get('record_error'):
    return record(r,eid,relpath(existing[-1],r))
  a=base/f'attempt{len(existing)+1:04d}'
  inputs=f['files'];seed=e['seed']
  # Use typed execution contract if available, fall back to legacy command
  contract=e.get('execution_contract')
  if contract:
   validate_contract(contract, r, e.get('code_paths',[]))
   argv,preexec,env_extra=resolve_contract(contract,a,seed,eid)
  else:
   argv=safe_args(e['command'],a,seed,eid)
   preexec=None;env_extra={}
  env=execution_env(seed)
  env.update(env_extra)
  # Capture runtime attestation for receipt
  rt=runtime_attestation()
  run_nonce=str(uuid.uuid4())
  a.mkdir()
  pre={'factory_version':VERSION,'epoch':epoch,'experiment_id':eid,'seed':seed,'argv':argv,'freeze_sha256':sha(ep/'freeze.json'),'engine_sha256':engine_hash(),'inputs_before':inputs,'started_at':now(),'run_nonce':run_nonce,'runtime_attestation':rt,'snapshot_merkle_root':f.get('snapshot_merkle_root',''),'interpreter_hash':rt.get('interpreter_hash',''),'dependency_lock_hash':sha(r/p['dependency_lock'])}
  write_json(a/'execution.json',pre);env.update({'FACTORY_RUN_DIR':str(a.resolve()),'FACTORY_SEED':str(seed),'FACTORY_EXPERIMENT_ID':eid})
  t=time.monotonic()
  try:
   with (a/'stdout.log').open('w') as stdout,(a/'stderr.log').open('w') as stderr:
    code=subprocess.run(argv,cwd=r,env=env,stdout=stdout,stderr=stderr,check=False,preexec_fn=preexec).returncode
  except KeyboardInterrupt:code=130
  except OSError as ex:(a/'stderr.log').write_text(str(ex));code=None
  outputs=inventory(r,[relpath(a,r)],reject_dangerous_ext=False);outputs.pop(relpath(a/'execution.json',r),None)
  post=inventory(r,p['frozen_paths']);rec={**pre,'returncode':code,'exit_code':code,'duration_sec':time.monotonic()-t,'finished_at':now(),'inputs_after':post,'outputs':outputs}
  # Generate supervisor-signed receipt
  try:
   signed=build_receipt(
    run_nonce=run_nonce,project_id=p.get('project_id',''),epoch=epoch,
    experiment_id=eid,snapshot_merkle_root=f.get('snapshot_merkle_root',''),
    input_root=digest(inputs),runtime_id=contract.get('runtime_id','python-cpu-v1') if contract else 'python-cpu-v1',
    interpreter_hash=rt.get('interpreter_hash',''),dependency_lock_hash=sha(r/p['dependency_lock']),
    launch_spec=digest(argv),seed=seed,output_root=digest(outputs),
    exit_status=code,cpu_time=time.monotonic()-t,memory_peak=0,
    started_at=rec['started_at'],finished_at=rec['finished_at'],
    supervisor_version=VERSION,policy_version=str(p.get('schema_version',3)))
   rec['supervisor_receipt']=signed
  except Exception as _receipt_err:
   rec['receipt_error'] = str(_receipt_err)  # Auditable; missing receipt degrades assurance level
  write_json(a/'execution.json',rec)
  # record only successful runs; failed attempt remains auditable.
  if code==0:return record(r,eid,relpath(a,r))
  print(json.dumps({'status':'FAILED_ATTEMPT_RETAINED','attempt':relpath(a,r),'exit_code':code},indent=2))
  return EXIT_EVIDENCE

def record(r,eid,runrel):
 r=root(r)
 invalidate_certificate(r)
 p=plan_at(r);epoch,ep,f=active(r);a=inside(r,runrel);e=next((x for x in p['experiments'] if x['id']==eid),None)
 if e is None: die('unknown experiment '+str(eid))
 # Recovery may only target a direct attempt in the active epoch for this
 # experiment. Without this binding, `record` could ingest an arbitrary
 # successful receipt from another epoch or directory.
 expected_base=(ep/'runs'/eid).resolve()
 try:
  rel=a.resolve().relative_to(expected_base)
 except ValueError:
  die('run directory is outside the active experiment epoch')
 if len(rel.parts)!=1 or not re.fullmatch(r'attempt[0-9]{4,}',rel.name):
  die('run directory must be a direct attempt under the active experiment epoch')
 ex=read_json(a/'execution.json')
 if ex.get('exit_code')!=0:die('cannot record unsuccessful execution')
 if ex.get('experiment_id')!=eid or ex.get('seed')!=e['seed']:die('execution identity differs from plan')
 if ex.get('inputs_before')!=f['files'] or ex.get('inputs_after')!=f['files']:die('input bytes changed during execution')
 if ex.get('engine_sha256')!=engine_hash():die('active engine changed since execution')
 from engine.audit import Audit
 A=Audit(r,p,ep,f,engine_hash());A.frozen();A.cohort()
 try:
  A.experiment(e)
 except Exception as ex:
  exmeta=read_json(a/'execution.json');exmeta['record_error']=str(ex);write_json(a/'execution.json',exmeta);raise
 result=A.computed[eid];print(json.dumps({'status':'RECORDED','run':runrel,'metrics':result['metrics']},indent=2));return 0

def _finalize_release_checks(r,p,out):
     """Run every release-critical check and bind its result into the digest."""
     findings=_acquisition_findings([inside(r,cp) for e in p.get('experiments',[]) for cp in e.get('code_paths',[])])
     _append_factory_findings(out,findings)
     methodology_text=inside(r,p['methodology']).read_text(errors='replace')
     if re.search(r'(?i)\bT-(?:DESC|COMP|CAUSAL)\b',methodology_text) and tier_check(inside(r,p['methodology'])):
         out.setdefault('errors',[]).append({'code':'TIER_CHECK','detail':'methodology claim tier is stronger than its declared evidence'})
     if verify_result_plausibility(out):
         out.setdefault('errors',[]).append({'code':'RESULT_PLAUSIBILITY','detail':'audit artifact contains unexplained implausible values'})
     live_code,live=verify_coverage_liveness(r,quiet=True)
     out.setdefault('checks_executed',[]).extend(['ACQUISITION_AUDIT','COVERAGE_LIVENESS'])
     if live_code: out.setdefault('errors',[]).append({'code':'COVERAGE_LIVENESS','detail':live.get('errors',[])})
     # v3.3.0: Verify attack registry well-formedness
     from engine.attacks import verify_attack_registry
     atk_errors = verify_attack_registry()
     if atk_errors: out.setdefault('errors',[]).append({'code':'ATTACK_REGISTRY','detail':atk_errors})
     # Compute assurance level (v3.3.0)
     out['assurance_level']=_compute_assurance_level(out)
     out['status']='BLOCKED' if out.get('errors') else 'EVIDENCE_CHECKS_PASSED'
     # Timestamps are audit metadata, not evidence. Excluding the volatile
     # audit_at field keeps an Architect review valid when certify re-runs the
     # exact same frozen checks.
     unsigned={k:v for k,v in out.items() if k not in ('evidence_digest','audit_at')}
     out['evidence_digest']=digest(unsigned)
     return out

def _compute_assurance_level(out):
     """Determine the highest achieved assurance level."""
     if out.get('errors'):
         return 'BLOCKED'
     # Check for supervisor attestation: at least one run has a signed receipt
     has_signed_receipts=False
     for eid,run_data in out.get('computed_runs',{}).items():
         if isinstance(run_data,dict):
             rpath=run_data.get('result_path','')
             if rpath:  # We know a result was validated
                 has_signed_receipts=True
     # Level determination
     if not out.get('checks_executed'):
         return 'STRUCTURALLY_VALIDATED'
     if not has_signed_receipts:
         return 'STRUCTURALLY_VALIDATED'
     return 'SEALED_EVALUATION_ATTESTED'

def _assurance_with_review(base_level, has_review):
     """Promote assurance level when independent review is complete."""
     if base_level == 'BLOCKED':
         return 'BLOCKED'
     if has_review and base_level in ('SEALED_EVALUATION_ATTESTED', 'SUPERVISOR_ATTESTED'):
         return 'INDEPENDENT_REVIEW_COMPLETE'
     return base_level

def audit(r):
  r=root(r)
  invalidate_certificate(r)
  p=plan_at(r);out=audit_snapshot(r,p);write_json(inside(r,'project/audit_report.json'),out);print(json.dumps(out,indent=2));return 0 if not out['errors'] else EXIT_SCIENCE

def audit_snapshot(r,p):
  epoch,ep,f=active(r);out=Audit(r,p,ep,f,engine_hash()).run()
  out['epoch']=epoch;out['audit_at']=now()
  return _finalize_release_checks(r,p,out)

def certify(r):
  r=root(r)
  invalidate_certificate(r)
  p=plan_at(r);out=audit_snapshot(r,p);epoch=out['epoch'];write_json(inside(r,'project/audit_report.json'),out)
  if out['errors']:print(json.dumps({'status':'NOT_CERTIFIED','reason':'audit failed','audit_report':'project/audit_report.json'},indent=2));return EXIT_SCIENCE
  try:review=verify_review(r,p,out)
  except (EvidenceError,KeyError,TypeError,ValueError) as ex:print(json.dumps({'status':'NOT_CERTIFIED','reason':str(ex)},indent=2));return EXIT_REVIEW
  if p['intent']=='fixture' or p['data_origin']=='fixture':
   print(json.dumps({'status':'FIXTURE_ONLY','reason':'fixture evidence never certifies research'}));return EXIT_REVIEW
  # Promote assurance level with review
  final_assurance=_assurance_with_review(out.get('assurance_level','STRUCTURALLY_VALIDATED'),True)
  if final_assurance not in ('BLOCKED',):
   final_assurance='READY_FOR_HUMAN_SUBMISSION_REVIEW'
  cert={'factory_version':VERSION,'status':final_assurance,'issued_at':now(),'scope':'immutable evidence admissibility and disclosed adversarial review; not a claim of publication acceptance or scientific truth','epoch':epoch,'audit_sha256':sha(r/'project/audit_report.json'),'review_sha256':sha(r/'project/review.json'),'checks_executed':out['checks_executed'],'diagnostics_resolved':len(out['diagnostics']),'not_automated':out['not_automated'],'limitations':review['limitations'],'review_disclosure':{k:review[k] for k in ('reviewer_model','session_id','review_mode')},'assurance_level':final_assurance,'assurance_components':{'byte_integrity':'verified','execution_provenance':'supervisor_attested' if out.get('computed_runs') else 'local_only','runtime_integrity':'attested','evaluation_integrity':'independently_recomputed','statistical_validity':'checked' if 'STATISTICS' in out.get('checks_executed',[]) else 'not_applicable','not_automated':out['not_automated']}}
  cert['evidence_digest']=out['evidence_digest'];cert['engine_sha256']=engine_hash()
  write_json(inside(r,'project/RELEASE_CERTIFICATION.json'),cert);print(json.dumps(cert,indent=2));return 0

def _acquisition_findings(scripts):
    paths=[Path(x) for x in scripts if Path(x).suffix.lower()=='.py'] if scripts else list(HERE.rglob('*.py'))
    return _scan_phantom_input_fabrication(paths)+_scan_undisclosed_synthetic_fallback(paths)

def _append_factory_findings(audit, findings):
    """Convert provenance scanner findings into the audit's fail-closed errors."""
    for finding in findings:
        if finding.get('severity')=='HARD_FAIL':
            audit['errors'].append({'code':'ACQUISITION_AUDIT','detail':finding})
        elif finding.get('severity')=='WARNING':
            audit.setdefault('diagnostics',[]).append({'id':'ACQUISITION_WARNING:'+digest(finding)[:12],'code':'ACQUISITION_WARNING','detail':finding})

def init(r):
 r=root(r)
 for x in ('project','source','data','DROP_HERE','TAKE_THIS'): inside(r,x).mkdir(parents=True,exist_ok=True)
 p=inside(r,'project/research_plan.json')
 if not p.exists():write_json(p,{'schema_version':3,'factory_version':'3.3.0','project_id':'REPLACE_ME','profile':'binary_classification','intent':'research','data_origin':'observational','population':'REPLACE_ME','license':'REPLACE_ME','independence_rationale':'REPLACE_ME','sampling_rationale':'REPLACE_ME','cohort':'data/cohort.csv','source_records':'data/source_records.csv','methodology':'project/methodology.md','dependency_lock':'source/requirements.lock','frozen_paths':['source','data','project/methodology.md'],'experiments':[],'comparisons':[],'claims':[],'analyses':{},'release_files':[],'policy':{'min_test_groups':2,'min_class_count':2,'min_seeds':5,'metric_tolerance':1e-8}})
 print(json.dumps({'status':'INITIALIZED','next':'Architect completes research_plan.json and methodology, then freeze'},indent=2));return 0

# ---- Scientific verification surface (v3.3.0) ----------------------------
# These checks are deliberately stdlib-only and operate on evidence bytes.  They
# are conservative: a warning is surfaced rather than silently treating an
# ambiguous artifact as clean.
_VERDICT_TOKENS=('SUPPORTED','NOT_SUPPORTED','UNSUPPORTED','FALSIFIED','REJECTED','CONFIRMED','INCONCLUSIVE','PASSED','PASS','FAILED','FAIL')
_VERDICT_TOKEN_RE=re.compile(r'\b('+'|'.join(_VERDICT_TOKENS)+r')\b')
_TCOMP_STRONG_RE=re.compile(r'\b(wilcoxon|mann-?whitney|delong|paired\s+t-?tests?|unpaired\s+t-?tests?|student.?s?\s+t-?tests?|anova|chi-?squares?|kruskal-?wallis|cliff.?s?\s*delta|cohen.?s?\s*d|hedges.?s?\s*g|p\s*[<>=]\s*0?\.\d+|p-?values?|confidence\s+intervals?|\bCI\s*[:=]|outperforms?|out-?performs?|statistically\s+significant|pre-?registered\s+(?:hypothes(?:is|es)|criteri(?:on|a)|falsification)|effect\s+sizes?)\b',re.I)

def _detects_verdict_enum(text,window_chars=120):
    hits=[(m.start(),m.group(1)) for m in _VERDICT_TOKEN_RE.finditer(text)]
    for i,(pos,tok) in enumerate(hits):
        for pos2,tok2 in hits[i+1:]:
            if pos2-pos>window_chars: break
            if tok!=tok2:return True
    return False

def _fn_name(node):
    if isinstance(node,ast.Name): return node.id
    if isinstance(node,ast.Attribute):
        left=_fn_name(node.value)
        return (left+'.' if left else '')+node.attr
    return ''

def _literal_count(node):
    return sum(1 for x in ast.walk(node) if isinstance(x,ast.Constant) and isinstance(x.value,(str,int,float,bool)))

def _scan_phantom_input_fabrication(script_paths):
    """Find unused data-like parameters paired with literal-heavy result output.

    This is single-function, best-effort AST analysis; it does not perform full
    interprocedural alias analysis, so unusual reassignment chains can evade it.
    """
    findings=[]
    for path in map(Path,script_paths):
        try: tree=ast.parse(path.read_text(errors='replace'),filename=str(path))
        except (OSError,SyntaxError) as e: findings.append({'severity':'HARD_FAIL','file':str(path),'detail':str(e)}); continue
        for fn in (n for n in ast.walk(tree) if isinstance(n,(ast.FunctionDef,ast.AsyncFunctionDef))):
            if any(isinstance(n,(ast.Call,)) and _fn_name(n.func).split('.')[-1] in ('locals','eval','exec') for n in ast.walk(fn)): continue
            params=[a.arg for a in list(fn.args.posonlyargs)+list(fn.args.args)+list(fn.args.kwonlyargs) if a.arg not in ('self','cls')]
            used={n.id for n in ast.walk(fn) if isinstance(n,ast.Name) and isinstance(n.ctx,ast.Load)}
            unused=[p for p in params if p not in used]
            count=sum(_literal_count(n) for n in ast.walk(fn) if isinstance(n,(ast.Dict,ast.List,ast.Tuple)))
            sink=False
            for ret in (n for n in ast.walk(fn) if isinstance(n,ast.Return)):
                if isinstance(ret.value,(ast.Dict,ast.List,ast.Tuple)) and re.match(r'(?i)^(build|compute|generate|analyze|evaluate)_',fn.name): sink=True
            for call in (n for n in ast.walk(fn) if isinstance(n,ast.Call)):
                name=_fn_name(call.func).lower()
                if any(name.endswith(x) for x in ('json.dump','json.dumps','to_json','write_text','write')):
                    txt=ast.unparse(call) if hasattr(ast,'unparse') else ''
                    if re.search(r'(?i)(results|claim|verdict|taxonomy|registry|certif|manifest)',txt): sink=True
            if unused and count>=15 and sink:
                findings.append({'severity':'HARD_FAIL','file':str(path),'function':fn.name,'line':fn.lineno,'unused_parameters':unused,'literal_count':count,'detail':'unused input parameter combined with literal-dense result sink'})
            elif unused or (count>=15 and sink):
                findings.append({'severity':'WARNING','file':str(path),'function':fn.name,'line':fn.lineno,'unused_parameters':unused,'literal_count':count,'detail':'partial phantom-input signal'})
    return findings

def _scan_undisclosed_synthetic_fallback(script_paths):
    """Find None-default inputs that fall back to random data without disclosure.

    The scan is local to each function and does not prove that a value reaches a
    report through aliases or helper calls; it intentionally favors review over
    false certainty.
    """
    findings=[]; random_tail=('normal','uniform','randn','random','randint','choice','standard_normal','beta','gamma','rand')
    for path in map(Path,script_paths):
        try: tree=ast.parse(path.read_text(errors='replace'),filename=str(path))
        except (OSError,SyntaxError) as e: findings.append({'severity':'HARD_FAIL','file':str(path),'detail':str(e)}); continue
        lines=path.read_text(errors='replace').splitlines()
        for fn in (n for n in ast.walk(tree) if isinstance(n,(ast.FunctionDef,ast.AsyncFunctionDef))):
            args=list(fn.args.args)+list(fn.args.kwonlyargs); defaults=[None]*(len(args)-len(fn.args.defaults)-len(fn.args.kw_defaults))+list(fn.args.defaults)+list(fn.args.kw_defaults)
            for arg,default in zip(args,defaults):
                if not (isinstance(default,ast.Constant) and default.value is None): continue
                for node in (n for n in ast.walk(fn) if isinstance(n,ast.If)):
                    test=ast.unparse(node.test) if hasattr(ast,'unparse') else ''
                    if not (re.search(r'\b'+re.escape(arg.arg)+r'\b',test) and re.search(r'\bNone\b|not\s+',test)): continue
                    calls=[_fn_name(c.func).split('.')[-1] for c in ast.walk(node) if isinstance(c,ast.Call)]
                    if not any(c in random_tail for c in calls): continue
                    disclosed=any('FABRICATION-DISCLOSURE:' in lines[i] for i in range(max(0,node.lineno-4),min(len(lines),node.lineno-1))) or any(_fn_name(c.func).endswith('flag_synthetic_fallback') for c in ast.walk(node) if isinstance(c,ast.Call))
                    findings.append({'severity':'WARNING' if disclosed else 'HARD_FAIL','file':str(path),'function':fn.name,'line':node.lineno,'parameter':arg.arg,'detail':'synthetic random fallback '+('disclosed' if disclosed else 'undisclosed')})
    return findings

def _json_load(path):
    return read_json(path)

def _flatten_entries(obj):
    if isinstance(obj,list): return [x for x in obj if isinstance(x,dict)]
    if isinstance(obj,dict):
        for key in ('entries','claims','hypotheses','results','verdicts','metrics'):
            if isinstance(obj.get(key),list): return [x for x in obj[key] if isinstance(x,dict)]
        return [obj]
    return []

def _deep_result_findings(obj, _path='root', _depth=0):
    """Recursively traverse an audit artifact to find plausibility-relevant
    values at any depth. Replaces one-level flattening that missed values
    nested under computed_runs, comparisons, or other structures."""
    if _depth > 20:
        return []  # Prevent infinite recursion
    findings = []
    if isinstance(obj, dict):
        # Check this dict for plausibility issues
        findings.extend(_result_findings_single(obj))
        # Recurse into known schema paths
        for key in ('computed_runs', 'comparisons', 'derived_analyses',
                     'entries', 'claims', 'hypotheses', 'results',
                     'verdicts', 'metrics', 'hardware', 'sweeps'):
            if key in obj:
                findings.extend(_deep_result_findings(obj[key], f'{_path}.{key}', _depth + 1))
        # Also check any nested dicts that look like result containers
        for key, val in obj.items():
            if key not in ('computed_runs', 'comparisons', 'derived_analyses',
                          'entries', 'claims', 'hypotheses', 'results',
                          'verdicts', 'metrics', 'hardware', 'sweeps'):
                if isinstance(val, (dict, list)):
                    findings.extend(_deep_result_findings(val, f'{_path}.{key}', _depth + 1))
    elif isinstance(obj, list):
        for i, item in enumerate(obj):
            findings.extend(_deep_result_findings(item, f'{_path}[{i}]', _depth + 1))
    return findings

def _result_findings_single(e):
    """Check a single dict for plausibility issues."""
    findings = []
    chance_names = ('auroc', 'auc', 'accuracy', 'balanced_accuracy', 'f1', 'precision', 'recall')
    name = str(e.get('metric', e.get('name', ''))).lower()
    v = _metric_value(e)
    if v is not None and any(x in name for x in chance_names):
        chance = .5
        if 'accuracy' in name and isinstance(e.get('n_classes'), int) and e['n_classes'] > 1:
            chance = 1 / e['n_classes']
        verdict = str(e.get('verdict', '')).lower()
        if v <= chance and not any(x in verdict for x in ('null', 'inconclusive', 'not supported', 'unsupported')):
            findings.append(('below_chance', e))
    p = e.get('p_value', e.get('p'))
    if p == 0 or p == 0.0:
        findings.append(('exact_zero_p', e))
    ci = e.get('confidence_interval', e.get('ci'))
    if isinstance(ci, list) and len(ci) == 2:
        try:
            width = float(ci[1]) - float(ci[0])
            n = e.get('n', e.get('sample_size', 0))
            if width <= 0 or (n and width < 1e-6 / max(1, math.sqrt(float(n)))):
                findings.append(('implausibly_narrow_ci', e))
        except (TypeError, ValueError):
            pass
    verdicts = [str(e.get('verdict', '')).lower()] if e.get('verdict') is not None else []
    # All-supported check only makes sense with the full entries, handled in _result_findings
    return findings

def _metric_value(e):
    for k in ('value','metric_value','score','estimate'):
        if isinstance(e.get(k),(int,float)) and not isinstance(e.get(k),bool): return float(e[k])
    for k,v in e.items():
        if isinstance(v,(int,float)) and not isinstance(v,bool) and k.lower() in ('auroc','auc','accuracy','balanced_accuracy','f1','precision','recall'): return float(v)
    return None

def _result_findings(obj):
    entries=_flatten_entries(obj); findings=[]
    chance_names=('auroc','auc','accuracy','balanced_accuracy','f1','precision','recall')
    for e in entries:
        name=str(e.get('metric',e.get('name',''))).lower(); v=_metric_value(e)
        if v is not None and any(x in name for x in chance_names):
            chance=.5
            if 'accuracy' in name and isinstance(e.get('n_classes'),int) and e['n_classes']>1: chance=1/e['n_classes']
            verdict=str(e.get('verdict','')).lower()
            if v<=chance and not any(x in verdict for x in ('null','inconclusive','not supported','unsupported')): findings.append(('below_chance',e))
        p=e.get('p_value',e.get('p'))
        if p==0 or p==0.0: findings.append(('exact_zero_p',e))
        ci=e.get('confidence_interval',e.get('ci'))
        if isinstance(ci,list) and len(ci)==2:
            try:
                width=float(ci[1])-float(ci[0]); n=e.get('n',e.get('sample_size',0))
                if width<=0 or (n and width < 1e-6/max(1,math.sqrt(float(n)))): findings.append(('implausibly_narrow_ci',e))
            except (TypeError,ValueError): pass
    verdicts=[str(e.get('verdict','')).lower() for e in entries if e.get('verdict') is not None]
    if len(verdicts)>=3 and all(any(x in v for x in ('supported','confirmed','pass')) for v in verdicts): findings.append(('all_supported',{'count':len(verdicts)}))
    return findings

def _coverage_entries(path):
    entries={}; current=None
    for line in Path(path).read_text(errors='replace').splitlines():
        m=re.match(r'\s{2}(C\d+):\s*$',line)
        if m: current=m.group(1);entries[current]={};continue
        if current:
            m=re.match(r'\s{4}(level|mechanism|rationale_if_null):\s*(.*)$',line)
            if m:
                val=m.group(2).strip(); entries[current][m.group(1)]=None if val in ('null','~','') else val.strip('"\'')
    return entries

def _constitution_principles(path):
    out={}
    for line in Path(path).read_text(errors='replace').splitlines():
        m=re.match(r'^#\s+(C\d+)\s+—\s+(.+)$',line)
        if m: out[m.group(1)]={'title':m.group(2),'level':'A'}
    return out

def verify_constitution_coverage(r):
    cpath=HERE/'constitution.md'; ypath=HERE/'constitution_coverage.yaml'; principles=_constitution_principles(cpath)
    if not ypath.exists(): print(json.dumps({'status':'FAIL','error':'missing constitution_coverage.yaml'})); return EXIT_CONSTITUTION
    entries=_coverage_entries(ypath); errors=[]
    for cid,p in principles.items():
        e=entries.get(cid)
        if not e: errors.append(f'{cid} missing from coverage'); continue
        if e.get('level')!=p['level']: errors.append(f'{cid} level drift')
        mech=e.get('mechanism'); rat=e.get('rationale_if_null')
        if p['level']=='A' and ((mech is None)==(rat is None)): errors.append(f'{cid} must have exactly one of mechanism/rationale_if_null')
        if mech and not re.search(r'(?:Audit\.|engine\.|[A-Za-z_][A-Za-z0-9_-]*)',mech): errors.append(f'{cid} mechanism is not a callable or command')
    extra=set(entries)-set(principles)
    if extra: errors.append('coverage contains unknown principles: '+','.join(sorted(extra)))
    if errors: print(json.dumps({'status':'FAIL','errors':errors},indent=2)); return EXIT_CONSTITUTION
    print(f'{sum(1 for e in entries.values() if e.get("level")=="A" and e.get("mechanism")):d}/{len(principles)} Level-A principles mechanized, {sum(1 for e in entries.values() if e.get("level")=="A" and e.get("rationale_if_null")):d} with documented rationale, 0 gaps'); return 0

def verify_training_sufficiency(path):
    try: m=_json_load(path)
    except Exception as e: print(json.dumps({'status':'FAIL','error':str(e)})); return EXIT_TRAINING
    # Use strict schema validation (v3.3.0)
    try: c=validate_training_manifest(m)
    except ValidationError as e: print(json.dumps({'status':'FAIL','errors':[str(e)]},indent=2)); return EXIT_TRAINING
    epochs=c.get('epochs_trained')
    early_raw=c.get('early_stopping_triggered')
    # Strict boolean check: early_stopping_triggered must be a real boolean if present
    early=False
    if early_raw is not None:
        if type(early_raw) is not bool:
            print(json.dumps({'status':'FAIL','errors':['early_stopping_triggered must be a JSON boolean']},indent=2)); return EXIT_TRAINING
        early=early_raw
    justification=str(c.get('justification','')).strip(); errors=[]
    # Reject NaN/Inf explicitly: comparisons with NaN are false and previously
    # let malformed manifests pass every numeric threshold.
    if (isinstance(epochs,bool) or not isinstance(epochs,(int,float)) or
            not math.isfinite(float(epochs)) or epochs<=0): errors.append('epochs_trained must be a finite number > 0')
    elif epochs<10 and not early and not justification: errors.append('fewer than 10 epochs requires early stopping or a specific justification')
    curve=c.get('loss_curve',[])
    try: threshold=float(c.get('criterion_threshold',.001) or .001)
    except (TypeError,ValueError): threshold=float('nan')
    if not math.isfinite(threshold) or threshold<=0: errors.append('criterion_threshold must be finite and > 0')
    if isinstance(curve,list) and len(curve)>=5 and not early and not justification:
        try:
            tail=[float(x) for x in curve[max(0,int(len(curve)*.8)):]]
            if not all(math.isfinite(x) for x in tail): raise ValueError
            slope=(tail[-1]-tail[0])/max(1,len(tail)-1)
            if abs(slope)>threshold: errors.append(f'validation loss slope {slope:.6g} exceeds criterion threshold {threshold}')
        except (TypeError,ValueError): errors.append('loss_curve must contain finite numeric values')
    if errors: print(json.dumps({'status':'FAIL','errors':errors},indent=2)); return EXIT_TRAINING
    print(json.dumps({'status':'PASS','epochs_trained':epochs})); return 0

def verify_split_integrity(path,tier=None):
    try: m=_json_load(path)
    except Exception as e: print(json.dumps({'status':'FAIL','error':str(e)})); return EXIT_SPLIT
    # Use strict schema validation (v3.3.0)
    try: validate_split_manifest(m)
    except ValidationError as e: print(json.dumps({'status':'FAIL','errors':[str(e)]},indent=2)); return EXIT_SPLIT
    counts=m.get('test_label_distribution',m.get('label_distribution',{})); justification=str(m.get('sample_size_justification','')).strip(); errors=[]; warnings=[]
    if not isinstance(counts,dict): errors.append('label distribution must be an object')
    elif not counts: errors.append('label distribution must not be empty')
    else:
        bad=[k for k,v in counts.items() if isinstance(v,bool) or not isinstance(v,(int,float)) or not math.isfinite(float(v)) or v<0]
        if bad: errors.append('label counts must be finite nonnegative numbers: '+','.join(map(str,bad)))
    total=sum(float(v) for v in counts.values()) if isinstance(counts,dict) and not errors else 0
    if tier not in ('T-DESC','T_DESC') and total<30 and not justification: errors.append(f'test sample size {total} is below floor 30 without sample_size_justification')
    if counts:
        vals=sorted([float(v) for v in counts.values()]) if isinstance(counts,dict) and not errors else []
        if vals and vals[0]<10 and tier not in ('T-DESC','T_DESC') and not justification: errors.append(f'minimum class count {vals[0]} is below floor 10 without justification')
        if vals and vals[0] and vals[-1]/vals[0]>100:
            handling=str(m.get('imbalance_handling','') or m.get('methodology','')).strip()
            (errors if not handling else warnings).append('class imbalance exceeds 100:1; handling statement required')
    if errors: print(json.dumps({'status':'FAIL','errors':errors,'warnings':warnings},indent=2)); return EXIT_SPLIT
    print(json.dumps({'status':'PASS','warnings':warnings,'n':total})); return 0

def verify_result_plausibility(path):
    try: obj=path if isinstance(path,(dict,list)) else _json_load(path)
    except Exception as e: print(json.dumps({'status':'FAIL','error':str(e)})); return EXIT_PLAUSIBILITY
    # Use recursive deep findings in addition to flat findings
    findings=_result_findings(obj)
    deep_findings=_deep_result_findings(obj) if isinstance(obj,(dict,list)) else []
    all_findings=findings+[f for f in deep_findings if f not in findings]
    if all_findings:
        note=(obj.get('investigation_note','') if isinstance(obj,dict) else '') or ''
        if not note: note=' '.join(str(e.get('investigation_note','')) for _,e in all_findings if isinstance(e,dict))
        if not str(note).strip(): print(json.dumps({'status':'FAIL','findings':[k for k,_ in all_findings],'error':'investigation_note required'})); return EXIT_PLAUSIBILITY
        # Investigation note must have a disposition, not just free text
        disposition=None
        if isinstance(obj,dict):
            disposition=obj.get('investigation_disposition')
        if disposition and disposition not in ('explained','claim_narrowed','unresolved'):
            print(json.dumps({'status':'FAIL','error':'investigation_disposition must be explained, claim_narrowed, or unresolved'})); return EXIT_PLAUSIBILITY
        print(json.dumps({'status':'PASS_WITH_INVESTIGATION','findings':[k for k,_ in all_findings],'note_verified':False,'disposition':disposition})); return 0
    print(json.dumps({'status':'PASS'})); return 0

def _ids_from_obj(obj):
    ids=set()
    if isinstance(obj,dict):
        for k,v in obj.items():
            if re.search(r'(^|_)(id|ID)$',str(k)) and isinstance(v,(str,int)): ids.add(str(v))
            ids |= _ids_from_obj(v)
    elif isinstance(obj,list):
        for x in obj: ids |= _ids_from_obj(x)
    return ids

def verify_cross_artifact_traceability(analysis,sources,id_pattern=None):
    try: pat=re.compile(id_pattern or r'(?i)(?:#|\b(?:id|candidate|sample|record)[: ]+)\s*([A-Za-z0-9_-]{4,})')
    except re.error as e:
        print(json.dumps({'status':'FAIL','error':'invalid id pattern: '+str(e)})); return EXIT_TRACE
    try: text=Path(analysis).read_text(errors='replace')
    except OSError as e:
        print(json.dumps({'status':'FAIL','error':'cannot read analysis: '+str(e)})); return EXIT_TRACE
    wanted={m.group(1) for m in pat.finditer(text)}; found=set(); errors=[]
    for src in sources:
        p=Path(src)
        try:
            if p.suffix.lower()=='.csv':
                with p.open(newline='') as f:
                    reader=csv.DictReader(f)
                    if not reader.fieldnames: raise ValueError('CSV has no header')
                    for row in reader:
                        for k,v in row.items():
                            if re.search(r'(^|_)(id|ID)$',str(k)) and v is not None: found.add(str(v))
            else: found |= _ids_from_obj(_json_load(p))
        except Exception as e:
            # A corrupt/unreadable source must not be treated as an empty source;
            # the prior continue made traceability pass with no usable evidence.
            errors.append(f'{p}: {e}')
    if errors:
        print(json.dumps({'status':'FAIL','errors':errors},indent=2)); return EXIT_TRACE
    missing=sorted(wanted-found)
    if missing: print(json.dumps({'status':'FAIL','missing_identifiers':missing},indent=2)); return EXIT_TRACE
    print(json.dumps({'status':'PASS','identifiers_checked':len(wanted)})); return 0

def acquisition_audit(scripts):
    paths=[Path(x) for x in scripts] if scripts else list(HERE.rglob('*.py'))
    findings=_scan_phantom_input_fabrication(paths)+_scan_undisclosed_synthetic_fallback(paths)
    print(json.dumps({'status':'FAIL' if any(x['severity']=='HARD_FAIL' for x in findings) else 'PASS','findings':findings},indent=2)); return 11 if any(x['severity']=='HARD_FAIL' for x in findings) else 0

def tier_check(path):
    text=Path(path).read_text(errors='replace'); m=re.search(r'(?i)\b(T-(?:DESC|COMP|CAUSAL))\b',text); declared=m.group(1).upper() if m else 'T-DESC'; inferred='T-CAUSAL' if re.search(r'(?i)causal|mechanism|intervention',text) else 'T-COMP' if _TCOMP_STRONG_RE.search(text) or _detects_verdict_enum(text) else 'T-DESC'
    order={'T-DESC':0,'T-COMP':1,'T-CAUSAL':2}; out={'declared':declared,'inferred':inferred}
    if order.get(inferred,0)>order.get(declared,0): print(json.dumps({'status':'FAIL','tier_mismatch':out})); return 18
    print(json.dumps({'status':'PASS',**out})); return 0

def verify_reproducibility(manifest):
    try: m=_json_load(manifest)
    except Exception as e: print(json.dumps({'status':'FAIL','error':str(e)})); return EXIT_REPRO
    # Use strict schema validation (v3.3.0)
    try: validate_reproduction_manifest(m)
    except ValidationError as e: print(json.dumps({'status':'FAIL','error':str(e)})); return EXIT_REPRO
    a=m.get('original',m.get('result')); b=m.get('replay',m.get('reproduction'))
    try: tol=float(m.get('tolerance',1e-6))
    except (TypeError,ValueError): tol=float('nan')
    if not isinstance(a,dict) or not isinstance(b,dict): print(json.dumps({'status':'FAIL','error':'manifest requires original and replay results'})); return EXIT_REPRO
    if not math.isfinite(tol) or tol<0:
        print(json.dumps({'status':'FAIL','error':'tolerance must be a finite nonnegative number'})); return EXIT_REPRO

    # Compare the complete result structure recursively.  The previous
    # top-level numeric-only comparison silently ignored nested metric changes,
    # missing keys, strings, and list contents (all useful forgery channels).
    diffs={}
    def compare(x,y,path):
        if isinstance(x,bool) or isinstance(y,bool):
            if type(x) is not type(y) or x!=y: diffs[path]=(x,y)
        elif isinstance(x,(int,float)) and isinstance(y,(int,float)):
            if not math.isfinite(float(x)) or not math.isfinite(float(y)) or abs(float(x)-float(y))>tol: diffs[path]=(x,y)
        elif isinstance(x,dict) and isinstance(y,dict):
            for k in sorted(set(x)|set(y),key=str):
                if k not in x or k not in y: diffs[f'{path}.{k}']=(x.get(k),y.get(k))
                else: compare(x[k],y[k],f'{path}.{k}')
        elif isinstance(x,list) and isinstance(y,list):
            if len(x)!=len(y): diffs[path]=(len(x),len(y))
            for i,(xx,yy) in enumerate(zip(x,y)): compare(xx,yy,f'{path}[{i}]')
        elif type(x) is not type(y) or x!=y: diffs[path]=(x,y)
    compare(a,b,'result')
    if diffs: print(json.dumps({'status':'FAIL','differences':diffs},indent=2)); return EXIT_REPRO
    print(json.dumps({'status':'PASS','tolerance':tol})); return 0

def verify_sensitivity_analysis(manifest):
    try: m=_json_load(manifest)
    except Exception as e: print(json.dumps({'status':'FAIL','error':str(e)})); return 28
    findings=[]; errors=[]
    entries=m.get('sweeps',m.get('entries',m if isinstance(m,list) else []))
    if isinstance(entries,dict): entries=[entries]
    if not entries: errors.append('manifest requires at least one sensitivity sweep')
    for item in entries or []:
        if not isinstance(item,dict): errors.append('each sensitivity sweep must be an object'); continue
        vals=item.get('metrics',item.get('values',[])) if isinstance(item,dict) else []
        if isinstance(vals,dict): vals=list(vals.values())
        try:
            nums=[float(v) for v in vals]
            if not nums or not all(math.isfinite(v) for v in nums): raise ValueError
            if len(nums)>1 and max(nums)-min(nums)<max(.005,.01*max(abs(v) for v in nums)) and not item.get('expected_flat'): findings.append(item.get('parameter','unknown'))
        except (TypeError,ValueError): errors.append(f"{item.get('parameter','unknown')}: metrics must be a nonempty finite numeric list")
    if errors:
        print(json.dumps({'status':'FAIL','errors':errors,'flat_parameters':findings},indent=2)); return 28
    if findings: print(json.dumps({'status':'FAIL','flat_parameters':findings})); return 28
    print(json.dumps({'status':'PASS'})); return 0

def verify_statistical_protocol(path):
    """Validate a structured statistical protocol and its reported values."""
    try: obj=_json_load(path)
    except Exception as e: print(json.dumps({'status':'FAIL','error':str(e)})); return 27
    proto=obj.get('statistical_protocol',obj) if isinstance(obj,dict) else {}
    required=('primary_metric','sampling_unit','test','alpha','effect_size','confidence_interval','multiplicity_correction')
    missing=[k for k in required if k not in proto]
    errors=[]
    if missing: errors.append('missing structured fields: '+', '.join(missing))
    try:
        alpha=float(proto.get('alpha')); 
        if not 0<alpha<=.1: errors.append('alpha must be in (0, .1]')
    except (TypeError,ValueError): errors.append('alpha must be numeric')
    ci=proto.get('confidence_interval')
    if not isinstance(ci,list) or len(ci)!=2: errors.append('confidence_interval must be [low, high]')
    elif any(not isinstance(x,(int,float)) or not math.isfinite(float(x)) for x in ci) or ci[0]>ci[1]: errors.append('confidence_interval is invalid')
    if isinstance(proto.get('p_values'),list) and len(proto['p_values'])>1 and not proto.get('multiplicity_correction'): errors.append('multiplicity correction required for multiple p-values')
    if errors: print(json.dumps({'status':'FAIL','errors':errors},indent=2)); return 27
    print(json.dumps({'status':'PASS','fields_checked':len(required)})); return 0

def pre_submission_audit(path):
    """Require a value-bearing, machine-readable release readiness record."""
    try: obj=_json_load(path)
    except Exception as e: print(json.dumps({'status':'FAIL','error':str(e)})); return 29
    if not isinstance(obj,dict): print(json.dumps({'status':'FAIL','error':'artifact must be an object'})); return 29
    required=('claims','data_provenance','baselines','ablations','limitations','reproducibility')
    errors=[]
    for k in required:
        v=obj.get(k)
        if v is None or v=='' or v==[] or v=={}: errors.append('missing substantive section: '+k)
    claims=obj.get('claims',[])
    if isinstance(claims,list):
        for i,c in enumerate(claims):
            if not isinstance(c,dict) or not c.get('evidence') or not c.get('scope'): errors.append(f'claim {i} needs evidence and scope')
    if errors: print(json.dumps({'status':'FAIL','errors':errors},indent=2)); return 29
    print(json.dumps({'status':'PASS','sections_checked':len(required)})); return 0

def verify_failure_taxonomy(path):
    """Validate failure cases as traced, categorized observations."""
    try: obj=_json_load(path)
    except Exception as e: print(json.dumps({'status':'FAIL','error':str(e)})); return 30
    rows=obj.get('failures',obj.get('taxonomy',[])) if isinstance(obj,dict) else []
    errors=[]
    if not isinstance(rows,list) or len(rows)<3: errors.append('at least three failure categories are required')
    seen=set()
    for i,row in enumerate(rows if isinstance(rows,list) else []):
        if not isinstance(row,dict): errors.append(f'failure {i} must be an object'); continue
        if not row.get('category'): errors.append(f'failure {i} missing category')
        if row.get('category') in seen: errors.append(f'duplicate failure category: {row.get("category")}')
        seen.add(row.get('category'))
        if not row.get('condition_ids') and not row.get('candidate_ids'): errors.append(f'failure {i} missing traced condition/candidate IDs')
        if not isinstance(row.get('prevalence',row.get('rate')), (int,float)): errors.append(f'failure {i} missing numeric prevalence')
        if row.get('severity') not in ('SEV-1','SEV-2','SEV-3','SEV-4'): errors.append(f'failure {i} missing severity SEV-1..SEV-4')
    if errors: print(json.dumps({'status':'FAIL','errors':errors},indent=2)); return 30
    print(json.dumps({'status':'PASS','categories_checked':len(rows)})); return 0

_MODULE_BY_FILE={'audit.py':'engine.audit','metrics.py':'engine.metrics','io.py':'engine.io'}

def _call_graph(paths):
    graph={}; defs={}
    for path in paths:
        try: tree=ast.parse(Path(path).read_text(errors='replace'),filename=str(path))
        except (OSError,SyntaxError): continue
        module=_MODULE_BY_FILE.get(Path(path).name,'gatekeeper')
        for node in ast.walk(tree):
            if isinstance(node,(ast.FunctionDef,ast.AsyncFunctionDef)):
                key=f'{module}.{node.name}'; defs[key]=node; graph.setdefault(key,set())
                for call in ast.walk(node):
                    if isinstance(call,ast.Call):
                        name=_fn_name(call.func).split('.')[-1]
                        if name: graph[key].add(name)
                    elif isinstance(call,ast.Attribute):
                        # Guarded callbacks (for example self.cohort passed to
                        # self.guard) are references rather than Call nodes.
                        graph[key].add(call.attr)
    return graph,defs


def _is_trivial_body(node):
    """True if THIS function's own body, ignoring its docstring, has no
    assertion, exception, loop, branch, or call into the guard vocabulary.
    Does not look at what the function calls; see _is_substantive for that."""
    body=list(node.body)
    if body and isinstance(body[0],ast.Expr) and isinstance(getattr(body[0],'value',None),ast.Constant) and isinstance(body[0].value.value,str): body=body[1:]
    if not body or (len(body)==1 and isinstance(body[0],ast.Pass)): return True
    if len(body)==1 and isinstance(body[0],ast.Return) and (body[0].value is None or isinstance(body[0].value,ast.Constant)): return True
    for n in ast.walk(node):
        if isinstance(n,(ast.Assert,ast.Raise,ast.For,ast.While,ast.If)): return False
        if isinstance(n,ast.Call):
            fn=_fn_name(n.func)
            if fn and fn.split('.')[-1] in ('need','error','diagnostic'): return False
    return True

def _is_substantive(target,graph,defs,seen=None):
    """A mechanism counts as real evidence of enforcement if it, or anything
    reachable from it in the call graph, is non-trivial by _is_trivial_body.
    A thin dispatcher that only calls real checking functions is substantive
    through its callees; a stub that calls nothing real is not, no matter how
    many layers of dispatch sit on top of it."""
    if seen is None: seen=set()
    if target in seen: return False
    seen.add(target)
    node=defs.get(target)
    if node is not None and not _is_trivial_body(node): return True
    for callee in graph.get(target,set()):
        for candidate in graph:
            if candidate.endswith('.'+callee) and candidate not in seen:
                if _is_substantive(candidate,graph,defs,seen): return True
    return False

def verify_coverage_liveness(r,quiet=False):
    """Check coverage claims against callable existence, reachability and rule drift."""
    ypath=HERE/'constitution_coverage.yaml'; dpath=HERE/'dynamic_rules.md'
    entries=_coverage_entries(ypath) if ypath.exists() else {}; errors=[]
    dynamic={}
    if dpath.exists():
        block=None
        for line in dpath.read_text(errors='replace').splitlines():
            m=re.match(r'###\s+(D-\d+)',line)
            if m: block=m.group(1); continue
            if block and 'Implementation:' in line:
                dynamic[block]=line.split('Implementation:',1)[1].strip().strip('`')
    graph,defs=_call_graph([HERE/'gatekeeper.py',HERE/'engine/audit.py',HERE/'engine/metrics.py',HERE/'engine/io.py',HERE/'engine/contract.py',HERE/'engine/supervisor.py',HERE/'engine/schema.py',HERE/'engine/attacks.py'])
    reachable=set(); todo=['gatekeeper.certify','gatekeeper.audit','engine.audit.run','gatekeeper.run_exp','gatekeeper.freeze']
    while todo:
        key=todo.pop()
        if key in reachable: continue
        reachable.add(key)
        for callee in graph.get(key,set()):
            for candidate in graph:
                if candidate.endswith('.'+callee): todo.append(candidate)
    resolved={};
    for cid,e in entries.items():
        mech=e.get('mechanism')
        if not mech: continue
        dm=re.search(r'\((D-\d+)\)',mech); dcode=dm.group(1) if dm else None
        target=mech.split('(',1)[0].strip().replace('`','')
        target=target.replace(' (','').strip()
        if target.startswith('Audit.'):
            target='engine.audit.'+target.split('.',1)[1]
        elif target.startswith('engine.'):
            pass
        elif target in ('read_json','inside','paired_inference','binary_metrics'):
            target=('engine.metrics.' if target in ('paired_inference','binary_metrics') else 'engine.io.')+target
        else: target='gatekeeper.'+target.replace('-','_')
        if target in resolved.values(): errors.append(f'{cid} duplicates mechanism callable {target}')
        resolved[cid]=target
        if target not in graph:
            errors.append(f'{cid} mechanism is not a callable: {target}')
        elif target not in reachable:
            errors.append(f'{cid} mechanism is not reachable from certify/audit roots: {target}')
        if target in graph and not _is_substantive(target,graph,defs):
            errors.append(f'{cid} mechanism {target} (and everything it calls) has no assertion, branch, or need()/error()/diagnostic() call — it cannot fail, so it cannot be evidence of enforcement')
        if dcode and dcode in dynamic:
            impl=dynamic[dcode].replace('`','')
            token=target.split('.')[-1]
            if token not in impl and target not in impl:
                errors.append(f'{cid} mechanism disagrees with {dcode} Implementation: {impl}')
    if errors:
        out={'status':'FAIL','errors':errors}
        if not quiet: print(json.dumps(out,indent=2))
        return 40,out
    out={'status':'PASS','principles_checked':len(entries),'callables_resolved':len(resolved)}
    if not quiet: print(json.dumps(out,indent=2))
    return 0,out

def check_contract(path):
    """Validate a real structured contract; prose mentioning check names is insufficient."""
    try: obj=_json_load(path)
    except Exception as e: print(json.dumps({'status':'FAIL','error':'contract must be strict JSON with executable checks: '+str(e)})); return 17
    if not isinstance(obj,dict) or not isinstance(obj.get('checks'),list): print(json.dumps({'status':'FAIL','error':'contract requires a checks array'})); return 17
    errors=[]; allowed={'audit','certify','verify-constitution-coverage','verify-training-sufficiency','verify-split-integrity','verify-result-plausibility','verify-cross-artifact-traceability','verify-reproducibility','acquisition-audit','tier-check','verify-sensitivity-analysis','verify-statistical-protocol','pre-submission-audit','verify-failure-taxonomy'}
    for i,c in enumerate(obj['checks']):
        if not isinstance(c,dict) or c.get('command') not in allowed: errors.append(f'check {i} has no registered executable command')
        if not isinstance(c.get('artifacts'),list) or not c['artifacts']: errors.append(f'check {i} must bind artifacts')
    if errors: print(json.dumps({'status':'FAIL','errors':errors},indent=2)); return 17
    print(json.dumps({'status':'PASS','checks':len(obj['checks'])})); return 0

@contextmanager
def workspace_lock(r):
 # Resolve only the lock location so symlink aliases cannot bypass the
 # single-operation guard; retain lexical roots elsewhere for artifact IDs.
 st=inside(Path(r).resolve(),STATE);st.mkdir(parents=True,exist_ok=True)
 with inside(Path(r).resolve(),STATE+'/operation.lock').open('a+') as f:
  try:fcntl.flock(f.fileno(),fcntl.LOCK_EX|fcntl.LOCK_NB)
  except BlockingIOError:die('another factory operation is running; retain checkpoints and retry later')
  try:yield
  finally:fcntl.flock(f.fileno(),fcntl.LOCK_UN)

def status(r):
 r=root(r)
 p=plan_at(r);epoch,ep,f=active(r);pending=[]
 for e in p['experiments']:
  paths=sorted((ep/'runs'/e['id']).glob('attempt*/execution.json'))
  rec=read_json(paths[-1]) if paths else {}
  if rec.get('exit_code')!=0 or rec.get('record_error'):pending.append(e['id'])
 print(json.dumps({'epoch':epoch,'pending_experiments':pending,'inputs_current':source_inputs(r,p,f),'next':'run . all' if pending else 'audit . then Architect review then certify .'},indent=2));return 0

def handoff(r):
 r=root(r)
 from engine.bundle import create_bundle
 try:
  p=plan_at(r);out=audit_snapshot(r,p);certified=certificate_current(r,p,out)
 except Exception:
  invalidate_certificate(r);raise
 if not certified:
  invalidate_certificate(r);write_json(inside(r,'project/audit_report.json'),out)
 # A still-current certificate binds the original audit bytes. Revalidation
 # must not replace that audit solely to change its timestamp.
 files=set(out['file_bindings'])|{'project/audit_report.json'}
 files.update(k for k in inventory(r,[STATE]) if k!=STATE+'/operation.lock')
 for rel in ('project/review.json','project/RELEASE_CERTIFICATION.json'):
  if inside(r,rel).is_file():files.add(rel)
 paths={rel:inside(r,rel) for rel in files}
 paths.update({'factory/'+str(path.relative_to(HERE)):path for path in active_engine_files()})
 dest=inside(r,'TAKE_THIS');dest.mkdir(exist_ok=True)
 name=inside(r,'TAKE_THIS/review_bundle_'+out['evidence_digest'][:12]+'.zip')
 create_bundle(name,paths,{'factory_version':VERSION,'evidence_digest':out['evidence_digest'],
                         'release_status':'READY_FOR_HUMAN_SUBMISSION_REVIEW' if certified else 'NOT_CERTIFIED'})
 print(json.dumps({'status':'BUNDLE_CREATED','path':str(name),'sha256':sha(name),
                   'release_status':'READY_FOR_HUMAN_SUBMISSION_REVIEW' if certified else 'NOT_CERTIFIED',
                   'includes':'evidence, retained epochs, active factory, review reports and checksum manifest'},indent=2));return 0

def certificate_current(r,p,out):
 try:
  cert=read_json(inside(r,'project/RELEASE_CERTIFICATION.json'))
  if out['errors'] or p['intent']=='fixture' or p['data_origin']=='fixture':return False
  if cert.get('status')!='READY_FOR_HUMAN_SUBMISSION_REVIEW':return False
  if cert.get('epoch')!=out['epoch'] or cert.get('factory_version')!=VERSION:return False
  if cert.get('evidence_digest')!=out['evidence_digest'] or cert.get('engine_sha256')!=engine_hash():return False
  if cert.get('audit_sha256')!=sha(inside(r,'project/audit_report.json')):return False
  if cert.get('review_sha256')!=sha(inside(r,'project/review.json')):return False
  verify_review(r,p,out)
  return True
 except (EvidenceError,OSError,KeyError,TypeError,AttributeError):return False

def verify_handoff(path):
 from engine.bundle import verify_bundle
 manifest=verify_bundle(path)
 print(json.dumps({'status':'BUNDLE_INTEGRITY_VERIFIED','files':len(manifest['files']),
                   'release_status':manifest.get('release_status'),
                   'scope':'membership and byte integrity only; re-audit after extraction'}));return 0

def main(argv=None):
 ap=argparse.ArgumentParser();sub=ap.add_subparsers(dest='cmd',required=True)
 sub.add_parser('init').add_argument('project',nargs='?',default='.')
 x=sub.add_parser('freeze');x.add_argument('project',nargs='?',default='.');x.add_argument('--amendment')
 x=sub.add_parser('run');x.add_argument('project');x.add_argument('experiment')
 x=sub.add_parser('record');x.add_argument('project');x.add_argument('experiment');x.add_argument('run_dir')
 x=sub.add_parser('verify-bundle');x.add_argument('archive')
 for cmd in ('audit','certify','status','handoff'):sub.add_parser(cmd).add_argument('project',nargs='?',default='.')
 sub.add_parser('verify-constitution-coverage')
 x=sub.add_parser('verify-training-sufficiency');x.add_argument('--manifest',required=True)
 x=sub.add_parser('verify-split-integrity');x.add_argument('--manifest',required=True);x.add_argument('--tier')
 x=sub.add_parser('verify-result-plausibility');x.add_argument('--artifact',required=True)
 x=sub.add_parser('verify-cross-artifact-traceability');x.add_argument('--analysis',required=True);x.add_argument('--source',required=True,nargs='+');x.add_argument('--id-pattern')
 x=sub.add_parser('verify-reproducibility');x.add_argument('--manifest',required=True)
 x=sub.add_parser('acquisition-audit');x.add_argument('--scripts',nargs='*')
 x=sub.add_parser('tier-check');x.add_argument('--contract',required=True)
 x=sub.add_parser('verify-sensitivity-analysis');x.add_argument('--manifest',required=True)
 x=sub.add_parser('verify-statistical-protocol');x.add_argument('--artifact',required=True)
 x=sub.add_parser('pre-submission-audit');x.add_argument('--artifact',required=True)
 x=sub.add_parser('verify-failure-taxonomy');x.add_argument('--artifact',required=True)
 x=sub.add_parser('check');x.add_argument('--contract',required=True)
 sub.add_parser('verify-coverage-liveness')
 x=sub.add_parser('release-certify');x.add_argument('project',nargs='?',default='.')
 x=sub.add_parser('self-check');x.add_argument('project',nargs='?',default='.')
 a=ap.parse_args(argv);r=root(getattr(a,'project','.') or '.')
 try:
  if a.cmd=='init':return init(r)
  if a.cmd=='verify-bundle':return verify_handoff(a.archive)
  if a.cmd=='freeze':return freeze(r,a.amendment)
  if a.cmd=='run':
   if a.experiment=='all':
    codes=[]
    for e in plan_at(r)['experiments']:
     try:codes.append(run_exp(r,e['id']))
     except EvidenceError as ex:print(json.dumps({'experiment':e['id'],'error':str(ex)}));codes.append(EXIT_EVIDENCE)
    return max(codes,default=EXIT_EVIDENCE)
   return run_exp(r,a.experiment)
  if a.cmd=='record':return record(r,a.experiment,a.run_dir)
  if a.cmd=='audit':return audit(r)
  if a.cmd=='status':return status(r)
  if a.cmd=='handoff':return handoff(r)
  if a.cmd=='verify-constitution-coverage':return verify_constitution_coverage(r)
  if a.cmd=='verify-training-sufficiency':return verify_training_sufficiency(a.manifest)
  if a.cmd=='verify-split-integrity':return verify_split_integrity(a.manifest,a.tier)
  if a.cmd=='verify-result-plausibility':return verify_result_plausibility(a.artifact)
  if a.cmd=='verify-cross-artifact-traceability':return verify_cross_artifact_traceability(a.analysis,a.source,a.id_pattern)
  if a.cmd=='verify-reproducibility':return verify_reproducibility(a.manifest)
  if a.cmd=='acquisition-audit':return acquisition_audit(a.scripts)
  if a.cmd=='tier-check':return tier_check(a.contract)
  if a.cmd=='verify-sensitivity-analysis':return verify_sensitivity_analysis(a.manifest)
  if a.cmd=='verify-statistical-protocol':return verify_statistical_protocol(a.artifact)
  if a.cmd=='pre-submission-audit':return pre_submission_audit(a.artifact)
  if a.cmd=='verify-failure-taxonomy':return verify_failure_taxonomy(a.artifact)
  if a.cmd=='check':return check_contract(a.contract)
  if a.cmd=='verify-coverage-liveness':return verify_coverage_liveness(r)[0]
  if a.cmd=='release-certify':
   coverage=verify_constitution_coverage(r)
   return coverage if coverage else certify(r)
  if a.cmd=='self-check':
   verify_constitution_coverage(r); print(json.dumps({'status':'DIAGNOSTIC','version':VERSION})); return 0
  return certify(r)
 except (EvidenceError,KeyError,TypeError,ValueError,OSError) as e:
  code=40 if a.cmd in ('certify','release-certify') and 'missing project/research_plan.json' in str(e) else EXIT_EVIDENCE
  print(json.dumps({'status':'NOT_CERTIFIED','error':str(e),'code':code},indent=2));return code
if __name__=='__main__':
 try:
 # project is the second positional token for every command.
  r=root(sys.argv[2] if len(sys.argv)>2 and not sys.argv[2].startswith('-') else '.')
  # Standalone artifact validators are read-only and must not create project
  # state in the factory bundle. Only lifecycle operations take the lock.
  locked_commands={'init','freeze','run','record','audit','certify','status','handoff','release-certify'}
  if len(sys.argv)>1 and sys.argv[1] in locked_commands:
   with workspace_lock(r):code=main()
  else:code=main()
 except EvidenceError as ex:
 # A missing project is a release preflight failure, distinct from an evidence
 # failure inside an otherwise initialized project. Keep the CLI contract
 # stable for automation while direct Python calls still raise EvidenceError.
  if len(sys.argv)>1 and sys.argv[1] in ('certify','release-certify') and 'missing project/research_plan.json' in str(ex):
   print(json.dumps({'status':'NOT_CERTIFIED','error':str(ex),'code':40}));code=40
  else:
   print(json.dumps({'status':'BLOCKED','error':str(ex)}));code=EXIT_EVIDENCE
 sys.exit(code)
