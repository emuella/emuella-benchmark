import importlib.util
from pathlib import Path
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


if __name__=='__main__':unittest.main()
