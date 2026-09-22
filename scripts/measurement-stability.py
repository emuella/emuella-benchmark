#!/usr/bin/env python3
"""Opt-in measurement-stability-qualification/v1; requires an authorised reservation."""
import argparse
from contextlib import contextmanager
import fcntl
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import time

sys.path.insert(0, str(Path(__file__).resolve().parent))
import precision_feasibility_analysis as analysis
import importlib.util
SPEC = importlib.util.spec_from_file_location('stability_precision', Path(__file__).with_name('precision-feasibility.py'))
p = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(p)
refresh, write, sha = p.refresh, p.write, p.sha
POLICY = 'measurement-stability-qualification/v1'
BALANCED_AA_SCHEMA = 'measurement-balanced-aa-qualification/v1'
PREPARATION_SCHEMA = 'balanced-measurement-stability-preparation/v1'
PAIRS, CALL_CAP, WALL_CAP, BYTE_CAP, BUILD_CAP = 40, 964, 7200, 2*1024**3, 30*1024**3
ORDERS = ((0, 1, 2, 3), (2, 3, 0, 1), (3, 2, 1, 0))
RAW_STREAM = (
    ('aaf064a2d6b302d839e7f3c13b99e1344ba749fed53be6daf64f8a6c4c67bfe7', 'ebac8279fd3c42cc757d98c9d17cfc0c18019ae839910084e0fd2a758fb801fb'),
    ('11b98f162a80c8d45a50f2ca3f1bc4e8b6d763aa4cc4af6401f340244b074573', '9e444c320a97937863a45d4fad62b691e9df6c769a51c484bfb2c0f4afcd74d0'),
    ('4b3b0f7baf1b13d65fff072ad1f52c7861388463a9b349918b3324d494660fd1', 'e4f42a0238389c5e39037c229dc6b6660edc91910cdf3d26801dbf06cbd1d289'))
STABLE_CPU = ('online', 'topology/core_id', 'topology/physical_package_id', 'topology/thread_siblings_list',
              'cpufreq/scaling_driver', 'cpufreq/scaling_governor', 'cpufreq/energy_performance_preference',
              'cpufreq/scaling_min_freq', 'cpufreq/scaling_max_freq')
CGROUP_FILES = ('cpuset.cpus.effective', 'cpuset.cpus.exclusive.effective', 'cpuset.cpus.partition',
                'cpuset.mems.effective', 'cpu.max', 'memory.max', 'pids.max')


def cpulist(value):
    result = set()
    for part in value.split(','):
        if part:
            bounds = [int(n) for n in part.split('-')]
            result.update(range(bounds[0], bounds[-1]+1))
    return sorted(result)


def schedule():
    return [dict(index=4*sweep+position, sweep=sweep, cell=cell,
                 starting_arm='A' if (cell+sweep) % 2 == 0 else 'B')
            for sweep, order in enumerate(ORDERS) for position, cell in enumerate(order)]


def calls(entry):
    first = entry['starting_arm']
    order = first+('B' if first == 'A' else 'A')
    return [dict(round=r, arm=arm, position=position)
            for r in range(PAIRS) for position, arm in enumerate(order if r % 2 == 0 else order[::-1])]


def reservation(receipt, *, sysroot=Path('/sys'), now=None, expected_partition='isolated', expected_schema=POLICY, occupied_group=None, expected_condition='balanced'):
    """Read-only admission of an existing delegated isolated cpuset, never creation.

    The authority record is supplied by the operational owner after review; its
    presence cannot itself confer administrator authority or establish provenance.
    """
    required = {'schema', 'authority', 'issuer', 'approved', 'valid_from_epoch', 'valid_until_epoch',
                'cgroup', 'worker_cpus', 'reserved_cpus', 'controller_cpus', 'residual_interference'}
    if expected_partition == 'root':
        required |= {'condition', 'partition_mode'}
        if receipt.get('condition') != expected_condition or receipt.get('partition_mode') != 'root':
            raise ValueError('explicit balanced partition identity required')
    elif expected_partition != 'isolated':
        raise ValueError('unsupported partition mode')
    if set(receipt) != required or receipt['schema'] != expected_schema or receipt['approved'] is not True:
        raise ValueError('explicit allowlisted reservation/authority receipt required')
    if not all(isinstance(receipt[k], str) and receipt[k].strip() for k in ('authority', 'issuer', 'residual_interference')):
        raise ValueError('authority and residual shared-package/cache interference must be stated')
    now = time.time() if now is None else now
    if not receipt['valid_from_epoch'] <= now < receipt['valid_until_epoch']:
        raise ValueError('reservation window is not active')
    groups = []
    for key in ('worker_cpus', 'reserved_cpus', 'controller_cpus'):
        values = receipt[key]
        if not isinstance(values, list) or not values or any(type(c) is not int or c < 0 for c in values) or values != sorted(set(values)):
            raise ValueError('CPU placement must be explicit sorted unique integers')
        groups.append(set(values))
    workers, reserved, controller = groups
    if len(workers) != 8 or not workers <= reserved or controller & reserved:
        raise ValueError('eight physical workers and disjoint controller placement required')
    cgroup = Path(receipt['cgroup']).resolve()
    cgroup.relative_to((sysroot/'fs/cgroup').resolve())
    values = {key: (cgroup/key).read_text().strip() for key in CGROUP_FILES}
    if (values['cpuset.cpus.partition'] != expected_partition
            or set(cpulist(values['cpuset.cpus.effective'])) != reserved
            or set(cpulist(values['cpuset.cpus.exclusive.effective'])) != reserved):
        raise ValueError('enforceable isolated exclusive cpuset covering all reserved CPUs required')
    members = (cgroup/'cgroup.procs').read_text().split()
    if any(cgroup.glob('*/cgroup.procs')) or (members and occupied_group is None):
        raise ValueError('worker partition must be empty and have no child cgroups')
    if occupied_group is not None and any(os.getpgid(int(pid)) != occupied_group for pid in members):
        raise ValueError('unrelated task entered worker reservation')
    if not os.access(cgroup/'cgroup.procs', os.W_OK):
        raise ValueError('worker cgroup placement has not been delegated')
    physical = set()
    for cpu in sorted(workers):
        root = sysroot/f'devices/system/cpu/cpu{cpu}/topology'
        siblings = set(cpulist((root/'thread_siblings_list').read_text()))
        if not siblings <= reserved:
            raise ValueError('reservation omits an SMT sibling')
        physical.add(((root/'physical_package_id').read_text(), (root/'core_id').read_text()))
    if len(physical) != 8:
        raise ValueError('worker placement repeats a physical core')
    values['ancestor_limits'] = []
    ancestor = cgroup.parent
    while ancestor.is_relative_to((sysroot/'fs/cgroup').resolve()):
        values['ancestor_limits'].append({key: p.read_optional(ancestor/key) for key in ('cpu.max', 'memory.max', 'cpuset.mems.effective')})
        if ancestor == (sysroot/'fs/cgroup').resolve():
            break
        ancestor = ancestor.parent
    return values



def admit(receipt, *, sysroot=Path('/sys'), now=None):
    """Explicit balanced A/A receipt; historical isolated admission is unchanged."""
    if receipt.get('schema') != BALANCED_AA_SCHEMA:
        return reservation(receipt, sysroot=sysroot, now=now)
    if (receipt['worker_cpus'] != list(range(8))
            or receipt['reserved_cpus'] != list(range(8))+list(range(16,24))
            or receipt['controller_cpus'] != list(range(8,16))+list(range(24,32))):
        raise ValueError('balanced A/A requires the diagnostically checked allocation')
    value = reservation(receipt, sysroot=sysroot, now=now, expected_partition='root',
                        expected_schema=BALANCED_AA_SCHEMA, expected_condition='balanced-aa')
    if value['cpu.max'].split()[0] != 'max' or any(
            row['cpu.max'] is not None and row['cpu.max'].split()[0] != 'max'
            for row in value['ancestor_limits']):
        raise ValueError('balanced A/A requires unlimited task and available ancestor CPU quotas')
    owner = Path(receipt['cgroup']).parent
    for child in (sysroot/'fs/cgroup').iterdir():
        if child.is_dir() and child != owner:
            if set(cpulist((child/'cpuset.cpus.effective').read_text())) & set(receipt['reserved_cpus']):
                raise ValueError('ordinary workload exclusion differs')
    return value


def environment(receipt, reservation_check=None):
    """Allowlisted external counters only; never enumerate unrelated commands."""
    value = dict(monotonic_ns=time.monotonic_ns(), utc_epoch=time.time(),
                 controller_affinity=sorted(os.sched_getaffinity(0)),
                 reservation=(reservation_check or admit)(receipt), cpu={},
                 boost=p.read_optional('/sys/devices/system/cpu/cpufreq/boost'),
                 proc={key: p.read_optional('/proc/'+key) for key in ('stat', 'loadavg', 'pressure/cpu', 'pressure/memory', 'pressure/io')},
                 effective_frequency='unavailable; frequency snapshots are not effective frequency',
                 migrations='unavailable', task_context_switches='per-call GNU time, outside operation clock')
    for cpu in receipt['reserved_cpus']:
        root = Path(f'/sys/devices/system/cpu/cpu{cpu}')
        value['cpu'][str(cpu)] = {key: p.read_optional(root/key) for key in STABLE_CPU +
            ('cpufreq/scaling_cur_freq', 'thermal_throttle/core_throttle_count', 'thermal_throttle/package_throttle_count')}
        value['cpu'][str(cpu)]['numa_nodes'] = sorted(x.name for x in root.glob('node[0-9]*'))
        value['cpu'][str(cpu)]['shared_caches'] = {x.parent.name: p.read_optional(x) for x in root.glob('cache/index*/shared_cpu_list')}
    root = Path(receipt['cgroup'])
    value['task_cgroup'] = {key: p.read_optional(root/key) for key in ('cpu.stat', 'cpu.pressure', 'memory.current', 'memory.events')}
    return value


def environment_issues(before, after, receipt):
    issues = []
    if after['controller_affinity'] != receipt['controller_cpus']:
        issues.append('controller affinity differs from frozen off-core placement')
    for key in ('reservation', 'boost'):
        if before[key] != after[key]:
            issues.append(key+' changed')
    if before['cpu'].keys() != after['cpu'].keys():
        issues.append('CPU topology changed')
    for cpu, original in before['cpu'].items():
        observed = after['cpu'].get(cpu, {})
        for key in STABLE_CPU + ('numa_nodes', 'shared_caches'):
            if original.get(key) != observed.get(key):
                issues.append(f'CPU {cpu} {key} changed')
        for key in ('thermal_throttle/core_throttle_count', 'thermal_throttle/package_throttle_count'):
            a, b = original.get(key), observed.get(key)
            if a is not None and b is not None and int(b) > int(a):
                issues.append(f'CPU {cpu} {key} increased')
    def counter(snapshot, key):
        fields = (snapshot.get('task_cgroup', {}).get('cpu.stat') or '').split()
        return dict(zip(fields[::2], fields[1::2])).get(key)
    a, b = counter(before, 'nr_throttled'), counter(after, 'nr_throttled')
    if a is not None and b is not None and int(b) > int(a):
        issues.append('task CPU throttle counter increased')
    return issues


@contextmanager
def controller_placement(receipt, output):
    original = set(os.sched_getaffinity(0))
    intended = set(receipt['controller_cpus'])
    if not intended <= original:
        raise ValueError('controller placement exceeds existing delegated affinity')
    write(output/'placement-original.json', dict(original=sorted(original), intended=sorted(intended), host_policy_changes=False))
    os.sched_setaffinity(0, intended)
    handlers = {}
    def interrupted(signum, frame):
        raise KeyboardInterrupt('interrupted by signal '+str(signum))
    try:
        for signum in (signal.SIGTERM, signal.SIGINT):
            handlers[signum] = signal.signal(signum, interrupted)
        yield
    finally:
        current = set(os.sched_getaffinity(0))
        intervened = current != intended
        if not intervened:
            os.sched_setaffinity(0, original)
        restored = set(os.sched_getaffinity(0)) == original and not intervened
        empty = not (Path(receipt['cgroup'])/'cgroup.procs').read_text().strip()
        write(output/'restoration.json', dict(original=sorted(original), observed_before_restore=sorted(current),
            final=sorted(os.sched_getaffinity(0)), restored=restored, intervening_change=intervened,
            worker_cgroup_empty=empty, host_policy_changes=False,
            reservation_release='externally owned; this task neither creates nor releases it'))
        for signum, handler in handlers.items():
            signal.signal(signum, handler)
        if not restored or not empty:
            raise ValueError('operational blocker: placement restoration or worker cleanup unresolved')


def placement(receipt):
    # Executed only in the new child. The controller never enters the worker partition.
    def enter():
        (Path(receipt['cgroup'])/'cgroup.procs').write_text(str(os.getpid()))
    return enter


def estimator_identity(executable):
    executable = Path(executable).resolve()
    root = executable.parents[2]
    provenance = json.loads((root/'provenance.json').read_text())
    source = analysis.COMPARE_SOURCE.read_text()
    owner_module = (root/'src/owner_compare.rs').read_text()
    import hashlib
    if (provenance.get('owner_sha256') != sha(analysis.COMPARE_SOURCE)
            or not owner_module.startswith(source)
            or provenance.get('wrapper_sha256') != hashlib.sha256(owner_module[len(source):].encode()).hexdigest()
            or provenance.get('method') != 'Unchanged owner interval and classification; fixed40 independent means;5%;99% conservative per-comparison ratio interval; no outlier removal'):
        raise ValueError('actual forty-pair comparator wrapper provenance differs')
    return dict(path=str(executable), sha256=sha(executable), provenance=provenance,
                provenance_sha256=sha(root/'provenance.json'),
                owner_module_sha256=sha(root/'src/owner_compare.rs'),
                entrypoint_sha256=sha(root/'src/main.rs'), manifest_sha256=sha(root/'Cargo.toml'))


def verify_core(binding):
    if any(os.environ.get(key) for key in ('EMUELLA_TIER1_ENCODER', 'EMUELLA_CLASSIC_WINDOW', 'LD_PRELOAD', 'LD_LIBRARY_PATH')):
        raise ValueError('runtime selector/library overrides must be unset')
    p.verify_build(binding['build'])
    if estimator_identity(binding['estimator']['path']) != binding['estimator']:
        raise ValueError('frozen comparator executable/provenance changed')
    specs = [('encode', 1, 8, 'emuella'), ('encode', 1, 8, 'emuella'), ('decode', 0, 8, 'openjpeg'), ('decode', 0, 1, 'openjpeg')]
    if len(binding['cells']) != 4:
        raise ValueError('four mandatory workload cells required')
    for index, (cell, expected) in enumerate(zip(binding['cells'], specs)):
        if tuple(cell[key] for key in ('operation', 'style', 'workers', 'origin')) != expected:
            raise ValueError('fixed workload cell differs')
        request = cell['request']
        if (request['raw_sha256'], request['stream_sha256']) != RAW_STREAM[min(index, 2)]:
            raise ValueError('exact inherited workload identities required')
        if (request['codec'], request['operation'], request['style'], request['workers'], request['layout'], request['max_working_bytes'], request['max_output_bytes']) != ('emuella', *expected[:3], 'interleaved', refresh.classic.WORKING, refresh.classic.OUTPUT):
            raise ValueError('fixed production request differs')
        if set(request) != {'codec', 'operation', 'case_id', 'round', 'width', 'height', 'components', 'bits', 'layout', 'style', 'workers', 'raw_path', 'raw_sha256', 'stream_path', 'stream_sha256', 'max_working_bytes', 'max_output_bytes'}:
            raise ValueError('unexpected worker request fields')
    if binding['policy'] != POLICY or binding['schedule'] != schedule() or binding['pairs'] != PAIRS:
        raise ValueError('frozen protocol/schedule differs')
    if (binding['boundary'] != refresh.BOUNDARY or binding['warmups'] != 0 or binding['samples_per_process'] != 1
            or binding['prepared_sha256'] != refresh.classic.MANIFEST):
        raise ValueError('inherited fresh-process boundary or prepared identity differs')
    if binding['limits'] != limits() or binding['launch_cadence'] != cadence():
        raise ValueError('frozen budgets/cadence differ')
    if refresh.classic.clean_source(refresh.ROOT) != binding['runner']:
        raise ValueError('runner source changed')
    if not Path(binding['build_root']).is_dir():
        raise ValueError('registered build root missing')
    if p.bytes_used(Path(binding['build_root'])) > BUILD_CAP:
        raise ValueError('registered disposable build cap exceeded')


def verify_binding(binding):
    verify_core(binding)
    if sha(binding['authority_path']) != binding['authority_sha256']:
        raise ValueError('authority receipt changed')
    admit(binding['condition'])
    if binding['condition'].get('schema') == BALANCED_AA_SCHEMA:
        preparation = read_preparation(Path(binding['preparation_path']), binding['preparation_sha256'])
        if any(binding.get(key) != value for key,value in preparation['binding'].items()):
            raise ValueError('prepared production identities changed')
        if binding['condition']['authority'] != binding['decisions']:
            raise ValueError('live authority differs from the reviewed decision')


def limits():
    return dict(timed_calls=960, preflights=4, total_calls=CALL_CAP, pairs_per_session=PAIRS,
                sessions=12, observation_seconds=WALL_CAP, evidence_bytes=BYTE_CAP, disposable_build_bytes=BUILD_CAP)


def cadence():
    return 'Sequential fresh processes; zero warmups; external identity/reservation checks and telemetry before/after each call; no inserted sleep or outcome-dependent delay.'


def planned_binding(args):
    build = refresh.bind(args.build)
    p.verify_build(build)
    store = args.prepared.parent.resolve()
    if args.output.parent.resolve() != store or args.streams.parent.resolve() != store:
        raise ValueError('evidence/streams must remain in the approved persistent store')
    if sha(store/'source/LICENSE.txt') != p.NOTICE or sha(args.prepared/'prepared.json') != refresh.classic.MANIFEST:
        raise ValueError('reviewed notice or exact prepared contract differs')
    cells = [p.selected_cells(refresh.classic.assets(args.prepared))[i] for i in (1, 3, 5, 4)]
    for index, cell in enumerate(cells):
        cell['request'] = refresh.make_request(cell['asset'], args.prepared, args.streams, cell['origin'], 'emuella', cell['style'], cell['workers'], cell['operation'], 0)
        expected = RAW_STREAM[min(index, 2)]
        if (cell['request']['raw_sha256'], cell['request']['stream_sha256']) != expected:
            raise ValueError('inherited raw/stream identity differs')
    binding = dict(policy=POLICY, estimator=estimator_identity(args.estimator), build_path=str(args.build.resolve()), build=build,
        codec_source=str(args.codec_source.resolve()), benchmark_source=str(args.worker_benchmark_source.resolve()),
        runner=refresh.classic.clean_source(refresh.ROOT), prepared_manifest=str(args.prepared/'prepared.json'),
        prepared_sha256=sha(args.prepared/'prepared.json'), cells=cells, schedule=schedule(), pairs=PAIRS,
        build_root=str(args.build_root.resolve()), limits=limits(),
        launch_cadence=cadence(), boundary=refresh.BOUNDARY, warmups=0, samples_per_process=1,
        decisions=args.decisions, invalidity='Identity, reservation, policy, topology, affinity, throttle counter increase, failed/missing call or cap failure stops the cohort; retain all attempts. Timing outcomes never invalidate.')
    verify_core(binding)
    for cell in cells:
        p.verify_call(binding, cell)
    return binding


def publish_binding(output, binding):
    store = output.parent.resolve()
    output.mkdir(exist_ok=False)
    (output/'LICENSE.txt').write_bytes((store/'source/LICENSE.txt').read_bytes())
    (output/'NOTICE.txt').write_text('RarePlanes Dataset (June 2020), J. Shermeyer et al.; In-Q-Tel – CosmiQ Works and AI.Reverie. CC BY-SA 4.0. Local A/A observations; unchanged inputs, streams and lineage remain in their authorised store. No imagery redistribution.\n')
    write(output/'binding.json', binding)
    print('Frozen binding SHA-256: '+sha(output/'binding.json'))


def freeze(args):
    condition = json.loads(args.authority.read_text())
    # Historical entry point stays isolated; balanced A/A uses a frozen preparation.
    reservation(condition)
    if condition['valid_until_epoch']-time.time() < WALL_CAP:
        raise ValueError('authorised reservation must cover the complete two-hour window')
    binding = planned_binding(args)
    binding.update(authority_path=str(args.authority.resolve()), authority_sha256=sha(args.authority),
                   condition=condition, environment=environment(condition))
    verify_binding(binding)
    publish_binding(args.output, binding)


def read_preparation(path, digest):
    import measurement_reservation as helper
    if sha(path) != digest:
        raise ValueError('frozen preparation changed')
    prepared = json.loads(path.read_text())
    if (prepared['schema'] != PREPARATION_SCHEMA or prepared['condition'] != 'balanced-aa'
            or prepared['helper_sha256'] != sha(Path(__file__).with_name('measurement_reservation.py'))
            or prepared['host_policy'] != helper.policy()):
        raise ValueError('prepared condition, helper or frequency/boost/SMT policy changed')
    if Path(prepared['output']).parent.resolve() != Path(prepared['binding']['prepared_manifest']).parent.parent.resolve():
        raise ValueError('prepared output leaves approved store')
    return prepared


def prepare_balanced(args):
    import measurement_reservation as helper
    if args.preparation.parent.resolve() != args.build_root.resolve() or args.output.exists():
        raise ValueError('new preparation belongs in registered scratch; output must be unlaunched')
    binding = planned_binding(args)
    write(args.preparation, dict(schema=PREPARATION_SCHEMA, condition='balanced-aa',
          binding=binding, output=str(args.output.resolve()), host_policy=helper.policy(),
          helper_sha256=sha(Path(__file__).with_name('measurement_reservation.py')),
          scope='Unlaunched production A/A; same fixed 964 starts, two hours, 2 GiB. Live reservation admission remains mandatory.'))
    print('Frozen preparation SHA-256: '+sha(args.preparation))


def launch_balanced(args):
    prepared = read_preparation(args.preparation, args.preparation_sha256)
    binding = dict(prepared['binding'])
    verify_core(binding)
    condition = json.loads(args.authority.read_text())
    if condition.get('schema') != BALANCED_AA_SCHEMA or condition.get('authority') != binding['decisions']:
        raise ValueError('balanced A/A requires its exact reviewed live authority')
    admit(condition)
    if condition['valid_until_epoch']-time.time() < WALL_CAP:
        raise ValueError('authorised reservation must cover the complete two-hour window')
    for cell in binding['cells']:
        p.verify_call(binding,cell)
    binding.update(authority_path=str(args.authority.resolve()), authority_sha256=sha(args.authority),
                   condition=condition, environment=environment(condition),
                   preparation_path=str(args.preparation.resolve()), preparation_sha256=args.preparation_sha256)
    verify_binding(binding)
    output = Path(prepared['output'])
    publish_binding(output, binding)
    write(output/'preparation.json',prepared)
    study(output)


def budget_check(root, start_ns):
    if p.started_count(root) >= CALL_CAP:
        raise ValueError('964-call cap reached, including failed attempts')
    if time.monotonic_ns()-start_ns >= (WALL_CAP-150)*10**9:
        raise ValueError('insufficient observation window for one bounded call')
    if p.bytes_used(root) >= BYTE_CAP-1024**2:
        raise ValueError('new-evidence cap reached')


def observe(root, binding, folder, cell, identity, start_ns):
    budget_check(root, start_ns)
    name = f"call-{identity['round']:02}-{identity['arm']}"
    started = time.monotonic_ns()
    write(folder/(name+'-started.json'), dict(identity=identity, monotonic_ns=started))
    result = {}
    try:
        verify_binding(binding)
        before = environment(binding['condition'])
        issues = environment_issues(binding['environment'], before, binding['condition'])
        if issues:
            raise ValueError('; '.join(issues))
        p.verify_call(binding, cell)
        result = refresh.run_process(binding['build']['binary'], dict(cell['request'], round=identity['round']),
            folder/name, binding['condition']['worker_cpus'][:cell['workers']], placement=placement(binding['condition']))
        p.verify_call(binding, cell)
        verify_binding(binding)
        after = environment(binding['condition'])
        issues = environment_issues(binding['environment'], after, binding['condition'])
        write(folder/(name+'-environment.json'), dict(before=before, after=after, issues=issues))
        if issues:
            result.update(status='invalid_environment', reason='; '.join(issues))
    except BaseException as error:
        result.update(status='failed_attempt', reason=str(error))
        row = dict(identity, result=result, started_monotonic_ns=started)
        write(folder/(name+'-receipt.json'), row)
        if not isinstance(error, Exception):
            raise
        return row
    row = dict(identity, result=result, started_monotonic_ns=started)
    write(folder/(name+'-receipt.json'), row)
    return row


def read_binding(root):
    binding = json.loads((root/'binding.json').read_text())
    launch = json.loads((root/'launch.json').read_text())
    if sha(root/'binding.json') != launch['binding_sha256']:
        raise ValueError('binding changed after launch')
    verify_binding(binding)
    return binding, launch


def session(root, index):
    with (root/'session.lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        binding, launch = read_binding(root)
        pre = json.loads((root/'preflight/preflight.json').read_text())
        if len(pre['rows']) != 4 or any(r['result']['status'] != 0 for r in pre['rows']):
            raise ValueError('four successful preflights required')
        if index:
            previous = json.loads((root/f'session-{index-1:02}/session.json').read_text())
            if not previous['complete'] or not previous['valid']:
                raise ValueError('previous session incomplete or invalid')
        entry = schedule()[index]
        folder = root/f'session-{index:02}'
        folder.mkdir(exist_ok=False)
        write(folder/'started.json', dict(session=entry, binding_sha256=sha(root/'binding.json'), controller_pid=os.getpid()))
        rows, issues = [], []
        try:
            for identity in calls(entry):
                row = observe(root, binding, folder, binding['cells'][entry['cell']], identity, launch['start_ns'])
                rows.append(row)
                if row['result']['status'] != 0:
                    issues.append('failed or invalid call; no replacement or further observations')
                    break
        except BaseException as error:
            issues.append(str(error))
            raise
        finally:
            write(folder/'session.json', dict(session=entry, rows=rows, issues=issues, valid=not issues,
                complete=len(rows)==80 and all(r['result']['status']==0 for r in rows), binding_sha256=sha(root/'binding.json')))


def study(root):
    with (root/'study.lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        binding = json.loads((root/'binding.json').read_text())
        verify_binding(binding)
        if binding['condition']['valid_until_epoch']-time.time() < WALL_CAP:
            raise ValueError('reservation no longer covers full observation window')
        if (root/'launch.json').exists():
            raise ValueError('cohort already launched; retries/replacements forbidden')
        with controller_placement(binding['condition'], root):
            before = environment(binding['condition'])
            issues = environment_issues(binding['environment'], before, binding['condition'])
            if issues:
                raise ValueError('; '.join(issues))
            start = time.monotonic_ns()
            write(root/'launch.json', dict(start_ns=start, binding_sha256=sha(root/'binding.json'), environment=before))
            outcomes, failures = [], []
            try:
                pre = root/'preflight'
                pre.mkdir()
                rows = []
                try:
                    for index, cell in enumerate(binding['cells']):
                        row = observe(root, binding, pre, cell, dict(round=index, arm='preflight', position=0), start)
                        rows.append(row)
                        if row['result']['status'] != 0:
                            raise ValueError('preflight failed; no replacements')
                finally:
                    write(pre/'preflight.json', dict(rows=rows, interpretation='Untimed setup for inference; retained worker clocks excluded'))
                for entry in schedule():
                    budget_check(root, start)
                    child = subprocess.Popen([sys.executable, str(Path(__file__).resolve()), 'session', '--output', str(root), '--index', str(entry['index'])])
                    try:
                        code = child.wait()
                    except BaseException:
                        child.terminate()
                        child.wait()
                        raise
                    outcomes.append(dict(index=entry['index'], exit_code=code))
                    measured = json.loads((root/f"session-{entry['index']:02}/session.json").read_text()) if code == 0 else {}
                    if code or not measured.get('valid') or not measured.get('complete'):
                        raise ValueError('session failed/invalid/incomplete; cohort stopped')
            except BaseException as error:
                failures.append(str(error))
                raise
            finally:
                write(root/'completion.json', dict(outcomes=outcomes, failures=failures, started_calls=p.started_count(root),
                    wall_seconds=(time.monotonic_ns()-start)/1e9, new_evidence_bytes=p.bytes_used(root), binding_sha256=sha(root/'binding.json')))


def analyse(root, estimator, report):
    binding = json.loads((root/'binding.json').read_text())
    launch = json.loads((root/'launch.json').read_text())
    if binding['policy'] != POLICY or binding['schedule'] != schedule() or sha(root/'binding.json') != launch['binding_sha256']:
        raise ValueError('frozen identity/schedule differs')
    if estimator_identity(estimator) != binding['estimator']:
        raise ValueError('analysis must use the prospectively frozen comparator executable/provenance')
    if report.parent.resolve() != root.resolve():
        raise ValueError('raw report must stay in the approved evidence root')
    def optional(path):
        return json.loads(path.read_text()) if path.exists() else {}
    completion = optional(root/'completion.json')
    restoration = optional(root/'restoration.json')
    preflight = optional(root/'preflight/preflight.json')
    global_valid = (completion.get('started_calls') == CALL_CAP and p.started_count(root) == CALL_CAP
        and not completion.get('failures') and completion.get('wall_seconds', WALL_CAP+1) <= WALL_CAP
        and completion.get('new_evidence_bytes', BYTE_CAP+1) <= BYTE_CAP
        and restoration.get('restored') is True and restoration.get('worker_cgroup_empty') is True
        and len(preflight.get('rows', [])) == 4 and all(r['result']['status'] == 0 for r in preflight.get('rows', [])))
    sessions = []
    for entry in schedule():
        folder = root/f"session-{entry['index']:02}"
        path = folder/'session.json'
        measured = json.loads(path.read_text()) if path.exists() else {}
        rows = sorted((json.loads(x.read_text()) for x in folder.glob('call-*-receipt.json')), key=lambda r:(r['round'], r['position']))
        valid = (measured.get('session') == entry and measured.get('binding_sha256') == launch['binding_sha256']
                 and measured.get('rows') == rows and measured.get('valid') is True
                 and [{k: r[k] for k in ('round', 'arm', 'position')} for r in rows] == calls(entry))
        # Retain comparator outputs for every structurally complete session even
        # when environmental/provenance validity failed; never qualify that scope.
        result = analysis.analyse_session(rows, estimator, rounds=PAIRS)
        if not valid:
            result['valid'] = False
            result['issues'].append('session environment/provenance validity was not established')
        result.update(session=entry, environment_issues=measured.get('issues', ['missing terminal session record']),
            started_attempts=[json.loads(x.read_text()) for x in sorted(folder.glob('call-*-started.json'))])
        sessions.append(result)
    # Aggregate receipts cannot substitute for complete, valid mandatory sessions.
    global_valid = global_valid and all(session['complete'] and session['valid'] for session in sessions)
    cells = [dict(cell=index, operation=cell['operation'], workers=cell['workers'], case_id=cell['asset']['id'],
                  disposition=(analysis.classify_cell([s for s in sessions if s['session']['cell']==index]) if global_valid else analysis.INCOMPLETE),
                  session_only_disposition=analysis.classify_cell([s for s in sessions if s['session']['cell']==index]))
             for index, cell in enumerate(binding['cells'])]
    write(report, dict(policy=POLICY, binding_sha256=sha(root/'binding.json'), estimator_sha256=sha(estimator),
        comparator_sha256=sha(analysis.COMPARE_SOURCE), cells=cells, sessions=sessions,
        completion=completion, restoration=restoration, operationally_complete=global_valid,
        scope='Prospective condition check only; no historical pooling, candidate claim, empirical coverage, power or probability-of-all-passing guarantee.'))


def inspect(output):
    """No authority inference, real inputs, worker build or reservation mutation."""
    current = p.read_optional('/proc/self/cgroup')
    relative = next((line[3:] for line in (current or '').splitlines() if line.startswith('0::')), None)
    cgroup = Path('/sys/fs/cgroup')/relative.lstrip('/') if relative else None
    observed = {key: p.read_optional(cgroup/key) for key in CGROUP_FILES} if cgroup else {}
    sessions = []
    for entry in schedule():
        value = analysis.analyse_session([], lambda payload: None, valid=False, rounds=PAIRS)
        value.update(session=entry, state='not launched; authorised enforceable reservation absent')
        sessions.append(value)
    write(output, dict(policy=POLICY, status='blocked before preflight', real_input_calls=0,
        condition_established=False, authority_supplied=False, limits=limits(), schedule=schedule(),
        comparator_sha256=sha(analysis.COMPARE_SOURCE), launch_cadence=cadence(),
        controller_affinity=sorted(os.sched_getaffinity(0)), observed_current_cgroup=observed,
        placement_delegated=os.access(cgroup/'cgroup.procs', os.W_OK) if cgroup else False,
        sessions=sessions, cells=[dict(cell=i, disposition=analysis.INCOMPLETE) for i in range(4)],
        restoration=dict(task_changes=[], restoration_required=False, host_policy_changes=False),
        next_decision='Obtain one reviewed resource-owner delegation for an enforceable SMT-inclusive exclusive CPU reservation; then freeze before any real-input invocation.',
        scope='No stability conclusion, projection, confirmation design or candidate decision is supported by an unlaunched cohort.'))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='command', required=True)
    freeze_parser = sub.add_parser('freeze')
    for name in ('build', 'codec-source', 'worker-benchmark-source', 'prepared', 'streams', 'authority', 'build-root', 'estimator', 'output'):
        freeze_parser.add_argument('--'+name, type=Path, required=True)
    freeze_parser.add_argument('--decisions', required=True, help='Exact reviewed workspace operational/design decision permalink')
    prepare_parser = sub.add_parser('prepare-balanced')
    for name in ('build','codec-source','worker-benchmark-source','prepared','streams','build-root','estimator','output','preparation'):
        prepare_parser.add_argument('--'+name,type=Path,required=True)
    prepare_parser.add_argument('--decisions',required=True)
    launch_parser = sub.add_parser('launch-balanced')
    launch_parser.add_argument('--preparation',type=Path,required=True)
    launch_parser.add_argument('--preparation-sha256',required=True)
    launch_parser.add_argument('--authority',type=Path,required=True)
    estimator_parser = sub.add_parser('estimator')
    estimator_parser.add_argument('--output', type=Path, required=True)
    inspect_parser = sub.add_parser('inspect')
    inspect_parser.add_argument('--output', type=Path, required=True)
    check = sub.add_parser('check-reservation')
    check.add_argument('--authority', type=Path, required=True)
    for name in ('study', 'session', 'analyse'):
        child = sub.add_parser(name)
        child.add_argument('--output', type=Path, required=True)
        if name == 'session':
            child.add_argument('--index', type=int, choices=range(12), required=True)
        if name == 'analyse':
            for key in ('estimator', 'report'):
                child.add_argument('--'+key, type=Path, required=True)
    args = parser.parse_args()
    if args.command == 'freeze':
        freeze(args)
    elif args.command == 'prepare-balanced':
        prepare_balanced(args)
    elif args.command == 'launch-balanced':
        launch_balanced(args)
    elif args.command == 'inspect':
        inspect(args.output)
    elif args.command == 'estimator':
        refresh.classic.estimator_build(refresh.ROOT, args.output, rounds=PAIRS)
    elif args.command == 'check-reservation':
        print(json.dumps(admit(json.loads(args.authority.read_text())), indent=2))
    elif args.command == 'study':
        study(args.output)
    elif args.command == 'session':
        def interrupted(signum, frame):
            raise KeyboardInterrupt('session interrupted')
        signal.signal(signal.SIGTERM, interrupted)
        session(args.output, args.index)
    else:
        analyse(args.output, args.estimator, args.report)


if __name__ == '__main__':
    main()
