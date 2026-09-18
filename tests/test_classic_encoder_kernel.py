import importlib.util
import contextlib
import io
import json
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest

SPEC=importlib.util.spec_from_file_location('kernel',Path(__file__).resolve().parents[1]/'scripts/classic-encoder-kernel.py')
kernel=importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(kernel)


class KernelCoverageTests(unittest.TestCase):
    def fixture(self, phase):
        assets=[dict(id=f'{prefix}-{p}',product=p) for prefix in ('94_a','106_b')
                for p in ('PAN16','MS16','RGB8','RGB16')]+[dict(id='105_c-RGB8',product='RGB8')]
        cases=[dict(case_id=a['id'],style=s,workers=w,operation=op,origin=o)
               for a,s,w,op,o in kernel.contrasts(assets,phase)]
        rounds=3 if phase=='screen' else 20
        manifest=dict(phase=phase,rounds=rounds,assets=assets,contrasts=cases)
        rows=[dict(c,round=r,arm=arm,result=dict(status=0)) for c in cases
              for r in range(rounds) for arm in kernel.ARMS]
        return manifest,rows

    def test_screen_excludes_confirmation_and_cannot_promote(self):
        manifest,rows=self.fixture('screen')
        self.assertEqual(len(rows),36)
        self.assertTrue(all(r['case_id'].startswith('94_') and r['workers']==1 for r in rows))
        kernel.validate_rows(manifest,rows)
        with self.assertRaises(ValueError):
            kernel.validate_rows(dict(manifest,phase='confirm'),rows)

    def test_confirmation_requires_every_arm_round_style_and_worker(self):
        manifest,rows=self.fixture('confirm')
        self.assertEqual(len(rows),1920)
        kernel.validate_rows(manifest,rows)
        for field,value in [('arm','reference'),('round',19),('style',1),('workers',8),('operation','decode')]:
            with self.subTest(field=field),self.assertRaises(ValueError):
                kernel.validate_rows(manifest,[r for r in rows if r[field]!=value])
        with self.assertRaises(ValueError):
            kernel.validate_rows(manifest,rows+[rows[0]])

    def test_failure_remains_a_required_observation(self):
        manifest,rows=self.fixture('confirm')
        rows[0]['result']['status']='timeout'
        kernel.validate_rows(manifest,rows)
        with self.assertRaises(ValueError):
            kernel.validate_rows(manifest,rows[1:])

    def test_geographic_reserve_cannot_enter_spacenet_timing(self):
        assets=[dict(id=f'RGB-PanSharpen_AOI_2_Vegas_img{i}',role='development') for i in range(12)]
        self.assertEqual(len(kernel.contrasts(assets,'spacenet')),24)
        for delta in [dict(role='reserved'),dict(id='RGB-PanSharpen_AOI_5_Khartoum_img1')]:
            changed=[dict(a) for a in assets];changed[0].update(delta)
            with self.assertRaises(ValueError):kernel.contrasts(changed,'spacenet')

    def test_parallel_screen_and_fixed_spacenet_worker_coverage(self):
        manifest, _ = self.fixture('screen')
        cases=kernel.contrasts(manifest['assets'],'screen','parallel')
        self.assertEqual(len(cases),12)
        self.assertEqual({c[2] for c in cases},{1,8})
        manifest.update(study='parallel',contrasts=[dict(case_id=a['id'],style=s,workers=w,operation=op,origin=o) for a,s,w,op,o in cases])
        rows=[dict(c,round=r,arm=arm,result=dict(status=0)) for c in manifest['contrasts'] for r in range(3) for arm in kernel.ARMS]
        self.assertEqual(len(rows),72)
        kernel.validate_rows(manifest,rows)
        with self.assertRaises(ValueError):kernel.validate_rows(manifest,[r for r in rows if r['workers']==8])
        chips=['AOI_2_Vegas_img1454','AOI_3_Paris_img235','AOI_4_Shanghai_img1196']+[f'AOI_2_Vegas_img{i}' for i in range(9)]
        assets=[dict(id='RGB-PanSharpen_'+chip,role='development') for chip in chips]
        contrasts=kernel.contrasts(assets,'spacenet','parallel')
        self.assertEqual(len(contrasts),12)
        self.assertEqual({c[0]['id'] for c in contrasts},{'RGB-PanSharpen_'+c for c in chips[:3]})
        with self.assertRaises(ValueError):kernel.contrasts(assets[1:]+[assets[-1]],'spacenet','parallel')

    def test_entropy_stages_partition_the_frozen_matrix(self):
        manifest, _ = self.fixture('screen')
        assets = manifest['assets']
        stages = {phase:kernel.contrasts(assets,phase,'entropy')
                  for phase in ('screen','describe','primary','confirm')}
        self.assertEqual({p:len(c) for p,c in stages.items()},
                         dict(screen=6,describe=6,primary=2,confirm=34))
        self.assertTrue(all(c[2:] == (1,'decode','openjpeg') for c in stages['screen']))
        self.assertTrue(all(c[2:] == (8,'decode','openjpeg') for c in stages['describe']))
        self.assertTrue(all(c[0]['id'].startswith('106_') and c[1:]==(0,1,'decode','openjpeg')
                            for c in stages['primary']))
        key=lambda c:(c[0]['id'],*c[1:])
        combined=list(map(key,stages['primary']+stages['confirm']))
        self.assertEqual(len(set(combined)),36)
        chips=['AOI_2_Vegas_img1454','AOI_3_Paris_img235','AOI_4_Shanghai_img1196']+[f'AOI_2_Vegas_img{i}' for i in range(9)]
        sn=[dict(id='RGB-PanSharpen_'+chip,role='development') for chip in chips]
        cases=kernel.contrasts(sn,'spacenet','entropy')
        self.assertEqual(len(cases),8)
        self.assertTrue(all(c[3:] == ('decode','emuella') for c in cases))
        self.assertEqual({c[0]['id'] for c in cases if c[2]==8},{'RGB-PanSharpen_'+chips[0]})

    def test_entropy_row_validation_rejects_missing_origin_and_budget_changes(self):
        manifest, _ = self.fixture('screen')
        for phase,rounds in [('screen',3),('describe',3),('primary',20),('confirm',20)]:
            cases=[dict(case_id=a['id'],style=s,workers=w,operation=op,origin=o)
                   for a,s,w,op,o in kernel.contrasts(manifest['assets'],phase,'entropy')]
            frozen=dict(manifest,phase=phase,study='entropy',rounds=rounds,contrasts=cases)
            rows=[dict(c,round=r,arm=arm,result=dict(status=0))
                  for c in cases for r in range(rounds) for arm in kernel.ARMS]
            kernel.validate_rows(frozen,rows)
            for changed in [rows[:-1],rows+[rows[0]]]:
                with self.assertRaises(ValueError):kernel.validate_rows(frozen,changed)
            with self.assertRaises(ValueError):kernel.validate_rows(dict(frozen,rounds=rounds+1),rows)
        with self.assertRaises(ValueError):kernel.contrasts(manifest['assets'],'primary','kernel')

    def test_entropy_origins_have_distinct_paths_without_changing_legacy_paths(self):
        args=(0,'case',0,1,'decode','openjpeg','reference')
        for study in ('kernel','parallel'):
            self.assertEqual(kernel.observation_name(study,*args), 'r00-case-s0-w1-decode-reference')
        self.assertEqual(kernel.observation_name('entropy',*args), 'r00-case-s0-w1-decode-openjpeg-reference')
        self.assertNotEqual(kernel.observation_name('entropy',*args),
                            kernel.observation_name('entropy',0,'case',0,1,'decode','emuella','reference'))

    def test_incremental_matrix_is_finite_and_has_no_screen(self):
        assets = self.fixture('screen')[0]['assets']
        primary = kernel.contrasts(assets, 'primary', 'incremental')
        regression = kernel.contrasts(assets, 'confirm', 'incremental')
        self.assertEqual((len(primary), len(regression)), (2, 12))
        self.assertEqual({c[0]['product'] for c in primary}, {'PAN16', 'MS16'})
        for phase in ('screen', 'describe'):
            with self.assertRaises(ValueError): kernel.contrasts(assets, phase, 'incremental')
        chips = ['AOI_2_Vegas_img1454','AOI_3_Paris_img235','AOI_4_Shanghai_img1196'] + [f'AOI_2_Vegas_img{i}' for i in range(9)]
        sn = [dict(id='RGB-PanSharpen_'+chip, role='development') for chip in chips]
        cases = kernel.contrasts(sn, 'spacenet', 'incremental')
        self.assertEqual(len(cases), 2)
        self.assertEqual({c[1:] for c in cases}, {(0,1,'decode','emuella'), (1,1,'decode','emuella')})
        for phase, selected in [('primary', assets), ('confirm', assets), ('spacenet', sn)]:
            contrasts = [dict(case_id=a['id'],style=s,workers=w,operation=op,origin=o)
                         for a,s,w,op,o in kernel.contrasts(selected,phase,'incremental')]
            manifest = dict(study='incremental',phase=phase,rounds=20,assets=selected,contrasts=contrasts)
            rows = [dict(c,round=r,arm=arm) for c in contrasts for r in range(20) for arm in kernel.ARMS]
            kernel.validate_rows(manifest, rows)
            with self.assertRaises(ValueError): kernel.validate_rows(manifest, rows[:-1])
            with self.assertRaises(ValueError): kernel.validate_rows(dict(manifest,rounds=21),rows)

    def test_three_round_screen_never_calls_twenty_round_estimator(self):
        manifest,rows=self.fixture('screen')
        for row in rows:
            row['result'].update(observation=dict(samples_ns=[100],stream_bytes=5),
                                 process_peak_rss_bytes=1000,process_cpu_seconds=0.01)
        with tempfile.TemporaryDirectory() as directory:
            output=Path(directory)
            kernel.write(output/'manifest.json',manifest)
            kernel.write(output/'measurement.json',dict(manifest_sha256=kernel.sha(output/'manifest.json'),rows=rows,complete=True))
            with contextlib.redirect_stdout(io.StringIO()):
                kernel.analyse(SimpleNamespace(output=output,estimator=output/'must-not-be-invoked'))
            report=json.loads((output/'report.json').read_text())
            self.assertTrue(all(c['verdict']=='development_screen_only' for c in report['comparisons']))


if __name__=='__main__':unittest.main()
