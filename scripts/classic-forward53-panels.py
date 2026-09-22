#!/usr/bin/env python3
"""Frozen, development-only forward 5/3 observations; no confirmation launcher."""
import argparse
from collections import Counter, defaultdict
import importlib.util
import json
from pathlib import Path
import statistics
import time

SPEC = importlib.util.spec_from_file_location('forward53_resources', Path(__file__).with_name('mq-d2-resources.py'))
resources = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(resources)
kernel = resources.kernel
refresh = kernel.refresh
budget_module = refresh.module('forward53_budget', 'mq-d2-budget.py')
POLICY = 'classic-forward53-panels/v1'
ARMS = ('reference', 'q1', 'qW')
MODES = ('ordinary', 'resource', 'diagnostic')
STAGES = ('resources', 'ordinary', 'diagnostic', 'decoder')
COUNTS = dict(resources=68, ordinary=84, diagnostic=12, decoder=4)
NOTICES = {
    'rareplanes': ('source/LICENSE.txt', 'f627ad059128fa5246a21e25759c1d33e35c4bb6287d636c4b970f7df57e7eba'),
    'spacenet': ('source/LICENSE.md', 'ebeaa5a46058cce9e893f42d601e1155bae27aa538f2854c79c626e297356c35'),
}
ATTRIBUTIONS = {
    'rareplanes': 'RarePlanes Dataset, June 2020. J. Shermeyer et al.; In-Q-Tel – CosmiQ Works and AI.Reverie.',
    'spacenet': 'SpaceNet Dataset, SpaceNet Partners and DigitalGlobe imagery; Van Etten, Lindenbaum and Bacastow (2018).',
}


def schedule(rareplanes, spacenet):
    """Each RGB8 round rotates ABC/BCA/CAB: every form occupies each position."""
    kernel.front_end_contrasts(rareplanes, 'screen')
    kernel.entropy_contrasts(spacenet, 'spacenet')
    mansfield = {a['product']: a for a in rareplanes if a['id'].startswith('94_')}
    chips = []
    for suffix in ('AOI_2_Vegas_img1454', 'AOI_3_Paris_img235'):
        selected = [a for a in spacenet if a['id'].endswith(suffix)]
        if len(selected) != 1:
            raise ValueError('fixed SpaceNet development chip differs')
        chips.extend(selected)
    rows = []

    def add(stage, asset, style, workers, round_id, arm, store='rareplanes'):
        rows.append(dict(index=len(rows), stage=stage, store=store, case_id=asset['id'],
                         style=style, workers=workers, round=round_id, arm=arm,
                         operation='decode' if stage == 'decoder' else 'encode',
                         origin='openjpeg' if stage == 'decoder' else 'emuella',
                         mode={'resources': 'resource', 'diagnostic': 'diagnostic'}.get(stage, 'ordinary')))

    for product in ('RGB8', 'PAN16', 'MS16', 'RGB16'):
        for style in (0, 1):
            for workers in (1, 2, 4, 8):
                for arm in ('reference', 'qW'):
                    add('resources', mansfield[product], style, workers, 0, arm)
    for style in (0, 1):
        for workers in (1, 8):
            add('resources', mansfield['RGB8'], style, workers, 0, 'q1')
    for round_id in range(3):
        for style in (0, 1):
            for workers in (1, 8):
                for arm in ARMS[round_id:] + ARMS[:round_id]:
                    add('ordinary', mansfield['RGB8'], style, workers, round_id, arm)
    for product in ('PAN16', 'MS16', 'RGB16'):
        for style in (0, 1):
            for workers in (1, 8):
                for arm in ARMS:
                    add('ordinary', mansfield[product], style, workers, 0, arm)
    for asset in chips:
        for style in (0, 1):
            for arm in ARMS:
                add('ordinary', asset, style, 8, 0, arm, 'spacenet')
    for style in (0, 1):
        for workers in (1, 8):
            for arm in ARMS:
                add('diagnostic', mansfield['RGB8'], style, workers, 0, arm)
    for style in (0, 1):
        for arm in ('reference', 'qW'):
            add('decoder', mansfield['RGB8'], style, 8, 0, arm)
    if Counter(r['stage'] for r in rows) != COUNTS:
        raise ValueError('development schedule differs')
    return rows


def absolute(value):
    path = Path(value)
    if not path.is_absolute() or path.resolve() != path:
        raise ValueError('paths must be absolute, resolved and free of symlink aliases')
    return path


def build_bindings(config, receipt):
    if receipt.get('panel_width') != 16 or set(receipt.get('forms', {})) != set(ARMS):
        raise ValueError('source receipt requires fixed width 16 and all three forms')
    forms = dict(reference='Reference', q1='RowPanelScalar', qW='RowPanelParallel')
    bound = {}
    for arm in ARMS:
        form = receipt['forms'][arm]
        source = refresh.classic.clean_source(absolute(form['source']))
        if form.get('form') != forms[arm] or source['source_revision'] != form['revision']:
            raise ValueError('source form/revision differs')
        if set(config['arms'][arm]) != set(MODES):
            raise ValueError('each arm requires ordinary/resource/diagnostic builds')
        bound[arm] = {}
        for mode in MODES:
            path = absolute(config['arms'][arm][mode])
            build = refresh.bind(path)
            if build['codec'] != source:
                raise ValueError('build codec source differs from clean committed source')
            if (build.get('sampling') or build.get('encoder_backend') != 'default'
                    or build.get('scheduling_window') != 'default'
                    or build.get('execution_diagnostics') != (mode == 'diagnostic')
                    or build.get('allocation_diagnostics') != (mode == 'resource')
                    or bool(build.get('forward53_diagnostics')) != (mode == 'diagnostic' and arm != 'reference')):
                raise ValueError('build instrumentation/backend/window differs')
            command = build['command']
            if '--profile' not in command or command[command.index('--profile') + 1] != 'perf':
                raise ValueError('perf builds required')
            for target in ('emuella_j2k_core', 'emuella_j2k_codestream'):
                artefacts = [a for a in build['artefacts'] if a['target']['name'] == target]
                if not artefacts or any('parallel' not in a['features'] or 'simd' in a['features']
                                        or a['profile']['opt_level'] != '3' for a in artefacts):
                    raise ValueError('parallel/perf/no-SIMD artefacts required')
            for name, expected in build['logs'].items():
                if refresh.sha(path.parent / name) != expected:
                    raise ValueError('build log differs')
            bound[arm][mode] = dict(receipt_sha256=refresh.sha(path), build=build)
    base = bound['reference']['ordinary']['build']
    for builds in bound.values():
        for entry in builds.values():
            build = entry['build']
            for field in ('rustc', 'openjpeg', 'libraries', 'environment', 'cargo_configs', 'lock_sha256'):
                if build[field] != base[field]:
                    raise ValueError('build treatment differs: ' + field)
            if refresh.worker_sources(build['benchmark']) != refresh.worker_sources(base['benchmark']):
                raise ValueError('worker source differs')
    return bound


def validate_budget_roots(config, budget):
    stores = [absolute(s['prepared']).parent for s in config['stores'].values()]
    excluded = stores + [absolute(s[k]) for s in config['stores'].values() for k in ('prepared', 'streams')]
    roots = [absolute(p) for p in budget.config['protected_output_roots']]
    expected = {absolute(s['output']) for s in config['stores'].values()}
    if not expected.issubset(roots):
        raise ValueError('ledger must cover both output roots')
    if any(not any(root.is_relative_to(store) for store in stores)
           or any(root == path or root.is_relative_to(path) or path.is_relative_to(root)
                  for path in excluded if path not in stores)
           or root in stores for root in roots):
        raise ValueError('ledger roots must be approved-store metadata, excluding prepared inputs/streams')
    if any(a.is_relative_to(b) or b.is_relative_to(a) for i, a in enumerate(roots) for b in roots[i + 1:]):
        raise ValueError('ledger metadata roots overlap')
    if not budget.path.is_relative_to(absolute(config['stores']['rareplanes']['output'])):
        raise ValueError('ledger must remain with RarePlanes observations')


def bind(config):
    if config.get('policy') != POLICY or config.get('panel_width') != 16 or config.get('cpus') != list(range(8)):
        raise ValueError('fixed policy, width or CPUs differ')
    if set(config['arms']) != set(ARMS) or set(config['stores']) != set(NOTICES):
        raise ValueError('build forms or source stores differ')
    receipt_path = absolute(config['source_receipt'])
    receipt = json.loads(receipt_path.read_text())
    bindings = dict(source_receipt=receipt, source_receipt_sha256=refresh.sha(receipt_path),
                    builds=build_bindings(config, receipt), stores={})
    budget_path = absolute(config['budget'])
    budget = budget_module.Budget(budget_path, POLICY)
    for name, info in config['stores'].items():
        prepared, streams, output = (absolute(info[k]) for k in ('prepared', 'streams', 'output'))
        store = prepared.parent
        if streams.parent != store or output.parent != store or len({prepared, streams, output}) != 3:
            raise ValueError('evidence and streams must remain in their approved input store')
        notice = store / NOTICES[name][0]
        if refresh.sha(notice) != NOTICES[name][1]:
            raise ValueError('reviewed source notice differs')
        assets = kernel.assets(prepared, 'spacenet' if name == 'spacenet' else 'primary')
        if any(not (prepared / a['path']).resolve().is_relative_to(store) for a in assets):
            raise ValueError('prepared asset escapes its approved store')
        bindings['stores'][name] = dict(assets=assets, prepared_sha256=refresh.sha(prepared / 'prepared.json'),
                                       notice_sha256=refresh.sha(notice))
    validate_budget_roots(config, budget)
    absolute(budget.config['scratch_root'])
    rows = schedule(*(bindings['stores'][s]['assets'] for s in ('rareplanes', 'spacenet')))
    for row in rows:
        info = config['stores'][row['store']]
        assets = bindings['stores'][row['store']]['assets']
        asset = next(a for a in assets if a['id'] == row['case_id'])
        prepared, streams = Path(info['prepared']), Path(info['streams'])
        request = refresh.make_request(asset, prepared, streams, row['origin'], 'emuella',
                                       row['style'], row['workers'], 'prepare', row['round'])
        stream = Path(request['stream_path'])
        if row['store'] == 'spacenet':
            stream = streams / 'streams' / f"{asset['id']}-style{row['style']}.j2k"
        if not stream.resolve().is_relative_to(prepared.parent):
            raise ValueError('reference stream escapes its approved store')
        request.update(operation=row['operation'], stream_path=str(stream), stream_sha256=refresh.sha(stream))
        row['request'] = request
    owner = refresh.classic.clean_source(refresh.ROOT)
    base = bindings['builds']['reference']['ordinary']['build']['benchmark']
    if refresh.worker_sources(owner) != refresh.worker_sources(base):
        raise ValueError('current worker source differs from frozen builds')
    bindings.update(schedule=rows, budget_sha256=refresh.sha(budget_path), owner=owner)
    return bindings


def freeze(config_path, output):
    config = json.loads(config_path.read_text())
    output = absolute(str(output))
    root = absolute(config['stores']['rareplanes']['output'])
    if output.parent != root:
        raise ValueError('freeze must remain in the RarePlanes observation root')
    # Output roots may contain only the operator-created budget before freezing.
    allowed = {absolute(config['budget'])}
    for store in config['stores'].values():
        folder = absolute(store['output'])
        if folder.exists() and any(p not in allowed for p in folder.iterdir()):
            raise ValueError('observation root already contains evidence')
    binding = bind(config)
    state = budget_module.Budget(Path(config['budget']), POLICY).state_path
    if state.exists():
        raise ValueError('budget already started; cannot freeze replacement observations')
    for name, info in config['stores'].items():
        folder = Path(info['output'])
        folder.mkdir(exist_ok=True)
        notice = Path(info['prepared']).parent / NOTICES[name][0]
        (folder / 'LICENSE.txt').write_bytes(notice.read_bytes())
        (folder / 'NOTICE.txt').write_text(ATTRIBUTIONS[name] + ' CC BY-SA 4.0. Local development observations; '
                                         'unchanged source lineage and protected payloads remain in this store.\n')
    refresh.write(output, dict(policy=POLICY, config=config, bindings=binding,
                               machine=refresh.cpu_identity(config['cpus']), frozen_unix=time.time(),
                               confirmation_supported=False, promotion='qualification-pending'))
    print(f'frozen {len(binding["schedule"])} development calls', flush=True)


def receipt_path(frozen, row):
    root = Path(frozen['config']['stores'][row['store']]['output'])
    return root / f"call-{row['index']:03d}-receipt.json"


def read_rows(frozen, stage):
    rows = []
    for planned in frozen['bindings']['schedule']:
        if planned['stage'] != stage:
            continue
        path = receipt_path(frozen, planned)
        if path.exists():
            row = json.loads(path.read_text())
            if row['planned'] != planned:
                raise ValueError('observation differs from frozen schedule')
            rows.append(row)
    return rows


def stage_complete(frozen, stage):
    rows = read_rows(frozen, stage)
    root = Path(frozen['config']['stores']['rareplanes']['output'])
    terminal = root / (stage + '-complete.json')
    return (terminal.exists() and json.loads(terminal.read_text()).get('complete') is True
            and len(rows) == COUNTS[stage]
            and all(r['result']['status'] == 0 and
                    (stage != 'resources' or r.get('resources', {}).get('eligible') is True) for r in rows))


def validate_resource_queries(rows):
    """Panel admission must not change the existing facade allocation queries."""
    by_case = {(r['planned']['case_id'], r['planned']['style'], r['planned']['workers'],
                r['planned']['arm']): r for r in rows}
    for key, row in by_case.items():
        reference = by_case[(*key[:3], 'reference')]['result']['observation']
        candidate = row['result']['observation']
        for field in ('working_bytes', 'output_capacity_limit'):
            if candidate.get(field) != reference.get(field):
                raise ValueError('panel resource query changed: ' + field)


def run(freeze_path, stage):
    frozen = json.loads(freeze_path.read_text())
    config = frozen['config']
    root = Path(config['stores']['rareplanes']['output'])
    if stage != 'resources' and not stage_complete(frozen, 'resources'):
        raise ValueError('all fixed resource prerequisites must pass before later stages')
    # Exclusive creation precedes validation: failed attempts remain non-retryable.
    refresh.write(root / (stage + '-started.json'), dict(freeze_sha256=refresh.sha(freeze_path), started_unix=time.time()))
    rows = []
    try:
        if bind(config) != frozen['bindings']:
            raise ValueError('frozen source/build/input/stream/ledger identity changed')
        budget = budget_module.Budget(Path(config['budget']), POLICY)
        for planned in frozen['bindings']['schedule']:
            if planned['stage'] != stage:
                continue
            path = receipt_path(frozen, planned)
            budget.before_call()
            refresh.write(path.with_name(path.stem + '-started.json'), dict(planned=planned, started_unix=time.time()))
            build = frozen['bindings']['builds'][planned['arm']][planned['mode']]['build']
            try:
                result = refresh.run_process(build['binary'], planned['request'],
                                             path.parent / f"call-{planned['index']:03d}",
                                             config['cpus'][:planned['workers']],
                                             allocation_diagnostics=stage == 'resources',
                                             execution_diagnostics=stage == 'diagnostic')
            except Exception as error:
                result = dict(status='launch_or_receipt_failure', reason=str(error))
            row = dict(planned=planned, result=result)
            if result['status'] == 0 and stage == 'resources':
                try:
                    row['resources'] = resources.resource_observation(result['observation'], planned['request'])
                except ValueError as error:
                    result.update(status='invalid_resource_response', reason=str(error))
            refresh.write(path, row)
            rows.append(row)
            print(planned['index'], stage, planned['arm'], result['status'], flush=True)
            if result['status'] != 0 or (stage == 'resources' and not row['resources']['eligible']):
                raise ValueError('failed prerequisite/observation retained; stage incomplete, no replacement')
        if stage == 'resources':
            validate_resource_queries(rows)
        if bind(config) != frozen['bindings']:
            raise ValueError('frozen identities changed during observations')
        # Check terminal storage/wall bounds without consuming another invocation.
        state = json.loads(budget.state_path.read_text())
        if (time.time() - state['started_unix'] > budget.seconds
                or sum(budget_module.size(p) for p in budget.config['protected_output_roots']) >= budget.protected_bytes
                or budget_module.size(budget.config['scratch_root']) >= budget.scratch_bytes):
            raise ValueError('terminal observation budget exceeded')
    except Exception as error:
        refresh.write(root / (stage + '-complete.json'), dict(complete=False, reason=str(error), observed=len(rows)))
        raise
    refresh.write(root / (stage + '-complete.json'), dict(complete=True, observed=len(rows)))


def report(freeze_path, output):
    frozen = json.loads(freeze_path.read_text())
    root = Path(frozen['config']['stores']['rareplanes']['output'])
    if absolute(str(output)).parent != root:
        raise ValueError('report must remain in the approved observation root')
    stages = {s: dict(complete=stage_complete(frozen, s), rows=read_rows(frozen, s)) for s in STAGES}
    for stage, detail in stages.items():
        observed = {r['planned']['index'] for r in detail['rows']}
        detail['missing_indices'] = [r['index'] for r in frozen['bindings']['schedule']
                                     if r['stage'] == stage and r['index'] not in observed]
    groups = defaultdict(list)
    for row in stages['ordinary']['rows']:
        p = row['planned']
        if row['result']['status'] == 0:
            groups[(p['case_id'], p['style'], p['workers'], p['arm'])].append(row['result']['observation']['samples_ns'][0])
    descriptive = [dict(case_id=k[0], style=k[1], workers=k[2], arm=k[3], samples_ns=v,
                        arithmetic_mean_ns=statistics.mean(v)) for k, v in sorted(groups.items())]
    complete = all(s['complete'] for s in stages.values())
    result = dict(policy=POLICY, freeze_sha256=refresh.sha(freeze_path), complete=complete,
                  disposition='qualification-pending', performance_claim=False, confirmation_supported=False,
                  expected_calls=sum(COUNTS.values()), observed_calls=sum(len(s['rows']) for s in stages.values()),
                  stages=stages, descriptive_ordinary=descriptive)
    refresh.write(output, result)
    return complete


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest='command', required=True)
    command = commands.add_parser('freeze')
    command.add_argument('--config', type=Path, required=True)
    command.add_argument('--output', type=Path, required=True)
    command = commands.add_parser('run')
    command.add_argument('--freeze', type=Path, required=True)
    command.add_argument('--stage', choices=STAGES, required=True)
    command = commands.add_parser('report')
    command.add_argument('--freeze', type=Path, required=True)
    command.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    if args.command == 'freeze':
        freeze(args.config, args.output)
    elif args.command == 'run':
        run(args.freeze, args.stage)
    elif not report(args.freeze, args.output):
        raise SystemExit('incomplete development observations; no qualification claim')


if __name__ == '__main__':
    main()
