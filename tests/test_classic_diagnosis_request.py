import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
ENTRY = ROOT / 'scripts/classic-diagnosis-request.py'
SPEC = importlib.util.spec_from_file_location('diagnosis_request', ENTRY)
diagnosis = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(diagnosis)


class ExistingStreamRequestTests(unittest.TestCase):
    def config(self, root):
        raw_hash = 'a' * 64
        stream_hash = 'b' * 64
        stream = root / 'streams/streams/authored-emuella-s0.j2k'
        return dict(kind='preflight', asset=dict(id='authored', path='missing.raw', sha256=raw_hash,
                    image=dict(width=19, height=17, components=1, precision=8)),
                    prepared=str(root / 'prepared'), streams=str(root / 'streams'),
                    origin='emuella', codec='emuella', style=0, workers=1, round=0,
                    stream_identity=dict(case_id='authored', origin='emuella', style=0,
                                         raw_sha256=raw_hash, stream_path=str(stream),
                                         stream_sha256=stream_hash))

    def test_dry_run_uses_explicit_identity_without_payload_or_worker(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            config = self.config(root)
            refresh = diagnosis.refresh_module()
            with patch.object(refresh, 'sha', side_effect=AssertionError('payload read')), \
                    patch.object(diagnosis, 'refresh_module', return_value=refresh):
                # The CLI also uses a fresh import; nonexistent payload paths prove
                # that its request construction needs only the metadata file.
                call = diagnosis.build(config)
            path = root / 'metadata.json'
            path.write_text(json.dumps(config))
            process = subprocess.run([sys.executable, str(ENTRY), '--config', str(path)],
                                     text=True, capture_output=True, check=True)
            self.assertEqual(json.loads(process.stdout), call)
            self.assertEqual(call['request']['operation'], 'encode')
            self.assertEqual(call['request']['stream_sha256'], 'b' * 64)
            self.assertFalse(call['timing_eligible'])
            self.assertFalse(Path(call['request']['raw_path']).exists())
            self.assertFalse(Path(call['request']['stream_path']).exists())
            ordinary = diagnosis.build(dict(config, kind='ordinary'))
            self.assertTrue(ordinary['timing_eligible'])
            self.assertEqual(ordinary['request'], call['request'])
            observation = dict(call['request'], samples_ns=[123])
            result = dict(status=0, observation=observation)
            self.assertEqual(refresh.ordinary_samples_from_existing_stream_call(call, result), [])
            self.assertEqual(refresh.ordinary_samples_from_existing_stream_call(ordinary, result), [123])
            with self.assertRaisesRegex(ValueError, 'identity differs'):
                refresh.ordinary_samples_from_existing_stream_call(
                    ordinary, dict(status=0, observation=dict(observation, stream_sha256='c' * 64)))

    def test_missing_or_inconsistent_existing_identity_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            config = self.config(Path(directory))
            identity = config['stream_identity']
            changes = [None, {}, dict(identity, raw_sha256='c' * 64),
                       dict(identity, stream_path='/wrong/stream.j2k'),
                       dict(identity, case_id='other'), dict(identity, origin='openjpeg'),
                       dict(identity, style=1), dict(identity, stream_sha256='wrong'),
                       dict(identity, stream_sha256='C' * 64)]
            for change in changes:
                with self.subTest(change=change), self.assertRaises(ValueError):
                    diagnosis.build(dict(config, stream_identity=change))
            for kind in ('prepare', 'diagnostic', ''):
                with self.subTest(kind=kind), self.assertRaises(ValueError):
                    diagnosis.build(dict(config, kind=kind))

    def test_prepare_keeps_create_new_contract(self):
        with tempfile.TemporaryDirectory() as directory:
            config = self.config(Path(directory))
            refresh = diagnosis.refresh_module()
            request = refresh.make_request(config['asset'], Path(config['prepared']),
                                           Path(config['streams']), 'emuella', 'emuella',
                                           0, 1, 'prepare', 0)
            self.assertEqual(request['operation'], 'prepare')
            self.assertNotIn('stream_sha256', request)


if __name__ == '__main__':
    unittest.main()
