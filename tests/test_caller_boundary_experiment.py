"""Authored finite three-arm protocol checks; never starts a corpus worker."""
import copy
from contextlib import nullcontext
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import caller_boundary_experiment as c


def rows():
    return [dict(planned=p,gates_passed=True,result=dict(status=0,observation=dict(samples_ns=[{'A':100000000,'B':110000000,'C':90000000}[p['arm']]]))) for p in c.schedule()]


def estimator(payload):
    a=sum(payload['baseline'])/40; b=sum(payload['candidate'])/40
    return dict(verdict='improved' if b<a*.95 else 'regressed' if b>a*1.05 else 'equivalent',
                baseline_mean_ns=a,candidate_mean_ns=b,relative_interval_99=[b/a-1,b/a-1])


class BoundaryTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(); self.addCleanup(self.temp.cleanup); self.root=Path(self.temp.name)

    def test_exact_schedule_balance_and_position_imbalance(self):
        plan=c.schedule(); self.assertEqual(len(plan),126)
        self.assertEqual([p['stage'] for p in plan[:6]],['preflight']*3+['allocation']*3)
        self.assertEqual([p['arm'] for p in plan[:6]],list('ABCABC'))
        self.assertEqual([p['order'] for p in plan[6::3]],list(('ABC','CBA','ACB','BCA','BAC','CAB')*6+('ABC','CBA','ACB','BCA')))
        self.assertEqual(c.order_summary()['relative_pair_order'],{'AB':20,'AC':20,'BC':20})
        self.assertEqual(c.order_summary()['positions'],{'A':[14,12,14],'B':[13,14,13],'C':[13,14,13]})
        for a in 'ABC': self.assertEqual(sum(p['arm']==a for p in plan[6:]),40)
        self.assertEqual(plan[-1]['block'],6); self.assertEqual(len({p['call_id'] for p in plan}),126)

    def test_three_directions_reuse_each_vector_once(self):
        calls=[]
        def record(payload): calls.append(payload); return estimator(payload)
        result=c.analyse(rows(),record)
        self.assertEqual(len(calls),3)
        self.assertEqual([(p['baseline'][0],p['candidate'][0]) for p in calls],[(110000000,90000000),(100000000,110000000),(100000000,90000000)])
        self.assertTrue(all(len(p[k])==40 for p in calls for k in ('baseline','candidate')))
        self.assertEqual(result['contrasts']['C/B']['mean_saving_ms'],20)
        self.assertEqual(result['contrasts']['B/A']['mean_change_ms'],10)
        self.assertTrue(result['screen']['intervention_benefit_supported'])
        self.assertTrue(result['screen']['serial_endpoint_bound_passed'])
        self.assertFalse(result['screen']['production_promotion_authorised'])

    def test_fixed_count_failure_and_order_never_reach_estimator(self):
        invalid=[rows()[:-1],rows()+rows()[:1]]
        for stage_index in (0,3,6,125):
            value=rows(); value[stage_index]['result']['status']='timeout'; invalid.append(value)
        value=rows(); value[6],value[7]=value[7],value[6]; invalid.append(value)
        value=rows(); value[6]['result']['observation']['allocation_diagnostic']={}; invalid.append(value)
        value=rows(); value[6]['result']['observation']['samples_ns']=[1,2]; invalid.append(value)
        for value in invalid:
            with self.subTest(length=len(value)),patch.object(c.analysis,'_estimate') as estimate:
                with self.assertRaises(ValueError): c.analyse(value,estimator)
                estimate.assert_not_called()

    def test_screen_boundaries_no_new_magnitude_gate(self):
        def screen(primary,serial): return c.screen({'C/B':dict(lower=primary[0],upper=primary[1]),'C/A':dict(lower=serial[0],upper=serial[1])})
        self.assertFalse(screen((-.01,0),(-.02,0))['intervention_benefit_supported'])
        self.assertTrue(screen((-.000002,-.000001),(-.01,.01))['intervention_benefit_supported'])
        self.assertTrue(screen((-.000002,-.000001),(-.01,.01))['serial_endpoint_bound_passed'])
        self.assertFalse(screen((-.01,-.001),(-.01,.010001))['serial_endpoint_bound_passed'])
        self.assertIn('unproved',screen((-.01,-.001),(-.01,.010001))['disposition'])
        self.assertFalse(screen((-.01,.01),(-.02,-.01))['intervention_benefit_supported'])
        self.assertTrue(screen((.001,.002),(.001,.002))['resolved_adverse_intervention'])

    def test_caps_and_receipt_headroom(self):
        value=dict(c.CAPS); self.assertEqual(c.budget_issues(value),[])
        self.assertEqual(len(c.budget_issues(value,True)),3)
        for key in c.CAPS:
            bad=dict(value); bad[key]+=1
            self.assertTrue(any(key in issue for issue in c.budget_issues(bad)))
        for bad in (None,float('nan'),-1):
            self.assertTrue(c.budget_issues(dict(value,wall_seconds=bad)))

    def test_bound_tool_and_cache_environment_rejects_flag_overrides(self):
        environment = dict(RUSTC='/toolchain/rustc', CC='/usr/bin/cc',
            CARGO_TARGET_X86_64_UNKNOWN_LINUX_GNU_LINKER='/usr/bin/cc',
            PKG_CONFIG_PATH='/native/lib/pkgconfig', CARGO_HOME='/cache/cargo')
        c.validate_build_environment(environment)
        c.validate_build_environment({})
        for key in ('RUSTFLAGS', 'CARGO_ENCODED_RUSTFLAGS', 'CARGO_PROFILE_PERF_LTO',
                    'RUSTC_WRAPPER', 'CFLAGS', 'CARGO_BUILD_TARGET'):
            with self.subTest(key=key), self.assertRaisesRegex(ValueError, 'override forbidden'):
                c.validate_build_environment(dict(environment, **{key:'changed'}))

    def test_request_cannot_change_treatment_endpoint(self):
        request=dict(codec='emuella',operation='encode',case_id='106_authored-RGB8',round=0,width=5577,height=5036,components=3,bits=8,layout='interleaved',style=0,workers=1,raw_path='/raw',stream_path='/stream',raw_sha256=c.RAW,stream_sha256=c.STREAM,max_working_bytes=c.refresh.classic.WORKING,max_output_bytes=c.refresh.classic.OUTPUT)
        c.validate_request(request)
        for key,value in [('width',100),('workers',2),('style',1),('raw_sha256','0'*64),('stream_sha256','0'*64),('bits',16),('extra',True)]:
            with self.subTest(key=key),self.assertRaises(ValueError): c.validate_request(dict(request,**{key:value}))

    def test_owning_restoration_runs_after_controller_error(self):
        binding=dict(config=dict(output=str(self.root)),installation={'authored':True})
        authority=self.root/'lease/public/authority.json'; authority.parent.mkdir(parents=True); authority.write_text('{}')
        calls=[]
        def invoke(command,**kwargs):
            calls.append(command)
            if command[0]=='/usr/bin/python3': raise OSError('authored transport failure')
            return type('Result',(),dict(returncode=0,stdout='restored',stderr=''))()
        with patch.object(c.live,'authenticate_lease'),patch.object(c.live,'authority'),patch.object(c.live,'installed_binding',return_value=binding['installation']),patch.object(c.live,'validate_restoration',return_value={'restored':True}),patch.object(c.subprocess,'run',side_effect=invoke):
            self.assertEqual(c.execute_owned(binding,self.root/'prep','digest',authority),1)
        self.assertEqual([v[-1] for v in calls[1:]],['stop','verify'])
        terminal=json.loads((self.root/'execution-complete.json').read_text())
        self.assertTrue(terminal['restoration_verified']); self.assertIn('transport failure',terminal['error'])
        with self.assertRaisesRegex(ValueError,'consumed'): c.execute_owned(binding,self.root/'prep','digest',authority)

    def test_no_stop_of_unauthenticated_lease(self):
        binding=dict(config=dict(output=str(self.root)),installation={})
        with patch.object(c.live,'authenticate_lease',side_effect=ValueError('not owned')),patch.object(c.subprocess,'run') as invoke:
            self.assertEqual(c.execute_owned(binding,self.root/'prep','digest',self.root/'lease/public/authority.json'),1)
            invoke.assert_not_called()

    def acquire(self,fail=None):
        binding=dict(config=dict(output=str(self.root)))
        (self.root/'execution-started.json').write_text(json.dumps(dict(preparation_sha256='digest',authority_sha256='authority')))
        calls=[]
        def observe(binding,planned,receipt,environment,start,observed,*rest):
            calls.append(planned); row=rows()[planned['index']]
            if planned['index']==fail: row['gates_passed']=False; row['result']['status']='timeout'
            observed.append(row); return row
        with patch.object(c.live,'authority',return_value={'valid_until_epoch':c.time.time()+10000}),patch.object(c,'sha',return_value='authority'),patch.object(c,'identities'),patch.object(c.live,'controller_admission'),patch.object(c.stability,'controller_placement',return_value=nullcontext()),patch.object(c.stability,'environment',return_value={}),patch.object(c.stability,'environment_issues',return_value=[]),patch.object(c,'observe',side_effect=observe),patch.object(c,'consumption',side_effect=lambda b,s,n:dict(started_calls=n,wall_seconds=50,evidence_bytes=500,build_bytes=500)),patch.object(c,'analyse') as analyse:
            status=c.acquire(binding,self.root/'prep','digest',self.root/'authority')
            analyse.assert_not_called()
        return status,calls,json.loads((self.root/'completion.json').read_text())

    def test_all_calls_before_analysis_and_failure_retains_unstarted(self):
        status,calls,completion=self.acquire(9)
        self.assertEqual(status,1); self.assertEqual(len(calls),10)
        self.assertFalse(completion['complete']); self.assertEqual(len(completion['unstarted_call_ids']),116)
        (self.root/'execution-started.json').unlink(); (self.root/'completion.json').unlink(); (self.root/'launch.json').unlink()
        status,calls,completion=self.acquire()
        self.assertEqual(status,0); self.assertEqual(len(calls),126); self.assertTrue(completion['complete'])
        self.assertEqual(completion['unstarted_call_ids'],[])

    def test_missing_receipt_retained_and_no_success_subset_analysis(self):
        planned=c.schedule()[0]
        (self.root/(planned['call_id']+'-started.json')).write_text(json.dumps(dict(planned=planned,monotonic_ns=1)))
        binding=dict(config=dict(output=str(self.root)))
        with patch.object(c,'analyse') as analyse:
            result=c.reconstruct(binding,'digest',estimator)
            analyse.assert_not_called()
        self.assertFalse(result['complete']); self.assertEqual(result['started_calls'],1)
        self.assertEqual(result['missing_terminal_call_ids'],[planned['call_id']]); self.assertEqual(len(result['unstarted_call_ids']),125)
        self.assertEqual(result['raw_rows'][0]['result']['status'],'missing_terminal_receipt')


if __name__=='__main__': unittest.main()
