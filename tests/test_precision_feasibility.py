"""Authored offline protocol tests; never launch real codecs or read corpora."""
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

SPEC = importlib.util.spec_from_file_location('precision_acquire', Path(__file__).resolve().parents[1]/'scripts/precision-feasibility.py')
p = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(p)


class ProtocolTests(unittest.TestCase):
    def test_counterbalanced_fixed_schedule_and_counts(self):
        schedule = p.schedule()
        self.assertEqual(len(schedule), 18)
        self.assertEqual(sum(len(p.calls(s)) for s in schedule), 720)
        for sweep in range(3):
            self.assertEqual(sorted(s['cell'] for s in schedule if s['sweep']==sweep), list(range(6)))
        for cell in range(6):
            entries = [s for s in schedule if s['cell']==cell]
            self.assertEqual(len(entries), 3)
            self.assertEqual(sorted((s['index']%6)//2 for s in entries), [0,1,2])
            self.assertEqual(len({s['starting_arm'] for s in entries}), 2)
        for session in schedule:
            rows = p.calls(session)
            self.assertEqual(sum(r['arm']=='A' and r['position']==0 for r in rows), 10)
            for pair in range(20):
                self.assertEqual({r['arm'] for r in rows[2*pair:2*pair+2]}, {'A','B'})

    def test_fixed_complete_products(self):
        assets = [dict(id=prefix+'id-'+product, product=product) for prefix,product in
                  [('106_','RGB8'),('94_','RGB16'),('94_','RGB8')]]
        cells = p.selected_cells(assets)
        self.assertEqual([c['workers'] for c in cells], [1,8]*3)
        self.assertEqual([(c['operation'],c['style'],c['origin']) for c in cells[::2]],
                         [('encode',1,'emuella'),('encode',1,'emuella'),('decode',0,'openjpeg')])
        with self.assertRaises(ValueError):
            p.selected_cells(assets[1:])

    def test_same_request_binary_for_both_metadata_labels(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            folder = root/'session-00'
            folder.mkdir()
            binding = {'build':{'binary':'/same/executable'}}
            cell = {'request':{'operation':'encode'}, 'workers':8}
            observed = []
            def execute(binary, request, directory, cpus):
                observed.append((binary,request,cpus))
                return {'status':0,'observation':{'samples_ns':[10]}}
            with patch.object(p,'verify_call'), patch.object(p,'budget_check'), patch.object(p.refresh,'run_process',side_effect=execute):
                for label in ('A','B'):
                    p.observe(root,binding,folder,cell,dict(round=0,arm=label,position=0),0)
            self.assertEqual(observed[0],observed[1])
            self.assertNotIn('arm',observed[0][1])
            self.assertEqual(p.started_count(root),2)

    def test_failure_retained_consumes_attempt_and_no_overwrite(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            folder = root/'session-00'
            folder.mkdir()
            identity = dict(round=0,arm='A',position=0)
            with patch.object(p,'budget_check'), patch.object(p,'verify_call',side_effect=ValueError('hash changed')):
                row = p.observe(root,{},folder,{},identity,0)
                self.assertEqual(row['result']['status'],'failed_attempt')
                self.assertEqual(p.started_count(root),1)
                self.assertEqual(json.loads((folder/'call-00-A-receipt.json').read_text()),row)
                with self.assertRaises(FileExistsError):
                    p.observe(root,{},folder,{},identity,0)

    def test_caps_stop_before_an_extra_attempt_without_removing_rows(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            marker = root/'retained.json'
            marker.write_text('{}')
            for count, now, size in ((732,0,0),(0,7200*10**9,0),(0,0,p.BYTE_CAP)):
                with patch.object(p,'bytes_used',return_value=size), self.assertRaises(ValueError):
                    p.budget_check(root,0,count,now)
                self.assertTrue(marker.exists())

    def test_identical_production_build_enforced(self):
        build = dict(codec={'source_revision':p.CODEC},encoder_backend='default',scheduling_window='default',
                     command=['--features','classic-compare','--profile','perf'],binary='/same/binary')
        p.verify_build(build)
        for key, value in [('encoder_backend','reference'),('scheduling_window','4W'),('sampling',True),
                           ('command',['--features','simd','--profile','perf'])]:
            with self.assertRaises(ValueError):
                p.verify_build(dict(build,**{key:value}))


if __name__ == '__main__':
    unittest.main()
