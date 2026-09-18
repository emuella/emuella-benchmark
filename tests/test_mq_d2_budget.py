import importlib.util
import json
from pathlib import Path
import tempfile
import time
import unittest
from unittest.mock import patch

SPEC=importlib.util.spec_from_file_location('budget',Path(__file__).resolve().parents[1]/'scripts/mq-d2-budget.py')
budget=importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(budget)


class BudgetTests(unittest.TestCase):
    def test_restart_preserves_call_and_wall_limits(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory)
            config=root/'budget.json'
            config.write_text(json.dumps(dict(policy='mq-d2-incremental-confirmation/v1',protected_output_roots=[],scratch_root=str(root))))
            b=budget.Budget(config)
            b.before_call()
            budget.Budget(config).before_call()
            self.assertEqual(json.loads(b.state_path.read_text())['started_calls'],2)
            for calls,started in [(800,time.time()),(0,time.time()-7200)]:
                b.state_path.write_text(json.dumps(dict(started_calls=calls,started_unix=started)))
                with self.assertRaises(ValueError): b.before_call()

    def test_storage_cap_blocks_call_without_consuming_slot(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory)
            config=root/'budget.json'
            config.write_text(json.dumps(dict(policy='mq-d2-incremental-confirmation/v1',protected_output_roots=[str(root)],scratch_root=str(root))))
            b=budget.Budget(config)
            with patch.object(budget,'size',return_value=2*1024**3), self.assertRaises(ValueError):
                b.before_call()
            self.assertFalse(b.state_path.exists())


class FrontEndBudgetTests(unittest.TestCase):
    def test_frozen_front_end_caps_and_shared_restart_state(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory); config = root/'budget.json'
            config.write_text(json.dumps(dict(policy='classic-encode-front-end/v1',protected_output_roots=[str(root/'protected')],scratch_root=str(root/'scratch'))))
            b = budget.Budget(config, 'classic-encode-front-end/v1')
            self.assertEqual((b.calls,b.seconds,b.protected_bytes,b.scratch_bytes),(1600,14400,4*1024**3,30*1024**3))
            b.before_call(); budget.Budget(config).before_call()
            self.assertEqual(json.loads(b.state_path.read_text())['started_calls'],2)
            for calls,elapsed in [(1600,0),(0,14400-119)]:
                b.state_path.write_text(json.dumps(dict(started_calls=calls,started_unix=time.time()-elapsed)))
                with self.assertRaisesRegex(ValueError,'incomplete'): b.before_call()
            b.state_path.unlink()
            for protected,scratch in [(4*1024**3,0),(0,30*1024**3)]:
                with patch.object(budget,'size',side_effect=lambda p: protected if p.endswith('protected') else scratch):
                    with self.assertRaisesRegex(ValueError,'incomplete'): b.before_call()
                    self.assertFalse(b.state_path.exists())
            with self.assertRaisesRegex(ValueError,'policy differs'):
                budget.Budget(config,'mq-d2-incremental-confirmation/v1')
