import importlib.util
from pathlib import Path
import unittest

SPEC = importlib.util.spec_from_file_location('resources',Path(__file__).resolve().parents[1]/'scripts/mq-d2-resources.py')
resources = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(resources)


class ResourceCoverage(unittest.TestCase):
    def test_fixed_calls_origins_workers_and_no_reserved_inputs(self):
        assets = [dict(id=f'{prefix}-{p}',product=p) for prefix in ('94_a','106_b')
                  for p in ('PAN16','MS16','RGB8','RGB16')]+[dict(id='105_c-RGB8',product='RGB8')]
        for phase, count, operation in [('primary',32,'decode'),('encode',8,'encode'),('confirm',32,'decode')]:
            cases = resources.cases(assets,phase)
            self.assertEqual(len(cases), count)
            self.assertEqual({c[2] for c in cases},{1,2,4,8})
            self.assertEqual({c[3] for c in cases},{operation})
            self.assertEqual(len({(c[0]['id'],*c[1:]) for c in cases}),count)
            self.assertEqual({c[4] for c in cases},{'emuella'} if operation=='encode' else {'emuella','openjpeg'})
        chips = ['AOI_2_Vegas_img1454','AOI_3_Paris_img235','AOI_4_Shanghai_img1196']+[f'AOI_2_Vegas_img{i}' for i in range(9)]
        sn = [dict(id='RGB-PanSharpen_'+chip,role='development') for chip in chips]
        self.assertEqual(len(resources.cases(sn,'spacenet')),8)
        sn[0]['role']='reserved'
        with self.assertRaises(ValueError): resources.cases(sn,'spacenet')
        with self.assertRaises(ValueError): resources.cases(assets,'screen')


if __name__=='__main__': unittest.main()
