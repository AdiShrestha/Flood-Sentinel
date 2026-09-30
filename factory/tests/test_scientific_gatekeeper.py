import json,subprocess,sys
from pathlib import Path
def test_missing_project_fails(tmp_path):
 gk = Path(__file__).resolve().parent.parent / "gatekeeper.py"
 r=subprocess.run([sys.executable,str(gk),'certify',str(tmp_path)],capture_output=True,text=True)
 assert r.returncode==40 and 'NOT_CERTIFIED' in r.stdout
