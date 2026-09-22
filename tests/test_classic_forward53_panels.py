import contextlib
from collections import Counter, defaultdict
import importlib.util
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

SPEC = importlib.util.spec_from_file_location('panels', Path(__file__).resolve().parents[1] / 'scripts/classic-forward53-panels.py')
panels = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(panels)


def assets():
    rareplanes = [dict(id=f'{prefix}-{product}', product=product)
                  for prefix in ('94_Mansfield', '106_Boca')
                  for product in ('PAN16', 'MS16', 'RGB8', 'RGB16')]
    rareplanes.append(dict(id='105_Tok-RGB8', product='RGB8'))
    suffixes = ['AOI_2_Vegas_img1454', 'AOI_3_Paris_img235', 'AOI_4_Shanghai_img1196']
    suffixes += [f'AOI_2_Vegas_img{i}' for i in range(9)]
    spacenet = [dict(id='RGB-PanSharpen_' + suffix, role='development') for suffix in suffixes]
    return rareplanes, spacenet


class ScheduleTests(unittest.TestCase):
    def test_fixed_counts_scope_and_balanced_round_positions(self):
        rows = panels.schedule(*assets())
        self.assertEqual(len(rows), 168)
        self.assertEqual(Counter(r['stage'] for r in rows), panels.COUNTS)
        self.assertEqual([r['index'] for r in rows], list(range(168)))
        self.assertTrue(all('Boca' not in r['case_id'] and 'Tok' not in r['case_id'] for r in rows))
        ordinary = [r for r in rows if r['stage'] == 'ordinary']
        rgb = [r for r in ordinary if r['case_id'] == '94_Mansfield-RGB8']
        self.assertEqual(len(rgb), 36)
        groups = defaultdict(list)
        for r in rgb:
            groups[r['style'], r['workers'], r['round']].append(r['arm'])
        for style in (0, 1):
            for workers in (1, 8):
                for position in range(3):
                    self.assertEqual({groups[style, workers, round_id][position] for round_id in range(3)}, set(panels.ARMS))
        self.assertEqual(Counter(r['mode'] for r in rows), dict(resource=68, ordinary=88, diagnostic=12))
        self.assertEqual(len([r for r in ordinary if r['store'] == 'spacenet']), 12)
        self.assertEqual(len([r for r in ordinary if r['store'] == 'rareplanes' and not r['case_id'].endswith('RGB8')]), 36)
        self.assertTrue(all(r['workers'] == 8 and r['origin'] == 'openjpeg' for r in rows if r['stage'] == 'decoder'))
        self.assertEqual(rows, panels.schedule(*assets()))

    def test_no_reserved_or_duplicate_selection(self):
        rareplanes, spacenet = assets()
        for delta in ({'role': 'reserved'}, {'id': 'RGB-PanSharpen_AOI_5_Khartoum_img1'}):
            changed = [dict(a) for a in spacenet]
            changed[0].update(delta)
            with self.assertRaises(ValueError):
                panels.schedule(rareplanes, changed)
        with self.assertRaises(ValueError):
            panels.schedule(rareplanes, spacenet[:-1] + [spacenet[0]])
        with self.assertRaises(ValueError):
            panels.schedule(rareplanes[:-1], spacenet)

    def test_queries_remain_identical_across_forms(self):
        rows = [dict(planned=dict(case_id='rgb', style=0, workers=8, arm=arm),
                     result=dict(observation=dict(working_bytes=100, output_capacity_limit=50))) for arm in panels.ARMS]
        panels.validate_resource_queries(rows)
        rows[-1]['result']['observation']['working_bytes'] = 101
        with self.assertRaisesRegex(ValueError, 'query changed'):
            panels.validate_resource_queries(rows)


class BuildBindingTests(unittest.TestCase):
    def fixture(self, root):
        root = Path(root)
        binary = root / 'authored-worker'
        binary.write_text('authored executable identity; never executed')
        source = dict(source_revision='a' * 40, source_tree='b' * 40, source_files_sha256={})
        benchmark = dict(source_files_sha256={'workers/src/lib.rs': 'worker-source'})
        receipt = dict(panel_width=16, forms={})
        config = dict(arms={})
        for arm, form in zip(panels.ARMS, ('Reference', 'RowPanelScalar', 'RowPanelParallel')):
            receipt['forms'][arm] = dict(source=str(root), revision='a' * 40, form=form)
            config['arms'][arm] = {}
            for mode in panels.MODES:
                path = root / (arm + '-' + mode + '.json')
                build = dict(codec=source, benchmark=benchmark, binary=str(binary), binary_sha256=panels.refresh.sha(binary),
                             libraries={}, logs={}, command=['cargo', 'build', '--profile', 'perf'],
                             encoder_backend='default', scheduling_window='default', sampling=False,
                             allocation_diagnostics=mode == 'resource', execution_diagnostics=mode == 'diagnostic',
                             forward53_diagnostics=mode == 'diagnostic' and arm != 'reference',
                             rustc='authored', openjpeg='authored', environment={}, cargo_configs={}, lock_sha256='lock',
                             artefacts=[dict(target=dict(name=target), features=['parallel'], profile=dict(opt_level='3'))
                                        for target in ('emuella_j2k_core', 'emuella_j2k_codestream')])
                path.write_text(json.dumps(build))
                config['arms'][arm][mode] = str(path)
        return config, receipt, source, binary

    def test_all_build_modes_and_fresh_binary_identity(self):
        with tempfile.TemporaryDirectory() as directory:
            config, receipt, source, binary = self.fixture(directory)
            with patch.object(panels.refresh.classic, 'clean_source', return_value=source):
                self.assertEqual(set(panels.build_bindings(config, receipt)), set(panels.ARMS))
                binary.write_text('changed executable')
                with self.assertRaisesRegex(ValueError, 'binary identity changed'):
                    panels.build_bindings(config, receipt)

    def test_source_instrumentation_and_worker_identity_are_enforced(self):
        for field, value, message in (
                ('codec', {}, 'codec source'),
                ('forward53_diagnostics', False, 'instrumentation'),
                ('benchmark', dict(source_files_sha256={'workers/src/lib.rs': 'different'}), 'worker source'),
                ('sampling', True, 'instrumentation')):
            with self.subTest(field=field), tempfile.TemporaryDirectory() as directory:
                config, receipt, source, _ = self.fixture(directory)
                path = Path(config['arms']['qW']['diagnostic'])
                build = json.loads(path.read_text())
                build[field] = value
                path.write_text(json.dumps(build))
                with patch.object(panels.refresh.classic, 'clean_source', return_value=source):
                    with self.assertRaisesRegex(ValueError, message):
                        panels.build_bindings(config, receipt)

    def test_ordinary_build_cannot_enable_forward53_diagnostics(self):
        with tempfile.TemporaryDirectory() as directory:
            config, receipt, source, _ = self.fixture(directory)
            path = Path(config['arms']['qW']['ordinary'])
            build = json.loads(path.read_text())
            build['forward53_diagnostics'] = True
            path.write_text(json.dumps(build))
            with patch.object(panels.refresh.classic, 'clean_source', return_value=source):
                with self.assertRaisesRegex(ValueError, 'instrumentation'):
                    panels.build_bindings(config, receipt)


class LifecycleTests(unittest.TestCase):
    def fixture(self, root):
        root = Path(root)
        budget = root / 'budget.json'
        budget.write_text(json.dumps(dict(policy=panels.POLICY, protected_output_roots=[str(root)], scratch_root=str(root / 'scratch'))))
        rows = panels.schedule(*assets())
        for r in rows:
            r['request'] = dict(max_working_bytes=768 * 1024**2, max_output_bytes=64 * 1024**2)
        builds = {a: {m: dict(build=dict(binary='fixture-worker')) for m in panels.MODES} for a in panels.ARMS}
        frozen = dict(config=dict(budget=str(budget), cpus=list(range(8)), stores={s: dict(output=str(root)) for s in ('rareplanes', 'spacenet')}),
                      bindings=dict(schedule=rows, builds=builds))
        freeze = root / 'freeze.json'
        freeze.write_text(json.dumps(frozen))
        return frozen, freeze

    @staticmethod
    def successful_result(*args, **kwargs):
        if kwargs['allocation_diagnostics']:
            return dict(status=0, observation=dict(samples_ns=[], working_bytes=100, output_capacity=50,
                        output_capacity_limit=50, allocation_diagnostic=dict(allocation_peak_additional_requested_bytes=99,
                        successful_allocation_or_reallocation_requests=3)))
        return dict(status=0, observation=dict(samples_ns=[123]))

    def test_resources_gate_later_stages_and_failure_is_not_retryable(self):
        with tempfile.TemporaryDirectory() as directory:
            frozen, freeze = self.fixture(directory)
            with self.assertRaisesRegex(ValueError, 'resource prerequisites'):
                panels.run(freeze, 'ordinary')
            with patch.object(panels, 'bind', return_value=frozen['bindings']), \
                    patch.object(panels.refresh, 'run_process', return_value=dict(status='timeout')) as launch, \
                    contextlib.redirect_stdout(io.StringIO()):
                with self.assertRaisesRegex(ValueError, 'stage incomplete'):
                    panels.run(freeze, 'resources')
                self.assertEqual(launch.call_count, 1)
                with self.assertRaises(FileExistsError):
                    panels.run(freeze, 'resources')
            self.assertFalse(panels.stage_complete(frozen, 'resources'))
            self.assertEqual(panels.read_rows(frozen, 'resources')[0]['result']['status'], 'timeout')
            state = json.loads((Path(directory) / 'budget-state.json').read_text())
            self.assertEqual(state['started_calls'], 1)
            output = Path(directory) / 'report.json'
            self.assertFalse(panels.report(freeze, output))
            report = json.loads(output.read_text())
            self.assertFalse(report['performance_claim'])
            self.assertEqual(report['observed_calls'], 1)
            self.assertEqual(len(report['stages']['resources']['missing_indices']), 67)

    def test_completed_stages_have_all_calls_and_no_diagnostic_timing_pool(self):
        with tempfile.TemporaryDirectory() as directory:
            frozen, freeze = self.fixture(directory)
            with patch.object(panels, 'bind', return_value=frozen['bindings']), \
                    patch.object(panels.refresh, 'run_process', side_effect=self.successful_result) as launch, \
                    contextlib.redirect_stdout(io.StringIO()):
                for stage in panels.STAGES:
                    panels.run(freeze, stage)
                    self.assertTrue(panels.stage_complete(frozen, stage))
            self.assertEqual(launch.call_count, 168)
            output = Path(directory) / 'report.json'
            self.assertTrue(panels.report(freeze, output))
            report = json.loads(output.read_text())
            self.assertEqual(sum(len(r['samples_ns']) for r in report['descriptive_ordinary']), 84)
            self.assertFalse(report['confirmation_supported'])
            self.assertEqual(report['disposition'], 'qualification-pending')
            self.assertEqual(json.loads((Path(directory) / 'budget-state.json').read_text())['started_calls'], 168)
            # A completed marker cannot hide missing or changed call receipts.
            first = panels.receipt_path(frozen, frozen['bindings']['schedule'][0])
            first.unlink()
            self.assertFalse(panels.stage_complete(frozen, 'resources'))

    def test_launch_exception_consumes_and_retains_attempt(self):
        with tempfile.TemporaryDirectory() as directory:
            frozen, freeze = self.fixture(directory)
            with patch.object(panels, 'bind', return_value=frozen['bindings']), \
                    patch.object(panels.refresh, 'run_process', side_effect=OSError('cannot launch')), \
                    contextlib.redirect_stdout(io.StringIO()):
                with self.assertRaises(ValueError):
                    panels.run(freeze, 'resources')
            row = panels.read_rows(frozen, 'resources')[0]
            self.assertEqual(row['result']['status'], 'launch_or_receipt_failure')
            self.assertEqual(row['result']['reason'], 'cannot launch')

    def test_changed_identity_stops_before_first_launch(self):
        with tempfile.TemporaryDirectory() as directory:
            frozen, freeze = self.fixture(directory)
            with patch.object(panels, 'bind', return_value={}), patch.object(panels.refresh, 'run_process') as launch:
                with self.assertRaisesRegex(ValueError, 'identity changed'):
                    panels.run(freeze, 'resources')
                launch.assert_not_called()
            self.assertFalse(panels.stage_complete(frozen, 'resources'))

    def test_policy_caps_and_failed_attempts_cannot_reset_ledger(self):
        with tempfile.TemporaryDirectory() as directory:
            _, freeze = self.fixture(directory)
            budget = panels.budget_module.Budget(freeze.parent / 'budget.json', panels.POLICY)
            self.assertEqual((budget.calls, budget.seconds, budget.protected_bytes, budget.scratch_bytes),
                             (180, 5400, 2 * 1024**3, 30 * 1024**3))
            budget.state_path.write_text(json.dumps(dict(started_unix=panels.time.time(), started_calls=180)))
            with self.assertRaisesRegex(ValueError, 'budget exhausted'):
                budget.before_call()


if __name__ == '__main__':
    unittest.main()
