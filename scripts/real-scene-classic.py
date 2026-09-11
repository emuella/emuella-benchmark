#!/usr/bin/env python3
"""Bounded facade treatment and application-schedule experiment.

Different coding/thread/context treatments remain separately named. This is not
an ordinary compare() run and never changes that contract's comparability keys.
Inputs and generated streams must stay in an independently authorised store.
"""
import argparse
import concurrent.futures
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import signal
import resource
import re
import subprocess
import time

ROLES = {'94_104001000B823500': 'development',
         '106_10400100413CDF00': 'validation', '105_104001002F92BB00': 'regression'}
PRODUCTS = ('PAN16', 'RGB16', 'MS16', 'RGB8')
WORKING = 768 * 1024**2
OUTPUT = 64 * 1024**2
BUDGET = 8 * 1024**3
CONTROLLER = 128 * 1024**2
CONTRASTS = [('bypass_at1',(0,1),(1,1)), ('bypass_at8',(0,8),(1,8)), ('combined',(0,1),(1,8))]
MANIFEST = '6c37b54bf75af0c17c1b67c5ad7bd2d56b5d34d45de9737ddb50d0fc1fe10e7b'


def digest(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda: stream.read(1024**2), b''):
            h.update(block)
    return h.hexdigest()


def write(path, value):
    with path.open('x') as stream:
        json.dump(value, stream, indent=2)
        stream.write('\n')


def bind_build(binary, allocation, source, provenance):
    record = json.loads(provenance.read_text())
    revision = record.get('source_revision', '')
    tree = record.get('source_tree', '')
    if not all(isinstance(value,str) and re.fullmatch('[0-9a-f]{40}',value) for value in (revision,tree)):
        raise ValueError('build provenance needs full source and tree identities')
    observed_tree = subprocess.check_output(['git','-C',str(source),'rev-parse','--verify',revision+'^{tree}'],text=True).strip()
    if observed_tree != tree:
        raise ValueError('recorded codec source tree differs from Git objects')
    for path, field in [('Cargo.toml','workspace_cargo_sha256'),('Cargo.lock','lock_sha256')]:
        original = subprocess.check_output(['git','-C',str(source),'show',revision+':'+path])
        if hashlib.sha256(original).hexdigest() != record.get(field):
            raise ValueError('bound source configuration differs: '+path)
    if record.get('requested_profile') != 'perf':
        raise ValueError('the frozen treatment requires the perf build')
    for target in ('emuella_j2k_core','emuella_j2k_codestream'):
        observations = [a for a in record.get('artefacts',[]) if a['target']['name']==target]
        if not observations or any('parallel' not in a['features'] or 'simd' in a['features'] for a in observations):
            raise ValueError('observed codec feature selection differs: '+target)
    for name, path in [('lossless_bypass_batch',binary),('lossless_bypass_allocation',allocation)]:
        artefact = record['binaries'][name]
        profile = artefact['profile']
        if digest(path) != artefact['sha256']:
            raise ValueError('executable differs from bound build provenance: '+name)
        if ('parallel' not in artefact['features'] or 'simd' in artefact['features'] or
                profile['opt_level']!='3' or profile['debug_assertions'] or profile['test']):
            raise ValueError('observed executable profile or features differ: '+name)
    return dict(codec_revision=revision,codec_tree=tree,build_provenance_sha256=digest(provenance))


def clean_source(source):
    git = lambda *args: subprocess.check_output(['git','-C',str(source),*args])
    if git('status','--porcelain'):
        raise ValueError('codec build requires a clean committed checkout')
    revision = git('rev-parse','HEAD').decode().strip()
    tree = git('rev-parse','HEAD^{tree}').decode().strip()
    files = {}
    for entry in git('ls-tree','-rz','--full-tree',revision).split(b'\0'):
        if not entry:
            continue
        metadata, relative = entry.split(b'\t',1)
        mode, kind, expected = metadata.split()
        path = source / relative.decode()
        if kind != b'blob' or mode not in (b'100644',b'100755') or path.is_symlink() or not path.is_file():
            raise ValueError('codec source requires ordinary tracked files')
        data = path.read_bytes()
        observed = hashlib.sha1(b'blob '+str(len(data)).encode()+b'\0'+data).hexdigest().encode()
        if observed != expected or bool(path.stat().st_mode & 0o111) != (mode == b'100755'):
            raise ValueError('working source differs from committed Git bytes or mode: '+str(relative))
        files[relative.decode()] = hashlib.sha256(data).hexdigest()
    return dict(source_revision=revision,source_tree=tree,source_files_sha256=files)


def build_consumer(source, output):
    source = source.resolve()
    output = output.resolve()
    harness = Path(__file__).resolve().parents[1]
    if any(output == root or root in output.parents for root in (source,harness)):
        raise ValueError('consumer build output must be outside source checkouts')
    before = clean_source(source)
    output.mkdir(parents=True)
    # Reuse the owner helper's Cargo configuration/environment inventory.
    spec = importlib.util.spec_from_file_location('build_workers',Path(__file__).with_name('build-workers.py'))
    helper = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(helper)
    environment = dict(os.environ,CARGO_TARGET_DIR=str(output/'target'))
    configs = helper.cargo_config_files(source,environment)
    command = ['cargo','build','--locked','--profile','perf','-p','emuella-j2k-test-support',
               '--features','parallel','--example','lossless_bypass_batch','--example','lossless_bypass_allocation',
               '--example','classic_ht_support','--message-format=json-render-diagnostics','-vv']
    with (output/'cargo-build.jsonl').open('x') as stdout,(output/'cargo-build.stderr').open('x') as stderr:
        subprocess.run(command,cwd=source,env=environment,stdout=stdout,stderr=stderr,check=True)
    if clean_source(source) != before or helper.cargo_config_files(source,environment) != configs:
        raise ValueError('codec source or Cargo configuration changed during build')
    events = []
    for line in (output/'cargo-build.jsonl').read_text().splitlines():
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(event,dict):
            events.append(event)
    if not any(e.get('reason')=='build-finished' and e.get('success') is True for e in events):
        raise ValueError('Cargo did not report a completed build')
    artefacts = [e for e in events if e.get('reason')=='compiler-artifact']
    binaries = {}
    for name in ('lossless_bypass_batch','lossless_bypass_allocation','classic_ht_support'):
        matches = [a for a in artefacts if a['target']['name']==name and a.get('executable')]
        if len(matches)!=1:
            raise ValueError('expected one observed consumer executable: '+name)
        a = matches[0]
        binaries[name] = dict(path=a['executable'],sha256=digest(a['executable']),profile=a['profile'],features=a['features'],
                             libraries=[dict(path=str(p),sha256=digest(p)) for p in helper.libraries(Path(a['executable']))])
    record = dict(**before,command=command,cwd=str(source),requested_profile='perf',requested_features=['parallel'],
        harness_revision=subprocess.check_output(['git','-C',str(harness),'rev-parse','HEAD'],text=True).strip(),
        harness_script_sha256=digest(Path(__file__)),build_helper_sha256=digest(Path(__file__).with_name('build-workers.py')),
        compiler=subprocess.check_output(['rustc','-Vv'],cwd=source,env=environment,text=True),
        cargo=subprocess.check_output(['cargo','-Vv'],cwd=source,env=environment,text=True),
        build_environment=helper.build_environment(environment),cargo_configs=configs,
        lock_sha256=digest(source/'Cargo.lock'),workspace_cargo_sha256=digest(source/'Cargo.toml'),
        artefacts=artefacts,binaries=binaries,build_jsonl_sha256=digest(output/'cargo-build.jsonl'),
        build_stderr_sha256=digest(output/'cargo-build.stderr'),
        compiler_observation='Cargo-vv dispatched commands retained; artefact profiles can be overridden by ordered rustflags; wrapper internals are not observed')
    write(output/'build-provenance.json',record)
    bind_build(Path(binaries['lossless_bypass_batch']['path']),Path(binaries['lossless_bypass_allocation']['path']),source,output/'build-provenance.json')
    print(json.dumps(dict(source_revision=before['source_revision'],provenance_sha256=digest(output/'build-provenance.json'),binaries=binaries)),flush=True)


def assets(prepared):
    manifest = prepared / 'prepared.json'
    if digest(manifest) != MANIFEST:
        raise ValueError('prepared manifest identity differs')
    selected = [a for a in json.loads(manifest.read_text())['assets']
                if a['bundle_id'] in ROLES and
                (ROLES[a['bundle_id']] != 'regression' or a['product'] == 'RGB8')]
    if len(selected) != 9 or any(a['product'] not in PRODUCTS for a in selected):
        raise ValueError('frozen nine-product coverage differs')
    for asset in selected:
        if digest(prepared / asset['path']) != asset['sha256']:
            raise ValueError('source identity differs')
    return sorted(selected, key=lambda a: (list(ROLES).index(a['bundle_id']), PRODUCTS.index(a['product'])))


def request(asset, prepared, output, style, workers, operation, round_id=0, context='direct_global'):
    image = asset['image']
    stream = output / 'streams' / (asset['id'] + '-style' + str(style) + '.j2k')
    value = dict(case_id=asset['id'], width=image['width'], height=image['height'],
                 components=image['components'], bits=image['precision'], layout='interleaved',
                 style=style, workers=workers, operation=operation, round=round_id,
                 raw_path=str(prepared / asset['path']), raw_sha256=asset['sha256'],
                 stream_path=str(stream), boundary='facade_operation', execution_context=context,
                 max_working_bytes=WORKING, max_output_bytes=OUTPUT)
    if operation != 'prepare':
        value['stream_sha256'] = digest(stream)
    return value


def execute(binary, req, directory, cpus, address_limit=BUDGET, extra_args=None):
    directory.mkdir()
    write(directory / 'request.json', req)
    command = [str(binary), str(directory / 'request.json')] if extra_args is None else [str(binary), *extra_args]
    # prlimit constrains each process; disjoint schedule allowances sum to the
    # aggregate ceiling. taskset fixes the aggregate available CPU set.
    command = ['taskset', '-c', ','.join(map(str, cpus)), 'prlimit',
               '--as=' + str(address_limit), '--', '/usr/bin/time',
               '-f', '%U %S %M', '-o', str(directory / 'resources.txt'), *command]
    start = time.monotonic_ns()
    with (directory / 'stdout.json').open('x') as stdout, (directory / 'stderr.txt').open('x') as stderr:
        child = subprocess.Popen(command, stdout=stdout, stderr=stderr, start_new_session=True)
        try:
            status = child.wait(timeout=120)
        except subprocess.TimeoutExpired:
            os.killpg(child.pid, signal.SIGKILL)
            child.wait()
            status = 'timeout'
    result = dict(status=status, process_wall_ns=time.monotonic_ns() - start)
    if status == 0:
        try:
            observation = json.loads((directory / 'stdout.json').read_text())
            if not isinstance(observation, dict):
                raise ValueError('worker response is not an object')
            if extra_args is None and req.get('operation') in ('encode','decode'):
                samples = observation.get('samples_ns')
                if not isinstance(samples,list) or len(samples)!=1 or not isinstance(samples[0],int) or samples[0]<=0:
                    raise ValueError('worker timing cardinality differs')
                for field in ('raw_sha256','stream_sha256','style','workers','execution_context','max_working_bytes','max_output_bytes'):
                    if observation.get(field) != req[field]:
                        raise ValueError('worker applied identity differs: '+field)
                if observation.get('native_exact') is not True:
                    raise ValueError('worker did not prove exact reconstruction')
            user, system, rss = (directory / 'resources.txt').read_text().split()
            result.update(observation=observation,process_cpu_seconds=float(user)+float(system),process_peak_rss_bytes=int(rss)*1024)
        except (ValueError,TypeError,KeyError) as error:
            result.update(status='invalid_response',reason=str(error))
    write(directory / 'result.json', result)
    return result


def verify_inputs(args, selected, manifest):
    if 'build_provenance_sha256' in manifest and digest(args.output/'build-provenance.json') != manifest['build_provenance_sha256']:
        raise ValueError('retained build provenance changed')
    if digest(args.allocation) != manifest['allocation_sha256']:
        raise ValueError('bound allocation diagnostic changed during experiment')
    if digest(args.binary) != manifest['binary_sha256']:
        raise ValueError('bound executable changed during experiment')
    if digest(args.prepared / 'prepared.json') != MANIFEST:
        raise ValueError('prepared manifest changed during experiment')
    for asset in selected:
        if digest(args.prepared / asset['path']) != asset['sha256']:
            raise ValueError('raw source changed during experiment')
        for style in (0,1):
            record = json.loads((args.output/'preparation'/(asset['id']+'-'+str(style))/'result.json').read_text())
            stream = args.output/'streams'/(asset['id']+'-style'+str(style)+'.j2k')
            if record['status'] != 0 or digest(stream) != record['observation']['stream_sha256']:
                raise ValueError('prepared stream identity changed')


def reprofile_schedule(args, selected, cpus, folder):
    """Observe the selected concurrent configuration without headline clocks."""
    if args.schedule != '8x1':
        raise ValueError('selected reprofile requires explicit --schedule 8x1')
    rows = []
    for asset in selected:
        if asset['product'] not in ('PAN16','RGB8'):
            continue
        req = request(asset,args.prepared,args.output,1,1,'requirements')
        admission = execute(args.binary,req,folder/('admission-'+asset['id']),cpus)
        if admission['status'] != 0:
            raise RuntimeError('selected reprofile requirements failed; retained evidence')
        allowance = admission['observation']['requirements_working_bytes'] + asset['bytes']*3 + OUTPUT + 64*1024**2
        for operation in ('profile','decode_diagnostic'):
            row = dict(case=asset['id'],operation=operation,concurrent=8,workers=1,requests=8,
                       boundary='instrumented_selected_schedule; excluded from headline statistics',
                       per_process_allowance=allowance,aggregate_allowance=8*allowance+CONTROLLER)
            if row['aggregate_allowance'] > BUDGET:
                row.update(status='rejected',reason='conservative aggregate admission exceeds8GiB')
            elif resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024 > CONTROLLER:
                row.update(status='rejected',reason='controller high-water exceeds reserved128MiB before diagnostic dispatch')
            else:
                req = request(asset,args.prepared,args.output,1,1,operation)
                def one(index):
                    started = time.monotonic_ns()
                    result = execute(args.binary,req,folder/(asset['id']+'-'+operation+'-'+str(index)),
                                     cpus,address_limit=(BUDGET-CONTROLLER)//8)
                    return dict(invocation_started_ns=started,invocation_finished_ns=time.monotonic_ns(),result=result)
                with concurrent_module(8) as pool:
                    invocations = list(pool.map(one,range(8)))
                results = [r['result'] for r in invocations]
                controller = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024
                peak_bound = sum(r.get('process_peak_rss_bytes',0) for r in results)+controller
                row.update(status='ok' if all(r['status']==0 for r in results) and controller<=CONTROLLER and peak_bound<=BUDGET else 'failed',
                           invocations=invocations,controller_peak_rss_bytes=controller,
                           sum_process_peak_rss_plus_controller_upper_bound=peak_bound)
            rows.append(row)
            print(json.dumps(dict(reprofile_case=asset['id'],operation=operation,status=row['status'])),flush=True)
    return rows


def schedule_cohort(binary, req, folder, index, cpus, concurrent):
    """Keep the original application clock; enforce controller/total RSS gates."""
    controller_before = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024
    if controller_before > CONTROLLER:
        return dict(status='rejected',reason='controller high-water exceeds reserved128MiB before dispatch',
                    controller_peak_rss_bytes=controller_before)
    start = time.monotonic_ns()
    def one(child_index):
        return execute(binary,req,folder/(str(index)+'-'+str(child_index)),cpus,address_limit=(BUDGET-CONTROLLER)//concurrent)
    with concurrent_module(concurrent) as pool:
        results = list(pool.map(one,range(8)))
    elapsed = time.monotonic_ns()-start
    controller = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024
    child_peak = sum(sorted((r.get('process_peak_rss_bytes',0) for r in results),reverse=True)[:concurrent])
    row = dict(status='ok' if all(r['status']==0 for r in results) else 'failed',
               application_wall_ns=elapsed,results=results,sum_process_peak_rss_upper_bound=child_peak,
               controller_peak_rss_bytes=controller)
    if controller > CONTROLLER:
        row.update(status='failed',reason='controller high-water exceeds reserved128MiB after cohort')
    elif child_peak+controller > BUDGET:
        row.update(status='failed',reason='conservative total process RSS exceeds8GiB after cohort')
    return row


def estimator_build(repo, directory):
    """Use the historical exact owner module and classification-block wrapper."""
    directory.mkdir()
    (directory / 'src').mkdir()
    source = (repo / 'src/compare.rs').read_text()
    start = source.index('        let bounds = [ylow / xhigh - 1.0, yhigh / xlow - 1.0];')
    end = source.index('        result.cases.push(', start)
    classify = source[start:end].replace('let threshold = a.experiment.protocol.practical_relative_threshold;', 'let threshold = 0.05;')
    wrapper = '''
pub fn treatment(xs: &[f64], ys: &[f64]) -> serde_json::Value {
    assert_eq!(xs.len(), 20); assert_eq!(ys.len(), 20);
    assert!(xs.iter().chain(ys).all(|x| x.is_finite() && *x > 0.0));
    let (x, xlow, xhigh) = interval(xs);
    let (y, ylow, yhigh) = interval(ys);
    if xlow <= 0.0 || ylow <= 0.0 { return serde_json::json!({"verdict":"inconclusive", "baseline_mean_ns":x, "candidate_mean_ns":y}); }
''' + classify + '''
    serde_json::json!({"verdict":verdict,"baseline_mean_ns":x,"candidate_mean_ns":y,
        "relative_change":y/x-1.0,"relative_interval_99":bounds})
}
'''
    (directory / 'src/owner_compare.rs').write_text(source + wrapper)
    (directory / 'src/main.rs').write_text('''pub use emuella_benchmark::{Result, contract, metrics, runner};
mod owner_compare;
fn main() -> Result<()> {
 let v: serde_json::Value = serde_json::from_reader(std::io::stdin())?;
 let a = |s: &str| v[s].as_array().unwrap().iter().map(|x| x.as_f64().unwrap()).collect::<Vec<_>>();
 println!("{}", owner_compare::treatment(&a("baseline"), &a("candidate"))); Ok(())
}
''')
    (directory / 'Cargo.toml').write_text('[package]\nname="classic-treatment-estimator"\nversion="0.0.0"\nedition="2024"\n[dependencies]\nemuella-benchmark={path=' + json.dumps(str(repo)) + '}\nserde={version="1",features=["derive"]}\nserde_json="1"\n')
    write(directory / 'provenance.json', {'owner_revision': subprocess.check_output(['git', '-C', str(repo), 'rev-parse', 'HEAD'], text=True).strip(),
         'owner_sha256': digest(repo / 'src/compare.rs'), 'wrapper_sha256': hashlib.sha256(wrapper.encode()).hexdigest(),
         'method': 'Unchanged owner interval and classification; fixed20 independent means;5%;99% conservative per-comparison ratio interval; no outlier removal',
         'identity': 'separately named treatments, no forged Run/Case comparability'})
    subprocess.run(['cargo', 'build', '--release', '--manifest-path', str(directory / 'Cargo.toml'),
                    '--target-dir', str(directory / 'target')], check=True)


def analysis_cases(output):
    manifest = json.loads((output/'manifest.json').read_text())
    role = manifest.get('role')
    if manifest.get('prepared_sha256') != MANIFEST or role not in ROLES.values() or manifest.get('protocol',{}).get('rounds') != 20:
        raise ValueError('analysis requires the bound frozen manifest and twenty-round protocol')
    bundle = next(bundle for bundle,value in ROLES.items() if value == role)
    products = ('RGB8',) if role == 'regression' else PRODUCTS
    expected = {bundle+'-'+product for product in products}
    assets = manifest.get('assets',[])
    if (len(assets) != len(expected) or {a.get('id') for a in assets} != expected or
            any(a.get('bundle_id') != bundle or a.get('id') != bundle+'-'+a.get('product','') for a in assets)):
        raise ValueError('bound manifest does not contain the complete declared role')
    return manifest, sorted(expected)


def index_observations(rows, expected, fields):
    """Reject favourable subsets and repeated batches before any estimation."""
    if not isinstance(rows,list):
        raise ValueError('observations must be a list')
    types = tuple(type(value) for value in next(iter(expected)))
    indexed = {}
    for row in rows:
        if not isinstance(row,dict):
            raise ValueError('observation must be an object')
        key = tuple(row.get(field) for field in fields)
        if any(type(value) is not kind for value,kind in zip(key,types)) or key not in expected:
            raise ValueError('unexpected or malformed observation identity')
        if key in indexed:
            raise ValueError('duplicate observation identity')
        indexed[key] = row
    if indexed.keys() != expected:
        raise ValueError('missing expected observations')
    return indexed


def analyse(output, estimator):
    manifest, cases = analysis_cases(output)
    expected = {(case,operation,contrast,*arm,round_id) for case in cases for operation in ('encode','decode')
                for contrast,left,right in CONTRASTS for arm in (left,right) for round_id in range(20)}
    indexed = index_observations(json.loads((output/'batches.json').read_text()),expected,
                                 ('case','operation','contrast','style','workers','round'))
    comparisons = []
    for case in cases:
        for operation in ('encode', 'decode'):
            for contrast, left, right in CONTRASTS:
                sides = [[indexed[(case,operation,contrast,*side,round_id)] for round_id in range(20)] for side in (left,right)]
                record = dict(case=case,operation=operation,contrast=contrast,baseline=left,candidate=right)
                if any(r['result']['status'] != 0 for side in sides for r in side):
                    record['verdict'] = 'invalid'
                else:
                    data = {name:[r['result']['observation']['samples_ns'][0] for r in side]
                            for name,side in zip(('baseline','candidate'),sides)}
                    result = subprocess.check_output([str(estimator)], input=json.dumps(data), text=True)
                    record.update(json.loads(result))
                comparisons.append(record)
    write(output / 'comparisons.json', comparisons)
    write(output / 'analysis-identity.json', dict(estimator_sha256=digest(estimator) if estimator.is_file() else None,
        manifest_sha256=digest(output/'manifest.json'),declared_phase='measure',role=manifest['role'],
        batches_sha256=digest(output/'batches.json'),comparisons_sha256=digest(output/'comparisons.json')))


def analyse_schedules(output, estimator, schedule='all'):
    manifest, cases = analysis_cases(output)
    cases = [case for case in cases if case.rsplit('-',1)[1] in ('PAN16','RGB8')]
    choices = {'all':[(1,8),(2,4),(8,1)],'1x8':[(1,8)],'2x4':[(2,4)],'8x1':[(8,1)]}
    if schedule not in choices or (manifest['role'] != 'development' and schedule == 'all'):
        raise ValueError('analysis requires an explicit fixed schedule for reserved roles')
    declared = choices[schedule]
    expected = {(case,operation,*arm,round_id) for case in cases for operation in ('encode','decode')
                for arm in declared for round_id in range(20)}
    indexed = index_observations(json.loads((output/'schedules.json').read_text()),expected,
                                 ('case','operation','concurrent','workers','round'))
    comparisons = []
    for case in cases:
        for operation in ('encode','decode'):
            for candidate in ((2,4),(8,1)):
                record = dict(case=case,operation=operation,baseline=[1,8],candidate=candidate,
                              boundary='eight_request_application_cohort_including_process_io_and_verification')
                if (1,8) not in declared or candidate not in declared:
                    record['verdict'] = 'not_measured'
                else:
                    sides = [[indexed[(case,operation,*arm,round_id)] for round_id in range(20)] for arm in ((1,8),candidate)]
                    if any(r['status']!='ok' for side in sides for r in side):
                        record['verdict'] = 'invalid'
                    else:
                        data = {name:[r['application_wall_ns'] for r in side] for name,side in zip(('baseline','candidate'),sides)}
                        record.update(json.loads(subprocess.check_output([str(estimator)],input=json.dumps(data),text=True)))
                comparisons.append(record)
    write(output/'schedule-comparisons.json',comparisons)
    write(output/'schedule-analysis-identity.json',dict(estimator_sha256=digest(estimator) if estimator.is_file() else None,
        manifest_sha256=digest(output/'manifest.json'),declared_phase='schedule',declared_schedule=schedule,
        schedules_sha256=digest(output/'schedules.json'),comparisons_sha256=digest(output/'schedule-comparisons.json')))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('phase', choices=['build','estimator','prepare','measure','diagnose','schedule','reprofile','analyse','analyse-schedules'])
    parser.add_argument('--prepared', type=Path)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--binary', type=Path)
    parser.add_argument('--allocation', type=Path)
    parser.add_argument('--codec-source', type=Path)
    parser.add_argument('--build-provenance', type=Path)
    parser.add_argument('--estimator', type=Path)
    parser.add_argument('--cpus', default='0,1,2,3,4,5,6,7')
    parser.add_argument('--role', choices=ROLES.values(), default='development')
    parser.add_argument('--schedule', choices=['all','1x8','2x4','8x1'], default='all')
    args = parser.parse_args()
    if args.phase == 'build':
        if args.codec_source is None:
            raise ValueError('build requires --codec-source')
        build_consumer(args.codec_source,args.output)
        return
    if args.phase == 'estimator':
        estimator_build(Path(__file__).resolve().parents[1], args.output)
        return
    if args.phase == 'analyse-schedules':
        analyse_schedules(args.output,args.estimator,args.schedule)
        return
    if args.phase == 'analyse':
        analyse(args.output, args.estimator)
        return
    cpus = [int(c) for c in args.cpus.split(',')]
    if len(cpus) != 8 or len(set(cpus)) != 8 or not set(cpus) <= os.sched_getaffinity(0):
        raise ValueError('exactly eight distinct available CPUs required')
    if args.output.parent.resolve() != args.prepared.parent.resolve() or not args.output.name.startswith('real-scene-viewing-'):
        raise ValueError('campaign output must be a fresh real-scene-viewing child of the approved store')
    if args.allocation is None:
        args.allocation = args.binary.parent / 'lossless_bypass_allocation'
    os.sched_setaffinity(0, cpus)
    selected = [a for a in assets(args.prepared) if ROLES[a['bundle_id']] == args.role]
    if args.phase == 'prepare':
        if args.codec_source is None or args.build_provenance is None:
            raise ValueError('preparation requires codec Git objects and bound build provenance')
        build_identity = bind_build(args.binary,args.allocation,args.codec_source,args.build_provenance)
        args.output.mkdir()
        with (args.output/'build-provenance.json').open('xb') as bound:
            bound.write(args.build_provenance.read_bytes())
        (args.output / 'streams').mkdir()
        (args.output / 'preparation').mkdir()
        licence = args.prepared.parent / 'source/LICENSE.txt'
        if digest(licence) != 'f627ad059128fa5246a21e25759c1d33e35c4bb6287d636c4b970f7df57e7eba':
            raise ValueError('reviewed licence notice identity differs')
        (args.output / 'LICENSE.txt').write_bytes(licence.read_bytes())
        write(args.output / 'manifest.json', dict(assets=selected, prepared_sha256=MANIFEST,
            **build_identity,
            environment=dict(uname=list(os.uname()),affinity=sorted(os.sched_getaffinity(0)),cpuinfo_sha256=digest('/proc/cpuinfo'),
                rustc=subprocess.check_output(['rustc','-Vv'],text=True),rayon_threads='explicit builder per worker'),
            binary_sha256=digest(args.binary), allocation_sha256=digest(args.allocation), cpus=cpus, role=args.role,
            limits=dict(max_working_bytes=WORKING,max_output_bytes=OUTPUT,aggregate_bytes=BUDGET),
            protocol=dict(rounds=20,warmups=0,samples=1,timeout_seconds=120,order='AB/BA',threshold=0.05),
            source_revision=subprocess.check_output(['git','-C',str(Path(__file__).resolve().parents[1]),'rev-parse','HEAD'],text=True).strip()))
        (args.output / 'ATTRIBUTION.md').write_text('RarePlanes Dataset, June 2020: J. Shermeyer, T. Hossler, A. Van Etten, D. Hogan, R. Lewis and D. Kim; In-Q-Tel - CosmiQ Works and AI.Reverie.\nCC BY-SA 4.0: https://creativecommons.org/licenses/by-sa/4.0/\nModifications: lossless JPEG 2000 derivatives from the bound prepared-final raw products. manifest.json retains source lineage and identities. Source pixels are unchanged.\n')
        for asset in selected:
            for style in (0,1):
                req = request(asset,args.prepared,args.output,style,1,'prepare')
                result = execute(args.binary,req,args.output/'preparation'/(asset['id']+'-'+str(style)),cpus)
                if result['status'] != 0:
                    raise RuntimeError('preparation failed; retained evidence')
        return
    manifest = json.loads((args.output / 'manifest.json').read_text())
    if manifest['binary_sha256'] != digest(args.binary) or manifest['cpus'] != cpus or manifest['assets'] != selected:
        raise ValueError('bound build, CPUs or coverage changed')
    verify_inputs(args,selected,manifest)
    folder = args.output / args.phase
    folder.mkdir()
    rows = []
    if args.phase == 'reprofile':
        rows = reprofile_schedule(args,selected,cpus,folder)
        verify_inputs(args,selected,manifest)
        write(args.output/'selected-reprofile.json',dict(rows=rows,
            source_revision=subprocess.check_output(['git','-C',str(Path(__file__).resolve().parents[1]),'rev-parse','HEAD'],text=True).strip(),
            script_sha256=digest(Path(__file__)),binary_sha256=digest(args.binary),
            allocation_limitation='Existing allocation-only probe uses nested_pool; direct/global decode allocation is not observed.'))
    elif args.phase == 'measure':
        for round_id in range(20):
            for asset in selected:
                for operation in ('encode','decode'):
                    for contrast, left, right in CONTRASTS:
                        treatments = [left,right] if round_id % 2 == 0 else [right,left]
                        for style,workers in treatments:
                            req = request(asset,args.prepared,args.output,style,workers,operation,round_id)
                            result = execute(args.binary,req,folder/str(len(rows)),cpus)
                            rows.append(dict(case=asset['id'],operation=operation,contrast=contrast,style=style,workers=workers,round=round_id,result=result))
            print(json.dumps({'round_complete':round_id,'batches':len(rows),'failures':sum(r['result']['status']!=0 for r in rows)}),flush=True)
        verify_inputs(args,selected,manifest)
        write(args.output/'batches.json',rows)
    elif args.phase == 'diagnose':
        for asset in selected:
            for style in (0,1):
                for workers in (1,8):
                    req = request(asset,args.prepared,args.output,style,workers,'profile')
                    result = execute(args.binary,req,folder/(str(len(rows))+'-profile'),cpus)
                    allocation_req = dict(req,operation='allocation',execution_context='nested_pool')
                    alloc = execute(args.allocation,allocation_req,folder/(str(len(rows))+'-allocation'),cpus,
                        extra_args=[req['raw_path'],str(req['width']),str(req['height']),str(req['components']),str(req['bits']),str(workers),str(style),str(WORKING),str(OUTPUT)])
                    direct_req = request(asset,args.prepared,args.output,style,workers,'decode_diagnostic')
                    direct = execute(args.binary,direct_req,folder/(str(len(rows))+'-direct'),cpus)
                    nested_req = request(asset,args.prepared,args.output,style,workers,'decode_diagnostic',context='nested_pool')
                    nested = execute(args.binary,nested_req,folder/(str(len(rows))+'-nested'),cpus)
                    rows.append(dict(case=asset['id'],style=style,workers=workers,profile=result,allocation=alloc,direct=direct,nested=nested))
        verify_inputs(args,selected,manifest)
        write(args.output/'diagnostics.json',rows)
    elif args.phase == 'schedule':
        # Eight identical requests per cohort; only the admission-checked window
        # of concurrent processes is dispatched. Process lifecycle/IO/validation
        # are included in application wall time, separate from facade latency.
        selected = [a for a in selected if a['product'] in ('PAN16','RGB8')]
        admissions = {}
        for asset in selected:
            for workers in (1,4,8):
                req = request(asset,args.prepared,args.output,1,workers,'requirements')
                admissions[(asset['id'],workers)] = execute(args.binary,req,folder/('admission-'+asset['id']+'-'+str(workers)),cpus)
        for round_id in range(20):
            for asset in selected:
                for operation in ('encode','decode'):
                    schedules = [(1,8),(2,4),(8,1)]
                    if args.schedule != 'all':
                        schedules = [tuple(map(int,args.schedule.split('x')))]
                    if args.role != 'development' and args.schedule == 'all':
                        raise ValueError('freeze selected schedule before validation')
                    if round_id % 2:
                        schedules.reverse()
                    for concurrent,workers in schedules:
                        req = request(asset,args.prepared,args.output,1,workers,operation,round_id)
                        admission = admissions[(asset['id'],workers)]
                        if admission['status'] != 0:
                            raise RuntimeError('actual same-context requirements failed; retained evidence')
                        # Admission bounds encoder allocations. Add source,
                        # reference/reconstruction, retained stream and runtime
                        # margin; the process address-space ceiling also bounds
                        # decoder allocations, whose facade has no query API.
                        allowance = admission['observation']['requirements_working_bytes'] + asset['bytes']*3 + OUTPUT + 64*1024**2
                        row = dict(case=asset['id'],operation=operation,round=round_id,concurrent=concurrent,workers=workers,requests=8,
                                   per_process_allowance=allowance,aggregate_allowance=allowance*concurrent+CONTROLLER)
                        if allowance * concurrent + CONTROLLER > BUDGET:
                            row.update(status='rejected',reason='conservative aggregate admission exceeds8GiB')
                        else:
                            row.update(schedule_cohort(args.binary,req,folder,len(rows),cpus,concurrent))
                        rows.append(row)
            print(json.dumps({'schedule_round_complete':round_id,'cohorts':len(rows)}),flush=True)
        verify_inputs(args,selected,manifest)
        write(args.output/'schedules.json',rows)


def concurrent_module(workers):
    return concurrent.futures.ThreadPoolExecutor(max_workers=workers)


if __name__ == '__main__':
    main()
