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
