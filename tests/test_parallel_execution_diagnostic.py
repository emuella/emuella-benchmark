"""Authored diagnostics; opt-in synthetic codec checks, no protected inputs or host policy changes."""
import copy
from contextlib import ExitStack, contextmanager
import importlib.util
import json
import os
from pathlib import Path
import tempfile
import socket
import subprocess
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

SPEC = importlib.util.spec_from_file_location('parallel_diagnostic', Path(__file__).resolve().parents[1]/'scripts/parallel-execution-diagnostic.py')
d = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(d)


def fixture(workers=8, operation='decode', outer=10_200_000, elapsed=10_000_000):
    pid, pool = 100, list(range(101, 101+workers))
    begin = dict(schema='emuella-parallel-diagnostic-v1', event='begin', pid=pid,
                 operation=operation, requested_workers=workers, pool_threads=workers, pool_thread_ids=pool)
    runtimes = {pid: 500_000, **dict.fromkeys(pool, 8_000_000)} if workers == 8 else {pid:9_000_000, pool[0]:0}
    def snapshot(final):
        return dict(start_ns=outer-100 if final else 0, end_ns=outer if final else 100,
                    threads={str(t):dict(runtime_ns=1_000_000+(runtimes[t] if final else 0),
                            cpu=0 if t==pid else (t-101)%workers, allowed=list(range(workers)),
                            voluntary=0, involuntary=0) for t in [pid]+pool})
    environment = dict(task_cgroup={'cpu.stat':'nr_throttled 0\n'})
    trace = dict(begin=begin, end=dict(begin, event='end', diagnostic_facade_ns=elapsed, cpu_snapshot_span_ns=outer,
                     thread_cpu_before_ns={str(t):1_000_000 for t in [pid]+pool},
                     thread_cpu_after_ns={str(t):1_000_000+runtimes[t] for t in [pid]+pool}),
                 samples=[snapshot(False),snapshot(True)], environment_begin=environment, environment_end=environment)
    observation = dict(diagnostic_parallel=True, samples_ns=[], parallel_diagnostic=dict(
        effective_workers=workers if operation=='encode' else None,
        participating_workers=workers if operation=='encode' else None))
    observation['parallel_diagnostic'].update({k:trace['end'][k] for k in ('cpu_snapshot_span_ns','thread_cpu_before_ns','thread_cpu_after_ns')})
    return trace, observation


class TraceTests(unittest.TestCase):
    def test_conservative_bound_removes_every_threads_outside_span(self):
        trace, observation = fixture(outer=14_000_000)
        result = d.analyse_trace(trace, observation)
        self.assertEqual(result['total_cpu_ns'], 64_500_000)
        self.assertEqual(result['outside_span_ns'], 4_000_000)
        self.assertEqual(result['operation_cpu_lower_ns'], 28_500_000)
        self.assertEqual(result['operation_cpu_lower_ratio'], 2.85)
        trace['samples'][-1]['end_ns'] = 30_000_000
        trace['end']['cpu_snapshot_span_ns'] = observation['parallel_diagnostic']['cpu_snapshot_span_ns'] = 30_000_000
        result = d.analyse_trace(trace, observation)
        self.assertEqual(result['operation_cpu_lower_ns'], 0)
        self.assertFalse(result['supported'])

    def test_serial_cpu_cannot_prove_parallel_execution(self):
        trace, observation = fixture()
        for tid in trace['begin']['pool_thread_ids']:
            trace['samples'][-1]['threads'][str(tid)]['runtime_ns'] = 2_000_000
            trace['end']['thread_cpu_after_ns'][str(tid)] = 2_000_000
        result = d.analyse_trace(trace, observation)
        self.assertFalse(result['supported'])
        self.assertLessEqual(result['operation_cpu_lower_ratio'], 1.5)

    def test_parallel_fixtures_and_encode_admission(self):
        for operation in ('encode','decode'):
            trace, observation = fixture(operation=operation)
            result = d.analyse_trace(trace, observation)
            self.assertTrue(result['supported'], result['issues'])
            self.assertEqual(len(result['productive_pool_tids']), 8)
        observation['parallel_diagnostic']['effective_workers'] = 1
        trace['begin']['operation'] = trace['end']['operation'] = 'encode'
        self.assertFalse(d.analyse_trace(trace, observation)['supported'])

    def test_every_pool_thread_and_every_worker_cpu_are_required(self):
        for change in ('idle_thread','missing_cpu','caller_cannot_supply_missing_pool_cpu'):
            trace, observation = fixture()
            last = trace['samples'][-1]['threads']
            if change=='idle_thread':
                last['108']['runtime_ns'] = trace['samples'][0]['threads']['108']['runtime_ns']
                trace['end']['thread_cpu_after_ns']['108'] = trace['end']['thread_cpu_before_ns']['108']
            else:
                last['108']['cpu'] = 6
                if change=='caller_cannot_supply_missing_pool_cpu': last['100']['cpu'] = 7
            self.assertFalse(d.analyse_trace(trace, observation)['supported'], change)

    def test_requested_and_actual_pool_must_match(self):
        trace, observation = fixture()
        trace['begin']['pool_threads'] = 4
        with self.assertRaisesRegex(ValueError,'pool'):
            d.analyse_trace(trace, observation)

    def test_single_cpu_control_counts_caller_without_requiring_pool_work(self):
        trace, observation = fixture(workers=1)
        self.assertTrue(d.analyse_trace(trace, observation)['supported'])
        trace['samples'][-1]['threads']['100']['cpu'] = 1
        with self.assertRaisesRegex(ValueError,'placement'): d.analyse_trace(trace, observation)
        trace, observation = fixture(workers=1)
        trace['end']['thread_cpu_after_ns']['100'] += 4_000_000
        self.assertFalse(d.analyse_trace(trace, observation)['supported'])

    def test_runtime_reversal_or_missing_mandatory_samples_fail_closed(self):
        for mutation in ('reversal','missing_thread','missing_runtime','one_snapshot','duplicate_tid','bad_boundary'):
            trace, observation = fixture()
            if mutation=='reversal': trace['samples'][-1]['threads']['101']['runtime_ns'] = 0
            elif mutation=='missing_thread': del trace['samples'][-1]['threads']['101']
            elif mutation=='missing_runtime': del trace['samples'][-1]['threads']['101']['runtime_ns']
            elif mutation=='one_snapshot': trace['samples'] = trace['samples'][:1]
            elif mutation=='duplicate_tid': trace['begin']['pool_thread_ids'][-1] = 101
            else: trace['end']['diagnostic_facade_ns'] = 30_000_000
            with self.assertRaises((ValueError,KeyError), msg=mutation):
                d.analyse_trace(trace, observation)

    def test_diagnostic_cannot_supply_headline_samples(self):
        for field,value in [('samples_ns',[10]),('diagnostic_parallel',False)]:
            trace, observation = fixture()
            observation[field] = value
            with self.assertRaisesRegex(ValueError,'headline|diagnostic'):
                d.analyse_trace(trace, observation)

    def test_thermal_counters_are_advisory_when_absent_and_block_support_when_changed(self):
        for key in ('thermal_throttle/core_throttle_count','thermal_throttle/package_throttle_count'):
            for after in ('0','1',None):
                trace, observation=fixture()
                trace['environment_begin']=dict(trace['environment_begin'],cpu={'0':{key:'0'}})
                trace['environment_end']=dict(trace['environment_end'],cpu={'0':{key:after}})
                result=d.assess(trace,observation)
                self.assertEqual(result['supported'],after!='1')
                counter=result['thermal_throttle_counters']['0'][key]
                self.assertEqual(counter['status'],'unavailable' if after is None else 'available')
                self.assertEqual(counter['delta'],None if after is None else int(after))
        trace['environment_begin']['cpu']['0'][key]='2'
        trace['environment_end']['cpu']['0'][key]='1'
        self.assertFalse(d.assess(trace,observation)['supported'])

    def test_reconstruction_retains_thermal_failure_and_detects_assessment_tampering(self):
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary)
            trace, observation=fixture()
            trace['environment_begin']=dict(trace['environment_begin'],cpu={'0':{'thermal_throttle/core_throttle_count':'0'}})
            trace['environment_end']=dict(trace['environment_end'],cpu={'0':{'thermal_throttle/core_throttle_count':'1'}})
            request=dict(operation='decode',case_id='authored',workers=8,style=0,raw_sha256='raw',stream_sha256='stream')
            observation.update(request,binary_sha256='binary',exact=True)
            binding=dict(schema=d.SCHEMA,caps=d.CAPS,criteria=d.CRITERIA,
                cells=[dict(request=request,workers=8,operation='decode')]*4,
                build=dict(binary_sha256='binary',benchmark={'source_revision':'worker'},codec={'source_revision':'codec'}),
                runner={'source_revision':'runner'})
            d.write(root/'binding.json',binding)
            d.write(root/'launch.json',dict(binding_sha256=d.sha(root/'binding.json')))
            d.write(root/'completion.json',dict(started_calls=4,failures=[],wall_seconds=1,evidence_bytes=100))
            d.write(root/'restoration.json',dict(restored=True,worker_cgroup_empty=True))
            assessment=d.assess(trace,observation)
            for index in range(4):
                folder=root/f'call-{index}';folder.mkdir()
                d.write(folder/'result.json',dict(status=0,observation=observation))
                (folder/'thread-samples.jsonl').write_text(''.join(json.dumps(v)+'\n' for v in trace['samples']))
                d.write(root/f'call-{index}-markers.json',trace)
                d.write(root/f'call-{index}-started.json',{})
                d.write(root/f'call-{index}-assessment.json',assessment)
            report=d.reconstruct(root)
            self.assertTrue(report['operationally_complete'])
            self.assertFalse(report['all_cells_supported'])
            self.assertTrue(all(row['assessment']==assessment for row in report['rows']))
            (root/'call-0-assessment.json').write_text(json.dumps(dict(assessment,supported=True)))
            self.assertFalse(d.reconstruct(root)['operationally_complete'])


class FrozenBindingTests(unittest.TestCase):
    def test_fixed_caps_are_explicit(self):
        self.assertEqual(d.CAPS, dict(calls=4,window_seconds=900,evidence_bytes=64*1024**2,
            build_bytes=30*1024**3,call_seconds=120,sample_seconds=.002,
            trace_bytes_per_call=12*1024**2,samples_per_call=20000))

    def test_frozen_identity_tampering_fails_before_measurement(self):
        with tempfile.TemporaryDirectory() as temporary, ExitStack() as stack:
            root = Path(temporary); original = root/'original.json'
            cells = [dict(index=i) for i in range(4)]
            original.write_text(json.dumps(dict(cells=cells)))
            build = dict(benchmark={},parallel_diagnostics=True,codec=dict(source_revision=d.p.CODEC),
                encoder_backend='default',scheduling_window='default',
                command=['cargo','--features',d.FEATURES,'--profile','perf'])
            binding = dict(schema=d.SCHEMA,caps=copy.deepcopy(d.CAPS),criteria=copy.deepcopy(d.CRITERIA),
                build_path=str(root/'build'),build=build,runner='runner',policy_identity='policy',original_binding=str(original),
                prepared_manifest='prepared',prepared_sha256=d.refresh.classic.MANIFEST,cells=cells,build_root=str(root))
            stack.enter_context(patch.dict(os.environ,{},clear=True))
            stack.enter_context(patch.object(d.helper,'policy',return_value='policy'))
            stack.enter_context(patch.object(d.refresh,'bind',return_value=build))
            stack.enter_context(patch.object(d.refresh,'worker_sources',return_value={}))
            stack.enter_context(patch.object(d.refresh.classic,'clean_source',return_value='runner'))
            stack.enter_context(patch.object(d,'sha',side_effect=lambda path:d.ORIGINAL if str(path)==str(original) else d.refresh.classic.MANIFEST))
            stack.enter_context(patch.object(d.p,'bytes_used',return_value=0))
            calls = stack.enter_context(patch.object(d.p,'verify_call'))
            d.verify_binding(binding)
            self.assertEqual(calls.call_count,4)
            for change in ('schema','cap','criteria','build','runner','cells','prepared'):
                bad = copy.deepcopy(binding)
                if change=='schema': bad['schema'] = 'unknown'
                elif change=='cap': bad['caps']['calls'] = 5
                elif change=='criteria': bad['criteria']['productive_pool_thread_lower_ns'] = 0
                elif change=='build': bad['build']['codec']['source_revision'] = 'changed'
                elif change=='runner': bad['runner'] = 'changed'
                elif change=='cells': bad['cells'].reverse()
                else: bad['prepared_sha256'] = 'changed'
                with self.assertRaises(ValueError,msg=change): d.verify_binding(bad)
            with patch.object(d.p,'bytes_used',return_value=d.CAPS['build_bytes']+1):
                with self.assertRaisesRegex(ValueError,'build cap'): d.verify_binding(binding)


class RunTests(unittest.TestCase):
    def exercise(self, mode):
        with tempfile.TemporaryDirectory() as temporary, ExitStack() as stack:
            root = Path(temporary)
            cells = [dict(workers=w,operation=operation,request={'operation':operation}) for operation,w in [('encode',8),('decode',8),('encode',1),('decode',1)]]
            if mode=='five': cells.append(cells[0])
            binding = dict(store=str(root),cells=cells,build=dict(binary='/authored/mock-worker'))
            binding_path=root/'binding.json'; binding_path.write_text(json.dumps(binding))
            authority=root/'authority.json'; authority.write_text(json.dumps(dict(valid_until_epoch=10000)))
            args=SimpleNamespace(binding=binding_path,binding_sha256='digest',authority=authority,output=root/'evidence')
            restored=[]
            @contextmanager
            def placement(*_):
                try: yield
                finally: restored.append(True)
            for owner,name,value in [(d,'sha','digest'),(d,'verify_binding',None),(d,'admission',None),
                (d.s,'environment',{}),(d,'stable_issues',[]),(d.s,'placement',None),
                (d.time,'time',0),(d.time,'monotonic_ns',0),(d.signal,'signal',None),(d.signal,'alarm',None)]:
                stack.enter_context(patch.object(owner,name,return_value=value))
            stack.enter_context(patch.object(d.s,'controller_placement',side_effect=placement))
            stack.enter_context(patch.object(d.socket,'socket'))
            stack.enter_context(patch.object(Path,'chmod'))
            stack.enter_context(patch.object(d.p,'bytes_used',return_value=d.CAPS['evidence_bytes'] if mode=='storage' else 0))
            if mode=='window':
                stack.enter_context(patch.object(d.time,'monotonic_ns',side_effect=[0,751*10**9,752*10**9,753*10**9]))
            def process(binary,request,folder,cpus,**kwargs):
                folder.mkdir()
                trace,observation=fixture(len(cpus),request['operation'])
                kwargs['monitor'].trace=trace
                if mode=='missing_throttle': trace['environment_end']={'task_cgroup':{'cpu.stat':''}}
                if mode=='reversed_throttle': trace['environment_begin']={'task_cgroup':{'cpu.stat':'nr_throttled 2\n'}}
                result=dict(status=1 if mode=='failure' else 0,observation=observation)
                (folder/'result.json').write_text(json.dumps(result))
                if mode=='exception': raise RuntimeError('synthetic interrupted call')
                return result
            called=stack.enter_context(patch.object(d.refresh,'run_process',side_effect=process))
            if mode in ('complete','reversed_throttle'):
                d.run(args)
            else:
                with self.assertRaises((ValueError,RuntimeError)): d.run(args)
            completion=json.loads((args.output/'completion.json').read_text())
            self.assertEqual(restored,[True])
            self.assertLessEqual(called.call_count,4)
            if mode in ('storage','window'):
                self.assertEqual(called.call_count,0); self.assertEqual(completion['started_calls'],0)
            elif mode in ('failure','exception','missing_throttle'):
                self.assertEqual(called.call_count,1); self.assertEqual(completion['started_calls'],1)
                self.assertTrue(completion['failures'])
                self.assertTrue((args.output/'call-0-markers.json').exists())
                self.assertTrue((args.output/'call-0/result.json').exists())
            else:
                self.assertEqual(called.call_count,4)
                self.assertEqual(completion['started_calls'],4)
            return completion

    def test_failed_attempt_is_retained_without_replacement_and_restores_controller(self):
        for mode in ('failure','exception','missing_throttle'):
            with self.subTest(mode=mode): self.exercise(mode)

    def test_call_storage_and_window_caps_restore_controller(self):
        for mode in ('five','storage','window'):
            with self.subTest(mode=mode): self.exercise(mode)

    def test_four_fixed_calls_complete(self):
        completion=self.exercise('complete')
        self.assertEqual(len(completion['rows']),4)
        self.assertEqual(completion['failures'],[])

    def test_reversed_throttle_counter_cannot_support_parallelism(self):
        completion=self.exercise('reversed_throttle')
        self.assertTrue(all(not row['assessment']['supported'] for row in completion['rows']))


class SharedRunnerTests(unittest.TestCase):
    def test_ordinary_runner_rejects_diagnostic_response_even_with_headline_sample(self):
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary); binary=root/'worker'; binary.write_bytes(b'authored identity')
            request=dict(codec='emuella',operation='encode',case_id='authored',round=0,style=0,workers=8,
                         raw_sha256='raw',stream_sha256='stream')
            response=dict(request,boundary=d.refresh.BOUNDARY,exact=True,binary_sha256=d.sha(binary),
                          samples_ns=[100],diagnostic_parallel=True,parallel_diagnostic={})
            def spawn(*args,**kwargs):
                kwargs['stdout'].write(json.dumps(response)); kwargs['stdout'].flush()
                return Mock(wait=Mock(return_value=0))
            with patch.object(d.refresh.subprocess,'Popen',side_effect=spawn):
                result=d.refresh.run_process(binary,request,root/'call',[0])
            self.assertEqual(result['status'],'invalid_response')
            self.assertIn('headline',result['reason'])

    def test_diagnostic_monitor_is_mandatory_before_process_creation(self):
        with patch.object(d.refresh.subprocess,'Popen') as spawn:
            with self.assertRaisesRegex(ValueError,'monitor'):
                d.refresh.run_process('unused',{},Path('/unused'),[0],parallel_diagnostics=True)
            spawn.assert_not_called()


@unittest.skipUnless(os.environ.get('EMUELLA_PARALLEL_DIAGNOSTIC_TEST_WORKER'), 'opt-in built diagnostic worker')
class AuthoredWorkerJourney(unittest.TestCase):
    def test_actual_fresh_decoder_transport_exactness_and_cpu_boundaries(self):
        binary=Path(os.environ['EMUELLA_PARALLEL_DIAGNOSTIC_TEST_WORKER']).resolve()
        with tempfile.TemporaryDirectory(prefix='emuella-authored-') as temporary:
            root=Path(temporary)
            raw=bytes((i*37+i//13)%256 for i in range(128*128*3))
            (root/'raw').write_bytes(raw)
            (root/'input.ppm').write_bytes(b'P6\n128 128\n255\n'+raw)
            subprocess.run(['opj_compress','-i',str(root/'input.ppm'),'-o',str(root/'stream.j2k'),'-n','3','-b','64,64','-mct','1'],check=True,capture_output=True)
            for workers in (1,8):
                request=dict(codec='emuella',operation='decode',case_id='authored-128-rgb',round=0,width=128,height=128,
                             components=3,bits=8,style=0,workers=workers,layout='interleaved',raw_path=str(root/'raw'),
                             raw_sha256=d.sha(root/'raw'),stream_path=str(root/'stream.j2k'),stream_sha256=d.sha(root/'stream.j2k'),
                             max_working_bytes=d.refresh.classic.WORKING,max_output_bytes=d.refresh.classic.OUTPUT)
                folder=root/f'call-{workers}'; endpoint=root/f'socket-{workers}'
                with socket.socket(socket.AF_UNIX,socket.SOCK_STREAM) as server:
                    server.bind(str(endpoint)); server.listen(1)
                    monitor=d.Monitor(server,folder,{},dict(operation='decode',workers=workers),str(binary))
                    with patch.object(d.s,'environment',return_value={'task_cgroup':{'cpu.stat':'nr_throttled 0'}}):
                        result=d.refresh.run_process(str(binary),request,folder,list(range(workers)),placement=lambda:None,
                              parallel_diagnostics=True,monitor=monitor,environment=dict(os.environ,EMUELLA_PARALLEL_DIAGNOSTIC_SOCKET=str(endpoint)))
                    self.assertEqual(result['status'],0,result)
                    self.assertEqual(result['observation']['samples_ns'],[])
                    self.assertTrue(result['observation']['exact'])
                    assessed=d.assess(monitor.trace,result['observation'])
                    self.assertGreater(assessed['operation_ns'],0)
                    self.assertEqual(len(assessed['runtime_deltas_ns']),workers+1)
                    self.assertEqual(monitor.trace['begin']['pool_threads'],workers)
                    # Tiny authored input is transport validation, never a stability/parallel qualification.


if __name__=='__main__': unittest.main()
