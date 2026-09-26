"""Offline assessment contract, stop policy and historical isolation checks."""
import copy
import hashlib
import json
from pathlib import Path
import shutil
import tempfile
import unittest
from unittest.mock import Mock, patch

import finite_confirmation_analysis as finite
import finite_confirmation_live as live
import finite_confirmation_report as report
import integration_assessment as assessment
import test_finite_confirmation_analysis as authored
import test_finite_confirmation_live as acquisition
import test_finite_confirmation_repairs as retained


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

    def test_complete_reconstruction_after_scratch_cleanup_and_retained_rejection(self):
        case = retained.RepairTests()
        case.setUp()
        self.addCleanup(case.doCleanups)
        binding = case.binding
        binding['schema'] = assessment.PREPARATION
        binding['manifest'] = self.manifest
        binding['config']['authority'] = 'reviewed assessment authority'
        binding['config']['contract'] = dict(v1_sha256=finite.sha(self.v1))
        binding['config']['evidence_roots'] = [str(case.output), str(case.other)]
        scratch = case.root/'registered-scratch'
        scratch.mkdir()
        binding['config']['build_root'] = str(scratch)
        _, lease, _, _, authority = case.fixture()
        restoration = case.restoration(authority)
        authority_sha = hashlib.sha256(restoration['authority_text'].encode()).hexdigest()
        environment = dict(controller_affinity=authority['controller_cpus'], reservation={},
                           boost=None, cpu={}, task_cgroup={})
        builds, frozen_instances, copies = {}, {}, {}
        retained_root = case.output/'retained-builds'
        retained_root.mkdir()
        for instance in ('main', 'repeat'):
            builds[instance], frozen_instances[instance], copies[instance] = {}, {}, {}
            for arm in ('baseline', 'candidate'):
                builds[instance][arm], frozen_instances[instance][arm], copies[instance][arm] = {}, {}, {}
                for mode in ('ordinary', 'resource'):
                    label = f'{instance}-{arm}-{mode}'
                    original = scratch/label
                    original.mkdir()
                    binary = original/'worker'
                    binary.write_bytes(label.encode())
                    build_json = original/'build.json'
                    build_json.write_text(json.dumps(dict(authored=label)))
                    binary_sha = live.sha(binary)
                    text_sha = hashlib.sha256(b'authored text section').hexdigest()
                    builds[instance][arm][mode] = dict(path=str(build_json), sha256=live.sha(build_json),
                        build=dict(binary=str(binary), binary_sha256=binary_sha))
                    frozen_instances[instance][arm][mode] = dict(binary_sha256=binary_sha,
                        text_sha256=text_sha, build_sha256=live.sha(build_json))
                    copied = retained_root/(label+'-worker')
                    shutil.copyfile(binary, copied)
                    copies[instance][arm][mode] = dict(path=str(copied), binary_sha256=binary_sha,
                        text_sha256=text_sha)
        binding['builds'] = builds
        frozen = dict(schema='classic-forward53-integration-builds/v1', instances=frozen_instances,
            review=dict(verdict='PASS', reviewer='independent reviewer', locator='authored fixture',
                explanation='All corresponding sections agree', section_differences=[]))
        binding['build_reproducibility'] = frozen
        binding['prerequisites'] = {}
        source_review = self.source['independent_review']
        Path(source_review['path']).write_text(self.review_text)
        for key in live.ASSESSMENT_PREREQUISITES:
            path = Path(source_review['path']) if key == 'source_review' else case.root/(key+'.json')
            if key == 'build_reproducibility':
                path.write_text(json.dumps(frozen))
            elif key != 'source_review':
                path.write_text('{}')
            binding['prerequisites'][key] = dict(path=str(path), sha256=live.sha(path))
            if key != 'independent_decode':
                binding['prerequisites'][key]['source_treatment_sha256'] = self.manifest['source_treatment_sha256']
        binding['requests'] = {}
        rows = []
        for planned in self.schedule:
            request = dict(codec='emuella', operation='encode', case_id=planned.get('case_id', 'authored'),
                round=planned.get('round', 0), style=planned.get('style', 1),
                workers=planned.get('workers', 8), raw_sha256='raw', stream_sha256='stream',
                max_working_bytes=768*1024**2, max_output_bytes=64*1024**2)
            instance = planned.get('build_instance', 'main')
            binary_sha = builds[instance][planned['arm']]['resource' if planned['stage'] == 'allocation'
                                                         else 'ordinary']['build']['binary_sha256']
            observed = dict(request, exact=True, binary_sha256=binary_sha,
                boundary=live.refresh.BOUNDARY,
                samples_ns=[100_000_000 if planned['arm'] == 'baseline' else 80_000_000])
            if planned['stage'] == 'allocation':
                observed.update(samples_ns=[], working_bytes=100, output_capacity=20,
                    output_capacity_limit=30, allocation_diagnostic=dict(
                        allocation_peak_additional_requested_bytes=90,
                        successful_allocation_or_reallocation_requests=3))
            row = dict(planned=planned, result=dict(status=0, observation=observed), gates_passed=True,
                       environment=dict(before=environment, after=environment, issues=[]))
            if planned['stage'] == 'allocation':
                row['resources'] = live.panels.resources.resource_observation(observed, request)
            binding['requests'][planned['call_id']] = dict(store='rareplanes', request=request)
            folder = case.output/planned['call_id']
            folder.mkdir()
            (folder/'request.json').write_text(json.dumps(request))
            (case.output/(planned['call_id']+'-started.json')).write_text(json.dumps(
                dict(planned=planned, monotonic_ns=planned['index']+1)))
            (case.output/(planned['call_id']+'-receipt.json')).write_text(json.dumps(row))
            rows.append(row)
        # The bound preparation is written once; report never rewrites it.
        preparation = case.output/'preparation.json'
        preparation.write_text(json.dumps(binding))
        digest = live.sha(preparation)
        preparation_bytes = preparation.read_bytes()
        consumption = dict(started_calls=2900, wall_seconds=100, evidence_bytes=100, build_bytes=100)
        estimators = {40:authored.estimator, 160:authored.estimator}
        expected = assessment.analyse_attempt(self.manifest, rows, estimators,
            checks=dict.fromkeys(assessment.CHECKS, True), consumption=consumption)
        records = {
            'execution-started.json':dict(preparation_sha256=digest, authority_sha256=authority_sha,
                                          lease_id=lease.name),
            'execution-complete.json':dict(schema=assessment.SCHEMA, status=0, error=None,
                                           restoration_verified=True, lease_id=lease.name),
            'launch.json':dict(preparation_sha256=digest, authority_sha256=authority_sha,
                               condition=live.common_authority(authority), environment=environment),
            'independent-restoration.json':restoration,
            'placement-original.json':dict(original=[0], intended=authority['controller_cpus']),
            'restoration.json':dict(restored=True, worker_cgroup_empty=True, intervening_change=False,
                                    host_policy_changes=False, original=[0], final=[0],
                                    observed_before_restore=authority['controller_cpus']),
            'completion.json':dict(schema=assessment.SCHEMA, preparation_sha256=digest,
                started_calls=2900, consumption=consumption, missing_call_ids=[],
                disposition=finite.PASS, issues=[], decisions=expected['endpoints']+expected['repeats'])}
        for name, value in records.items():
            (case.output/name).write_text(json.dumps(value))
        mapping = dict(schema='classic-forward53-integration-retained-builds/v1',
            preparation_sha256=digest,
            build_reproducibility_sha256=binding['prerequisites']['build_reproducibility']['sha256'],
            instances=copies)
        mapping_path = case.output/'retained-builds.json'
        mapping_path.write_text(json.dumps(mapping))
        mapping_sha = live.sha(mapping_path)
        shutil.rmtree(scratch)
        self.assertFalse(scratch.exists())
        with patch.object(live, 'assessment_build_receipt', side_effect=AssertionError('original scratch reopened')), \
             patch.object(report.subprocess, 'check_output', return_value=b'authored text section'):
            result = report.reconstruct(binding, digest, estimators,
                retained_builds=mapping_path, retained_builds_sha256=mapping_sha)
            self.assertEqual((result['disposition'], result['issues']), (finite.PASS, []))
            self.assertEqual((len(result['endpoints']), len(result['repeats'])), (28, 3))
            self.assertEqual(preparation.read_bytes(), preparation_bytes)
            unbound = report.reconstruct(binding, digest, estimators)
            self.assertEqual(unbound['disposition'], finite.INCOMPLETE)
            self.assertIn('externally pinned retained assessment builds required',
                          ' '.join(unbound['issues']))
            missing = retained_root/'main-baseline-ordinary-worker'
            data = missing.read_bytes()
            missing.unlink()
            failed = report.reconstruct(binding, digest, estimators,
                retained_builds=mapping_path, retained_builds_sha256=mapping_sha)
            self.assertEqual(failed['disposition'], finite.INCOMPLETE)
            self.assertIn('retained executable missing', ' '.join(failed['issues']))
            missing.write_bytes(data+b'changed')
            failed = report.reconstruct(binding, digest, estimators,
                retained_builds=mapping_path, retained_builds_sha256=mapping_sha)
            self.assertEqual(failed['disposition'], finite.INCOMPLETE)
            self.assertIn('retained executable or frozen build identity', ' '.join(failed['issues']))


if __name__ == '__main__':
    unittest.main()
