#!/usr/bin/env python3
"""Bounded encoder treatment using the existing refresh worker and estimator."""
import argparse
import json
from pathlib import Path
import statistics
import subprocess
import time

import importlib.util
SPEC = importlib.util.spec_from_file_location('kernel_refresh', Path(__file__).with_name('openjpeg-refresh.py'))
refresh = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(refresh)
sha, write = refresh.sha, refresh.write
ARMS = ('reference', 'packed')
SPACENET_MANIFEST = '209eb97c250f108c4ff0aff9a226db6dc6e4ecd68b10bc074e844b60b89e406e'


def assets(prepared, phase):
    if phase != 'spacenet':
        return refresh.classic.assets(prepared)
    if sha(prepared/'prepared.json') != SPACENET_MANIFEST:
        raise ValueError('frozen SpaceNet input manifest differs')
    helper=refresh.module('kernel_spacenet', 'spacenet-classic.py')
    return [a for a in helper.assets(prepared) if a['role']=='development']


def entropy_contrasts(assets, phase):
    if phase == 'spacenet':
        if len(assets) != 12 or any(a.get('role') != 'development' or 'Khartoum' in a['id'] for a in assets):
            raise ValueError('entropy timing requires the fixed SpaceNet development selection')
        suffixes = ('AOI_2_Vegas_img1454', 'AOI_3_Paris_img235', 'AOI_4_Shanghai_img1196')
        chips = [a for a in assets if any(a['id'].endswith(s) for s in suffixes)]
        if len(chips) != 3 or len({a['id'] for a in chips}) != 3:
            raise ValueError('fixed entropy SpaceNet chips differ')
        return [(a,s,w,'decode','emuella') for a in chips for s in (0,1)
                for w in ((1,8) if a['id'].endswith(suffixes[0]) else (1,))]
    if len(assets) != 9 or len({a['id'] for a in assets}) != 9:
        raise ValueError('fixed entropy RarePlanes cohort differs')
    dev = [a for a in assets if a['id'].startswith('94_') and a['product'] in ('PAN16','MS16','RGB8')]
    primary = [a for a in assets if a['id'].startswith('106_') and a['product'] in ('PAN16','MS16')]
    if len(dev) != 3 or len(primary) != 2:
        raise ValueError('entropy development or primary acquisition differs')
    if phase in ('screen','describe'):
        return [(a,s,1 if phase == 'screen' else 8,'decode','openjpeg') for a in dev for s in (0,1)]
    primaries = [(a,0,1,'decode','openjpeg') for a in primary]
    if phase == 'primary':
        return primaries
    if phase != 'confirm':
        raise ValueError('unknown entropy phase')
    cases = [(a,s,1,'decode','openjpeg') for a in assets for s in (0,1)]
    cases += [(a,s,8,'decode','openjpeg') for a in assets
              if a in primary or a['id'].startswith('105_') for s in (0,1)]
    cases += [(a,0,w,'decode','emuella') for a in primary for w in (1,8)]
    cases += [(a,s,1,'encode','emuella') for a in dev for s in (0,1)]
    cases += [(a,s,8,'encode','emuella') for a in dev if a['product']=='PAN16' for s in (0,1)]
    return [c for c in cases if c not in primaries]


def incremental_contrasts(assets, phase):
    """Prospective MQ D2 matrix; no development screening or extra rounds."""
    if phase == 'spacenet':
        # Reuse existing cohort/role validation before narrowing the fixed chip.
        eligible = entropy_contrasts(assets, phase)
        return [c for c in eligible if c[0]['id'].endswith('AOI_2_Vegas_img1454') and c[2] == 1]
    primary = entropy_contrasts(assets, 'primary')
    if phase == 'primary':
        return primary
    if phase != 'confirm':
        raise ValueError('incremental confirmation has no screening or descriptive phase')
    boca = [c[0] for c in primary]
    tok = [a for a in assets if a['id'].startswith('105_') and a['product'] == 'RGB8']
    pan = [a for a in assets if a['id'].startswith('94_') and a['product'] == 'PAN16']
    if len(tok) != 1 or len(pan) != 1:
        raise ValueError('incremental regression cohort differs')
    cases = [(a,1,1,'decode','openjpeg') for a in boca]
    cases += [(a,s,w,'decode','openjpeg') for a in tok for w in (1,8) for s in (0,1)]
    cases += [(a,0,8,'decode','openjpeg') for a in boca]
    cases += [(a,0,1,'decode','emuella') for a in boca]
    cases += [(a,s,1,'encode','emuella') for a in pan for s in (0,1)]
    return cases


def contrasts(assets, phase, study="kernel"):
    if study == "incremental":
        return incremental_contrasts(assets, phase)
    if study == "entropy":
        return entropy_contrasts(assets, phase)
    if phase in ("describe", "primary"):
        raise ValueError("phase requires the entropy study")
    if study not in ("kernel", "parallel"):
        raise ValueError("unknown finite study")
    if phase == 'spacenet':
        if len(assets)!=12 or any(a.get('role')!='development' or 'Khartoum' in a['id'] for a in assets):
            raise ValueError('SpaceNet regression requires twelve development chips, excluding Khartoum')
        if study == 'parallel':
            selected = [a for a in assets if any(a['id'].endswith(suffix) for suffix in ('AOI_2_Vegas_img1454','AOI_3_Paris_img235','AOI_4_Shanghai_img1196'))]
            if len(selected) != 3:
                raise ValueError('fixed three-AOI parallel regression cohort differs')
            return [(a,s,w,'encode','emuella') for a in selected for s in (0,1) for w in (1,8)]
        return [(a,s,1,'encode','emuella') for a in assets for s in (0,1)]
    selected = assets
    if phase == 'screen':
        selected = [a for a in assets if a['id'].startswith('94_') and a['product'] in ('PAN16', 'RGB8', 'MS16')]
    if len(selected) != (3 if phase == 'screen' else 9):
        raise ValueError('fixed cohort differs')
    cases = [(a, s, w, 'encode', 'emuella') for a in selected for s in (0, 1)
             for w in ((1,) if phase == 'screen' and study == 'kernel' else (1, 8))]
    if phase == 'confirm':
        # Targeted unchanged-decoder regression: every development product/style,
        # at one/eight workers on the same OpenJPEG-origin stream.
        cases += [(a, s, w, 'decode', 'openjpeg') for a in selected
                  if a['id'].startswith('94_') and a['product'] in ('PAN16', 'RGB8', 'MS16')
                  for s in (0, 1) for w in (1, 8)]
    return cases


def observation_name(study, round_id, case_id, style, workers, operation, origin, arm):
    origin_suffix = '-'+origin if study in ('entropy','incremental') else ''
    return f"r{round_id:02}-{case_id}-s{style}-w{workers}-{operation}{origin_suffix}-{arm}"


def measure(args):
    budget = None
    if args.study == "incremental":
        if args.budget is None:
            raise ValueError("incremental observations require the shared finite budget ledger")
        budget = refresh.module("incremental_budget", "mq-d2-budget.py").Budget(args.budget)
    owner = refresh.classic.clean_source(refresh.ROOT)
    builds = {arm: refresh.bind(getattr(args, arm)) for arm in ARMS}
    if any(b.get('sampling') or b.get('execution_diagnostics') or b.get('allocation_diagnostics') for b in builds.values()):
        raise ValueError('diagnostic builds cannot supply treatment timings')
    if builds['reference']['codec']['source_revision'] != args.reference_revision:
        raise ValueError('reference revision differs from declared baseline')
    if args.study in ('parallel','entropy','incremental') and any(b.get('encoder_backend') != 'default' for b in builds.values()):
        raise ValueError('treatment requires packed-default dispatch with selector unset in both arms')
    if builds['packed'].get('encoder_backend') not in ('packed', 'default'):
        raise ValueError('candidate build forces the reference')
    for field in ('rustc','openjpeg','libraries','environment','cargo_configs'):
        if builds['reference'][field] != builds['packed'][field]:
            raise ValueError('matched build configuration differs: '+field)
    worker_source=lambda b: {p:d for p,d in b['benchmark']['source_files_sha256'].items()
                            if p.startswith(('workers/','src/','.cargo/')) or p in ('Cargo.toml','Cargo.lock','build.rs','rust-toolchain.toml')}
    if worker_source(builds['reference']) != worker_source(builds['packed']):
        raise ValueError('treatment workers must have identical benchmark source')
    selected = assets(args.prepared,args.phase)
    cases = contrasts(selected, args.phase, args.study)
    store = args.prepared.parent.resolve()
    if args.output.parent.resolve() != store or args.streams.parent.resolve() != store:
        raise ValueError('outputs and reference stream owner must remain in the approved store')
    cpus = list(range(8))
    machine = refresh.cpu_identity(cpus)
    notice = store / ('source/LICENSE.md' if args.phase=='spacenet' else 'source/LICENSE.txt')
    expected_notice = ('ebeaa5a46058cce9e893f42d601e1155bae27aa538f2854c79c626e297356c35' if args.phase=='spacenet'
                       else 'f627ad059128fa5246a21e25759c1d33e35c4bb6287d636c4b970f7df57e7eba')
    if sha(notice) != expected_notice:
        raise ValueError('reviewed notice differs')
    stream_path=lambda a,s,origin: args.streams/'streams'/(f"{a['id']}-style{s}.j2k" if args.phase=='spacenet' else f"{a['id']}-{origin}-s{s}.j2k")
    stream_hashes = {str(stream_path(a,s,origin)): sha(stream_path(a,s,origin))
                     for a,s,w,op,origin in cases}
    args.output.mkdir(exist_ok=False)
    (args.output/'LICENSE.txt').write_bytes(notice.read_bytes())
    attribution=('SpaceNet Dataset, SpaceNet Partners and DigitalGlobe imagery; Van Etten, Lindenbaum and Bacastow (2018). '
                 if args.phase=='spacenet' else 'RarePlanes Dataset, June 2020. J. Shermeyer et al.; In-Q-Tel - CosmiQ Works and AI.Reverie. ')
    (args.output/'NOTICE.txt').write_text(attribution+'CC BY-SA 4.0. Local lossless encoder observations; unchanged inputs and reference streams remain with the source lineage. No imagery redistribution.\n')
    rounds = 3 if args.phase in ('screen','describe') else 20
    manifest = dict(study=args.study,phase=args.phase,rounds=rounds,builds=builds,owner=owner,
                    machine=machine,assets=selected,prepared_sha256=sha(args.prepared/'prepared.json'),
                    reference_streams=stream_hashes,boundary=refresh.BOUNDARY,
                    timeout_seconds=120,address_space_bytes=refresh.classic.BUDGET,
                    working_bytes=refresh.classic.WORKING,output_bytes=refresh.classic.OUTPUT,
                    warmups=0,samples_per_process=1,order='adjacent alternating AB/BA',
                    contrasts=[dict(case_id=a['id'],style=s,workers=w,operation=op,origin=o) for a,s,w,op,o in cases],
                    started_utc=time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime()))
    write(args.output/'manifest.json',manifest)
    rows=[]
    for round_id in range(rounds):
        for a,style,workers,operation,origin in cases:
            for arm in ARMS if round_id % 2 == 0 else ARMS[::-1]:
                name=observation_name(args.study,round_id,a['id'],style,workers,operation,origin,arm)
                request=refresh.make_request(a,args.prepared,args.streams,origin,'emuella',style,workers,'prepare',round_id)
                request.update(operation=operation,stream_path=str(stream_path(a,style,origin)),stream_sha256=sha(stream_path(a,style,origin)))
                if budget is not None:
                    budget.before_call()
                result=refresh.run_process(builds[arm]['binary'],request,args.output/name,cpus[:workers])
                rows.append(dict(case_id=a['id'],style=style,workers=workers,operation=operation,origin=origin,round=round_id,arm=arm,result=result,path=name))
                # Preserve each completed observation even if the driver later fails.
                write(args.output/(name+'-receipt.json'),rows[-1])
                print(name,result['status'],flush=True)
    for arm in ARMS:
        if refresh.bind(getattr(args,arm)) != builds[arm]:
            raise ValueError('build changed during measurement')
    if refresh.classic.clean_source(refresh.ROOT) != owner or assets(args.prepared,args.phase) != selected:
        raise ValueError('runner or inputs changed during measurement')
    if any(sha(path)!=digest for path,digest in stream_hashes.items()):
        raise ValueError('reference stream changed')
    end_machine=refresh.cpu_identity(cpus)
    complete=all(r['result']['status']==0 for r in rows)
    write(args.output/'measurement.json',dict(manifest_sha256=sha(args.output/'manifest.json'),
        rows=rows,complete=complete,end_machine=end_machine,finished_utc=time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime())))


def validate_rows(manifest, rows):
    cases=manifest['contrasts']; rounds=manifest['rounds']
    if manifest['phase'] not in ('screen','describe','primary','confirm','spacenet') or rounds != (3 if manifest['phase'] in ('screen','describe') else 20):
        raise ValueError('phase and finite round budget differ')
    frozen=[dict(case_id=a['id'],style=s,workers=w,operation=op,origin=o)
            for a,s,w,op,o in contrasts(manifest['assets'],manifest['phase'],manifest.get('study','kernel'))]
    if cases != frozen:
        raise ValueError('declared contrasts differ from the fixed cohort')
    keys=lambda r: (r['case_id'],r['style'],r['workers'],r['operation'],r['origin'])
    expected={(keys(c),n,a) for c in cases for n in range(rounds) for a in ARMS}
    observed=[(keys(r),r['round'],r['arm']) for r in rows]
    if len(observed)!=len(set(observed)) or set(observed)!=expected:
        raise ValueError('missing, duplicate or unexpected observations')
    return keys


def analyse(args):
    manifest=json.loads((args.output/'manifest.json').read_text())
    measurement=json.loads((args.output/'measurement.json').read_text())
    if measurement['manifest_sha256'] != sha(args.output/'manifest.json'):
        raise ValueError('manifest changed')
    rows=measurement['rows']; cases=manifest['contrasts']
    keys=validate_rows(manifest,rows)
    if measurement['complete'] != all(r['result']['status']==0 for r in rows):
        raise ValueError('completion claim differs from retained observations')
    comparisons=[]
    for c in cases:
        subset=[r for r in rows if keys(r)==keys(c)]
        entry=dict(c)
        if any(r['result']['status']!=0 for r in subset):
            entry.update(verdict='invalid_coverage',failures=[r for r in subset if r['result']['status']!=0])
        else:
            arms={a:[r['result'] for r in subset if r['arm']==a] for a in ARMS}
            samples={a:[r['observation']['samples_ns'][0] for r in arm] for a,arm in arms.items()}
            if manifest['phase'] in ('screen','describe'):
                entry.update(verdict='development_screen_only' if manifest['phase']=='screen' else 'eight_worker_description_only',
                             descriptive_ratio=statistics.mean(samples['packed'])/statistics.mean(samples['reference']))
            else:
                entry.update(json.loads(subprocess.check_output([str(args.estimator)],text=True,
                    input=json.dumps(dict(baseline=samples['reference'],candidate=samples['packed'])))))
            entry['arms']={a:dict(mean_ms=statistics.mean(samples[a])/1e6,samples_ns=samples[a],
                stream_bytes=sorted({r['observation']['stream_bytes'] for r in arm}),
                maximum_process_rss_bytes=max(r['process_peak_rss_bytes'] for r in arm),
                mean_process_cpu_seconds=statistics.mean(r['process_cpu_seconds'] for r in arm)) for a,arm in arms.items()}
        comparisons.append(entry)
    write(args.output/'report.json',dict(phase=manifest['phase'],complete=measurement['complete'],
        manifest_sha256=sha(args.output/'manifest.json'),measurement_sha256=sha(args.output/'measurement.json'),
        estimator_sha256=None if manifest['phase'] in ('screen','describe') else sha(args.estimator),comparisons=comparisons,
        interpretation=('Descriptive three-round means only; no confidence interval or promotion claim. ' if manifest['phase'] in ('screen','describe') else 'Candidate/reference minus one; conservative 99% per-case intervals, 5% practical gate. ') + 'Legacy reference/packed arm names identify baseline/candidate treatments, not encoder selectors. RSS/CPU are whole-process metrics. No outlier removal.'))
    print(json.dumps([{k:v for k,v in c.items() if k!='arms'} for c in comparisons],indent=2))


def diagnose(args):
    """Finite attribution/resource/scaling processes; never headline inference."""
    kind = args.command
    owner = refresh.classic.clean_source(refresh.ROOT)
    build = refresh.bind(args.build)
    if build.get('sampling') or build.get('encoder_backend') != 'default':
        raise ValueError('requires packed-default dispatch without sampling')
    if bool(build.get('execution_diagnostics')) != (kind == 'diagnose') or bool(build.get('allocation_diagnostics')) != (kind == 'resources'):
        raise ValueError('observation mode differs from build instrumentation')
    selected = assets(args.prepared, 'screen')
    if kind == 'diagnose':
        selected = [a for a in selected if a['id'].startswith('94_') and a['product'] in ('PAN16', 'RGB8', 'MS16')]
    if len(selected) != (3 if kind == 'diagnose' else 9):
        raise ValueError('fixed observation cohort differs')
    store = args.prepared.parent.resolve()
    if args.output.parent.resolve() != store or args.streams.parent.resolve() != store:
        raise ValueError('diagnostics and streams must stay in the approved input store')
    notice = store/'source/LICENSE.txt'
    if sha(notice) != 'f627ad059128fa5246a21e25759c1d33e35c4bb6287d636c4b970f7df57e7eba':
        raise ValueError('reviewed notice differs')
    worker_counts = (8,1) if kind == 'diagnose' else ((1,2,4,8) if kind == 'resources' else (2,4))
    rounds = 3 if kind == 'scaling' else 1
    requests = [refresh.make_request(a,args.prepared,args.streams,'emuella','emuella',style,workers,'encode',round_id)
                for round_id in range(rounds) for workers in worker_counts for a in selected for style in (0,1)]
    stream_hashes = {r['stream_path']:r['stream_sha256'] for r in requests}
    args.output.mkdir(exist_ok=False)
    (args.output/'LICENSE.txt').write_bytes(notice.read_bytes())
    (args.output/'NOTICE.txt').write_text('RarePlanes Dataset, June 2020. J. Shermeyer et al.; In-Q-Tel - CosmiQ Works and AI.Reverie. CC BY-SA 4.0. Local execution observations; unchanged input and stream lineage stays in this store. No imagery redistribution.\n')
    manifest = dict(kind=kind,arm=args.arm,build=build,owner=owner,
                    requests=requests,prepared_sha256=sha(args.prepared/'prepared.json'),
                    machine=refresh.cpu_identity(list(range(8))),calls=len(requests),rounds=rounds,
                    attribution_campaign_cap=36,headline_samples=False)
    write(args.output/'manifest.json',manifest)
    rows=[]
    for request in requests:
        name=f"{request['case_id']}-s{request['style']}-w{request['workers']}-r{request['round']}"
        result=refresh.run_process(build['binary'],request,args.output/name,list(range(request['workers'])),execution_diagnostics=kind == 'diagnose',allocation_diagnostics=kind == 'resources')
        rows.append(dict(request=request,result=result,path=name))
        write(args.output/(name+'-receipt.json'),rows[-1])
        print(name,result['status'],flush=True)
    if refresh.bind(args.build)!=build or refresh.classic.clean_source(refresh.ROOT)!=owner:
        raise ValueError('diagnostic source/build changed')
    if any(sha(path)!=digest for path,digest in stream_hashes.items()) or sha(args.prepared/'prepared.json')!=manifest['prepared_sha256']:
        raise ValueError('diagnostic input/stream identity changed')
    write(args.output/'measurement.json',dict(manifest_sha256=sha(args.output/'manifest.json'),rows=rows,
          complete=all(r['result']['status']==0 for r in rows),end_machine=refresh.cpu_identity(list(range(8)))))


def main():
    p=argparse.ArgumentParser(description=__doc__); sub=p.add_subparsers(dest='command',required=True)
    m=sub.add_parser('measure'); m.add_argument('--phase',choices=('screen','describe','primary','confirm','spacenet'),required=True)
    for name in ('reference','packed','prepared','streams','output'):
        m.add_argument('--'+name,type=Path,required=True)
    m.add_argument('--budget',type=Path); m.add_argument('--reference-revision',required=True); m.add_argument('--study',choices=('kernel','parallel','entropy','incremental'),default='kernel')
    a=sub.add_parser('analyse'); a.add_argument('--output',type=Path,required=True); a.add_argument('--estimator',type=Path,required=True)
    for command in ('diagnose','resources','scaling'):
        d=sub.add_parser(command); d.add_argument('--arm',choices=('baseline','selected','attribution'),required=True)
        for name in ('build','prepared','streams','output'):
            d.add_argument('--'+name,type=Path,required=True)
    args=p.parse_args()
    for key,value in vars(args).items():
        if isinstance(value,Path):setattr(args,key,value.resolve())
    {'measure':measure,'analyse':analyse,'diagnose':diagnose,'resources':diagnose,'scaling':diagnose}[args.command](args)


if __name__=='__main__':main()
