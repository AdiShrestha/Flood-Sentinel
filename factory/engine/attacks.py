"""Attack registry: behavioral mutation tests for every security invariant.

Each entry has four required fields:
    invariant       — what the system promises
    implementation  — where the enforcement lives
    attack_fixture  — the test that exercises the bypass
    expected_transition — what must happen (BLOCKED)

A release candidate is blocked until every listed attack fails through the
complete lifecycle. "The mechanism exists" is not enough; the system
demonstrates that the mechanism blocks a concrete attack.
"""

ATTACK_REGISTRY = [
    {
        'id': 'ATK-001',
        'invariant': 'no_inline_interpreter_code',
        'description': 'Attached inline interpreter code (-c, -cexec(...)) must be rejected',
        'implementation': 'engine.contract.command_to_contract',
        'attack_fixture': 'tests.test_v3_3_hardening.AttackTests.test_inline_c_flag_rejected',
        'expected_transition': 'BLOCKED',
    },
    {
        'id': 'ATK-002',
        'invariant': 'no_shell_wrapper_injection',
        'description': 'Shell wrapper injection (env, bash -c, sh -lc) must be rejected',
        'implementation': 'engine.contract.command_to_contract',
        'attack_fixture': 'tests.test_v3_3_hardening.AttackTests.test_shell_wrapper_rejected',
        'expected_transition': 'BLOCKED',
    },
    {
        'id': 'ATK-003',
        'invariant': 'no_env_startup_hook_injection',
        'description': 'Environment startup hooks (PYTHONSTARTUP, LD_PRELOAD) must be rejected',
        'implementation': 'gatekeeper.execution_env',
        'attack_fixture': 'tests.test_v3_3_hardening.AttackTests.test_env_startup_hooks_rejected',
        'expected_transition': 'BLOCKED',
    },
    {
        'id': 'ATK-004',
        'invariant': 'no_importable_bytecode_mutation',
        'description': '.pyc files in frozen paths must be rejected by inventory',
        'implementation': 'engine.io.inventory',
        'attack_fixture': 'tests.test_v3_3_hardening.AttackTests.test_pyc_in_frozen_paths_rejected',
        'expected_transition': 'BLOCKED',
    },
    {
        'id': 'ATK-005',
        'invariant': 'no_path_spelling_bypass',
        'description': 'Dot-segment tricks (project/./audit_report.json) must be normalized',
        'implementation': 'engine.io.inside',
        'attack_fixture': 'tests.test_v3_3_hardening.AttackTests.test_dot_segment_path_rejected',
        'expected_transition': 'BLOCKED',
    },
    {
        'id': 'ATK-006',
        'invariant': 'no_mutable_source_race',
        'description': 'Source mutation during execution must be detected by post-run hash check',
        'implementation': 'gatekeeper.run_exp',
        'attack_fixture': 'tests.test_v3_3_hardening.AttackTests.test_source_mutation_during_run_detected',
        'expected_transition': 'BLOCKED',
    },
    {
        'id': 'ATK-007',
        'invariant': 'no_receipt_forgery',
        'description': 'Tampered receipt signature must be rejected',
        'implementation': 'engine.supervisor.verify_receipt_signature',
        'attack_fixture': 'tests.test_v3_3_hardening.AttackTests.test_receipt_forgery_rejected',
        'expected_transition': 'BLOCKED',
    },
    {
        'id': 'ATK-008',
        'invariant': 'no_receipt_replay',
        'description': 'Receipt from a different experiment must be rejected',
        'implementation': 'engine.audit.Audit.experiment',
        'attack_fixture': 'tests.test_v3_3_hardening.AttackTests.test_receipt_replay_rejected',
        'expected_transition': 'BLOCKED',
    },
    {
        'id': 'ATK-009',
        'invariant': 'no_failed_attempt_deletion',
        'description': 'Missing failed attempts must be detected by the audit',
        'implementation': 'engine.audit.Audit.experiment',
        'attack_fixture': 'tests.test_v3_3_hardening.AttackTests.test_failed_attempt_deletion_detected',
        'expected_transition': 'BLOCKED',
    },
    {
        'id': 'ATK-010',
        'invariant': 'no_stale_certificate_reuse',
        'description': 'Certificate from a previous epoch/evidence must be invalidated',
        'implementation': 'gatekeeper.certificate_current',
        'attack_fixture': 'tests.test_v3_3_hardening.AttackTests.test_stale_certificate_rejected',
        'expected_transition': 'BLOCKED',
    },
    {
        'id': 'ATK-011',
        'invariant': 'no_relocation_failure',
        'description': 'Bundle must verify after relocation to a new directory',
        'implementation': 'engine.bundle.verify_bundle',
        'attack_fixture': 'tests.test_v3_3_hardening.AttackTests.test_bundle_verifies_after_relocation',
        'expected_transition': 'PASS',
    },
    {
        'id': 'ATK-012',
        'invariant': 'no_malformed_validator_coercion',
        'description': '"false" strings, empty structures, and type confusion must be rejected',
        'implementation': 'engine.schema',
        'attack_fixture': 'tests.test_v3_3_hardening.AttackTests.test_schema_type_coercion_rejected',
        'expected_transition': 'BLOCKED',
    },
    {
        'id': 'ATK-013',
        'invariant': 'no_nested_plausibility_bypass',
        'description': 'Zero p-values nested in computed_runs/comparisons must be detected',
        'implementation': 'gatekeeper._deep_result_findings',
        'attack_fixture': 'tests.test_v3_3_hardening.AttackTests.test_nested_plausibility_detected',
        'expected_transition': 'BLOCKED',
    },
    {
        'id': 'ATK-014',
        'invariant': 'no_reproduction_relabeling',
        'description': 'A different model relabeled as reproduction of the target must be rejected',
        'implementation': 'engine.audit.Audit.claims',
        'attack_fixture': 'tests.test_v3_3_hardening.AttackTests.test_reproduction_relabeling_rejected',
        'expected_transition': 'BLOCKED',
    },
    {
        'id': 'ATK-015',
        'invariant': 'no_hidden_label_copying',
        'description': 'Predictions with label values from held-out data must be detected',
        'implementation': 'engine.audit.Audit.experiment',
        'attack_fixture': 'tests.test_v3_3_hardening.AttackTests.test_phantom_prediction_blocked',
        'expected_transition': 'BLOCKED',
    },
    {
        'id': 'ATK-016',
        'invariant': 'no_dependency_runtime_substitution',
        'description': 'Changed interpreter or dependency lock must be detected in receipts',
        'implementation': 'gatekeeper.run_exp',
        'attack_fixture': 'tests.test_v3_3_hardening.AttackTests.test_runtime_substitution_detected',
        'expected_transition': 'BLOCKED',
    },
    {
        'id': 'ATK-017',
        'invariant': 'no_bundle_tampering',
        'description': 'Altered byte in bundle, missing member, added member must be detected',
        'implementation': 'engine.bundle.verify_bundle',
        'attack_fixture': 'tests.test_v3_3_hardening.AttackTests.test_bundle_tampering_detected',
        'expected_transition': 'BLOCKED',
    },
    {
        'id': 'ATK-018',
        'invariant': 'no_module_execution_outside_frozen',
        'description': 'python -m execution mode must be rejected',
        'implementation': 'engine.contract.command_to_contract',
        'attack_fixture': 'tests.test_v3_3_hardening.AttackTests.test_module_execution_rejected',
        'expected_transition': 'BLOCKED',
    },
]


def verify_attack_registry():
    """Validate that the attack registry is well-formed."""
    ids = set()
    errors = []
    for entry in ATTACK_REGISTRY:
        required = ('id', 'invariant', 'implementation', 'attack_fixture', 'expected_transition')
        for k in required:
            if k not in entry:
                errors.append(f'{entry.get("id", "?")} missing {k}')
        aid = entry.get('id', '')
        if aid in ids:
            errors.append(f'duplicate attack id: {aid}')
        ids.add(aid)
    return errors


def get_attack_count():
    """Return the number of registered attacks."""
    return len(ATTACK_REGISTRY)
