"""Authored offline contracts and arithmetic only; no protected inputs or workers."""
import copy
import importlib.util
import json
import math
import os
from pathlib import Path
import statistics
import sys
import tempfile
import unittest
from unittest.mock import Mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'scripts'))
import finite_confirmation_analysis as f


def register():
    return dict(schema='balanced-measurement-stability-endpoint-register/v1',
                baseline_codec=f.BASELINE, candidate_codec=f.CANDIDATE,
                endpoints=[dict(id=f'endpoint-{i:02}', case_id='authored-RGB16', operation='encode', style=1, workers=8,
                                role='sole_primary' if i == 0 else 'critical_non_regression',
                                upper_relative_99=dict(operator='<' if i == 0 else '<=', value=-.05 if i == 0 else .01),
                                absolute_mean_saving_ms=dict(operator='>=', value=10) if i == 0 else None,
                                owner_field=dict(retained='unmodified')) for i in range(28)],
                unchanged_allocation_matrix=dict(initial_calls=32, conditional_calls=80,
                    initial_cases=['authored-boca', 'authored-mansfield'],
                    conditional_cases=['authored-pan', 'authored-rgb16', 'authored-ms', 'authored-tok', 'authored-vegas'],
                    styles=[0, 1], workers=[1, 2, 4, 8], arms=['baseline', 'candidate']))


def rows(n=40, candidate=80_000_000):
    return [dict(round=r, arm=arm, position=p, result=dict(status=0, observation=dict(
                    exact=True, samples_ns=[100_000_000 if arm == 'A' else candidate])))
            for r in range(n) for p, arm in enumerate('AB' if r % 2 == 0 else 'BA')]


def estimator(payload):
    """Independent authored arithmetic for control-flow probes; real routes below."""
    a, b = payload['baseline'], payload['candidate']
    n = len(a)
    q = {40: 3.030, 160: 2.860}[n]
    x, y = statistics.mean(a), statistics.mean(b)
    mx, my = (q*statistics.stdev(v)/math.sqrt(n) for v in (a, b))
    result = dict(baseline_mean_ns=x, candidate_mean_ns=y, verdict='inconclusive')
    if x-mx > 0 and y-my > 0:
        lo, hi = (y-my)/(x+mx)-1, (y+my)/(x-mx)-1
        result.update(relative_interval_99=[lo, hi], relative_change=y/x-1)
        result['verdict'] = ('regressed' if lo > .05 else 'improved' if hi < -.05 else
                             'equivalent' if lo >= -.05 and hi <= .05 else 'inconclusive')
    return result


def session(lower, upper, x=200_000_000, y=180_000_000):
    output = dict(baseline_mean_ns=x, candidate_mean_ns=y, verdict='inconclusive',
                  relative_interval_99=[lower, upper] if upper is not None else None)
    return dict(valid=True, complete=True, estimator={'B_over_A': dict(output=output, lower=lower, upper=upper)})


class FiniteTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.register_path, self.design_path = self.root/'register.json', self.root/'design.json'
        self.register_path.write_text(json.dumps(register()))
        self.design_path.write_text(json.dumps(dict(authored='source/correctness/resource owner binding')))
        self.manifest = f.make_manifest(self.register_path, self.design_path)
        self.schedule = sorted((p for stage in ('allocation', 'preflight', 'ordinary')
                                for p in self.manifest['schedule'][stage]), key=lambda p: p['index'])

    def attempt(self, records, **kwargs):
        return f.analyse_attempt(self.manifest, records, {40: estimator, 160: estimator},
            checks=kwargs.pop('checks', dict.fromkeys(f.CHECKS, True)),
            consumption=kwargs.pop('consumption', dict(started_calls=len(records), wall_seconds=100,
                                                     evidence_bytes=100, build_bytes=100)), **kwargs)

    def receipts(self, through=27, candidate=80_000_000):
        last = max(p['index'] for p in self.schedule if p['endpoint_id'] == f'endpoint-{through:02}')
        return [dict(planned=copy.deepcopy(p), gates_passed=True,
                     result=dict(status=0, observation=dict(exact=True, samples_ns=[
                         100_000_000 if p['arm'] == 'baseline' else candidate]))) for p in self.schedule[:last+1]]

    def test_full_counts_order_prerequisites_and_import_immutability(self):
        m = self.manifest
        self.assertEqual(m['endpoints'], register()['endpoints'])
        self.assertEqual([len(m['schedule'][s]) for s in ('allocation', 'preflight', 'ordinary')], [112, 56, 2480])
        self.assertEqual(len(self.schedule), 2648)
        self.assertEqual([p['index'] for p in self.schedule], list(range(2648)))
        self.assertEqual(len(set(m['schedule']['call_order'])), 2648)
        self.assertEqual(m['schedule']['call_order'], [p['call_id'] for p in self.schedule])
        self.assertEqual(m['pairs_per_endpoint'], [40]*11+[160]+[40]*16)
        self.assertEqual(m['endpoint_order'], [0, 2, 1, 3, 10, 11, 4, 5, 6, 7, 8, 9, *range(12, 28)])
        for index, count in enumerate(m['pairs_per_endpoint']):
            ordinary = [p for p in m['schedule']['ordinary'] if p['endpoint_id'] == f'endpoint-{index:02}']
            self.assertEqual(len(ordinary), 2*count)
            expected = ['baseline', 'candidate', 'candidate', 'baseline']*(count//2)
            self.assertEqual([p['arm'] for p in ordinary], expected)
            block = [p for p in self.schedule if p['endpoint_id'] == f'endpoint-{index:02}']
            self.assertEqual([p['stage'] for p in block[:2]], ['preflight']*2)
            self.assertTrue(all(p['stage'] == 'allocation' for p in block[2:-2*count]))
        self.assertEqual([p['endpoint_id'] for p in m['schedule']['allocation'][::16]],
                         ['endpoint-00', 'endpoint-00', 'endpoint-10', 'endpoint-04', 'endpoint-12', 'endpoint-16', 'endpoint-24'])
        self.assertEqual([(p['style'], p['workers'], p['arm']) for p in m['schedule']['allocation'][:16]],
                         [(s, w, a) for s in (0, 1) for w in (1, 2, 4, 8) for a in ('baseline', 'candidate')])

    def test_manifest_register_source_and_comparator_digest_binding(self):
        path = self.root/'manifest.json'
        path.write_text(json.dumps(self.manifest))
        digest = f.sha(path)
        self.assertEqual(f.load_manifest(path, digest, self.register_path, self.design_path), self.manifest)
        path.write_text(path.read_text()+'\n')
        with self.assertRaisesRegex(ValueError, 'digest'):
            f.load_manifest(path, digest, self.register_path, self.design_path)
        path.write_text(json.dumps(self.manifest))
        self.design_path.write_text('changed source design')
        with self.assertRaisesRegex(ValueError, 'binding'):
            f.load_manifest(path, f.sha(path), self.register_path, self.design_path)
        self.design_path.write_text(json.dumps(dict(authored='source/correctness/resource owner binding')))
        for field, value in [('endpoint_order', list(range(28))), ('pairs_per_endpoint', [40]*28),
                             ('endpoints', self.manifest['endpoints'][:-1]),
                             ('sources', dict(self.manifest['sources'], comparator_sha256='0'*64))]:
            changed = dict(self.manifest, **{field: value})
            path.write_text(json.dumps(changed))
            with self.assertRaises(ValueError):
                f.load_manifest(path, f.sha(path), self.register_path, self.design_path)

    def test_directionality_thresholds_and_uncertainty(self):
        tests = [(False, -.2, .01, 100_000_000, 80_000_000, f.PASS),
                 (False, -.01, .02, 100_000_000, 101_500_000, f.NOT_QUALIFIED),
                 (False, .01, .03, 100_000_000, 102_000_000, f.NOT_QUALIFIED),
                 (False, .0101, .03, 100_000_000, 102_000_000, f.NOT_SELECTED),
                 (True, -.2, -.05, 200_000_000, 180_000_000, f.NOT_QUALIFIED),
                 (True, -.2, -.0501, 100_000_000, 90_000_000, f.PASS),
                 (True, -.2, -.0501, 100_000_000, 90_000_001, f.NOT_SELECTED),
                 (True, -.05, -.02, 300_000_000, 288_000_000, f.NOT_SELECTED),
                 (True, None, None, 200_000_000, 180_000_000, f.NOT_QUALIFIED)]
        for primary, lo, hi, x, y, expected in tests:
            with self.subTest(primary=primary, lo=lo, hi=hi, y=y):
                result = f.endpoint_decision(session(lo, hi, x, y), primary)
                self.assertEqual(result['disposition'], expected)
                self.assertEqual(result['legacy_timing_verdict'], 'inconclusive')
        result = f.analyse_endpoint(1, rows(candidate=97_000_000), estimator)
        self.assertEqual(result['disposition'], f.PASS)
        self.assertEqual(result['legacy_timing_verdict'], 'equivalent')
        self.assertEqual(f.analysis.classify_cell([result['analysis']]*3), f.analysis.NOT_DEMONSTRATED)
        null = rows()
        for row in null:
            row['result']['observation']['samples_ns'] = [95_000_000 if row['round'] % 2 == 0 else 105_000_000]
        null_result = f.analyse_endpoint(1, null, estimator)
        self.assertEqual(f.analysis.classify_cell([null_result['analysis']]*3), f.analysis.NOT_DEMONSTRATED)
        faster = copy.deepcopy(null)
        for row in faster:
            if row['arm'] == 'B': row['result']['observation']['samples_ns'][0] -= 10_000_000
        self.assertEqual(f.analyse_endpoint(1, faster, estimator)['disposition'], f.PASS)

    def test_no_interim_160_inference_at_40_or_80_and_no_replacements(self):
        for n in (40, 80, 159, 161):
            mock = Mock()
            result = f.analyse_endpoint(11, rows(n), mock)
            self.assertEqual(result['disposition'], f.INCOMPLETE)
            self.assertEqual(len(result['analysis']['raw_rows']), 2*n)
            mock.assert_not_called()
        self.assertEqual(f.analyse_endpoint(11, rows(160), estimator)['disposition'], f.PASS)
        for bad in (rows()[:-1], rows()+rows()[:1], [rows()[1], rows()[0]]+rows()[2:]):
            self.assertEqual(f.analyse_endpoint(0, bad, Mock())['disposition'], f.INCOMPLETE)

    def test_failure_and_missing_data_retained_without_success_subset(self):
        records = self.receipts(0)
        records[-1]['result'] = dict(status='timeout', reason='authored timeout')
        result = self.attempt(records)
        self.assertEqual(result['disposition'], f.INCOMPLETE)
        self.assertEqual(result['raw_rows'], records)
        self.assertEqual(result['endpoints'][0]['analysis']['raw_rows'][-1]['result'], records[-1]['result'])
        self.assertTrue(all(e['status'] == 'unstarted' for e in result['endpoints'][1:]))
        for damage in ('missing', 'duplicate', 'failed-allocation', 'failed-preflight', 'missing-result'):
            records = self.receipts(0)
            if damage == 'missing': removed = records.pop(50)
            elif damage == 'duplicate': records[50] = copy.deepcopy(records[49])
            elif damage == 'missing-result': records[-1].pop('result')
            else: records[2 if damage == 'failed-allocation' else 0]['gates_passed'] = False
            result = self.attempt(records)
            self.assertEqual(result['disposition'], f.INCOMPLETE)
            self.assertEqual(result['raw_rows'], records)
            if damage == 'missing': self.assertIn(removed['planned']['call_id'], result['missing_call_ids'])

    def test_stop_leaves_later_endpoints_unstarted_and_cannot_hide_unresolved_secondary(self):
        records = self.receipts(0, candidate=95_000_000)
        result = self.attempt(records)
        self.assertEqual(result['disposition'], f.NOT_SELECTED)
        self.assertTrue(all(e['status'] == 'unstarted' for e in result['endpoints'][1:]))
        self.assertEqual(len(result['missing_call_ids']), 2648-len(records))
        result = self.attempt(self.receipts(0))
        self.assertEqual(result['endpoints'][0]['disposition'], f.PASS)
        self.assertEqual(result['disposition'], f.INCOMPLETE)
        records = self.receipts(2)
        for row in records:
            p = row['planned']
            if p['endpoint_id'] == 'endpoint-02' and p['stage'] == 'ordinary' and p['arm'] == 'candidate':
                row['result']['observation']['samples_ns'] = [90_000_000 if p['round'] % 2 == 0 else 113_000_000]
        result = self.attempt(records)
        self.assertEqual(result['endpoints'][0]['disposition'], f.PASS)
        self.assertEqual(result['endpoints'][1]['disposition'], f.NOT_QUALIFIED)
        self.assertEqual(result['disposition'], f.NOT_QUALIFIED)
        self.assertTrue(all(e['status'] == 'unstarted' for e in result['endpoints'][2:]))
        result = self.attempt(self.receipts(2, candidate=95_000_000))
        self.assertEqual(result['disposition'], f.INCOMPLETE)
        self.assertIn('later calls', result['issues'][0])

    def test_full_offline_coverage_does_not_authorise_live_promotion(self):
        result = self.attempt(self.receipts())
        self.assertEqual(result['disposition'], f.PASS)
        self.assertEqual(len(result['endpoints']), 28)
        self.assertEqual(result['missing_call_ids'], [])
        self.assertFalse(result['promotion_authorised'])
        for check in f.CHECKS:
            result = self.attempt(self.receipts(), checks={k: k != check for k in f.CHECKS})
            self.assertEqual(result['disposition'], f.INCOMPLETE)

    def test_caps_headroom_and_zero_start_decline(self):
        counter = dict(started_calls=2647, wall_seconds=7050, evidence_bytes=2*1024**3-1024**2, build_bytes=30*1024**3)
        self.assertEqual(f.budget_issues(counter, before_start=True), [])
        for key in counter:
            self.assertTrue(f.budget_issues(dict(counter, **{key: counter[key]+1}), before_start=True))
        for key, cap in [('wall_seconds', 7200), ('evidence_bytes', 2*1024**3), ('build_bytes', 30*1024**3)]:
            consumption=dict(started_calls=114, wall_seconds=0, evidence_bytes=0, build_bytes=0)
            consumption[key] = cap+1
            self.assertEqual(self.attempt(self.receipts(0), consumption=consumption)['disposition'], f.INCOMPLETE)
        result = self.attempt([], declined_reason='No fresh reservation; no launch')
        self.assertEqual(result['disposition'], f.DECLINED)
        self.assertEqual(result['started_calls'], 0)
        self.assertEqual(len(result['endpoints']), 28)
        self.assertTrue(all(e['status'] == 'unstarted' and e['baseline_mean_ns'] is None
                            and e['candidate_mean_ns'] is None and e['relative_interval_99'] is None for e in result['endpoints']))
        with self.assertRaisesRegex(ValueError, 'zero starts'):
            self.attempt(self.receipts(0), declined_reason='invalid declaration')


@unittest.skipUnless(os.environ.get('FINITE_ESTIMATOR_40') and os.environ.get('FINITE_ESTIMATOR_160'),
                     'owner supplies both compiled comparator wrappers for integration')
class ActualComparatorTests(unittest.TestCase):
    def test_both_fixed_count_routes_use_unchanged_owner_in_both_directions(self):
        spec = importlib.util.spec_from_file_location('finite_stability', Path(__file__).resolve().parents[1]/'scripts/measurement-stability.py')
        stability = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(stability)
        for count, index in ((40, 0), (160, 11)):
            executable = Path(os.environ[f'FINITE_ESTIMATOR_{count}'])
            identity = stability.estimator_identity(executable, rounds=count)
            self.assertEqual(identity['provenance']['owner_sha256'], f.sha(f.analysis.COMPARE_SOURCE))
            records = rows(count)
            for row in records:
                row['result']['observation']['samples_ns'][0] += (row['round'] % 3)*100_000
            actual = f.analyse_endpoint(index, records, executable)
            expected = f.analyse_endpoint(index, records, estimator)
            self.assertEqual(actual['disposition'], expected['disposition'])
            for direction in ('B_over_A', 'A_over_B'):
                a = actual['analysis']['estimator'][direction]
                e = expected['analysis']['estimator'][direction]
                self.assertEqual(a['returncode'], 0)
                self.assertEqual(a['output']['verdict'], e['output']['verdict'])
                for key in ('baseline_mean_ns', 'candidate_mean_ns'):
                    self.assertAlmostEqual(a['output'][key], e['output'][key], places=7)
                for av, ev in zip(a['output']['relative_interval_99'], e['output']['relative_interval_99']):
                    self.assertAlmostEqual(av, ev, places=12)
            with self.assertRaises(ValueError):
                stability.estimator_identity(executable, rounds=160 if count == 40 else 40)


if __name__ == '__main__':
    unittest.main()
