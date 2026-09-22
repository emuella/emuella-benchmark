#!/usr/bin/env python3
"""Opt-in fixed identical-binary A/A acquisition; no estimator or worker changes."""
import argparse
import fcntl
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import time

SPEC = importlib.util.spec_from_file_location('precision_refresh', Path(__file__).with_name('openjpeg-refresh.py'))
refresh = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(refresh)
sha, write = refresh.sha, refresh.write
POLICY = 'precision-feasibility-v1'
CODEC = '975a5e734773578f61abf76d5fddfbd837f3bd7d'
NOTICE = 'f627ad059128fa5246a21e25759c1d33e35c4bb6287d636c4b970f7df57e7eba'
PAIRS, SESSIONS, PREFLIGHTS = 20, 18, 6
CALL_CAP, WALL_CAP, BYTE_CAP = 732, 7200, 2 * 1024**3
CPUS = list(range(8))


def schedule():
    """Three cyclic sweeps; each cell visits early, middle and late positions."""
    return [dict(index=sweep*6+position, sweep=sweep, cell=cell,
                 starting_arm=('A' if (cell+sweep) % 2 == 0 else 'B'))
            for sweep in range(3)
            for position, cell in enumerate([(i+2*sweep) % 6 for i in range(6)])]


def calls(session):
    start = session['starting_arm']
    return [dict(round=pair, arm=arm, position=position)
            for pair in range(PAIRS)
            for position, arm in enumerate((start, 'B' if start == 'A' else 'A')[::1 if pair % 2 == 0 else -1])]


def selected_cells(assets):
    specs = [('106_', 'RGB8', 'encode', 1, 'emuella'),
             ('94_', 'RGB16', 'encode', 1, 'emuella'),
             ('94_', 'RGB8', 'decode', 0, 'openjpeg')]
    result = []
    for prefix, product, operation, style, origin in specs:
        matches = [a for a in assets if a['id'].startswith(prefix) and a['product'] == product]
        if len(matches) != 1:
            raise ValueError('fixed complete-product selection differs')
        for workers in (1, 8):
            result.append(dict(asset=matches[0], operation=operation, style=style,
                               origin=origin, workers=workers))
    return result


def read_optional(path):
    try:
        return Path(path).read_text().strip()
    except (OSError, UnicodeError):
        return None


def environment(processes=False):
    value = dict(monotonic_ns=time.monotonic_ns(), utc=time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
                 affinity=sorted(os.sched_getaffinity(0)),
                 proc={name: read_optional('/proc/'+name) for name in
                       ('stat', 'schedstat', 'loadavg', 'meminfo', 'vmstat', 'pressure/cpu', 'pressure/memory', 'pressure/io')},
                 cpu={}, thermal={})
    for cpu in CPUS:
        root = Path(f'/sys/devices/system/cpu/cpu{cpu}')
        value['cpu'][str(cpu)] = {name: read_optional(root/name) for name in
            ('online', 'topology/core_id', 'topology/thread_siblings_list',
             'cpufreq/scaling_governor', 'cpufreq/scaling_driver', 'cpufreq/scaling_min_freq',
             'cpufreq/scaling_max_freq', 'cpufreq/scaling_cur_freq', 'cpufreq/energy_performance_preference',
             'thermal_throttle/core_throttle_count', 'thermal_throttle/package_throttle_count')}
    for pattern in ('/sys/class/thermal/thermal_zone*/temp', '/sys/class/hwmon/hwmon*/temp*_input'):
        import glob
        for name in glob.glob(pattern):
            value['thermal'][name] = read_optional(name)
    if processes:
        value['processes'] = subprocess.check_output(['ps', '-eo', 'pid,ppid,psr,pcpu,comm', '--sort=-pcpu'], text=True)
    return value


def environment_issues(before, after):
    issues = []
    if before['affinity'] != after['affinity']:
        issues.append('controller affinity changed')
    stable = ('online', 'topology/core_id', 'topology/thread_siblings_list',
              'cpufreq/scaling_governor', 'cpufreq/scaling_driver',
              'cpufreq/scaling_min_freq', 'cpufreq/scaling_max_freq', 'cpufreq/energy_performance_preference')
    for cpu in before['cpu']:
        a, b = before['cpu'][cpu], after['cpu'][cpu]
        for key in stable:
            if a[key] != b[key]:
                issues.append(f'CPU {cpu} {key} changed')
        for key in ('thermal_throttle/core_throttle_count', 'thermal_throttle/package_throttle_count'):
            if a[key] is not None and b[key] is not None and int(b[key]) > int(a[key]):
                issues.append(f'CPU {cpu} {key} increased')
    # Explicit process identities, not slow samples, determine competing-build contamination.
    for line in after.get('processes', '').splitlines()[1:]:
        fields = line.split()
        if fields and fields[-1] in ('rustc', 'cargo', 'cc1', 'cc1plus', 'ninja', 'classic-compare', 'classic-compare-worker', 'emuella-worker', 'openjpeg-worker', 'openjph-worker'):
            issues.append('competing build/codec process at session boundary: '+line.strip())
    return issues


def verify_build(record):
    if any(record.get(x) for x in ('sampling', 'execution_diagnostics', 'allocation_diagnostics', 'parallel_diagnostics')):
        raise ValueError('diagnostic worker is not production')
    if record.get('encoder_backend') != 'default' or record.get('scheduling_window') != 'default':
        raise ValueError('production selectors must be unset')
    if record['codec']['source_revision'] != CODEC:
        raise ValueError('prospectively frozen production codec differs')
    features = record['command'][record['command'].index('--features')+1]
    if features != 'classic-compare' or record['command'][record['command'].index('--profile')+1] != 'perf':
        raise ValueError('tuned non-SIMD production build differs')
    if not Path(record['binary']).is_absolute():
        raise ValueError('worker path must be absolute')


def verify_call(binding, cell):
    """Both labels reach this same function with the same immutable treatment."""
    if refresh.bind(Path(binding['build_path'])) != binding['build']:
        raise ValueError('build receipt changed')
    for owner in ('codec', 'benchmark'):
        root = Path(binding[owner+'_source'])
        if refresh.classic.clean_source(root) != binding['build'][owner]:
            raise ValueError(owner+' source changed since worker build')
    request = cell['request']
    for path, expected in ((request['raw_path'], request['raw_sha256']),
                           (request['stream_path'], request['stream_sha256'])):
        if sha(path) != expected:
            raise ValueError('immutable input/stream changed')
    if sha(binding['prepared_manifest']) != binding['prepared_sha256']:
        raise ValueError('prepared contract changed')


def freeze(args):
    build = refresh.bind(args.build)
    verify_build(build)
    store = args.prepared.parent.resolve()
    if args.output.parent.resolve() != store or args.streams.parent.resolve() != store:
        raise ValueError('evidence and existing streams must remain in the approved store')
    if sha(store/'source/LICENSE.txt') != NOTICE:
        raise ValueError('reviewed RarePlanes notice differs')
    assets = refresh.classic.assets(args.prepared)
    cells = selected_cells(assets)
    for cell in cells:
        cell['request'] = refresh.make_request(cell['asset'], args.prepared, args.streams,
            cell['origin'], 'emuella', cell['style'], cell['workers'], cell['operation'], 0)
    binding = dict(policy=POLICY, build_path=str(args.build.resolve()), build=build,
                   codec_source=str(args.codec_source.resolve()), benchmark_source=str(refresh.ROOT),
                   prepared_manifest=str(args.prepared/'prepared.json'), prepared_sha256=sha(args.prepared/'prepared.json'),
                   cells=cells, schedule=schedule(), cpus=CPUS, environment=environment(True),
                   boundary=refresh.BOUNDARY, pairs=PAIRS, preflights=PREFLIGHTS,
                   timed_calls=720, total_call_cap=CALL_CAP, wall_cap_seconds=WALL_CAP, evidence_cap_bytes=BYTE_CAP,
                   rights_notice_sha256=NOTICE, warmups=0, samples_per_process=1)
    for cell in cells:
        verify_call(binding, cell)
    args.output.mkdir(exist_ok=False)
    (args.output/'LICENSE.txt').write_bytes((store/'source/LICENSE.txt').read_bytes())
    (args.output/'NOTICE.txt').write_text('RarePlanes Dataset, June 2020. J. Shermeyer et al.; In-Q-Tel - CosmiQ Works and AI.Reverie. CC BY-SA 4.0. Local identical-binary observations; original inputs, immutable streams and source lineage remain in this authorised store. No imagery redistribution.\n')
    write(args.output/'binding.json', binding)
    print('Frozen binding SHA-256:', sha(args.output/'binding.json'), flush=True)


def bytes_used(root):
    return sum(p.stat().st_size for p in root.rglob('*') if p.is_file())


def budget_check(root, start_ns, count, now_ns=None):
    now_ns = time.monotonic_ns() if now_ns is None else now_ns
    if count >= CALL_CAP:
        raise ValueError('total call cap reached')
    # Reserve the worker's existing 120-second timeout plus verification/receipts.
    if (now_ns-start_ns)/1e9 >= WALL_CAP-150:
        raise ValueError('observation-window cap: insufficient time for one bounded call')
    if bytes_used(root) >= BYTE_CAP-1024**2:
        raise ValueError('new-evidence cap reached')


def started_count(root):
    return len(list(root.glob('*/call-*-started.json')))


def observe(root, binding, folder, cell, identity, start_ns):
    name = f"call-{identity['round']:02}-{identity['arm']}"
    budget_check(root, start_ns, started_count(root))
    # Intent is durable before validation or invocation; failed attempts consume budget.
    started_ns = time.monotonic_ns()
    write(folder/(name+'-started.json'), dict(identity=identity, monotonic_ns=started_ns))
    result = {}
    try:
        verify_call(binding, cell)
        request = dict(cell['request'], round=identity['round'])
        result = refresh.run_process(binding['build']['binary'], request, folder/name, CPUS[:cell['workers']])
        verify_call(binding, cell)
    except Exception as error:
        result.update(status='failed_attempt', reason=str(error))
    row = dict(identity, result=result, started_monotonic_ns=started_ns)
    write(folder/(name+'-receipt.json'), row)
    return row


def session(root, index):
    binding = json.loads((root/'binding.json').read_text())
    launch = json.loads((root/'launch.json').read_text())
    if sha(root/'binding.json') != launch['binding_sha256'] or binding['schedule'] != schedule():
        raise ValueError('frozen binding/schedule differs')
    preflight = json.loads((root/'preflight/preflight.json').read_text())
    if len(preflight['rows']) != PREFLIGHTS or any(r['result']['status'] != 0 for r in preflight['rows']):
        raise ValueError('complete exact preflight required')
    if index and not (root/f'session-{index-1:02}').is_dir():
        raise ValueError('sessions must follow frozen order')
    entry = binding['schedule'][index]
    folder = root/f'session-{index:02}'
    folder.mkdir(exist_ok=False)
    before = environment(True)
    write(folder/'started.json', dict(session=entry, environment=before, binding_sha256=sha(root/'binding.json')))
    rows, issues = [], environment_issues(binding['environment'], before)
    stop = None
    for identity in calls(entry):
        try:
            row = observe(root, binding, folder, binding['cells'][entry['cell']], identity, launch['start_ns'])
            rows.append(row)
            if identity['position'] == 1:
                sample = environment()
                issues += environment_issues(before, sample)
                write(folder/f"environment-{identity['round']:02}.json", sample)
        except Exception as error:
            stop = str(error)
            break
    after = environment(True)
    issues += environment_issues(before, after)
    if stop:
        issues.append(stop)
    result = dict(session=entry, rows=rows, issues=sorted(set(issues)), valid=not issues,
                  complete=len(rows)==40 and all(r['result']['status']==0 for r in rows),
                  environment_after=after, binding_sha256=sha(root/'binding.json'))
    write(folder/'session.json', result)
    print(f"session {index:02} cell {entry['cell']} calls {len(rows)}/40 complete={result['complete']} valid={result['valid']}", flush=True)


def study(root):
    # Exclusive whole-study lock plus exclusive launch receipt prohibit restarts/replacements.
    with (root/'study.lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        binding = json.loads((root/'binding.json').read_text())
        write(root/'launch.json', dict(start_ns=time.monotonic_ns(), binding_sha256=sha(root/'binding.json'), environment=environment(True)))
        launch = json.loads((root/'launch.json').read_text())
        pre = root/'preflight'
        pre.mkdir()
        preflight = []
        for index, cell in enumerate(binding['cells']):
            row = observe(root, binding, pre, cell, dict(round=index, arm='preflight', position=0), launch['start_ns'])
            preflight.append(row)
        write(pre/'preflight.json', dict(rows=preflight, interpretation='Setup only; operation clock values excluded from study analysis'))
        outcomes = []
        # Even failed preflights are retained; study cannot start if identities/exactness fail.
        if all(r['result']['status']==0 for r in preflight):
            for entry in schedule():
                try:
                    budget_check(root, launch['start_ns'], started_count(root))
                except ValueError as error:
                    outcomes.append(dict(index=entry['index'], status='not_started', reason=str(error)))
                    break
                code = subprocess.call([sys.executable, str(Path(__file__).resolve()), 'session', '--output', str(root), '--index', str(entry['index'])])
                outcomes.append(dict(index=entry['index'], exit_code=code))
        write(root/'completion.json', dict(outcomes=outcomes, started_calls=started_count(root),
            wall_seconds=(time.monotonic_ns()-launch['start_ns'])/1e9, new_evidence_bytes=bytes_used(root),
            expected_timed_calls=720, expected_preflights=6, binding_sha256=sha(root/'binding.json')))
        print(json.dumps(json.loads((root/'completion.json').read_text())), flush=True)


def analyse(root, estimator, report):
    analysis = refresh.module('precision_analysis', 'precision_feasibility_analysis.py')
    binding = json.loads((root/'binding.json').read_text())
    launch = json.loads((root/'launch.json').read_text())
    if sha(root/'binding.json') != launch['binding_sha256'] or binding['schedule'] != schedule():
        raise ValueError('frozen binding/schedule differs')
    if report.parent.resolve() != root.resolve():
        raise ValueError('raw analysis belongs in the approved evidence root')
    sessions = []
    for entry in schedule():
        folder = root/f"session-{entry['index']:02}"
        path = folder/'session.json'
        if path.is_file():
            measured = json.loads(path.read_text())
            if measured['session'] != entry or measured['binding_sha256'] != launch['binding_sha256']:
                raise ValueError('session binding differs')
            rows = measured['rows']
            if rows and rows[0]['arm'] != entry['starting_arm']:
                raise ValueError('starting arm differs from frozen schedule')
            # Receipts, including failed attempts, must agree with the session record.
            receipts = [json.loads(p.read_text()) for p in sorted(folder.glob('call-*-receipt.json'))]
            if sorted(receipts, key=lambda r:(r['round'],r['position'])) != rows:
                raise ValueError('session records differ from durable per-call receipts')
            result = analysis.analyse_session(rows, estimator, valid=measured['valid'])
            result['environment_issues'] = measured['issues']
            result['session_receipt_sha256'] = sha(path)
        else:
            rows = [json.loads(p.read_text()) for p in folder.glob('call-*-receipt.json')]
            rows.sort(key=lambda r:(r['round'],r['position']))
            result = analysis.analyse_session(rows, estimator, valid=False)
            result['environment_issues'] = ['missing terminal session record']
        result['session'] = entry
        result['started_attempts'] = [json.loads(p.read_text()) for p in sorted(folder.glob('call-*-started.json'))]
        sessions.append(result)
    cells = []
    for index, cell in enumerate(binding['cells']):
        selected = [s for s in sessions if s['session']['cell']==index]
        cells.append(dict(cell=index, case_id=cell['asset']['id'], workers=cell['workers'],
                          operation=cell['operation'], style=cell['style'],
                          disposition=analysis.classify_cell(selected)))
    value = dict(policy=POLICY, binding_sha256=sha(root/'binding.json'),
                 estimator_sha256=sha(estimator), comparator_sha256=sha(refresh.ROOT/'src/compare.rs'),
                 sessions=sessions, cells=cells,
                 completion=json.loads((root/'completion.json').read_text()))
    write(report, value)
    print(json.dumps(cells, indent=2))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='command', required=True)
    freeze_parser = sub.add_parser('freeze')
    for name in ('build', 'prepared', 'streams', 'codec-source', 'output'):
        freeze_parser.add_argument('--'+name, type=Path, required=True)
    analyser = sub.add_parser('analyse')
    for name in ('output', 'estimator', 'report'):
        analyser.add_argument('--'+name, type=Path, required=True)
    for name in ('study', 'session'):
        child = sub.add_parser(name)
        child.add_argument('--output', type=Path, required=True)
        if name == 'session':
            child.add_argument('--index', type=int, choices=range(18), required=True)
    args = parser.parse_args()
    if args.command == 'freeze':
        freeze(args)
    elif args.command == 'analyse':
        analyse(args.output, args.estimator, args.report)
    elif args.command == 'study':
        study(args.output)
    else:
        with (args.output/'session.lock').open('a') as lock:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            session(args.output, args.index)


if __name__ == '__main__':
    main()
