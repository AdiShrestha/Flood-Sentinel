"""Executable adversarial regression registry with explicit test scope.

A passing regression is evidence about its concrete attack, not a proof against
arbitrary adversarial workspace owners. Structural registry checks do not run
fixtures; release checks execute the registered tests in an isolated process.
"""
import ast
import re
from pathlib import Path
from .metrics import EvidenceError

_TEST_MODULE = 'tests.test_review_regressions.'
_CASES = [
    ('no_inline_interpreter_code', 'engine.plan.validate', 'LifecycleAttackTests.test_inline_code_rejected_before_execution', 'freeze'),
    ('no_shell_wrapper_injection', 'engine.plan.validate', 'LifecycleAttackTests.test_shell_wrapper_rejected_before_execution', 'freeze'),
    ('no_env_startup_hook_injection', 'gatekeeper.execution_env', 'LifecycleAttackTests.test_loader_hook_rejected_on_run', 'run'),
    ('no_importable_bytecode_in_frozen_inputs', 'engine.io.inventory', 'LifecycleAttackTests.test_bytecode_rejected_on_freeze', 'freeze'),
    ('no_path_spelling_bypass', 'engine.io.inside', 'LifecycleAttackTests.test_path_alias_rejected', 'path_validator'),
    ('no_mutated_source_admissibility', 'engine.audit.Audit.frozen', 'LifecycleAttackTests.test_source_mutation_blocks_audit', 'run_and_audit'),
    ('no_receipt_forgery', 'engine.audit.Audit.experiment', 'LifecycleAttackTests.test_forged_receipt_blocks_audit', 'run_and_audit'),
    ('no_receipt_replay', 'engine.audit.Audit.experiment', 'LifecycleAttackTests.test_replayed_receipt_blocks_audit', 'run_and_audit'),
    ('no_deleted_failed_attempt_admissibility', 'engine.audit.Audit.experiment', 'LifecycleAttackTests.test_deleted_failed_attempt_blocks_audit', 'failed_run_and_audit'),
    ('no_stale_certificate_reuse', 'gatekeeper.certificate_current', 'LifecycleAttackTests.test_stale_certificate_invalidated_by_handoff', 'run_audit_and_handoff'),
    ('archive_integrity_survives_relocation', 'engine.bundle.verify_bundle', 'LifecycleAttackTests.test_archive_relocation_preserves_integrity', 'archive_validator'),
    ('no_vacuous_validator_pass', 'engine.schema.expect_dict', 'StandaloneReviewTests.test_vacuous_manifests', 'standalone_validators'),
    ('no_unresolved_nested_plausibility_pass', 'gatekeeper.verify_result_plausibility', 'StandaloneReviewTests.test_unresolved_nested_result_blocks', 'standalone_validator'),
    ('no_reproduction_relabeling', 'engine.audit.Audit.claims', 'LifecycleAttackTests.test_reproduction_relabeling_blocks_audit', 'run_and_audit'),
    ('no_prediction_membership_tampering', 'engine.audit.Audit.experiment', 'LifecycleAttackTests.test_prediction_membership_tampering_blocks_audit', 'run_and_audit'),
    ('no_runtime_binding_tampering', 'engine.audit.Audit.experiment', 'LifecycleAttackTests.test_runtime_binding_tampering_blocks_audit', 'run_and_audit'),
    ('no_bundle_byte_tampering', 'engine.bundle.verify_bundle', 'LifecycleAttackTests.test_archive_tampering_rejected', 'archive_validator'),
    ('no_module_execution_outside_frozen_inputs', 'engine.plan.validate', 'LifecycleAttackTests.test_module_execution_rejected_before_execution', 'freeze'),
]
ATTACK_REGISTRY = [
    {'id': f'ATK-{index:03d}', 'invariant': invariant, 'implementation': implementation,
     'attack_fixture': _TEST_MODULE + fixture, 'expected_transition': 'PASS' if index == 11 else 'BLOCKED',
     'scope': scope}
    for index, (invariant, implementation, fixture, scope) in enumerate(_CASES, 1)
]


_PUBLICATION_CASES = [
    ('no_private_file_publication', 'test_force_added_internal_file_is_blocked'),
    ('no_historical_leak_publication', 'test_outgoing_history_checks_deleted_leaks'),
    ('no_internal_commit_narration', 'test_commit_messages_are_checked_by_real_hook'),
    ('no_annotated_tag_leak', 'test_annotated_tag_message_cannot_leak'),
]
ATTACK_REGISTRY.extend(
    {'id': f'ATK-{index:03d}', 'invariant': invariant,
     'implementation': 'engine.publication.check',
     'attack_fixture': 'tests.test_publication.PublicationTests.' + method,
     'expected_transition': 'BLOCKED', 'scope': 'real_git_commit_and_push'}
    for index, (invariant, method) in enumerate(_PUBLICATION_CASES, len(ATTACK_REGISTRY)+1)
)


def resolve_attack_fixture(name):
    """Resolve a single unittest method by parsing source, without importing tests."""
    if not isinstance(name, str) or not re.fullmatch(r'tests\.test_[A-Za-z0-9_]+\.[A-Za-z0-9_]+\.test_[A-Za-z0-9_]+', name):
        raise EvidenceError('invalid regression test reference: ' + str(name))
    _, module, class_name, method = name.split('.')
    path = Path(__file__).resolve().parents[1] / 'tests' / (module + '.py')
    try: tree = ast.parse(path.read_text(), filename=str(path))
    except (OSError, SyntaxError) as error: raise EvidenceError('unreadable regression: ' + name) from error
    classes = [node for node in tree.body if isinstance(node, ast.ClassDef) and node.name == class_name]
    if len(classes) != 1 or not any(isinstance(node, ast.FunctionDef) and node.name == method for node in classes[0].body):
        raise EvidenceError('regression test does not exist: ' + name)
    return name


def verify_attack_registry():
    """Validate identity, expectation, implementation and resolvable fixture references."""
    errors = []; ids = set(); fixtures = set()
    for entry in ATTACK_REGISTRY:
        if not isinstance(entry, dict): errors.append('attack entry must be an object'); continue
        for field in ('id', 'invariant', 'implementation', 'attack_fixture', 'expected_transition', 'scope'):
            if not isinstance(entry.get(field), str) or not entry[field].strip():
                errors.append(f'{entry.get("id", "?")} missing substantive {field}')
        attack_id = entry.get('id')
        if attack_id in ids: errors.append('duplicate attack id: ' + str(attack_id))
        ids.add(attack_id)
        if entry.get('expected_transition') not in ('BLOCKED', 'PASS'): errors.append(str(attack_id) + ' has unknown expected transition')
        fixture = entry.get('attack_fixture')
        if fixture in fixtures: errors.append('duplicate attack fixture: ' + str(fixture))
        fixtures.add(fixture)
        try: resolve_attack_fixture(fixture)
        except EvidenceError as error: errors.append(str(error))
        implementation = entry.get('implementation', '')
        if not re.fullmatch(r'(?:gatekeeper|engine\.[A-Za-z_]+)\.[A-Za-z_.]+', implementation):
            errors.append(str(attack_id) + ' has invalid implementation reference')
    return errors


def run_registered_attacks(timeout=120):
    """Execute exactly the registered tests; missing, failed or skipped tests block."""
    import os
    import subprocess
    import sys
    import tempfile
    errors = verify_attack_registry()
    if errors: return {'status': 'FAIL', 'errors': errors, 'tests_run': 0}
    factory = Path(__file__).resolve().parents[1]
    with tempfile.TemporaryDirectory(prefix='factory-release-check-') as folder:
        environment = {key: value for key, value in os.environ.items()
                       if not key.startswith(('PYTHON', 'LD_', 'DYLD_', 'NODE_', 'RUBY', 'PERL'))}
        environment['FACTORY_SUPERVISOR_KEY'] = str(Path(folder) / 'supervisor.key')
        environment['PYTHONDONTWRITEBYTECODE'] = '1'
        command = [sys.executable, '-B', '-m', 'unittest'] + [entry['attack_fixture'] for entry in ATTACK_REGISTRY]
        try:
            result = subprocess.run(command, cwd=factory, env=environment, text=True,
                                    stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=timeout)
        except subprocess.TimeoutExpired:
            return {'status': 'FAIL', 'errors': ['registered attack regressions exceeded timeout'], 'tests_run': 0}
    match = re.search(r'Ran (\d+) tests?', result.stderr)
    count = int(match.group(1)) if match else 0
    errors = []
    if result.returncode: errors.append('registered attack regression failed')
    if count != len(ATTACK_REGISTRY): errors.append('registered test count differs from executed count')
    if 'skipped=' in result.stderr: errors.append('registered attack regression was skipped')
    report = {'status': 'FAIL' if errors else 'PASS', 'tests_run': count,
              'registered_attacks': len(ATTACK_REGISTRY), 'scope': 'concrete regressions with per-entry lifecycle scope'}
    if errors: report.update(errors=errors, details=result.stderr[-12000:])
    return report


def get_attack_count():
    return len(ATTACK_REGISTRY)
