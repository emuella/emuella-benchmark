"""Authored worker lifecycle and incomplete-evidence checks, no external assets."""
import importlib.util
import json
import os
from pathlib import Path
import tempfile
import unittest

spec = importlib.util.spec_from_file_location('classic', Path(__file__).resolve().parents[1] / 'scripts/real-scene-classic.py')
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class ClassicTests(unittest.TestCase):
    def test_failed_worker_is_retained_without_success_observation(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            result = module.execute(Path('/bin/sh'), {}, root/'batch', [min(os.sched_getaffinity(0))], extra_args=['-c','exit 7'])
            self.assertEqual(result['status'], 7)
            self.assertNotIn('observation', result)
            self.assertEqual(json.loads((root/'batch/result.json').read_text()), result)
            self.assertTrue((root/'batch/stderr.txt').is_file())
            with self.assertRaises(FileExistsError):
                module.execute(Path('/bin/sh'), {}, root/'batch', [min(os.sched_getaffinity(0))], extra_args=['-c','exit 0'])

    def test_incomplete_coverage_never_invokes_estimator(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            module.write(root/'batches.json', [dict(case='authored',operation='encode',style=0,workers=1,result=dict(status=0))])
            module.analyse(root, Path('/nonexistent-estimator'))
            rows = json.loads((root/'comparisons.json').read_text())
            self.assertEqual(len(rows), 10)
            self.assertTrue(all(r['verdict']=='invalid' for r in rows))
