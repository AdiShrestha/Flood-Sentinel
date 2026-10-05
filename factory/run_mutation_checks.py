#!/usr/bin/env python3
"""Run a focused, reproducible behavioral mutation benchmark in temporary copies.

This measures the listed guard and expression changes and selected regressions. It is
not a repository-wide mutation score or proof that every policy is mechanized.
The original factory is never edited. Baseline, missing targets, collection
errors and timeouts cannot be counted as killed mutants.
"""
import argparse
import ast
import datetime
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import time
import unittest


FACTORY = Path(__file__).resolve().parent
_INDEPENDENT = 'test_independent_scientific_review.'
_GUARDS = _INDEPENDENT + 'MutationCriticalGuardsTests.'
_PLAN = _INDEPENDENT + 'PlanBoundaryTests.'
_AUDIT = 'test_audit_integrity.AuditIntegrityTests.'
_LIFECYCLE = 'test_v3.LifecycleTests.'
POSITIVE_CONTROL = _LIFECYCLE + 'test_valid_evidence_path'


def _mutant(identifier, file, function, call, marker, test, replacement='None'):
    return {'id': identifier, 'file': file, 'function': function, 'call': call,
            'marker': marker, 'replacement': replacement, 'tests': [test, POSITIVE_CONTROL]}


MUTANTS = [
    _mutant('M01', 'engine/audit.py', 'Audit.frozen', 'need', 'frozen input changed',
            'test_review_regressions.LifecycleAttackTests.test_source_mutation_blocks_audit'),
    _mutant('M02', 'engine/audit.py', 'Audit.frozen', 'need', 'plan changed after freeze',
            _LIFECYCLE + 'test_mutated_plan_invalidates_freeze'),
    _mutant('M03', 'engine/audit.py', 'Audit.frozen', 'need', 'active factory code changed',
            _GUARDS + 'test_engine_freeze_binding_is_checked_before_run_validation'),
    _mutant('M04', 'engine/audit.py', 'Audit.frozen', 'need', 'frozen plan snapshot changed',
            _GUARDS + 'test_plan_snapshot_is_checked_before_history_validation'),
    _mutant('M05', 'engine/audit.py', 'Audit.experiment', 'verify_execution_record', 'experiment=e',
            _GUARDS + 'test_receipt_verification_is_required_in_the_run_validator', replacement='{}'),
    _mutant('M06', 'engine/audit.py', 'Audit.experiment', 'need', 'stale freeze binding',
            _AUDIT + 'test_stale_freeze_binding_even_with_valid_signature'),
    _mutant('M07', 'engine/audit.py', 'Audit.experiment', 'need', 'output hash/membership changed',
            _AUDIT + 'test_extra_output_membership_blocks'),
    _mutant('M08', 'engine/audit.py', 'Audit.experiment', 'need', 'duplicate prediction id',
            _GUARDS + 'test_duplicate_prediction_is_rejected_with_complete_membership'),
    _mutant('M09', 'engine/audit.py', 'Audit.cohort', 'need', 'empty/duplicate sample_id',
            _GUARDS + 'test_duplicate_cohort_identity_is_rejected_directly'),
    _mutant('M10', 'engine/audit.py', 'Audit.cohort', 'need', 'empty/duplicate source record_id',
            _GUARDS + 'test_duplicate_source_identity_is_rejected_directly'),
    _mutant('M11', 'engine/audit.py', 'Audit.cohort', 'need', 'leakage across splits',
            _LIFECYCLE + 'test_group_leakage'),
    _mutant('M12', 'engine/audit.py', '_review_text', 'need', 'repetitive or placeholder reasoning',
            _GUARDS + 'test_repetitive_padding_is_rejected_even_with_an_evidence_citation'),
    _mutant('M13', 'engine/audit.py', 'verify_review', 'need', 'review stale:',
            _GUARDS + 'test_stale_review_digest_has_a_specific_rejection'),
    _mutant('M14', 'engine/audit.py', '_review_evidence', 'need', 'review evidence must belong to current audit',
            _AUDIT + 'test_unrelated_review_evidence_blocks'),
    _mutant('M15', 'engine/plan.py', 'validate', 'need', 'freeze the whole source directory',
            _GUARDS + 'test_added_source_cannot_evade_directory_freezing'),
    _mutant('M16', 'engine/plan.py', '_shape', 'expect_int', "'schema_version'",
            _GUARDS + 'test_schema_version_must_be_an_integer'),
    _mutant('M17', 'engine/plan.py', 'validate', 'need', 'seed inference requires explicit inference_scope',
            _GUARDS + 'test_seed_scope_is_required_without_comparative_prose'),
    _mutant('M18', 'engine/plan.py', 'validate', 'need', 'infeasible two-sided sign-flip resolution',
            _PLAN + 'test_infeasible_five_seed_superiority_fails_before_execution'),
    _mutant('M19', 'engine/plan.py', 'validate', 'need', 'paired seeds mismatch or duplicate',
            _GUARDS + 'test_distinct_experiment_ids_do_not_make_duplicate_seeds_independent'),
]


_PUBLICATION = 'test_publication.PublicationTests.'
MUTANTS.extend([
    _mutant('M20', 'engine/publication.py', 'check', '_allowed_path', 'path,policy',
            _PUBLICATION + 'test_force_added_internal_file_is_blocked', 'True'),
    _mutant('M21', 'engine/publication.py', '_content', '_text_findings', 'text,path',
            _PUBLICATION + 'test_comments_docs_notebooks_and_ci_are_scanned', '[]'),
    _mutant('M22', 'engine/publication.py', 'check', '_text_findings', "text,'commit message'",
            _PUBLICATION + 'test_commit_messages_are_checked_by_real_hook', '[]'),
    _mutant('M23', 'engine/publication.py', 'check', '_text_findings', "tag,'tag message'",
            _PUBLICATION + 'test_annotated_tag_message_cannot_leak', '[]'),
    _mutant('M24', 'engine/publication.py', 'check', '_ref_findings', 'branch',
            _PUBLICATION + 'test_internal_ref_names_are_blocked', '[]'),
])

_NONCE = 'test_review_addendum.ExecutionNonceTests.'
_FORMULA = 'test_review_addendum.IndependentFormulaTests.'
MUTANTS.extend([
    _mutant('M25', 'engine/audit.py', 'Audit.history', 'need', 'execution nonce differs from signed reservation',
            _NONCE + 'test_signed_ledger_nonce_must_match_record'),
    _mutant('M26', 'engine/audit.py', 'Audit.history', 'need', 'execution nonce reused across epochs',
            _NONCE + 'test_signed_nonce_reuse_across_epochs_is_rejected'),
    _mutant('M27', 'engine/audit.py', 'Audit.history', 'validate_execution_ledger', 'project_id=old',
            _NONCE + 'test_signed_duplicate_nonce_is_rejected_by_audit', 'set()'),
])


def _expression(identifier, file, function, kind, marker, replacement, test, positive_control=POSITIVE_CONTROL):
    return {'id': identifier, 'file': file, 'function': function, 'node_kind': kind,
            'marker': marker, 'replacement': replacement, 'tests': [test, positive_control]}


MUTANTS.extend([
    _expression('M28', 'gatekeeper.py', 'run_exp', 'Compare', 'run_nonce in reserved', 'False',
                _NONCE + 'test_repeated_generated_nonce_blocks_before_launch'),
    _expression('M29', 'engine/metrics.py', 'binary_metrics', 'Compare', 'a == 0', 'a == 1',
                _FORMULA + 'test_all_binary_metrics_match_independent_confusion_and_loss_oracles',
                # Lifecycle fixtures report independent F1, so corrupting F1
                # appropriately raises EvidenceError there. Use an unaffected
                # scientific control and score the oracle's assertion failure.
                _INDEPENDENT + 'IndependentMetricTests.test_t_interval_matches_independent_table_value'),
    _expression('M30', 'engine/metrics.py', 'binary_metrics', 'BoolOp',
                'any(not 0 <= v <= 1 for v in s) or not 0 <= threshold <= 1',
                'any(not 0 <= v <= 1 for v in s) and not 0 <= threshold <= 1',
                _FORMULA + 'test_probability_domains_and_holm_upper_boundary'),
    _expression('M31', 'engine/metrics.py', 'quantile', 'BinOp', '(len(a)-1) * q', '(len(a)-2) * q',
                _FORMULA + 'test_probability_domains_and_holm_upper_boundary'),
    _expression('M32', 'engine/metrics.py', 'holm', 'Compare', '0 <= p <= 1', '0 <= p <= 2',
                _FORMULA + 'test_probability_domains_and_holm_upper_boundary'),
    _expression('M33', 'gatekeeper.py', 'certify', 'Compare', "checks.get('status')!='PASS'", 'False',
                'test_review_addendum.CertificationPreflightTests.test_failed_preflight_status_cannot_be_reported_with_success_code'),
    _mutant('M34', 'gatekeeper.py', 'certify', 'sha', "project/release_checks.json",
            'test_review_addendum.CertificationPreflightTests.test_ordinary_certify_runs_fresh_preflight_despite_persisted_pass', "'0'*64"),
    _expression('M35', 'engine/supervisor.py', 'verify_execution_record', 'Compare', "'receipt_error' in record", 'False',
                _NONCE + 'test_receipt_error_blocks_even_with_valid_signature_and_binding'),
])


def _function(tree, qualified):
    nodes = tree.body
    result = None
    for name in qualified.split('.'):
        matching = [node for node in nodes if isinstance(node, (ast.ClassDef, ast.FunctionDef)) and node.name == name]
        if len(matching) != 1:
            raise ValueError('missing or ambiguous function: ' + qualified)
        result = matching[0]
        nodes = result.body
    return result


def apply_mutation(source, specification):
    """Replace exactly one selected AST expression, preserving all other bytes."""
    tree = ast.parse(source)
    function = _function(tree, specification['function'])
    kind = specification.get('node_kind', 'Call')
    if kind not in {'Call', 'Compare', 'BoolOp', 'BinOp', 'UnaryOp'}:
        raise ValueError('unsupported AST mutation kind: ' + str(kind))
    candidates = []
    for node in ast.walk(function):
        if type(node).__name__ != kind:
            continue
        segment = ast.get_source_segment(source, node)
        if kind == 'Call':
            matched = (isinstance(node.func, ast.Name) and node.func.id == specification['call']
                       and specification['marker'] in segment)
        else:
            matched = segment == specification['marker']
        if matched:
            candidates.append(node)
    if len(candidates) != 1:
        raise ValueError(f'expected one matching {kind}, found {len(candidates)}')
    node = candidates[0]
    # AST column offsets count UTF-8 bytes, rather than Python characters.
    encoded = source.encode('utf-8')
    lines = encoded.splitlines(keepends=True)
    start = sum(map(len, lines[:node.lineno-1])) + node.col_offset
    end = sum(map(len, lines[:node.end_lineno-1])) + node.end_col_offset
    changed = (encoded[:start] + specification['replacement'].encode() + encoded[end:]).decode('utf-8')
    ast.parse(changed)
    location = {'line': node.lineno, 'node_kind': kind,
                'original_expression': ast.get_source_segment(source, node),
                'replacement': specification['replacement']}
    if kind == 'Call': location['deleted_call'] = location['original_expression']
    return changed, location


def _write(path, payload):
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + '.tmp')
    temporary.write_text(json.dumps(payload, indent=2, sort_keys=True)+'\n')
    temporary.replace(path)


def _worker(names, report_path):
    sys.path.insert(0, str(FACTORY))
    sys.path.insert(0, str(FACTORY / 'tests'))
    isolated_key = os.environ['FACTORY_SUPERVISOR_KEY']
    loader = unittest.TestLoader()
    suite = loader.loadTestsFromNames(names)
    class IsolatedResult(unittest.TextTestResult):
        def startTest(self, test):
            os.environ['FACTORY_SUPERVISOR_KEY'] = isolated_key
            super().startTest(test)
        def stopTest(self, test):
            os.environ['FACTORY_SUPERVISOR_KEY'] = isolated_key
            super().stopTest(test)
    result = unittest.TextTestRunner(verbosity=1, resultclass=IsolatedResult).run(suite)
    payload = {'tests_run': result.testsRun,
               'failures': [{'test': test.id(), 'detail': detail[-4000:]} for test, detail in result.failures],
               'errors': [{'test': test.id(), 'detail': detail[-4000:]} for test, detail in result.errors],
               'skipped': [{'test': test.id(), 'reason': reason} for test, reason in result.skipped],
               'collection_errors': loader.errors,
               'status': 'PASS' if result.wasSuccessful() and not loader.errors else 'FAIL'}
    _write(report_path, payload)
    return 0 if payload['status'] == 'PASS' else 1


def _run_tests(factory, names, folder, timeout):
    folder.mkdir()
    path = folder / 'worker.json'
    environment = dict(os.environ)
    environment.update(FACTORY_SUPERVISOR_KEY=str(folder / 'keys' / 'supervisor.key'),
                       PYTHONDONTWRITEBYTECODE='1', PYTHONHASHSEED='0')
    environment.pop('PYTHONPATH', None)
    command = [sys.executable, '-B', str(factory / 'run_mutation_checks.py'),
               '--worker-report', str(path), '--worker', *names]
    started = time.monotonic()
    try:
        result = subprocess.run(command, cwd=factory, env=environment, capture_output=True,
                                text=True, timeout=timeout)
    except subprocess.TimeoutExpired:
        return {'status': 'TIMEOUT', 'duration_seconds': round(time.monotonic()-started, 3)}
    if not path.is_file():
        return {'status': 'ERROR', 'exit_code': result.returncode,
                'detail': result.stderr[-4000:], 'duration_seconds': round(time.monotonic()-started, 3)}
    payload = json.loads(path.read_text())
    payload.update(exit_code=result.returncode, duration_seconds=round(time.monotonic()-started, 3),
                   command=['python', '-B', 'run_mutation_checks.py', '--worker', *names])
    return payload


def run_benchmark(*, minimum_score=80, timeout=180):
    report = {'schema_version': 1, 'factory_version': '3.3.0',
              'created_at': datetime.datetime.now(datetime.timezone.utc).isoformat(),
              'python_version': sys.version, 'minimum_score_percent': minimum_score,
              'scope': str(len(MUTANTS))+' named call removals/replacements, comparison flips, boolean changes and arithmetic changes; selected stdlib regressions; active engine only',
              'limitations': ['Focused benchmark, not all possible mutations or repository-wide coverage.',
                              'Kills assert specified guard behavior; redundant defense layers may also block invalid artifacts.',
                              'No equivalent mutants are excluded automatically.'], 'mutants': []}
    with tempfile.TemporaryDirectory(prefix='factory-mutation-') as temporary:
        folder = Path(temporary)
        pristine = folder / 'pristine' / 'factory'
        ignored = shutil.ignore_patterns('legacy', '__pycache__', '.pytest_cache', '.DS_Store',
                                          '__MACOSX', '*.pyc', '*.pyo', '*.tmp', 'TAKE_THIS', 'DROP_HERE')
        shutil.copytree(FACTORY, pristine, ignore=ignored)
        source_files = {str(path.relative_to(pristine)): hashlib.sha256(path.read_bytes()).hexdigest()
                        for path in sorted(pristine.rglob('*')) if path.is_file()}
        report['snapshot_sha256'] = hashlib.sha256(json.dumps(source_files, sort_keys=True,
                                                            separators=(',', ':')).encode()).hexdigest()
        report['source_files'] = source_files
        baseline_names = sorted({name for mutant in MUTANTS for name in mutant['tests']})
        report['baseline'] = _run_tests(pristine, baseline_names, folder / 'baseline', timeout)
        if report['baseline']['status'] != 'PASS' or report['baseline']['skipped']:
            report.update(status='BASELINE_FAILED', score_percent=None,
                          detail='Baseline must pass without skips before any mutant can be scored.')
            return report
        for specification in MUTANTS:
            case = folder / specification['id']
            factory = case / 'factory'
            shutil.copytree(pristine, factory, ignore=ignored)
            row = {key: specification[key] for key in ('id', 'file', 'function', 'tests')}
            try:
                path = factory / specification['file']
                changed, location = apply_mutation(path.read_text(), specification)
                path.write_text(changed)
                row.update(location)
                result = _run_tests(factory, specification['tests'], case / 'run', timeout)
                row['test_result'] = result
                if result['status'] in ('TIMEOUT', 'ERROR') or result.get('collection_errors') or result.get('skipped') or result.get('errors'):
                    row['status'] = 'ERROR'
                else:
                    row['status'] = 'KILLED' if result['failures'] else 'SURVIVED'
            except (OSError, SyntaxError, ValueError) as error:
                row.update(status='ERROR', detail=str(error))
            report['mutants'].append(row)
    killed = sum(row['status'] == 'KILLED' for row in report['mutants'])
    survivors = [row['id'] for row in report['mutants'] if row['status'] == 'SURVIVED']
    errors = [row['id'] for row in report['mutants'] if row['status'] == 'ERROR']
    score = 100 * killed / len(MUTANTS)
    report.update(killed=killed, total=len(MUTANTS), survivors=survivors, errors=errors,
                  equivalent_mutants=[], score_percent=score,
                  status='PASS' if score >= minimum_score and not errors else 'FAIL')
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--report', type=Path, help='write the complete machine-readable benchmark artifact')
    parser.add_argument('--minimum-score', type=float, default=80,
                        help='minimum killed percentage for this declared benchmark (default: 80)')
    parser.add_argument('--timeout', type=int, default=180, help='per-process timeout in seconds')
    parser.add_argument('--worker', nargs='+', help=argparse.SUPPRESS)
    parser.add_argument('--worker-report', type=Path, help=argparse.SUPPRESS)
    args = parser.parse_args()
    if args.worker:
        if args.worker_report is None:
            parser.error('internal worker requires a report path')
        return _worker(args.worker, args.worker_report)
    if not 0 <= args.minimum_score <= 100 or args.timeout < 1:
        parser.error('score must be in [0,100] and timeout must be positive')
    payload = run_benchmark(minimum_score=args.minimum_score, timeout=args.timeout)
    if args.report:
        _write(args.report, payload)
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0 if payload['status'] == 'PASS' else 1


if __name__ == '__main__':
    raise SystemExit(main())
