import contextlib, io, json, sys, tempfile, unittest
from pathlib import Path
FACTORY = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(FACTORY))
import gatekeeper as g
from engine.io import read_json
from tests.test_v3 import SCRIPT, fixture

# Same-directory temp paths so the suite is invocation-independent: it passes
# whether run via run_self_tests.py from the repo root or via
# `python -m unittest discover` from inside factory/.
HERE = Path(__file__).resolve().parent

class V31HardeningTests(unittest.TestCase):
    def test_coverage_liveness_is_clean(self):
        code, report = g.verify_coverage_liveness(FACTORY, quiet=True)
        self.assertEqual(code, 0)
        self.assertEqual(report['principles_checked'], 23)
        self.assertEqual(report['callables_resolved'], 23)

    def test_check_contract_rejects_keyword_theater(self):
        with self.subTest('prose is not a contract'):
            p = HERE / '.tmp_contract.md'
            try:
                p.write_text('verify-contract lint-contract recompute')
                self.assertEqual(g.check_contract(p), 17)
            finally:
                p.unlink(missing_ok=True)

    def test_check_contract_requires_bound_executable_checks(self):
        p = HERE / '.tmp_contract.json'
        try:
            p.write_text(json.dumps({'checks':[{'command':'audit','artifacts':['project/audit_report.json']}]}))
            self.assertEqual(g.check_contract(p), 0)
        finally:
            p.unlink(missing_ok=True)

    def test_statistical_protocol_is_value_level(self):
        p = HERE / '.tmp_stats.json'
        try:
            p.write_text(json.dumps({'primary_metric':'average_precision','sampling_unit':'seed_fixed_test','test':'permutation','alpha':0.05,'effect_size':0.2,'confidence_interval':[0.1,0.3],'multiplicity_correction':'Holm'}))
            self.assertEqual(g.verify_statistical_protocol(p), 0)
        finally:
            p.unlink(missing_ok=True)

    def test_failure_taxonomy_requires_traced_categories(self):
        p = HERE / '.tmp_failures.json'
        try:
            p.write_text(json.dumps({'failures':[{'category':'a','candidate_ids':['s1'],'prevalence':0.1,'severity':'SEV-2'}]}))
            self.assertEqual(g.verify_failure_taxonomy(p), 30)
        finally:
            p.unlink(missing_ok=True)


# A function matching the scanner's own trigger definition: an unused,
# data-like parameter, a literal-dense dict, and a return from a
# build_/compute_/generate_/analyze_/evaluate_-named function. This is
# appended to the working fixture script so the run still executes
# successfully; the scanner is static and does not care whether the
# fabricated function is ever called.
PHANTOM_INPUT_TAIL = '''
def build_results(unused_flag):
    return {'a':1,'b':2,'c':3,'d':4,'e':5,'f':6,'g':7,'h':8,'i':9,'j':10,'k':11,'l':12,'m':13,'n':14,'o':15,'p':16}
'''

class AcquisitionAuditBlocksCertifyTests(unittest.TestCase):
    """Regression guard for the acquisition scanner's wiring into certify().
    This is the fix that mattered most in v3.1.0 and had no end-to-end test:
    a phantom-input-fabrication pattern in a declared code_path must reach
    certify() as a hard, blocking error, not just as something the standalone
    scanner can detect if invoked manually."""
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(); self.r = Path(self.tmp.name)
        self.p = fixture(self.r)
        (self.r / 'source/run.py').write_text(SCRIPT + PHANTOM_INPUT_TAIL)
        self.redirect = contextlib.redirect_stdout(io.StringIO()); self.redirect.__enter__()

    def tearDown(self):
        self.redirect.__exit__(None, None, None); self.tmp.cleanup()

    def test_certify_blocks_on_fabricated_result_sink(self):
        g.freeze(self.r)
        self.assertEqual(g.run_exp(self.r, 'known'), 0)
        code = g.certify(self.r)
        self.assertNotEqual(code, 0)
        report = read_json(self.r / 'project/audit_report.json')
        codes = [e.get('code') for e in report.get('errors', [])]
        self.assertIn('ACQUISITION_AUDIT', codes)

    def test_scanner_finds_nothing_in_the_unmodified_fixture(self):
        """Negative control: the same lifecycle on the real fixture script,
        with no fabrication pattern added, must not trip the scanner. Without
        this, the positive test above could pass for the wrong reason (e.g.
        certify failing on something unrelated)."""
        (self.r / 'source/run.py').write_text(SCRIPT)
        g.freeze(self.r)
        self.assertEqual(g.run_exp(self.r, 'known'), 0)
        g.certify(self.r)
        report = read_json(self.r / 'project/audit_report.json')
        codes = [e.get('code') for e in report.get('errors', [])]
        self.assertNotIn('ACQUISITION_AUDIT', codes)
