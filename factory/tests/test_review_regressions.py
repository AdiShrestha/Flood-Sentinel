"""Independent regressions for verified gaps in the October factory review."""
import ast
import contextlib
import copy
import io
import json
import os
import shutil
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest.mock import patch

FACTORY = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(FACTORY))
import gatekeeper as g
from engine.io import EvidenceError, read_json, write_json, inside
from engine.bundle import create_bundle, verify_bundle
from tests.test_v3 import fixture, evaluate


class StandaloneReviewTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.output = contextlib.redirect_stdout(io.StringIO())
        self.output.__enter__()

    def tearDown(self):
        self.output.__exit__(None, None, None)
        self.temp.cleanup()

    def artifact(self, value):
        path = self.root / 'artifact.json'
        write_json(path, value)
        return path

    def test_vacuous_manifests(self):
        self.assertEqual(g.pre_submission_audit(self.artifact({key: 'x' for key in
                         ('claims', 'data_provenance', 'baselines', 'ablations', 'limitations', 'reproducibility')})), 29)
        self.assertEqual(g.check_contract(self.artifact({'checks': []})), 17)
        self.assertEqual(g.check_contract(self.artifact({'checks': ['x']})), 17)
        self.assertEqual(g.verify_sensitivity_analysis(self.artifact('x')), 28)
        self.assertEqual(g.verify_result_plausibility(self.artifact('x')), g.EXIT_PLAUSIBILITY)

    def test_readiness_requires_existing_evidence(self):
        evidence = self.root / 'evidence.json'; write_json(evidence, {'metric': 'auroc', 'value': .8})
        assessment='Inspected the specific predictions, scope and provenance for this declared local design.'
        readiness={'claims':[{'id':'claim1','scope':'The declared fixed study cohort only.','evidence':['evidence.json']}],
                   'data_provenance':{'assessment':assessment,'evidence':['evidence.json']},
                   'reproducibility':{'assessment':assessment,'evidence':['evidence.json']},
                   'baselines':[{'id':'baseline1','assessment':assessment,'evidence':['evidence.json']}],
                   'ablations':[{'id':'ablation1','assessment':assessment,'evidence':['evidence.json']}],
                   'limitations':['Local evidence cannot establish truthful acquisition.']}
        self.assertEqual(g.pre_submission_audit(self.artifact(readiness)),0)
        evidence.unlink()
        self.assertEqual(g.pre_submission_audit(self.artifact(readiness)),29)

    def test_training_policy_blocks_text_bypass(self):
        self.assertEqual(g.verify_training_sufficiency(self.artifact({'epochs_trained': 3,
                         'loss_curve': [9, 5, 1], 'justification': 'x'})), g.EXIT_TRAINING)
        self.assertEqual(g.verify_training_sufficiency(self.artifact({'epochs_trained': 10,
                         'loss_curve': [10-i for i in range(10)], 'early_stopping_triggered': True})), g.EXIT_TRAINING)
        self.assertEqual(g.verify_training_sufficiency(self.artifact({'epochs_trained': 10,
                         'loss_curve': [.1]*10})), 0)

    def test_split_floor_blocks_text_bypass(self):
        self.assertEqual(g.verify_split_integrity(self.artifact({'test_label_distribution': {'0': 2, '1': 2},
                         'test_group_count': 4, 'sample_size_justification': 'x'})), g.EXIT_SPLIT)
        self.assertEqual(g.verify_split_integrity(self.artifact({'test_label_distribution': {'0': 15, '1': 15},
                         'test_group_count': 30})), 0)
        self.assertEqual(g.verify_split_integrity(self.artifact({'test_label_distribution': {'0': 15, '1': 15},
                         'test_group_count': 1})), g.EXIT_SPLIT)

    def test_metric_specific_baselines(self):
        for metric, value, prevalence in [('average_precision', .3, .05), ('f1', .4, .1)]:
            self.assertEqual(g.verify_result_plausibility(self.artifact({'metric': metric, 'value': value,
                             'prevalence': prevalence, 'verdict': 'SUPPORTED'})), 0)
        self.assertEqual(g.verify_result_plausibility(self.artifact({'metric': 'accuracy', 'value': .93,
                         'prevalence': .95, 'verdict': 'SUPPORTED'})), g.EXIT_PLAUSIBILITY)
        self.assertEqual(g.verify_result_plausibility(self.artifact({'metric': 'auroc', 'value': .12,
                         'verdict': 'INCONCLUSIVE'})), 0)

    def test_unresolved_nested_result_blocks(self):
        payload = {'computed_runs': {'a': {'metrics': [{'metric': 'auroc', 'value': .12, 'p_value': 0}]}},
                   'investigation_note': 'x', 'investigation_disposition': 'unresolved'}
        self.assertEqual(g.verify_result_plausibility(self.artifact(payload)), g.EXIT_PLAUSIBILITY)
        for bad in ({'p_value': 1.1}, {'p_value': True}, {'confidence_interval': [2, 1]}):
            self.assertEqual(g.verify_result_plausibility(self.artifact(bad)), g.EXIT_PLAUSIBILITY)

    def test_excessive_result_depth_blocks_instead_of_skipping(self):
        obj = {'p_value': 0}
        for _ in range(102): obj = {'nested': obj}
        self.assertEqual(g.verify_result_plausibility(self.artifact(obj)), g.EXIT_PLAUSIBILITY)

    def test_sensitivity_requires_multiple_typed_levels(self):
        for values in ([1], [True, 1, 2], [1, 1, 1]):
            self.assertEqual(g.verify_sensitivity_analysis(self.artifact({'sweeps': [{'parameter': 'width', 'metrics': values}]})), 28)
        self.assertEqual(g.verify_sensitivity_analysis(self.artifact({'sweeps': [{'parameter': 'width', 'metrics': [1, 1, 1], 'expected_flat': 'false'}]})), 28)
        self.assertEqual(g.verify_sensitivity_analysis(self.artifact({'sweeps': [{'parameter': 'width', 'metrics': [1, 2, 3]}]})), 0)

    def test_traceability_requires_identifiers(self):
        analysis = self.root / 'analysis.md'; analysis.write_text('No declared identifiers can be found.')
        source = self.artifact({'id': 'S1234'})
        self.assertEqual(g.verify_cross_artifact_traceability(analysis, [source]), g.EXIT_TRACE)
        analysis.write_text('record: S1234')
        self.assertEqual(g.verify_cross_artifact_traceability(analysis, [source]), 0)
        self.assertEqual(g.verify_cross_artifact_traceability(analysis, [source], 'S[0-9]+'), g.EXIT_TRACE)

    def test_protocol_rejects_null_fields_and_no_correction(self):
        protocol = {'primary_metric': 'auroc', 'sampling_unit': 'group', 'test': 'paired permutation',
                    'alpha': .05, 'effect_size': .1, 'confidence_interval': [0, .2],
                    'multiplicity_correction': 'Holm', 'p_values': [.02, .03]}
        self.assertEqual(g.verify_statistical_protocol(self.artifact(protocol)), 0)
        for key, value in [('sampling_unit', None), ('test', None), ('alpha', True), ('multiplicity_correction', 'none')]:
            malformed = dict(protocol); malformed[key] = value
            self.assertEqual(g.verify_statistical_protocol(self.artifact(malformed)), 27)

    def test_failure_taxonomy_rejects_boolean_rate_and_string_ids(self):
        rows = [{'category': name, 'condition_ids': ['S1234'], 'prevalence': .2, 'severity': 'SEV-2'} for name in ('a', 'b', 'c')]
        self.assertEqual(g.verify_failure_taxonomy(self.artifact({'failures': rows})), 0)
        for key, value in [('prevalence', True), ('prevalence', 1.1), ('condition_ids', 'x')]:
            changed = copy.deepcopy(rows); changed[0][key] = value
            self.assertEqual(g.verify_failure_taxonomy(self.artifact({'failures': changed})), 30)

    def test_tier_negation_and_positive_paraphrase(self):
        path = self.root / 'methodology.md'
        for text in ('T-DESC makes no causal claims.', 'T-DESC baseline_class: mechanism_matched'):
            path.write_text(text); self.assertEqual(g.tier_check(path), 0)
        path.write_text('T-DESC: We estimate the intervention effect and identified mechanism.')
        self.assertEqual(g.tier_check(path), 18)
        path.write_text('T-DESC: reports confidence intervals and effect sizes.')
        self.assertEqual(g.tier_check(path), 18)

    def test_coverage_rejects_todo_duplicate_and_dead_guard(self):
        mapping = self.root / 'coverage.yaml'
        mapping.write_text('principles:\n  C70:\n    level: A\n    mechanism: TODO\n  C70:\n    level: A\n')
        with self.assertRaises(EvidenceError): g._coverage_entries(mapping)
        module = self.root / 'gatekeeper.py'
        module.write_text('def audit():\n    check\n\ndef check():\n    if False:\n        raise ValueError()\n    return {}\n')
        graph, definitions = g._call_graph([module])
        self.assertFalse(g._is_substantive('gatekeeper.check', graph, definitions))
        self.assertNotIn('gatekeeper.check', graph['gatekeeper.audit'])

    def test_large_ablation_requires_alias_structure(self):
        from engine.audit import Audit
        audit = Audit(self.root, {'policy': {'min_seeds': 5}}, self.root, {}, 'hash')
        components = list('abcdef')
        cells = {(False,) * 6: set(range(5)), (True,) * 6: set(range(5))}
        with self.assertRaises(EvidenceError): audit.analyses_ablation(components, cells, {})
        audit.analyses_ablation(components, cells, {'design': 'fractional', 'alias_structure': 'Main effects aliased with interactions; interaction claims restricted.'})

    def test_acquisition_requires_explicit_producer(self):
        self.assertEqual(g.acquisition_audit(None), 11)
        self.assertEqual(g.acquisition_audit([self.root / 'missing.py']), 11)
        path = self.root / 'run.py'; path.write_text('print("hello")\n')
        self.assertEqual(g.acquisition_audit([path]), 0)


class LifecycleAttackTests(unittest.TestCase):
    """Adversarial regressions with their actual enforcement scope declared in registry."""
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(); self.root = Path(self.temp.name)
        self.plan = fixture(self.root)
        self.output = contextlib.redirect_stdout(io.StringIO()); self.output.__enter__()

    def tearDown(self):
        self.output.__exit__(None, None, None); self.temp.cleanup()

    def execute(self):
        g.freeze(self.root)
        self.assertEqual(g.run_exp(self.root, 'known'), 0)
        self.assertEqual(evaluate(self.root)['errors'], [])
        return g.active(self.root)[1] / 'runs/known/attempt0001'

    def rejected_command(self, command):
        self.plan['experiments'][0]['command'] = command
        write_json(self.root / g.ROOT_PLAN, self.plan)
        with self.assertRaises(EvidenceError): g.freeze(self.root)
        self.assertFalse((self.root / 'project/RELEASE_CERTIFICATION.json').exists())

    def test_inline_code_rejected_before_execution(self):
        self.rejected_command([sys.executable, '-c', 'print(1)', 'source/run.py', '{run_dir}', '{seed}'])

    def test_shell_wrapper_rejected_before_execution(self):
        self.rejected_command(['sh', '-c', 'python3 source/run.py', '{run_dir}', '{seed}'])

    def test_loader_hook_rejected_on_run(self):
        g.freeze(self.root)
        with patch.dict(os.environ, {'NODE_PATH': '/tmp/injected'}, clear=False):
            self.assertNotIn('NODE_PATH', g.execution_env(42))
            self.assertEqual(g.run_exp(self.root, 'known'), 0)

    def test_bytecode_rejected_on_freeze(self):
        (self.root / 'source/injected.pyc').write_bytes(b'code')
        with self.assertRaises(EvidenceError): g.freeze(self.root)

    def test_path_alias_rejected(self):
        with self.assertRaises(EvidenceError): inside(self.root, 'project/./research_plan.json')

    def test_source_mutation_blocks_audit(self):
        self.execute(); (self.root / 'source/run.py').write_text('print("mutated")')
        self.assertTrue(any(error['code'] == 'FREEZE' for error in evaluate(self.root)['errors']))

    def test_forged_receipt_blocks_audit(self):
        attempt = self.execute(); path = attempt / 'execution.json'; rec = read_json(path)
        rec['supervisor_receipt']['supervisor_signature'] = '00' * 64; write_json(path, rec)
        self.assertTrue(any(error['code'] == 'RUN:known' for error in evaluate(self.root)['errors']))

    def test_replayed_receipt_blocks_audit(self):
        other = copy.deepcopy(self.plan['experiments'][0]); other['id'] = 'other'
        self.plan['experiments'].append(other); write_json(self.root / g.ROOT_PLAN, self.plan)
        g.freeze(self.root); self.assertEqual(g.run_exp(self.root, 'known'), 0); self.assertEqual(g.run_exp(self.root, 'other'), 0)
        epoch = g.active(self.root)[1]
        source = read_json(epoch / 'runs/known/attempt0001/execution.json')
        path = epoch / 'runs/other/attempt0001/execution.json'; rec = read_json(path)
        rec['supervisor_receipt'] = source['supervisor_receipt']; write_json(path, rec)
        self.assertTrue(any(error['code'] == 'RUN:other' for error in evaluate(self.root)['errors']))

    def test_deleted_failed_attempt_blocks_audit(self):
        (self.root / 'source/run.py').write_text('raise RuntimeError("failure")')
        g.freeze(self.root); self.assertNotEqual(g.run_exp(self.root, 'known'), 0)
        epoch = g.active(self.root)[1]; shutil.rmtree(epoch / 'runs/known/attempt0001')
        self.assertTrue(any(error['code'] == 'RUN:known' for error in evaluate(self.root)['errors']))

    def test_stale_certificate_invalidated_by_handoff(self):
        self.execute(); cert = self.root / 'project/RELEASE_CERTIFICATION.json'; write_json(cert, {'status': 'READY_FOR_HUMAN_SUBMISSION_REVIEW'})
        self.assertEqual(g.handoff(self.root), 0); self.assertFalse(cert.exists())

    def bundle(self):
        path = self.root / 'evidence.txt'; path.write_text('evidence')
        archive = self.root / 'bundle.zip'; create_bundle(archive, {'evidence.txt': path}, {'factory_version': '3.3.0'})
        return archive

    def test_archive_relocation_preserves_integrity(self):
        archive = self.bundle()
        with tempfile.TemporaryDirectory() as elsewhere:
            moved = Path(elsewhere) / 'moved.zip'; shutil.copy2(archive, moved)
            self.assertEqual(len(verify_bundle(moved)['files']), 1)

    def test_reproduction_relabeling_blocks_audit(self):
        other = copy.deepcopy(self.plan['experiments'][0]); other.update(id='replay', role='reproduction', reproduces='known', model='easier-model')
        self.plan['experiments'].append(other); write_json(self.root / g.ROOT_PLAN, self.plan)
        with self.assertRaisesRegex(EvidenceError, 'identity|model|reproduction'): g.freeze(self.root)

    def test_prediction_membership_tampering_blocks_audit(self):
        attempt = self.execute(); path = attempt / 'predictions.csv'; path.write_text(path.read_text().replace('s8,', 'phantom,'))
        self.assertTrue(any(error['code'] == 'RUN:known' for error in evaluate(self.root)['errors']))

    def test_runtime_binding_tampering_blocks_audit(self):
        attempt = self.execute(); path = attempt / 'execution.json'; rec = read_json(path)
        rec['interpreter_hash'] = '0' * 64; write_json(path, rec)
        self.assertTrue(any(error['code'] == 'RUN:known' for error in evaluate(self.root)['errors']))

    def test_archive_tampering_rejected(self):
        archive = self.bundle(); changed = self.root / 'changed.zip'
        with zipfile.ZipFile(archive) as old, zipfile.ZipFile(changed, 'w') as new:
            for info in old.infolist(): new.writestr(info, b'forged' if info.filename == 'evidence.txt' else old.read(info.filename))
        with self.assertRaises(EvidenceError): verify_bundle(changed)

    def test_module_execution_rejected_before_execution(self):
        self.rejected_command([sys.executable, '-m', 'json.tool', 'source/run.py', '{run_dir}', '{seed}'])
