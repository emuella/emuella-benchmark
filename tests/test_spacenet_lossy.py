"""Offline authored coverage for source-valid reduction and reserved exclusion."""
import importlib.util
import json
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

SPEC = importlib.util.spec_from_file_location('spacenet_lossy', Path(__file__).parents[1] / 'scripts/spacenet-lossy.py')
SCRIPT = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(SCRIPT)


class LossyTests(unittest.TestCase):
    def test_freeze_never_reads_reserved_sources(self):
        try:
            import numpy as np
        except ImportError:
            self.skipTest('optional NumPy source-quality dependency')
        with tempfile.TemporaryDirectory() as name:
            root = Path(name)
            prepared = root / 'prepared.json'
            assets = [{'id': f'chip-{i}', 'bundle_id': str(i),
                       'role': 'reserved' if i == 3 else 'development'} for i in range(4)]
            prepared.write_text(json.dumps({'pack_id': 'common/spacenet-psrgb16', 'assets': assets}))
            values = np.ones((3, 260, 260), dtype=np.uint16)
            with patch.object(SCRIPT, 'source_arrays', return_value=(values, values.astype(bool))) as read:
                SCRIPT.freeze(SimpleNamespace(prepared=prepared, store=root, output=root / 'views.json'))
            self.assertEqual([call.args[1]['id'] for call in read.call_args_list], ['chip-0', 'chip-1', 'chip-2'])
            self.assertEqual(SCRIPT.digest(root / 'views.json'), (root / 'views.json.sha256').read_text().strip())

    def test_path_cannot_escape_or_follow_symlinks(self):
        with tempfile.TemporaryDirectory() as name:
            root = Path(name)
            (root / 'source').write_text('authored')
            (root / 'link').symlink_to(root / 'source')
            for path in ['../source', '/source', 'link']:
                with self.assertRaises(ValueError):
                    SCRIPT.confined(root, path)
            self.assertEqual(SCRIPT.confined(root, 'source'), root / 'source')

    def test_partial_valid_cells_retain_any_and_all(self):
        try:
            import numpy as np
        except ImportError:
            self.skipTest('optional NumPy source-quality dependency')
        valid = np.zeros((8, 8), dtype=bool)
        valid[:4, :4] = True
        valid[4, 4] = True
        result = SCRIPT.populations(valid, 4)
        np.testing.assert_array_equal(result['any_valid'], [[True, False], [False, True]])
        np.testing.assert_array_equal(result['all_valid'], [[True, False], [False, False]])
        np.testing.assert_array_equal(result['partial_valid'], [[False, False], [False, True]])


if __name__ == '__main__':
    unittest.main()
