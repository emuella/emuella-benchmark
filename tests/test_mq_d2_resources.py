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

    def test_front_end_initial_and_conditional_resources_have_112_calls(self):
        assets = [dict(id=f'{prefix}-{p}',product=p) for prefix in ('94_a','106_b')
                  for p in ('PAN16','MS16','RGB8','RGB16')]+[dict(id='105_c-RGB8',product='RGB8')]
        chips = ['AOI_2_Vegas_img1454','AOI_3_Paris_img235','AOI_4_Shanghai_img1196']+[f'AOI_2_Vegas_img{i}' for i in range(9)]
        sn = [dict(id='RGB-PanSharpen_'+chip,role='development') for chip in chips]
        total = 0
        for phase,selected,calls in [('primary',assets,32),('confirm',assets,64),('spacenet',sn,16)]:
            cases = resources.cases(selected,phase,'front-end')
            self.assertEqual(len(cases)*2,calls)
            self.assertEqual({c[2] for c in cases},{1,2,4,8})
            self.assertEqual({c[3:] for c in cases},{('encode','emuella')})
            self.assertEqual(len({(c[0]['id'],*c[1:]) for c in cases}),len(cases))
            total += calls
        self.assertEqual(total,112)
        sn[0]['id']='RGB-PanSharpen_AOI_5_Khartoum_img1'
        with self.assertRaises(ValueError): resources.cases(sn,'spacenet','front-end')
        with self.assertRaises(ValueError): resources.cases(assets,'encode','front-end')

    def test_front_end_resource_eligibility_uses_working_query_including_output(self):
        request = dict(max_working_bytes=768,max_output_bytes=64)
        observation = dict(samples_ns=[],working_bytes=700,output_capacity=32,output_capacity_limit=64,
                           allocation_diagnostic=dict(allocation_peak_additional_requested_bytes=699,
                                                      successful_allocation_or_reallocation_requests=41))
        facts = resources.resource_observation(observation,request)
        self.assertTrue(facts['eligible'])
        changed = dict(observation,allocation_diagnostic=dict(observation['allocation_diagnostic'],successful_allocation_or_reallocation_requests=42))
        self.assertTrue(resources.resource_observation(changed,request)['eligible'])
        self.assertEqual(resources.resource_observation(changed,request)['allocation_requests'],42)
        changed['allocation_diagnostic']['allocation_peak_additional_requested_bytes']=701
        facts = resources.resource_observation(changed,request)
        self.assertFalse(facts['eligible'])
        self.assertFalse(facts['gates']['peak_within_query'])
        self.assertTrue(facts['gates']['peak_within_working_limit'])
        for delta in [dict(working_bytes=769),dict(output_capacity=65),dict(output_capacity=40,output_capacity_limit=39)]:
            self.assertFalse(resources.resource_observation(dict(observation,**delta),request)['eligible'])
        for delta in [dict(samples_ns=[1]),dict(working_bytes=None),dict(allocation_diagnostic={})]:
            with self.assertRaises(ValueError): resources.resource_observation(dict(observation,**delta),request)


if __name__=='__main__': unittest.main()
