"""Offline authored coverage for SpaceNet admission and reserve protection."""
import copy
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest import mock

spec = importlib.util.spec_from_file_location('spacenet', Path(__file__).resolve().parents[1] / 'scripts/spacenet-classic.py')
runner = importlib.util.module_from_spec(spec)
spec.loader.exec_module(runner)


class SpaceNetTests(unittest.TestCase):
    def fixture(self, root):
        selected = []
        for group in range(4):
            for chip in range(4):
                name = f'RGB-PanSharpen_AOI_{group}_City_img{chip}'
                # Distinct U16 values and a distinct per-band invalid position.
                pixels = bytes([group, chip, 255, 255, 0, 128]) * 16
                validity = bytes([1, 0, 1]) * 16
                (root / (name + '.raw')).write_bytes(pixels)
                (root / (name + '.mask')).write_bytes(validity)
                selected.append(dict(id=name, bundle_id=f'AOI_{group}_City', product='RGB16',
                    source_kind='supplier-pansharpened-rgb16', role='reserved' if group == 3 else 'development',
                    path=name + '.raw', bytes=len(pixels), sha256=hashlib.sha256(pixels).hexdigest(),
                    image=dict(width=4, height=4, components=3, precision=16, signed=False),
                    validity=dict(path=name + '.mask', bytes=len(validity), sha256=hashlib.sha256(validity).hexdigest())))
        record = dict(schema_version=1, pack_id=runner.PACK, version="1", assets=selected)
        (root / 'prepared.json').write_text(json.dumps(record))
        return record

    def test_original_pack_and_per_band_contract(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            record = self.fixture(root)
            self.assertEqual(runner.assets(root), record['assets'])
            for damage in ('pack', 'role', 'split_group', 'precision', 'validity_length', 'duplicate', 'path'):
                with self.subTest(damage=damage):
                    bad = copy.deepcopy(record)
                    first = bad['assets'][0]
                    if damage == 'pack': bad['pack_id'] = 'common/rareplanes-expanded'
                    elif damage == 'role': first['role'] = 'validation'
                    elif damage == 'split_group': first['role'] = 'reserved'
                    elif damage == 'precision': first['image']['precision'] = 8
                    elif damage == 'validity_length': first['validity']['bytes'] //= 3
                    elif damage == 'duplicate': bad['assets'][1]['id'] = first['id']
                    else: first['path'] = '../outside.raw'
                    (root / 'prepared.json').write_text(json.dumps(bad))
                    with self.assertRaises(ValueError): runner.assets(root)

    def test_changed_raw_and_mask_rejected(self):
        for field in ('path', 'validity'):
            with self.subTest(field=field), tempfile.TemporaryDirectory() as temp:
                root = Path(temp)
                record = self.fixture(root)
                asset = record['assets'][0]
                path = asset['path'] if field == 'path' else asset['validity']['path']
                (root / path).write_bytes(b'corrupted')
                with self.assertRaises(ValueError): runner.assets(root)

    def test_schedule_and_summary_never_admit_reserved_performance(self):
        with tempfile.TemporaryDirectory() as temp:
            selected = self.fixture(Path(temp))['assets']
            schedule = runner.schedule(selected)
            self.assertEqual(len(schedule), 240)
            self.assertTrue(all(a['role'] == 'development' for a, _, _, _ in schedule))
            rows = [dict(case=a['id'], style=s, operation=op, round=r,
                         result=dict(status=0, observation=dict(samples_ns=[1000], complete_stream_bytes=48),
                                     process_peak_rss_bytes=1024)) for a, s, op, r in schedule]
            summary = runner.summarise(rows, selected)
            self.assertTrue(summary['complete'])
            self.assertEqual(len(summary['points']), 48)
            self.assertEqual(summary['points'][0]['raw_storage_ratio'], [2.0] * 5)
            for bad in (rows[:-1], rows + [rows[0]], [dict(rows[0], case=selected[-1]['id'])] + rows[1:]):
                with self.assertRaises(ValueError): runner.summarise(bad, selected)
            rows[0]['result'] = dict(status='unsupported')
            summary = runner.summarise(rows, selected)
            self.assertFalse(summary['complete'])
            self.assertNotIn('mean_ns', summary['points'][0])
            self.assertIn('unsupported', summary['points'][0]['statuses'])

    def test_untimed_subprocess_retains_failure_without_resource_fields(self):
        with tempfile.TemporaryDirectory() as temp:
            output = Path(temp) / 'process'
            status = runner.untimed(['/bin/sh', '-c', 'echo authored-error >&2; exit 7'], output,
                                    [min(os.sched_getaffinity(0))])
            self.assertEqual(status, 7)
            self.assertEqual((output / 'stderr.txt').read_text(), 'authored-error\n')
            self.assertFalse((output / 'resources.txt').exists())
            self.assertNotIn('/usr/bin/time', json.loads((output / 'command.json').read_text()))
            with self.assertRaises(FileExistsError):
                runner.untimed(['/bin/true'], output, [min(os.sched_getaffinity(0))])

    def test_complete_untimed_preparation_checks_independent_full_samples(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            prepared = root / 'prepared'; prepared.mkdir()
            output = root / 'experiment'; output.mkdir()
            selected = self.fixture(prepared)['assets']
            record = dict(prepared=str(prepared), assets=selected, cpus=[0],
                          binary=dict(path='authored-worker', sha256='abc'), decoder=dict(path='authored-decoder'))

            def execute(command, directory, cpus):
                directory.mkdir()
                if command[0] == 'authored-worker':
                    req = json.loads(Path(command[1]).read_text())
                    Path(req['stream_path']).write_bytes(b'authored stream')
                    observation = dict(req, binary_sha256='abc', native_exact=True, rct=True,
                        parallel=True, simd=False, warmup=0, samples_ns=[], complete_stream_bytes=15,
                        stream_sha256=runner.digest(req['stream_path']))
                    (directory / 'stdout.txt').write_text(json.dumps(observation))
                else:
                    req = json.loads((directory.parent / 'request.json').read_text())
                    pixels = Path(req['raw_path']).read_bytes()
                    big = bytearray(len(pixels)); big[::2], big[1::2] = pixels[1::2], pixels[::2]
                    Path(command[command.index('-o') + 1]).write_bytes(b'P6\n4 4\n65535\n' + big)
                    self.assertIn('-quiet', command)
                return 0

            with mock.patch.object(runner, 'untimed', side_effect=execute), mock.patch.object(runner, 'load', return_value=record):
                rows = runner.prepare(output, record)
            self.assertEqual(len(rows), 32)
            self.assertTrue(all(row['independent_exact'] for row in rows))
            self.assertEqual(len([r for r in rows if r['role'] == 'reserved']), 8)
            self.assertFalse(any('process_peak_rss_bytes' in r or 'process_wall_ns' in r for r in rows))
            self.assertEqual(len(runner.prepared_rows(output, record)), 32)
            Path(rows[-1]['independent_output']['path']).write_bytes(b'changed')
            with self.assertRaises(ValueError): runner.prepared_rows(output, record)

    def test_preparation_rejects_sample_clocks_and_changed_profile(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            selected = self.fixture(root)['assets']
            (root / 'streams').mkdir()
            req = runner.classic.request(selected[0], root, root, 0, 1, 'prepare')
            Path(req['stream_path']).write_bytes(b'authored stream')
            observation = dict(req, binary_sha256='abc', native_exact=True, rct=True, parallel=True,
                               simd=False, warmup=0, samples_ns=[], complete_stream_bytes=15,
                               stream_sha256=runner.digest(req['stream_path']))
            runner.validate_observation(req, observation, 'abc', False)
            for field, value in (('samples_ns', [1000]), ('rct', False), ('simd', True), ('workers', 8), ('native_exact', False)):
                with self.subTest(field=field), self.assertRaises(ValueError):
                    runner.validate_observation(req, dict(observation, **{field: value}), 'abc', False)


if __name__ == '__main__':
    unittest.main()
