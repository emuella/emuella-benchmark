import importlib.util
from pathlib import Path
import unittest

SPEC = importlib.util.spec_from_file_location('refresh', Path(__file__).resolve().parents[1] / 'scripts/openjpeg-refresh.py')
refresh = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(refresh)

class RefreshCoverageTests(unittest.TestCase):
    def rows(self):
        fields=('case_id','style','workers','operation','origin','round','codec')
        return [dict(zip(fields,key)) for key in refresh.expected_keys(['first','second'],20)]

    def test_every_stream_origin_and_codec_required(self):
        rows=self.rows()
        self.assertEqual(len(rows),960)
        refresh.validate_rows(rows,['first','second'],20)
        for field,value in [('origin','emuella'),('codec','openjpeg'),('workers',8),('round',19)]:
            with self.subTest(field=field):
                with self.assertRaisesRegex(ValueError,'missing'):
                    refresh.validate_rows([r for r in rows if r[field]!=value],['first','second'],20)

    def test_duplicate_and_unknown_case_rejected(self):
        rows=self.rows()
        with self.assertRaisesRegex(ValueError,'duplicate'):
            refresh.validate_rows(rows+[rows[0]],['first','second'],20)
        rows[0]=dict(rows[0],case_id='unplanned')
        with self.assertRaisesRegex(ValueError,'unexpected'):
            refresh.validate_rows(rows,['first','second'],20)

    def test_probe_cannot_satisfy_twenty_round_protocol(self):
        fields=('case_id','style','workers','operation','origin','round','codec')
        rows=[dict(zip(fields,key)) for key in refresh.expected_keys(['first'],1)]
        refresh.validate_rows(rows,['first'],1)
        with self.assertRaisesRegex(ValueError,'missing'):
            refresh.validate_rows(rows,['first'],20)

    def test_encode_only_anchor_has_every_fixed_style_worker_and_codec(self):
        fields=('case_id','style','workers','operation','origin','round','codec')
        rows=[dict(zip(fields,key)) for key in refresh.expected_keys(['first'],20,True)]
        self.assertEqual(len(rows),160)
        self.assertEqual({r['operation'] for r in rows},{'encode'})
        refresh.validate_rows(rows,['first'],20,True)
        with self.assertRaisesRegex(ValueError,'missing'):
            refresh.validate_rows(rows,['first'],20)
        with self.assertRaisesRegex(ValueError,'missing'):
            refresh.validate_rows(rows[:-1],['first'],20,True)

if __name__=='__main__':
    unittest.main()
