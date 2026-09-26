"""Offline assessment contract, stop policy and historical isolation checks."""
import copy
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock, patch

import finite_confirmation_analysis as finite
import finite_confirmation_live as live
import finite_confirmation_report as report
import integration_assessment as assessment
import test_finite_confirmation_analysis as authored
import test_finite_confirmation_live as acquisition


class AssessmentTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        root = Path(temporary.name)
        self.register, self.design, self.v1 = (root/name for name in ('register.json', 'design.json', 'v1.json'))
        inherited = authored.register()
        for row in inherited['endpoints']:
            row.update(origin='emuella', raw_sha256='1'*64, stream_sha256='2'*64)
        self.register.write_text(json.dumps(inherited))
        self.design.write_text('{}')
        self.original = finite.make_manifest(self.register, self.design)
        self.v1.write_text(json.dumps(self.original))
        old_source = dict(schema='classic-forward53-parallel-dispatch-source/v1',
            recorded_production_codec=finite.BASELINE, baseline_codec=finite.DISPATCH_BASELINE,
            donor_codec=finite.CANDIDATE, candidate_codec='f'*40,
            baseline_tree='1'*40, donor_tree='2'*40, candidate_tree='3'*40,
            production_to_candidate_diff_sha256='1'*64,
            donor_to_candidate_diff_sha256='2'*64, recorded_to_baseline_diff_sha256='3'*64)
        old_review = json.dumps(dict(schema='classic-forward53-parallel-dispatch-source-review/v1',
            verdict='PASS', reviewer='independent reviewer', locator='old review',
            sources={key:old_source[key] for key in finite.SOURCE_FIELDS}))
        old_source['independent_review'] = dict(path=str(root/'old-review.json'),
            sha256=hashlib.sha256(old_review.encode()).hexdigest())
        old_text = json.dumps(old_source)
        self.predecessor = root/'dispatch.json'
        self.predecessor.write_text(json.dumps(live.derive_dispatch(self.v1, finite.sha(self.v1),
            self.register, self.design, 'old authority', old_text,
            hashlib.sha256(old_text.encode()).hexdigest(), old_review)))
        self.source = dict(schema=assessment.SOURCE_SCHEMA, baseline_codec='a'*40,
            candidate_codec='b'*40, baseline_tree='c'*40, candidate_tree='d'*40,
            baseline_to_candidate_diff_sha256='e'*64)
        review = dict(schema=assessment.REVIEW_SCHEMA, verdict='PASS', reviewer='independent reviewer',
                      locator='reviewed source', sources={k:self.source[k] for k in assessment.SOURCE_FIELDS})
        self.review_text = json.dumps(review)
        self.source['independent_review'] = dict(path=str(root/'source-review.json'),
            sha256=hashlib.sha256(self.review_text.encode()).hexdigest())
        self.source_text = json.dumps(self.source)
        self.policy = dict(schema=assessment.REGISTER_SCHEMA, policy=assessment.SCHEMA,
            predecessor=dict(sha256=finite.sha(self.predecessor)), order=list(finite.ORDER),
            repeats=[f'endpoint-{i:02}' for i in assessment.REPEATS], endpoints=[])
        for index, old in enumerate(self.original['endpoints']):
            row = {key:old[key] for key in ('id', 'case_id', 'operation', 'style', 'workers', 'origin',
                                           'raw_sha256', 'stream_sha256')}
            row.update(role='sole_primary' if index == 0 else 'secondary',
                       old_upper_relative_99=old['upper_relative_99'],
                       new_upper_relative_99=dict(operator='<' if index == 0 else '<=',
                                                   value=-.05 if index == 0 else .05),
                       old_absolute_mean_saving_ms=old['absolute_mean_saving_ms'],
                       new_absolute_mean_saving_ms=old['absolute_mean_saving_ms'])
            self.policy['endpoints'].append(row)
        self.policy_text = json.dumps(self.policy)
        self.manifest = self.derive()
        self.schedule = assessment.ordered(self.manifest)

    def derive(self, **values):
        inputs = dict(source_text=self.source_text, source_sha=hashlib.sha256(self.source_text.encode()).hexdigest(),
                      review_text=self.review_text, policy_text=self.policy_text,
                      policy_sha=hashlib.sha256(self.policy_text.encode()).hexdigest())
        inputs.update(values)
        return assessment.derive(self.v1, finite.sha(self.v1), self.register, self.design,
                                 self.predecessor, finite.sha(self.predecessor),
                                 'reviewed assessment authority', **inputs)

    def rows(self, count=2900, *, changes=None):
        changes = changes or {}
        result = []
        for planned in self.schedule[:count]:
            endpoint = planned['endpoint_id']
            candidate = changes.get(endpoint, 80_000_000)
            result.append(dict(planned=copy.deepcopy(planned), gates_passed=True,
                result=dict(status=0, observation=dict(exact=True,
                    samples_ns=[100_000_000 if planned['arm'] == 'baseline' else candidate]))))
        return result

    def analyse(self, rows):
        return assessment.analyse_attempt(self.manifest, rows, {40: authored.estimator, 160: authored.estimator},
            checks=dict.fromkeys(assessment.CHECKS, True), consumption=dict(started_calls=len(rows),
                wall_seconds=100, evidence_bytes=100, build_bytes=100))

    def test_exact_order_count_instances_and_historical_design(self):
        self.assertEqual(len(self.schedule), 2900)
        self.assertEqual([len(self.manifest['schedule'][s]) for s in ('ordinary', 'preflight', 'allocation')],
                         [2720, 62, 118])
        self.assertEqual(self.manifest['schedule']['call_order'], [p['call_id'] for p in self.schedule])
        self.assertEqual([p['index'] for p in self.schedule], list(range(2900)))
        self.assertEqual(self.schedule[:2648], sorted((p for stage in ('ordinary', 'preflight', 'allocation')
                                   for p in self.original['schedule'][stage]), key=lambda p:p['index']))
        self.assertEqual([p['endpoint_id'] for p in self.schedule[2648::84]], ['repeat-00', 'repeat-01', 'repeat-10'])
        self.assertTrue(all(p['build_instance'] == 'repeat' for p in self.schedule[2648:]))
        self.assertEqual(live.preparation_schema(self.manifest), assessment.PREPARATION)
        self.assertEqual(self.original['limits'], finite.limits())
        self.assertNotIn('source_treatment_text', self.original)

    def test_pinned_source_review_and_tighter_margin_rejection(self):
        with self.assertRaisesRegex(ValueError, 'register'):
            self.derive(policy_sha='0'*64)
        changed = copy.deepcopy(self.policy); changed['endpoints'][1]['new_upper_relative_99']['value'] = .051
        with self.assertRaisesRegex(ValueError, 'margin'):
            self.derive(policy_text=json.dumps(changed),
                policy_sha=hashlib.sha256(json.dumps(changed).encode()).hexdigest())
        changed = copy.deepcopy(self.policy); changed['endpoints'][10]['new_upper_relative_99']['value'] = .01
        text = json.dumps(changed)
        self.assertEqual(self.derive(policy_text=text, policy_sha=hashlib.sha256(text.encode()).hexdigest())
                         ['secondary_upper_relative_99']['endpoint-10'], .01)
        with self.assertRaisesRegex(ValueError, 'digest'):
            self.derive(source_sha='0'*64)
        failed = json.dumps(dict(json.loads(self.review_text), verdict='FAIL'))
        source = dict(self.source, independent_review=dict(self.source['independent_review'],
            sha256=hashlib.sha256(failed.encode()).hexdigest()))
        text = json.dumps(source)
        with self.assertRaisesRegex(ValueError, 'review'):
            self.derive(source_text=text, source_sha=hashlib.sha256(text.encode()).hexdigest(), review_text=failed)

    def test_tighter_endpoint_override_changes_both_independent_decisions(self):
        changed = copy.deepcopy(self.policy)
        changed['endpoints'][10]['new_upper_relative_99']['value'] = .01
        text = json.dumps(changed)
        self.manifest = self.derive(policy_text=text,
            policy_sha=hashlib.sha256(text.encode()).hexdigest())
        self.schedule = assessment.ordered(self.manifest)
        result = self.analyse(self.rows(changes={'endpoint-10': 103_000_000,
                                                 'repeat-10': 103_000_000}))
        main = next(row for row in result['endpoints'] if row['endpoint_id'] == 'endpoint-10')
        repeat = next(row for row in result['repeats'] if row['endpoint_id'] == 'repeat-10')
        self.assertEqual((main['disposition'], repeat['disposition']),
                         (finite.NOT_SELECTED, finite.NOT_SELECTED))
        self.assertEqual((main['required_upper_relative_99'], repeat['required_upper_relative_99']),
                         (.01, .01))

    def test_endpoint_11_never_decides_on_an_intermediate_count(self):
        for count in (40, 80, 159):
            estimator = Mock()
            decision = assessment.analyse_endpoint(self.manifest, 'endpoint-11',
                authored.rows(count), estimator)
            self.assertEqual(decision['disposition'], finite.INCOMPLETE)
            estimator.assert_not_called()
        complete = assessment.analyse_endpoint(self.manifest, 'endpoint-11',
            authored.rows(160), authored.estimator)
        self.assertEqual(complete['disposition'], finite.PASS)

    def test_secondary_failure_continues_full_matrix_and_repeat_is_independent(self):
        rows = self.rows(changes={'endpoint-01': 107_000_000, 'repeat-10': 107_000_000})
        result = self.analyse(rows)
        self.assertEqual(result['disposition'], finite.NOT_SELECTED)
        self.assertEqual(len(result['endpoints']), 28)
        self.assertEqual(len(result['repeats']), 3)
        self.assertEqual(result['endpoints'][2]['endpoint_id'], 'endpoint-01')
        self.assertEqual(result['endpoints'][2]['disposition'], finite.NOT_SELECTED)
        self.assertEqual(result['repeats'][0]['disposition'], finite.PASS)
        self.assertEqual(result['repeats'][1]['disposition'], finite.PASS)
        self.assertEqual(result['repeats'][2]['disposition'], finite.NOT_SELECTED)
        self.assertEqual(result['missing_call_ids'], [])

    def test_repeat_primary_failure_does_not_stop_later_repeat_blocks(self):
        result = self.analyse(self.rows(changes={'repeat-00': 96_000_000}))
        self.assertEqual(result['disposition'], finite.NOT_SELECTED)
        self.assertEqual(len(result['repeats']), 3)
        self.assertEqual(result['repeats'][0]['disposition'], finite.NOT_SELECTED)
        self.assertEqual(result['repeats'][1]['disposition'], finite.PASS)
        self.assertEqual(result['repeats'][2]['disposition'], finite.PASS)

    def test_primary_failure_stops_and_later_calls_are_invalid(self):
        end = max(p['index'] for p in self.schedule if p['endpoint_id'] == 'endpoint-00')+1
        rows = self.rows(end, changes={'endpoint-00': 96_000_000})
        result = self.analyse(rows)
        self.assertEqual(result['disposition'], finite.NOT_SELECTED)
        self.assertEqual(len(result['missing_call_ids']), 2900-end)
        result = self.analyse(self.rows(changes={'endpoint-00': 96_000_000}))
        self.assertEqual(result['disposition'], finite.INCOMPLETE)
        self.assertIn('later calls after primary stop', result['issues'])

    def test_failed_call_and_cap_never_use_successful_subset(self):
        rows = self.rows()
        rows[2600]['gates_passed'] = False
        result = self.analyse(rows)
        self.assertEqual(result['disposition'], finite.INCOMPLETE)
        self.assertIn('failed mandatory call', result['issues'][0])
        self.assertIn('started_calls cap', finite.budget_issues(dict(started_calls=2901,
            wall_seconds=0, evidence_bytes=0, build_bytes=0), caps=self.manifest['limits'])[0])

    def test_live_controller_continues_after_valid_secondary_timing_failure(self):
        case = acquisition.LiveTests()
        case.setUp()
        self.addCleanup(case.doCleanups)
        case.contract = self.manifest
        outcome, calls, completion = case.acquire(unresolved='endpoint-02')
        self.assertEqual(outcome, finite.NOT_QUALIFIED)
        self.assertEqual(len(calls), 2900)
        self.assertEqual(len(completion['decisions']), 31)
        self.assertEqual(completion['decisions'][1]['disposition'], finite.NOT_QUALIFIED)
        self.assertEqual(completion['missing_call_ids'], [])
        endpoint11 = next(d for d in completion['decisions'] if d['endpoint_id'] == 'endpoint-11')
        self.assertEqual(len(endpoint11['analysis']['raw_rows']), 320)
        self.assertEqual(sum(p['endpoint_id'] == 'endpoint-11' and p['stage'] == 'ordinary'
                             for p in calls), 320)

    def test_live_hard_failure_stops_immediately_and_counts_attempt(self):
        case = acquisition.LiveTests()
        case.setUp()
        self.addCleanup(case.doCleanups)
        case.contract = self.manifest
        outcome, calls, completion = case.acquire(fail_at=2600)
        self.assertEqual(outcome, finite.INCOMPLETE)
        self.assertEqual(len(calls), 2601)
        self.assertEqual(completion['started_calls'], 2601)
        self.assertEqual(completion['missing_call_ids'],
                         self.manifest['schedule']['call_order'][2601:])

    def test_repeat_failed_call_receipt_is_retained_without_replacement(self):
        planned = self.schedule[2648]
        root = self.v1.parent/'observation'
        root.mkdir()
        binding = dict(manifest=self.manifest,
            config=dict(stores=dict(rareplanes=dict(output=str(root)))),
            requests={planned['call_id']:dict(store='rareplanes', request=dict(workers=1))},
            builds=dict(repeat=dict(baseline=dict(ordinary=dict(build=dict(binary='/assessed/repeat'))))))
        rows = []
        with patch.object(live, 'budget'), patch.object(live, 'sha', return_value='digest'), \
             patch.object(live, 'place', return_value=lambda: None), \
             patch.object(live, 'verify_identities'), patch.object(live.stability, 'environment', return_value={}), \
             patch.object(live.stability, 'environment_issues', return_value=[]), \
             patch.object(live.refresh, 'run_process', return_value=dict(status='failed')) as worker:
            receipt = live.observe(binding, planned, {}, {}, 0, rows,
                root/'preparation.json', 'digest', root/'authority.json', 'digest')
            self.assertEqual(worker.call_args.args[0], '/assessed/repeat')
            self.assertEqual(receipt['result']['status'], 'failed')
            self.assertEqual(json.loads((root/(planned['call_id']+'-receipt.json')).read_text()), receipt)
            with self.assertRaises(FileExistsError):
                live.observe(binding, planned, {}, {}, 0, rows,
                    root/'preparation.json', 'digest', root/'authority.json', 'digest')

    def test_retained_contract_rederives_without_live_source_checkout(self):
        path = self.v1.parent/'preparation.json'
        binding = dict(schema=assessment.PREPARATION, manifest=self.manifest,
                       config=dict(authority='reviewed assessment authority',
                                   contract=dict(v1_sha256=finite.sha(self.v1))))
        path.write_text(json.dumps(binding))
        self.assertEqual(report.retained_binding(path, finite.sha(path), self.v1,
            self.register, self.design, self.predecessor), binding)
        with self.assertRaisesRegex(ValueError, 'predecessor'):
            report.retained_binding(path, finite.sha(path), self.v1, self.register, self.design)

    def test_separate_build_receipt_hashes_and_reviewed_section_difference(self):
        path = self.v1.parent/'build-reproducibility.json'
        builds, instances = {}, {}
        for name in ('main', 'repeat'):
            builds[name], instances[name] = {}, {}
            for arm in ('baseline', 'candidate'):
                builds[name][arm], instances[name][arm] = {}, {}
                for mode in ('ordinary', 'resource'):
                    binary = f'/{name}/{arm}/{mode}/worker'
                    builds[name][arm][mode] = dict(sha256='a'*64,
                        build=dict(binary=binary, binary_sha256='b'*64))
                    text = b'changed' if (name, arm, mode) == ('repeat', 'baseline', 'ordinary') else b'same'
                    instances[name][arm][mode] = dict(build_sha256='a'*64, binary_sha256='b'*64,
                        text_sha256=hashlib.sha256(text).hexdigest())
        record = dict(schema='classic-forward53-integration-builds/v1', instances=instances,
            review=dict(verdict='PASS', reviewer='independent reviewer', locator='retained review',
                explanation='Reviewed section difference is compatible with the frozen treatment',
                section_differences=['baseline/ordinary']))
        path.write_text(json.dumps(record))
        binding = dict(builds=builds, prerequisites=dict(build_reproducibility=dict(path=str(path))))
        def section(command):
            return b'changed' if command[4] == '/repeat/baseline/ordinary/worker' else b'same'
        with patch.object(live.subprocess, 'check_output', side_effect=section):
            self.assertEqual(live.assessment_build_receipt(binding), record)
            record['review']['section_differences'] = []
            path.write_text(json.dumps(record))
            with self.assertRaisesRegex(ValueError, 'compatibility review'):
                live.assessment_build_receipt(binding)

    def test_source_review_prerequisite_is_exact_treatment_review(self):
        review = self.source['independent_review']
        descriptor = dict(review, source_treatment_sha256=self.manifest['source_treatment_sha256'])
        live.validate_prerequisite_treatment(self.manifest, 'source_review', descriptor)
        with self.assertRaisesRegex(ValueError, 'source prerequisite'):
            live.validate_prerequisite_treatment(self.manifest, 'source_review',
                dict(descriptor, sha256='0'*64))


if __name__ == '__main__':
    unittest.main()
