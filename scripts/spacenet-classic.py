#!/usr/bin/env python3
"""Freeze and run the separate SpaceNet PS-RGB16 absolute classic baseline."""
import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import signal
import subprocess


def module(name, filename):
    spec = importlib.util.spec_from_file_location(name, Path(__file__).with_name(filename))
    value = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(value)
    return value


classic = module('classic', 'real-scene-classic.py')
raw = module('raw', 'prepare-generated.py')
build = module('build', 'build-workers.py')
digest, write = classic.digest, classic.write
PACK = 'common/spacenet-psrgb16'
LIMIT = 4 * 1024**3
PROTOCOL = dict(rounds=5, warmups=0, samples=1, workers=1, styles=[0, 1],
                operations=['encode', 'decode'], timeout_seconds=120,
                execution_context='direct_global', boundary='facade_operation',
                max_working_bytes=classic.WORKING, max_output_bytes=classic.OUTPUT,
                process_address_limit_bytes=LIMIT, observed_process_rss_ceiling_bytes=LIMIT,
                resource_claim='execution cap only; no owner admission qualification')


def assets(prepared):
    record = json.loads((prepared / 'prepared.json').read_text())
    if record.get('schema_version') != 1 or record.get('pack_id') != PACK or record.get('version') != '1':
        raise ValueError('requires the distinct SpaceNet prepared schema 1 pack')
    selected = record['assets']
    if len(selected) != 16 or len({a['id'] for a in selected}) != 16:
        raise ValueError('requires sixteen uniquely identified frozen chips')
    groups = {}
    for asset in selected:
        if not re.fullmatch(r'RGB-PanSharpen_AOI_[A-Za-z0-9_]+_img[0-9]+', asset['id']):
            raise ValueError('unexpected original supplier chip identity')
        image = asset['image']
        if (asset.get('product') != 'RGB16' or asset.get('source_kind') != 'supplier-pansharpened-rgb16'
                or image.get('components') != 3 or image.get('precision') != 16 or image.get('signed') is not False
                or any(type(image.get(k)) is not int or not 4 <= image[k] <= 4096 for k in ('width', 'height'))):
            raise ValueError('requires original unsigned supplier RGB16 chip semantics')
        role = asset.get('role')
        if role not in ('development', 'reserved'):
            raise ValueError('unknown acquisition-group role')
        groups.setdefault(asset['bundle_id'], []).append(role)
        sample_count = image['width'] * image['height'] * 3
        for item, size in ((asset, sample_count * 2), (asset['validity'], sample_count)):
            path = raw.regular_file(prepared, item['path'])
            if item['bytes'] != size or path.stat().st_size != size or digest(path) != item['sha256']:
                raise ValueError('raw or per-band validity identity/length differs')
        validity = raw.regular_file(prepared, asset['validity']['path']).read_bytes()
        if any(v not in (0, 1) for v in validity):
            raise ValueError('validity must preserve per-band interleaved 0/1 samples')
    if (len(groups) != 4 or any(len(v) != 4 or len(set(v)) != 1 for v in groups.values())
            or sum(v[0] == 'reserved' for v in groups.values()) != 1):
        raise ValueError('requires four groups of four, one whole geographic reserve')
    return selected


def schedule(selected):
    # Recheck roles before deriving any timing requests, including resumed runs.
    if any(a.get('role') not in ('development', 'reserved') for a in selected):
        raise ValueError('unknown role cannot enter timing schedule')
    return [(a, style, operation, round_id) for round_id in range(5)
            for a in selected if a['role'] == 'development'
            for operation in ('encode', 'decode') for style in (0, 1)]


def identity(path):
    path = path.resolve(strict=True)
    return dict(path=str(path), sha256=digest(path))


def tool_identity(path):
    return dict(**identity(path), libraries=[identity(p) for p in build.libraries(path)])


def verify_identity(item):
    if digest(item['path']) != item['sha256']:
        raise ValueError('bound file identity changed: ' + item['path'])
    for library in item.get('libraries', []):
        verify_identity(library)


def freeze(args):
    selected = assets(args.prepared)
    if args.output.parent.resolve() != args.prepared.parent.resolve():
        raise ValueError('experiment and prepared inputs must share the authorised store')
    bound = classic.bind_build(args.binary, args.binary.parent / 'lossless_bypass_allocation',
                               args.codec_source, args.build_provenance)
    if bound['codec_revision'] != args.codec_revision:
        raise ValueError('build does not match the explicit frozen codec revision')
    cpus = [int(c) for c in args.cpus.split(',')]
    if not cpus or len(set(cpus)) != len(cpus) or not set(cpus) <= os.sched_getaffinity(0):
        raise ValueError('requires distinct available CPUs')
    harness = Path(__file__).resolve().parents[1]
    if subprocess.check_output(['git', '-C', str(harness), 'status', '--porcelain']):
        raise ValueError('freeze requires a clean committed benchmark source')
    record = dict(schema_version=1, pack=PACK, assets=selected, protocol=PROTOCOL,
        prepared=str(args.prepared.resolve()), prepared_manifest=identity(args.prepared / 'prepared.json'),
        source_views=identity(args.source_views), build_provenance=identity(args.build_provenance),
        binary=tool_identity(args.binary), decoder=tool_identity(args.decoder),
        decoder_provenance=identity(args.decoder_provenance), **bound,
        harness_revision=subprocess.check_output(['git', '-C', str(harness), 'rev-parse', 'HEAD'], text=True).strip(),
        scripts=[identity(Path(__file__)), identity(Path(classic.__file__)), identity(Path(raw.__file__))],
        cpus=cpus, environment=dict(uname=list(os.uname()), affinity=sorted(os.sched_getaffinity(0)),
            cpu_model=[line.strip() for line in Path('/proc/cpuinfo').read_text().splitlines() if line.startswith('model name')][:1],
            governors={str(c): Path(f'/sys/devices/system/cpu/cpu{c}/cpufreq/scaling_governor').read_text().strip()
                       for c in cpus if Path(f'/sys/devices/system/cpu/cpu{c}/cpufreq/scaling_governor').exists()}),
        interpretation='Absolute separate profile observations; no ranking, speedup or RarePlanes pooling')
    args.output.mkdir()
    write(args.output / 'manifest.json', record)
    (args.output / 'manifest.sha256').write_text(digest(args.output / 'manifest.json') + '\n')


def load(output):
    if digest(output / 'manifest.json') != (output / 'manifest.sha256').read_text().strip():
        raise ValueError('frozen experiment manifest changed')
    record = json.loads((output / 'manifest.json').read_text())
    if record['protocol'] != PROTOCOL or record['pack'] != PACK:
        raise ValueError('frozen protocol differs')
    for key in ('prepared_manifest', 'source_views', 'build_provenance', 'binary', 'decoder', 'decoder_provenance'):
        verify_identity(record[key])
    for script in record['scripts']:
        verify_identity(script)
    if assets(Path(record['prepared'])) != record['assets']:
        raise ValueError('frozen input coverage changed')
    return record


def untimed(command, directory, cpus):
    """No process clocks, resource samples or /usr/bin/time in reserve evidence."""
    directory.mkdir()
    command = ['taskset', '-c', ','.join(map(str, cpus)), 'prlimit', '--as=' + str(LIMIT), '--', *command]
    write(directory / 'command.json', command)
    with (directory / 'stdout.txt').open('x') as stdout, (directory / 'stderr.txt').open('x') as stderr:
        process = subprocess.Popen(command, stdout=stdout, stderr=stderr, start_new_session=True)
        try:
            return process.wait(timeout=120)
        except subprocess.TimeoutExpired:
            os.killpg(process.pid, signal.SIGKILL)
            process.wait()
            return 'timeout'


def validate_observation(req, observation, binary_sha, timed):
    for key in ('case_id', 'operation', 'round', 'width', 'height', 'components', 'bits', 'layout',
                'style', 'workers', 'raw_sha256', 'execution_context', 'boundary',
                'max_working_bytes', 'max_output_bytes'):
        if observation.get(key) != req[key]:
            raise ValueError('worker applied identity differs: ' + key)
    if (observation.get('native_exact') is not True or observation.get('rct') is not True
            or observation.get('binary_sha256') != binary_sha or observation.get('parallel') is not True
            or observation.get('simd') is not False or observation.get('warmup') != 0):
        raise ValueError('worker build, profile or full-sample exactness differs')
    samples = observation.get('samples_ns')
    if timed:
        if not isinstance(samples, list) or len(samples) != 1 or type(samples[0]) is not int or samples[0] <= 0:
            raise ValueError('requires one positive measured sample')
    elif samples != []:
        raise ValueError('untimed preparation returned sample clocks')
    stream = Path(req['stream_path'])
    if digest(stream) != observation.get('stream_sha256') or stream.stat().st_size != observation.get('complete_stream_bytes'):
        raise ValueError('stream identity differs from observed complete output')
    if 'stream_sha256' in req and req['stream_sha256'] != observation['stream_sha256']:
        raise ValueError('prepared stream was replaced')


def prepare(output, record):
    prepared = Path(record['prepared'])
    (output / 'streams').mkdir()
    folder = output / 'preparation'
    folder.mkdir()
    rows = []
    for asset in record['assets']:
        for style in (0, 1):
            root = folder / (asset['id'] + '-' + str(style))
            root.mkdir()
            req = classic.request(asset, prepared, output, style, 1, 'prepare')
            write(root / 'request.json', req)
            status = untimed([record['binary']['path'], str(root / 'request.json')], root / 'worker', record['cpus'])
            result = dict(case=asset['id'], role=asset['role'], style=style, status=status)
            if status == 0:
                try:
                    observation = json.loads((root / 'worker/stdout.txt').read_text())
                    validate_observation(req, observation, record['binary']['sha256'], False)
                    result['observation'] = observation
                    ppm = root / 'independent.ppm'
                    independent_status = untimed([record['decoder']['path'], '-quiet', '-i', req['stream_path'],
                                                   '-o', str(ppm), '-threads', '1'], root / 'independent', record['cpus'])
                    result['independent_status'] = independent_status
                    if independent_status != 0:
                        raise ValueError('independent decoder failed')
                    pixels, image = raw.read_pnm(ppm.read_bytes())
                    exact = image == asset['image'] and hashlib.sha256(pixels).hexdigest() == asset['sha256']
                    result['independent_exact'] = exact
                    result['independent_output'] = identity(ppm)
                    if not exact:
                        raise ValueError('independent full-sample equality failed')
                except (ValueError, KeyError, OSError) as error:
                    result.update(status='invalid_preparation', reason=str(error))
            write(root / 'result.json', result)
            rows.append(result)
    load(output)
    write(output / 'preparation.json', rows)
    return rows


def prepared_rows(output, record):
    rows = json.loads((output / 'preparation.json').read_text())
    expected = {(a['id'], s) for a in record['assets'] for s in (0, 1)}
    if len(rows) != len(expected) or {(r['case'], r['style']) for r in rows} != expected:
        raise ValueError('preparation coverage incomplete or duplicated')
    by_id = {a['id']: a for a in record['assets']}
    for row in rows:
        if row['status'] != 0 or row.get('independent_exact') is not True:
            raise ValueError('preparation contains a retained failure; measurement is not admitted')
        verify_identity(row['independent_output'])
        req = classic.request(by_id[row['case']], Path(record['prepared']), output, row['style'], 1, 'prepare')
        validate_observation(req, row['observation'], record['binary']['sha256'], False)
    return rows


def measure(output, record):
    prepared_rows(output, record)
    folder = output / 'measure'
    folder.mkdir()
    rows = []
    for asset, style, operation, round_id in schedule(record['assets']):
        req = classic.request(asset, Path(record['prepared']), output, style, 1, operation, round_id)
        result = classic.execute(Path(record['binary']['path']), req, folder / str(len(rows)), record['cpus'], address_limit=LIMIT)
        if result['status'] == 0:
            try:
                validate_observation(req, result['observation'], record['binary']['sha256'], True)
                if result['process_peak_rss_bytes'] > LIMIT:
                    raise ValueError('observed process RSS exceeds execution ceiling')
            except (ValueError, KeyError, OSError) as error:
                result.update(status='invalid_observation', reason=str(error))
        rows.append(dict(case=asset['id'], role=asset['role'], style=style, operation=operation, round=round_id, result=result))
        if len(rows) % 48 == 0:
            print(json.dumps(dict(batches=len(rows), failures=sum(r['result']['status'] != 0 for r in rows))), flush=True)
    load(output)
    prepared_rows(output, record)
    write(output / 'batches.json', rows)
    write(output / 'summary.json', summarise(rows, record['assets']))
    return rows


def summarise(rows, selected):
    expected = {(a['id'], s, op, r) for a, s, op, r in schedule(selected)}
    observed = [(r['case'], r['style'], r['operation'], r['round']) for r in rows]
    if len(observed) != len(expected) or set(observed) != expected:
        raise ValueError('missing, duplicate or reserved measurement coverage')
    points = []
    for asset in selected:
        if asset['role'] != 'development':
            continue
        for style in (0, 1):
            for operation in ('encode', 'decode'):
                batches = [r['result'] for r in rows if (r['case'], r['style'], r['operation']) == (asset['id'], style, operation)]
                valid = [b for b in batches if b['status'] == 0]
                point = dict(case=asset['id'], style=style, operation=operation,
                             statuses=[b['status'] for b in batches], complete=len(valid) == 5)
                if point['complete']:
                    samples = [b['observation']['samples_ns'][0] for b in valid]
                    sizes = [b['observation']['complete_stream_bytes'] for b in valid]
                    point.update(samples_ns=samples, mean_ns=sum(samples) / 5,
                        component_msamples_per_second=[asset['image']['width'] * asset['image']['height'] * 3 * 1000 / n for n in samples],
                        complete_stream_bytes=sizes, raw_storage_ratio=[asset['bytes'] / n for n in sizes],
                        process_peak_rss_bytes=[b['process_peak_rss_bytes'] for b in valid])
                points.append(point)
    return dict(schema_version=1, pack=PACK, points=points,
        complete=all(p['complete'] for p in points), boundary=PROTOCOL['boundary'],
        rss_boundary='fresh whole process including input and verification; separate from codec clock',
        interpretation='Absolute observations only; no comparative ranking or reserve performance')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('phase', choices=['freeze', 'prepare', 'measure'])
    parser.add_argument('--output', type=Path, required=True)
    for name in ('prepared', 'binary', 'codec-source', 'build-provenance', 'decoder', 'decoder-provenance', 'source-views'):
        parser.add_argument('--' + name, type=Path)
    parser.add_argument('--codec-revision')
    parser.add_argument('--cpus', default='0')
    args = parser.parse_args()
    args.output = args.output.resolve()
    if args.phase == 'freeze':
        if any(getattr(args, n) is None for n in ('prepared', 'binary', 'codec_source', 'build_provenance', 'decoder', 'decoder_provenance', 'source_views', 'codec_revision')):
            parser.error('freeze requires all input, build, decoder and source-view identities')
        freeze(args)
    else:
        record = load(args.output)
        rows = (prepare if args.phase == 'prepare' else measure)(args.output, record)
        if any((row.get('result') or row)['status'] != 0 for row in rows):
            raise SystemExit(1)


if __name__ == '__main__':
    main()
