"""Project publication boundaries over actual Git blobs, refs and messages.

Internal evidence stays local. Public files describe the project and preserve
scientific provenance and required licensing, rather than narrating tooling.
Local hooks are guardrails, not an authentication or server enforcement boundary.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import shlex
import shutil
import subprocess
import sys

if __package__ in (None, ''):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    from engine.io import EvidenceError, inside, read_json, write_json
else:
    from .io import EvidenceError, inside, read_json, write_json

POLICY = 'project/.factory/publication_policy.json'
REPORT = 'project/.factory/publication_report.json'
HOOKS = ('pre-commit', 'commit-msg', 'pre-push')
DEFAULT_DIRS = ['source','src','app','lib','include','tests','docs','scripts','examples',
                'data','assets','figures','results','notebooks','configs','web','public',
                'components','packages','.github']
DEFAULT_FILES = ['.gitignore','.gitattributes','.gitmodules','.editorconfig',
                 'README','README.md','README.rst','LICENSE','LICENSE.md','LICENSE.txt',
                 'NOTICE','CITATION.cff','CHANGELOG.md','CONTRIBUTING.md','SECURITY.md',
                 'pyproject.toml','requirements.txt','requirements.lock',
                 'requirements-dev.txt','environment.yml','environment.yaml',
                 'setup.py','setup.cfg','MANIFEST.in','Makefile','Dockerfile',
                 'compose.yml','docker-compose.yml','package.json','package-lock.json',
                 'pnpm-lock.yaml','yarn.lock','tsconfig.json','Cargo.toml','Cargo.lock',
                 'go.mod','go.sum','pom.xml','build.gradle','pytest.ini','tox.ini',
                 '.pre-commit-config.yaml','index.html']
PRIVATE_DIRS = {'factory','project','DROP_HERE','TAKE_THIS','.factory','.codex','.agents',
                '.aws','.ssh','.secrets'}
LOCAL_DIRS = {'__pycache__','.pytest_cache','.mypy_cache','.ruff_cache','.cache',
              '.venv','venv','node_modules','.ipynb_checkpoints','__MACOSX'}
PRIVATE_NAMES = {'AGENTS.md','ClaudeInitialization.md','architect_spec.md',
                 'implementor_spec.md','gatekeeper_spec.md','factory_spec.md',
                 'constitution_coverage.yaml','dynamic_rules.md','bootstrap_manifest.yaml',
                 'RELEASE_CERTIFICATION.json','HUMAN_EVIDENCE_DIGEST.json',
                 'execution_ledger.json','research_plan_snapshot.json'}
PRIVATE_NAMES.update({'AGENT_WORKFLOW.md','PUBLICATION_POLICY.md','SCIENCE_PROTOCOL.md',
                      'SCIENTIFIC_CHECKS.md','domain_checklists.md','constitution.md'})
CONTENT_RULES = {
    'INTERNAL_FRAMEWORK': re.compile(r'(?i)\b(?:AI\s+)?software[-_ ]factory\b|\b(?:factory_version|FACTORY_RUN_DIR|FACTORY_SEED|FACTORY_EXPERIMENT_ID|supervisor_receipt)\b|(?:^|[\s"\x27(/])(?:factory/|\.factory/)|\bgatekeeper\.py\b'),
    'INTERNAL_PROCEDURE': re.compile(r'(?i)\b(?:constitution_coverage\.yaml|dynamic_rules\.md|architect_spec\.md|implementor_spec\.md|gatekeeper_spec\.md|factory_spec\.md|RELEASE_CERTIFICATION\.json|HUMAN_EVIDENCE_DIGEST\.json)\b|\b(?:Architect|Implementor)\s+(?:handoff|agent|instructions?|prompt)\b'),
    'TOOL_NARRATION': re.compile(r'(?im)\bas an AI(?:\s+(?:language model|assistant))?\b|\b(?:generated|written|implemented|assisted) by (?:ChatGPT|Claude|Codex|GitHub Copilot|an AI agent)\b|\b(?:passed|satisf(?:y|ied)) (?:the )?(?:factory|gatekeeper) (?:gate|rules?|checks?)\b|^(?:co-authored-by|signed-off-by):\s*(?:ChatGPT|Claude|Codex|GitHub Copilot)\b|\b(?:ChatGPT|Claude|Codex)\s+(?:suggested|implemented|wrote|reviewed|session|prompt|handoff)\b'),
    'LOCAL_HOST_PATH': re.compile(r'/(?:Users|home)/[^/\s]+/|[A-Za-z]:\\Users\\[^\\\s]+\\'),
    'PRIVATE_KEY': re.compile(r'-----BEGIN (?:[A-Z]+ )?PRIVATE KEY-----'),
    'ACCESS_TOKEN': re.compile(r'\bgh[pousr]_[A-Za-z0-9_]{30,}\b|\bgithub_pat_[A-Za-z0-9_]{40,}\b|\bAKIA[0-9A-Z]{16}\b'),
    'CREDENTIAL_URL': re.compile(r'https?://[^\s/@:]+:[^\s/@]+@'),
}
CONTENT_RULES['INTERNAL_PROCEDURE']=re.compile(CONTENT_RULES['INTERNAL_PROCEDURE'].pattern+
    '|\\b(?:'+ '|'.join(re.escape(name) for name in sorted(PRIVATE_NAMES))+')\\b|\\b(?:DROP_HERE|TAKE_THIS)\\b|'
    'project/(?:research_plan\\.json|methodology\\.md|review\\.json|audit_report\\.json)',re.I)
ARCHIVE_SUFFIXES = ('.zip','.tar','.tgz','.tar.gz','.tar.bz2','.tar.xz','.7z','.rar')
BINARY_SUFFIXES = {'.png','.jpg','.jpeg','.gif','.webp','.ico','.pdf','.woff','.woff2',
                   '.ttf','.otf','.mp4','.webm','.wav','.mp3','.parquet','.npy','.npz',
                   '.pt','.pth','.onnx','.safetensors','.bin'}
MANAGED_BEGIN = '# Published project files'
MANAGED_END = '# End published project files'


def _git(root, *args, data=None, acceptable=(0,)):
    environment = os.environ.copy()
    # Keep Git's temporary commit index (e.g. commit --only), but prevent an
    # unrelated inherited repository/worktree from redirecting these checks.
    for key in ('GIT_DIR','GIT_WORK_TREE','GIT_COMMON_DIR','GIT_OBJECT_DIRECTORY',
                'GIT_ALTERNATE_OBJECT_DIRECTORIES','GIT_NAMESPACE','GIT_PREFIX'):
        environment.pop(key, None)
    result = subprocess.run(['git','-C',str(root),*args],input=data,
                            stdout=subprocess.PIPE,stderr=subprocess.PIPE,
                            env=environment,timeout=60)
    if result.returncode not in acceptable:
        raise EvidenceError('Git operation failed: '+result.stderr.decode('utf-8','replace').strip())
    return result.stdout


def repository_root(root):
    top = _git(root,'rev-parse','--show-toplevel').decode().strip()
    if Path(top).resolve()!=Path(root).resolve():
        raise EvidenceError('publication workspace must be the Git repository root')
    return Path(top)


def is_distribution(root):
    root = Path(root)
    if not (root/'bootstrap.sh').is_file() or not (root/'factory/VERSION').is_file():return False
    try:
        version=(root/'factory/VERSION').read_text().strip()
        title=(root/'README.md').read_text(errors='replace').splitlines()[0]
    except (OSError,IndexError):return False
    return title=='# Software Factory '+version


def _validate_policy(policy):
    if not isinstance(policy,dict) or type(policy.get('schema_version')) is not int or policy['schema_version']!=1:
        raise EvidenceError('invalid local publication policy')
    for field in ('public_directories','public_files'):
        values=policy.get(field)
        if not isinstance(values,list) or any(not isinstance(x,str) or not x or
                str(PurePosixPath(x))!=x or '/' in x or x in ('.','..') or
                any(char.isspace() for char in x) or
                any(c in x for c in '\\\x00\n\r*?![]') for x in values):
            raise EvidenceError(field+' must contain plain root names')
        if {value.casefold() for value in values}&{name.casefold() for name in PRIVATE_DIRS|PRIVATE_NAMES|LOCAL_DIRS}:
            raise EvidenceError('internal paths cannot be public')
        if len(set(values))!=len(values):raise EvidenceError('duplicate publication path')
    if '.gitignore' not in policy['public_files']:raise EvidenceError('public .gitignore required')
    for field in ('max_text_bytes','max_blob_bytes','max_commits','max_files'):
        if type(policy.get(field)) is not int or policy[field]<1:raise EvidenceError('invalid '+field)
    approvals=policy.get('approved_binary_artifacts',{})
    if not isinstance(approvals,dict):raise EvidenceError('binary approvals must be an object')
    for name,entry in approvals.items():
        if (not isinstance(name,str) or not isinstance(entry,dict) or
                not _allowed_path(name,policy) or not isinstance(entry.get('sha256'),str) or
                not re.fullmatch('[0-9a-f]{64}',entry.get('sha256','')) or
                not isinstance(entry.get('reason'),str) or len(entry['reason'].strip())<20):
            raise EvidenceError('binary approval requires path, SHA-256 and specific review reason')
    previous=policy.get('previous_hooks',{})
    if not isinstance(previous,dict) or any(name not in HOOKS or not isinstance(path,str) or
            not Path(path).is_absolute() for name,path in previous.items()):
        raise EvidenceError('invalid previous hook configuration')
    return policy


def load_policy(root):
    return _validate_policy(read_json(inside(root,POLICY)))


def _default_policy():
    return {'schema_version':1,'public_directories':DEFAULT_DIRS.copy(),
            'public_files':DEFAULT_FILES.copy(),'max_text_bytes':8*1024**2,
            'max_blob_bytes':100*1024**2,'max_commits':10000,'max_files':100000,
            'approved_binary_artifacts':{},'previous_hooks':{}}


def public_ignore(policy):
    lines=[MANAGED_BEGIN,'/*']
    lines += ['!/'+name for name in policy['public_files']]
    # The root-only ignore needs only its directory reopened. A recursive
    # unignore would override nested private exclusions in Git's info/exclude.
    for name in policy['public_directories']:lines += ['!/'+name+'/']
    lines += ['# Local configuration, caches and build output',
              '**/.env','**/.env.*','!**/.env.example','!**/.env.sample',
              '**/__pycache__/','**/*.py[cod]','**/.pytest_cache/','**/.mypy_cache/',
              '**/.ruff_cache/','**/.DS_Store','**/node_modules/','**/.venv/',
              '**/venv/','**/.cache/','**/.ipynb_checkpoints/',
              '**/dist/','**/build/','**/*.egg-info/',MANAGED_END]
    return '\n'.join(lines)+'\n'


def _text_findings(text,path):
    findings=[]
    for code,expression in CONTENT_RULES.items():
        for match in expression.finditer(text):
            findings.append({'code':code,'path':path,'line':text.count('\n',0,match.start())+1})
            if len(findings)>=100:return findings
    return findings


def _safe_location(name):
    if any(CONTENT_RULES[code].search(name) for code in ('ACCESS_TOKEN','PRIVATE_KEY','CREDENTIAL_URL','LOCAL_HOST_PATH')):
        return 'redacted location sha256:'+hashlib.sha256(name.encode('utf-8','surrogateescape')).hexdigest()
    return name


def _managed_gitignore(root,policy):
    path=inside(root,'.gitignore')
    original=path.read_text(encoding='utf-8') if path.exists() else ''
    if MANAGED_BEGIN in original:
        if original.count(MANAGED_BEGIN)!=1 or original.count(MANAGED_END)!=1:
            raise EvidenceError('ambiguous managed .gitignore section')
        before,after=original.split(MANAGED_BEGIN,1)
        _,after=after.split(MANAGED_END,1)
        original=before+after.lstrip('\n')
    # Legacy internal ignore lines move to the private Git exclude file. The
    # public allowlist already excludes these roots without naming the framework.
    kept=[];moved=[]
    for line in original.splitlines():
        names=set(line.strip().lstrip('!').strip('/').split('/'))
        if _text_findings(line,'.gitignore') or names & (PRIVATE_NAMES|PRIVATE_DIRS):
            moved.append(line)
        else:kept.append(line)
    prefix='\n'.join(kept).strip()
    path.write_text(public_ignore(policy)+('\n'+prefix+'\n' if prefix else ''),encoding='utf-8')
    return moved


def _hook_path(root):
    value=_git(root,'rev-parse','--git-path','hooks').decode().strip()
    path=Path(value)
    return path if path.is_absolute() else Path(root)/path


def initialize(root, *, create_repository=True):
    """Install neutral public ignore rules and private, chained Git hooks."""
    root=Path(root).absolute()
    if is_distribution(root):return {'status':'DISTRIBUTION','scope':'project publication rules apply to bootstrapped projects'}
    if shutil.which('git') is None:raise EvidenceError('Git is required for project publication safeguards')
    try:repository_root(root)
    except EvidenceError:
        # Never turn a directory inside another repository into its parent repo.
        detected=_git(root,'rev-parse','--show-toplevel',acceptable=(0,128))
        if detected:raise EvidenceError('initialize publication at the Git root, not in a nested project')
        if not create_repository:raise
        _git(root,'init')
        repository_root(root)
    git_dir=Path(_git(root,'rev-parse','--absolute-git-dir').decode().strip()).resolve()
    common=Path(_git(root,'rev-parse','--git-common-dir').decode().strip())
    common=(common if common.is_absolute() else root/common).resolve()
    worktree_config=_git(root,'config','--bool','--get','extensions.worktreeConfig',acceptable=(0,1)).strip()==b'true'
    if git_dir!=common and not worktree_config:
        raise EvidenceError('linked worktree requires extensions.worktreeConfig=true before installing independent hooks; shared hook configuration was not changed')
    path=inside(root,POLICY)
    policy=load_policy(root) if path.exists() else _default_policy()
    hooks=inside(root,'project/.factory/hooks');hooks.mkdir(parents=True,exist_ok=True)
    old_hooks=_hook_path(root)
    if old_hooks.resolve()!=hooks.resolve():
        policy['previous_hooks']={name:str((old_hooks/name).absolute()) for name in HOOKS if (old_hooks/name).is_file()}
    moved=_managed_gitignore(root,policy)
    excludes=_git(root,'rev-parse','--git-path','info/exclude').decode().strip()
    excludes=Path(excludes) if Path(excludes).is_absolute() else root/excludes
    old=excludes.read_text(encoding='utf-8') if excludes.exists() else ''
    required=['**/'+name+'/' for name in sorted(PRIVATE_DIRS|LOCAL_DIRS)]+['**/'+name for name in sorted(PRIVATE_NAMES)]+moved
    added=[line for line in required if line not in old.splitlines()]
    if added:
        excludes.parent.mkdir(parents=True,exist_ok=True)
        excludes.write_text(old.rstrip('\n')+'\n'+'\n'.join(added)+'\n',encoding='utf-8')
    script=Path(__file__).resolve()
    for name in HOOKS:
        hook=inside(root,'project/.factory/hooks/'+name)
        hook.write_text('#!/bin/sh\nexec '+shlex.quote(sys.executable)+' -B '+shlex.quote(str(script))+
                        ' hook '+shlex.quote(name)+' "$@"\n',encoding='utf-8')
        hook.chmod(0o700)
    write_json(path,policy)
    _git(root,'config','--worktree' if worktree_config else '--local','core.hooksPath','project/.factory/hooks')
    return {'status':'INSTALLED','hooks':list(HOOKS),'policy':POLICY}


def _private_path(name):
    parts=PurePosixPath(name).parts
    if (not parts or name.startswith('/') or '..' in parts or '\\' in name or '\x00' in name or
            any(ord(char)<32 or ord(char)==127 for char in name) or str(PurePosixPath(name))!=name):return True
    lowered=[part.casefold() for part in parts]
    private={value.casefold() for value in PRIVATE_DIRS|LOCAL_DIRS|PRIVATE_NAMES}
    return bool(set(lowered)&private or '.git' in lowered or
                lowered[-1]=='.ds_store' or lowered[-1].endswith(('.pyc','.pyo','.swp','.swo','.tmp')) or
                any(part=='.env' or part.startswith('.env.') and part not in ('.env.example','.env.sample') for part in lowered) or
                any(part.startswith('review_bundle_') for part in lowered))


def _allowed_path(name,policy):
    parts=PurePosixPath(name).parts
    return not _private_path(name) and (name in policy['public_files'] or
                                      len(parts)>1 and parts[0] in policy['public_directories'])


def _blob(root,oid,policy):
    size=int(_git(root,'cat-file','-s',oid))
    if size>policy['max_blob_bytes']:raise EvidenceError('public blob exceeds configured byte limit')
    return _git(root,'cat-file','blob',oid)


def _content(root,path,oid,policy,cache):
    if oid not in cache:
        try:
            raw=_blob(root,oid,policy)
            # Bound memory across a long history, including large reviewed assets.
            if sum(map(len,cache.values()))+len(raw)>16*1024**2:cache.clear()
            cache[oid]=raw
        except EvidenceError as error:return [{'code':'UNINSPECTED_BLOB','path':path,'detail':str(error)}]
    raw=cache[oid]
    try:text=raw.decode('utf-8')
    except UnicodeDecodeError:text=None
    archive=path.lower().endswith(ARCHIVE_SUFFIXES) or raw.startswith((b'PK\x03\x04',b'PK\x05\x06',b'PK\x07\x08',
            b'7z\xbc\xaf\x27\x1c',b'Rar!',b'\x1f\x8b',b'BZh',b'\xfd7zXZ\x00')) or raw[257:263] in (b'ustar\x00',b'ustar ')
    if archive:
        return [{'code':'PUBLIC_ARCHIVE','path':path,'detail':'archives can carry internal files; publish inspected project files instead'}]
    if text is not None and '\x00' not in text:
        if len(raw)>policy['max_text_bytes']:return [{'code':'UNINSPECTED_TEXT','path':path}]
        if text.startswith('version https://git-lfs.github.com/spec/v1\n'):
            return [{'code':'UNINSPECTED_EXTERNAL_ARTIFACT','path':path,'detail':'LFS content is outside the inspected Git blobs'}]
        return _text_findings(text,path)
    metadata=_text_findings(raw.decode('utf-8','replace'),path)
    if metadata:return metadata
    if PurePosixPath(path).suffix.lower() not in BINARY_SUFFIXES:
        return [{'code':'UNREVIEWED_BINARY','path':path}]
    approval=policy['approved_binary_artifacts'].get(path)
    if not approval or hashlib.sha256(raw).hexdigest()!=approval['sha256']:
        return [{'code':'UNREVIEWED_BINARY','path':path,'detail':'binary artifacts need a local path/hash/reason approval'}]
    return []


def _entries(root,ref=None):
    if ref is None:
        data=_git(root,'ls-files','--stage','-z')
        for record in data.split(b'\x00'):
            if not record:continue
            metadata,path=record.split(b'\t',1);mode,oid,stage=metadata.decode().split()
            yield mode,oid,path.decode('utf-8','surrogateescape'),stage
    else:
        data=_git(root,'ls-tree','-r','-z',ref)
        for record in data.split(b'\x00'):
            if not record:continue
            metadata,path=record.split(b'\t',1);mode,kind,oid=metadata.decode().split()
            yield mode,oid,path.decode('utf-8','surrogateescape'),'0'


def _ignore_checks(root,policy):
    private=['factory/gatekeeper.py','project/research_plan.json','TAKE_THIS/review_bundle.zip',
             'DROP_HERE/input.zip','.codex/config.toml','AGENTS.md','source/.factory/state.json',
             'source/factory/gatekeeper.py','docs/project/review.json','src/.aws/credentials']
    output=_git(root,'check-ignore','--no-index','-z','--stdin',data=('\x00'.join(private)+'\x00').encode(),acceptable=(0,1))
    ignored=set(output.decode().split('\x00'))
    errors=[{'code':'IGNORE_GAP','path':name} for name in private if name not in ignored]
    if _hook_path(root).resolve()!=inside(root,'project/.factory/hooks').resolve():
        errors.append({'code':'HOOKS_NOT_INSTALLED','detail':'run init to install publication hooks'})
    for name in HOOKS:
        hook=inside(root,'project/.factory/hooks/'+name)
        expected=' hook '+shlex.quote(name)+' "$@"'
        if not hook.is_file() or not os.access(hook,os.X_OK) or expected not in hook.read_text():
            errors.append({'code':'HOOKS_NOT_INSTALLED','path':name})
    return errors


def _ref_findings(ref):
    name=ref.removeprefix('refs/heads/').removeprefix('refs/tags/')
    return _text_findings(ref,'Git ref')+([{'code':'INTERNAL_REF_NAME','path':_safe_location(ref)}]
        if re.search(r'(?i)(?:^|/)(?:codex|claude|factory|architect|implementor)(?:$|/|[-_])',name) else [])


def check(root, *, refs=None, staged=True, commit_message=None):
    """Read the index and all reachable published commits; never inspect unstaged substitutes."""
    root=Path(root).absolute();repository_root(root);policy=load_policy(root)
    errors=_ignore_checks(root,policy);cache={};checked=0;commits=[]
    branch=_git(root,'symbolic-ref','--quiet','HEAD',acceptable=(0,1)).decode().strip()
    if branch:errors.extend(_ref_findings(branch))
    def tree(ref):
        nonlocal checked
        entries=list(_entries(root,ref))
        if len(entries)>policy['max_files']:raise EvidenceError('publication file count exceeds configured limit')
        for mode,oid,path,stage in entries:
            checked+=1
            found=[]
            if stage!='0':found=[{'code':'UNMERGED_INDEX','path':path}]
            elif not _allowed_path(path,policy):found=[{'code':'NON_PROJECT_PATH','path':path}]
            elif mode not in ('100644','100755'):found=[{'code':'UNINSPECTED_LINK','path':path}]
            else:found=_text_findings(path,path)+_content(root,path,oid,policy,cache)
            if ref:
                for item in found:item['commit']=ref
            errors.extend(found)
    if staged:tree(None)
    if commit_message is not None:
        text=Path(commit_message).read_text(encoding='utf-8')
        errors.extend(_text_findings(text,'commit message'))
        if not text.strip():errors.append({'code':'EMPTY_COMMIT_MESSAGE','path':'commit message'})
    for ref in refs or []:
        if not isinstance(ref,str) or not ref or ref.startswith('-'):
            raise EvidenceError('invalid publication ref')
        errors.extend(_ref_findings(ref))
        oid=_git(root,'rev-parse','--verify','--end-of-options',ref+'^{object}').decode().strip()
        # Annotated tag messages are public even when their target commit is clean.
        tag_depth=0
        while _git(root,'cat-file','-t',oid).strip()==b'tag':
            tag_depth+=1
            if tag_depth>32:raise EvidenceError('publication tag nesting exceeds limit')
            size=int(_git(root,'cat-file','-s',oid))
            if size>policy['max_text_bytes']:raise EvidenceError('publication tag exceeds text limit')
            tag=_git(root,'cat-file','tag',oid).decode('utf-8','strict')
            errors.extend(_text_findings(tag,'tag message'))
            oid=tag.splitlines()[0].removeprefix('object ')
            if not re.fullmatch('[0-9a-f]{40}|[0-9a-f]{64}',oid):raise EvidenceError('invalid tag target')
        if _git(root,'cat-file','-t',oid).strip()!=b'commit':
            errors.append({'code':'UNINSPECTED_REF','path':ref});continue
        commits+=_git(root,'rev-list','--max-count='+str(policy['max_commits']+1),oid,'--').decode().splitlines()
    commits=list(dict.fromkeys(commits))
    if len(commits)>policy['max_commits']:raise EvidenceError('publication history exceeds configured limit')
    for commit in commits:
        tree(commit)
        if len(errors)>1000:raise EvidenceError('publication finding limit exceeded; resolve reported content before continuing')
        if int(_git(root,'cat-file','-s',commit))>policy['max_text_bytes']:
            raise EvidenceError('commit metadata exceeds text limit')
        metadata,_,message=_git(root,'cat-file','commit',commit).decode('utf-8','replace').partition('\n\n')
        found=_text_findings(message,'commit message')+_text_findings(metadata,'commit metadata')
        for item in found:item['commit']=commit
        errors.extend(found)
    # Findings contain locations/rules, never secret bytes or the full messages.
    for entry in errors:
        if 'path' in entry:entry['path']=_safe_location(entry['path'])
    report={'status':'PASS' if not errors else 'BLOCKED','errors':errors,
            'files_checked':checked,'cached_blobs':len(cache),'commits_checked':len(commits),
            'scope':'public allowlist, staged/committed bytes, internal references, credential markers, refs and messages; binary identity by local review'}
    write_json(inside(root,REPORT),report)
    return report


def current_refs(root):
    refs=_git(root,'symbolic-ref','--quiet','HEAD',acceptable=(0,1)).decode().strip()
    exists=_git(root,'rev-parse','--verify','HEAD',acceptable=(0,128)).decode().strip()
    return [refs or exists] if exists else []


def release_check(root):
    """Check current publication candidates when Git is present at this root."""
    if is_distribution(root):return {'status':'DISTRIBUTION','errors':[]}
    detected=_git(root,'rev-parse','--show-toplevel',acceptable=(0,128)).decode().strip()
    if not detected:return {'status':'NOT_INITIALIZED','errors':[]}
    if Path(detected).resolve()!=Path(root).resolve():
        return {'status':'BLOCKED','errors':[{'code':'NESTED_REPOSITORY'}]}
    try:return check(root,refs=current_refs(root))
    except (EvidenceError,OSError,ValueError) as error:
        return {'status':'BLOCKED','errors':[{'code':'PUBLICATION_CONFIGURATION','detail':str(error)}]}


def hook(name,args):
    root=Path.cwd();repository_root(root);policy=load_policy(root)
    data=sys.stdin.buffer.read() if name=='pre-push' else None
    previous=policy.get('previous_hooks',{}).get(name)
    def prior():
        if previous and Path(previous).is_file() and os.access(previous,os.X_OK):
            return subprocess.run([previous,*args],cwd=root,input=data).returncode
        return 0
    # Earlier pre-push hooks may upload LFS objects. Inspect first so a rejected
    # push cannot leak artifacts through a chained uploader before Git is blocked.
    if name!='pre-push':
        code=prior()
        if code:return code
    if name=='pre-commit':report=check(root,staged=True)
    elif name=='commit-msg':
        if len(args)!=1:raise EvidenceError('commit-msg hook requires its message path')
        report=check(root,staged=True,commit_message=args[0])
    elif name=='pre-push':
        refs=[]
        for line in data.decode('utf-8').splitlines():
            fields=line.split()
            if len(fields)!=4:raise EvidenceError('invalid pre-push ref update')
            local,oid,remote,remote_oid=fields
            if set(oid)=={'0'}:continue
            if not re.fullmatch('[0-9a-f]{40}|[0-9a-f]{64}',oid):raise EvidenceError('invalid push object identity')
            refs.append(oid)
            # Both exposed branch/tag names and their exact immutable object matter.
            errors=_ref_findings(local)+_ref_findings(remote)
            if errors:
                print(json.dumps({'status':'BLOCKED','errors':errors}),file=sys.stderr);return 44
        report=check(root,refs=refs,staged=False)
    else:raise EvidenceError('unsupported publication hook')
    if report['errors']:
        print(json.dumps(report,indent=2),file=sys.stderr);return 44
    return prior() if name=='pre-push' else 0


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    sub=parser.add_subparsers(dest='command',required=True)
    action=sub.add_parser('hook');action.add_argument('name',choices=HOOKS);action.add_argument('args',nargs='*')
    args=parser.parse_args()
    try:return hook(args.name,args.args)
    except (EvidenceError,OSError,ValueError) as error:
        print(json.dumps({'status':'BLOCKED','error':str(error)}),file=sys.stderr);return 44

if __name__=='__main__':raise SystemExit(main())
