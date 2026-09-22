"""Authored offline metadata fixtures; no codec, corpus or host-state access."""
import copy
import hashlib
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

SPEC = importlib.util.spec_from_file_location('execution_audit', Path(__file__).resolve().parents[1]/'scripts/measurement_execution_audit.py')
a = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(a)


def stat(ticks=None):
    ticks = ticks or {}
    return '\n'.join(f'cpu{cpu} {ticks.get(cpu, 0)} 2 3 900 0 70 20 0 8 1' for cpu in range(32))


def environment():
    before = dict(proc=dict(stat=stat()), monotonic_ns=100,
                  reservation={'cpu.max': 'max 100000', 'ancestor_limits': [{'cpu.max': None}]},
                  task_cgroup={'cpu.stat': 'usage_usec 100\nnr_throttled 2'})
    after = copy.deepcopy(before)
    after['proc']['stat'] = stat({0: 100})
    after['monotonic_ns'] = 200
    return dict(before=before, after=after, issues=[])


def fixture(root):
    manifest = {}

    def write(name, value):
        path = root/name
        path.parent.mkdir(parents=True, exist_ok=True)
        data = json.dumps(value).encode()
        path.write_bytes(data)
        manifest[name] = hashlib.sha256(data).hexdigest()

    cells = [dict(workers=w, operation='decode', asset=dict(id=f'authored-{i}')) for i, w in enumerate([8, 8, 8, 1])]
    binding = dict(policy=a.POLICY, schedule=a.schedule(), pairs=40,
                   condition=dict(reserved_cpus=a.CPUS, worker_cpus=list(range(8))), cells=cells, build=dict(binary_sha256='a'*64))
    write('binding.json', binding)
    digest = manifest['binding.json']
    write('launch.json', dict(binding_sha256=digest))
    sessions = []
    for entry in a.schedule():
        rows = []
        cell = cells[entry['cell']]
        for identity in a.calls(entry):
            result = dict(status=0, process_cpu_seconds=1.0, process_wall_ns=2_000_000_000,
                          observation=dict(exact=True, workers=cell['workers'], binary_sha256='a'*64,
                                           operation='decode', case_id=cell['asset']['id']))
            row = dict(**identity, result=result, started_monotonic_ns=50)
            rows.append(row)
            name = f"session-{entry['index']:02}/call-{identity['round']:02}-{identity['arm']}"
            write(name+'-receipt.json', row)
            write(name+'-environment.json', environment())
            write(name+'-started.json', dict(identity=identity, monotonic_ns=50))
        write(f"session-{entry['index']:02}/session.json", dict(session=entry, rows=rows,
              binding_sha256=digest, valid=True, complete=True, issues=[]))
        sessions.append(dict(session=entry, raw_rows=rows, valid=True, complete=True))
    for i in range(4):
        write(f'preflight/call-{i:02}-preflight-started.json', dict(identity=dict(round=i, arm='preflight', position=0)))
    write('report.json', dict(policy=a.POLICY, binding_sha256=digest, operationally_complete=True,
                             completion=dict(started_calls=964), sessions=sessions))
    return manifest


def manifest_digest(root, manifest):
    data = json.dumps(manifest).encode()
    (root/'observation-manifest.json').write_bytes(data)
    return hashlib.sha256(data).hexdigest()


class ExecutionAuditTests(unittest.TestCase):
    def test_user_nice_system_excludes_guest_double_count_and_other_fields(self):
        self.assertEqual(a.cpu_counters(stat({0: 10}))[0], (10, 2, 3))
        d = a.derive(environment(), dict(process_cpu_seconds=1, process_wall_ns=2_000_000_000))
        self.assertEqual(d['reserved_ticks'], 100)
        self.assertEqual(d['dominant_share'], 1)
        self.assertEqual(d['whole_process_cpu_wall_ratio'], .5)

    def test_multicore_share_and_outside_reservation(self):
        e = environment()
        e['after']['proc']['stat'] = stat({0: 30, 1: 70, 8: 45, 16: 100})
        d = a.derive(e, dict(process_cpu_seconds=1, process_wall_ns=1))
        self.assertEqual((d['dominant_logical_cpu'], d['dominant_share']), (16, .5))
        self.assertEqual((d['worker_dominant_logical_cpu'], d['worker_dominant_share']), (1, .7))
        self.assertEqual(d['reserved_sibling_cpu_ticks'], 100)
        self.assertEqual(d['other_reserved_cpu_ticks'], 100)
        self.assertEqual(d['other_worker_cpu_ticks'], 30)
        self.assertEqual(d['outside_reserved_cpu_ticks'], 45)

    def test_invalid_cpu_counters_and_deltas_rejected(self):
        for value in (None, '', stat().replace('cpu0 0', 'cpu0 -1'), stat().replace('cpu0 0', 'cpu0 bad'),
                      '\n'.join(stat().splitlines()[1:]), stat()+'\ncpu0 1 2 3', 'cpu0 0 2\n'+'\n'.join(stat().splitlines()[1:])):
            with self.subTest(value=value), self.assertRaises(ValueError):
                a.cpu_counters(value)
        e = environment()
        e['before']['proc']['stat'] = stat({0: 200})
        with self.assertRaisesRegex(ValueError, 'negative'):
            a.derive(e, dict(process_cpu_seconds=1, process_wall_ns=1))

    def test_optional_throttle_is_unavailable_and_quotas_preserved(self):
        e = environment()
        e['after']['task_cgroup']['cpu.stat'] = 'usage_usec 200'
        d = a.derive(e, dict(process_cpu_seconds=1, process_wall_ns=1))
        self.assertEqual(d['nr_throttled_before'], 2)
        self.assertIsNone(d['nr_throttled_after'])
        self.assertIsNone(d['nr_throttled_delta'])
        self.assertEqual(d['quota_after'], dict(leaf='max 100000', ancestors=[None]))
        for value in ('nr_throttled -1', 'nr_throttled x', 'nr_throttled 1\nnr_throttled 2'):
            with self.assertRaises(ValueError):
                a.throttle_counter(value)

    def test_complete_coverage_hashes_and_no_overwrite(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            manifest = fixture(root)
            digest = manifest_digest(root, manifest)
            output = root/'audit.json'
            a.main(['--root', str(root), '--manifest-sha256', digest, '--output', str(output)])
            result = json.loads(output.read_text())
            self.assertEqual(len(result['calls']), 960)
            self.assertEqual(len(result['sessions']), 12)
            self.assertEqual(result['coverage'], dict(sessions=12, measured_calls=960, started_calls=964, verified_metadata_files=2900))
            self.assertEqual(result['source_identity']['report_sha256'], manifest['report.json'])
            with patch.object(a, 'audit', side_effect=AssertionError('must not audit')):
                with self.assertRaises(FileExistsError):
                    a.main(['--root', str(root), '--manifest-sha256', digest, '--output', str(output)])

    def test_missing_tampered_unbound_and_incomplete_evidence_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            manifest = fixture(root)
            digest = manifest_digest(root, manifest)
            name = 'session-00/call-00-A-environment.json'
            original = (root/name).read_bytes()
            for action in ('missing', 'tampered', 'unbound', 'bad_manifest', 'coverage', 'extra_start'):
                with self.subTest(action=action):
                    m = manifest.copy()
                    if action == 'missing':
                        (root/name).unlink()
                    elif action == 'tampered':
                        (root/name).write_text('{}')
                    elif action == 'unbound':
                        del m[name]
                    elif action == 'coverage':
                        p = root/'session-00/session.json'
                        s = json.loads(p.read_text()); s['rows'].pop()
                        p.write_text(json.dumps(s))
                        m['session-00/session.json'] = hashlib.sha256(p.read_bytes()).hexdigest()
                    elif action == 'extra_start':
                        (root/'session-00/call-40-A-started.json').write_text('{}')
                    test_digest = manifest_digest(root, m)
                    with self.assertRaises((ValueError, FileNotFoundError)):
                        a.audit(root, '0'*64 if action == 'bad_manifest' else test_digest)
                    (root/name).write_bytes(original)
                    if action == 'coverage':
                        # Restore the authored fixture before testing extra retained starts.
                        manifest = fixture(root)


if __name__ == '__main__':
    unittest.main()
