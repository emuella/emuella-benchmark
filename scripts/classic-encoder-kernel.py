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


def contrasts(assets, phase):
    selected = assets
    if phase == 'screen':
        selected = [a for a in assets if a['id'].startswith('94_') and a['product'] in ('PAN16', 'RGB8', 'MS16')]
    if len(selected) != (3 if phase == 'screen' else 9):
        raise ValueError('fixed cohort differs')
    cases = [(a, s, w, 'encode', 'emuella') for a in selected for s in (0, 1)
             for w in ((1,) if phase == 'screen' else (1, 8))]
    if phase == 'confirm':
        # Targeted unchanged-decoder regression: every development product/style,
        # at one/eight workers on the same OpenJPEG-origin stream.
        cases += [(a, s, w, 'decode', 'openjpeg') for a in selected
                  if a['id'].startswith('94_') and a['product'] in ('PAN16', 'RGB8', 'MS16')
                  for s in (0, 1) for w in (1, 8)]
    return cases


def measure(args):
    owner = refresh.classic.clean_source(refresh.ROOT)
    builds = {arm: refresh.bind(getattr(args, arm)) for arm in ARMS}
    if any(b.get('sampling') for b in builds.values()):
        raise ValueError('diagnostic builds cannot supply treatment timings')
    if builds['reference']['codec']['source_revision'] != args.reference_revision:
        raise ValueError('reference revision differs from declared baseline')
    if builds['packed'].get('encoder_backend') not in ('packed', 'default'):
        raise ValueError('candidate build forces the reference')
    for field in ('rustc','openjpeg','libraries','environment','cargo_configs'):
        if builds['reference'][field] != builds['packed'][field]:
            raise ValueError('matched build configuration differs: '+field)
    if builds['reference']['benchmark']['source_files_sha256'] != builds['packed']['benchmark']['source_files_sha256']:
        raise ValueError('treatment workers must have identical benchmark source')
    selected = refresh.classic.assets(args.prepared)
    cases = contrasts(selected, args.phase)
    store = args.prepared.parent.resolve()
    if args.output.parent.resolve() != store or args.streams.parent.resolve() != store:
        raise ValueError('outputs and reference stream owner must remain in the approved store')
    cpus = list(range(8))
    machine = refresh.cpu_identity(cpus)
    notice = store / 'source/LICENSE.txt'
    if sha(notice) != 'f627ad059128fa5246a21e25759c1d33e35c4bb6287d636c4b970f7df57e7eba':
        raise ValueError('reviewed notice differs')
    stream_hashes = {str(args.streams/'streams'/f"{a['id']}-{origin}-s{s}.j2k"):
                     sha(args.streams/'streams'/f"{a['id']}-{origin}-s{s}.j2k")
                     for a,s,w,op,origin in cases}
    args.output.mkdir(exist_ok=False)
    (args.output/'LICENSE.txt').write_bytes(notice.read_bytes())
    (args.output/'NOTICE.txt').write_text('RarePlanes Dataset, June 2020. J. Shermeyer et al.; In-Q-Tel - CosmiQ Works and AI.Reverie. CC BY-SA 4.0. Local lossless encoder observations; unchanged inputs and reference streams remain with the source lineage. No imagery redistribution.\n')
    rounds = 3 if args.phase == 'screen' else 20
    manifest = dict(phase=args.phase,rounds=rounds,builds=builds,owner=owner,
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
                name=f"r{round_id:02}-{a['id']}-s{style}-w{workers}-{operation}-{arm}"
                request=refresh.make_request(a,args.prepared,args.streams,origin,'emuella',style,workers,operation,round_id)
                result=refresh.run_process(builds[arm]['binary'],request,args.output/name,cpus[:workers])
                rows.append(dict(case_id=a['id'],style=style,workers=workers,operation=operation,origin=origin,round=round_id,arm=arm,result=result,path=name))
                # Preserve each completed observation even if the driver later fails.
                write(args.output/(name+'-receipt.json'),rows[-1])
                print(name,result['status'],flush=True)
    for arm in ARMS:
        if refresh.bind(getattr(args,arm)) != builds[arm]:
            raise ValueError('build changed during measurement')
    if refresh.classic.clean_source(refresh.ROOT) != owner or refresh.classic.assets(args.prepared) != selected:
        raise ValueError('runner or inputs changed during measurement')
    if any(sha(path)!=digest for path,digest in stream_hashes.items()):
        raise ValueError('reference stream changed')
    end_machine=refresh.cpu_identity(cpus)
    complete=all(r['result']['status']==0 for r in rows)
    write(args.output/'measurement.json',dict(manifest_sha256=sha(args.output/'manifest.json'),
        rows=rows,complete=complete,end_machine=end_machine,finished_utc=time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime())))


def validate_rows(manifest, rows):
    cases=manifest['contrasts']; rounds=manifest['rounds']
    if manifest['phase'] not in ('screen','confirm') or rounds != (3 if manifest['phase']=='screen' else 20):
        raise ValueError('phase and finite round budget differ')
    frozen=[dict(case_id=a['id'],style=s,workers=w,operation=op,origin=o)
            for a,s,w,op,o in contrasts(manifest['assets'],manifest['phase'])]
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
            entry.update(json.loads(subprocess.check_output([str(args.estimator)],text=True,
                input=json.dumps(dict(baseline=samples['reference'],candidate=samples['packed'])))))
            entry['arms']={a:dict(mean_ms=statistics.mean(samples[a])/1e6,samples_ns=samples[a],
                stream_bytes=sorted({r['observation']['stream_bytes'] for r in arm}),
                maximum_process_rss_bytes=max(r['process_peak_rss_bytes'] for r in arm),
                mean_process_cpu_seconds=statistics.mean(r['process_cpu_seconds'] for r in arm)) for a,arm in arms.items()}
        comparisons.append(entry)
    write(args.output/'report.json',dict(phase=manifest['phase'],complete=measurement['complete'],
        manifest_sha256=sha(args.output/'manifest.json'),measurement_sha256=sha(args.output/'measurement.json'),
        estimator_sha256=sha(args.estimator),comparisons=comparisons,
        interpretation='Packed/reference minus one; conservative 99% per-case intervals, 5% practical gate. Three-round screens cannot promote. RSS/CPU are whole-process metrics. No outlier removal.'))
    print(json.dumps([{k:v for k,v in c.items() if k!='arms'} for c in comparisons],indent=2))


def main():
    p=argparse.ArgumentParser(description=__doc__); sub=p.add_subparsers(dest='command',required=True)
    m=sub.add_parser('measure'); m.add_argument('--phase',choices=('screen','confirm'),required=True)
    for name in ('reference','packed','prepared','streams','output'):
        m.add_argument('--'+name,type=Path,required=True)
    m.add_argument('--reference-revision',required=True)
    a=sub.add_parser('analyse'); a.add_argument('--output',type=Path,required=True); a.add_argument('--estimator',type=Path,required=True)
    args=p.parse_args()
    for key,value in vars(args).items():
        if isinstance(value,Path):setattr(args,key,value.resolve())
    (measure if args.command=='measure' else analyse)(args)


if __name__=='__main__':main()
