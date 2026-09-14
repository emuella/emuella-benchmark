#!/usr/bin/env python3
"""Matched current-codec comparison; protected inputs remain in their approved store."""
import argparse
import importlib.util
import json
import os
from pathlib import Path
import platform
import signal
import statistics
import subprocess
import time

ROOT = Path(__file__).resolve().parents[1]

def module(name, filename):
    spec = importlib.util.spec_from_file_location(name, ROOT / 'scripts' / filename)
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result

classic = module('classic_refresh_support', 'real-scene-classic.py')
build_support = module('refresh_build_support', 'build-workers.py')
sha = classic.digest
write = classic.write
CODECS = ('openjpeg', 'emuella')
STYLES = (0, 1)
THREADS = (1, 8)
ROUNDS = 20
BOUNDARY = 'owned_interleaved_bytes_to_owned_codestream_or_interleaved_bytes'


def git(source, *args):
    return subprocess.check_output(['git', '-C', str(source), *args], text=True).strip()


def build(source, output, sampling=False):
    benchmark = classic.clean_source(ROOT)
    codec = classic.clean_source(source)
    output.mkdir(parents=True, exist_ok=False)
    snapshot = output / 'source'
    snapshot.mkdir()
    archive = subprocess.Popen(['git', '-C', str(ROOT), 'archive', benchmark['source_revision']], stdout=subprocess.PIPE)
    subprocess.run(['tar', '-x', '-C', str(snapshot)], stdin=archive.stdout, check=True)
    archive.stdout.close()
    if archive.wait():
        raise ValueError('source archive failed')
    command = ['cargo', 'build', '--profile', 'perf', '--manifest-path', str(snapshot / 'workers/Cargo.toml'),
               '--bin', 'classic-compare-worker', '--features', 'classic-encode-sampling' if sampling else 'classic-compare', '--target-dir', str(output / 'target'), '--message-format=json', '-vv']
    for package in ('emuella-j2k', 'emuella-j2k-codestream'):
        command += ['--config', 'patch."https://github.com/emuella/emuella-j2k".' + package + '.path=' + json.dumps(str(source / 'crates' / package))]
    env = dict(os.environ)
    configs = build_support.cargo_config_files(snapshot, env)
    with (output / 'cargo.jsonl').open('x') as stdout, (output / 'cargo.stderr').open('x') as stderr:
        subprocess.run(command, cwd=snapshot, env=env, stdout=stdout, stderr=stderr, check=True)
    events = []
    for line in (output / 'cargo.jsonl').read_text().splitlines():
        try:
            events.append(json.loads(line))
        except json.JSONDecodeError:
            pass
    binaries = [e for e in events if e.get('reason') == 'compiler-artifact' and e.get('target', {}).get('name') == 'classic-compare-worker' and e.get('executable')]
    if len(binaries) != 1 or not any(e.get('reason') == 'build-finished' and e.get('success') for e in events):
        raise ValueError('missing unique completed Cargo executable')
    binary = Path(binaries[0]['executable'])
    if classic.clean_source(ROOT) != benchmark or classic.clean_source(source) != codec or configs != build_support.cargo_config_files(snapshot, env):
        raise ValueError('source/configuration changed during build')
    libraries = {str(p): sha(p) for p in build_support.libraries(binary)}
    write(output / 'build.json', dict(benchmark=benchmark, codec=codec, sampling=sampling,
          encoder_backend=env.get('EMUELLA_TIER1_ENCODER', 'default'), binary=str(binary), binary_sha256=sha(binary),
          libraries=libraries, rustc=subprocess.check_output(['rustc', '-vV'], text=True),
          openjpeg=subprocess.check_output(['pkg-config', '--modversion', 'libopenjp2'], text=True).strip(),
          command=command, environment=build_support.build_environment(env), cargo_configs=configs,
          artefacts=[e for e in events if e.get('reason') == 'compiler-artifact'],
          lock_sha256=sha(snapshot / 'workers/Cargo.lock'), logs={p:sha(output / p) for p in ('cargo.jsonl','cargo.stderr')}))
    print(binary, flush=True)


def bind(build_path):
    record = json.loads(build_path.read_text())
    if sha(record['binary']) != record['binary_sha256']:
        raise ValueError('binary identity changed')
    for path, expected in record['libraries'].items():
        if sha(path) != expected:
            raise ValueError('runtime library identity changed')
    return record


def cpu_identity(cpus):
    return dict(cpus=cpus, cpuinfo_sha256=sha('/proc/cpuinfo'), platform=platform.platform(),
                model=next((x.split(':',1)[1].strip() for x in Path('/proc/cpuinfo').read_text().splitlines() if x.startswith('model name')), 'unknown'),
                governors={str(c):Path(f'/sys/devices/system/cpu/cpu{c}/cpufreq/scaling_governor').read_text().strip() for c in cpus},
                topology={str(c):{k:Path(f'/sys/devices/system/cpu/cpu{c}/topology/{k}').read_text().strip() for k in ('physical_package_id','core_id','thread_siblings_list')} for c in cpus})


def run_process(binary, request, directory, cpus):
    directory.mkdir()
    write(directory / 'request.json', request)
    command = ['taskset','-c',','.join(map(str,cpus)), 'prlimit','--as='+str(classic.BUDGET),'--',
               '/usr/bin/time','-f','%U %S %M','-o',str(directory/'resources.txt'),str(binary),str(directory/'request.json')]
    start = time.monotonic_ns()
    with (directory/'stdout.json').open('x') as stdout, (directory/'stderr.txt').open('x') as stderr:
        process = subprocess.Popen(command, stdout=stdout, stderr=stderr, start_new_session=True)
        try:
            status = process.wait(timeout=120)
        except subprocess.TimeoutExpired:
            os.killpg(process.pid, signal.SIGKILL)
            process.wait()
            status = 'timeout'
    result = dict(status=status, process_wall_ns=time.monotonic_ns()-start)
    if status == 0:
        try:
            value = json.loads((directory/'stdout.json').read_text())
            for field in ('codec','operation','case_id','round','style','workers','raw_sha256'):
                if value.get(field) != request[field]:
                    raise ValueError('response differs: '+field)
            if value.get('boundary') != BOUNDARY or value.get('exact') is not True or value.get('binary_sha256') != sha(binary):
                raise ValueError('response exactness/binary differs')
            samples = value.get('samples_ns')
            if request['operation'] == 'prepare':
                if samples != [] or value['stream_sha256'] != sha(request['stream_path']):
                    raise ValueError('prepare response differs')
            elif (not isinstance(samples,list) or len(samples)!=1 or type(samples[0]) is not int or samples[0]<=0 or value.get('stream_sha256') != request['stream_sha256']):
                raise ValueError('timing/stream identity differs')
            user, system, rss = (directory/'resources.txt').read_text().split()
            result.update(observation=value,process_cpu_seconds=float(user)+float(system),process_peak_rss_bytes=int(rss)*1024)
        except (ValueError,TypeError,KeyError) as error:
            result.update(status='invalid_response',reason=str(error))
    write(directory/'result.json', result)
    return result


def make_request(asset, prepared, folder, origin, codec, style, workers, operation, round_id):
    image = asset['image']
    stream = folder/'streams'/f"{asset['id']}-{origin}-s{style}.j2k"
    request = dict(codec=codec,operation=operation,case_id=asset['id'],round=round_id,
                   width=image['width'],height=image['height'],components=image['components'],bits=image['precision'],
                   layout='interleaved',style=style,workers=workers,raw_path=str(prepared/asset['path']),
                   raw_sha256=asset['sha256'],stream_path=str(stream),
                   max_working_bytes=classic.WORKING,max_output_bytes=classic.OUTPUT)
    if operation != 'prepare':
        request['stream_sha256'] = sha(stream)
    return request


def expected_keys(case_ids, rounds):
    return {(case,s,w,op,origin,r,codec) for case in case_ids for s in STYLES for w in THREADS
            for op,origin in (('encode','own'),('decode','openjpeg'),('decode','emuella'))
            for r in range(rounds) for codec in CODECS}


def validate_rows(rows, case_ids, rounds):
    expected = expected_keys(case_ids, rounds)
    seen = set()
    for row in rows:
        key = tuple(row[k] for k in ('case_id','style','workers','operation','origin','round','codec'))
        if key not in expected or key in seen:
            raise ValueError('duplicate or unexpected measurement identity')
        seen.add(key)
    if seen != expected:
        raise ValueError('missing planned measurements')


def measure(args):
    owner = classic.clean_source(ROOT)
    build_record = bind(args.build)
    if build_record.get('sampling'):
        raise ValueError('sampling builds cannot supply headline measurements')
    # Source identity is fixed by committed bytes, including hidden index changes.
    if build_record['benchmark']['source_files_sha256'] != owner['source_files_sha256']:
        raise ValueError('build and runner source trees differ')
    selected = classic.assets(args.prepared)
    if args.probe:
        selected = [a for a in selected if a['id']=='94_104001000B823500-PAN16']
    rounds = 1 if args.probe else ROUNDS
    store = args.prepared.parent.resolve()
    if args.output.parent.resolve() != store or store not in args.prepared.resolve().parents:
        raise ValueError('output must be a new direct child of the prepared approved store')
    cpus = [int(x) for x in args.cpus.split(',')]
    if len(cpus)!=8 or len(set(cpus))!=8 or not set(cpus)<=os.sched_getaffinity(0):
        raise ValueError('requires eight distinct available CPU IDs')
    args.output.mkdir(exist_ok=False)
    (args.output/'streams').mkdir()
    notice = store/'source/LICENSE.txt'
    if sha(notice) != 'f627ad059128fa5246a21e25759c1d33e35c4bb6287d636c4b970f7df57e7eba':
        raise ValueError('reviewed licence notice differs')
    (args.output/'LICENSE.txt').write_bytes(notice.read_bytes())
    (args.output/'NOTICE.txt').write_text('RarePlanes Dataset, June 2020. J. Shermeyer, T. Hossler, A. Van Etten, D. Hogan, R. Lewis and D. Kim; In-Q-Tel - CosmiQ Works and AI.Reverie. CC BY-SA 4.0. New lossless JPEG 2000 encodings of the identified prepared samples; no imagery redistribution. See manifest.json for source lineage.\n')
    manifest = dict(schema_version=1,probe=args.probe,rounds=rounds,case_ids=[a['id'] for a in selected],assets=selected,
                    prepared_sha256=sha(args.prepared/'prepared.json'),build_sha256=sha(args.build),build=build_record,
                    owner=owner,machine=cpu_identity(cpus),boundary=BOUNDARY,styles=list(STYLES),workers=list(THREADS),
                    timeout_seconds=120,address_space_bytes=classic.BUDGET,warmup=0,samples_per_batch=1,
                    order='alternating AB/BA per adjacent codec pair; OpenJPEG first in even rounds',
                    started_utc=time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime()))
    write(args.output/'manifest.json',manifest)
    binary = build_record['binary']
    preparations = []
    for asset in selected:
        for style in STYLES:
            for codec in CODECS:
                request = make_request(asset,args.prepared,args.output,codec,codec,style,1,'prepare',0)
                name=f"prepare-{asset['id']}-{codec}-s{style}"
                result=run_process(binary,request,args.output/name,cpus[:1])
                preparations.append(dict(case_id=asset['id'],style=style,codec=codec,result=result,path=name))
                print(name,result['status'],flush=True)
    write(args.output/'preparations.json',preparations)
    rows=[]
    for round_id in range(rounds):
        for asset in selected:
            for style in STYLES:
                for workers in THREADS:
                    for operation,origin in (('encode','own'),('decode','openjpeg'),('decode','emuella')):
                        for codec in CODECS if round_id%2==0 else tuple(reversed(CODECS)):
                            stream_origin=codec if origin=='own' else origin
                            name=f"r{round_id:02}-{asset['id']}-s{style}-w{workers}-{operation}-{origin}-{codec}"
                            stream=args.output/'streams'/f"{asset['id']}-{stream_origin}-s{style}.j2k"
                            prep=next(p for p in preparations if p['case_id']==asset['id'] and p['style']==style and p['codec']==stream_origin)
                            if prep['result']['status']!=0:
                                result=dict(status='preparation_failed')
                            else:
                                request=make_request(asset,args.prepared,args.output,stream_origin,codec,style,workers,operation,round_id)
                                result=run_process(binary,request,args.output/name,cpus[:workers])
                            rows.append(dict(case_id=asset['id'],style=style,workers=workers,operation=operation,origin=origin,round=round_id,codec=codec,result=result,path=name))
        print(f'round {round_id+1}/{rounds}: {len(rows)} observations; {sum(r["result"]["status"]!=0 for r in rows)} failures',flush=True)
    validate_rows(rows,manifest['case_ids'],rounds)
    if classic.clean_source(ROOT)!=owner or bind(args.build)!=build_record or sha(args.prepared/'prepared.json')!=manifest['prepared_sha256']:
        raise ValueError('source/build/manifest changed during measurement')
    for asset in selected:
        if sha(args.prepared/asset['path'])!=asset['sha256']:
            raise ValueError('prepared asset changed during measurement')
    success=all(r['result']['status']==0 for r in rows+preparations)
    write(args.output/'measurement.json',dict(complete=success,manifest_sha256=sha(args.output/'manifest.json'),rows=rows,
          preparations=preparations,finished_utc=time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime())))
    return 0 if success else 4


def analyse(folder, estimator):
    manifest=json.loads((folder/'manifest.json').read_text())
    measurement=json.loads((folder/'measurement.json').read_text())
    if manifest['probe'] or manifest['rounds']!=ROUNDS or sha(folder/'manifest.json')!=measurement['manifest_sha256']:
        raise ValueError('headline analysis requires complete bound twenty-round protocol')
    rows=measurement['rows']
    validate_rows(rows,manifest['case_ids'],ROUNDS)
    comparisons=[]
    for case in manifest['case_ids']:
        for style in STYLES:
            for workers in THREADS:
                for operation,origin in (('encode','own'),('decode','openjpeg'),('decode','emuella')):
                    subset=[r for r in rows if (r['case_id'],r['style'],r['workers'],r['operation'],r['origin'])==(case,style,workers,operation,origin)]
                    entry=dict(case_id=case,style=style,workers=workers,operation=operation,origin=origin)
                    if any(r['result']['status']!=0 for r in subset):
                        entry.update(verdict='invalid_coverage',failures=[r for r in subset if r['result']['status']!=0])
                    else:
                        arms={c:[r['result'] for r in sorted(subset,key=lambda r:r['round']) if r['codec']==c] for c in CODECS}
                        samples={c:[r['observation']['samples_ns'][0] for r in arm] for c,arm in arms.items()}
                        estimate=json.loads(subprocess.check_output([str(estimator)],input=json.dumps(dict(baseline=samples['openjpeg'],candidate=samples['emuella'])),text=True))
                        entry.update(estimate)
                        entry['codecs']={c:dict(mean_ms=statistics.mean(samples[c])/1e6,operation_samples_ns=samples[c],exact_batches=len(arm),maximum_process_rss_bytes=max(r['process_peak_rss_bytes'] for r in arm),mean_process_cpu_seconds=statistics.mean(r['process_cpu_seconds'] for r in arm),stream_bytes=sorted({r['observation']['stream_bytes'] for r in arm})) for c,arm in arms.items()}
                    comparisons.append(entry)
    report=dict(schema_version=1,complete=measurement['complete'],manifest_sha256=sha(folder/'manifest.json'),measurement_sha256=sha(folder/'measurement.json'),
                codec_revision=manifest['build']['codec']['source_revision'],codec_tree=manifest['build']['codec']['source_tree'],
                benchmark_revision=manifest['owner']['source_revision'],openjpeg=manifest['build']['openjpeg'],
                analysis_revision=git(ROOT,'rev-parse','HEAD'),analysis_script_sha256=sha(__file__),
                build_summary=dict(rustc=manifest['build']['rustc'],requested_profile='perf',binary_sha256=manifest['build']['binary_sha256'],runtime_libraries={Path(p).name:d for p,d in manifest['build']['libraries'].items()}),
                inputs=[dict(case_id=a['id'],image=a['image'],raw_sha256=a['sha256'],raw_bytes=(a['image']['width']*a['image']['height']*a['image']['components']*a['image']['precision']//8)) for a in manifest['assets']],
                estimator_provenance=json.loads((estimator.parents[2]/'provenance.json').read_text()),
                machine=manifest['machine'],comparisons=comparisons,
                interpretation='candidate is Emuella; relative change is Emuella/OpenJPEG minus one; per-comparison uncertainty only; failures retained',
                estimator_sha256=sha(estimator),completed_utc=measurement['finished_utc'])
    write(folder/'report.json',report)
    lines=['# Refreshed Emuella–OpenJPEG comparison','',f"Codec `{report['codec_revision']}`; OpenJPEG {report['openjpeg']}; {report['completed_utc']}.",'',
           'Twenty fresh-process rounds per codec and contrast; mean milliseconds, lower is better. E/O is Emuella time divided by OpenJPEG time. Decode origin names the identical stream supplied to both decoders. Verdict uses the conservative 99% interval and 5% practical gate; candidate is Emuella.','',
           '| Case | Style | Workers | Operation / stream origin | OpenJPEG ms | Emuella ms | E/O | Verdict |','|---|---:|---:|---|---:|---:|---:|---|']
    for e in comparisons:
        if 'codecs' in e:
            o=e['codecs']['openjpeg']['mean_ms']; m=e['codecs']['emuella']['mean_ms']
            values=f'{o:.3f} | {m:.3f} | {m/o:.3f}'
        else:
            values='— | — | —'
        lines.append(f"| {e['case_id']} | {e['style']} | {e['workers']} | {e['operation']} / {e['origin']} | {values} | {e['verdict']} |")
    lines += ['', 'Whole-process peak RSS and CPU time, compressed sizes, exact identities and all intervals are in report.json. These measurements describe the fixed nine-product cohort on one host. They do not establish full corpus coverage or a universal codec ranking.', '', 'RarePlanes attribution: J. Shermeyer, T. Hossler, A. Van Etten, D. Hogan, R. Lewis and D. Kim; In-Q-Tel - CosmiQ Works and AI.Reverie; RarePlanes Dataset, June 2020, CC BY-SA 4.0. Factual measurements only; no image payload.']
    (folder/'report.md').write_text('\n'.join(lines)+'\n')
    print(json.dumps({'comparisons':len(comparisons),'complete':report['complete']}))


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    sub=parser.add_subparsers(dest='command',required=True)
    p=sub.add_parser('build'); p.add_argument('--codec-source',type=Path,required=True); p.add_argument('--output',type=Path,required=True); p.add_argument('--sampling',action='store_true')
    p=sub.add_parser('measure'); p.add_argument('--build',type=Path,required=True); p.add_argument('--prepared',type=Path,required=True); p.add_argument('--output',type=Path,required=True); p.add_argument('--cpus',required=True); p.add_argument('--probe',action='store_true')
    p=sub.add_parser('analyse'); p.add_argument('--output',type=Path,required=True); p.add_argument('--estimator',type=Path,required=True)
    p=sub.add_parser('estimator'); p.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    for key in ('output','build','prepared','codec_source','estimator'):
        if getattr(args,key,None) is not None:
            setattr(args,key,getattr(args,key).resolve())
    if args.command=='build': build(args.codec_source,args.output,args.sampling)
    elif args.command=='measure': return measure(args)
    elif args.command=='analyse': analyse(args.output,args.estimator)
    elif args.command=='estimator': classic.estimator_build(ROOT,args.output)
    return 0

if __name__=='__main__':
    raise SystemExit(main())
