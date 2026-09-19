import importlib.util
from pathlib import Path
import unittest
import contextlib
import io
import json
import tempfile
from types import SimpleNamespace
from unittest.mock import Mock, patch

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

class FrontEndAnchorTests(unittest.TestCase):
    def assets(self):
        return [dict(id=f'{prefix}-{p}',product=p,path='authored.raw',sha256='digest')
                for prefix in ('94_a','106_b') for p in ('PAN16','MS16','RGB8','RGB16')] + [dict(id='105_c-RGB8',product='RGB8',path='authored.raw',sha256='digest')]

    def test_selection_and_manifest_reject_other_products_and_incomplete_bindings(self):
        assets = self.assets()
        selected = refresh.front_end_assets(assets)
        self.assertEqual([a['id'] for a in selected],['106_b-RGB8'])
        for changed in [assets[:-1], assets+[assets[0]], [dict(a,product='PAN16') for a in assets]]:
            with self.assertRaises(ValueError): refresh.front_end_assets(changed)
        manifest = dict(assets=selected,case_ids=['106_b-RGB8'],encode_only=True,probe=False,rounds=20,
                        styles=[0,1],workers=[1,8],reused_streams={f'/owner/streams/106_b-RGB8-{c}-s{s}.j2k':'digest' for c in refresh.CODECS for s in refresh.STYLES},
                        reused_records={f'/owner/{name}.json':'digest' for name in ('manifest','measurement','preparations')})
        refresh.validate_front_end_manifest(manifest)
        for delta in [dict(encode_only=False),dict(probe=True),dict(rounds=19),dict(workers=[1]),
                      dict(case_ids=['94_a-RGB8']),dict(reused_streams={}),dict(reused_records={}),dict(assets=[assets[0]])]:
            with self.assertRaises(ValueError): refresh.validate_front_end_manifest(dict(manifest,**delta))

    def test_budget_and_immutable_encode_only_are_required_before_launch(self):
        args = dict(study='front-end',probe=False,encode_only=True,streams=Path('streams'),budget=Path('budget'))
        for delta in [dict(probe=True),dict(encode_only=False),dict(streams=None),dict(budget=None)]:
            with patch.object(refresh,'run_process') as run, self.assertRaises(ValueError):
                refresh.measure(SimpleNamespace(**dict(args,**delta)))
            run.assert_not_called()
        with tempfile.TemporaryDirectory() as directory:
            config = Path(directory)/'budget.json'
            config.write_text(json.dumps(dict(policy='mq-d2-incremental-confirmation/v1')))
            with self.assertRaisesRegex(ValueError,'policy differs'):
                refresh.measure(SimpleNamespace(**dict(args,budget=config)))

    def test_front_end_rejects_diagnostics_selectors_and_changed_worker_source(self):
        args = SimpleNamespace(study='front-end',probe=False,encode_only=True,streams=Path('streams'),budget=Path('budget'),build=Path('build'))
        source = dict(source_files_sha256={'workers/src/worker.rs':'same'})
        ordinary = dict(benchmark=source,encoder_backend='default',scheduling_window='default')
        for delta in [dict(sampling=True),dict(execution_diagnostics=True),dict(allocation_diagnostics=True),
                      dict(encoder_backend='packed'),dict(scheduling_window='4W'),
                      dict(benchmark=dict(source_files_sha256={'workers/src/worker.rs':'changed'}))]:
            with patch.object(refresh,'module',return_value=SimpleNamespace(Budget=Mock())), \
                 patch.object(refresh.classic,'clean_source',return_value=source), \
                 patch.object(refresh,'bind',return_value=dict(ordinary,**delta)), patch.object(refresh,'run_process') as run:
                with self.assertRaises(ValueError): refresh.measure(args)
                run.assert_not_called()

    def test_driver_runs_only_160_budgeted_adjacent_calls_and_binds_analysis(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root/'source').mkdir(); (root/'source/LICENSE.txt').write_text('Authored test notice')
            args = SimpleNamespace(study='front-end',probe=False,encode_only=True,streams=root/'streams-owner',budget=root/'budget.json',
                                   build=root/'build.json',prepared=root/'prepared',output=root/'observations',cpus='0,1,2,3,4,5,6,7')
            source = dict(source_files_sha256={'workers/src/worker.rs':'same','scripts/openjpeg-refresh.py':'new'})
            build = dict(benchmark=dict(source_files_sha256={'workers/src/worker.rs':'same','scripts/openjpeg-refresh.py':'old'}),
                         encoder_backend='default',scheduling_window='default',binary='authored-worker')
            events = []
            budget = SimpleNamespace(before_call=lambda:events.append('budget'))
            def run(binary,request,path,cpus):
                events.append(request)
                return dict(status=1)
            def request(asset,prepared,streams,origin,codec,style,workers,operation,round_id):
                return dict(case_id=asset['id'],codec=codec,style=style,workers=workers,operation=operation,round=round_id)
            def digest(path):
                return 'f627ad059128fa5246a21e25759c1d33e35c4bb6287d636c4b970f7df57e7eba' if str(path).endswith('LICENSE.txt') else 'digest'
            with patch.object(refresh,'module',return_value=SimpleNamespace(Budget=Mock(return_value=budget))), \
                 patch.object(refresh.classic,'clean_source',return_value=source), patch.object(refresh,'bind',return_value=build), \
                 patch.object(refresh.classic,'assets',return_value=self.assets()), patch.object(refresh,'sha',side_effect=digest), \
                 patch.object(refresh.os,'sched_getaffinity',return_value=set(range(8))), patch.object(refresh,'cpu_identity',return_value={}), \
                 patch.object(refresh,'make_request',side_effect=request), patch.object(refresh,'run_process',side_effect=run), \
                 contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(refresh.measure(args),4)
                manifest = json.loads((args.output/'manifest.json').read_text())
                measurement = json.loads((args.output/'measurement.json').read_text())
                self.assertEqual(len(events),320)
                self.assertTrue(all(e=='budget' for e in events[::2]))
                calls = events[1::2]
                self.assertEqual({r['case_id'] for r in calls},{'106_b-RGB8'})
                self.assertEqual({r['operation'] for r in calls},{'encode'})
                self.assertTrue(all(p['result'].get('reused') for p in measurement['preparations']))
                self.assertFalse(measurement['complete'])
                refresh.validate_rows(measurement['rows'],manifest['case_ids'],20,True)
                for start in range(0,160,2):
                    first,second = calls[start:start+2]
                    self.assertEqual([first['codec'],second['codec']],list(refresh.CODECS if first['round']%2==0 else reversed(refresh.CODECS)))
                    self.assertEqual({k:v for k,v in first.items() if k!='codec'},{k:v for k,v in second.items() if k!='codec'})
                with self.assertRaisesRegex(ValueError,'study differs'):
                    refresh.analyse(args.output,root/'unused-estimator')
                measurement['rows'].pop()
                (args.output/'measurement.json').write_text(json.dumps(measurement))
                with self.assertRaisesRegex(ValueError,'missing planned'):
                    refresh.analyse(args.output,root/'unused-estimator','front-end')


if __name__=='__main__':
    unittest.main()
