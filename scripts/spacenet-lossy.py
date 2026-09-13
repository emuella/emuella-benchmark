#!/usr/bin/env python3
"""Opt-in SpaceNet source-view freeze and one unchanged indexed RGB16 baseline."""
import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import signal
import subprocess
import time


def digest(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def write(path, value):
    with Path(path).open('x') as stream:
        json.dump(value, stream, indent=2, allow_nan=False)
        stream.write('\n')


def bounded_process(command, timeout, **kwargs):
    """Terminate the complete local process group when its fixed budget expires."""
    process = subprocess.Popen(command, start_new_session=True, **kwargs)
    try:
        stdout, stderr = process.communicate(timeout=timeout)
    except subprocess.TimeoutExpired:
        os.killpg(process.pid, signal.SIGKILL)
        process.communicate()
        raise
    return subprocess.CompletedProcess(command, process.returncode, stdout, stderr)


def module(path):
    spec = importlib.util.spec_from_file_location(Path(path).stem, path)
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result


def confined(root, relative):
    path = Path(relative)
    if path.is_absolute() or '..' in path.parts:
        raise ValueError('relative asset path required')
    result = root / path
    if any(p.is_symlink() for p in [result, *result.parents]):
        raise ValueError('symlink in asset path')
    if not result.resolve(strict=True).is_relative_to(root.resolve(strict=True)):
        raise ValueError('asset escapes root')
    return result


def source_arrays(store, asset):
    import numpy as np
    from osgeo import gdal
    gdal.UseExceptions()
    gdal.SetConfigOption('GDAL_PAM_ENABLED', 'NO')
    path = confined(store / 'source', asset['source_path'])
    if digest(path) != asset['source_sha256']:
        raise ValueError('source identity mismatch')
    ds = gdal.OpenEx(str(path), gdal.OF_RASTER | gdal.OF_READONLY, allowed_drivers=['GTiff'])
    image = asset['image']
    if (ds.RasterXSize, ds.RasterYSize, ds.RasterCount) != (image['width'], image['height'], 3):
        raise ValueError('source geometry mismatch')
    values, valid = [], []
    for index in [1, 2, 3]:
        band = ds.GetRasterBand(index)
        if band.DataType != gdal.GDT_UInt16:
            raise ValueError('RGB16 source required')
        pixels = band.ReadAsArray()
        mask = band.GetMaskBand().ReadAsArray() != 0
        nodata = band.GetNoDataValue()
        if nodata is not None:
            mask &= pixels != nodata
        values.append(pixels)
        valid.append(mask)
    return np.stack(values), np.stack(valid)


def freeze(args):
    import numpy as np
    prepared = json.loads(args.prepared.read_text())
    if prepared['pack_id'] != 'common/spacenet-psrgb16':
        raise ValueError('distinct SpaceNet pack required')
    selected = {}
    for asset in sorted(prepared['assets'], key=lambda a: a['id']):
        if asset['role'] == 'development':
            selected.setdefault(asset['bundle_id'], asset)
    if len(selected) != 3:
        raise ValueError('exactly three development AOIs required')
    assets = []
    for asset in selected.values():
        values, valid = source_arrays(args.store, asset)
        ranges = []
        for pixels, mask in zip(values, valid):
            histogram = np.bincount(pixels[mask], minlength=65536)
            cumulative = histogram.cumsum()
            if not cumulative[-1]:
                raise ValueError('empty source-valid stretch population')
            ranges.append([int(np.searchsorted(cumulative, int(np.ceil(cumulative[-1] * q))))
                           for q in (.02, .98)])
        h, w = values.shape[1:]
        if min(w, h) < 256 or w % 4 or h % 4:
            raise ValueError('frozen 256-square scale-four views require compatible source geometry')
        views = [{'x': x, 'y': y, 'width': 256, 'height': 256}
                 for x, y in [(0, 0), (((w - 256) // 8) * 4, ((h - 256) // 8) * 4), (w - 256, h - 256)]]
        assets.append({**asset, 'bands': [1, 2, 3], 'views': views,
                       'stretches': {'percentile_2_98': ranges, 'full_storage': [[0, 65535]] * 3}})
    write(args.output, {'schema': 'spacenet-source-views/1', 'prepared_sha256': digest(args.prepared),
                       'selection': 'lexically first frozen development member per AOI; no reserved exposure',
                       'method': 'source-only exact nearest-rank per-band 2/98 percentiles on GDAL-mask AND nodata valid samples; fixed top-left, centre and bottom-right 256-square views',
                       'scales': [1, 4], 'rmse_limit': 3, 'p99_limit': 12,
                       'bits_per_spatial_pixel': 12, 'bits_per_component_sample': 4,
                       'assets': assets})
    with args.output.with_suffix(args.output.suffix + '.sha256').open('x') as stream:
        stream.write(digest(args.output) + '\n')


def populations(valid, scale):
    import numpy as np
    h, w = valid.shape
    if scale == 1:
        any_valid = all_valid = valid
    else:
        blocks = valid.reshape(h // scale, scale, w // scale, scale)
        any_valid, all_valid = blocks.any(axis=(1, 3)), blocks.all(axis=(1, 3))
    return {'all_pixels': np.ones(any_valid.shape, bool), 'any_valid': any_valid,
            'all_valid': all_valid, 'partial_valid': any_valid & ~all_valid}


def run(args):
    import numpy as np
    views = json.loads(args.views.read_text())
    if digest(args.views) != args.views.with_suffix(args.views.suffix + '.sha256').read_text().strip():
        raise ValueError('frozen source-view identity changed')
    if views['prepared_sha256'] != digest(args.prepared):
        raise ValueError('prepared identity mismatch')
    if views['bits_per_spatial_pixel'] != 12 or views['scales'] != [1, 4] or (views['rmse_limit'], views['p99_limit']) != (3, 12):
        raise ValueError('frozen policy mismatch')
    asset = next(a for a in views['assets'] if a['id'] == args.asset)
    if asset['role'] != 'development' or asset['bands'] != [1, 2, 3]:
        raise ValueError('lossy evaluation is restricted to development RGB')
    expected_asset = next(a for a in json.loads(args.prepared.read_text())['assets'] if a['id'] == args.asset)
    if any(asset[k] != v for k, v in expected_asset.items()):
        raise ValueError('view asset differs from prepared contract')
    build = json.loads(args.build.read_text())
    if subprocess.check_output(['git', '-C', str(args.polyorama), 'rev-parse', 'HEAD'], text=True).strip() != build['polyorama_revision']:
        raise ValueError('quality-tool source revision differs from frozen build')
    if subprocess.check_output(['git', '-C', str(args.polyorama), 'status', '--porcelain']):
        raise ValueError('quality-tool source must be clean')
    for name, path in [('tool', args.tool), ('gdal', args.gdal_library)]:
        if digest(path) != build[name]['sha256']:
            raise ValueError('tool build identity mismatch')
    source = module(args.polyorama / 'tools/viewer-real-scene-source.py')
    quality = module(args.polyorama / 'tools/viewer-real-scene-quality.py')
    acceptance = module(args.polyorama / 'tools/viewer-acceptance-quality.py')
    if Path(args.output_name).name != args.output_name or args.output_name in ('.', '..'):
        raise ValueError('new direct store child required')
    output = args.store / args.output_name
    output.mkdir(exist_ok=False)
    original, validity = source_arrays(args.store, asset)
    representation = output / 'representation'
    command = [str(args.tool), 'prepare', '--retain-incomplete', 'true', '--gdal-library', str(args.gdal_library),
               '--input', str(args.store / 'source' / asset['source_path']), '--output', str(representation),
               '--target', args.asset + '-psrgb16-bpp12', '--bits', '16', '--bands', '1,2,3',
               '--tile', '512', '--levels', '6', '--bpp', '12', '--codec-revision', build['codec_revision']]
    invocation = {'command': command, 'build_sha256': digest(args.build), 'views_sha256': digest(args.views),
                  'prepared_sha256': digest(args.prepared), 'script_sha256': digest(__file__),
                  'reused_tools': {p: digest(args.polyorama / 'tools' / p) for p in
                                   ['viewer-real-scene-source.py', 'viewer-real-scene-quality.py', 'viewer-acceptance-quality.py']},
                  'timeout_seconds': 1800, 'execution_address_space_bytes': 4 << 30,
                  'resource_boundary': 'whole preparation subprocess incl source hashing/read and verification; not codec-operation timing',
                  'attribution': 'SpaceNet Dataset, SpaceNet Partners; DigitalGlobe imagery; CC BY-SA 4.0',
                  'lineage': 'local indexed codec and quality derivatives of locked source; no source sample changes',
                  'environment': {k: os.environ.get(k) for k in ['LD_LIBRARY_PATH', 'GDAL_DATA', 'PROJ_DATA', 'RAYON_NUM_THREADS']}}
    write(output / 'invocation.json', invocation)
    started = time.monotonic()
    try:
        with (output / 'stdout.json').open('x') as out, (output / 'stderr.txt').open('x') as err:
            result = bounded_process(['/usr/bin/time', '-f', '%M', '-o', str(output / 'peak-rss-kib.txt'),
                                     'prlimit', '--as=' + str(4 << 30), '--', *command], stdout=out, stderr=err, timeout=1800,
                                    env={**os.environ, 'RAYON_NUM_THREADS': '1'})
        status = 'prepared' if result.returncode == 0 else 'preparation-failed'
        code = result.returncode
    except subprocess.TimeoutExpired:
        status, code = 'timeout', None
    report = {'status': status, 'exit': code, 'asset': args.asset, 'wall_seconds': time.monotonic() - started,
              'numerical_only': True, 'reserved_evaluation': False, 'passed': False}
    rss = output / 'peak-rss-kib.txt'
    if rss.exists() and rss.read_text().splitlines() and rss.read_text().splitlines()[-1].isdigit():
        report['preparation_peak_rss_bytes'] = int(rss.read_text().splitlines()[-1]) * 1024
    if status != 'prepared':
        write(output / 'quality.json', report)
        return
    manifest = json.loads((representation / 'manifest.json').read_text())
    identity = manifest['identity']
    if identity['source_sha256'] != asset['source_sha256'] or identity['bands'] != [1, 2, 3]:
        raise ValueError('representation source identity mismatch')
    profile = identity['profile']
    for key, expected in [('width', asset['image']['width']), ('height', asset['image']['height']),
                          ('components', 3), ('bits_per_sample', 16), ('bits_per_pixel', 12),
                          ('decomposition_levels', 6), ('tile_edge', 512)]:
        if profile[key] != expected:
            raise ValueError('applied indexed profile mismatch: ' + key)
    report['storage'] = acceptance.storage(representation)
    report['preparation_metrics'] = json.loads((output / 'stdout.json').read_text())[1]
    records = []
    for ordinal, view in enumerate(asset['views']):
        raw = output / f'view-{ordinal}.u16le'
        command = [str(args.tool), 'reference-export', '--representation', str(representation), '--output', str(raw)]
        for key in ['x', 'y', 'width', 'height']:
            command += ['--' + key, str(view[key])]
        try:
            decoded_result = bounded_process(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=120)
            (output / f'view-{ordinal}.stdout').write_bytes(decoded_result.stdout)
            (output / f'view-{ordinal}.stderr').write_bytes(decoded_result.stderr)
            if decoded_result.returncode:
                records.append({'view': view, 'status': 'decode-failed', 'exit': decoded_result.returncode})
                continue
        except subprocess.TimeoutExpired:
            records.append({'view': view, 'status': 'decode-timeout'})
            continue
        x, y, w, h = (view[k] for k in ['x', 'y', 'width', 'height'])
        orig = original[:, y:y+h, x:x+w]
        valid = validity[:, y:y+h, x:x+w]
        dec = np.fromfile(raw, dtype='<u2').reshape(h, w, 3).transpose(2, 0, 1)
        errors = [{'all': quality.errors(orig[c], dec[c], np.ones((h, w), bool)),
                   'valid': quality.errors(orig[c], dec[c], valid[c]),
                   'invalid': quality.errors(orig[c], dec[c], ~valid[c])} for c in range(3)]
        displays = []
        for scale in views['scales']:
            reduced = [v if scale == 1 else v.reshape(3, h//scale, scale, w//scale, scale).mean(axis=(2, 4))
                       for v in [orig, dec]]
            for name, ranges in asset['stretches'].items():
                left, right = [source.stretch(v, ranges) for v in reduced]
                metrics = [{key: quality.errors(left[:, :, c], right[:, :, c], mask)
                            for key, mask in populations(valid[c], scale).items()} for c in range(3)]
                passed = all(m['any_valid'] is None or (m['any_valid']['rmse'] <= 3 and
                             m['any_valid']['p99_absolute'] <= 12) for m in metrics)
                displays.append({'scale': scale, 'stretch': name, 'bands': metrics, 'passed': passed})
        records.append({'view': view, 'status': 'completed', 'source_errors': errors, 'display': displays,
                        'decoded_sha256': digest(raw)})
    report.update(status='completed', records=records)
    report['quality_passed'] = all(r['status'] == 'completed' and all(d['passed'] for d in r['display']) for r in records)
    report['passed'] = report['quality_passed'] and all(report['storage'][k] for k in
                                                      ['payload_eligible', 'descriptors_eligible', 'manifest_eligible'])
    report['limitations'] = 'Frozen regional numerical baseline only; no independent indexed decoder, full-viewer, human or analytical suitability claim. Quality-only representation; exact original validity retained separately.'
    write(output / 'quality.json', report)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest='command', required=True)
    for name in ['freeze', 'run']:
        cmd = commands.add_parser(name)
        cmd.add_argument('--store', type=Path, required=True)
        cmd.add_argument('--prepared', type=Path, required=True)
        if name == 'freeze':
            cmd.add_argument('--output', type=Path, required=True)
        else:
            for field in ['views', 'build', 'tool', 'gdal-library', 'polyorama']:
                cmd.add_argument('--' + field, type=Path, required=True)
            cmd.add_argument('--asset', required=True)
            cmd.add_argument('--output-name', required=True)
    args = parser.parse_args()
    (freeze if args.command == 'freeze' else run)(args)


if __name__ == '__main__':
    main()
