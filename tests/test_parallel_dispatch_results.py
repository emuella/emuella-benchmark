"""Terminal factual accounting and optional retained-metadata reconciliation."""
import collections
import hashlib
import json
import math
import os
from pathlib import Path
import statistics
import unittest

import test_finite_confirmation_analysis  # Establish the shared scripts import path.
import finite_confirmation_analysis as finite

EVIDENCE = Path(__file__).resolve().parents[1]/'docs/evidence/classic-forward53-parallel-dispatch.json'


class DispatchResultTests(unittest.TestCase):
    def setUp(self):
        self.result = json.loads(EVIDENCE.read_text())

    def test_complete_matrix_and_terminal_accounting(self):
        r = self.result; a = r['acquisition']; rows = r['endpoints']
        self.assertEqual([v['endpoint_id'] for v in rows], [f'endpoint-{i:02}' for i in finite.ORDER])
        self.assertEqual(sum(v['fixed_pairs'] for v in rows), finite.limits()['pairs'])
        self.assertEqual(sum(v['observed_pairs'] for v in rows), a['observed_pairs'])
        self.assertEqual(2*a['observed_pairs'], a['ordinary_calls'])
        self.assertEqual(a['ordinary_calls']+a['preflight_calls']+a['allocation_calls'], a['started_calls'])
        self.assertEqual(a['started_calls']+a['unstarted_calls'], finite.limits()['total_calls'])
        self.assertEqual(a['completed_endpoints']+a['unstarted_endpoints'], 28)
        self.assertEqual([v['status'] for v in rows], ['analysed']*3+['unstarted']*25)
        self.assertTrue(all(v['observed_pairs']==v['fixed_pairs']==40 for v in rows[:3]))
        self.assertTrue(all(v['observed_pairs']==0 for v in rows[3:]))
        self.assertEqual(rows[5]['endpoint_id'], 'endpoint-11'); self.assertEqual(rows[5]['fixed_pairs'],160)
        self.assertEqual(a['stopping_endpoint'],rows[2]['endpoint_id'])
        self.assertEqual(r['disposition'], finite.NOT_QUALIFIED)
        self.assertFalse(r['whole_scope_qualified'])
        self.assertEqual(finite.budget_issues(r['consumption_at_acquisition_end']), [])

    def test_published_decisions_preserve_the_directional_gates(self):
        for endpoint in self.result['endpoints']:
            primary = endpoint['endpoint_id']=='endpoint-00'
            self.assertEqual(endpoint['required_upper_relative_99'],dict(operator='<' if primary else '<=',value=-.05 if primary else .01))
            self.assertEqual(endpoint['required_absolute_mean_saving_ms'],dict(operator='>=',value=10) if primary else None)
            if endpoint['status']!='analysed': continue
            lower,upper = endpoint['relative_interval_99']
            output=dict(baseline_mean_ns=endpoint['baseline_mean_ns'],candidate_mean_ns=endpoint['candidate_mean_ns'],
                        relative_interval_99=[lower,upper],verdict=endpoint['legacy_timing_verdict'])
            decision=finite.endpoint_decision(dict(valid=True,complete=True,estimator=dict(B_over_A=dict(output=output,lower=lower,upper=upper))),primary)
            self.assertEqual(decision['disposition'],endpoint['disposition'])
            self.assertTrue(math.isclose(decision['mean_saving_ms'],endpoint['mean_saving_ms']))
        stopped=self.result['endpoints'][2]
        self.assertLess(stopped['relative_interval_99'][0], .01)
        self.assertGreater(stopped['relative_interval_99'][1], .01)
        self.assertEqual(stopped['legacy_timing_verdict'],'equivalent')
        self.assertEqual(stopped['disposition'],finite.NOT_QUALIFIED)

    def test_resource_and_restoration_scope_remains_explicit(self):
        r=self.result; resources=r['separate_resource_observations']
        self.assertEqual(sum(v['calls'] for v in resources['cells']),r['acquisition']['allocation_calls'])
        for v in resources['cells']:
            self.assertEqual(v['styles'],[0,1]); self.assertEqual(v['calls'],2)
            self.assertTrue(v['all_resource_gates_pass'])
            self.assertLessEqual(v['peak_bytes_range'][1],resources['working_limit_bytes'])
            self.assertLessEqual(v['output_capacity_range'][1],resources['output_limit_bytes'])
            self.assertNotIn('process_peak_rss_bytes',v)
        self.assertEqual(sum(v['processes'] for v in r['separate_whole_process_observations']['cells']),r['acquisition']['ordinary_calls'])
        checks=r['observed_prefix_checks']
        self.assertTrue(all(checks['checks'].values()));self.assertEqual(checks['reconstruction_issues'],[])
        self.assertEqual(checks['missing_terminal_receipts'],0);self.assertEqual(checks['orphaned_receipts'],0)
        restoration=r['setup_and_restoration']
        self.assertTrue(restoration['ordinary_runner_restored']);self.assertTrue(restoration['independently_restored'])
        self.assertEqual(restoration['journal_sha256'],restoration['installed_lease_records']['journal.json']['sha256'])
        # Public evidence is a deliberate aggregate projection, not a raw receipt dump.
        text=EVIDENCE.read_text()
        for excluded in ('/nvme/','/home/','samples_ns','raw_rows','journal_text','authority_text'):
            self.assertNotIn(excluded,text)

    @unittest.skipUnless(os.environ.get('PARALLEL_DISPATCH_RETAINED_REPORT'),'optional retained metadata path is unset')
    def test_projection_matches_externally_pinned_retained_report(self):
        path=Path(os.environ['PARALLEL_DISPATCH_RETAINED_REPORT']); data=path.read_bytes();r=json.loads(data)
        self.assertEqual(hashlib.sha256(data).hexdigest(),self.result['bindings']['retained_report_sha256'])
        self.assertEqual(r['issues'],[]);self.assertEqual(r['consumption'],self.result['consumption_at_acquisition_end'])
        for public,retained in zip(self.result['endpoints'],r['endpoints']):
            for key in ('endpoint_id','status','disposition','baseline_mean_ns','candidate_mean_ns','relative_interval_99'):
                self.assertEqual(public[key],retained[key])
            self.assertEqual(public['observed_pairs'],len(retained.get('analysis',{}).get('raw_rows',[]))//2)
        counts=collections.Counter(v['planned']['stage'] for v in r['raw_rows'])
        for stage in ('ordinary','preflight','allocation'):self.assertEqual(counts[stage],self.result['acquisition'][stage+'_calls'])
        for cell in self.result['separate_resource_observations']['cells']:
            rows=[v for v in r['raw_rows'] if v['planned']['stage']=='allocation' and
                  all(v['planned'][k]==cell[k] for k in ('case_id','workers','arm'))]
            for key in ('peak_bytes','allocation_requests','working_bytes','output_capacity','output_capacity_limit'):
                values=[v['resources'][key] for v in rows]
                self.assertEqual(cell[key+'_range'],[min(values),max(values)])
        for cell in self.result['separate_whole_process_observations']['cells']:
            rows=[v['result'] for v in r['raw_rows'] if v['planned']['stage']=='ordinary' and
                  all(v['planned'][k]==cell[k] for k in ('endpoint_id','arm'))]
            self.assertEqual(cell['mean_process_wall_ns'],statistics.mean(v['process_wall_ns'] for v in rows))
            self.assertEqual(cell['mean_process_cpu_seconds'],statistics.mean(v['process_cpu_seconds'] for v in rows))
            self.assertEqual(cell['max_process_peak_rss_bytes'],max(v['process_peak_rss_bytes'] for v in rows))
        for name,value in self.result['retention']['records'].items():
            retained=path.parent.parent/value['locator']
            self.assertEqual(hashlib.sha256(retained.read_bytes()).hexdigest(),value['sha256'])
        self.assertEqual(r['independent_restoration']['verification']['journal_sha256'],self.result['setup_and_restoration']['journal_sha256'])
