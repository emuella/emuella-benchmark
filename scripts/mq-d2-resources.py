#!/usr/bin/env python3
"""Finite separate-allocation resource observations for fixed codec treatments."""
import argparse
import importlib.util
import json
from pathlib import Path
import time

SPEC = importlib.util.spec_from_file_location('mq_d2_treatments', Path(__file__).with_name('classic-encoder-kernel.py'))
kernel = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(kernel)
refresh = kernel.refresh


def cases(assets, phase, study='incremental'):
    if study == 'front-end':
        if phase == 'spacenet':
            selected = kernel.front_end_contrasts(assets, phase)
        elif phase == 'primary':
            selected = kernel.front_end_contrasts(assets, 'primary') + kernel.front_end_contrasts(assets, 'screen')
        elif phase == 'confirm':
            selected = [c for c in kernel.front_end_contrasts(assets, phase) if c[3] == 'encode']
        else:
            raise ValueError('unknown front-end resource phase')
        products = {c[0]['id']:c[0] for c in selected}
        return [(a,s,w,'encode','emuella') for a in products.values() for s in (0,1) for w in (1,2,4,8)]
    if study != 'incremental':
        raise ValueError('unknown finite resource study')
    if phase == 'spacenet':
        chips = {c[0]['id']: c[0] for c in kernel.incremental_contrasts(assets, phase)}
        return [(a,s,w,'decode','emuella') for a in chips.values() for s in (0,1) for w in (1,2,4,8)]
    primary = kernel.incremental_contrasts(assets, 'primary')
    if phase == 'primary':
        return [(c[0],s,w,'decode',o) for c in primary for s in (0,1)
                for w in (1,2,4,8) for o in ('openjpeg','emuella')]
    if phase not in ('encode','confirm'):
        raise ValueError('unknown finite resource phase')
    selected = [a for a in assets if (a['id'].startswith('94_') and a['product']=='PAN16')
                or (phase=='confirm' and a['id'].startswith('105_') and a['product']=='RGB8')]
    if len(selected) != (1 if phase=='encode' else 2):
        raise ValueError('resource cohort differs')
    return [(a,s,w,'encode' if phase=='encode' else 'decode',o) for a in selected
            for s in (0,1) for w in (1,2,4,8)
            for o in (('emuella',) if phase=='encode' else ('openjpeg','emuella'))]


def resource_observation(observation, request):
    """Separate completed measurements from absolute resource eligibility."""
    diagnostic = observation.get('allocation_diagnostic')
    if not isinstance(diagnostic, dict) or observation.get('samples_ns') != []:
        raise ValueError('allocation-only observations required')
    values = dict(peak_bytes=diagnostic.get('allocation_peak_additional_requested_bytes'),
                  allocation_requests=diagnostic.get('successful_allocation_or_reallocation_requests'),
                  working_bytes=observation.get('working_bytes'),
                  output_capacity=observation.get('output_capacity'),
                  output_capacity_limit=observation.get('output_capacity_limit'))
    if any(type(v) is not int or v < 0 for v in values.values()):
        raise ValueError('resource bounds or allocation observations missing')
    gates = dict(peak_within_query=values['peak_bytes'] <= values['working_bytes'],
                 peak_within_working_limit=values['peak_bytes'] <= request['max_working_bytes'],
                 query_within_working_limit=values['working_bytes'] <= request['max_working_bytes'],
                 output_within_query=values['output_capacity'] <= values['output_capacity_limit'],
                 output_within_limit=values['output_capacity'] <= request['max_output_bytes'])
    return dict(**values, gates=gates, eligible=all(gates.values()))


def run(args):
    budget = kernel.observation_budget(args.study, args.budget)
    owner = refresh.classic.clean_source(refresh.ROOT)
    builds = {arm: refresh.bind(getattr(args,arm)) for arm in kernel.ARMS}
    for b in builds.values():
        if not b.get('allocation_diagnostics') or b.get('execution_diagnostics') or b.get('sampling') or b.get('encoder_backend')!='default':
            raise ValueError('resource checks require separate allocation-only packed-default builds')
    if args.study == 'front-end' and any(b.get('scheduling_window') != 'default' for b in builds.values()):
        raise ValueError('front-end resources require the unchanged scheduling window')
    if builds['reference']['codec']['source_revision'] != args.reference_revision:
        raise ValueError('reference source differs')
    if builds['packed']['codec']['source_revision'] != args.candidate_revision:
        raise ValueError('candidate source differs')
    for field in ('benchmark','rustc','openjpeg','libraries','environment','cargo_configs'):
        if builds['reference'][field] != builds['packed'][field]:
            raise ValueError('resource build treatment differs: '+field)
    selected = kernel.assets(args.prepared, 'spacenet' if args.phase=='spacenet' else 'primary')
    contrasts = cases(selected,args.phase,args.study)
    store = args.prepared.parent.resolve()
    if args.streams.parent.resolve()!=store or args.output.parent.resolve()!=store:
        raise ValueError('resource evidence must remain in its approved input store')
    sn = args.phase=='spacenet'
    notice = store/('source/LICENSE.md' if sn else 'source/LICENSE.txt')
    expected = 'ebeaa5a46058cce9e893f42d601e1155bae27aa538f2854c79c626e297356c35' if sn else 'f627ad059128fa5246a21e25759c1d33e35c4bb6287d636c4b970f7df57e7eba'
    if refresh.sha(notice)!=expected:
        raise ValueError('reviewed notice differs')
    requests = []
    for a,s,w,op,o in contrasts:
        r=refresh.make_request(a,args.prepared,args.streams,o,'emuella',s,w,'prepare',0)
        stream=args.streams/'streams'/(f"{a['id']}-style{s}.j2k" if sn else f"{a['id']}-{o}-s{s}.j2k")
        r.update(operation=op,stream_path=str(stream),stream_sha256=refresh.sha(stream))
        requests.append((r,o))
    args.output.mkdir(exist_ok=False)
    (args.output/'LICENSE.txt').write_bytes(notice.read_bytes())
    attribution = ('SpaceNet Dataset, SpaceNet Partners and DigitalGlobe imagery; Van Etten, Lindenbaum and Bacastow (2018).' if sn else 'RarePlanes Dataset, June 2020. J. Shermeyer et al.; In-Q-Tel - CosmiQ Works and AI.Reverie.')
    (args.output/'NOTICE.txt').write_text(attribution+' CC BY-SA 4.0. Local allocation/correctness observations; source lineage and unchanged payloads remain in this store. No imagery redistribution.\n')
    manifest = dict(study=args.study,phase=args.phase,builds=builds,owner=owner,requests=requests,
                    prepared_sha256=refresh.sha(args.prepared/'prepared.json'),
                    machine=refresh.cpu_identity(list(range(8))),calls=len(requests)*2,
                    headline_samples=False,started_utc=time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime()))
    refresh.write(args.output/'manifest.json',manifest)
    rows=[]
    for r,o in requests:
        for arm in kernel.ARMS:
            name=f"{r['case_id']}-s{r['style']}-w{r['workers']}-{r['operation']}-{o}-{arm}"
            budget.before_call()
            result=refresh.run_process(builds[arm]['binary'],r,args.output/name,list(range(r['workers'])),allocation_diagnostics=True)
            row=dict(request=r,origin=o,arm=arm,result=result,path=name)
            if args.study == 'front-end' and result['status'] == 0:
                try:
                    row['resources'] = resource_observation(result['observation'],r)
                except ValueError as error:
                    result.update(status='invalid_response', reason=str(error))
            rows.append(row)
            refresh.write(args.output/(name+'-receipt.json'),row)
            print(name,result['status'],flush=True)
    if refresh.classic.clean_source(refresh.ROOT)!=owner or kernel.assets(args.prepared,'spacenet' if sn else 'primary')!=selected:
        raise ValueError('source/input identities changed')
    for r,_ in requests:
        if refresh.sha(r['stream_path'])!=r['stream_sha256']:
            raise ValueError('reference stream changed')
    for arm in kernel.ARMS:
        if refresh.bind(getattr(args,arm))!=builds[arm]:
            raise ValueError('build changed')
    measurement = dict(manifest_sha256=refresh.sha(args.output/'manifest.json'),rows=rows,complete=all(r['result']['status']==0 for r in rows))
    if args.study == 'front-end':
        measurement['resource_eligible'] = all(r.get('resources',{}).get('eligible',False) for r in rows)
    refresh.write(args.output/'measurement.json',measurement)


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--study',choices=('incremental','front-end'),default='incremental')
    p.add_argument('--phase',choices=('primary','encode','confirm','spacenet'),required=True)
    for name in ('reference','packed','prepared','streams','output','budget'):
        p.add_argument('--'+name,type=lambda value:Path(value).resolve(),required=True)
    p.add_argument('--reference-revision',required=True)
    p.add_argument('--candidate-revision',required=True)
    run(p.parse_args())


if __name__=='__main__':main()
