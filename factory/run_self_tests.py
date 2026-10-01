#!/usr/bin/env python3
"""Run the v3 standard-library regression suite, offline."""
import unittest
import os
import sys
import tempfile
import json
from pathlib import Path
from unittest.mock import patch
if __name__=='__main__':
    # A regression suite must never fall back to personal signing keys, even
    # if an individual test temporarily edits the key environment variable.
    personal=(Path.home()/'.factory').resolve()
    key_opens=[]
    def audit_open(event,args):
        if event=='open' and isinstance(args[0],(str,bytes,os.PathLike)):
            path=Path(os.fsdecode(args[0])).resolve()
            if path.is_relative_to(personal):
                raise RuntimeError('regression suite attempted personal factory-key access')
            if path.suffix in ('.key','.pub'): key_opens.append(str(path))
    sys.addaudithook(audit_open)
    with tempfile.TemporaryDirectory(prefix='factory-suite-keys-') as td:
        with patch.dict(os.environ,{'FACTORY_SUPERVISOR_KEY':str(Path(td)/'fixture.key')}):
            from engine import supervisor
            supervisor._DEFAULT_KEY_DIR=Path(td)
            suite=unittest.defaultTestLoader.discover(str(Path(__file__).parent/'tests'),pattern='test_*.py')
            result=unittest.TextTestRunner(verbosity=2).run(suite)
        print(json.dumps({'scope':'regression parent-process file-open guard; children inherit restored temporary key environment',
                          'fixture_key_file_opens':len(key_opens),'personal_factory_directory_opens':0}))
    raise SystemExit(0 if result.wasSuccessful() else 1)
