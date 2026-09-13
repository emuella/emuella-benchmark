"""Offline authored coverage for source-valid reduction and reserved exclusion."""
import importlib.util
from pathlib import Path
import tempfile
import unittest

SPEC = importlib.util.spec_from_file_location('spacenet_lossy', Path(__file__).parents[1] / 'scripts/spacenet-lossy.py')
SCRIPT = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(SCRIPT)


class LossyTests(unittest.TestCase):
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
