"""Authored worker lifecycle and incomplete-evidence checks, no external assets."""
import importlib.util
import json
import os
import subprocess
from pathlib import Path
import tempfile
import unittest

spec = importlib.util.spec_from_file_location('classic', Path(__file__).resolve().parents[1] / 'scripts/real-scene-classic.py')
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class ClassicTests(unittest.TestCase):
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
