#!/usr/bin/env python3
"""Run all active regressions offline with an isolated signing key.

Unittest discovery plus the repository's five function-style regressions are
collected. Unsupported pytest fixtures fail collection instead of disappearing.
"""
import argparse
import importlib
import inspect
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path


def suite():
    factory = Path(__file__).resolve().parent
    sys.path.insert(0, str(factory))
    loader = unittest.TestLoader()
    result = loader.discover(str(factory / 'tests'), pattern='test_*.py')
    for path in sorted((factory / 'tests').glob('test_*.py')):
        module = importlib.import_module(path.stem)
        for name, function in inspect.getmembers(module, inspect.isfunction):
            if not name.startswith('test_') or function.__module__ != module.__name__: continue
            parameters = list(inspect.signature(function).parameters)
            if parameters not in ([], ['tmp_path']):
                raise RuntimeError('unsupported test fixtures: ' + path.name + '.' + name)
            def invoke(fn=function, params=parameters):
                if params:
                    with tempfile.TemporaryDirectory(prefix='factory-function-test-') as folder:
                        fn(Path(folder))
                else: fn()
            result.addTest(unittest.FunctionTestCase(invoke, description=path.stem + '.' + name))
    if loader.errors: raise RuntimeError('test discovery failed: ' + '; '.join(loader.errors))
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--report', type=Path, help='write a machine-readable validation report')
    args = parser.parse_args()
    sys.path.insert(0,str(Path(__file__).resolve().parent))
    import gatekeeper
    engine_before=gatekeeper.engine_hash();validation_before=gatekeeper.validation_hash()
    original = os.environ.get('FACTORY_SUPERVISOR_KEY')
    with tempfile.TemporaryDirectory(prefix='factory-self-test-key-') as folder:
        os.environ['FACTORY_SUPERVISOR_KEY'] = str(Path(folder) / 'supervisor.key')
        try:
            tests = suite()
            isolated_key = str(Path(folder) / 'supervisor.key')
            class IsolatedResult(unittest.TextTestResult):
                def startTest(self, test):
                    os.environ['FACTORY_SUPERVISOR_KEY'] = isolated_key
                    super().startTest(test)
                def stopTest(self, test):
                    os.environ['FACTORY_SUPERVISOR_KEY'] = isolated_key
                    super().stopTest(test)
            result = unittest.TextTestRunner(verbosity=2, resultclass=IsolatedResult).run(tests)
        finally:
            if original is None: os.environ.pop('FACTORY_SUPERVISOR_KEY', None)
            else: os.environ['FACTORY_SUPERVISOR_KEY'] = original
    unchanged=(engine_before==gatekeeper.engine_hash() and validation_before==gatekeeper.validation_hash())
    if args.report:
        from engine.io import write_json
        write_json(args.report, {'factory_version': '3.3.0', 'status': 'PASS' if result.wasSuccessful() and unchanged else 'FAIL',
                               'engine_sha256':engine_before,'validation_sha256':validation_before,
                               'source_unchanged_during_tests':unchanged,
                               'tests_run': result.testsRun, 'failures': len(result.failures),
                               'errors': len(result.errors), 'skipped': [{'test': str(test), 'reason': reason} for test, reason in result.skipped],
                               'python_version': sys.version, 'scope': 'active regressions; archived legacy code excluded'})
    return 0 if result.wasSuccessful() and unchanged else 1


if __name__ == '__main__':
    raise SystemExit(main())
