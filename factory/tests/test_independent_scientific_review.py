"""Behavioral regressions from an independent review of the v3.3 engine."""
import copy
import contextlib
import csv
import io
import itertools
import math
from pathlib import Path
import random
import sys
import tempfile
import unittest
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from engine.metrics import (EvidenceError, binary_metrics, holm, number,
                            paired_group_inference, paired_inference,
                            student_t_critical)
from engine.plan import validate
from engine.schema import (ValidationError, expect_enum, expect_float,
                           validate_plausibility_entry,
                           validate_reproduction_manifest,
                           validate_split_manifest, validate_split_support,
                           validate_training_manifest, validate_training_trace)
from test_v3 import fixture
import gatekeeper as g
from engine.audit import Audit, verify_review, _review_text
from engine.io import read_json, write_json, sha


class TypedEvidenceTests(unittest.TestCase):
    def test_fractional_counts_and_epochs_are_not_measurements(self):
        with self.assertRaises(ValidationError):
            validate_split_manifest({'test_label_distribution': {'0': 2.5, '1': 3}})
        with self.assertRaises(ValidationError):
            validate_training_manifest({'epochs_trained': 3.5})

    def test_every_loss_is_validated_even_when_early_stopping_is_claimed(self):
        with self.assertRaises(ValidationError):
            validate_training_manifest({'epochs_trained': 5, 'early_stopping_triggered': True,
                                        'loss_curve': [1, .8, .6, .4, 'bad']})

    def test_probability_and_interval_domains(self):
        for entry in ({'p': float('nan')}, {'p': float('inf')}, {'p': -1},
                      {'p': 1.1}, {'p': None}, {'ci': [2, 1]}, {'ci': None},
                      {'p': .01, 'p_value': .02}, {'ci': [0, 1], 'confidence_interval': [.1, 1]}):
            with self.subTest(entry=entry), self.assertRaises(ValidationError):
                validate_plausibility_entry(entry)

    def test_empty_replay_and_numeric_string_are_rejected(self):
        for manifest in ({'original': {}, 'replay': {}},
                         {'original': {'score': '1'}, 'replay': {'score': 1}},
                         {'original': {'score': 1}, 'replay': {'score': 1}, 'tolerance': None}):
            with self.assertRaises(ValidationError):
                validate_reproduction_manifest(manifest)

    def test_unhashable_enum_and_huge_number_fail_cleanly(self):
        for value in ([], {}):
            with self.assertRaises(ValidationError):
                expect_enum(value, {'fixed'})
        with self.assertRaises(ValidationError):
            expect_float(10**1000)
        with self.assertRaises(EvidenceError):
            number(10**1000)


class TrainingAndSplitTests(unittest.TestCase):
    @staticmethod
    def rows(losses):
        return [{'epoch': str(index), 'train_loss': str(loss+.1),
                 'validation_loss': str(loss)} for index, loss in enumerate(losses, 1)]

    def test_real_stopping_event_and_checkpoint_selection(self):
        policy = {'mode': 'early_stopping', 'min_epochs': 2, 'max_epochs': 8,
                  'patience': 2, 'min_delta': .01}
        rows = self.rows([1, .5, .505, .502])
        result = validate_training_trace(policy, rows, 4, 2)
        self.assertEqual(result['stop_epoch'], 4)
        with self.assertRaises(ValidationError):
            validate_training_trace(policy, rows, 4, 4)
        with self.assertRaises(ValidationError):
            validate_training_trace(policy, self.rows([1, .8, .6, .4]), 4, 4)
        with self.assertRaises(ValidationError):
            validate_training_trace(policy, rows + self.rows([.5]), 5, 2)

    def test_fixed_trace_requires_budget_and_stable_tail(self):
        policy = {'mode': 'fixed', 'min_epochs': 2, 'max_epochs': 6,
                  'tail_window': 2, 'relative_tolerance': .05}
        self.assertEqual(validate_training_trace(policy, self.rows([1, .7, .5, .5, .5, .5]), 6, 3)['checkpoint_epoch'], 3)
        for losses, checkpoint in (([1, .9, .8, .7, .6, .5], 6),
                                   ([1, .7, .5, .5, .5], 3)):
            with self.assertRaises(ValidationError):
                validate_training_trace(policy, self.rows(losses), len(losses), checkpoint)

    def test_declared_support_cannot_be_overridden_by_prose(self):
        with self.assertRaises(ValidationError):
            validate_split_support({'0': 10, '1': 1}, 30, min_class_count=10, min_test_groups=30)
        with self.assertRaises(ValidationError):
            validate_split_support({'0': 10, '1': 10}, 29, min_class_count=10, min_test_groups=30)
        self.assertEqual(validate_split_support({'0': 10, '1': 10}, 30,
                                               min_class_count=10, min_test_groups=30)['group_count'], 30)


class IndependentMetricTests(unittest.TestCase):
    def test_auc_matches_pairwise_definition_including_ties(self):
        rng = random.Random(944)
        for _ in range(30):
            labels = [0]*7 + [1]*5
            scores = [rng.choice((.1, .3, .5, .9)) for _ in labels]
            positive = [score for label, score in zip(labels, scores) if label]
            negative = [score for label, score in zip(labels, scores) if not label]
            expected = sum((a > b) + .5*(a == b) for a in positive for b in negative) / 35
            self.assertAlmostEqual(binary_metrics(labels, scores)['auroc'], expected)

    def test_t_interval_matches_independent_table_value(self):
        self.assertAlmostEqual(student_t_critical(.05, 4), 2.7764451051977987, places=12)
        result = paired_inference([1, 2, 3, 4, 5], [0]*5)
        half_width = 2.7764451051977987 * math.sqrt(.5)
        self.assertAlmostEqual(result['ci'][0], 3-half_width)
        self.assertAlmostEqual(result['ci'][1], 3+half_width)
        self.assertEqual(result['inference_scope'], 'fixed_test_corpus')

    def test_small_sample_normal_mean_interval_coverage(self):
        rng = random.Random(62205)
        covered = 0
        for _ in range(1000):
            ci = paired_inference([rng.gauss(0, 1) for _ in range(5)], [0]*5)['ci']
            covered += ci[0] <= 0 <= ci[1]
        self.assertGreaterEqual(covered, 925)
        self.assertLessEqual(covered, 975)

    def test_group_permutation_matches_enumeration_of_independent_items(self):
        labels = [0, 1]*4
        a = [.1, .9, .1, .9, .1, .9, .9, .1]
        b = [.9, .1, .9, .1, .1, .9, .1, .9]
        differences = [int(label == (x >= .5))-int(label == (z >= .5))
                       for label, x, z in zip(labels, a, b)]
        observed = sum(differences) / 8
        p = sum(abs(sum(d*s for d, s in zip(differences, signs))/8) >= abs(observed)
                for signs in itertools.product((-1, 1), repeat=8)) / 256
        result = paired_group_inference(labels, [(a, b)]*5, [str(i) for i in range(8)], 'accuracy', draws=1000)
        self.assertEqual(result['p_raw'], p)
        self.assertEqual(result['effect'], observed)
        self.assertEqual(result['n_units'], 8)

    def test_repeating_same_seeds_cannot_multiply_test_evidence(self):
        labels = [0, 1]*4
        a, b = [.1, .9]*3 + [.9, .1], [.9, .1]*2 + [.1, .9]*2
        one = paired_group_inference(labels, [(a, b)], [str(i) for i in range(8)], 'accuracy', draws=1000)
        repeated = paired_group_inference(labels, [(a, b)]*10, [str(i) for i in range(8)], 'accuracy', draws=1000)
        for key in ('p_raw', 'ci', 'n_units', 'effect'):
            self.assertEqual(one[key], repeated[key])

    def test_group_thresholds_and_loss_direction(self):
        labels = [0, 1]*4
        a, b = [.2, .7]*4, [.4, .6]*4
        result = paired_group_inference(labels, [(a, b)], [str(i) for i in range(8)],
                                       'brier', draws=1000)
        expected = binary_metrics(labels, b)['brier'] - binary_metrics(labels, a)['brier']
        self.assertAlmostEqual(result['effect'], expected)
        thresholds = paired_group_inference(labels, [(a, b)], [str(i) for i in range(8)],
                                           'accuracy', thresholds=[(.6, .8)], draws=1000)
        self.assertEqual(thresholds['effect'], .5)
        self.assertEqual(thresholds['p_raw'], .125)

    def test_degenerate_group_bootstrap_does_not_invent_zero_uncertainty(self):
        result = paired_group_inference([0, 1]*4, [([.1, .9]*4, [.9, .1]*4)],
                                        [str(i) for i in range(8)], 'accuracy', draws=1000)
        self.assertEqual(result['ci'], [-1, 1])
        self.assertTrue(result['degenerate_variance'])

    def test_scale_relative_permutation_tolerance(self):
        self.assertEqual(paired_inference([1e-20]*6, [0]*6)['p_raw'], 2/64)

    def test_bad_vectors_and_inference_settings_fail_cleanly(self):
        for value in (None, '01', {'0': 0, '1': 1}):
            with self.assertRaises(EvidenceError):
                binary_metrics(value, [.2, .8])
        for settings in ({'draws': True}, {'draws': 1000.5}, {'seed': False}, {'alpha': True}):
            with self.assertRaises(EvidenceError):
                paired_inference([1, 2], [0, 0], **settings)
        with self.assertRaises(EvidenceError):
            holm([float('nan')])


class PlanBoundaryTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.plan = fixture(self.root)

    def tearDown(self):
        self.tmp.cleanup()

    def comparison_plan(self, n=5):
        template = self.plan['experiments'][0]
        experiments, pairs = [], []
        for seed in range(n):
            pair = []
            for name in ('a', 'b'):
                experiment = copy.deepcopy(template)
                experiment.update(id=f'{name}{seed}', model=name, seed=seed, role='control')
                experiments.append(experiment)
                pair.append(experiment['id'])
            pairs.append(pair)
        self.plan['experiments'] = experiments
        self.plan['claims'][0]['experiment_ids'] = ['a0']
        self.plan['comparisons'] = [{'id': 'contrast', 'pairs': pairs, 'metric': 'accuracy',
                                    'sampling_unit': 'seed_fixed_test', 'inference_scope': 'fixed_test_corpus',
                                    'assertion': 'estimate', 'alpha': .05, 'minimum_effect': .1, 'max_ci_width': 2}]
        return self.plan

    def test_all_nested_container_mutants_reject_without_tracebacks(self):
        paths = []
        def visit(value, path=()):
            entries = value.items() if isinstance(value, dict) else enumerate(value) if isinstance(value, list) else ()
            for key, item in entries:
                paths.append(path+(key,))
                visit(item, path+(key,))
        visit(self.plan)
        for path in paths:
            for replacement in (None, False, [], {}, 3.5, 'x'):
                mutant = copy.deepcopy(self.plan)
                owner = mutant
                for key in path[:-1]:
                    owner = owner[key]
                owner[path[-1]] = replacement
                try:
                    validate(self.root, mutant)
                except EvidenceError:
                    pass
                except Exception as error:
                    self.fail(f'{path}: malformed input raised {type(error).__name__}: {error}')

    def test_research_policy_and_provenance_are_mandatory(self):
        self.plan.update(intent='research', data_origin='observational')
        with self.assertRaises(EvidenceError):
            validate(self.root, self.plan)
        self.plan['policy'].update(min_class_count=10, min_test_groups=30)
        with self.assertRaises(EvidenceError):
            validate(self.root, self.plan)
        self.plan['data_provenance'] = 'data/provenance.json'
        validate(self.root, self.plan)

    def test_numeric_strings_and_unknown_split_rejected(self):
        self.plan['experiments'][0]['threshold'] = '.5'
        with self.assertRaises(EvidenceError):
            validate(self.root, self.plan)
        self.plan['experiments'][0]['threshold'] = .5
        self.plan['experiments'][0]['evaluation_splits'].append('phantom')
        with self.assertRaises(EvidenceError):
            validate(self.root, self.plan)

    def test_infeasible_five_seed_superiority_fails_before_execution(self):
        p = self.comparison_plan()
        validate(self.root, p)
        p['comparisons'][0]['assertion'] = 'superiority'
        with self.assertRaisesRegex(EvidenceError, 'infeasible'):
            validate(self.root, p)
        validate(self.root, self.comparison_plan(6))

    def test_population_claim_cannot_use_fixed_corpus_seed_inference(self):
        p = self.comparison_plan(6)
        claim = p['claims'][0]
        claim.update(kind='comparative', comparison_id='contrast',
                     experiment_ids=[e['id'] for e in p['experiments']])
        with self.assertRaisesRegex(EvidenceError, 'fixed_test_corpus'):
            validate(self.root, p)
        claim.update(population='fixed_test_corpus', inference_scope='fixed_test_corpus')
        validate(self.root, p)

    def test_duplicate_pairs_and_unknown_analysis_do_not_run(self):
        p = self.comparison_plan(6)
        p['comparisons'][0]['pairs'][1] = p['comparisons'][0]['pairs'][0]
        with self.assertRaises(EvidenceError):
            validate(self.root, p)
        self.plan['comparisons'] = []
        self.plan['analyses'] = {'failures': [{'id': 'missing', 'experiment_id': 'phantom',
                                              'condition': {'column': 'label', 'equals': 0}}]}
        with self.assertRaises(EvidenceError):
            validate(self.root, self.plan)

    def test_contract_only_directory_entrypoint_is_preflighted(self):
        experiment = self.plan['experiments'][0]
        experiment.pop('command')
        experiment['code_paths'] = ['source']
        experiment['execution_contract'] = {
            'runtime_id': 'python-cpu-v1', 'entrypoint': 'source/run.py',
            'arguments': ['{run_dir}', '{seed}', '{experiment_id}']}
        validate(self.root, self.plan)
        experiment['execution_contract']['entrypoint'] = 'source/missing.py'
        with self.assertRaises(EvidenceError):
            validate(self.root, self.plan)

    def test_interpreter_flags_fail_before_a_freeze_can_be_created(self):
        self.plan['experiments'][0]['command'] = ['python3', '-c', 'print(1)', '{run_dir}', '{seed}']
        with self.assertRaises(EvidenceError):
            validate(self.root, self.plan)


LABEL_FREE_COMPARISON_SCRIPT = '''import csv,json,sys
from pathlib import Path
out=Path(sys.argv[1]);seed=int(sys.argv[2]);eid=sys.argv[3];method=sys.argv[4]
rows=list(csv.DictReader(open('data/input_features.csv')))
with open(out/'predictions.csv','w',newline='') as f:
 writer=csv.DictWriter(f,fieldnames=['sample_id','score']);writer.writeheader()
 for row in rows:
  if row['split'] in ('validation','test'):
   writer.writerow({'sample_id':row['sample_id'],'score':row[method]})
(out/'method.txt').write_text('TEST FIXTURE. Fixed feature lookup tests recomputation and comparison wiring. No training or population claim.')
(out/'result.json').write_text(json.dumps({'experiment_id':eid,'seed':seed,'config':{'method':method},'predictions':'predictions.csv','method_evidence':'method.txt'}))
'''


class ComparisonLifecycleTests(unittest.TestCase):
    """Exercise raw signed runs, metric recomputation and comparison decisions."""
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        temporary_root = Path(self.tmp.name)
        self.root = temporary_root / 'workspace'
        self.plan = fixture(self.root)
        self.keys = mock.patch.dict('os.environ', {
            'FACTORY_SUPERVISOR_KEY': str(temporary_root / 'supervisor' / 'key')})
        self.keys.start()
        self.quiet = contextlib.redirect_stdout(io.StringIO())
        self.quiet.__enter__()

    def tearDown(self):
        self.quiet.__exit__(None, None, None)
        self.keys.stop()
        self.tmp.cleanup()

    def configure(self, *, sampling_unit='test_group', same_predictions=False):
        (self.root / 'source/run.py').write_text(LABEL_FREE_COMPARISON_SCRIPT)
        feature_path = self.root / 'data/input_features.csv'
        with feature_path.open('w', newline='') as stream:
            writer = csv.DictWriter(stream, fieldnames=['sample_id', 'split', 'a', 'b'])
            writer.writeheader()
            for index in range(12):
                position = index % 4
                a = [.2, .8, .2, .8][position]
                b = a if same_predictions else [.2, .8, .6, .6][position]
                writer.writerow({'sample_id': f's{index}',
                                 'split': ['train', 'validation', 'test'][index//4],
                                 'a': a, 'b': b})
        template = self.plan['experiments'][0]
        experiments, pairs = [], []
        for seed in range(5):
            pair = []
            for method in ('a', 'b'):
                experiment = copy.deepcopy(template)
                experiment.update(id=f'{method}{seed}', model=method, seed=seed,
                                  role='control', config={'method': method})
                experiment['command'].append(method)
                experiments.append(experiment)
                pair.append(experiment['id'])
            pairs.append(pair)
        self.plan['experiments'] = experiments
        self.plan['claims'][0]['experiment_ids'] = [e['id'] for e in experiments]
        self.plan['comparisons'] = [{
            'id': 'lookup_contrast', 'pairs': pairs, 'metric': 'accuracy',
            'sampling_unit': sampling_unit, 'assertion': 'inconclusive', 'alpha': .05,
            'minimum_effect': 0, 'max_ci_width': 2, 'inference_draws': 1000,
            'inference_scope': ('fixed_test_corpus' if sampling_unit == 'seed_fixed_test'
                                else 'test_population_conditional_on_trained_models')}]
        write_json(self.root / g.ROOT_PLAN, self.plan)

    def execute_and_audit(self):
        self.assertEqual(g.freeze(self.root), 0)
        for experiment in self.plan['experiments']:
            self.assertEqual(g.run_exp(self.root, experiment['id']), 0)
        _, epoch, freeze = g.active(self.root)
        return Audit(self.root, g.plan_at(self.root), epoch, freeze, g.engine_hash()).run()

    def test_group_comparison_uses_label_free_executed_predictions(self):
        self.configure()
        report = self.execute_and_audit()
        self.assertEqual(report['errors'], [])
        comparison = report['comparisons'][0]
        self.assertEqual(comparison['sampling_unit'], 'test_group')
        self.assertEqual(comparison['n_units'], 4)
        self.assertEqual(comparison['n_seed_pairs'], 5)
        self.assertEqual(comparison['effect'], .25)
        self.assertEqual(comparison['p_raw'], 1)
        self.assertEqual(comparison['decision'], 'inconclusive')
        self.assertEqual(comparison['p_holm'], 1)
        self.assertEqual(report['computed_runs']['a0']['metrics']['test']['accuracy'], 1)
        self.assertEqual(report['computed_runs']['b0']['metrics']['test']['accuracy'], .75)
        self.assertTrue(all(run['receipt_verified'] for run in report['computed_runs'].values()))
        _, epoch, _ = g.active(self.root)
        result = read_json(epoch / 'runs/a0/attempt0001/result.json')
        self.assertNotIn('reported_metrics', result)
        with (epoch / 'runs/a0/attempt0001/predictions.csv').open() as stream:
            self.assertEqual(next(csv.reader(stream)), ['sample_id', 'score'])

    def test_fixed_corpus_null_preserves_conditional_scope(self):
        self.configure(sampling_unit='seed_fixed_test', same_predictions=True)
        report = self.execute_and_audit()
        self.assertEqual(report['errors'], [])
        comparison = report['comparisons'][0]
        self.assertEqual(comparison['effect'], 0)
        self.assertEqual(comparison['p_raw'], 1)
        self.assertEqual(comparison['decision'], 'inconclusive')
        self.assertEqual(comparison['inference_scope'], 'fixed_test_corpus')
        self.assertEqual(comparison['n_units'], 5)

    def test_fixed_corpus_population_claim_is_blocked_before_runs(self):
        self.configure(sampling_unit='seed_fixed_test', same_predictions=True)
        claim = self.plan['claims'][0]
        claim.update(kind='comparative', comparison_id='lookup_contrast',
                     population='future independently sampled patients',
                     inference_scope='test_population_conditional_on_trained_models')
        write_json(self.root / g.ROOT_PLAN, self.plan)
        with self.assertRaisesRegex(EvidenceError, 'fixed_test_corpus'):
            g.freeze(self.root)
        self.assertFalse((self.root / g.STATE).exists())


class MutationCriticalGuardsTests(unittest.TestCase):
    """Isolate policy decisions that broader rejection assertions can obscure."""
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name) / 'workspace'
        self.plan = fixture(self.root)
        self.keys = mock.patch.dict('os.environ', {
            'FACTORY_SUPERVISOR_KEY': str(Path(self.tmp.name) / 'keys' / 'supervisor.key')})
        self.keys.start()
        self.quiet = contextlib.redirect_stdout(io.StringIO())
        self.quiet.__enter__()

    def tearDown(self):
        self.quiet.__exit__(None, None, None)
        self.keys.stop()
        self.tmp.cleanup()

    def auditor(self):
        return Audit(self.root, self.plan, self.root, {}, g.engine_hash())

    def comparison_plan(self):
        builder = PlanBoundaryTests(methodName='test_numeric_strings_and_unknown_split_rejected')
        builder.plan = self.plan
        return builder.comparison_plan(6)

    def test_duplicate_cohort_identity_is_rejected_directly(self):
        path = self.root / 'data/cohort.csv'
        path.write_text(path.read_text()+'s8,0,g8,test,r8\n')
        with self.assertRaisesRegex(EvidenceError, 'duplicate sample_id'):
            self.auditor().cohort()

    def test_duplicate_source_identity_is_rejected_directly(self):
        path = self.root / 'data/source_records.csv'
        path.write_text(path.read_text()+'r0,fixture\n')
        with self.assertRaisesRegex(EvidenceError, 'duplicate source record_id'):
            self.auditor().cohort()

    def test_duplicate_prediction_is_rejected_with_complete_membership(self):
        from test_audit_integrity import AuditIntegrityTests
        g.freeze(self.root)
        self.assertEqual(g.run_exp(self.root, 'known'), 0)
        _, epoch, freeze = g.active(self.root)
        attempt = epoch / 'runs/known/attempt0001'
        predictions = attempt / 'predictions.csv'
        predictions.write_text(predictions.read_text()+'s8,0,0.2\n')
        signer = AuditIntegrityTests(methodName='test_duplicate_predictions_with_valid_signature')
        signer.root, signer.attempt = self.root, attempt
        signer.trusted_resign(read_json(attempt / 'execution.json'))
        auditor = Audit(self.root, self.plan, epoch, freeze, g.engine_hash())
        auditor.cohort()
        with self.assertRaisesRegex(EvidenceError, 'duplicate prediction id'):
            auditor.experiment(self.plan['experiments'][0])

    def test_receipt_verification_is_required_in_the_run_validator(self):
        g.freeze(self.root)
        self.assertEqual(g.run_exp(self.root, 'known'), 0)
        _, epoch, freeze = g.active(self.root)
        record_path = epoch / 'runs/known/attempt0001/execution.json'
        record = read_json(record_path)
        record['supervisor_receipt']['supervisor_signature'] = '00'*64
        write_json(record_path, record)
        auditor = Audit(self.root, self.plan, epoch, freeze, g.engine_hash())
        auditor.cohort()
        with self.assertRaises(EvidenceError):
            auditor.experiment(self.plan['experiments'][0])

    def test_engine_freeze_binding_is_checked_before_run_validation(self):
        g.freeze(self.root)
        _, epoch, freeze = g.active(self.root)
        auditor = Audit(self.root, self.plan, epoch, freeze, g.engine_hash())
        auditor.frozen()
        auditor.engine_hash = '0'*64
        with self.assertRaisesRegex(EvidenceError, 'active factory code changed'):
            auditor.frozen()

    def test_plan_snapshot_is_checked_before_history_validation(self):
        g.freeze(self.root)
        _, epoch, freeze = g.active(self.root)
        snapshot = read_json(epoch / 'research_plan_snapshot.json')
        snapshot['population'] = 'An altered snapshot of the declared fixture population'
        write_json(epoch / 'research_plan_snapshot.json', snapshot)
        with self.assertRaisesRegex(EvidenceError, 'frozen plan snapshot changed'):
            Audit(self.root, self.plan, epoch, freeze, g.engine_hash()).frozen()

    def test_repetitive_padding_is_rejected_even_with_an_evidence_citation(self):
        reasoning = 'project/methodology.md source data metrics training fixture scope evidence '*20
        with self.assertRaisesRegex(EvidenceError, 'repetitive or placeholder'):
            _review_text(reasoning, 'method_identity')

    def test_stale_review_digest_has_a_specific_rejection(self):
        from test_audit_integrity import AuditIntegrityTests
        audit = {'evidence_digest': 'a'*64, 'diagnostics': [],
                 'file_bindings': {'project/methodology.md': sha(self.root / 'project/methodology.md')}}
        builder = AuditIntegrityTests(methodName='test_padding_review_blocks')
        builder.root = self.root
        review = builder.review(audit)
        write_json(self.root / 'project/review.json', review)
        verify_review(self.root, self.plan, audit)
        review['evidence_digest'] = 'b'*64
        write_json(self.root / 'project/review.json', review)
        with self.assertRaisesRegex(EvidenceError, 'review stale'):
            verify_review(self.root, self.plan, audit)

    def test_added_source_cannot_evade_directory_freezing(self):
        self.plan['frozen_paths'] = ['source/run.py', 'source/requirements.lock',
                                     'data', 'project/methodology.md']
        with self.assertRaisesRegex(EvidenceError, 'freeze the whole source directory'):
            validate(self.root, self.plan)

    def test_schema_version_must_be_an_integer(self):
        self.plan['schema_version'] = 3.0
        with self.assertRaises(ValidationError):
            validate(self.root, self.plan)

    def test_seed_scope_is_required_without_comparative_prose(self):
        plan = self.comparison_plan()
        plan['comparisons'][0]['inference_scope'] = 'future_population'
        with self.assertRaisesRegex(EvidenceError, 'explicit inference_scope'):
            validate(self.root, plan)

    def test_distinct_experiment_ids_do_not_make_duplicate_seeds_independent(self):
        plan = self.comparison_plan()
        plan['experiments'][2]['seed'] = 0
        plan['experiments'][3]['seed'] = 0
        with self.assertRaisesRegex(EvidenceError, 'paired seeds mismatch or duplicate'):
            validate(self.root, plan)


class MutationRunnerTests(unittest.TestCase):
    def test_exact_ast_mutation_preserves_unicode_and_surrounding_code(self):
        from run_mutation_checks import apply_mutation
        source = 'def check():\n    label = "π"; need(False, "guard"); return label\n'
        changed, location = apply_mutation(source, {
            'function': 'check', 'call': 'need', 'marker': 'guard', 'replacement': 'None'})
        namespace = {}
        exec(compile(changed, '<isolated mutation>', 'exec'), namespace)
        self.assertEqual(namespace['check'](), 'π')
        self.assertEqual(location['deleted_call'], 'need(False, "guard")')

    def test_ambiguous_or_missing_mutation_targets_are_errors(self):
        from run_mutation_checks import apply_mutation
        source = 'def check():\n    need(False, "guard"); need(False, "guard")\n'
        with self.assertRaisesRegex(ValueError, 'found 2'):
            apply_mutation(source, {'function': 'check', 'call': 'need',
                                    'marker': 'guard', 'replacement': 'None'})
        with self.assertRaisesRegex(ValueError, 'found 0'):
            apply_mutation(source, {'function': 'check', 'call': 'need',
                                    'marker': 'missing', 'replacement': 'None'})


if __name__ == '__main__':
    unittest.main()
