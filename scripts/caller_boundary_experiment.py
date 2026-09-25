#!/usr/bin/env python3
"""One prospective caller-boundary experiment; no production qualification."""
import argparse
import copy
import fcntl
import hashlib
import json
import math
import os
from pathlib import Path
import signal
import subprocess
import sys
import time
import tomllib

sys.path.insert(0, str(Path(__file__).resolve().parent))
import finite_confirmation_live as live
import finite_confirmation_report as retained
import precision_feasibility_analysis as analysis

refresh, stability, panels = live.refresh, live.stability, live.panels
sha, write, absolute = live.sha, live.write, live.absolute
SCHEMA = 'classic-forward53-caller-boundary/v1'
A = 'a7576ad03486e097ac923b8e49cac39a1cbef5d2'
B = '4f5bfb39f02e043c9a1f594a8159d3cf86d52c3f'
B_TREE = '259066112bda675e67a8d3eab3dbf9088d18fe91'
WORKER = '0db375523ead4ff5113d7e73a77a39b04cff6644'
RAW = 'aaf064a2d6b302d839e7f3c13b99e1344ba749fed53be6daf64f8a6c4c67bfe7'
STREAM = '5686eb89ffbf5152d5572441347ec388ae107d0e6790086a817a5529b702843c'
ORDERS = ('ABC', 'CBA', 'ACB', 'BCA', 'BAC', 'CAB') * 6 + ('ABC', 'CBA', 'ACB', 'BCA')
CAPS = dict(started_calls=126, wall_seconds=2700, evidence_bytes=2*1024**3, build_bytes=30*1024**3)
PREREQUISITES = {'source_correctness', 'source_review', 'acquisition_review', 'independent_decode', 'build_provenance', 'compiled_code'}


def schedule():
    rows = []
    for stage in ('preflight', 'allocation', 'ordinary'):
        for round_id, order in enumerate(ORDERS if stage == 'ordinary' else ('ABC',)):
            for position, arm in enumerate(order):
                index = len(rows)
                rows.append(dict(index=index, call_id=f'{stage}-{index:04}', stage=stage, arm=arm,
                    round=round_id, block=round_id//6 if stage == 'ordinary' else None,
                    position=position, order=order, endpoint_id='boca-rgb8-style0-one-worker'))
    return rows


def order_summary():
    return dict(round_orders=list(ORDERS),
        positions={a:[sum(o[p] == a for o in ORDERS) for p in range(3)] for a in 'ABC'},
        relative_pair_order={a+b:sum(o.index(a) < o.index(b) for o in ORDERS) for a,b in (('A','B'),('A','C'),('B','C'))},
        interpretation='Three-arm extension: pairs are not always adjacent; small position imbalance retained. The unchanged independent-means comparator uses each arm once per contrast; contrasts share samples, with no joint 99% coverage claim.')


def budget_issues(value, before_start=False):
    issues = []
    for key, cap in CAPS.items():
        observed = value.get(key)
        if (type(observed) not in (int, float) or not math.isfinite(observed) or observed < 0
                or key != 'wall_seconds' and type(observed) is not int):
            issues.append(key+' missing or invalid'); continue
        headroom = dict(started_calls=1, wall_seconds=150, evidence_bytes=1024**2, build_bytes=0)[key] if before_start else 0
        if observed+headroom > cap:
            issues.append(key+' cap or receipt headroom exhausted')
    return issues


def validate_request(request):
    expected = dict(codec='emuella', operation='encode', round=0, width=5577, height=5036,
        components=3, bits=8, layout='interleaved', style=0, workers=1,
        raw_sha256=RAW, stream_sha256=STREAM,
        max_working_bytes=refresh.classic.WORKING, max_output_bytes=refresh.classic.OUTPUT)
    if set(request) != set(expected) | {'case_id', 'raw_path', 'stream_path'} or any(request[k] != v for k,v in expected.items()):
        raise ValueError('exact full Boca one-worker style-zero request required')
    if not request['case_id'].startswith('106_') or not request['case_id'].endswith('RGB8'):
        raise ValueError('Boca RGB8 catalogue identity required')


def roots(config):
    scratch = absolute(config['build_root'])
    marker = scratch/'.emuella-campaign-scratch.json'
    if marker.is_symlink() or json.loads(marker.read_text()) != dict(kind='emuella-campaign-scratch', schema_version=1, slug='classic-forward53-caller-boundary'):
        raise ValueError('registered caller-boundary scratch required')
    store, output = absolute(config['store_root']), absolute(config['output'])
    values = [absolute(p) for p in config['evidence_roots']]
    if output not in values or len(set(values)) != len(values):
        raise ValueError('distinct evidence roots including output required')
    inputs = [absolute(config['request'][k+'_path']) for k in ('raw','stream')]
    if any(not p.is_relative_to(store) for p in [*values, *inputs]):
        raise ValueError('inputs and evidence must remain in approved store')
    if any(a == b or a.is_relative_to(b) or b.is_relative_to(a) for i,a in enumerate(values) for b in values[i+1:]):
        raise ValueError('overlapping evidence roots')
    if any(p == r or p.is_relative_to(r) for p in inputs for r in values):
        raise ValueError('new evidence budget cannot include existing protected inputs')
    return values


def pinned(record):
    path = absolute(record['path'])
    if sha(path) != record['sha256']:
        raise ValueError('pinned evidence differs: '+str(path))
    return path


def source_treatment(config):
    source = json.loads(pinned(config['source_treatment']).read_text())
    if (source.get('schema') != SCHEMA+'/source' or source.get('A') != A or source.get('B') != B
            or source.get('B_tree') != B_TREE or source.get('intervention') != 'owning-helper-with-serial-bypass'
            or type(source.get('inline_never')) is not bool or source.get('production_enabled') is not False):
        raise ValueError('declared source treatment differs')
    for arm in 'ABC':
        checkout = absolute(config['codec_sources'][arm])
        identity = refresh.classic.clean_source(checkout)
        if identity['source_revision'] != source[arm] or identity['source_tree'] != source[arm+'_tree']:
            raise ValueError('clean treatment source differs: '+arm)
    diff = subprocess.check_output(['git','-C',config['codec_sources']['C'],'diff', '--no-ext-diff', '--no-textconv',
        '--binary', '--full-index', '--no-renames', '--no-color', '--diff-algorithm=myers', '--no-indent-heuristic',
        '--unified=3', '--src-prefix=a/', '--dst-prefix=b/', B, source['C'], '--'])
    if hashlib.sha256(diff).hexdigest() != source['B_to_C_diff_sha256']:
        raise ValueError('complete reviewed B-to-C source diff differs')
    return source


def builds(config):
    source = source_treatment(config)
    worker = refresh.classic.clean_source(absolute(config['worker_source']))
    if worker['source_revision'] != WORKER or set(config['arms']) != set('ABC'):
        raise ValueError('unchanged worker and exactly three arms required')
    result = {}
    for arm in 'ABC':
        if set(config['arms'][arm]) != {'ordinary','resource'}:
            raise ValueError('separate ordinary and allocation binaries required')
        result[arm] = {}
        for mode, location in config['arms'][arm].items():
            path = absolute(location); build = refresh.bind(path)
            if build['benchmark'] != worker or build['codec'] != refresh.classic.clean_source(absolute(config['codec_sources'][arm])):
                raise ValueError('build worker/codec inventory differs')
            if (any(build.get(k) for k in ('sampling','execution_diagnostics','parallel_diagnostics','forward53_diagnostics'))
                    or build.get('allocation_diagnostics') != (mode == 'resource')
                    or build.get('encoder_backend') != 'default' or build.get('scheduling_window') != 'default'):
                raise ValueError('ordinary/allocation modes or selectors differ')
            command = build['command']
            if (command[command.index('--profile')+1] != 'perf'
                    or command[command.index('--features')+1] != ('classic-allocation-diagnostics' if mode == 'resource' else 'classic-compare')):
                raise ValueError('fixed perf features required')
            profile = tomllib.loads((path.parent/'source/workers/Cargo.toml').read_text())['profile']['perf']
            if profile.get('lto') != 'thin' or profile.get('codegen-units') != 1 or build['cargo_configs']:
                raise ValueError('matched unmodified build recipe required')
            allowed_environment = {'RUSTC', 'CC', 'CARGO_TARGET_X86_64_UNKNOWN_LINUX_GNU_LINKER', 'PKG_CONFIG_PATH'}
            if set(build['environment']) - allowed_environment:
                raise ValueError('build flags/profile/instrumentation override forbidden')
            lines = [line for line in (path.parent/'cargo.stderr').read_text().splitlines() if 'Running ' in line and '--crate-name classic_compare_worker ' in line]
            if len(lines) != 1 or any(flag not in lines[0] for flag in ('opt-level=3','lto=thin','codegen-units=1','debuginfo=line-tables-only')):
                raise ValueError('effective ordinary compiler flags differ')
            for target in ('emuella_j2k_core', 'emuella_j2k_codestream'):
                artefacts = [r for r in build['artefacts'] if r['target']['name'] == target]
                if not artefacts or any('parallel' not in r['features'] or 'simd' in r['features'] or r['profile']['opt_level'] != '3' for r in artefacts):
                    raise ValueError('parallel/perf/no-SIMD required')
            if any(sha(path.parent/name) != digest for name,digest in build['logs'].items()):
                raise ValueError('build log changed')
            result[arm][mode] = dict(path=str(path), sha256=sha(path), build=build)
    base = result['A']['ordinary']['build']
    for modes in result.values():
        for entry in modes.values():
            for key in ('rustc','openjpeg','libraries','environment','cargo_configs','lock_sha256'):
                if entry['build'][key] != base[key]:
                    raise ValueError('matched build dependency differs: '+key)
    return result, source


def prepare(config_path, output):
    config = json.loads(config_path.read_text()); validate_request(config['request']); evidence = roots(config)
    output = absolute(str(output))
    if output.parent != absolute(config['output']) or output.exists() or absolute(config['output']).exists():
        raise ValueError('fresh preparation and acquisition output required')
    bound_builds, source = builds(config)
    if set(config['prerequisites']) != PREREQUISITES or not config.get('authority','').strip():
        raise ValueError('complete prerequisites and fresh authority required')
    for key, record in config['prerequisites'].items():
        pinned(record)
        if key != 'independent_decode' and record.get('source_treatment_sha256') != config['source_treatment']['sha256']:
            raise ValueError('new prerequisite must bind this treatment: '+key)
    for kind, digest in (('raw',RAW),('stream',STREAM)):
        if sha(config['request'][kind+'_path']) != digest:
            raise ValueError('input identity differs')
    if Path(config['request']['stream_path']).stat().st_size != 14339292:
        raise ValueError('reference stream length differs')
    notice = absolute(config['store_root'])/panels.NOTICES['rareplanes'][0]
    if sha(notice) != panels.NOTICES['rareplanes'][1]:
        raise ValueError('reviewed corpus notice differs')
    binding = dict(schema=SCHEMA, config=config, source=source, schedule=schedule(), ordering=order_summary(),
        builds=bound_builds, estimator=stability.estimator_identity(absolute(config['estimator']),40),
        runner=refresh.classic.clean_source(refresh.ROOT), installation=live.installed_binding(),
        host_policy=live.host_policy(), warmups=0, samples_per_process=1, boundary=refresh.BOUNDARY)
    files = {str(config_path), str(pinned(config['source_treatment'])), str(notice)}
    files.update(str(pinned(r)) for r in config['prerequisites'].values())
    files.update(str(p) for p in (refresh.ROOT/'scripts').glob('*.py'))
    files.update(config['request'][k+'_path'] for k in ('raw','stream'))
    for modes in bound_builds.values():
        for entry in modes.values():
            files.update([entry['path'],entry['build']['binary'],*entry['build']['libraries']])
            files.update(str(Path(entry['path']).parent/p) for p in entry['build']['logs'])
    estimator_root = Path(binding['estimator']['path']).parents[2]
    files.update([binding['estimator']['path'],*(str(estimator_root/p) for p in ('provenance.json','src/owner_compare.rs','src/main.rs','Cargo.toml'))])
    binding['file_identities'] = {p:live.file_identity(p) for p in sorted(files)}
    if stability.p.bytes_used(Path(config['build_root'])) > CAPS['build_bytes']:
        raise ValueError('build scratch cap exceeded')
    for folder in evidence:
        folder.mkdir(exist_ok=True)
        if (folder/'LICENSE.txt').exists() or (folder/'NOTICE.txt').exists():
            raise ValueError('evidence notice already exists; no preparation replacement')
        (folder/'LICENSE.txt').write_bytes(notice.read_bytes())
        (folder/'NOTICE.txt').write_text(panels.ATTRIBUTIONS['rareplanes']+' CC BY-SA 4.0. Local caller-boundary experiment; protected payloads remain in their approved store.\n')
    write(output,binding)
    return binding


def read_binding(path,digest):
    if sha(path) != digest:
        raise ValueError('externally pinned preparation differs')
    value = json.loads(Path(path).read_text())
    if value.get('schema') != SCHEMA or value.get('schedule') != schedule() or value.get('ordering') != order_summary():
        raise ValueError('frozen experiment schedule/schema differs')
    validate_request(value['config']['request'])
    return value


def identities(binding, full=False):
    if any(os.environ.get(k) for k in ('EMUELLA_TIER1_ENCODER','EMUELLA_CLASSIC_WINDOW','LD_PRELOAD','LD_LIBRARY_PATH')):
        raise ValueError('runtime overrides forbidden')
    if live.host_policy() != binding['host_policy'] or refresh.classic.clean_source(refresh.ROOT) != binding['runner']:
        raise ValueError('host policy or controller changed')
    if any(live.file_identity(p) != identity for p,identity in binding['file_identities'].items()):
        raise ValueError('immutable evidence/input/build changed')
    if full:
        actual,source = builds(binding['config'])
        if actual != binding['builds'] or source != binding['source'] or live.installed_binding() != binding['installation']:
            raise ValueError('frozen source/build/installation changed')
        if stability.estimator_identity(binding['estimator']['path'],40) != binding['estimator']:
            raise ValueError('estimator changed')
        for kind in ('raw','stream'):
            request = binding['config']['request']
            if sha(request[kind+'_path']) != request[kind+'_sha256']:
                raise ValueError('input changed')


def consumption(binding,start,started):
    return dict(started_calls=started, wall_seconds=(time.monotonic_ns()-start)/1e9,
        evidence_bytes=sum(stability.p.bytes_used(p) for p in roots(binding['config'])),
        build_bytes=stability.p.bytes_used(Path(binding['config']['build_root'])))


def resource_gate(row,request,rows):
    if row['planned']['stage'] != 'allocation': return
    row['resources'] = panels.resources.resource_observation(row['result']['observation'], request)
    if not row['resources']['eligible']:
        raise ValueError('allocation bounds failed')
    prior = next((r for r in rows if r['planned']['stage'] == 'allocation'),None)
    if prior and any(row['result']['observation'][k] != prior['result']['observation'][k] for k in ('working_bytes','output_capacity_limit')):
        raise ValueError('allocation query differs between arms')


def observe(binding,planned,receipt,environment,start,rows,path,digest,authority_path,authority_sha):
    issues = budget_issues(consumption(binding,start,len(rows)),True)
    if issues: raise ValueError('; '.join(issues))
    root = Path(binding['config']['output']); request = dict(binding['config']['request'],round=planned['round'])
    write(root/(planned['call_id']+'-started.json'),dict(planned=planned,monotonic_ns=time.monotonic_ns()))
    row = dict(planned=planned,result=dict(status='started_without_result'),gates_passed=False)
    try:
        if sha(path) != digest or sha(authority_path) != authority_sha:
            raise ValueError('preparation/authority changed')
        identities(binding)
        before = stability.environment(receipt,reservation_check=live.admit)
        if stability.environment_issues(environment,before,receipt): raise ValueError('environment drift before call')
        mode = 'resource' if planned['stage'] == 'allocation' else 'ordinary'
        row['result'] = refresh.run_process(binding['builds'][planned['arm']][mode]['build']['binary'],request,
            root/planned['call_id'],[0],allocation_diagnostics=mode == 'resource',placement=live.place(receipt))
        if row['result']['status'] != 0: raise ValueError('failed call retained; no replacement')
        resource_gate(row,request,rows); identities(binding)
        after = stability.environment(receipt,reservation_check=live.admit)
        issues = stability.environment_issues(environment,after,receipt)
        row['environment'] = dict(before=before,after=after,issues=issues)
        issues += budget_issues(consumption(binding,start,len(rows)+1))
        if issues: raise ValueError('; '.join(issues))
        row['gates_passed'] = True
    except BaseException as error:
        row['failure'] = str(error)
        if row['result']['status'] in (0,'started_without_result'):
            row['result'].update(status='failed_attempt',reason=str(error))
        if not isinstance(error,Exception): raise
    finally:
        write(root/(planned['call_id']+'-receipt.json'),row); rows.append(row)
    return row


def acquire(binding,path,digest,authority_path):
    root = Path(binding['config']['output']); receipt = live.authority(binding,authority_path)
    authority_sha = sha(authority_path); identities(binding,True); live.controller_admission(receipt)
    transport = json.loads((root/'execution-started.json').read_text())
    if transport['preparation_sha256'] != digest or transport['authority_sha256'] != authority_sha:
        raise ValueError('outside restoration owner binding differs')
    if receipt['valid_until_epoch']-time.time() < CAPS['wall_seconds']:
        raise ValueError('lease cannot cover full observation cap')
    rows,issues = [],[]; start = None
    with stability.controller_placement(receipt,root):
        environment = stability.environment(receipt,reservation_check=live.admit)
        if stability.environment_issues(environment,environment,receipt): raise ValueError('initial environment differs')
        try:
            start = time.monotonic_ns()
            write(root/'launch.json',dict(start_ns=start,preparation_sha256=digest,authority_sha256=authority_sha,condition=receipt,environment=environment))
            for planned in schedule():
                row = observe(binding,planned,receipt,environment,start,rows,path,digest,authority_path,authority_sha)
                print(planned['call_id'],planned['arm'],row['result']['status'],flush=True)
                if not row['gates_passed']: raise ValueError('mandatory call gate failed')
            identities(binding,True)
            issues.extend(budget_issues(consumption(binding,start,len(rows))))
        except BaseException as error:
            issues.append(str(error))
            if not isinstance(error,Exception): raise
        finally:
            if start is not None:
                write(root/'completion.json',dict(schema=SCHEMA,preparation_sha256=digest,issues=issues,
                    started_calls=len(rows),unstarted_call_ids=[r['call_id'] for r in schedule()[len(rows):]],
                    consumption=consumption(binding,start,len(rows)),complete=len(rows)==126 and not issues,
                    interpretation='No performance interpretation before all ordinary calls and independent restoration'))
    return 0 if len(rows)==126 and not issues else 1


def execute_owned(binding,path,digest,authority_path):
    """Same installed transport/restoration contract; this module is the controller."""
    root = Path(binding['config']['output']); lease = authority_path.parent.parent
    if (root/'execution-started.json').exists(): raise ValueError('attempt already consumed')
    owned=False; error=None; status=None; terminal=None; handlers={}; authority_sha=None
    def interrupted(signum,frame): raise KeyboardInterrupt('signal '+str(signum))
    try:
        for signum in (signal.SIGINT,signal.SIGTERM): handlers[signum]=signal.signal(signum,interrupted)
        live.authenticate_lease(binding,authority_path); owned=True; authority_sha=sha(authority_path)
        write(root/'execution-started.json',dict(preparation_sha256=digest,authority_sha256=authority_sha,lease_id=lease.name))
        live.authority(binding,authority_path)
        status=subprocess.run(['/usr/bin/python3','-I',str(lease/'helper.py'),'--condition','balanced-reusable','run','--',
            '/usr/bin/python3','-I',str(Path(__file__).resolve()),'run','--preparation',str(path),'--sha256',digest,
            '--authority-receipt',str(authority_path)],check=False).returncode
    except BaseException as failure: error=str(failure) or type(failure).__name__
    finally:
        for signum in handlers: signal.signal(signum,signal.SIG_IGN)
        try:
            if not owned: raise ValueError('lease ownership not authenticated; cannot stop an unrelated lease')
            if live.installed_binding()!=binding['installation']: raise ValueError('installation changed')
            calls=[]
            for action in ('stop','verify'):
                try:
                    result=subprocess.run(['/usr/bin/sudo','-n',str(live.INSTALL/'measurement_launcher.py'),action],capture_output=True,text=True,timeout=200)
                    calls.append(dict(action=action,status=result.returncode,stdout=result.stdout,stderr=result.stderr))
                except (OSError,subprocess.SubprocessError) as failure: calls.append(dict(action=action,status='failed',error=str(failure)))
            write(root/'installed-restoration-commands.json',calls)
            terminal=live.validate_restoration(binding,lease,authority_sha); write(root/'independent-restoration.json',terminal)
        except BaseException as failure: error=(error+'; ' if error else '')+'restoration unresolved: '+str(failure)
        finally:
            for signum,handler in handlers.items(): signal.signal(signum,handler)
        write(root/'execution-complete.json',dict(schema=SCHEMA,status=status,error=error,lease_id=lease.name,restoration_verified=terminal is not None))
    return 1 if error or status!=0 else 0


def screen(contrasts):
    primary,serial = contrasts['C/B'],contrasts['C/A']
    benefit = primary['upper'] is not None and primary['upper'] < 0
    serial_pass = serial['upper'] is not None and serial['upper'] <= .01
    return dict(intervention_benefit_supported=benefit,serial_endpoint_bound_passed=serial_pass,
        resolved_adverse_intervention=primary['lower'] is not None and primary['lower'] > 0,
        disposition=('measured repair candidate subject to independent engineering value judgement and separate qualification authority' if benefit and serial_pass else
            'useful intervention evidence; serial requirement unproved' if benefit else 'no worthwhile supported repair at this budget'),
        production_promotion_authorised=False)


def analyse(rows,estimator):
    """All 126 gates, then exactly 40 samples per arm; no AB/BA relabelling."""
    if len(rows)!=126 or [r.get('planned') for r in rows]!=schedule(): raise ValueError('complete fixed 126-call schedule required')
    vectors={a:[] for a in 'ABC'}
    for row in rows:
        if row.get('gates_passed') is not True or row.get('result',{}).get('status')!=0: raise ValueError('failed/incomplete call')
        if row['planned']['stage']!='ordinary': continue
        observed=row['result']['observation']; samples=observed.get('samples_ns')
        if (not isinstance(samples,list) or len(samples)!=1 or type(samples[0]) is not int or samples[0]<=0
                or any(observed.get(k) is not None for k in ('allocation_diagnostic','execution_diagnostic'))): raise ValueError('ordinary sample differs')
        vectors[row['planned']['arm']].append(samples[0])
    contrasts={}
    for candidate,baseline in (('C','B'),('B','A'),('C','A')):
        record=analysis._estimate(estimator,vectors[baseline],vectors[candidate])
        if not record['valid']: raise ValueError('owner comparator failed: '+str(record))
        output=record['output']; base=output['baseline_mean_ns']; cand=output['candidate_mean_ns']
        record.update(relative_change=cand/base-1,mean_change_ms=(cand-base)/1e6,mean_saving_ms=(base-cand)/1e6,
            baseline_mean_ms=base/1e6,candidate_mean_ms=cand/1e6,
            interpretation='99% interval for this contrast only; legacy +/-5% verdict retained')
        contrasts[candidate+'/'+baseline]=record
    return dict(vectors_ns=vectors,contrasts=contrasts,screen=screen(contrasts),ordering=order_summary())


def reconstruct(binding,digest,estimator):
    root=Path(binding['config']['output']); evidence={}; rows=[]; missing=[]; issues=[]; started=[]
    def read(name): return retained.read_optional(root/name,evidence)
    expected=set()
    for planned in schedule():
        names=[planned['call_id']+suffix for suffix in ('-started.json','-receipt.json')]; expected.update(names)
        start,row=map(read,names)
        if start is None:
            if row is not None or (root/planned['call_id']).exists(): issues.append('orphaned call '+planned['call_id'])
            continue
        started.append(start)
        if start.get('planned')!=planned or type(start.get('monotonic_ns')) is not int: issues.append('start identity differs')
        if row is None:
            missing.append(planned['call_id']); row=dict(planned=planned,result=dict(status='missing_terminal_receipt'),gates_passed=False)
        if row.get('planned')!=planned: issues.append('receipt identity differs')
        rows.append(row)
    if [s.get('planned') for s in started]!=schedule()[:len(started)]: issues.append('starts are not schedule prefix')
    for pattern in ('ordinary-*-*.json','preflight-*-*.json','allocation-*-*.json'):
        if any(p.name not in expected for p in root.glob(pattern)): issues.append('unexpected call receipt')
    completion,execution,terminal,restoration,launch=[read(p) for p in ('completion.json','execution-started.json','execution-complete.json','independent-restoration.json','launch.json')]
    try:
        if not execution or execution['preparation_sha256']!=digest: raise ValueError('execution identity absent')
        live.verify_retained_restoration(binding,restoration,execution['lease_id'],execution['authority_sha256'])
        receipt=json.loads(restoration['authority_text'])
        if not retained.runner_restored(root,started,evidence,receipt['controller_cpus']): raise ValueError('controller restoration absent')
        if (not terminal or terminal['schema']!=SCHEMA or terminal['lease_id']!=execution['lease_id'] or terminal.get('error') or terminal.get('status')!=0 or not terminal['restoration_verified']): raise ValueError('terminal acquisition/restoration failed')
        if not launch or launch['preparation_sha256']!=digest or launch['authority_sha256']!=execution['authority_sha256'] or launch['condition']!=live.common_authority(receipt): raise ValueError('launch identity differs')
        for record in binding['config']['prerequisites'].values(): pinned(record)
        for row in rows:
            planned,result=row['planned'],row['result']; request=dict(binding['config']['request'],round=planned['round'])
            folder=root/planned['call_id']
            if result.get('status')!=0 or not row.get('gates_passed'): raise ValueError('failed/incomplete retained call')
            if json.loads((folder/'request.json').read_text())!=request or json.loads((folder/'result.json').read_text())!=result: raise ValueError('raw retained request/result differs')
            observed=result['observation']; mode='resource' if planned['stage']=='allocation' else 'ordinary'
            if any(observed.get(k)!=request[k] for k in ('codec','operation','case_id','round','style','workers','raw_sha256','stream_sha256')): raise ValueError('result workload differs')
            if observed.get('binary_sha256')!=binding['builds'][planned['arm']][mode]['build']['binary_sha256'] or observed.get('exact') is not True or observed.get('boundary')!=refresh.BOUNDARY: raise ValueError('result binary/boundary/exactness differs')
            for snapshot in ('before','after'):
                if stability.environment_issues(launch['environment'],row['environment'][snapshot],launch['condition']): raise ValueError('retained environment differs')
            if row['environment']['issues']: raise ValueError('environment gate failed')
            copied=copy.deepcopy(row); resource_gate(copied,request,rows[:rows.index(row)])
            if copied.get('resources')!=row.get('resources'): raise ValueError('allocation evidence differs')
        if (not completion or completion['schema']!=SCHEMA or completion['preparation_sha256']!=digest or completion['started_calls']!=len(started)
                or completion['unstarted_call_ids']!=[r['call_id'] for r in schedule()[len(started):]] or completion['issues'] or not completion['complete']): raise ValueError('incomplete accounting')
        issues.extend(budget_issues(dict(completion['consumption'],started_calls=len(started))))
    except (ValueError,KeyError,TypeError,OSError) as error: issues.append(str(error))
    result=dict(schema=SCHEMA,complete=False,issues=issues,raw_rows=rows,started_calls=len(started),
        missing_terminal_call_ids=missing,unstarted_call_ids=[r['call_id'] for r in schedule() if r not in [s.get('planned') for s in started]],
        evidence_sha256=evidence,preparation_sha256=digest,independent_restoration=restoration,
        interpretation='Prospective source-level refactoring, not historical causality or production qualification')
    if not issues:
        try: result.update(analyse(rows,estimator),complete=True)
        except ValueError as error: issues.append(str(error))
    return result


def main():
    parser=argparse.ArgumentParser(description=__doc__); commands=parser.add_subparsers(dest='command',required=True)
    command=commands.add_parser('prepare'); command.add_argument('--config',type=Path,required=True); command.add_argument('--output',type=Path,required=True)
    for name in ('execute','run','report'):
        command=commands.add_parser(name); command.add_argument('--preparation',type=Path,required=True); command.add_argument('--sha256',required=True)
        if name=='report':
            command.add_argument('--estimator',type=Path,required=True); command.add_argument('--output',type=Path,required=True)
        else: command.add_argument('--authority-receipt',type=Path,required=True)
    args=parser.parse_args()
    if args.command=='prepare': prepare(args.config,args.output); return 0
    binding=read_binding(args.preparation,args.sha256); root=Path(binding['config']['output'])
    if args.command=='report':
        identity=stability.estimator_identity(args.estimator,40)
        if any(identity[k]!=binding['estimator'][k] for k in ('owner_module_sha256','entrypoint_sha256','manifest_sha256')): raise ValueError('report comparator differs')
        if absolute(str(args.output)).parent!=root: raise ValueError('report must remain in approved observation root')
        result=reconstruct(binding,args.sha256,args.estimator); write(args.output,result); return 0 if result['complete'] else 1
    if args.command=='execute':
        with live.lifecycle(root): return execute_owned(binding,args.preparation,args.sha256,args.authority_receipt)
    with (root/'acquisition.lock').open('a') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB); write(root/'acquisition-started.json',dict(preparation_sha256=args.sha256))
        return acquire(binding,args.preparation,args.sha256,args.authority_receipt)


if __name__=='__main__': sys.exit(main())
