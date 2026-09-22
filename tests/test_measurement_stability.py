"""Offline synthetic checks: never access real inputs or change host reservations."""
import copy
import importlib.util
import json
import math
import os
from pathlib import Path
import statistics
import tempfile
import unittest
from unittest.mock import Mock, patch

SPEC = importlib.util.spec_from_file_location('stability', Path(__file__).resolve().parents[1]/'scripts/measurement-stability.py')
s = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(s)


def rows(a=None, b=None, start='A'):
    a = [999000, 1001000]*20 if a is None else a
    b = a if b is None else b
    return [dict(identity, result=dict(status=0, observation=dict(exact=True, samples_ns=[{'A': a, 'B': b}[identity['arm']][identity['round']]])))
            for identity in s.calls(dict(starting_arm=start))]


def estimator(payload):
    a, b = payload['baseline'], payload['candidate']
    x, y = statistics.mean(a), statistics.mean(b)
    q = s.analysis.critical_value(len(a))
    mx, my = [q*statistics.stdev(v)/math.sqrt(len(v)) for v in (a, b)]
    return dict(baseline_mean_ns=x, candidate_mean_ns=y, relative_change=y/x-1,
                relative_interval_99=[(y-my)/(x+mx)-1, (y+my)/(x-mx)-1], verdict='equivalent')


class StabilityTests(unittest.TestCase):
    def test_fixed_schedule_counts_and_counterbalance(self):
        schedule = s.schedule()
        self.assertEqual(len(schedule), 12)
        self.assertEqual([tuple(x['cell'] for x in schedule[4*i:4*i+4]) for i in range(3)], list(s.ORDERS))
        self.assertEqual(sum(len(s.calls(x)) for x in schedule)+4, 964)
        for cell in range(4):
            entries = [x for x in schedule if x['cell']==cell]
            self.assertEqual(len(entries), 3)
            self.assertEqual(len({x['index']%4 for x in entries}), 3)
            self.assertEqual({x['starting_arm'] for x in entries}, {'A', 'B'})
        for entry in schedule:
            calls = s.calls(entry)
            self.assertEqual(sum(c['position']==0 and c['arm']=='A' for c in calls), 20)
            self.assertEqual(sum(c['position']==0 and c['arm']=='B' for c in calls), 20)

    def test_identical_requests_and_binary_for_external_labels(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); folder = root/'session-00'; folder.mkdir()
            binding = dict(condition=dict(worker_cpus=list(range(8))), environment={}, build=dict(binary='/one/production'))
            cell = dict(request=dict(operation='encode'), workers=8)
            with patch.object(s, 'budget_check'), patch.object(s, 'verify_binding'), patch.object(s, 'environment'), patch.object(s, 'environment_issues', return_value=[]), patch.object(s.p, 'verify_call'), patch.object(s, 'placement', return_value=None), patch.object(s.refresh, 'run_process', return_value={'status':0}) as run:
                for label in ('A', 'B'):
                    s.observe(root, binding, folder, cell, dict(round=0, arm=label, position=0), 0)
            first, second = [c.args for c in run.call_args_list]
            self.assertEqual(first[:2], second[:2])
            self.assertEqual(first[3], second[3])
            self.assertNotIn('arm', first[1])

    def test_failure_retained_and_consumes_call_without_replacement(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); folder = root/'session-00'; folder.mkdir()
            with patch.object(s, 'budget_check'), patch.object(s, 'verify_binding', side_effect=ValueError('reservation lost')):
                row = s.observe(root, {}, folder, {}, dict(round=0, arm='A', position=0), 0)
                self.assertEqual(row['result']['status'], 'failed_attempt')
                self.assertEqual(s.p.started_count(root), 1)
                self.assertEqual(json.loads((folder/'call-00-A-receipt.json').read_text()), row)
                with self.assertRaises(FileExistsError):
                    s.observe(root, {}, folder, {}, dict(round=0, arm='A', position=0), 0)

    def test_budget_boundaries(self):
        for count, elapsed, size in ((964, 0, 0), (0, 7050*10**9, 0), (0, 0, s.BYTE_CAP-1024**2)):
            with patch.object(s.p, 'started_count', return_value=count), patch.object(s.p, 'bytes_used', return_value=size), patch.object(s.time, 'monotonic_ns', return_value=elapsed):
                with self.assertRaises(ValueError):
                    s.budget_check(Path('/mock'), 0)

    def reservation_fixture(self, root):
        cgroup = root/'fs/cgroup/delegated'
        cgroup.mkdir(parents=True)
        values = dict(zip(s.CGROUP_FILES, ('0-7,16-23', '0-7,16-23', 'isolated', '0', 'max 100000', 'max', 'max')))
        for key, value in values.items():
            (cgroup/key).write_text(value)
        (cgroup/'cgroup.procs').write_text('')
        for cpu in range(8):
            topology = root/f'devices/system/cpu/cpu{cpu}/topology'; topology.mkdir(parents=True)
            for key, value in dict(thread_siblings_list=f'{cpu},{cpu+16}', physical_package_id='0', core_id=str(cpu)).items():
                (topology/key).write_text(value)
        return dict(schema=s.POLICY, authority='reviewed delegation receipt', issuer='resource owner', approved=True,
            valid_from_epoch=1, valid_until_epoch=10000, cgroup=str(cgroup), worker_cpus=list(range(8)),
            reserved_cpus=list(range(8))+list(range(16,24)), controller_cpus=list(range(8,16)),
            residual_interference='Shared package/memory remain; CPU reservation does not eliminate IRQs.')

    def test_reservation_requires_authority_exclusivity_siblings_and_empty_group(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); receipt = self.reservation_fixture(root)
            s.reservation(receipt, sysroot=root, now=2)
            for field, value in [('approved', False), ('authority', ''), ('valid_until_epoch', 2), ('controller_cpus', [0]), ('reserved_cpus', list(range(8)))]:
                bad = dict(receipt, **{field:value})
                with self.assertRaises(ValueError):
                    s.reservation(bad, sysroot=root, now=2)
            cgroup = Path(receipt['cgroup'])
            for name, bad in [('cpuset.cpus.partition', 'member'), ('cpuset.cpus.exclusive.effective', ''), ('cgroup.procs', '123')]:
                path = cgroup/name; original = path.read_text(); path.write_text(bad)
                with self.assertRaises(ValueError):
                    s.reservation(receipt, sysroot=root, now=2)
                path.write_text(original)
            (root/'devices/system/cpu/cpu0/topology/thread_siblings_list').write_text('0,24')
            with self.assertRaisesRegex(ValueError, 'sibling'):
                s.reservation(receipt, sysroot=root, now=2)

    def test_cleanup_on_exception_and_intervention_guard(self):
        for intervene in (False, True):
            with tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp); cgroup = root/'cg'; cgroup.mkdir(); (cgroup/'cgroup.procs').write_text('')
                state = [set(range(16))]
                def set_affinity(pid, cpus): state[0] = set(cpus)
                receipt = dict(controller_cpus=list(range(8,16)), cgroup=str(cgroup))
                with patch.object(s.os, 'sched_getaffinity', side_effect=lambda pid:state[0]), patch.object(s.os, 'sched_setaffinity', side_effect=set_affinity):
                    with self.assertRaises((RuntimeError, ValueError)):
                        with s.controller_placement(receipt, root):
                            self.assertEqual(state[0], set(range(8,16)))
                            if intervene: state[0] = {9}
                            raise RuntimeError('synthetic failure')
                result = json.loads((root/'restoration.json').read_text())
                self.assertEqual(result['restored'], not intervene)
                self.assertEqual(state[0], {9} if intervene else set(range(16)))

    def test_session_separation_reversal_and_planning_only(self):
        result = s.analysis.analyse_session(rows(), estimator, rounds=40)
        self.assertTrue(result['valid'], result['issues'])
        self.assertEqual(result['estimator']['B_over_A']['input'], result['estimator']['A_over_B']['input'])
        self.assertEqual([x['n_per_arm'] for x in result['projections']['values']], [20,40,80,160])
        self.assertEqual([x['critical_value'] for x in result['projections']['values']], [3.287,3.030,2.915,2.860])
        displaced = s.analysis.analyse_session(rows([1000000]*40, [1004000]*40), estimator, rounds=40)
        self.assertEqual(s.analysis.classify_cell([result, result, displaced]), s.analysis.NOT_DEMONSTRATED)
        reverse = s.analysis.analyse_session(rows([1004000]*40, [1000000]*40, 'B'), estimator, rounds=40)
        self.assertEqual(displaced['estimator']['B_over_A'], reverse['estimator']['A_over_B'])
        self.assertFalse(s.analysis.analyse_session(rows()[:-1], Mock(), rounds=40)['valid'])
        self.assertFalse(s.analysis.interval_metrics([-.01,.01])['excludes_positive']['1%'])
        self.assertIn('not measured precision', result['projections']['interpretation'])

    def test_manifest_production_boundary_and_schedule_fail_closed(self):
        with tempfile.TemporaryDirectory() as tmp:
            build = dict(codec={'source_revision':s.p.CODEC}, encoder_backend='default', scheduling_window='default',
                         command=['--features','classic-compare','--profile','perf'], binary='/same/binary')
            cells = []
            for index, (op, style, workers, origin) in enumerate([('encode',1,8,'emuella'),('encode',1,8,'emuella'),('decode',0,8,'openjpeg'),('decode',0,1,'openjpeg')]):
                raw, stream = s.RAW_STREAM[min(index,2)]
                request = dict(codec='emuella', operation=op, case_id=str(index), round=0, width=1, height=1, components=3, bits=8,
                    layout='interleaved', style=style, workers=workers, raw_path='/mock/raw', raw_sha256=raw,
                    stream_path='/mock/stream', stream_sha256=stream, max_working_bytes=s.refresh.classic.WORKING, max_output_bytes=s.refresh.classic.OUTPUT)
                cells.append(dict(operation=op,style=style,workers=workers,origin=origin,request=request))
            binding = dict(policy=s.POLICY, schedule=s.schedule(), pairs=40, limits=s.limits(), launch_cadence=s.cadence(),
                runner={'revision':'authored'}, estimator={'path':'/mock/estimator'}, authority_path='/mock/authority', authority_sha256='authorised', condition={},
                build_root=tmp, build=build, cells=cells, boundary=s.refresh.BOUNDARY, warmups=0, samples_per_process=1,
                prepared_sha256=s.refresh.classic.MANIFEST)
            with patch.object(s.refresh.classic,'clean_source',return_value=binding['runner']), patch.object(s,'sha',return_value='authorised'), patch.object(s,'reservation'), patch.object(s,'estimator_identity',return_value=binding['estimator']), patch.dict(os.environ, {}, clear=True):
                s.verify_binding(binding)
                cases = []
                for key, value in [('pairs',20),('warmups',1),('samples_per_process',2),('prepared_sha256','wrong'),('boundary','other')]:
                    cases.append(dict(binding,**{key:value}))
                changed = copy.deepcopy(binding); changed['schedule'][0]['starting_arm']='B'; cases.append(changed)
                changed = copy.deepcopy(binding); changed['build']['codec']['source_revision']='candidate'; cases.append(changed)
                changed = copy.deepcopy(binding); changed['build']['encoder_backend']='reference'; cases.append(changed)
                changed = copy.deepcopy(binding); changed['cells'][0]['request']['arm']='A'; cases.append(changed)
                changed = copy.deepcopy(binding); changed['cells'][0]['request']['raw_sha256']='other'; cases.append(changed)
                changed = copy.deepcopy(binding); changed['limits']['total_calls']=965; cases.append(changed)
                for bad in cases:
                    with self.assertRaises(ValueError): s.verify_binding(bad)
                with patch.object(s,'estimator_identity',return_value={'path':'/changed/comparator'}):
                    with self.assertRaisesRegex(ValueError,'comparator'): s.verify_binding(binding)

    def test_cleanup_normal_exit_and_keyboard_interruption(self):
        for interrupt in (False, True):
            with tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp); cgroup=root/'cg'; cgroup.mkdir(); (cgroup/'cgroup.procs').write_text('')
                state=[set(range(16))]
                def set_affinity(pid, cpus): state[0]=set(cpus)
                receipt=dict(controller_cpus=list(range(8,16)),cgroup=str(cgroup))
                with patch.object(s.os,'sched_getaffinity',side_effect=lambda pid:state[0]), patch.object(s.os,'sched_setaffinity',side_effect=set_affinity):
                    try:
                        with s.controller_placement(receipt,root):
                            if interrupt: raise KeyboardInterrupt('authored signal substitute')
                    except KeyboardInterrupt:
                        self.assertTrue(interrupt)
                result=json.loads((root/'restoration.json').read_text())
                self.assertTrue(result['restored'])
                self.assertTrue(result['worker_cgroup_empty'])
                self.assertEqual(state[0],set(range(16)))

    def test_late_missing_session_retains_earlier_session_analysis(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            binding = dict(policy=s.POLICY, estimator={'path':'/mock/estimator'}, schedule=s.schedule(), cells=[dict(operation='encode', workers=8, asset=dict(id=str(i))) for i in range(4)])
            s.write(root/'binding.json', binding)
            digest = s.sha(root/'binding.json')
            s.write(root/'launch.json', dict(binding_sha256=digest))
            folder = root/'session-00'; folder.mkdir()
            observations = rows()
            for row in observations:
                s.write(folder/f"call-{row['round']:02}-{row['arm']}-receipt.json", row)
            s.write(folder/'session.json', dict(session=s.schedule()[0], binding_sha256=digest, rows=observations, valid=True, complete=True, issues=[]))
            executable = root/'mock-estimator'; executable.write_text('authored mock')
            original = s.analysis._estimate
            with patch.object(s.analysis, '_estimate', side_effect=lambda ignored,a,b:original(estimator,a,b)), patch.object(s,'estimator_identity',return_value=binding['estimator']):
                s.analyse(root, executable, root/'report.json')
            report = json.loads((root/'report.json').read_text())
            self.assertFalse(report['operationally_complete'])
            self.assertEqual(len(report['sessions']), 12)
            self.assertTrue(report['sessions'][0]['valid'])
            self.assertTrue(report['sessions'][0]['estimator'])
            self.assertTrue(report['sessions'][0]['projections'])
            self.assertTrue(all(c['disposition']==s.analysis.INCOMPLETE for c in report['cells']))

    def test_whole_study_invalidity_cannot_qualify_twelve_complete_sessions(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            binding=dict(policy=s.POLICY, estimator={'path':'/mock/estimator'}, schedule=s.schedule(),
                         cells=[dict(operation='encode',workers=8,asset=dict(id=str(i))) for i in range(4)])
            s.write(root/'binding.json',binding); digest=s.sha(root/'binding.json')
            s.write(root/'launch.json',dict(binding_sha256=digest))
            (root/'preflight').mkdir(); s.write(root/'preflight/preflight.json',dict(rows=[dict(result=dict(status=0)) for _ in range(4)]))
            for entry in s.schedule():
                folder=root/f"session-{entry['index']:02}";folder.mkdir()
                observations=rows(start=entry['starting_arm'])
                for row in observations:
                    s.write(folder/f"call-{row['round']:02}-{row['arm']}-receipt.json",row)
                s.write(folder/'session.json',dict(session=entry,binding_sha256=digest,rows=observations,valid=True,complete=True,issues=[]))
            executable=root/'mock-estimator';executable.write_text('authored mock')
            original=s.analysis._estimate
            cases=[('missing-restoration',None,1,100),
                   ('failed-restoration',dict(restored=False,worker_cgroup_empty=True),1,100),
                   ('worker-cgroup-not-empty',dict(restored=True,worker_cgroup_empty=False),1,100),
                   ('wall-cap',dict(restored=True,worker_cgroup_empty=True),s.WALL_CAP+1,100),
                   ('evidence-cap',dict(restored=True,worker_cgroup_empty=True),1,s.BYTE_CAP+1),
                   ('valid',dict(restored=True,worker_cgroup_empty=True),1,100)]
            with patch.object(s.analysis,'_estimate',side_effect=lambda ignored,a,b:original(estimator,a,b)), patch.object(s,'estimator_identity',return_value=binding['estimator']), patch.object(s.p,'started_count',return_value=964):
                for label,restoration,wall,size in cases:
                    (root/'completion.json').write_text(json.dumps(dict(started_calls=964,failures=[],wall_seconds=wall,new_evidence_bytes=size)))
                    if restoration is not None: (root/'restoration.json').write_text(json.dumps(restoration))
                    report_path=root/(label+'.json');s.analyse(root,executable,report_path)
                    report=json.loads(report_path.read_text())
                    self.assertEqual(report['operationally_complete'],label=='valid')
                    expected=s.analysis.DEMONSTRATED if label=='valid' else s.analysis.INCOMPLETE
                    self.assertTrue(all(cell['disposition']==expected for cell in report['cells']))
                    self.assertTrue(all(cell['session_only_disposition']==s.analysis.DEMONSTRATED for cell in report['cells']))
                    self.assertTrue(all(session['valid'] and session['estimator'] and session['projections'] for session in report['sessions']))

    def test_inspect_never_launches_worker_and_renders_all_missing_sessions(self):
        with tempfile.TemporaryDirectory() as tmp, patch.object(s.refresh, 'run_process') as worker:
            path = Path(tmp)/'inspection.json'
            s.inspect(path)
            result = json.loads(path.read_text())
            self.assertEqual(result['real_input_calls'], 0)
            self.assertEqual(len(result['sessions']), 12)
            self.assertTrue(all(not x['valid'] and not x['complete'] for x in result['sessions']))
            worker.assert_not_called()

    def test_actual_estimator_identity_rejects_changed_provenance(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp); executable=root/'target/release/comparator'; executable.parent.mkdir(parents=True); executable.write_text('authored binary')
            (root/'src').mkdir(); (root/'src/owner_compare.rs').write_text(s.analysis.COMPARE_SOURCE.read_text()+'changed wrapper')
            s.write(root/'provenance.json',dict(owner_sha256=s.sha(s.analysis.COMPARE_SOURCE), wrapper_sha256='wrong', method='fixed20'))
            with self.assertRaisesRegex(ValueError,'provenance'): s.estimator_identity(executable)

    @unittest.skipUnless(os.environ.get('STABILITY_ESTIMATOR'), 'existing comparator executable supplied by owner')
    def test_actual_comparator_parity_at_forty_pairs(self):
        identity=s.estimator_identity(Path(os.environ['STABILITY_ESTIMATOR']))
        self.assertEqual(identity['sha256'],s.sha(os.environ['STABILITY_ESTIMATOR']))
        result = s.analysis.analyse_session(rows(), Path(os.environ['STABILITY_ESTIMATOR']), rounds=40)
        self.assertTrue(result['valid'], result['issues'])
        projected = result['projections']['values'][1]['observed_displacement']
        for label in ('B_over_A','A_over_B'):
            for actual, expected in zip(result['estimator'][label]['output']['relative_interval_99'], projected[label]['relative_interval_99']):
                self.assertAlmostEqual(actual, expected, places=12)


if __name__ == '__main__':
    unittest.main()
