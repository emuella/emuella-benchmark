#!/usr/bin/env python3
"""Separately authorised v2 finite acquisition; never reopen the closed v1 attempt."""
import argparse
import copy
import fcntl
import json
import os
from pathlib import Path
import resource
import signal
import subprocess
import sys
import time
import tomllib

sys.path.insert(0, str(Path(__file__).resolve().parent))
import finite_confirmation_analysis as finite
import importlib.util
SPEC = importlib.util.spec_from_file_location('finite_stability', Path(__file__).with_name('measurement-stability.py'))
stability = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(stability)
refresh = stability.refresh
panels = refresh.module('finite_panels', 'classic-forward53-panels.py')
launcher = refresh.module('finite_launcher', 'measurement_launcher.py')
SCHEMA = 'classic-forward53-finite-confirmation/v2'
PREPARATION = 'classic-forward53-finite-confirmation-preparation/v2'
RESERVATION = 'measurement-balanced-reusable-qualification/v1'
INSTALL = Path('/usr/local/libexec/emuella-measurement')
LEASES = Path('/var/lib/emuella-measurement/leases')
PACKAGE = '1d66974f1a02e70f8aaba15721e6b26e9e8c3420d897adbb187e90bfa0285392'
PREREQUISITES = ('source_correctness', 'independent_decode', 'output_failure', 'parallel_route')
sha, write, absolute = refresh.sha, refresh.write, panels.absolute


def derive(v1, digest, register, design, authority):
    """V1's complete owner rows and call graph survive byte-for-byte as values."""
    value = finite.load_manifest(v1, digest, register, design)
    if not isinstance(authority, str) or not authority.strip():
        raise ValueError('separate v2 authority locator required')
    result = copy.deepcopy(value)
    result.update(schema=SCHEMA, predecessor_sha256=digest, authority=authority,
                  reservation_schema=RESERVATION, condition='balanced-reusable')
    return result


def manifest(config):
    paths = config['contract']
    value = derive(absolute(paths['v1']), paths['v1_sha256'], absolute(paths['register']),
                   absolute(paths['design']), config['authority'])
    if sha(absolute(paths['manifest'])) != paths['manifest_sha256']:
        raise ValueError('v2 manifest digest differs')
    if json.loads(Path(paths['manifest']).read_text()) != value:
        raise ValueError('v2 differs from the frozen v1 contract derivation')
    return value


def build_bindings(config):
    if set(config['arms']) != {'baseline', 'candidate'}:
        raise ValueError('exactly two frozen source arms required')
    builds = {}
    benchmark = refresh.classic.clean_source(absolute(config['benchmark_source']))
    for arm, revision in (('baseline', finite.BASELINE), ('candidate', finite.CANDIDATE)):
        source = refresh.classic.clean_source(absolute(config['codec_sources'][arm]))
        if source['source_revision'] != revision or set(config['arms'][arm]) != {'ordinary', 'resource'}:
            raise ValueError('frozen source or separate build modes differ')
        builds[arm] = {}
        for mode in ('ordinary', 'resource'):
            path = absolute(config['arms'][arm][mode])
            build = refresh.bind(path)
            if build['codec'] != source or build['benchmark'] != benchmark:
                raise ValueError('fresh build source differs')
            if (build.get('sampling') or build.get('execution_diagnostics') or build.get('parallel_diagnostics')
                    or build.get('forward53_diagnostics') or build.get('encoder_backend') != 'default'
                    or build.get('scheduling_window') != 'default'
                    or build.get('allocation_diagnostics') != (mode == 'resource')):
                raise ValueError('ordinary/allocation treatment or selectors differ')
            command = build['command']
            features = 'classic-allocation-diagnostics' if mode == 'resource' else 'classic-compare'
            if command[command.index('--profile')+1] != 'perf' or command[command.index('--features')+1] != features:
                raise ValueError('fixed perf feature selection required')
            for target in ('emuella_j2k_core', 'emuella_j2k_codestream'):
                artefacts = [a for a in build['artefacts'] if a['target']['name'] == target]
                if not artefacts or any('parallel' not in a['features'] or 'simd' in a['features']
                                        or a['profile']['opt_level'] != '3' for a in artefacts):
                    raise ValueError('parallel/perf/no-SIMD artefacts required')
            profile = tomllib.loads((path.parent/'source/workers/Cargo.toml').read_text())['profile']['perf']
            if profile.get('lto') != 'thin' or profile.get('codegen-units') != 1 or build['environment'] or build['cargo_configs']:
                raise ValueError('unmodified ThinLTO/one-codegen-unit build configuration required')
            commands = (path.parent/'cargo.stderr').read_text()
            worker_commands = [line for line in commands.splitlines() if 'Running ' in line and '--crate-name classic_compare_worker ' in line]
            if len(worker_commands) != 1 or 'lto=thin' not in worker_commands[0] or 'codegen-units=1' not in worker_commands[0]:
                raise ValueError('effective worker compiler flags differ')
            for name, digest in build['logs'].items():
                if sha(path.parent/name) != digest:
                    raise ValueError('fresh build log differs')
            if not path.is_relative_to(absolute(config['build_root'])) or not absolute(build['binary']).is_relative_to(path.parent):
                raise ValueError('fresh builds must remain in registered build scratch')
            builds[arm][mode] = dict(path=str(path), sha256=sha(path), build=build)
    baseline = builds['baseline']['ordinary']['build']
    for modes in builds.values():
        for entry in modes.values():
            for field in ('rustc', 'openjpeg', 'libraries', 'environment', 'cargo_configs', 'lock_sha256'):
                if entry['build'][field] != baseline[field]:
                    raise ValueError('build dependency/configuration differs: '+field)
            if refresh.worker_sources(entry['build']['benchmark']) != refresh.worker_sources(baseline['benchmark']):
                raise ValueError('worker source differs')
    if refresh.worker_sources(refresh.classic.clean_source(refresh.ROOT)) != refresh.worker_sources(benchmark):
        raise ValueError('live owner worker source differs from fresh builds')
    return builds


def prepare_requests(config, contract):
    if set(config['stores']) != {'rareplanes', 'spacenet'}:
        raise ValueError('both approved source stores required')
    stores, selected = {}, {}
    for name, info in config['stores'].items():
        prepared, streams, output = (absolute(info[k]) for k in ('prepared', 'streams', 'output'))
        store = prepared.parent
        if streams.parent != store or output.parent != store or len({prepared, streams, output}) != 3:
            raise ValueError('metadata and streams must stay in the approved input store')
        notice = store/panels.NOTICES[name][0]
        if sha(notice) != panels.NOTICES[name][1]:
            raise ValueError('reviewed source notice differs')
        assets = panels.kernel.assets(prepared, 'spacenet' if name == 'spacenet' else 'primary')
        stores[name] = dict(prepared_sha256=sha(prepared/'prepared.json'), notice_sha256=sha(notice))
        for asset in assets:
            if not absolute(str((prepared/asset['path']).resolve())).is_relative_to(store):
                raise ValueError('input escaped its approved store')
            selected[asset['id']] = (name, asset)
    endpoints = {e['id']: e for e in contract['endpoints']}
    requests, stream_hashes = {}, {}
    allocations = {(r['case_id'], r['style']): r for r in config['allocation_identities']}
    expected_allocations = {(r['case_id'], r['style']) for r in contract['schedule']['allocation']}
    if len(config['allocation_identities']) != 14 or set(allocations) != expected_allocations:
        raise ValueError('all fourteen independently bound allocation streams required')
    for planned in ordered(contract):
        endpoint = endpoints[planned['endpoint_id']]
        case = planned.get('case_id', endpoint['case_id'])
        name, asset = selected[case]
        info = config['stores'][name]
        allocation = planned['stage'] == 'allocation'
        style, workers = (planned.get(k, endpoint[k]) for k in ('style', 'workers'))
        origin, operation = ('emuella', 'encode') if allocation else (endpoint['origin'], endpoint['operation'])
        request = refresh.make_request(asset, Path(info['prepared']), Path(info['streams']), origin,
                                       'emuella', style, workers, 'prepare', planned.get('round', 0))
        stream = Path(request['stream_path'])
        if name == 'spacenet':
            stream = Path(info['streams'])/'streams'/f'{case}-style{style}.j2k'
        if not stream.resolve().is_relative_to(Path(info['prepared']).parent):
            raise ValueError('stream escaped its approved store')
        if str(stream) not in stream_hashes:
            stream_hashes[str(stream)] = sha(stream)
        request.update(operation=operation, stream_path=str(stream), stream_sha256=stream_hashes[str(stream)])
        if not allocation and any(request[k] != endpoint[k] for k in ('raw_sha256', 'stream_sha256')):
            raise ValueError('exact endpoint identity differs')
        # Allocation cells inherit the matching encode stream, including workers 2/4.
        references = [e for e in contract['endpoints'] if e['case_id'] == case and e['style'] == style
                      and e['operation'] == 'encode']
        if allocation:
            identity = allocations[(case, style)]
            if any(request[k] != identity[k] for k in ('raw_sha256', 'stream_sha256')):
                raise ValueError('allocation identity differs from independently bound stream')
            if references and any(request[k] != references[0][k] for k in ('raw_sha256', 'stream_sha256')):
                raise ValueError('allocation identity differs from registered encode endpoint')
        requests[planned['call_id']] = dict(store=name, request=request)
    # Hash each raw/stream once during preparation; the worker also checks each call.
    for path, digest in {(r['request'][kind+'_path'], r['request'][kind+'_sha256'])
                          for r in requests.values() for kind in ('raw', 'stream')}:
        if sha(path) != digest:
            raise ValueError('prepared raw/stream digest differs')
    return stores, requests


def ordered(contract):
    return sorted((r for stage in ('allocation', 'preflight', 'ordinary')
                   for r in contract['schedule'][stage]), key=lambda r: r['index'])


def installed_binding():
    manifest_path = launcher.trusted(INSTALL/'manifest.json')
    if sha(manifest_path) != PACKAGE:
        raise ValueError('installed historical package differs')
    files = json.loads(manifest_path.read_text())['files']
    for name, digest in files.items():
        if sha(launcher.trusted(INSTALL/name)) != digest:
            raise ValueError('installed historical source differs')
    return dict(package_sha256=PACKAGE, files=files,
                policy_sha256=sha(launcher.trusted(INSTALL/'policy.json')))


def file_identity(path):
    info = Path(path).stat()
    return [info.st_dev, info.st_ino, info.st_size, info.st_mtime_ns, info.st_ctime_ns]


def evidence_roots(config):
    scratch = absolute(config['build_root'])
    marker = scratch/'.emuella-campaign-scratch.json'
    if (scratch.name != 'classic-forward53-finite-confirmation-v2' or marker.is_symlink()
            or json.loads(marker.read_text()) != dict(kind='emuella-campaign-scratch', schema_version=1,
                                                     slug='classic-forward53-finite-confirmation-v2')):
        raise ValueError('registered finite v2 build scratch required')
    roots = [absolute(p) for p in config['evidence_roots']]
    outputs = {absolute(s['output']) for s in config['stores'].values()}
    stores = {absolute(s['prepared']).parent for s in config['stores'].values()}
    excluded = [absolute(s[k]) for s in config['stores'].values() for k in ('prepared', 'streams')]
    if not outputs <= set(roots) or len(roots) != len(set(roots)):
        raise ValueError('evidence budget must include every output root exactly once')
    if any(r.parent not in stores or any(r == x or r.is_relative_to(x) or x.is_relative_to(r) for x in excluded) for r in roots):
        raise ValueError('budget roots must be separate approved-store metadata directories')
    return roots


def host_policy():
    result = dict(boost=stability.p.read_optional('/sys/devices/system/cpu/cpufreq/boost'), cpu={})
    for cpu in list(range(8))+list(range(16, 24)):
        root = Path(f'/sys/devices/system/cpu/cpu{cpu}')
        result['cpu'][str(cpu)] = {key: stability.p.read_optional(root/key) for key in stability.STABLE_CPU}
    return result


def prepare(config_path, output):
    config = json.loads(config_path.read_text())
    contract = manifest(config)
    evidence_roots(config)
    builds = build_bindings(config)
    stores, requests = prepare_requests(config, contract)
    if set(config['estimators']) != {'40', '160'} or set(config['prerequisites']) != set(PREREQUISITES):
        raise ValueError('both fixed comparators and complete reviewed prerequisites required')
    prerequisites = {}
    for key, evidence in config['prerequisites'].items():
        if sha(absolute(evidence['path'])) != evidence['sha256']:
            raise ValueError('reviewed prerequisite evidence differs: '+key)
        prerequisites[key] = evidence
    estimators = {n: stability.estimator_identity(absolute(path), int(n)) for n, path in config['estimators'].items()}
    output = absolute(str(output))
    if output != absolute(config['stores']['rareplanes']['output'])/'preparation.json':
        raise ValueError('preparation must stay in the approved observation root')
    for info in config['stores'].values():
        if Path(info['output']).exists():
            raise ValueError('fresh output roots required; no replacement attempt')
    binding = dict(schema=PREPARATION, config=config, manifest=contract, builds=builds, stores=stores,
                   requests=requests, estimators=estimators, prerequisites=prerequisites,
                   runner=refresh.classic.clean_source(refresh.ROOT), installation=installed_binding(),
                   warmups=0, samples_per_process=1, boundary=refresh.BOUNDARY, host_policy=host_policy())
    # Cheap per-call change detection complements start/end hashes and worker hashes.
    files = set()
    for arm in builds.values():
        for entry in arm.values():
            files.update([entry['path'], entry['build']['binary'], *entry['build']['libraries']])
            files.update(str(Path(entry['path']).parent/name) for name in entry['build']['logs'])
            files.add(str(Path(entry['path']).parent/'source/workers/Cargo.toml'))
    for entry in requests.values():
        files.update(entry['request'][k+'_path'] for k in ('raw', 'stream'))
    for name, info in config['stores'].items():
        files.update([str(Path(info['prepared'])/'prepared.json'), str(Path(info['prepared']).parent/panels.NOTICES[name][0])])
    files.update(e['path'] for e in prerequisites.values())
    for estimator in estimators.values():
        root = Path(estimator['path']).parents[2]
        files.update([estimator['path'], *map(str, [root/'provenance.json', root/'src/owner_compare.rs', root/'src/main.rs', root/'Cargo.toml'])])
    files.update(str(p) for p in (refresh.ROOT/'scripts').glob('*.py'))
    files.update(config['contract'][k] for k in ('v1', 'register', 'design', 'manifest'))
    binding['file_identities'] = {p: file_identity(p) for p in sorted(files)}
    if stability.p.bytes_used(Path(config['build_root'])) > finite.limits()['build_bytes']:
        raise ValueError('registered build cap exceeded')
    for name, info in config['stores'].items():
        root = Path(info['output']); root.mkdir()
        notice = Path(info['prepared']).parent/panels.NOTICES[name][0]
        (root/'LICENSE.txt').write_bytes(notice.read_bytes())
        (root/'NOTICE.txt').write_text(panels.ATTRIBUTIONS[name]+' CC BY-SA 4.0. Local finite v2 observations; protected payloads remain in the approved store.\n')
    write(output, binding)
    return binding


def read_preparation(path, digest):
    if sha(path) != digest:
        raise ValueError('externally pinned preparation digest differs')
    value = json.loads(path.read_text())
    if value['schema'] != PREPARATION or value['manifest'] != manifest(value['config']):
        raise ValueError('prepared schema/contract differs')
    return value


def verify_identities(binding, *, full=False):
    if any(os.environ.get(key) for key in ('EMUELLA_TIER1_ENCODER', 'EMUELLA_CLASSIC_WINDOW', 'LD_PRELOAD', 'LD_LIBRARY_PATH')):
        raise ValueError('runtime overrides must be unset')
    if host_policy() != binding['host_policy']:
        raise ValueError('frequency/boost/topology policy changed after preparation')
    for arm, source in binding['config']['codec_sources'].items():
        if refresh.classic.clean_source(Path(source)) != binding['builds'][arm]['ordinary']['build']['codec']:
            raise ValueError('frozen codec source changed')
    for path, identity in binding['file_identities'].items():
        if file_identity(path) != identity:
            raise ValueError('immutable file changed: '+path)
    if refresh.classic.clean_source(refresh.ROOT) != binding['runner']:
        raise ValueError('live runner source changed')
    if full:
        if build_bindings(binding['config']) != binding['builds'] or installed_binding() != binding['installation']:
            raise ValueError('fresh build/installed binding changed')
        for n, estimator in binding['estimators'].items():
            if stability.estimator_identity(estimator['path'], int(n)) != estimator:
                raise ValueError('comparator changed')
        for path, digest in {(r['request'][k+'_path'], r['request'][k+'_sha256'])
                              for r in binding['requests'].values() for k in ('raw', 'stream')}:
            if sha(path) != digest:
                raise ValueError('raw/stream identity changed')


def admit(receipt, *, sysroot=Path('/sys'), now=None):
    if (receipt.get('schema') != RESERVATION or receipt.get('condition') != 'balanced-reusable'
            or receipt.get('partition_mode') != 'root'
            or receipt.get('worker_cpus') != list(range(8))
            or receipt.get('reserved_cpus') != list(range(8))+list(range(16, 24))
            or receipt.get('controller_cpus') != list(range(8, 16))+list(range(24, 32))):
        raise ValueError('explicit balanced-reusable physical-core allocation required')
    values = stability.reservation(receipt, sysroot=sysroot, now=now, expected_partition='root',
        expected_schema=RESERVATION, expected_condition='balanced-reusable')
    if values['cpu.max'].split()[0] != 'max' or any(
            row['cpu.max'] is not None and row['cpu.max'].split()[0] != 'max' for row in values['ancestor_limits']):
        raise ValueError('task and ancestor CPU quotas must be unlimited')
    owner = Path(receipt['cgroup']).parent
    for child in (sysroot/'fs/cgroup').iterdir():
        if child.is_dir() and child != owner:
            if set(stability.cpulist((child/'cpuset.cpus.effective').read_text())) & set(receipt['reserved_cpus']):
                raise ValueError('ordinary workload exclusion differs')
    return values


def authority(binding, path):
    path = absolute(str(path))
    lease = path.parent.parent
    if path.name != 'authority.json' or path.parent.name != 'public' or lease.parent != LEASES:
        raise ValueError('fresh installed lease authority path required')
    receipt = json.loads(launcher.trusted(path).read_text())
    if receipt['authority'] != binding['config']['authority']:
        raise ValueError('lease authority differs from separately reviewed v2 authority')
    current = json.loads(launcher.trusted(LEASES.parent/'current.json').read_text())
    if (current['lease_id'] != lease.name or current['installation']['package_sha256'] != PACKAGE
            or current['installation']['policy_sha256'] != binding['installation']['policy_sha256']):
        raise ValueError('active lease/installed binding differs')
    if sha(launcher.trusted(lease/'helper.py')) != binding['installation']['files']['measurement_reservation.py']:
        raise ValueError('lease recovery source differs')
    admit(receipt)
    return receipt


def consumption(binding, start, started):
    return dict(started_calls=started, wall_seconds=(time.monotonic_ns()-start)/1e9,
                evidence_bytes=sum(stability.p.bytes_used(p) for p in evidence_roots(binding['config'])),
                build_bytes=stability.p.bytes_used(Path(binding['config']['build_root'])))


def budget(binding, start, started, *, before_start=False):
    value = consumption(binding, start, started)
    issues = finite.budget_issues(value, before_start=before_start)
    if issues:
        raise ValueError('; '.join(issues))
    return value


def place(receipt):
    enter = stability.placement(receipt)
    def child():
        # Bounded worker logs leave the remaining 1 MiB headroom for receipts.
        resource.setrlimit(resource.RLIMIT_FSIZE, (128*1024, 128*1024))
        enter()
    return child


def resource_gate(row, request, previous):
    if row['planned']['stage'] != 'allocation':
        return
    result = panels.resources.resource_observation(row['result']['observation'], request)
    row['resources'] = result
    if not result['eligible']:
        raise ValueError('allocation peak/output exceeds unchanged query or absolute cap')
    if row['planned']['arm'] == 'candidate':
        if not previous or previous['planned'] != dict(row['planned'], arm='baseline', index=row['planned']['index']-1,
                                                       call_id=f"allocation-{int(row['planned']['call_id'].split('-')[1])-1:04}"):
            raise ValueError('missing adjacent baseline allocation')
        for field in ('working_bytes', 'output_capacity_limit'):
            if row['result']['observation'][field] != previous['result']['observation'][field]:
                raise ValueError('candidate resource query changed: '+field)


def observe(binding, planned, receipt, reference_environment, start, rows, preparation_path, preparation_sha, authority_path, authority_sha):
    budget(binding, start, len(rows), before_start=True)
    item = binding['requests'][planned['call_id']]
    root = Path(binding['config']['stores'][item['store']]['output'])
    path = root/(planned['call_id']+'-receipt.json')
    # Exclusive started receipt is the consumed invocation slot even on launch failure.
    write(root/(planned['call_id']+'-started.json'), dict(planned=planned, monotonic_ns=time.monotonic_ns()))
    row = dict(planned=planned, result=dict(status='started_without_result'), gates_passed=False)
    interrupted = None
    try:
        if sha(preparation_path) != preparation_sha or sha(authority_path) != authority_sha:
            raise ValueError('preparation/authority bytes changed')
        verify_identities(binding)
        before = stability.environment(receipt, reservation_check=admit)
        issues = stability.environment_issues(reference_environment, before, receipt)
        if issues:
            raise ValueError('; '.join(issues))
        mode = 'resource' if planned['stage'] == 'allocation' else 'ordinary'
        build = binding['builds'][planned['arm']][mode]['build']
        row['result'] = refresh.run_process(build['binary'], item['request'], root/planned['call_id'],
            list(range(item['request']['workers'])), allocation_diagnostics=mode == 'resource', placement=place(receipt))
        if planned['stage'] == 'preflight' and row['result'].get('process_wall_ns', 0) > 0 and 'process_cpu_seconds' in row['result']:
            row['preflight_route_observation'] = dict(
                process_cpu_wall_ratio=row['result']['process_cpu_seconds']/(row['result']['process_wall_ns']/1e9),
                interpretation='Descriptive whole-process route evidence; operation clock excluded from inference; no new A/A or timing gate')
        if row['result']['status'] != 0:
            raise ValueError('failed worker receipt retained; no replacement')
        resource_gate(row, item['request'], rows[-1] if rows else None)
        verify_identities(binding)
        after = stability.environment(receipt, reservation_check=admit)
        issues = stability.environment_issues(reference_environment, after, receipt)
        row['environment'] = dict(before=before, after=after, issues=issues)
        if issues:
            raise ValueError('; '.join(issues))
        budget(binding, start, len(rows)+1)
        row['gates_passed'] = True
    except BaseException as error:
        row['failure'] = str(error)
        if row['result']['status'] in (0, 'started_without_result'):
            row['result'].update(status='failed_attempt', reason=str(error))
        if not isinstance(error, Exception):
            interrupted = error
    finally:
        write(path, row)
        rows.append(row)
    if interrupted:
        raise interrupted
    return row


def endpoint_budget(binding, endpoint_id, start, rows, *, before_start=False):
    elapsed = (time.monotonic_ns()-start)/1e9
    size = 0
    for row in rows:
        planned = row['planned']
        if planned['endpoint_id'] == endpoint_id and planned['stage'] == 'ordinary':
            item = binding['requests'][planned['call_id']]
            root = Path(binding['config']['stores'][item['store']]['output'])
            size += sum(stability.p.bytes_used(p) if p.is_dir() else p.stat().st_size for p in root.glob(planned['call_id']+'*'))
    if elapsed+(150 if before_start else 0) > 1800 or size+(1024**2 if before_start else 0) > 64*1024**2:
        raise ValueError('inherited ordinary endpoint wall/evidence cap exhausted')


def controller_admission(receipt):
    actual_cgroup = Path('/proc/self/cgroup').read_text().strip()
    expected_controller = str(Path(receipt['cgroup']).parent/'controller').removeprefix('/sys/fs/cgroup')
    if actual_cgroup != '0::'+expected_controller:
        raise ValueError('acquisition must run inside the installed ordinary controller')


def acquire(binding, preparation_path, digest, authority_path):
    config = binding['config']; root = Path(config['stores']['rareplanes']['output'])
    receipt = authority(binding, authority_path)
    authority_sha = sha(authority_path)
    verify_identities(binding, full=True)
    if receipt['valid_until_epoch']-time.time() < finite.limits()['wall_seconds']:
        raise ValueError('lease must cover the entire observation window')
    transport = json.loads((root/'execution-started.json').read_text())
    if transport['preparation_sha256'] != digest or transport['authority_sha256'] != authority_sha:
        raise ValueError('outside restoration owner did not bind this acquisition')
    controller_admission(receipt)
    rows, decisions, issues = [], [], []
    endpoint_starts = {}
    disposition = finite.INCOMPLETE
    start = None
    with stability.controller_placement(receipt, root):
        environment = stability.environment(receipt, reservation_check=admit)
        if stability.environment_issues(environment, environment, receipt):
            raise ValueError('controller does not match the frozen placement')
        try:
            # Clock starts immediately before the first preflight; controller and allocation work count.
            start = time.monotonic_ns()
            write(root/'launch.json', dict(start_ns=start, preparation_sha256=digest, authority_sha256=authority_sha,
                                          condition=receipt, environment=environment))
            for planned in ordered(binding['manifest']):
                if planned['stage'] == 'ordinary':
                    endpoint_starts.setdefault(planned['endpoint_id'], time.monotonic_ns())
                    endpoint_budget(binding, planned['endpoint_id'], endpoint_starts[planned['endpoint_id']], rows, before_start=True)
                row = observe(binding, planned, receipt, environment, start, rows, preparation_path, digest,
                              authority_path, authority_sha)
                print(planned['call_id'], planned['endpoint_id'], row['result']['status'], flush=True)
                if row['result']['status'] != 0 or not row['gates_passed']:
                    raise ValueError('failed call or mandatory gate; finite attempt stopped')
                if planned['stage'] != 'ordinary':
                    continue
                endpoint_budget(binding, planned['endpoint_id'], endpoint_starts[planned['endpoint_id']], rows)
                index = int(planned['endpoint_id'].split('-')[1]); count = binding['manifest']['pairs_per_endpoint'][index]
                if planned['round'] != count-1 or planned['position'] != 1:
                    continue
                ordinary = [dict(round=r['planned']['round'], position=r['planned']['position'],
                                 arm='A' if r['planned']['arm'] == 'baseline' else 'B', result=r['result'])
                            for r in rows if r['planned']['endpoint_id'] == planned['endpoint_id'] and r['planned']['stage'] == 'ordinary']
                decision = finite.analyse_endpoint(index, ordinary, binding['estimators'][str(count)]['path'])
                write(root/(planned['endpoint_id']+'-decision.json'), decision)
                decisions.append(decision)
                if decision['disposition'] != finite.PASS:
                    disposition = decision['disposition']; break
            else:
                disposition = finite.PASS
            verify_identities(binding, full=True)
            budget(binding, start, len(rows))
        except BaseException as error:
            issues.append(str(error)); disposition = finite.INCOMPLETE
            if not isinstance(error, Exception):
                raise
        finally:
            if start is not None:
                write(root/'completion.json', dict(schema=SCHEMA, disposition=disposition, issues=issues,
                    decisions=decisions, started_calls=len(rows), consumption=consumption(binding, start, len(rows)),
                    preparation_sha256=digest, missing_call_ids=binding['manifest']['schedule']['call_order'][len(rows):],
                    promotion_authorised=False, independent_restoration='required after controller exit'))
    return disposition


def validate_restoration(binding, lease):
    current = json.loads(launcher.trusted(LEASES.parent/'current.json').read_text())
    if current['lease_id'] != lease.name:
        raise ValueError('another lease replaced the attempt before restoration verification')
    journal_path = launcher.trusted(lease/'journal.json')
    journal = json.loads(journal_path.read_text())
    restoration = json.loads(launcher.trusted(lease/'public/restoration.json').read_text())
    verified = json.loads(launcher.trusted(lease/'public/launcher-verification.json').read_text())
    if (journal.get('schema') != 'measurement-balanced-reusable-reservation/v1'
            or journal.get('id') != lease.name or journal.get('authority') != binding['config']['authority']
            or journal.get('installation', {}).get('package_sha256') != PACKAGE
            or not journal.get('cleanup_executed')
            or restoration.get('condition') != 'balanced-reusable' or restoration.get('partition_mode') != 'root'
            or restoration.get('unit') != journal.get('unit')
            or restoration.get('issues') != [] or verified.get('restored') is not True
            or verified.get('lease_id') != lease.name or verified.get('boot') != journal.get('boot')
            or verified.get('journal_sha256') != sha(journal_path)
            or verified.get('report', {}).get('restored') is not True or verified['report'].get('issues') != []):
        raise ValueError('independent installed restoration not proved for this exact lease')
    return dict(restoration=restoration, verification=verified, journal_sha256=sha(journal_path))


def execute(preparation_path, digest, authority_path):
    """Outside controller: one command transport, then unconditional installed cleanup."""
    binding = read_preparation(preparation_path, digest)
    root = Path(binding['config']['stores']['rareplanes']['output'])
    receipt = authority(binding, authority_path)
    lease = authority_path.parent.parent
    write(root/'execution-started.json', dict(preparation_sha256=digest, authority_sha256=sha(authority_path),
                                             lease_id=lease.name, controller_transport='single use'))
    error, status, terminal = None, None, None
    old_handlers = {}
    def interrupted(signum, frame):
        raise KeyboardInterrupt('interrupted by signal '+str(signum))
    try:
        for signum in (signal.SIGINT, signal.SIGTERM):
            old_handlers[signum] = signal.signal(signum, interrupted)
        command = ['/usr/bin/python3', '-I', str(lease/'helper.py'), '--condition', 'balanced-reusable', 'run', '--',
                   '/usr/bin/python3', '-I', str(Path(__file__).resolve()), 'run', '--preparation', str(preparation_path),
                   '--sha256', digest, '--authority-receipt', str(authority_path)]
        status = subprocess.run(command, check=False).returncode
    except BaseException as failure:
        error = str(failure)
    finally:
        # Do not allow a second interrupt to skip safety restoration. No corpus calls here.
        for signum in old_handlers:
            signal.signal(signum, signal.SIG_IGN)
        try:
            if installed_binding() != binding['installation']:
                raise ValueError('installed policy changed before independent restoration')
            restoration_calls = []
            for action in ('stop', 'verify'):
                try:
                    response = subprocess.run(['/usr/bin/sudo', '-n', str(INSTALL/'measurement_launcher.py'), action],
                                              capture_output=True, text=True, timeout=200)
                    restoration_calls.append(dict(action=action, status=response.returncode, stdout=response.stdout, stderr=response.stderr))
                except (OSError, subprocess.SubprocessError) as failure:
                    restoration_calls.append(dict(action=action, status='failed', error=str(failure)))
            write(root/'installed-restoration-commands.json', restoration_calls)
            terminal = validate_restoration(binding, lease)
            write(root/'independent-restoration.json', terminal)
        except BaseException as failure:
            error = (error+'; ' if error else '')+'restoration unresolved: '+str(failure)
        finally:
            for signum, handler in old_handlers.items():
                signal.signal(signum, handler)
        write(root/'execution-complete.json', dict(schema=SCHEMA, status=status, error=error,
            lease_id=lease.name, restoration_verified=terminal is not None,
            production_decision='requires complete retained evidence and independent engineering review'))
    return 1 if error or status else 0


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest='command', required=True)
    derive_command = commands.add_parser('derive')
    for key in ('v1', 'register', 'design', 'output'):
        derive_command.add_argument('--'+key, type=Path, required=True)
    derive_command.add_argument('--sha256', required=True)
    derive_command.add_argument('--authority', required=True)
    command = commands.add_parser('prepare')
    for key in ('config', 'output'):
        command.add_argument('--'+key, type=Path, required=True)
    for name in ('execute', 'run'):
        command = commands.add_parser(name)
        for key in ('preparation', 'authority-receipt'):
            command.add_argument('--'+key, type=Path, required=True)
        command.add_argument('--sha256', required=True)
    args = parser.parse_args()
    if args.command == 'derive':
        write(args.output, derive(args.v1, args.sha256, args.register, args.design, args.authority))
    elif args.command == 'prepare':
        prepare(args.config, args.output)
    elif args.command == 'execute':
        return execute(args.preparation, args.sha256, args.authority_receipt)
    else:
        binding = read_preparation(args.preparation, args.sha256)
        root = Path(binding['config']['stores']['rareplanes']['output'])
        with (root/'acquisition.lock').open('a') as lock:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            write(root/'acquisition-started.json', dict(preparation_sha256=args.sha256))
            return 0 if acquire(binding, args.preparation, args.sha256, args.authority_receipt) == finite.PASS else 1
    return 0


if __name__ == '__main__':
    sys.exit(main())
