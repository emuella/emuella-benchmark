#!/usr/bin/env python3
"""Bounded facade treatment and application-schedule experiment.

Different coding/thread/context treatments remain separately named. This is not
an ordinary compare() run and never changes that contract's comparability keys.
Inputs and generated streams must stay in an independently authorised store.
"""
import argparse
import concurrent.futures
import hashlib
import json
import os
from pathlib import Path
import signal
import resource
import subprocess
import time

ROLES = {'94_104001000B823500': 'development',
         '106_10400100413CDF00': 'validation', '105_104001002F92BB00': 'regression'}
PRODUCTS = ('PAN16', 'RGB16', 'MS16', 'RGB8')
WORKING = 768 * 1024**2
OUTPUT = 64 * 1024**2
BUDGET = 8 * 1024**3
CONTROLLER = 128 * 1024**2
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
        result['observation'] = json.loads((directory / 'stdout.json').read_text())
        user, system, rss = (directory / 'resources.txt').read_text().split()
        result.update(process_cpu_seconds=float(user) + float(system), process_peak_rss_bytes=int(rss) * 1024)
    write(directory / 'result.json', result)
    return result


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


def analyse(output, estimator):
    rows = json.loads((output / 'batches.json').read_text())
    comparisons = []
    for case in sorted({r['case'] for r in rows}):
        for operation in ('encode', 'decode'):
            for contrast, left, right in [('bypass_at1',(0,1),(1,1)), ('bypass_at8',(0,8),(1,8)),
                                           ('combined',(0,1),(1,8)), ('style0_parallel',(0,1),(0,8)),
                                           ('bypass_parallel',(1,1),(1,8))]:
                sides = [[r for r in rows if (r['case'],r['operation'],r['style'],r['workers']) ==
                          (case,operation,*side)] for side in (left,right)]
                record = dict(case=case,operation=operation,contrast=contrast,baseline=left,candidate=right)
                if any(len(s) != 20 or any(r['result']['status'] != 0 for r in s) for s in sides):
                    record['verdict'] = 'invalid'
                else:
                    data = {name:[r['result']['observation']['samples_ns'][0] for r in side]
                            for name,side in zip(('baseline','candidate'),sides)}
                    result = subprocess.check_output([str(estimator)], input=json.dumps(data), text=True)
                    record.update(json.loads(result))
                comparisons.append(record)
    write(output / 'comparisons.json', comparisons)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('phase', choices=['estimator','prepare','measure','diagnose','schedule','analyse'])
    parser.add_argument('--prepared', type=Path)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--binary', type=Path)
    parser.add_argument('--allocation', type=Path)
    parser.add_argument('--codec-source', type=Path)
    parser.add_argument('--estimator', type=Path)
    parser.add_argument('--cpus', default='0,1,2,3,4,5,6,7')
    parser.add_argument('--role', choices=ROLES.values(), default='development')
    parser.add_argument('--schedule', choices=['all','1x8','2x4','8x1'], default='all')
    args = parser.parse_args()
    if args.phase == 'estimator':
        estimator_build(Path(__file__).resolve().parents[1], args.output)
        return
    if args.phase == 'analyse':
        analyse(args.output, args.estimator)
        return
    cpus = [int(c) for c in args.cpus.split(',')]
    if len(cpus) != 8 or len(set(cpus)) != 8 or not set(cpus) <= os.sched_getaffinity(0):
        raise ValueError('exactly eight distinct available CPUs required')
    os.sched_setaffinity(0, cpus)
    selected = [a for a in assets(args.prepared) if ROLES[a['bundle_id']] == args.role]
    if args.phase == 'prepare':
        args.output.mkdir()
        (args.output / 'streams').mkdir()
        (args.output / 'preparation').mkdir()
        licence = args.prepared.parent / 'source/LICENSE.txt'
        if digest(licence) != 'f627ad059128fa5246a21e25759c1d33e35c4bb6287d636c4b970f7df57e7eba':
            raise ValueError('reviewed licence notice identity differs')
        (args.output / 'LICENSE.txt').write_bytes(licence.read_bytes())
        write(args.output / 'manifest.json', dict(assets=selected, prepared_sha256=MANIFEST,
            codec_revision=subprocess.check_output(['git','-C',str(args.codec_source),'rev-parse','HEAD'],text=True).strip(),
            environment=dict(uname=list(os.uname()),affinity=sorted(os.sched_getaffinity(0)),cpuinfo_sha256=digest('/proc/cpuinfo'),
                rustc=subprocess.check_output(['rustc','-Vv'],text=True),rayon_threads='explicit builder per worker'),
            binary_sha256=digest(args.binary), cpus=cpus, role=args.role,
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
    folder = args.output / args.phase
    folder.mkdir()
    rows = []
    if args.phase == 'measure':
        for round_id in range(20):
            for asset in selected:
                for operation in ('encode','decode'):
                    treatments = [(0,1),(1,1),(0,8),(1,8)]
                    if round_id % 2:
                        treatments.reverse()
                    for style,workers in treatments:
                        req = request(asset,args.prepared,args.output,style,workers,operation,round_id)
                        result = execute(args.binary,req,folder/str(len(rows)),cpus)
                        rows.append(dict(case=asset['id'],operation=operation,style=style,workers=workers,round=round_id,result=result))
            print(json.dumps({'round_complete':round_id,'batches':len(rows),'failures':sum(r['result']['status']!=0 for r in rows)}),flush=True)
        write(args.output/'batches.json',rows)
    elif args.phase == 'diagnose':
        for asset in selected:
            for style in (0,1):
                for workers in (1,8):
                    req = request(asset,args.prepared,args.output,style,workers,'profile')
                    result = execute(args.binary,req,folder/(str(len(rows))+'-profile'),cpus)
                    alloc = execute(args.allocation,req,folder/(str(len(rows))+'-allocation'),cpus,
                        extra_args=[req['raw_path'],str(req['width']),str(req['height']),str(req['components']),str(req['bits']),str(workers),str(style),str(WORKING),str(OUTPUT)])
                    nested_req = request(asset,args.prepared,args.output,style,workers,'decode',context='nested_pool')
                    nested = execute(args.binary,nested_req,folder/(str(len(rows))+'-nested'),cpus)
                    rows.append(dict(case=asset['id'],style=style,workers=workers,profile=result,allocation=alloc,nested=nested))
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
                            start = time.monotonic_ns()
                            def one(index):
                                return execute(args.binary,req,folder/(str(len(rows))+'-'+str(index)),cpus,address_limit=(BUDGET-CONTROLLER)//concurrent)
                            with concurrent_module(concurrent) as pool:
                                results = list(pool.map(one,range(8)))
                            row.update(status='ok' if all(r['status']==0 for r in results) else 'failed',
                                application_wall_ns=time.monotonic_ns()-start,results=results,
                                sum_process_peak_rss_upper_bound=sum(sorted((r.get('process_peak_rss_bytes',0) for r in results),reverse=True)[:concurrent]),
                                controller_peak_rss_bytes=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024)
                        rows.append(row)
            print(json.dumps({'schedule_round_complete':round_id,'cohorts':len(rows)}),flush=True)
        write(args.output/'schedules.json',rows)


def concurrent_module(workers):
    return concurrent.futures.ThreadPoolExecutor(max_workers=workers)


if __name__ == '__main__':
    main()
