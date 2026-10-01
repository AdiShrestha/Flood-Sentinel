"""Record actual engineering checks, not research executions or experiment receipts."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import platform
import subprocess
import sys
import tempfile
import time


def main():
    p=argparse.ArgumentParser(); p.add_argument('suite',choices=('engine','factory'))
    args=p.parse_args(); root=Path(__file__).resolve().parents[3]; dest=Path(__file__).parent
    prior=list(dest.glob(args.suite+'_run*.json')); stem=f'{args.suite}_run{len(prior)+1:02d}'
    command=[sys.executable,'-m','pytest','-q','source/tests'] if args.suite=='engine' else [sys.executable,'factory/run_self_tests.py']
    inputs={}
    for folder in ('source/flood_sentinel','source/tests','factory/engine','factory/tests'):
        for path in sorted((root/folder).glob('*.py')):
            inputs[str(path.relative_to(root))]=hashlib.sha256(path.read_bytes()).hexdigest()
    for rel in ('factory/gatekeeper.py','factory/run_self_tests.py',
                'project/audit/tools/inspect_legacy_evidence.py',
                'project/audit/revalidation/run_checks.py'):
        inputs[rel]=hashlib.sha256((root/rel).read_bytes()).hexdigest()
    with tempfile.TemporaryDirectory(prefix='flood-check-keys-') as td:
        env=os.environ.copy(); overrides={'FACTORY_SUPERVISOR_KEY':str(Path(td)/'fixture.key'),'PYTHONDONTWRITEBYTECODE':'1'}
        env.update(overrides); start=datetime.now(timezone.utc).isoformat(); tick=time.monotonic()
        with (dest/(stem+'.log')).open('w') as log:
            completed=subprocess.run(command,cwd=root,env=env,stdout=log,stderr=subprocess.STDOUT,check=False)
        elapsed=time.monotonic()-tick
    record={'scope':'engineering tests using constructed fixtures only; no hydrological observations or performance claims',
            'command':command,'cwd':str(root),'started_at':start,'finished_at':datetime.now(timezone.utc).isoformat(),
            'elapsed_wall_seconds':elapsed,'exit_status':completed.returncode,'environment_overrides':overrides,
            'python':sys.version,'platform':platform.platform(),'input_sha256':inputs,
            'log':stem+'.log','log_sha256':hashlib.sha256((dest/(stem+'.log')).read_bytes()).hexdigest()}
    (dest/(stem+'.json')).write_text(json.dumps(record,indent=2)+'\n')
    print(json.dumps({'suite':args.suite,'exit_status':completed.returncode,'record':stem+'.json','elapsed_wall_seconds':elapsed}))
    raise SystemExit(completed.returncode)


if __name__=='__main__': main()
