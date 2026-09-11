"""Authored worker lifecycle and incomplete-evidence checks, no external assets."""
import importlib.util
import json
import os
import subprocess
from pathlib import Path
import tempfile
import unittest
from unittest import mock
from types import SimpleNamespace

spec = importlib.util.spec_from_file_location('classic', Path(__file__).resolve().parents[1] / 'scripts/real-scene-classic.py')
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class ClassicTests(unittest.TestCase):
    def test_controller_reserve_failure_prevents_dispatch(self):
        with mock.patch.object(module.resource,'getrusage',return_value=SimpleNamespace(ru_maxrss=module.CONTROLLER//1024+1)), mock.patch.object(module,'execute') as execute:
            row=module.schedule_cohort(Path('/unused'),{},Path('/unused'),0,list(range(8)),8)
        self.assertEqual(row['status'],'rejected')
        execute.assert_not_called()
        self.assertNotIn('application_wall_ns',row)

    def test_post_cohort_resource_failures_retain_all_observations(self):
        for controller_kib,child_peak in ((module.CONTROLLER//1024+1,1024),(1,module.BUDGET//8)):
            with self.subTest(controller_kib=controller_kib), mock.patch.object(module.resource,'getrusage',side_effect=[SimpleNamespace(ru_maxrss=1),SimpleNamespace(ru_maxrss=controller_kib)]), mock.patch.object(module,'execute',return_value=dict(status=0,process_peak_rss_bytes=child_peak)) as execute:
                row=module.schedule_cohort(Path('/unused'),{},Path('/unused'),0,list(range(8)),8)
            self.assertEqual(row['status'],'failed')
            self.assertEqual(len(row['results']),8)
            self.assertEqual(execute.call_count,8)
            self.assertIn('application_wall_ns',row)

    def test_selected_reprofile_rejects_over_budget_without_dispatch(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp)
            (root/'streams').mkdir()
            (root/'streams/authored-style1.j2k').write_bytes(b'authored stream')
            asset=dict(id='authored',product='PAN16',bytes=module.BUDGET,path='authored.raw',sha256='0'*64,
                       image=dict(width=4,height=4,components=1,precision=16))
            args=SimpleNamespace(schedule='8x1',prepared=root,output=root,binary=Path('/unused'))
            with mock.patch.object(module,'execute',return_value=dict(status=0,observation=dict(requirements_working_bytes=module.WORKING))) as execute:
                rows=module.reprofile_schedule(args,[asset],[0,1,2,3,4,5,6,7],root/'probe')
            self.assertEqual(execute.call_count,1)
            self.assertEqual(len(rows),2)
            self.assertTrue(all(r['status']=='rejected' and 'invocations' not in r for r in rows))

    def test_clean_build_rejects_hidden_source_changes_and_existing_output(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp)
            source=root/'source';source.mkdir()
            def git(*args):
                return subprocess.check_output(['git','-C',str(source),'-c','user.name=Authored Test','-c','user.email=test@example.invalid',*args],text=True,stderr=subprocess.DEVNULL).strip()
            git('init','-q')
            tracked=source/'authored.txt';tracked.write_text('committed bytes')
            git('add','authored.txt');git('commit','-qm','Authored source')
            self.assertEqual(module.clean_source(source)['source_revision'],git('rev-parse','HEAD'))
            destination=root/'existing';destination.mkdir()
            with self.assertRaises(FileExistsError):
                module.build_consumer(source,destination)
            with self.assertRaises(ValueError):
                module.build_consumer(source,source/'target')
            git('update-index','--assume-unchanged','authored.txt')
            tracked.write_text('hidden changed bytes')
            self.assertEqual(git('status','--porcelain'),'')
            with self.assertRaises(ValueError):
                module.clean_source(source)

    def test_build_identity_does_not_follow_a_later_checkout_head(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp)
            def git(*args):
                return subprocess.check_output(['git','-C',str(root),'-c','user.name=Authored Test','-c','user.email=test@example.invalid',*args],text=True,stderr=subprocess.DEVNULL).strip()
            git('init','-q')
            source=root/'source.txt';source.write_text('first')
            (root/'Cargo.toml').write_text('[workspace]\n')
            (root/'Cargo.lock').write_text('version = 4\n')
            git('add','source.txt','Cargo.toml','Cargo.lock');git('commit','-qm','First authored state')
            revision=git('rev-parse','HEAD');tree=git('rev-parse','HEAD^{tree}')
            source.write_text('second');git('commit','-qam','Second authored state')
            self.assertNotEqual(revision,git('rev-parse','HEAD'))
            batch=root/'batch';batch.write_bytes(b'authored batch')
            allocation=root/'allocation';allocation.write_bytes(b'authored diagnostic')
            provenance=root/'build.json'
            profile=dict(opt_level='3',debug_assertions=False,test=False)
            module.write(provenance,dict(source_revision=revision,source_tree=tree,requested_profile='perf',
                workspace_cargo_sha256=module.digest(root/'Cargo.toml'),lock_sha256=module.digest(root/'Cargo.lock'),
                artefacts=[dict(target=dict(name=n),features=['parallel']) for n in ('emuella_j2k_core','emuella_j2k_codestream')],
                binaries={
                'lossless_bypass_batch':dict(sha256=module.digest(batch),features=['parallel'],profile=profile),
                'lossless_bypass_allocation':dict(sha256=module.digest(allocation),features=['parallel'],profile=profile)}))
            bound=module.bind_build(batch,allocation,root,provenance)
            self.assertEqual(bound['codec_revision'],revision)
            self.assertEqual(bound['codec_tree'],tree)
            allocation.write_bytes(b'changed diagnostic')
            with self.assertRaises(ValueError):
                module.bind_build(batch,allocation,root,provenance)

    def test_failed_worker_is_retained_without_success_observation(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            result = module.execute(Path('/bin/sh'), {}, root/'batch', [min(os.sched_getaffinity(0))], extra_args=['-c','exit 7'])
            self.assertEqual(result['status'], 7)
            self.assertNotIn('observation', result)
            self.assertEqual(json.loads((root/'batch/result.json').read_text()), result)
            self.assertTrue((root/'batch/stderr.txt').is_file())
            with self.assertRaises(FileExistsError):
                module.execute(Path('/bin/sh'), {}, root/'batch', [min(os.sched_getaffinity(0))], extra_args=['-c','exit 0'])

    def test_success_exit_with_invalid_output_is_retained_as_failure(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            result = module.execute(Path('/bin/sh'), {}, root/'batch', [min(os.sched_getaffinity(0))], extra_args=['-c','printf invalid'])
            self.assertEqual(result['status'], 'invalid_response')
            self.assertNotIn('observation', result)
            self.assertEqual((root/'batch/stdout.json').read_text(), 'invalid')

    def test_incomplete_coverage_never_invokes_estimator(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            module.write(root/'batches.json', [dict(case='authored',operation='encode',contrast='bypass_at1',style=0,workers=1,result=dict(status=0))])
            module.analyse(root, Path('/nonexistent-estimator'))
            rows = json.loads((root/'comparisons.json').read_text())
            self.assertEqual(len(rows), 6)
            self.assertTrue(all(r['verdict']=='invalid' for r in rows))
