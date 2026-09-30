import json, subprocess, sys
from pathlib import Path

def test_init_and_fail_closed(tmp_path):
 g=Path(__file__).parents[1]/'gatekeeper.py'
 r=subprocess.run([sys.executable,str(g),'init',str(tmp_path)],capture_output=True,text=True); assert r.returncode==0
 r=subprocess.run([sys.executable,str(g),'certify',str(tmp_path)],capture_output=True,text=True); assert r.returncode != 0 and 'NOT_CERTIFIED' in r.stdout
