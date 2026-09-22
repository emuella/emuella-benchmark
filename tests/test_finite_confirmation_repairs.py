"""Installed-shape admission, zero-start checkpoints and retained v2 reconstruction."""
import copy
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock, patch

import test_finite_confirmation_analysis as authored
import finite_confirmation_live as live
import finite_confirmation_report as report


class RepairTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(); self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.register = self.root/'register.json'; self.design = self.root/'design.json'; self.v1 = self.root/'v1.json'
        self.register.write_text(json.dumps(authored.register())); self.design.write_text('{}')
        self.original = live.finite.make_manifest(self.register, self.design)
        self.v1.write_text(json.dumps(self.original))
        self.contract = live.derive(self.v1, live.sha(self.v1), self.register, self.design, 'separate v2 authority')
        self.output = self.root/'output'; self.output.mkdir()
        self.other = self.root/'other'; self.other.mkdir()
        self.binding = dict(schema=live.PREPARATION, manifest=self.contract,
            config=dict(authority='separate v2 authority', stores=dict(rareplanes=dict(output=str(self.output)),
                                                                    spacenet=dict(output=str(self.other)))),
            installation=dict(package_sha256=live.PACKAGE, policy_sha256='c'*64, standing_authority='standing authority', files={}))

    def fixture(self):
        lease_id = '11111111-1111-4111-8111-111111111111'
        leases = self.root/'state/leases'; lease = leases/lease_id; (lease/'public').mkdir(parents=True)
        helper = lease/'helper.py'; helper.write_text('# authored helper; never executed\n')
        self.binding['installation']['files']['measurement_reservation.py'] = live.sha(helper)
        installed = live.installation_record(self.binding)
        (leases.parent/'current.json').write_text(json.dumps(dict(lease_id=lease_id, installation=installed)))
        sysroot = self.root/'sys'; owner = sysroot/'fs/cgroup'/('emuella-measurement-reservation-'+lease_id+'.service')
        group = owner/'workers'; group.mkdir(parents=True)
        values = dict(zip(live.stability.CGROUP_FILES, ('0-7,16-23','0-7,16-23','root','0','max 100000','max','max')))
        for key,value in values.items(): (group/key).write_text(value)
        (group/'cgroup.procs').write_text('')
        for cpu in range(8):
            topology = sysroot/f'devices/system/cpu/cpu{cpu}/topology'; topology.mkdir(parents=True)
            for key,value in dict(thread_siblings_list=f'{cpu},{cpu+16}',physical_package_id='0',core_id=str(cpu)).items():
                (topology/key).write_text(value)
        receipt = dict(schema=live.RESERVATION,condition='balanced-reusable',partition_mode='root',
            authority=self.binding['config']['authority'],issuer='authored owner',approved=True,
            valid_from_epoch=1,valid_until_epoch=10000,cgroup=str(group),worker_cpus=list(range(8)),
            reserved_cpus=list(range(8))+list(range(16,24)),controller_cpus=list(range(8,16))+list(range(24,32)),
            residual_interference='Shared package and interrupts remain.',installation=installed,lease_id=lease_id)
        path = lease/'public/authority.json'; path.write_text(json.dumps(receipt))
        return leases, lease, sysroot, path, receipt

    def restoration(self, receipt):
        installed = live.installation_record(self.binding); lease_id=receipt['lease_id']
        journal = dict(schema='measurement-balanced-reusable-reservation/v1',id=lease_id,
            authority=self.binding['config']['authority'],installation=installed,cleanup_executed=True,
            condition='balanced-reusable',partition_mode='root',unit='authored.service',boot='authored-boot',before={'policy':'original'},
            helper_sha256=self.binding['installation']['files']['measurement_reservation.py'])
        journal_text=json.dumps(journal)
        restoration=dict(condition='balanced-reusable',partition_mode='root',installation=installed,
                         lease_id=lease_id,cleanup_executed=True,before=journal['before'],unit=journal['unit'],issues=[])
        verification=dict(restored=True,lease_id=lease_id,boot=journal['boot'],
                          journal_sha256=hashlib.sha256(journal_text.encode()).hexdigest(),report=dict(restored=True,issues=[],observed=journal['before']))
        return dict(journal_text=journal_text,authority_text=json.dumps(receipt),restoration=restoration,verification=verification)

    def test_real_installed_shape_reaches_actual_strict_admission(self):
        leases,lease,sysroot,path,receipt=self.fixture()
        with patch.object(live,'LEASES',leases), patch.object(live.launcher,'trusted',side_effect=Path):
            common=live.authority(self.binding,path,sysroot=sysroot,now=2)
            self.assertNotIn('installation',common); self.assertNotIn('lease_id',common)
            self.assertEqual(common,live.common_authority(receipt))
            for field,value in [('lease_id','22222222-2222-4222-8222-222222222222'),('installation',{})]:
                path.write_text(json.dumps(dict(receipt,**{field:value})))
                with self.assertRaisesRegex(ValueError,'binding'): live.authority(self.binding,path,sysroot=sysroot,now=2)
            path.write_text(json.dumps(dict(receipt,unexpected=True)))
            with self.assertRaisesRegex(ValueError,'fields'): live.authority(self.binding,path,sysroot=sysroot,now=2)

    def test_owned_admission_failure_and_interrupt_restore_before_transport(self):
        leases,lease,sysroot,path,receipt=self.fixture()
        real_authority=live.authority
        failures=[dict(receipt,schema='wrong-schema'),dict(receipt,valid_until_epoch=2),receipt]
        for index,value in enumerate(failures):
            output=self.root/f'failure-{index}';output.mkdir()
            self.binding['config']['stores']['rareplanes']['output']=str(output)
            path.write_text(json.dumps(value)); calls=[]
            if index==2: (Path(receipt['cgroup'])/'cpu.max').write_text('100000 100000')
            def run(command,**kwargs): calls.append(command);return Mock(returncode=0,stdout='{}',stderr='')
            with patch.object(live,'LEASES',leases),patch.object(live.launcher,'trusted',side_effect=Path), \
                 patch.object(live,'read_preparation',return_value=self.binding), \
                 patch.object(live,'authority',side_effect=lambda b,p: real_authority(b,p,sysroot=sysroot,now=2)), \
                 patch.object(live,'installed_binding',return_value=self.binding['installation']), \
                 patch.object(live,'validate_restoration',return_value={}),patch.object(live.subprocess,'run',side_effect=run):
                self.assertEqual(live.execute(output/'prep','digest',path),1)
            self.assertEqual([c[-1] for c in calls],['stop','verify'])
            self.assertTrue((output/'execution-started.json').exists())
        (Path(receipt['cgroup'])/'cpu.max').write_text('max 100000')
        path.write_text(json.dumps(receipt)); output=self.root/'interrupt';output.mkdir()
        self.binding['config']['stores']['rareplanes']['output']=str(output)
        with patch.object(live,'LEASES',leases),patch.object(live.launcher,'trusted',side_effect=Path), \
             patch.object(live,'read_preparation',return_value=self.binding),patch.object(live,'authority',side_effect=KeyboardInterrupt()), \
             patch.object(live,'installed_binding',return_value=self.binding['installation']), \
             patch.object(live,'validate_restoration',return_value={}), \
             patch.object(live.subprocess,'run',return_value=Mock(returncode=0,stdout='{}',stderr='')) as run:
            self.assertEqual(live.execute(output/'prep','digest',path),1)
        self.assertEqual([c.args[0][-1] for c in run.call_args_list],['stop','verify'])

    def test_unauthenticated_or_different_lease_is_never_stopped(self):
        leases,lease,sysroot,path,receipt=self.fixture()
        path.write_text(json.dumps(dict(receipt,lease_id='different')))
        with patch.object(live,'LEASES',leases),patch.object(live.launcher,'trusted',side_effect=Path), \
             patch.object(live,'read_preparation',return_value=self.binding),patch.object(live.subprocess,'run') as run:
            self.assertEqual(live.execute(self.output/'prep','digest',path),1)
        run.assert_not_called()

    def test_prelaunch_checkpoint_retains_old_bytes_and_rejects_any_start(self):
        for folder in (self.output,self.other):
            (folder/'LICENSE.txt').write_text('authored');(folder/'NOTICE.txt').write_text('authored')
        previous=self.output/'preparation.json';previous.write_text(json.dumps(self.binding));digest=live.sha(previous)
        output=self.output/'preparation-reviewed.json';original=previous.read_bytes()
        with patch.object(live,'manifest',return_value=self.contract):
            self.assertEqual(live.check_prelaunch_checkpoint(self.binding['config'],output,previous,digest),[previous])
            self.assertEqual(previous.read_bytes(),original)
            for name in ('execution-started.json','acquisition-started.json','preflight-0000-started.json','preflight-0000'):
                marker=self.output/name;marker.write_text('{}')
                with self.assertRaisesRegex(ValueError,'zero transport'):
                    live.check_prelaunch_checkpoint(self.binding['config'],output,previous,digest)
                marker.unlink()  # Authored fixture only.
            with self.assertRaisesRegex(ValueError,'predecessor'):
                live.check_prelaunch_checkpoint(self.binding['config'],output,previous,'0'*64)
            changed=copy.deepcopy(self.binding['config']);changed['authority']='different attempt'
            with self.assertRaisesRegex(ValueError,'identity'):
                live.check_prelaunch_checkpoint(changed,output,previous,digest)
        self.assertFalse(output.exists());self.assertEqual(previous.read_bytes(),original)

    def test_v2_analysis_preserves_identity_and_all_endpoint_statuses(self):
        result=live.finite.analyse_attempt(self.contract,[],{40:authored.estimator,160:authored.estimator},
            checks=dict.fromkeys(live.finite.CHECKS,True),consumption=dict(started_calls=0,wall_seconds=0,evidence_bytes=0,build_bytes=0))
        self.assertEqual(result['schema'],live.SCHEMA);self.assertEqual(len(result['endpoints']),28)
        self.assertEqual(result['predecessor_sha256'],live.sha(self.v1))
        self.assertTrue(all(r['status']=='unstarted' for r in result['endpoints']))
        with self.assertRaisesRegex(ValueError,'v2'):
            live.finite.analyse_attempt(dict(self.contract,predecessor_sha256=''),[],{},checks={},consumption={})

    def test_missing_terminal_and_orphaned_receipts_remain_explicit(self):
        scheduled=live.ordered(self.contract)
        self.binding['requests']={p['call_id']:dict(store='rareplanes') for p in scheduled}
        first=scheduled[0];second=scheduled[1]
        (self.output/(first['call_id']+'-started.json')).write_text(json.dumps(dict(planned=first,monotonic_ns=1)))
        orphan=dict(planned=second,result=dict(status='failed'))
        (self.output/(second['call_id']+'-receipt.json')).write_text(json.dumps(orphan))
        rows,starts,missing,orphans,issues=report.collect_rows(self.binding,{})
        self.assertEqual(missing,[first['call_id']]);self.assertEqual(orphans,[orphan]);self.assertEqual(len(starts),1)
        self.assertEqual(rows[0]['planned'],first);self.assertEqual(rows[0]['result']['status'],'missing_terminal_receipt')
        self.assertTrue(issues)

    def test_offline_restoration_matches_exact_authority_journal_and_lease(self):
        leases,lease,sysroot,path,receipt=self.fixture();terminal=self.restoration(receipt)
        authority_sha=hashlib.sha256(terminal['authority_text'].encode()).hexdigest()
        self.assertTrue(live.verify_retained_restoration(self.binding,terminal,lease.name,authority_sha))
        for field in ('lease','authority','journal','privileged','ordinary'):
            damaged=copy.deepcopy(terminal);identity=lease.name;digest=authority_sha
            if field=='lease': identity='wrong'
            elif field=='authority': digest='0'*64
            elif field=='journal': damaged['journal_text']+=' '
            elif field=='privileged': damaged['verification']['restored']=False
            else: damaged['restoration']['installation']={}
            with self.assertRaises(ValueError): live.verify_retained_restoration(self.binding,damaged,identity,digest)

    def test_reconstruction_needs_no_removed_builds_or_live_reservation(self):
        prep=self.output/'preparation.json';prep.write_text(json.dumps(self.binding));digest=live.sha(prep)
        original=copy.deepcopy(self.binding)
        with patch.object(live,'verify_identities',side_effect=AssertionError('no live sources')), \
             patch.object(live,'admit',side_effect=AssertionError('no live lease')):
            self.assertEqual(report.retained_binding(prep,digest,self.v1,self.register,self.design),original)
        self.design.write_text('{"changed":true}')
        with self.assertRaises(ValueError): report.retained_binding(prep,digest,self.v1,self.register,self.design)

    def test_complete_retained_v2_report_reproduces_all_28_decisions(self):
        leases,lease,sysroot,path,receipt=self.fixture();restoration=self.restoration(receipt)
        authority_sha=hashlib.sha256(restoration['authority_text'].encode()).hexdigest();digest='d'*64
        environment=dict(controller_affinity=receipt['controller_cpus'],reservation={},boost=None,cpu={},task_cgroup={})
        self.binding['requests']={}
        self.binding['builds']={arm:{mode:dict(build=dict(binary_sha256=arm)) for mode in ('ordinary','resource')}
                                for arm in ('baseline','candidate')}
        self.binding['prerequisites']={}
        for key in live.PREREQUISITES:
            evidence=self.root/(key+'.json');evidence.write_text('{}')
            self.binding['prerequisites'][key]=dict(path=str(evidence),sha256=live.sha(evidence))
        rows=[]
        for planned in live.ordered(self.contract):
            request=dict(codec='emuella',operation='encode',case_id=planned.get('case_id','authored'),
                         round=planned.get('round',0),style=planned.get('style',1),workers=planned.get('workers',8),
                         raw_sha256='raw',stream_sha256='stream',max_working_bytes=768*1024**2,max_output_bytes=64*1024**2)
            observed=dict(request,exact=True,binary_sha256=planned['arm'],boundary=live.refresh.BOUNDARY,
                          samples_ns=[100_000_000 if planned['arm']=='baseline' else 80_000_000])
            if planned['stage']=='allocation':
                observed.update(samples_ns=[],working_bytes=100,output_capacity=20,output_capacity_limit=30,
                    allocation_diagnostic=dict(allocation_peak_additional_requested_bytes=90,
                                               successful_allocation_or_reallocation_requests=3))
            row=dict(planned=planned,result=dict(status=0,observation=observed),gates_passed=True,
                     environment=dict(before=environment,after=environment,issues=[]))
            if planned['stage']=='allocation': row['resources']=live.panels.resources.resource_observation(observed,request)
            self.binding['requests'][planned['call_id']]=dict(store='rareplanes',request=request)
            folder=self.output/planned['call_id'];folder.mkdir()
            (folder/'request.json').write_text(json.dumps(request))
            (self.output/(planned['call_id']+'-started.json')).write_text(json.dumps(dict(planned=planned,monotonic_ns=planned['index']+1)))
            (self.output/(planned['call_id']+'-receipt.json')).write_text(json.dumps(row));rows.append(row)
        consumption=dict(started_calls=2648,wall_seconds=100,evidence_bytes=100,build_bytes=100)
        estimators={40:authored.estimator,160:authored.estimator}
        expected=live.finite.analyse_attempt(self.contract,rows,estimators,checks=dict.fromkeys(live.finite.CHECKS,True),consumption=consumption)
        records={
            'execution-started.json':dict(preparation_sha256=digest,authority_sha256=authority_sha,lease_id=lease.name),
            'execution-complete.json':dict(schema=live.SCHEMA,status=0,error=None,restoration_verified=True,lease_id=lease.name),
            'launch.json':dict(preparation_sha256=digest,authority_sha256=authority_sha,condition=live.common_authority(receipt),environment=environment),
            'independent-restoration.json':restoration,
            'placement-original.json':dict(original=[0],intended=receipt['controller_cpus']),
            'restoration.json':dict(restored=True,worker_cgroup_empty=True,intervening_change=False,host_policy_changes=False,
                                   original=[0],final=[0],observed_before_restore=receipt['controller_cpus']),
            'completion.json':dict(schema=live.SCHEMA,preparation_sha256=digest,started_calls=2648,consumption=consumption,
                                   missing_call_ids=[],disposition=live.finite.PASS,issues=[],decisions=expected['endpoints'])}
        for name,value in records.items(): (self.output/name).write_text(json.dumps(value))
        with patch.object(live,'verify_identities',side_effect=AssertionError('removed sources')), \
             patch.object(live,'admit',side_effect=AssertionError('no live reservation')):
            result=report.reconstruct(self.binding,digest,estimators)
        self.assertEqual(result['issues'],[])
        self.assertEqual(result['schema'],live.SCHEMA);self.assertEqual(result['disposition'],live.finite.PASS)
        self.assertEqual(result['endpoints'],expected['endpoints']);self.assertEqual(len(result['endpoints']),28)
        self.assertEqual(result['raw_rows'],rows);self.assertFalse(result['promotion_authorised'])
        # A vanished terminal receipt remains an explicit failed start, never a successful subset.
        (self.output/'ordinary-2479-receipt.json').unlink()
        result=report.reconstruct(self.binding,digest,estimators)
        self.assertEqual(result['disposition'],live.finite.INCOMPLETE)
        self.assertEqual(result['missing_terminal_call_ids'],['ordinary-2479'])
        self.assertEqual(len(result['started_receipts']),2648)
