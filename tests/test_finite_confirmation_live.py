"""Authored finite runner probes; no corpus calls, reservations or privileged changes."""
import copy
from contextlib import nullcontext
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch, Mock

import test_finite_confirmation_analysis as authored
import test_measurement_stability as reservation_tests
import finite_confirmation_live as live


class LiveTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.register = self.root/'register.json'; self.design = self.root/'design.json'
        self.v1 = self.root/'v1.json'
        self.register.write_text(json.dumps(authored.register()))
        self.design.write_text('{}')
        self.original = live.finite.make_manifest(self.register, self.design)
        self.v1.write_text(json.dumps(self.original))
        self.contract = live.derive(self.v1, live.sha(self.v1), self.register, self.design, 'separate v2 authority')

    def test_derivation_preserves_all_v1_rows_calls_and_thresholds(self):
        original_bytes = self.v1.read_bytes()
        for key, value in self.original.items():
            if key != 'schema':
                self.assertEqual(self.contract[key], value)
        self.assertEqual(self.v1.read_bytes(), original_bytes)
        self.assertEqual(self.contract['schema'], live.SCHEMA)
        self.assertEqual(len(live.ordered(self.contract)), 2648)
        self.assertEqual(self.contract['predecessor_sha256'], live.sha(self.v1))
        with self.assertRaisesRegex(ValueError, 'authority'):
            live.derive(self.v1, live.sha(self.v1), self.register, self.design, '')
        self.register.write_text('{}')
        with self.assertRaises((ValueError, KeyError)):
            live.derive(self.v1, live.sha(self.v1), self.register, self.design, 'authority')

    def binding(self):
        return dict(config=dict(stores=dict(rareplanes=dict(output=str(self.root))), authority='reviewed'),
                    installation={}, manifest=self.contract, estimators={str(n):dict(path=authored.estimator) for n in (40, 160)})

    def acquire(self, candidate=80_000_000, fail_at=None, unresolved=None):
        binding = self.binding(); started = []
        receipt = dict(valid_until_epoch=live.time.time()+10000, cgroup='/unused', controller_cpus=[])
        (self.root/'execution-started.json').write_text(json.dumps(dict(preparation_sha256='digest', authority_sha256='digest')))
        def observe(binding, planned, receipt, environment, start, rows, *args):
            started.append(planned)
            n = planned.get('round', 0)
            value = 100_000_000 if planned['arm'] == 'baseline' else candidate
            if unresolved == planned['endpoint_id'] and planned['arm'] == 'candidate':
                value = 90_000_000 if n % 2 == 0 else 113_000_000
            row = dict(planned=planned, gates_passed=planned['index'] != fail_at,
                       result=dict(status='failed' if planned['index'] == fail_at else 0,
                                   observation=dict(exact=True, samples_ns=[value])))
            rows.append(row)
            return row
        with patch.object(live, 'authority', return_value=receipt), patch.object(live, 'sha', return_value='digest'), \
             patch.object(live, 'verify_identities'), patch.object(live, 'controller_admission'), \
             patch.object(live.stability, 'controller_placement', return_value=nullcontext()), \
             patch.object(live.stability, 'environment', return_value={}), \
             patch.object(live.stability, 'environment_issues', return_value=[]), \
             patch.object(live, 'observe', side_effect=observe), patch.object(live, 'budget'), \
             patch.object(live, 'endpoint_budget'), patch.object(live, 'consumption', return_value={}), \
             patch('builtins.print'):
            result = live.acquire(binding, self.root/'prep', 'digest', self.root/'authority')
        return result, started, json.loads((self.root/'completion.json').read_text())

    def test_full_fixed_count_decisions_including_160(self):
        result, calls, completion = self.acquire()
        self.assertEqual(result, live.finite.PASS)
        self.assertEqual(calls, live.ordered(self.contract))
        self.assertEqual(len(completion['decisions']), 28)
        decision = next(d for d in completion['decisions'] if d['endpoint_id'] == 'endpoint-11')
        self.assertEqual(len(decision['analysis']['raw_rows']), 320)
        self.assertEqual(completion['missing_call_ids'], [])
        self.assertFalse(completion['promotion_authorised'])

    def test_primary_rejection_stops_before_secondary(self):
        result, calls, completion = self.acquire(candidate=95_000_000)
        self.assertEqual(result, live.finite.NOT_SELECTED)
        self.assertEqual(len(calls), 114)
        self.assertEqual(len(completion['decisions']), 1)
        self.assertEqual(completion['missing_call_ids'][0], 'preflight-0002')

    def test_primary_cannot_waive_unresolved_secondary(self):
        result, calls, completion = self.acquire(unresolved='endpoint-02')
        self.assertEqual(result, live.finite.NOT_QUALIFIED)
        self.assertEqual(completion['decisions'][0]['disposition'], live.finite.PASS)
        self.assertEqual(len(completion['decisions']), 2)
        self.assertEqual(calls[-1]['endpoint_id'], 'endpoint-02')

    def test_failed_call_stops_immediately_without_inference(self):
        result, calls, completion = self.acquire(fail_at=3)
        self.assertEqual(result, live.finite.INCOMPLETE)
        self.assertEqual(len(calls), 4)
        self.assertEqual(completion['decisions'], [])
        self.assertEqual(completion['started_calls'], 4)

    def test_observe_retains_failed_launch_and_forbids_replacement(self):
        planned = live.ordered(self.contract)[0]
        binding = self.binding()
        binding['requests'] = {planned['call_id']: dict(store='rareplanes', request={})}
        rows = []
        with patch.object(live, 'budget'), patch.object(live, 'sha', return_value='digest'), \
             patch.object(live, 'verify_identities', side_effect=ValueError('immutable source changed')):
            row = live.observe(binding, planned, {}, {}, 0, rows, self.root/'prep', 'digest', self.root/'authority', 'digest')
            self.assertEqual(row['result']['status'], 'failed_attempt')
            self.assertEqual(len(rows), 1)
            self.assertTrue((self.root/'preflight-0000-started.json').exists())
            self.assertEqual(json.loads((self.root/'preflight-0000-receipt.json').read_text()), row)
            with self.assertRaises(FileExistsError):
                live.observe(binding, planned, {}, {}, 0, rows, self.root/'prep', 'digest', self.root/'authority', 'digest')

    def test_interruption_retains_started_receipt(self):
        planned = live.ordered(self.contract)[0]; binding = self.binding(); rows = []
        binding['requests'] = {planned['call_id']: dict(store='rareplanes', request={})}
        with patch.object(live, 'budget'), patch.object(live, 'sha', return_value='digest'), \
             patch.object(live, 'verify_identities', side_effect=KeyboardInterrupt('interrupted')):
            with self.assertRaises(KeyboardInterrupt):
                live.observe(binding, planned, {}, {}, 0, rows, self.root/'prep', 'digest', self.root/'authority', 'digest')
        self.assertEqual(len(rows), 1)
        self.assertTrue((self.root/'preflight-0000-receipt.json').exists())

    def test_reusable_admission_rejects_old_schemas_quota_and_siblings(self):
        fixture = reservation_tests.StabilityTests()
        receipt = fixture.reservation_fixture(self.root)
        receipt.update(schema=live.RESERVATION, condition='balanced-reusable', partition_mode='root',
                       controller_cpus=list(range(8,16))+list(range(24,32)))
        cgroup = Path(receipt['cgroup']); (cgroup/'cpuset.cpus.partition').write_text('root')
        # The fixture's worker is directly under cgroup root; no sibling is an ordinary unit.
        with patch.object(live.stability, 'reservation', return_value=dict(cpu_max_unused='', **{'cpu.max':'max 100000','ancestor_limits':[]})), \
             patch.object(Path, 'iterdir', return_value=iter([])):
            live.admit(receipt, sysroot=self.root, now=2)
            for field, value in [('schema', live.stability.BALANCED_AA_SCHEMA), ('condition','balanced-aa'),
                                 ('partition_mode','isolated'), ('worker_cpus',[0]*8), ('reserved_cpus',list(range(8)))]:
                with self.assertRaises(ValueError):
                    live.admit(dict(receipt, **{field:value}), sysroot=self.root, now=2)
        with patch.object(live.stability, 'reservation', return_value={'cpu.max':'max 100000','ancestor_limits':[{'cpu.max':'100000 100000'}]}):
            with self.assertRaisesRegex(ValueError, 'quota'):
                live.admit(receipt)

    def test_resource_queries_and_absolute_bounds_cannot_be_waived(self):
        planned = self.contract['schedule']['allocation'][0]
        request = dict(max_working_bytes=768*1024**2,max_output_bytes=64*1024**2)
        observation = dict(samples_ns=[], working_bytes=100, output_capacity=20, output_capacity_limit=30,
                           allocation_diagnostic=dict(allocation_peak_additional_requested_bytes=90,
                                                      successful_allocation_or_reallocation_requests=3))
        baseline = dict(planned=planned,result=dict(observation=observation))
        live.resource_gate(baseline, request, None)
        candidate = dict(planned=self.contract['schedule']['allocation'][1], result=dict(observation=copy.deepcopy(observation)))
        live.resource_gate(candidate, request, baseline)
        candidate['result']['observation']['working_bytes']=101
        with self.assertRaisesRegex(ValueError, 'query changed'):
            live.resource_gate(candidate, request, baseline)
        baseline['result']['observation']['allocation_diagnostic']['allocation_peak_additional_requested_bytes']=101
        with self.assertRaisesRegex(ValueError, 'cap'):
            live.resource_gate(baseline, request, None)

    def test_caps_fail_before_consuming_start_and_include_binding_evidence(self):
        binding = self.binding()
        for values in (dict(started_calls=2648, wall_seconds=0,evidence_bytes=0,build_bytes=0),
                       dict(started_calls=0,wall_seconds=7051,evidence_bytes=0,build_bytes=0),
                       dict(started_calls=0,wall_seconds=0,evidence_bytes=2*1024**3,build_bytes=0),
                       dict(started_calls=0,wall_seconds=0,evidence_bytes=0,build_bytes=30*1024**3+1)):
            with patch.object(live, 'consumption', return_value=values):
                with self.assertRaises(ValueError): live.budget(binding, 0, 0, before_start=True)
        with patch.object(live.time, 'monotonic_ns', return_value=1651*10**9):
            with self.assertRaisesRegex(ValueError, 'endpoint'):
                live.endpoint_budget(binding, 'endpoint-11', 0, [], before_start=True)

    def test_file_identity_detects_same_size_mutation(self):
        before = live.file_identity(self.design)
        self.design.write_text('[]')
        self.assertNotEqual(live.file_identity(self.design), before)

    def test_execute_restores_after_success_failure_and_interrupt(self):
        for index, effect in enumerate((None, ValueError('transport failure'), KeyboardInterrupt('interrupted'))):
            root = self.root/str(index); root.mkdir()
            binding = dict(installation={}, config=dict(stores=dict(rareplanes=dict(output=str(root)))))
            calls = []
            def run(command, **kwargs):
                calls.append(command)
                if len(calls) == 1 and effect: raise effect
                return Mock(returncode=0, stdout='{}', stderr='')
            with patch.object(live, 'read_preparation', return_value=binding), patch.object(live, 'authority'), \
                 patch.object(live, 'sha', return_value='digest'), patch.object(live.subprocess, 'run', side_effect=run), \
                 patch.object(live, 'installed_binding', return_value={}), patch.object(live, 'validate_restoration', return_value={'restored':True}):
                status = live.execute(root/'preparation.json', 'digest', root/'lease/public/authority.json')
            self.assertEqual([c[-1] for c in calls[1:]], ['stop','verify'])
            self.assertEqual(status, 0 if effect is None else 1)
            self.assertTrue(json.loads((root/'execution-complete.json').read_text())['restoration_verified'])

    def test_unresolved_restoration_prevents_success(self):
        binding = self.binding()
        with patch.object(live, 'read_preparation', return_value=binding), patch.object(live, 'authority'), \
             patch.object(live, 'sha', return_value='digest'), patch.object(live, 'installed_binding', return_value={}), \
             patch.object(live.subprocess, 'run', return_value=Mock(returncode=0,stdout='{}',stderr='')), \
             patch.object(live, 'validate_restoration', side_effect=ValueError('wrong lease')):
            self.assertEqual(live.execute(self.root/'prep', 'digest', self.root/'lease/public/authority.json'), 1)
        self.assertFalse(json.loads((self.root/'execution-complete.json').read_text())['restoration_verified'])


if __name__ == '__main__': unittest.main()
