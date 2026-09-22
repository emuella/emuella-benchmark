#!/usr/bin/env python3
"""Four-call opt-in diagnostic; balanced exclusive CPUs, no headline measurements."""
import argparse
import importlib.util
import json
import os
from pathlib import Path
import select
import signal
import socket
import struct
import sys
import tempfile
import time

sys.path.insert(0, str(Path(__file__).resolve().parent))
import measurement_reservation as helper
SPEC = importlib.util.spec_from_file_location('parallel_stability', Path(__file__).with_name('measurement-stability.py'))
s = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(s)
p, refresh, sha, write = s.p, s.refresh, s.sha, s.write
SCHEMA = 'parallel-execution-diagnostic/v1'
ORIGINAL = '5e27912737fbecf98259ead8f4dec233e58ae638d4d77fb88d5392df494b0661'
FEATURES = 'classic-parallel-diagnostics,emuella-j2k-codestream/classic-execution-diagnostics'
CAPS = dict(calls=4, window_seconds=900, evidence_bytes=64*1024**2,
            build_bytes=30*1024**3, call_seconds=120, sample_seconds=.002,
            trace_bytes_per_call=12*1024**2, samples_per_call=20000)
CRITERIA = dict(parallel_operation_cpu_lower_ratio_strictly_above=1.5,
                productive_pool_thread_lower_ns=100000,
                require_all_eight_pool_threads=True, require_all_eight_observed_worker_cpus=True,
                control_worker_cpus=[0], max_control_outer_cpu_ratio=1.1, require_positive_control_operation_cpu=True)


def require(ok, reason):
    if not ok:
        raise ValueError(reason)


def admission(receipt, occupied_group=None):
    require(receipt['worker_cpus'] == list(range(8)) and receipt['reserved_cpus'] == list(range(8))+list(range(16,24))
            and receipt['controller_cpus'] == list(range(8,16))+list(range(24,32)), 'fixed CPU allocation differs')
    result = s.reservation(receipt, expected_partition='root', expected_schema='measurement-balanced-qualification/v1', occupied_group=occupied_group)
    require(result['cpu.max'].split()[0] == 'max', 'task CPU quota is finite')
    require(all(v['cpu.max'] is None or v['cpu.max'].split()[0] == 'max' for v in result['ancestor_limits']), 'ancestor CPU quota is finite')
    group = Path(receipt['cgroup']).parent
    for child in Path('/sys/fs/cgroup').iterdir():
        if child.is_dir() and child != group:
            require(not set(s.cpulist((child/'cpuset.cpus.effective').read_text())) & set(receipt['reserved_cpus']), 'ordinary workload exclusion differs')
    return result


def stable_issues(before, after, receipt):
    # Throttle increments are retained diagnostic findings, not policy identity changes.
    return [v for v in s.environment_issues(before, after, receipt) if 'throttle' not in v]


def task_snapshot(pid, tids, cpus):
    start = time.monotonic_ns()
    root = Path(f'/proc/{pid}/task')
    require({int(v.name) for v in root.iterdir()} == set(tids), 'task thread coverage changed')
    rows = {}
    for tid in tids:
        task = root/str(tid)
        fields = (task/'stat').read_text().rsplit(')',1)[1].split()
        status = dict(line.split(':',1) for line in (task/'status').read_text().splitlines() if ':' in line)
        allowed = s.cpulist(status['Cpus_allowed_list'].strip())
        require(allowed == cpus, 'thread affinity differs')
        runtime = (task/'schedstat').read_text().split()
        require(len(runtime) == 3 and all(x.isdigit() for x in runtime), 'thread runtime unavailable')
        rows[str(tid)] = dict(runtime_ns=int(runtime[0]), cpu=int(fields[36]), allowed=allowed,
                             voluntary=int(status['voluntary_ctxt_switches']), involuntary=int(status['nonvoluntary_ctxt_switches']))
    return dict(start_ns=start, end_ns=time.monotonic_ns(), threads=rows)


def analyse_trace(trace, observation):
    begin, end = trace['begin'], trace['end']
    require(begin['pool_thread_ids'] == end['pool_thread_ids'] and begin['pid'] == end['pid'], 'marker identities differ')
    workers = begin['requested_workers']
    require(begin['pool_threads'] == workers and workers in (1,8), 'constructed pool differs')
    tids = [begin['pid']]+begin['pool_thread_ids']
    samples = trace['samples']
    keys = {str(t) for t in tids}
    require(len(samples) >= 2 and len(tids) == len(set(tids)) == workers+1, 'missing snapshots or thread identity')
    first, last = samples[0], samples[-1]
    operation, span = end['diagnostic_facade_ns'], end['cpu_snapshot_span_ns']
    outer = last['end_ns']-first['start_ns']
    require(type(operation) is int and type(span) is int and 0 < operation <= span <= outer, 'operation boundary is inconsistent')
    slack = span-operation
    diagnostic = observation['parallel_diagnostic']
    require(observation.get('diagnostic_parallel') is True and observation.get('samples_ns') == [], 'headline or non-diagnostic response')
    for key in ('cpu_snapshot_span_ns','thread_cpu_before_ns','thread_cpu_after_ns'):
        require(diagnostic.get(key)==end[key], 'worker CPU response differs from marker')
    before, after = end['thread_cpu_before_ns'], end['thread_cpu_after_ns']
    require(set(before)==set(after)==keys, 'worker CPU coverage differs')
    deltas = {}
    seen = set()
    for key in keys:
        require(type(before[key]) is int and type(after[key]) is int and 0 <= before[key] <= after[key], 'worker CPU runtime decreased or invalid')
        deltas[key] = after[key]-before[key]
    previous_end = -1
    for snapshot in samples:
        require(set(snapshot['threads']) == keys and previous_end <= snapshot['start_ns'] <= snapshot['end_ns'], 'sample coverage or ordering differs')
        previous_end = snapshot['end_ns']
        for row in snapshot['threads'].values():
            require(row['allowed']==list(range(workers)) and row['cpu'] in row['allowed'], 'sample affinity or placement differs')
    for tid in tids:
        key = str(tid)
        values = [v['threads'][key]['runtime_ns'] for v in samples]
        require(all(b >= a for a,b in zip(values,values[1:])), 'thread runtime decreased')
        if workers==8 and tid==begin['pid']:
            continue
        for a,b in zip(samples,samples[1:]):
            if b['threads'][key]['runtime_ns'] > a['threads'][key]['runtime_ns']:
                seen.add(b['threads'][key]['cpu'])
    cpu = sum(deltas.values())
    lower = max(0, cpu-len(tids)*slack)
    productive = [tid for tid in begin['pool_thread_ids'] if deltas[str(tid)]-slack >= CRITERIA['productive_pool_thread_lower_ns']]
    reasons = []
    if workers == 8:
        if lower/operation <= 1.5: reasons.append('operation CPU lower bound does not exceed 1.5 CPUs')
        if len(productive) != 8: reasons.append('not all eight pool threads have bounded productive CPU evidence')
        if seen != set(range(8)): reasons.append('productive placement samples do not cover all eight worker CPUs')
        if begin['operation'] == 'encode' and (diagnostic.get('effective_workers') != 8 or diagnostic.get('participating_workers') != 8):
            reasons.append('codec encode admission/participation differs')
    elif seen != {0} or cpu/span > 1.1 or lower <= 0:
        reasons.append('single-worker control placement/accounting differs')
    return dict(supported=not reasons, issues=reasons, runtime_deltas_ns=deltas,
                operation_ns=operation, cpu_snapshot_span_ns=span, outer_span_ns=outer, outside_span_ns=slack,
                total_cpu_ns=cpu, operation_cpu_lower_ns=lower, operation_cpu_lower_ratio=lower/operation,
                whole_outer_cpu_ratio=cpu/outer, productive_pool_tids=productive, observed_productive_cpus=sorted(seen),
                scope='Worker CPUCLOCK_SCHED snapshots surround the operation; subtract one outside-span allowance per tracked thread. External schedstat/last-CPU samples are advisory placement evidence, not a scheduler trace or proof of eight-way simultaneity.')


class Monitor:
    def __init__(self, server, folder, receipt, cell, binary):
        self.server, self.folder, self.receipt, self.cell, self.binary = server, folder, receipt, cell, binary
        self.trace = dict(samples=[])

    def __call__(self, process, deadline):
        def alive():
            require(time.monotonic() < deadline, '120-second diagnostic call cap')
            require(p.bytes_used(self.folder.parent) < CAPS['evidence_bytes']-1024**2, 'evidence cap')
            require(process.poll() is None, 'worker exited before operation handshake')
        while not select.select([self.server],[],[],.05)[0]: alive()
        connection, _ = self.server.accept()
        with connection:
            peer = struct.unpack('3i', connection.getsockopt(socket.SOL_SOCKET,socket.SO_PEERCRED,12))
            require(peer[1] == os.getuid() and os.getpgid(peer[0]) == process.pid, 'diagnostic peer is not the owned worker')
            require(Path(f'/proc/{peer[0]}/exe').resolve() == Path(self.binary).resolve(), 'peer executable differs')
            connection.setblocking(False)
            buffer = b''
            def message():
                nonlocal buffer
                while b'\n' not in buffer:
                    alive()
                    if not select.select([connection],[],[],.05)[0]: continue
                    data = connection.recv(4096)
                    require(data, 'diagnostic marker EOF')
                    buffer += data
                    require(len(buffer) < 8192, 'oversized diagnostic marker')
                line, buffer = buffer.split(b'\n',1)
                return json.loads(line)
            begin = message()
            expected = dict(schema='emuella-parallel-diagnostic-v1', event='begin', pid=peer[0],
                            operation=self.cell['operation'], requested_workers=self.cell['workers'], pool_threads=self.cell['workers'])
            require(set(begin) == set(expected)|{'pool_thread_ids'} and all(begin[k]==v for k,v in expected.items()), 'begin marker differs')
            pool = begin['pool_thread_ids']
            require(len(pool)==self.cell['workers'] and all(type(t) is int for t in pool) and len(set(pool+[peer[0]]))==len(pool)+1, 'pool TID coverage differs')
            tids = [peer[0]]+pool
            cpus = list(range(self.cell['workers']))
            self.trace['begin'] = begin
            self.trace['environment_begin'] = s.environment(self.receipt, lambda r: admission(r, process.pid))
            trace_file = self.folder/'thread-samples.jsonl'
            with trace_file.open('x') as output:
                def sample():
                    snap = task_snapshot(peer[0],tids,cpus)
                    line = json.dumps(snap)+'\n'
                    require(output.tell()+len(line.encode()) <= CAPS['trace_bytes_per_call'] and len(self.trace['samples']) < CAPS['samples_per_call'], 'trace cap')
                    output.write(line); output.flush()
                    self.trace['samples'].append(snap)
                sample()
                connection.sendall(b'{"ack":"begin"}\n')
                while not select.select([connection],[],[],CAPS['sample_seconds'])[0]:
                    alive(); sample()
                end = message()
                require(set(end)==set(begin)|{'diagnostic_facade_ns','cpu_snapshot_span_ns','thread_cpu_before_ns','thread_cpu_after_ns'} and all(end[k]==v for k,v in begin.items() if k!='event') and end['event']=='end', 'end marker differs')
                self.trace['end'] = end
                sample()
                self.trace['environment_end'] = s.environment(self.receipt, lambda r: admission(r,process.pid))
                connection.sendall(b'{"ack":"end"}\n')
            # Verification occurs only after the final snapshot/ack.
            return process.wait(timeout=max(.001, deadline-time.monotonic()))


def verify_binding(binding):
    require(binding['schema']==SCHEMA and binding['caps']==CAPS and binding['criteria']==CRITERIA, 'frozen protocol differs')
    require(helper.policy()==binding['policy_identity'], 'frozen frequency/boost/SMT policy differs')
    require(not any(os.environ.get(v) for v in ('EMUELLA_TIER1_ENCODER','EMUELLA_CLASSIC_WINDOW','LD_PRELOAD','LD_LIBRARY_PATH')), 'runtime override set')
    b = refresh.bind(Path(binding['build_path']))
    require(b==binding['build'] and b.get('parallel_diagnostics') is True and b['codec']['source_revision']==p.CODEC, 'diagnostic build identity differs')
    require(not any(b.get(k) for k in ('sampling','execution_diagnostics','allocation_diagnostics')), 'mixed diagnostic features')
    require(b['encoder_backend']==b['scheduling_window']=='default' and b['command'][b['command'].index('--features')+1]==FEATURES
            and b['command'][b['command'].index('--profile')+1]=='perf', 'build mode differs')
    require(refresh.classic.clean_source(refresh.ROOT)==binding['runner'], 'runner changed')
    require(sha(binding['original_binding'])==ORIGINAL and sha(binding['prepared_manifest'])==binding['prepared_sha256']==refresh.classic.MANIFEST, 'inherited binding or prepared identity changed')
    old=json.loads(Path(binding['original_binding']).read_text())
    require(binding['cells']==old['cells'], 'fixed four inherited cells changed')
    require(p.bytes_used(Path(binding['build_root'])) <= CAPS['build_bytes'], 'build cap')
    for cell in binding['cells']: p.verify_call(binding,cell)


def freeze(args):
    require(sha(args.original_binding)==ORIGINAL, 'original binding identity differs')
    old=json.loads(args.original_binding.read_text())
    store=Path(old['prepared_manifest']).parent.parent.resolve()
    require(args.binding.parent.resolve()==Path(args.build_root).resolve(), 'binding must be in registered build root')
    require(sha(store/'source/LICENSE.txt')==p.NOTICE, 'reviewed rights notice differs')
    binding=dict(schema=SCHEMA, caps=CAPS, criteria=CRITERIA, build_path=str(args.build.resolve()), build=refresh.bind(args.build),
                 benchmark_source=str(refresh.ROOT), codec_source=str(args.codec_source.resolve()), runner=refresh.classic.clean_source(refresh.ROOT),
                 original_binding=str(args.original_binding.resolve()), prepared_manifest=old['prepared_manifest'], prepared_sha256=old['prepared_sha256'],
                 cells=old['cells'], build_root=str(args.build_root.resolve()), store=str(store), decisions=args.decisions,
                 policy_identity=helper.policy(), condition='exclusive CPUs0–7 and16–23; partition=root, ordinary internal balancing; unchanged frequency/boost/SMT/IRQ/security',
                 cadence='fixed cell order0,1,2,3; sequential fresh processes, zero warmups or replacements; task-only snapshots every2ms while operation runs')
    verify_binding(binding)
    require(not args.binding.exists(), 'binding already exists')
    write(args.binding,binding)
    print('Frozen diagnostic binding SHA-256: '+sha(args.binding))


def run(args):
    require(sha(args.binding)==args.binding_sha256, 'reviewed binding changed')
    binding=json.loads(args.binding.read_text()); verify_binding(binding)
    receipt=json.loads(args.authority.read_text()); admission(receipt)
    require(receipt['valid_until_epoch']-time.time() >= CAPS['window_seconds'], 'reservation does not cover full diagnostic window')
    require(args.output.parent.resolve()==Path(binding['store']), 'evidence must stay in approved store')
    args.output.mkdir(exist_ok=False)
    write(args.output/'binding.json',binding); write(args.output/'authority.json',receipt)
    failures=[]; rows=[]
    with s.controller_placement(receipt,args.output):
        initial=s.environment(receipt,admission)
        start=time.monotonic_ns()
        write(args.output/'launch.json',dict(binding_sha256=args.binding_sha256,start_ns=start,environment=initial))
        def expired(signum,frame): raise TimeoutError('15-minute diagnostic window exhausted')
        original=signal.signal(signal.SIGALRM,expired); signal.alarm(CAPS['window_seconds'])
        try:
            for index,cell in enumerate(binding['cells']):
                require(index<4 and time.monotonic_ns()-start < (900-150)*10**9, 'call/window cap')
                require(p.bytes_used(args.output)<CAPS['evidence_bytes']-16*1024**2, 'evidence admission cap')
                write(args.output/f'call-{index}-started.json',dict(index=index,monotonic_ns=time.monotonic_ns()))
                verify_binding(binding)
                before=s.environment(receipt,admission)
                require(not stable_issues(initial,before,receipt), 'condition identity changed')
                folder=args.output/f'call-{index}'
                with tempfile.TemporaryDirectory(prefix='emuella-parallel-') as temporary:
                    endpoint=Path(temporary)/'worker.sock'
                    with socket.socket(socket.AF_UNIX,socket.SOCK_STREAM) as server:
                        server.bind(str(endpoint)); endpoint.chmod(0o600); server.listen(1)
                        monitor=Monitor(server,folder,receipt,cell,binding['build']['binary'])
                        env=dict(os.environ,EMUELLA_PARALLEL_DIAGNOSTIC_SOCKET=str(endpoint))
                        try:
                            result=refresh.run_process(binding['build']['binary'],cell['request'],folder,list(range(cell['workers'])),
                                placement=s.placement(receipt),parallel_diagnostics=True,monitor=monitor,environment=env)
                        finally:
                            # Samples are already retained incrementally, including failed handshakes.
                            write(args.output/f'call-{index}-markers.json',{k:v for k,v in monitor.trace.items() if k!='samples'})
                require(result['status']==0, 'diagnostic call failed')
                verify_binding(binding)
                after=s.environment(receipt,admission)
                write(args.output/f'call-{index}-environment.json',dict(before=before,after=after))
                require(not stable_issues(initial,after,receipt), 'condition identity changed')
                assessment=analyse_trace(monitor.trace,result['observation'])
                for boundary in ('environment_begin','environment_end'):
                    require(not stable_issues(initial,monitor.trace[boundary],receipt), 'operation condition changed')
                counters=[]
                for boundary in ('environment_begin','environment_end'):
                    raw=monitor.trace[boundary]['task_cgroup']['cpu.stat']
                    counters.append(dict(line.split() for line in raw.splitlines()) if raw else {})
                require(all('nr_throttled' in c for c in counters), 'mandatory throttle accounting missing')
                throttle=int(counters[1]['nr_throttled'])-int(counters[0]['nr_throttled'])
                assessment['nr_throttled_delta']=throttle
                if throttle: assessment['issues'].append('throttle counter changed'); assessment['supported']=False
                write(args.output/f'call-{index}-assessment.json',assessment)
                rows.append(dict(index=index,assessment=assessment))
                # Valid diagnostic inadequacy remains reportable; no favourable-result stopping.
                print(f"cell {index}: diagnostic retained; supported={assessment['supported']}",flush=True)
        except BaseException as error:
            failures.append(str(error))
            write(args.output/'failure.json',dict(reason=str(error),type=type(error).__name__,monotonic_ns=time.monotonic_ns()))
            raise
        finally:
            signal.alarm(0); signal.signal(signal.SIGALRM,original)
            write(args.output/'completion.json',dict(rows=rows,failures=failures,started_calls=len(list(args.output.glob('call-*-started.json'))),
                 wall_seconds=(time.monotonic_ns()-start)/1e9,evidence_bytes=p.bytes_used(args.output)))


def main():
    parser=argparse.ArgumentParser(description=__doc__); sub=parser.add_subparsers(dest='command',required=True)
    f=sub.add_parser('freeze')
    for key in ('build','codec-source','original-binding','build-root','binding'): f.add_argument('--'+key,type=Path,required=True)
    f.add_argument('--decisions',required=True)
    r=sub.add_parser('run')
    for key in ('binding','authority','output'): r.add_argument('--'+key,type=Path,required=True)
    r.add_argument('--binding-sha256',required=True)
    args=parser.parse_args(); (freeze if args.command=='freeze' else run)(args)


if __name__=='__main__': main()
