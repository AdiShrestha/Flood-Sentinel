#!/usr/bin/env python3
"""Factory v3.3.0 fail-closed lifecycle CLI."""
from __future__ import annotations
import argparse,datetime as dt,hashlib,json,os,subprocess,sys,time,fcntl,ast,re,math,csv,uuid,io,signal,resource
from contextlib import contextmanager,redirect_stdout
from pathlib import Path
from enum import IntEnum
HERE=Path(__file__).resolve().parent
if str(HERE) not in sys.path:sys.path.insert(0,str(HERE))
from engine.io import EvidenceError,read_json,read_csv,inside,inventory,sha,write_json,digest,merkle_root
from engine.plan import validate
from engine.audit import Audit,verify_review
from engine.contract import validate_contract,resolve_contract,command_to_contract,contract_argv_template
from engine.supervisor import sign_receipt,verify_receipt_signature,build_receipt,runtime_attestation,init_supervisor_keys,supervisor_public_key,execution_binding,validate_execution_ledger,validate_run_nonce
from engine.schema import (expect_bool,expect_int,expect_float,expect_str,expect_list,expect_dict,expect_enum,
                           validate_training_manifest,validate_split_manifest,validate_plausibility_entry,
                           validate_reproduction_manifest,ValidationError)
class ExitCode(IntEnum):
    SUCCESS=0
    ACQUISITION=11
    CONTRACT=17
    TIER=18
    STATISTICAL_PROTOCOL=27
    SENSITIVITY=28
    PRE_SUBMISSION=29
    FAILURE_TAXONOMY=30
    CONSTITUTION=31
    TRAINING=32
    SPLIT=33
    PLAUSIBILITY=34
    TRACEABILITY=35
    REPRODUCTION=36
    RELEASE_PREFLIGHT=40
    EVIDENCE=41
    SCIENCE=42
    REVIEW=43
    PUBLICATION=44

VERSION='3.3.0';ROOT_PLAN='project/research_plan.json';STATE='project/.factory'
EXIT_EVIDENCE=ExitCode.EVIDENCE;EXIT_SCIENCE=ExitCode.SCIENCE;EXIT_REVIEW=ExitCode.REVIEW
EXIT_CONSTITUTION=ExitCode.CONSTITUTION;EXIT_TRAINING=ExitCode.TRAINING;EXIT_SPLIT=ExitCode.SPLIT
EXIT_PLAUSIBILITY=ExitCode.PLAUSIBILITY;EXIT_TRACE=ExitCode.TRACEABILITY;EXIT_REPRO=ExitCode.REPRODUCTION

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
 """Hash runtime code and governing policy, excluding tests and explanatory docs."""
 files={str(p.relative_to(HERE)):sha(p) for p in active_engine_files()
        if ('tests' not in p.relative_to(HERE).parts and
            (('engine' in p.relative_to(HERE).parts and p.suffix=='.py') or
             p.name in {'gatekeeper.py','verify_bundle_standalone.py','VERSION','constitution.md','dynamic_rules.md',
             'constitution_coverage.yaml','factory_spec.md','gatekeeper_spec.md','PUBLICATION_POLICY.md'}))}
 return merkle_root(files)

def validation_hash():
 """Bind the executable QA programs and regression corpus separately from freezes."""
 files={str(p.relative_to(HERE)):sha(p) for p in active_engine_files()
        if p.suffix=='.py' and ('tests' in p.relative_to(HERE).parts or
           (p.parent==HERE and p.name.startswith('run_')))}
 return merkle_root(files)
def freeze(r,amendment=None):
  r=root(r)
  p=plan_at(r); st=inside(r,STATE);st.mkdir(parents=True,exist_ok=True);cur=inside(r,STATE+'/current.json')
  for experiment in p['experiments']:
   experiment_contract(r,experiment)
  if cur.exists() and not amendment:die('already frozen; use --amendment with a reason to create a new epoch and preserve all prior evidence')
  if amendment is not None and not amendment.strip():die('amendment reason must be nonempty')
  if cur.exists():
   prior_epoch,prior_path,prior_freeze=active(r)
   if not (prior_path/'execution_ledger.json').is_file() or not (prior_path/'research_plan_snapshot.json').is_file():
    die('legacy frozen epoch lacks authenticated execution history; preserve the old project and migrate inputs into a new project directory; receipts cannot be retroactively attested')
   epoch=prior_epoch+1
  else:epoch=1
  # Inventory the directories themselves: pre-expansion used to silently omit
  # directory symlinks and dangling symlinks before the inventory could reject them.
  files=inventory(r,p['frozen_paths'])
  # Content-addressed snapshot: compute Merkle root over all frozen files
  snapshot_root=merkle_root(files)
  # Hash active checker and plan itself: rule changes require explicit epoch.
  previous=active(r)[1] if cur.exists() else None
  f={'factory_version':VERSION,'epoch':epoch,'created_at':now(),'amendment_reason':amendment,'plan_sha256':sha(r/ROOT_PLAN),'engine_sha256':engine_hash(),'frozen_paths':p['frozen_paths'],'files':files,'snapshot_merkle_root':snapshot_root,
     'previous_freeze_sha256':sha(previous/'freeze.json') if previous else None,
     'test_label_isolation':'not_enforced_workspace_readable'}
  test_rows=[row for row in read_csv(inside(r,p['cohort']),{'sample_id','group_id','split','label','source_ids'}) if row['split']=='test']
  f['holdout_fingerprint']=digest(sorted(test_rows,key=lambda row:row['sample_id']))
  f['holdout_group_ids']=sorted({row['group_id'] for row in test_rows})
  f['holdout_sample_ids']=sorted({row['sample_id'] for row in test_rows})
  f['holdout_source_ids']=sorted({source for row in test_rows for source in row['source_ids'].split('|')})
  f['previous_epoch_evidence']=inventory(r,[relpath(previous,r)],reject_dangerous_ext=False) if previous else None
  ep=inside(r,STATE+f'/epoch_{epoch:04d}')
  if ep.exists():die('epoch directory already exists; prior evidence will not be overwritten')
  if p['intent']=='research':
   Audit(r,p,ep,f,engine_hash()).cohort()
  invalidate_certificate(r)
  # Initialize supervisor keys if needed (outside workspace)
  private_key,_,_=init_supervisor_keys()
  if any(inside(r,path).resolve()==private_key.resolve() for path in files):
   die('supervisor private key cannot be included in frozen evidence or handoff files')
  key=supervisor_public_key();f['supervisor_public_key']=key['public_key'];f['supervisor_public_key_id']=key['public_key_id']
  ep.mkdir();(ep/'research_plan_snapshot.json').write_bytes((r/ROOT_PLAN).read_bytes())
  write_json(ep/'freeze.json',f)
  ledger={'artifact_type':'factory_execution_ledger','project_id':p['project_id'],'epoch':epoch,
          'freeze_sha256':sha(ep/'freeze.json'),'attempts':{}}
  write_json(ep/'execution_ledger.json',sign_receipt(ledger))
  write_json(cur,{'epoch':epoch,'freeze_path':str((ep/'freeze.json').relative_to(r))})
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
  """Compatibility adapter through the same typed command parser used by run."""
  code_paths=[args[1]] if isinstance(args,list) and len(args)>1 else []
  contract,_=command_to_contract(args,code_paths)
  argv,_,_=resolve_contract(contract,run,seed,eid)
  return argv

def execution_env(seed):
  """Pass only declared runtime settings; do not inherit credentials or loaders."""
  allowed={'PATH','LANG','LC_ALL','LC_CTYPE','TZ','OMP_NUM_THREADS','MKL_NUM_THREADS',
           'OPENBLAS_NUM_THREADS','CUDA_VISIBLE_DEVICES','SYSTEMROOT','TMPDIR'}
  env={k:v for k,v in os.environ.items() if k in allowed}
  env.setdefault('PATH',os.defpath)
  env['PYTHONHASHSEED']=str(int(seed) % (2**32))
  env['PYTHONDONTWRITEBYTECODE']='1'
  return env

def experiment_contract(r,e):
  contract=e.get('execution_contract')
  if contract is None:
   contract,_=command_to_contract(e['command'],e['code_paths'])
  return validate_contract(contract,r,e['code_paths'])

def execution_ledger(r,p,ep,f):
  ledger=read_json(inside(r,relpath(ep/'execution_ledger.json',r)))
  verify_receipt_signature(ledger,public_key=f['supervisor_public_key'])
  validate_execution_ledger(ledger,project_id=p['project_id'],epoch=f['epoch'],freeze_sha256=sha(ep/'freeze.json'),
                            run_prefix=relpath(ep/'runs',r),experiment_ids=[e['id'] for e in p['experiments']])
  return ledger

def run_exp(r,eid):
  r=root(r);invalidate_certificate(r)
  p=plan_at(r);epoch,ep,f=active(r)
  if not source_inputs(r,p,f):die('frozen inputs changed before run')
  if supervisor_public_key()['public_key_id']!=f.get('supervisor_public_key_id'):
   die('supervisor signing key changed since freeze; amend before execution')
  e=next((x for x in p['experiments'] if x['id']==eid),None)
  if not e:die('unknown experiment '+str(eid))
  ledger=execution_ledger(r,p,ep,f)
  base=inside(r,relpath(ep/'runs'/eid,r));base.mkdir(parents=True,exist_ok=True)
  existing=sorted(base.glob('attempt*'))
  if eid in ledger['attempts'] and not existing:
   die('recorded execution attempt was deleted; no same-epoch retry')
  if existing:
   last=read_json(inside(r,relpath(existing[-1]/'execution.json',r)))
   if isinstance(last,dict) and last.get('exit_code')==0 and not last.get('record_error'):
    return record(r,eid,relpath(existing[-1],r))
   die('failed attempt retained; no same-epoch retries. Amend the plan and disclose consumed holdouts before a new execution')
  a=inside(r,relpath(base/'attempt0001',r));seed=e['seed'];inputs=f['files']
  contract=experiment_contract(r,e)
  argv,preexec,env_extra=resolve_contract(contract,a,seed,eid)
  template=contract_argv_template(contract)
  env=execution_env(seed);env.update(env_extra)
  rt=runtime_attestation();run_nonce=validate_run_nonce(str(uuid.uuid4()))
  reserved=set()
  for number in range(1,epoch+1):
   prior=inside(r,STATE+f'/epoch_{number:04d}')
   old_f=read_json(prior/'freeze.json');old_p=read_json(prior/'research_plan_snapshot.json')
   old_ledger=execution_ledger(r,old_p,prior,old_f)
   nonces={entry['run_nonce'] for entry in old_ledger['attempts'].values()}
   if reserved & nonces:die('execution nonce reused across epochs')
   reserved.update(nonces)
  if run_nonce in reserved:die('execution nonce already reserved; no execution launched')
  a.mkdir()
  ledger['attempts'][eid]={'run_nonce':run_nonce,'attempt_path':relpath(a,r),'execution_sha256':None}
  write_json(ep/'execution_ledger.json',sign_receipt(ledger))
  timeout=contract.get('wall_seconds',3600)
  pre={'factory_version':VERSION,'project_id':p['project_id'],'epoch':epoch,
       'experiment_id':eid,'seed':seed,'argv':template,'argv_template':template,
       'execution_contract':contract,'freeze_sha256':sha(ep/'freeze.json'),
       'engine_sha256':engine_hash(),'inputs_before':inputs,'started_at':now(),
       'run_nonce':run_nonce,'runtime_attestation':rt,'snapshot_merkle_root':f['snapshot_merkle_root'],
       'interpreter_hash':rt['interpreter_hash'],'dependency_lock_hash':sha(r/p['dependency_lock']),
       'environment':{k:hashlib.sha256(v.encode()).hexdigest() for k,v in env.items()},
       'environment_representation':'value_sha256','runtime_id':contract['runtime_id'],
       'trust_profile':'same_user_local','network_isolation':'not_enforced',
       'wall_timeout_seconds':timeout}
  write_json(a/'execution.json',pre)
  env.update({'FACTORY_RUN_DIR':str(a.resolve()),'FACTORY_SEED':str(seed),'FACTORY_EXPERIMENT_ID':eid})
  t=time.monotonic();usage_before=resource.getrusage(resource.RUSAGE_CHILDREN)
  proc=None;capture_error=None
  try:
   with (a/'stdout.log').open('w') as stdout,(a/'stderr.log').open('w') as stderr:
    proc=subprocess.Popen(argv,cwd=r,env=env,stdout=stdout,stderr=stderr,
                          preexec_fn=preexec,start_new_session=True)
    try:code=proc.wait(timeout=timeout)
    except subprocess.TimeoutExpired:
     os.killpg(proc.pid,signal.SIGKILL);proc.wait();code=124;capture_error='wall-clock timeout'
    except KeyboardInterrupt:
     os.killpg(proc.pid,signal.SIGKILL);proc.wait();code=130;capture_error='interrupted'
    finally:
     try:os.killpg(proc.pid,signal.SIGKILL)
     except ProcessLookupError:pass
  except (OSError,subprocess.SubprocessError) as ex:
   (a/'stderr.log').write_text(str(ex));code=None;capture_error=str(ex)
  usage_after=resource.getrusage(resource.RUSAGE_CHILDREN)
  try:
   outputs=inventory(r,[relpath(a,r)],reject_dangerous_ext=False)
   outputs.pop(relpath(a/'execution.json',r),None)
   post=inventory(r,p['frozen_paths'])
  except EvidenceError as ex:
   outputs={};post={};capture_error=str(ex)
  rec={**pre,'returncode':code,'exit_code':code,'duration_sec':time.monotonic()-t,
       'finished_at':now(),'inputs_after':post,'outputs':outputs}
  if capture_error:rec['record_error']=capture_error
  rec['supervisor_receipt']=build_receipt(
    run_nonce=run_nonce,project_id=p['project_id'],epoch=epoch,experiment_id=eid,
    snapshot_merkle_root=f['snapshot_merkle_root'],input_root=digest(inputs),
    runtime_id=contract['runtime_id'],interpreter_hash=rt['interpreter_hash'],
    dependency_lock_hash=pre['dependency_lock_hash'],launch_spec=digest(template),seed=seed,
    output_root=digest(outputs),exit_status=code,
    cpu_time=(usage_after.ru_utime+usage_after.ru_stime)-(usage_before.ru_utime+usage_before.ru_stime),
    memory_peak=None,started_at=rec['started_at'],finished_at=rec['finished_at'],
    supervisor_version=VERSION,policy_version=str(p['schema_version']),
    execution_binding=execution_binding(rec),engine_sha256=pre['engine_sha256'],
    inputs_after_root=digest(post),trust_profile='same_user_local')
  write_json(a/'execution.json',rec)
  ledger['attempts'][eid]['execution_sha256']=sha(a/'execution.json')
  write_json(ep/'execution_ledger.json',sign_receipt(ledger))
  if code==0 and not capture_error:return record(r,eid,relpath(a,r))
  print(json.dumps({'status':'FAILED_ATTEMPT_RETAINED','attempt':relpath(a,r),
                    'exit_code':code,'error':capture_error},indent=2))
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
 except Exception:
  # The signed receipt is immutable even if validation fails.
  raise
 print(json.dumps({'status':'RECORDED','run':runrel,'heldout_metrics':'available at audit/review; labels remain workspace-readable'},indent=2));return 0

def _finalize_release_checks(r,p,out):
     """Run every release-critical check and bind its result into the digest."""
     findings=_acquisition_findings([inside(r,cp) for e in p.get('experiments',[]) for cp in e.get('code_paths',[])])
     _append_factory_findings(out,findings)
     methodology_text=inside(r,p['methodology']).read_text(errors='replace')
     with redirect_stdout(io.StringIO()):
         tier_code=tier_check(inside(r,p['methodology'])) if re.search(r'(?i)\bT-(?:DESC|COMP|CAUSAL)\b',methodology_text) else 0
         plausibility_code=verify_result_plausibility(out)
     if tier_code:
         out.setdefault('errors',[]).append({'code':'TIER_CHECK','detail':'methodology claim tier is stronger than its declared evidence'})
     if plausibility_code:
         out.setdefault('errors',[]).append({'code':'RESULT_PLAUSIBILITY','detail':'audit artifact contains unexplained implausible values'})
     live_code,live=verify_coverage_liveness(r,quiet=True)
     out.setdefault('checks_executed',[]).extend(['ACQUISITION_AUDIT','COVERAGE_LIVENESS'])
     if live_code: out.setdefault('errors',[]).append({'code':'COVERAGE_LIVENESS','detail':live.get('errors',[])})
     # v3.3.0: Verify attack registry well-formedness
     from engine.attacks import verify_attack_registry
     atk_errors = verify_attack_registry()
     if atk_errors: out.setdefault('errors',[]).append({'code':'ATTACK_REGISTRY','detail':atk_errors})
     from engine.publication import release_check
     publication=release_check(r)
     out['publication']=publication
     if publication['status']=='BLOCKED':
         out.setdefault('errors',[]).append({'code':'PUBLICATION','detail':publication['errors']})
     if publication['status'] not in ('NOT_INITIALIZED','DISTRIBUTION'):
         out.setdefault('checks_executed',[]).append('PUBLICATION')
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
     """Local signatures attest bytes under a same-user key, not isolation."""
     if out.get('errors'):
         return 'BLOCKED'
     # This execution backend cannot establish separate-identity supervision,
     # label escrow, or authenticated independent reviewer identity.
     return 'STRUCTURALLY_VALIDATED'

def _assurance_with_review(base_level, has_review):
     """A self-reported review mode cannot raise cryptographic assurance."""
     return base_level

def audit(r):
  r=root(r)
  invalidate_certificate(r)
  p=plan_at(r);out=audit_snapshot(r,p);write_json(inside(r,'project/audit_report.json'),out);print(json.dumps(out,indent=2));return 0 if not out['errors'] else EXIT_SCIENCE

def audit_snapshot(r,p):
  epoch,ep,f=active(r);out=Audit(r,p,ep,f,engine_hash()).run()
  out['epoch']=epoch;out['audit_at']=now()
  return _finalize_release_checks(r,p,out)

def release_preflight(r):
  """Run fresh behavioral checks; a persisted report is never an execution shortcut."""
  from engine.attacks import run_registered_attacks
  from run_mutation_checks import run_benchmark as mutations_benchmark
  from run_seeded_fault_benchmark import run_benchmark as seeded_benchmark
  report={'status':'RUNNING','created_at':now(),'engine_sha256':engine_hash(),
          'validation_sha256':validation_hash()}
  path=inside(r,'project/release_checks.json')
  write_json(path,report)
  captured=io.StringIO()
  with redirect_stdout(captured):coverage_code=verify_constitution_coverage(r)
  report['constitution_coverage']=json.loads(captured.getvalue())
  code=coverage_code
  if not code:
   report['registered_attacks']=run_registered_attacks()
   if report['registered_attacks'].get('status')!='PASS':code=ExitCode.RELEASE_PREFLIGHT
  if not code:
   report['mutation_benchmark']=mutations_benchmark(minimum_score=80)
   if report['mutation_benchmark'].get('status')!='PASS':code=ExitCode.RELEASE_PREFLIGHT
  if not code:
   report['seeded_fault_benchmark']=seeded_benchmark()
   if report['seeded_fault_benchmark'].get('status')!='PASS':code=ExitCode.RELEASE_PREFLIGHT
  if report['engine_sha256']!=engine_hash() or report['validation_sha256']!=validation_hash():
   report['error']='engine or validation corpus changed during preflight';code=ExitCode.RELEASE_PREFLIGHT
  report['status']='FAIL' if code else 'PASS'
  write_json(path,report)
  print(json.dumps({'check':'release_preflight','status':report['status'],
                   'checks':{name:value['status'] for name,value in report.items() if isinstance(value,dict)},
                   'report':'project/release_checks.json'}))
  return code,report

def certify(r,*,force_preflight=False):
  r=root(r)
  invalidate_certificate(r)
  checks=None
  if force_preflight:
   plan_at(r)
   code,checks=release_preflight(r)
   if code:return code
  while True:
   p=plan_at(r);out=audit_snapshot(r,p);epoch=out['epoch']
   write_json(inside(r,'project/audit_report.json'),out)
   if out['errors']:
    print(json.dumps({'status':'NOT_CERTIFIED','reason':'audit failed','errors':out['errors'],'audit_report':'project/audit_report.json'},indent=2))
    return EXIT_SCIENCE
   try:review=verify_review(r,p,out)
   except (EvidenceError,KeyError,TypeError,ValueError,AttributeError) as ex:
    print(json.dumps({'status':'NOT_CERTIFIED','reason':str(ex)},indent=2));return EXIT_REVIEW
   if p['intent']=='fixture' or p['data_origin']=='fixture':
    print(json.dumps({'status':'FIXTURE_ONLY','reason':'fixture evidence never certifies research'}));return EXIT_REVIEW
   if checks is not None:break
   code,checks=release_preflight(r)
   if code:return code
   # The preflight is intentionally expensive. Re-read project evidence and
   # review afterwards so a concurrent edit cannot inherit its earlier audit.
  if (checks.get('status')!='PASS' or checks.get('engine_sha256')!=engine_hash()
          or checks.get('validation_sha256')!=validation_hash()):
   print(json.dumps({'status':'NOT_CERTIFIED','reason':'release preflight is stale or failed'}));return ExitCode.RELEASE_PREFLIGHT
  components={'byte_integrity':'verified','execution_provenance':'local_signed_receipts_verified',
              'runtime_integrity':'recorded_same_user_runtime','evaluation_integrity':'independently_recomputed',
              'test_label_isolation':'not_enforced_workspace_readable',
              'statistical_validity':'registered_checks_passed' if out.get('comparisons') else 'not_applicable',
              'review_identity':'self_reported','not_automated':out['not_automated']}
  cert={'factory_version':VERSION,'status':'READY_FOR_HUMAN_SUBMISSION_REVIEW','issued_at':now(),
        'scope':'local evidence consistency and recorded scientific review; same-user signing does not prove authentic execution, label isolation, or scientific truth',
        'epoch':epoch,'audit_sha256':sha(r/'project/audit_report.json'),'review_sha256':sha(r/'project/review.json'),
        'checks_executed':out['checks_executed'],'diagnostics_resolved':len(out['diagnostics']),
        'not_automated':out['not_automated'],'limitations':review['limitations'],
        'review_disclosure':{k:review[k] for k in ('reviewer_model','session_id','review_mode')},
        'assurance_level':out['assurance_level'],'assurance_components':components,
        'amendments':out.get('amendments',[]),'attempts':out.get('attempts',{}),
        'holdout_reused':out.get('holdout_reused',False),'evidence_digest':out['evidence_digest'],
        'engine_sha256':engine_hash(),'validation_sha256':validation_hash(),
        'release_checks_sha256':sha(inside(r,'project/release_checks.json'))}
  write_json(inside(r,'project/RELEASE_CERTIFICATION.json'),cert)
  digest_report={'status':cert['status'],'assurance_level':cert['assurance_level'],
                 'scope':cert['scope'],'amendments':cert['amendments'],'attempts':cert['attempts'],
                 'holdout_reused':cert['holdout_reused'],'diagnostics':out['diagnostics'],
                 'comparisons':out['comparisons'],'assurance_components':components,
                 'limitations':review['limitations'],'evidence_digest':out['evidence_digest'],
                 'release_preflight':{'status':checks['status'],'report':'project/release_checks.json',
                       'sha256':cert['release_checks_sha256'],'validation_sha256':cert['validation_sha256'],
                       'scope':'fresh registered regressions and constructed QA controls; known unsupported faults remain disclosed in the report'}}
  write_json(inside(r,'project/HUMAN_EVIDENCE_DIGEST.json'),digest_report)
  print(json.dumps(cert,indent=2));return 0

def _acquisition_findings(scripts):
    paths=[]
    for x in scripts or []:
        path=Path(x)
        paths.extend(sorted(path.rglob('*.py')) if path.is_dir() else ([path] if path.suffix.lower()=='.py' else []))
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
 if not p.exists():write_json(p,{'schema_version':3,'factory_version':'3.3.0','project_id':'REPLACE_ME','profile':'binary_classification','intent':'research','data_origin':'observational','population':'REPLACE_ME','license':'REPLACE_ME','independence_rationale':'REPLACE_ME','sampling_rationale':'REPLACE_ME','cohort':'data/cohort.csv','data_provenance':'data/provenance.json','source_records':'data/source_records.csv','methodology':'project/methodology.md','dependency_lock':'source/requirements.lock','frozen_paths':['source','data','project/methodology.md'],'experiments':[],'comparisons':[],'claims':[],'analyses':{},'release_files':[],'policy':{'min_test_groups':30,'min_class_count':10,'min_seeds':5,'metric_tolerance':1e-8}})
 from engine.publication import initialize
 publication=initialize(r)
 print(json.dumps({'status':'INITIALIZED','publication':publication,'next':'Architect completes research_plan.json and methodology, then freeze'},indent=2));return 0

def verify_publication(r,refs=None,staged_only=False,commit_message=None):
 from engine.publication import check,current_refs
 try:out=check(r,refs=[] if staged_only else (refs if refs is not None else current_refs(r)),commit_message=commit_message)
 except (EvidenceError,OSError,ValueError) as error:out={'status':'BLOCKED','error':str(error)}
 print(json.dumps(out,indent=2))
 return 0 if out['status']=='PASS' else ExitCode.PUBLICATION

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
    if _depth > 100:
        raise ValidationError('artifact', 'plausibility nesting exceeds 100 levels')
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
    """Inspect metric-specific baselines, finite p-values and intervals."""
    findings = []
    name = str(e.get('metric', e.get('name', ''))).lower()
    value = _metric_value(e)
    baseline = None
    if name in ('auroc', 'auc', 'balanced_accuracy'):
        baseline = .5
    elif name in ('average_precision', 'auprc', 'precision', 'f1', 'accuracy'):
        prevalence = e.get('positive_prevalence', e.get('prevalence'))
        if type(prevalence) in (int, float) and math.isfinite(prevalence) and 0 < prevalence < 1:
            baseline = (2 * prevalence / (1 + prevalence) if name == 'f1' else
                        max(prevalence, 1 - prevalence) if name == 'accuracy' else prevalence)
        elif name == 'accuracy' and type(e.get('n_classes')) is int and e['n_classes'] > 1:
            baseline = 1 / e['n_classes']
        elif name == 'accuracy':
            # Even without prevalence, less than one half cannot beat a binary majority classifier.
            baseline = .5
    verdict = str(e.get('verdict', '')).lower()
    is_null = verdict in ('null', 'inconclusive', 'not_supported', 'not supported', 'unsupported')
    if value is not None and baseline is not None and value <= baseline and not is_null:
        findings.append(('below_chance', e))
    if e.get('p_value', e.get('p')) == 0:
        findings.append(('exact_zero_p', e))
    interval = e.get('confidence_interval', e.get('ci'))
    if isinstance(interval, list) and len(interval) == 2 and all(type(x) in (int, float) for x in interval):
        width = interval[1] - interval[0]
        n = e.get('n', e.get('sample_size', 0))
        if width <= 0 or type(n) in (int, float) and n > 0 and width < 1e-6 / max(1, math.sqrt(n)):
            findings.append(('implausibly_narrow_ci', e))
    return findings

def _metric_value(e):
    for k in ('value','metric_value','score','estimate'):
        if isinstance(e.get(k),(int,float)) and not isinstance(e.get(k),bool): return float(e[k])
    for k,v in e.items():
        if isinstance(v,(int,float)) and not isinstance(v,bool) and k.lower() in ('auroc','auc','accuracy','balanced_accuracy','f1','precision','recall'): return float(v)
    return None

def _result_findings(obj):
    entries = _flatten_entries(obj)
    findings = [finding for entry in entries for finding in _result_findings_single(entry)]
    verdicts = [str(entry['verdict']).lower() for entry in entries if entry.get('verdict') is not None]
    if len(verdicts) >= 3 and all(v in ('supported', 'confirmed', 'pass', 'passed') for v in verdicts):
        findings.append(('all_supported', {'count': len(verdicts)}))
    return findings

def _coverage_entries(path):
    """Parse the small coverage schema strictly, without accepting duplicate IDs."""
    entries = {}; current = None; seen_fields = set()
    for line_number, line in enumerate(Path(path).read_text().splitlines(), 1):
        match = re.match(r'\s{2}(C\d+):\s*$', line)
        if match:
            current = match.group(1)
            if current in entries: raise EvidenceError('duplicate coverage principle: ' + current)
            entries[current] = {}; seen_fields = set(); continue
        if current:
            match = re.match(r'\s{4}(level|mechanism|rationale_if_null|regression_tests):\s*(.*)$', line)
            if match:
                key, raw = match.groups()
                if key in seen_fields: raise EvidenceError(f'duplicate {current}.{key}')
                seen_fields.add(key)
                value = raw.strip()
                if key == 'regression_tests':
                    try: value = json.loads(value)
                    except ValueError as error: raise EvidenceError(f'{current}.regression_tests must be a JSON-compatible array') from error
                elif value in ('null', '~', ''): value = None
                elif value.startswith('"'):
                    try: value = json.loads(value)
                    except ValueError as error: raise EvidenceError(f'{current}.{key}: invalid quoted value') from error
                else: value = value.strip("'")
                entries[current][key] = value
            elif line.startswith('    ') and line.strip() and not line.lstrip().startswith('#'):
                raise EvidenceError(f'unsupported coverage field at line {line_number}')
    return entries

def _constitution_principles(path):
    out={}
    for line in Path(path).read_text(errors='replace').splitlines():
        m=re.match(r'^#\s+(C\d+)\s+—\s+(.+)$',line)
        if m: out[m.group(1)]={'title':m.group(2),'level':'A'}
    return out

def verify_constitution_coverage(r):
    """Validate coverage declarations and references; no claim of behavioral proof."""
    try:
        principles = _constitution_principles(HERE / 'constitution.md')
        entries = _coverage_entries(HERE / 'constitution_coverage.yaml')
        errors = []
        if not principles: errors.append('constitution has no active principles')
        for cid, principle in principles.items():
            entry = entries.get(cid)
            if not entry: errors.append(cid + ' missing from coverage'); continue
            if entry.get('level') != principle['level']: errors.append(cid + ' level drift')
            mechanism, rationale = entry.get('mechanism'), entry.get('rationale_if_null')
            if (mechanism is None) == (rationale is None): errors.append(cid + ' must name exactly one mechanism or limitation')
            if rationale and (not isinstance(rationale, str) or len(rationale.strip()) < 40): errors.append(cid + ' requires a specific limitation rationale')
            if mechanism:
                tests = entry.get('regression_tests')
                if not isinstance(tests, list) or not tests or any(not isinstance(test, str) or not test for test in tests):
                    errors.append(cid + ' mechanism requires named behavioral regression tests')
        if set(entries) != set(principles): errors.append('coverage IDs differ from active constitution')
        if not errors:
            _, live = verify_coverage_liveness(r, quiet=True)
            errors.extend(live.get('errors', []))
    except (EvidenceError, OSError, ValueError, TypeError) as error:
        errors = [str(error)]; entries = {}; principles = {}
    output = {'status': 'FAIL' if errors else 'PASS', 'principles_checked': len(principles),
              'mapped_mechanisms': sum(bool(entry.get('mechanism')) for entry in entries.values()),
              'documented_limitations': sum(bool(entry.get('rationale_if_null')) for entry in entries.values()),
              'scope': 'declarations, callable reachability and regression references; execute release tests for behavioral evidence'}
    if errors: output['errors'] = errors
    print(json.dumps(output, indent=2)); return EXIT_CONSTITUTION if errors else 0

def verify_training_sufficiency(path):
    """Check actual stopping evidence through the same trace validator as audit."""
    from engine.schema import validate_training_trace
    try:
        manifest = _json_load(path)
        convergence = validate_training_manifest(manifest)
        epochs = convergence['epochs_trained']
        curve = convergence.get('loss_curve')
        expect_list(curve, 'loss_curve', min_len=2)
        for i, loss in enumerate(curve):
            expect_float(loss, f'loss_curve[{i}]', minimum=0)
        policy = manifest.get('frozen_policy', convergence.get('convergence_policy'))
        if policy is None:
            policy = {'mode': 'fixed', 'min_epochs': 10, 'max_epochs': epochs,
                      'tail_window': max(2, epochs // 5), 'relative_tolerance': .001}
        expect_dict(policy, 'convergence_policy')
        early = convergence.get('early_stopping_triggered', False)
        if early != (policy.get('mode') == 'early_stopping'):
            raise ValidationError('early_stopping_triggered', 'must agree with the declared stopping policy')
        rows = [{'epoch': i, 'train_loss': loss, 'validation_loss': loss} for i, loss in enumerate(curve, 1)]
        checkpoint = convergence.get('checkpoint_epoch', min(range(len(curve)), key=curve.__getitem__) + 1)
        verified = validate_training_trace(policy, rows, epochs, checkpoint)
    except (EvidenceError, OSError, TypeError, ValueError, KeyError) as error:
        print(json.dumps({'status': 'FAIL', 'errors': [str(error)]})); return EXIT_TRAINING
    print(json.dumps({'status': 'PASS', 'epochs_trained': epochs, 'verified_policy': verified})); return 0

def verify_split_integrity(path, tier=None):
    """Validate integral binary support; free text never waives a count floor."""
    from engine.schema import validate_split_support
    try:
        manifest = _json_load(path)
        validate_split_manifest(manifest)
        if tier not in (None, 'T-DESC', 'T_DESC', 'T-COMP', 'T_COMP', 'T-CAUSAL', 'T_CAUSAL'):
            raise ValidationError('tier', 'unknown evidence tier')
        counts = manifest.get('test_label_distribution', manifest.get('label_distribution'))
        policy = manifest.get('frozen_policy', {})
        expect_dict(policy, 'frozen_policy')
        descriptive = tier in ('T-DESC', 'T_DESC')
        minimum_class = 2 if descriptive else 10
        minimum_groups = 2 if descriptive else 30
        class_floor = expect_int(policy.get('min_class_count', minimum_class), 'min_class_count', minimum=minimum_class)
        group_floor = expect_int(policy.get('min_test_groups', minimum_groups), 'min_test_groups', minimum=minimum_groups)
        groups = manifest.get('test_group_count', manifest.get('independent_group_count'))
        validate_split_support(counts, groups, min_class_count=class_floor, min_test_groups=group_floor)
        total = sum(counts.values())
        if not descriptive and total < 30:
            raise ValidationError('test_label_distribution', 'test sample size is below comparative floor 30')
        if max(counts.values()) / min(counts.values()) > 100:
            expect_str(manifest.get('imbalance_handling'), 'imbalance_handling', min_len=40)
    except (EvidenceError, OSError, TypeError, ValueError, KeyError) as error:
        print(json.dumps({'status': 'FAIL', 'errors': [str(error)]})); return EXIT_SPLIT
    print(json.dumps({'status': 'PASS', 'n': total, 'test_group_count': groups})); return 0

def verify_result_plausibility(path):
    """Inspect typed result values, then require a resolved, specific investigation."""
    try:
        obj = path if isinstance(path, (dict, list)) else _json_load(path)
        if not isinstance(obj, (dict, list)) or not obj:
            raise ValidationError('artifact', 'requires a nonempty structured result artifact')
        inspected = 0
        def validate_values(value, location='artifact'):
            nonlocal inspected
            if isinstance(value, dict):
                if any(key in value for key in ('p_value', 'p', 'confidence_interval', 'ci', 'metric')):
                    validate_plausibility_entry(value, location)
                    for key in ('p_value', 'p'):
                        if key in value: expect_float(value[key], location + '.' + key, minimum=0, maximum=1)
                    if 'metric' in value:
                        expect_str(value['metric'], location + '.metric')
                        metric_value = next((value[k] for k in ('value', 'metric_value', 'score', 'estimate') if k in value), None)
                        if metric_value is not None:
                            metric_name=value['metric'].lower()
                            if metric_name in ('auroc','auc','average_precision','auprc','accuracy','balanced_accuracy','f1','precision','recall','brier'):
                                expect_float(metric_value, location+'.value', minimum=0, maximum=1)
                            elif metric_name == 'log_loss': expect_float(metric_value, location+'.value', minimum=0)
                            else: expect_float(metric_value, location + '.value')
                    inspected += 1
                for key, child in value.items(): validate_values(child, location + '.' + str(key))
            elif isinstance(value, list):
                for index, child in enumerate(value): validate_values(child, f'{location}[{index}]')
        validate_values(obj)
        if not inspected and not isinstance(path, (dict, list)):
            raise ValidationError('artifact', 'contains no metric, p-value or confidence interval to inspect')
        findings = _result_findings(obj)
        findings += [finding for finding in _deep_result_findings(obj) if finding not in findings]
        if findings:
            note = obj.get('investigation_note') if isinstance(obj, dict) else None
            disposition = obj.get('investigation_disposition') if isinstance(obj, dict) else None
            expect_str(note, 'investigation_note', min_len=80)
            if len(set(re.findall(r'[A-Za-z0-9]+', note.lower()))) < 10:
                raise ValidationError('investigation_note', 'repetitive padding is not an investigation')
            expect_enum(disposition, {'explained', 'claim_narrowed'}, 'investigation_disposition')
            if any(kind == 'below_chance' for kind, _ in findings):
                raise ValidationError('below_chance', 'comparative support requires an explicit null/inconclusive verdict')
            print(json.dumps({'status': 'PASS_WITH_INVESTIGATION', 'findings': [kind for kind, _ in findings],
                              'note_verified': False, 'disposition': disposition})); return 0
    except (EvidenceError, OSError, TypeError, ValueError, KeyError) as error:
        print(json.dumps({'status': 'FAIL', 'error': str(error)})); return EXIT_PLAUSIBILITY
    print(json.dumps({'status': 'PASS', 'results_inspected': inspected})); return 0

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
    if pat.groups != 1:
        print(json.dumps({'status':'FAIL','error':'id pattern must contain exactly one capture group'})); return EXIT_TRACE
    wanted={m.group(1) for m in pat.finditer(text)}; found=set(); errors=[]
    if not wanted:
        print(json.dumps({'status':'FAIL','error':'no identifiers recognized; supply an explicit id pattern'})); return EXIT_TRACE
    if not sources:
        print(json.dumps({'status':'FAIL','error':'at least one source artifact is required'})); return EXIT_TRACE
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
    """Scan explicit producer paths; omitted inputs must not scan the installation."""
    if not scripts:
        print(json.dumps({'status': 'FAIL', 'error': 'declare producer scripts with --scripts'})); return ExitCode.ACQUISITION
    paths = [Path(path) for path in scripts]
    errors = [str(path) for path in paths if not path.is_file()]
    if errors:
        print(json.dumps({'status': 'FAIL', 'missing_scripts': errors})); return ExitCode.ACQUISITION
    findings = _scan_phantom_input_fabrication(paths) + _scan_undisclosed_synthetic_fallback(paths)
    failed = any(finding['severity'] == 'HARD_FAIL' for finding in findings)
    print(json.dumps({'status': 'FAIL' if failed else 'PASS', 'findings': findings,
                      'scope': 'static heuristic; semantic acquisition honesty requires review'}, indent=2)); return ExitCode.ACQUISITION if failed else 0

def tier_check(path):
    """Flag explicit positive comparative/causal wording; disclose heuristic scope."""
    text = Path(path).read_text(errors='replace')
    match = re.search(r'(?i)\b(T-(?:DESC|COMP|CAUSAL))\b', text)
    declared = match.group(1).upper() if match else 'T-DESC'
    filtered = re.sub(r'(?i)\b(?:no|without|does not|do not|not|non)[ -]+(?:causal(?: claims?| inference)?|mechanisms?|interventions?)\b', '', text)
    causal = re.search(r'(?i)\b(?:causal effect|causal identification|causally|causes|intervention effect|identified mechanism)\b', filtered)
    inferred = 'T-CAUSAL' if causal else 'T-COMP' if _TCOMP_STRONG_RE.search(filtered) or _detects_verdict_enum(filtered) else 'T-DESC'
    order = {'T-DESC': 0, 'T-COMP': 1, 'T-CAUSAL': 2}
    output = {'declared': declared, 'inferred': inferred, 'scope': 'wording heuristic; not semantic claim validation'}
    failed = order[inferred] > order[declared]
    print(json.dumps({'status': 'FAIL' if failed else 'PASS', **output})); return ExitCode.TIER if failed else 0

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
    except Exception as e: print(json.dumps({'status':'FAIL','error':str(e)})); return ExitCode.SENSITIVITY
    findings=[]; errors=[]
    entries=m.get('sweeps',m.get('entries',[])) if isinstance(m,dict) else m if isinstance(m,list) else []
    if isinstance(entries,dict): entries=[entries]
    if not isinstance(entries,list) or not entries: errors.append('manifest requires at least one sensitivity sweep'); entries=[]
    for item in entries or []:
        if not isinstance(item,dict): errors.append('each sensitivity sweep must be an object'); continue
        vals=item.get('metrics',item.get('values',[])) if isinstance(item,dict) else []
        if isinstance(vals,dict): vals=list(vals.values())
        try:
            expect_str(item.get('parameter'),'sensitivity.parameter')
            expect_list(vals,'sensitivity.metrics',min_len=3)
            expected=expect_bool(item.get('expected_flat',False),'sensitivity.expected_flat')
            if expected: expect_str(item.get('flat_rationale'),'sensitivity.flat_rationale',min_len=40)
            nums=[expect_float(v,'sensitivity.metrics') for v in vals]
            if not all(math.isfinite(v) for v in nums): raise ValueError
            if len(nums)>1 and max(nums)-min(nums)<max(.005,.01*max(abs(v) for v in nums)) and not item.get('expected_flat'): findings.append(item.get('parameter','unknown'))
        except (EvidenceError,TypeError,ValueError) as error: errors.append(str(error))
    if errors:
        print(json.dumps({'status':'FAIL','errors':errors,'flat_parameters':findings},indent=2)); return ExitCode.SENSITIVITY
    if findings: print(json.dumps({'status':'FAIL','flat_parameters':findings})); return ExitCode.SENSITIVITY
    print(json.dumps({'status':'PASS'})); return 0

def verify_statistical_protocol(path):
    """Require typed estimand, sampling scope, uncertainty and a multiplicity family."""
    try:
        obj = _json_load(path)
        expect_dict(obj, 'artifact')
        protocol = expect_dict(obj.get('statistical_protocol', obj), 'statistical_protocol')
        for key in ('primary_metric', 'sampling_unit', 'test', 'multiplicity_correction'):
            expect_str(protocol.get(key), key)
        expect_enum(protocol['test'].lower(), {'permutation','paired permutation','bootstrap','paired bootstrap','sign_flip','paired_group_permutation','paired_t','welch_t','wilcoxon','mann_whitney','delong'}, 'test')
        expect_enum(protocol['primary_metric'], {'auroc', 'average_precision', 'accuracy', 'f1', 'brier', 'log_loss'}, 'primary_metric')
        expect_enum(protocol['sampling_unit'], {'seed_fixed_test', 'item', 'group', 'site', 'subject', 'dataset'}, 'sampling_unit')
        if protocol['sampling_unit'] == 'seed_fixed_test':
            expect_enum(protocol.get('inference_scope'), {'fixed_test_corpus'}, 'inference_scope')
        expect_float(protocol.get('alpha'), 'alpha', minimum=0, maximum=.1)
        if protocol['alpha'] == 0: raise ValidationError('alpha', 'must be > 0')
        expect_float(protocol.get('effect_size'), 'effect_size')
        interval = expect_list(protocol.get('confidence_interval'), 'confidence_interval', min_len=2, max_len=2)
        for i, value in enumerate(interval): expect_float(value, f'confidence_interval[{i}]')
        if interval[0] > interval[1]: raise ValidationError('confidence_interval', 'bounds must be ordered')
        correction = protocol['multiplicity_correction'].lower()
        expect_enum(correction, {'holm', 'bonferroni', 'none'}, 'multiplicity_correction')
        values = protocol.get('p_values', [])
        expect_list(values, 'p_values')
        for i, value in enumerate(values): expect_float(value, f'p_values[{i}]', minimum=0, maximum=1)
        if len(values) > 1 and correction == 'none':
            raise ValidationError('multiplicity_correction', 'a correction is required for multiple confirmatory p-values')
        if any(value == 0 for value in values): raise ValidationError('p_values', 'finite randomization p-values cannot be exact zero')
    except (EvidenceError, OSError, TypeError, ValueError, KeyError) as error:
        print(json.dumps({'status': 'FAIL', 'error': str(error)})); return ExitCode.STATISTICAL_PROTOCOL
    print(json.dumps({'status': 'PASS', 'sampling_scope': protocol.get('inference_scope', protocol['sampling_unit'])})); return 0

def pre_submission_audit(path):
    """Check structured claim/evidence links instead of nonempty section strings."""
    try:
        obj = expect_dict(_json_load(path), 'artifact')
        def evidence_refs(references, field):
            expect_list(references, field, min_len=1)
            for reference in references:
                expected_hash=None
                if isinstance(reference,dict):
                    relative=expect_str(reference.get('path'), field+'.path')
                    expected_hash=expect_str(reference.get('sha256'), field+'.sha256')
                    if not re.fullmatch(r'[0-9a-f]{64}',expected_hash): raise ValidationError(field,'invalid SHA-256')
                else: relative=expect_str(reference,field+'.path')
                target=inside(Path(path).absolute().parent,relative)
                if not target.is_file(): raise ValidationError(field,'missing evidence: '+relative)
                if expected_hash is not None and sha(target)!=expected_hash: raise ValidationError(field,'evidence hash mismatch: '+relative)
                if target.suffix.lower()=='.json':
                    value=_json_load(target)
                    if not isinstance(value,(dict,list)) or not value: raise ValidationError(field,'vacuous JSON evidence: '+relative)
        claims = expect_list(obj.get('claims'), 'claims', min_len=1)
        ids = set()
        from engine.schema import expect_id
        for i, claim in enumerate(claims):
            expect_dict(claim, f'claims[{i}]')
            expect_id(claim.get('id'), f'claims[{i}].id', seen=ids)
            expect_str(claim.get('scope'), f'claims[{i}].scope', min_len=20)
            evidence = expect_list(claim.get('evidence'), f'claims[{i}].evidence', min_len=1)
            evidence_refs(evidence,'claim.evidence')
        for key in ('data_provenance', 'reproducibility'):
            section = expect_dict(obj.get(key), key)
            evidence_refs(section.get('evidence'),key+'.evidence')
            expect_str(section.get('assessment'), key + '.assessment', min_len=40)
        for key in ('baselines', 'ablations'):
            rows = expect_list(obj.get(key), key, min_len=1)
            for row in rows:
                expect_dict(row, key + '.entry')
                expect_str(row.get('id'), key + '.entry.id')
                expect_str(row.get('assessment'), key + '.entry.assessment', min_len=40)
                evidence_refs(row.get('evidence'),key+'.entry.evidence')
        expect_list(obj.get('limitations'), 'limitations', min_len=1,
                    element_validator=lambda value, field: expect_str(value, field, min_len=20))
    except (EvidenceError, OSError, TypeError, ValueError, KeyError) as error:
        print(json.dumps({'status': 'FAIL', 'error': str(error)})); return ExitCode.PRE_SUBMISSION
    print(json.dumps({'status': 'PASS', 'scope': 'structured readiness record; evidence semantics require human review'})); return 0

def verify_failure_taxonomy(path):
    """Require integral identifier lists and bounded, finite failure prevalence."""
    try:
        obj = expect_dict(_json_load(path), 'artifact')
        rows = expect_list(obj.get('failures', obj.get('taxonomy')), 'failures', min_len=3)
        seen = set()
        for i, row in enumerate(rows):
            expect_dict(row, f'failures[{i}]')
            category = expect_str(row.get('category'), f'failures[{i}].category')
            if category in seen: raise ValidationError('category', 'duplicate failure category: ' + category)
            seen.add(category)
            identifiers = row.get('condition_ids', row.get('candidate_ids'))
            expect_list(identifiers, f'failures[{i}].condition_ids', min_len=1, element_validator=expect_str)
            if len(set(identifiers)) != len(identifiers): raise ValidationError('condition_ids', 'duplicate identifiers')
            expect_float(row.get('prevalence', row.get('rate')), f'failures[{i}].prevalence', minimum=0, maximum=1)
            expect_enum(row.get('severity'), {'SEV-1', 'SEV-2', 'SEV-3', 'SEV-4'}, f'failures[{i}].severity')
    except (EvidenceError, OSError, TypeError, ValueError, KeyError) as error:
        print(json.dumps({'status': 'FAIL', 'error': str(error)})); return ExitCode.FAILURE_TAXONOMY
    print(json.dumps({'status': 'PASS', 'categories_checked': len(rows)})); return 0
def _live_ast_nodes(node):
    """Walk executable syntax, excluding constant-false arms and nested definitions."""
    yield node
    for child in ast.iter_child_nodes(node):
        if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            continue
        if isinstance(child, ast.If) and isinstance(child.test, ast.Constant):
            yield child.test
            for statement in child.body if child.test.value else child.orelse:
                yield from _live_ast_nodes(statement)
        else:
            yield from _live_ast_nodes(child)


def _call_graph(paths):
    """Resolve module imports and class callbacks, without suffix/attribute guesses."""
    graph = {}; definitions = {}; scopes = {}
    for path in paths:
        path = Path(path)
        try: tree = ast.parse(path.read_text(), filename=str(path))
        except (OSError, SyntaxError): continue
        module = 'gatekeeper' if path.name == 'gatekeeper.py' else 'engine.' + path.stem
        aliases = {}
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom):
                source = ('engine.' + (node.module or '')) if node.level else (node.module or '')
                for alias in node.names: aliases[alias.asname or alias.name] = source + '.' + alias.name
            elif isinstance(node, ast.Import):
                for alias in node.names: aliases[alias.asname or alias.name.split('.')[0]] = alias.name
        def collect(body, class_name=None):
            for node in body:
                if isinstance(node, ast.ClassDef): collect(node.body, node.name)
                elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    key = module + ('.' + class_name if class_name else '') + '.' + node.name
                    definitions[key] = node
                    scopes[key] = (module, class_name, aliases)
                    graph[key] = set()
        collect(tree.body)
    for key, node in definitions.items():
        module, class_name, aliases = scopes[key]
        local = dict(aliases)
        def resolve(expression):
            if isinstance(expression, ast.Name):
                if expression.id in ('self', 'cls') and class_name: return module + '.' + class_name
                return local.get(expression.id, module + '.' + expression.id)
            if isinstance(expression, ast.Attribute):
                base = resolve(expression.value)
                return base + '.' + expression.attr if base else ''
            if isinstance(expression, ast.Call): return resolve(expression.func)
            return ''
        for descendant in _live_ast_nodes(node):
            if isinstance(descendant, ast.Assign) and isinstance(descendant.value, ast.Call):
                for target in descendant.targets:
                    if isinstance(target, ast.Name): local[target.id] = resolve(descendant.value.func)
            if isinstance(descendant, ast.Call):
                target = resolve(descendant.func)
                if target in definitions: graph[key].add(target)
                # Audit.guard is the sole callback dispatcher that executes its supplied function.
                if target.endswith('.Audit.guard'):
                    for argument in descendant.args:
                        if isinstance(argument, (ast.Name, ast.Attribute)):
                            callback = resolve(argument)
                            if callback in definitions: graph[key].add(callback)
    return graph, definitions

def _is_trivial_body(node):
    """A dead branch, pass, or constant return is not a live guard."""
    for descendant in _live_ast_nodes(node):
        if isinstance(descendant, (ast.Assert, ast.Raise, ast.For, ast.While, ast.If, ast.Try)):
            return False
        if isinstance(descendant, ast.Call) and _fn_name(descendant.func).split('.')[-1] in ('need', 'error', 'diagnostic'):
            return False
    return True

def _is_substantive(target, graph, defs, seen=None):
    seen = set() if seen is None else seen
    if target in seen: return False
    seen.add(target)
    if target in defs and not _is_trivial_body(defs[target]): return True
    return any(_is_substantive(callee, graph, defs, seen) for callee in graph.get(target, set()))

def verify_coverage_liveness(r, quiet=False):
    """Check exact call resolution and named regression references, not scientific truth."""
    errors = []; resolved = {}; entries = {}
    try:
        entries = _coverage_entries(HERE / 'constitution_coverage.yaml')
        principles = _constitution_principles(HERE / 'constitution.md')
        if not principles or set(entries) != set(principles): errors.append('coverage IDs differ from the active constitution')
        for cid, entry in entries.items():
            if entry.get('level') != 'A': errors.append(cid + ' level drift')
            mechanism, rationale = entry.get('mechanism'), entry.get('rationale_if_null')
            if (mechanism is None) == (rationale is None): errors.append(cid + ' must name exactly one mechanism or limitation')
            if rationale and (not isinstance(rationale,str) or len(rationale.strip()) < 40): errors.append(cid + ' requires a specific limitation rationale')
        graph, definitions = _call_graph([HERE / 'gatekeeper.py'] + sorted((HERE / 'engine').glob('*.py')))
        reachable = set(); pending = ['gatekeeper.certify', 'gatekeeper.audit', 'gatekeeper.run_exp', 'gatekeeper.freeze', 'engine.audit.Audit.run']
        while pending:
            target = pending.pop()
            if target in reachable: continue
            reachable.add(target); pending.extend(graph.get(target, set()))
        from engine.attacks import resolve_attack_fixture
        for cid, entry in entries.items():
            mechanism = entry.get('mechanism')
            if not mechanism: continue
            target = mechanism.split('(', 1)[0].strip()
            if target.startswith('Audit.'): target = 'engine.audit.' + target
            elif not target.startswith(('engine.', 'gatekeeper.')):
                target = 'gatekeeper.' + target.replace('-', '_')
            resolved[cid] = target
            if target not in definitions: errors.append(cid + ' mechanism is not a callable: ' + target)
            elif target not in reachable: errors.append(cid + ' callable is not reached from the audit/execution roots: ' + target)
            elif not _is_substantive(target, graph, definitions): errors.append(cid + ' callable has no live validation branch: ' + target)
            tests = entry.get('regression_tests', [])
            if not isinstance(tests, list) or not tests: errors.append(cid + ' requires behavioral regression references'); continue
            for test in tests:
                try: resolve_attack_fixture(test)
                except (EvidenceError, ValueError, TypeError, ImportError, AttributeError) as error:
                    errors.append(cid + ' invalid regression: ' + str(error))
    except (EvidenceError, OSError, ValueError, TypeError) as error: errors.append(str(error))
    output = {'status': 'FAIL' if errors else 'PASS', 'principles_checked': len(entries), 'callables_resolved': len(resolved),
              'scope': 'static reachability and regression references; execute tests to establish observed enforcement'}
    if errors: output['errors'] = errors
    if not quiet: print(json.dumps(output, indent=2))
    return (40 if errors else 0), output

def check_contract(path):
    """Validate a real structured contract; prose mentioning check names is insufficient."""
    try: obj=_json_load(path)
    except Exception as e: print(json.dumps({'status':'FAIL','error':'contract must be strict JSON with executable checks: '+str(e)})); return ExitCode.CONTRACT
    if not isinstance(obj,dict) or not isinstance(obj.get('checks'),list) or not obj['checks']: print(json.dumps({'status':'FAIL','error':'contract requires a checks array'})); return ExitCode.CONTRACT
    errors=[]; allowed={'audit','certify','verify-constitution-coverage','verify-training-sufficiency','verify-split-integrity','verify-result-plausibility','verify-cross-artifact-traceability','verify-reproducibility','acquisition-audit','tier-check','verify-sensitivity-analysis','verify-statistical-protocol','pre-submission-audit','verify-failure-taxonomy','verify-publication'}
    for i,c in enumerate(obj['checks']):
        if not isinstance(c,dict): errors.append(f'check {i} must be an object'); continue
        if c.get('command') not in allowed: errors.append(f'check {i} has no registered executable command')
        if not isinstance(c.get('artifacts'),list) or not c['artifacts'] or any(not isinstance(a,str) or not a.strip() for a in c['artifacts']): errors.append(f'check {i} must bind artifacts')
    if errors: print(json.dumps({'status':'FAIL','errors':errors},indent=2)); return ExitCode.CONTRACT
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
 for rel in ('project/review.json','project/RELEASE_CERTIFICATION.json','project/HUMAN_EVIDENCE_DIGEST.json','project/release_checks.json'):
  if inside(r,rel).is_file():files.add(rel)
 paths={rel:inside(r,rel) for rel in files}
 paths.update({'factory/'+str(path.relative_to(HERE)):path for path in active_engine_files()})
 if (HERE.parent/'LICENSE').is_file():paths['LICENSE']=HERE.parent/'LICENSE'
 dest=inside(r,'TAKE_THIS');dest.mkdir(exist_ok=True)
 name=inside(r,'TAKE_THIS/review_bundle_'+out['evidence_digest'][:12]+'.zip')
 create_bundle(name,paths,{'factory_version':VERSION,'evidence_digest':out['evidence_digest'],
                         'assurance_level':out['assurance_level'],
                         'release_status':'READY_FOR_HUMAN_SUBMISSION_REVIEW' if certified else 'NOT_CERTIFIED'},sign_manifest=True)
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
  if cert.get('validation_sha256')!=validation_hash():return False
  if cert.get('release_checks_sha256')!=sha(inside(r,'project/release_checks.json')):return False
  checks=read_json(inside(r,'project/release_checks.json'))
  if (checks.get('status')!='PASS' or checks.get('engine_sha256')!=engine_hash()
          or checks.get('validation_sha256')!=validation_hash()):return False
  if cert.get('audit_sha256')!=sha(inside(r,'project/audit_report.json')):return False
  if cert.get('review_sha256')!=sha(inside(r,'project/review.json')):return False
  verify_review(r,p,out)
  return True
 except (EvidenceError,OSError,KeyError,TypeError,AttributeError):return False

def verify_handoff(path,public_key=None):
 from engine.bundle import verify_bundle
 manifest=verify_bundle(path,public_key_path=public_key)
 print(json.dumps({'status':'BUNDLE_INTEGRITY_VERIFIED','files':len(manifest['files']),
                   'release_status':manifest.get('release_status') if manifest.get('manifest_signature_verified') else 'UNVERIFIED_METADATA',
                   'assurance_level':manifest.get('assurance_level') if manifest.get('manifest_signature_verified') else 'UNVERIFIED_METADATA',
                   'manifest_signature_verified':manifest.get('manifest_signature_verified',False),
                   'scope':manifest.get('verification_scope','membership and byte integrity; externally pinned key needed for authenticity')}))
 return 0

def main(argv=None):
 ap=argparse.ArgumentParser();sub=ap.add_subparsers(dest='cmd',required=True)
 sub.add_parser('init').add_argument('project',nargs='?',default='.')
 x=sub.add_parser('freeze');x.add_argument('project',nargs='?',default='.');x.add_argument('--amendment')
 x=sub.add_parser('run');x.add_argument('project');x.add_argument('experiment')
 x=sub.add_parser('record');x.add_argument('project');x.add_argument('experiment');x.add_argument('run_dir')
 x=sub.add_parser('verify-bundle');x.add_argument('archive');x.add_argument('--public-key')
 x=sub.add_parser('verify-publication');x.add_argument('project',nargs='?',default='.');x.add_argument('--ref',action='append');x.add_argument('--staged-only',action='store_true');x.add_argument('--commit-message')
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
 captured=io.StringIO()
 try:
  with redirect_stdout(captured):
   if a.cmd in {'init','freeze','run','record','audit','certify','status','handoff','release-certify','verify-publication'}:
    with workspace_lock(r):code=_dispatch(a,r)
   else:code=_dispatch(a,r)
 except Exception as ex:
  code=EXIT_EVIDENCE
  captured=io.StringIO(json.dumps({'status':'BLOCKED','error':str(ex),'error_type':type(ex).__name__,'code':code}))
 text=captured.getvalue().strip();values=[];decoder=json.JSONDecoder()
 while text:
  try:value,end=decoder.raw_decode(text)
  except ValueError:
   values.append({'output':text});break
  values.append(value);text=text[end:].lstrip()
 output=values[0] if len(values)==1 else {'status':'PASS' if code==0 else 'BLOCKED','results':values}
 print(json.dumps(output,indent=2));return code

def _dispatch(a,r):
 try:
  if a.cmd=='init':return init(r)
  if a.cmd=='verify-publication':return verify_publication(r,a.ref,a.staged_only,a.commit_message)
  if a.cmd=='verify-bundle':return verify_handoff(a.archive,a.public_key)
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
   return certify(r,force_preflight=True)
  if a.cmd=='self-check':
   code=verify_constitution_coverage(r); print(json.dumps({'status':'DIAGNOSTIC' if code==0 else 'BLOCKED','version':VERSION})); return code
  return certify(r)
 except Exception as e:
  code=ExitCode.RELEASE_PREFLIGHT if a.cmd in ('certify','release-certify') and 'missing project/research_plan.json' in str(e) else EXIT_EVIDENCE
  print(json.dumps({'status':'NOT_CERTIFIED','error':str(e),'code':code},indent=2));return code
if __name__=='__main__':
 sys.exit(main())
