#!/usr/bin/env python3
"""Offline metadata audit of measurement-stability-qualification/v1 execution."""
import argparse
import hashlib
import json
import math
from pathlib import Path
import statistics

POLICY = 'measurement-stability-qualification/v1'
CPUS = list(range(8)) + list(range(16, 24))
ORDERS = ((0, 1, 2, 3), (2, 3, 0, 1), (3, 2, 1, 0))


def require(condition, message):
    if not condition:
        raise ValueError(message)


def schedule():
    return [dict(index=4*sweep+position, sweep=sweep, cell=cell,
                 starting_arm='A' if (cell+sweep) % 2 == 0 else 'B')
            for sweep, order in enumerate(ORDERS) for position, cell in enumerate(order)]


def calls(entry):
    order = 'AB' if entry['starting_arm'] == 'A' else 'BA'
    return [dict(round=r, arm=arm, position=p) for r in range(40)
            for p, arm in enumerate(order if r % 2 == 0 else order[::-1])]


def cpu_counters(value):
    """User (already including guest), nice and system ticks per logical CPU."""
    require(isinstance(value, str), 'missing /proc/stat')
    result = {}
    for line in value.splitlines():
        fields = line.split()
        if not fields or not fields[0].startswith('cpu') or fields[0] == 'cpu':
            continue
        require(fields[0][3:].isdigit() and len(fields) >= 4, 'malformed CPU counters')
        cpu = int(fields[0][3:])
        require(cpu not in result and all(v.isdigit() for v in fields[1:]), 'invalid CPU counters')
        result[cpu] = tuple(map(int, fields[1:4]))
    require(set(CPUS) <= result.keys(), 'missing reserved CPU counters')
    return result


def throttle_counter(value):
    if value is None:
        return None
    require(isinstance(value, str), 'malformed cpu.stat')
    result = {}
    for line in value.splitlines():
        fields = line.split()
        require(len(fields) == 2 and fields[1].isdigit() and fields[0] not in result,
                'malformed cpu.stat counters')
        result[fields[0]] = int(fields[1])
    return result.get('nr_throttled')


def quotas(environment):
    reservation = environment.get('reservation', {})
    ancestors = reservation.get('ancestor_limits')
    return dict(leaf=reservation.get('cpu.max'),
                ancestors=None if ancestors is None else [a.get('cpu.max') for a in ancestors])


def derive(environment, result):
    before, after = environment['before'], environment['after']
    require(environment['issues'] == [], 'invalid call environment')
    a, b = [cpu_counters(e['proc']['stat']) for e in (before, after)]
    require(a.keys() == b.keys(), 'CPU coverage changed')
    deltas = {}
    for cpu in a:
        fields = [y-x for x, y in zip(a[cpu], b[cpu])]
        require(min(fields) >= 0, 'negative CPU counter delta')
        deltas[cpu] = sum(fields)
    reserved = {str(cpu): deltas[cpu] for cpu in CPUS}
    total = sum(reserved.values())
    require(total > 0, 'no reserved CPU activity')
    dominant = max(CPUS, key=lambda cpu: deltas[cpu])
    worker_total = sum(deltas[cpu] for cpu in range(8))
    require(worker_total > 0, 'no worker CPU activity')
    worker_dominant = max(range(8), key=lambda cpu: deltas[cpu])
    throttles = [throttle_counter(e.get('task_cgroup', {}).get('cpu.stat')) for e in (before, after)]
    throttle_delta = None if None in throttles else throttles[1]-throttles[0]
    require(throttle_delta is None or throttle_delta >= 0, 'negative throttle counter delta')
    cpu_seconds, wall_ns = result['process_cpu_seconds'], result['process_wall_ns']
    require(all(type(x) in (int, float) and math.isfinite(x) and x > 0 for x in (cpu_seconds, wall_ns)),
            'invalid whole-process CPU/wall measurements')
    require(all(type(e['monotonic_ns']) is int and e['monotonic_ns'] >= 0 for e in (before, after)),
            'invalid environment timestamps')
    span = after['monotonic_ns']-before['monotonic_ns']
    require(span > 0, 'invalid environment counter span')
    return dict(reserved_user_nice_system_ticks=reserved, reserved_ticks=total,
                dominant_logical_cpu=dominant, dominant_share=deltas[dominant]/total,
                other_reserved_cpu_ticks=total-deltas[dominant],
                worker_cpu_ticks=worker_total, worker_dominant_logical_cpu=worker_dominant,
                worker_dominant_share=deltas[worker_dominant]/worker_total,
                other_worker_cpu_ticks=worker_total-deltas[worker_dominant],
                reserved_sibling_cpu_ticks=total-worker_total,
                outside_reserved_cpu_ticks=sum(v for cpu, v in deltas.items() if cpu not in CPUS),
                whole_process_cpu_seconds=cpu_seconds, whole_process_wall_ns=wall_ns,
                whole_process_cpu_wall_ratio=cpu_seconds*1e9/wall_ns, environment_span_ns=span,
                quota_before=quotas(before), quota_after=quotas(after),
                nr_throttled_before=throttles[0], nr_throttled_after=throttles[1],
                nr_throttled_delta=throttle_delta)


def audit(root, manifest_sha256):
    root = Path(root).resolve()
    used = {}

    def read(relative, digest):
        path = root/relative
        require(path.resolve().is_relative_to(root), 'metadata path escapes root')
        data = path.read_bytes()
        require(hashlib.sha256(data).hexdigest() == digest, f'metadata hash mismatch: {relative}')
        used[relative] = digest
        return json.loads(data)

    manifest = read('observation-manifest.json', manifest_sha256)

    def load(relative):
        require(relative in manifest, f'missing manifest coverage: {relative}')
        return read(relative, manifest[relative])

    binding, report, launch = [load(p) for p in ('binding.json', 'report.json', 'launch.json')]
    binding_sha = manifest['binding.json']
    require(binding['policy'] == report['policy'] == POLICY and binding['schedule'] == schedule()
            and binding['pairs'] == 40, 'unexpected study schedule')
    require(launch['binding_sha256'] == report['binding_sha256'] == binding_sha,
            'binding identity mismatch')
    require(report['operationally_complete'] is True and report['completion']['started_calls'] == 964,
            'incomplete study report')
    require(binding['condition']['reserved_cpus'] == CPUS
            and binding['condition']['worker_cpus'] == list(range(8)), 'unexpected reserved/worker CPUs')
    require(len(binding['cells']) == 4 and [c['workers'] for c in binding['cells']] == [8, 8, 8, 1],
            'unexpected requested workers')
    binary_sha = binding['build']['binary_sha256']
    require(isinstance(binary_sha, str) and len(binary_sha) == 64
            and all(c in '0123456789abcdef' for c in binary_sha), 'invalid binary identity')
    require(len(report['sessions']) == 12, 'report session coverage differs')
    rows, summaries, expected_started = [], [], set()
    for entry in schedule():
        index = entry['index']
        folder = f'session-{index:02}'
        session = load(f'{folder}/session.json')
        reported = report['sessions'][index]
        require(session['session'] == reported['session'] == entry
                and session['binding_sha256'] == binding_sha and session['valid'] is True
                and session['complete'] is True and session['issues'] == []
                and reported['valid'] is True and reported['complete'] is True,
                'invalid session')
        require(len(session['rows']) == 80 and reported['raw_rows'] == session['rows'], 'session row coverage differs')
        cell = binding['cells'][entry['cell']]
        derived = []
        for identity, retained in zip(calls(entry), session['rows']):
            name = f"{folder}/call-{identity['round']:02}-{identity['arm']}"
            receipt, environment, started = [load(name+suffix+'.json') for suffix in ('-receipt', '-environment', '-started')]
            expected_started.add(name+'-started.json')
            require(receipt == retained and all(receipt[k] == v for k, v in identity.items())
                    and started['identity'] == identity and started['monotonic_ns'] == receipt['started_monotonic_ns'],
                    'call identity or coverage differs')
            result, observation = receipt['result'], receipt['result']['observation']
            require(result['status'] == 0 and observation['exact'] is True
                    and observation['binary_sha256'] == binary_sha and observation['workers'] == cell['workers']
                    and observation['operation'] == cell['operation'] and observation['case_id'] == cell['asset']['id'],
                    'call outcome or binary/workload identity differs')
            derived.append(dict(session=index, cell=entry['cell'], requested_workers=cell['workers'],
                                **identity, **derive(environment, result)))
        rows.extend(derived)
        summaries.append(dict(session=index, cell=entry['cell'], requested_workers=cell['workers'], calls=80,
                              dominant_logical_cpus=sorted({r['dominant_logical_cpu'] for r in derived}),
                              minimum_dominant_share=min(r['dominant_share'] for r in derived),
                              single_cpu_calls=sum(r['dominant_share'] == 1 for r in derived),
                              minimum_worker_dominant_share=min(r['worker_dominant_share'] for r in derived),
                              single_worker_cpu_calls=sum(r['worker_dominant_share'] == 1 for r in derived),
                              mean_whole_process_cpu_wall_ratio=statistics.mean(r['whole_process_cpu_wall_ratio'] for r in derived),
                              throttle_delta_available_calls=sum(r['nr_throttled_delta'] is not None for r in derived)))
    for index in range(4):
        name = f'preflight/call-{index:02}-preflight-started.json'
        started = load(name)
        require(started['identity'] == dict(round=index, arm='preflight', position=0), 'preflight identity differs')
        expected_started.add(name)
    require({p for p in manifest if p.endswith('-started.json')} == expected_started, 'manifest started-call coverage differs')
    actual_started = {str(p.relative_to(root)) for folder in ['preflight']+[f'session-{i:02}' for i in range(12)]
                      for p in (root/folder).glob('*-started.json')}
    require(actual_started == expected_started, 'retained started-call coverage differs')
    quota_sets = {json.dumps(r[k], sort_keys=True) for r in rows for k in ('quota_before', 'quota_after')}
    return dict(schema='measurement-execution-audit/v1', source_identity=dict(
                    audit_script_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                    manifest_sha256=manifest_sha256, binding_sha256=binding_sha,
                    report_sha256=manifest['report.json'], binary_sha256=binary_sha),
                coverage=dict(sessions=12, measured_calls=960, started_calls=964, verified_metadata_files=len(used)),
                interpretation='Descriptive user+nice+system logical-CPU counters; effective single-core activity at counter granularity is not causal proof, per-thread affinity or an operation trace.',
                boundaries=dict(cpu_ticks='User includes guest; nice includes guest_nice. Idle, iowait, IRQ, softirq and steal excluded.',
                                process_ratio='WHOLE PROCESS CPU / whole process wall, not codec-operation utilisation.',
                                placement='CPU sets are declarations from the bound study; this audit does not independently establish per-thread affinity or partition enforcement.',
                                environment='Before/after span includes external hashing and identity checks outside the process and operation clocks.',
                                unavailable='Null quota or throttle values mean unavailable; they do not establish unlimited quota or zero throttling.'),
                reserved_logical_cpus=CPUS, worker_logical_cpus=list(range(8)),
                initial_quota_observations=dict(binding=quotas(binding.get('environment', {})),
                                                launch=quotas(launch.get('environment', {}))),
                effective_quota_observations=[json.loads(q) for q in sorted(quota_sets)],
                sessions=summaries, calls=rows)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, required=True)
    parser.add_argument('--manifest-sha256', required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args(argv)
    if args.output.exists():
        raise FileExistsError(args.output)
    result = audit(args.root, args.manifest_sha256)
    with args.output.open('x') as output:
        json.dump(result, output, indent=2, allow_nan=False)
        output.write('\n')


if __name__ == '__main__':
    main()
