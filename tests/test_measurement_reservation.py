"""Authored administrative simulations; never create a host cgroup or run sudo."""
import array
import copy
import importlib.util
import json
import os
from pathlib import Path
import socket
import subprocess
import tempfile
import threading
import unittest
import types
import uuid
import hashlib
from unittest.mock import patch, Mock

SPEC = importlib.util.spec_from_file_location('reservation', Path(__file__).resolve().parents[1] / 'scripts/measurement_reservation.py')
r = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(r)
REAL_LOAD = r.load


class ReservationTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.cg = self.root / 'cgroup'
        self.cg.mkdir()
        self.state_root = self.root / 'state'
        self.state_root.mkdir()
        (self.state_root / 'public').mkdir()
        self.addCleanup(patch.stopall)
        patch.object(r, 'CG', self.cg).start()
        patch.object(r, 'ROOT', self.state_root).start()
        self.state = {'unit': 'owned.service', 'uid': 3000, 'gid': 3000,
                      'before': {'policy': {'boost': '1'}}, 'changes': [], 'ownership': [],
                      'invocation': 'one'}
        self.group = self.cg / self.state['unit']
        self.group.mkdir()
        for name in ('workers', 'controller', 'supervisor'):
            (self.group / name).mkdir()
            (self.group / name / 'cgroup.procs').write_text('')
        patch.object(r, 'require_root').start()
        patch.object(r, 'load', side_effect=lambda: copy.deepcopy(self.state)).start()
        patch.object(r, 'policy', return_value={'boost': '1'}).start()
        patch.object(r, 'command', return_value='one').start()

    def put(self, path, value):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(value)

    def mutation(self, relative, original, applied):
        path = self.group / relative
        self.put(path, applied)
        self.state['changes'].append({'path': str(path), 'original': original, 'applied': applied})
        return path

    def test_fixed_masks_cover_siblings_and_leave_controller_disjoint(self):
        self.assertEqual(r.mask(r.RESERVED), '0-7,16-23')
        self.assertEqual(r.mask(r.HOUSE), '8-15,24-31')
        self.assertFalse(r.HOUSE & r.RESERVED)
        self.assertEqual(r.HOUSE | r.RESERVED, set(range(32)))
        self.assertEqual(r.cpus(r.mask(r.RESERVED)), r.RESERVED)
        self.assertEqual(r.LEASE, 10800)

    def test_journal_written_before_mutation_and_outside_path_rejected(self):
        path = self.group / 'cpuset.cpus.exclusive'
        self.put(path, '')
        journal = []
        with patch.object(r, 'save', side_effect=lambda state: journal.append((r.read(path), copy.deepcopy(state)))):
            r.mutate(self.state, path, '0-7,16-23')
        self.assertEqual(journal[0][0], '')
        self.assertEqual(journal[0][1]['changes'][0]['applied'], '0-7,16-23')
        with self.assertRaises(ValueError):
            r.mutate(self.state, self.cg / 'cpuset.cpus', '0')

    def test_restore_reverses_applied_changes_and_is_idempotent(self):
        exclusive = self.mutation('cpuset.cpus.exclusive', '', '0-7,16-23')
        partition = self.mutation('workers/cpuset.cpus.partition', 'member', 'isolated')
        self.assertFalse(r.restore())
        self.assertEqual(r.read(partition), 'member')
        self.assertEqual(r.read(exclusive), '')
        self.assertFalse(r.restore())
        self.assertTrue(json.loads(r.read(self.state_root / 'public/restoration.json'))['cleanup_executed'])

    def test_failed_write_intent_is_safe_to_restore(self):
        path = self.mutation('cpuset.cpus.exclusive', '', '0-7,16-23')
        path.write_text('')  # The journal was saved, but the kernel write failed.
        self.assertFalse(r.restore())
        self.assertEqual(r.read(path), '')

    def test_intervening_change_is_retained_and_reported(self):
        path = self.mutation('cpuset.cpus.exclusive', '', '0-7,16-23')
        path.write_text('1-7,17-23')
        self.assertTrue(r.restore())
        self.assertEqual(r.read(path), '1-7,17-23')
        receipt = json.loads(r.read(self.state_root / 'public/restoration.json'))
        self.assertIn('intervened', receipt['issues'][0])

    def test_live_process_or_replaced_invocation_blocks_recovery(self):
        self.put(self.group / 'workers/cgroup.procs', '123')
        with self.assertRaisesRegex(ValueError, 'processes remain'):
            r.restore()
        self.put(self.group / 'workers/cgroup.procs', '')
        with patch.object(r, 'command', return_value='other'):
            with self.assertRaisesRegex(ValueError, 'invocation changed'):
                r.restore()

    def test_policy_drift_never_written_back(self):
        with patch.object(r, 'policy', return_value={'boost': '0'}):
            self.assertTrue(r.restore())
        self.assertIn('not overwritten', json.loads(r.read(self.state_root / 'public/restoration.json'))['issues'][0])

    def partition(self):
        for name, value in [('cpuset.cpus.partition', 'isolated'),
                            ('cpuset.cpus.effective', '0-7,16-23'),
                            ('cpuset.cpus.exclusive.effective', '0-7,16-23')]:
            self.put(self.group / 'workers' / name, value)
        self.put(self.group / 'controller/cpuset.cpus.effective', '8-15,24-31')
        self.put(self.cg / 'user.slice/cpuset.cpus.effective', '8-15,24-31')

    def test_partition_and_ordinary_exclusion_required(self):
        self.partition()
        r.verify_partition(self.state)
        for relative, value in [('workers/cpuset.cpus.partition', 'isolated invalid (test)'),
                                ('workers/cpuset.cpus.exclusive.effective', '0-7'),
                                ('workers/cgroup.procs', '123'),
                                ('controller/cpuset.cpus.effective', '0-31')]:
            path = self.group / relative
            original = path.read_text()
            path.write_text(value)
            with self.assertRaises(ValueError):
                r.verify_partition(self.state)
            path.write_text(original)
        self.put(self.cg / 'user.slice/cpuset.cpus.effective', '0-31')
        with self.assertRaisesRegex(ValueError, 'exclusion'):
            r.verify_partition(self.state)

    def test_admission_probe_failure_is_not_success(self):
        with patch.object(r.os, 'fork', return_value=123), patch.object(r.os, 'waitpid', return_value=(123, 256)):
            with self.assertRaisesRegex(ValueError, 'admission failed'):
                r.admission_probe(self.state)

    def test_unprivileged_command_transport_preserves_exit_and_output(self):
        server, client = socket.socketpair(socket.AF_UNIX, socket.SOCK_SEQPACKET)
        self.addCleanup(server.close)
        self.addCleanup(client.close)
        result = []
        with tempfile.TemporaryFile() as output:
            thread = threading.Thread(target=lambda: result.append(r.execute_connection(server)))
            thread.start()
            payload = {'argv': ['/usr/bin/python3', '-I', '-c', 'print("authored"); raise SystemExit(7)'], 'cwd': str(self.root)}
            client.sendmsg([json.dumps(payload).encode()], [(socket.SOL_SOCKET, socket.SCM_RIGHTS, array.array('i', [output.fileno(), output.fileno()]))])
            self.assertEqual(json.loads(client.recv(4096)), {'returncode': 7})
            thread.join(timeout=5)
            self.assertFalse(thread.is_alive())
            output.seek(0)
            self.assertEqual(output.read(), b'authored\n')
        self.assertEqual(result, [7])

    def test_client_disconnect_terminates_only_its_command(self):
        server, client = socket.socketpair(socket.AF_UNIX, socket.SOCK_SEQPACKET)
        errors = []
        def serve():
            try:
                r.execute_connection(server)
            except ValueError as error:
                errors.append(str(error))
        with server, client, tempfile.TemporaryFile() as output:
            thread = threading.Thread(target=serve)
            thread.start()
            request = {'argv': ['/usr/bin/sleep', '30'], 'cwd': str(self.root)}
            client.sendmsg([json.dumps(request).encode()], [(socket.SOL_SOCKET, socket.SCM_RIGHTS, array.array('i', [output.fileno(), output.fileno()]))])
            client.shutdown(socket.SHUT_WR)
            thread.join(timeout=3)
            self.assertFalse(thread.is_alive())
            self.assertIn('disconnected', errors[0])

    def test_bad_command_cannot_invoke_process(self):
        server, client = socket.socketpair(socket.AF_UNIX, socket.SOCK_SEQPACKET)
        with server, client, tempfile.TemporaryFile() as output:
            request = {'argv': ['relative-program'], 'cwd': str(self.root)}
            client.sendmsg([json.dumps(request).encode()], [(socket.SOL_SOCKET, socket.SCM_RIGHTS, array.array('i', [output.fileno(), output.fileno()]))])
            with patch.object(r.subprocess, 'run') as execute:
                with self.assertRaisesRegex(ValueError, 'absolute'):
                    r.execute_connection(server)
                execute.assert_not_called()

    def test_drop_user_clears_privileges_before_command_environment(self):
        account = Mock(pw_name='task', pw_dir='/home/task')
        events = []
        with patch.object(r.pwd, 'getpwuid', return_value=account), patch.dict(r.os.environ, {'UNRELATED_SECRET': 'never-forward'}, clear=True), patch.object(r.os, 'initgroups', side_effect=lambda *a: events.append('groups')), patch.object(r.os, 'setresgid', side_effect=lambda *a: events.append('gid')), patch.object(r.os, 'setresuid', side_effect=lambda *a: events.append('uid')):
            r.drop_user(self.state)
            self.assertEqual(events, ['groups', 'gid', 'uid'])
            self.assertEqual(set(r.os.environ), {'PATH', 'HOME', 'USER', 'LOGNAME', 'LANG'})

    def test_final_verification_requires_unit_removal_and_original_snapshot(self):
        before = {'policy': {'boost': '1'}, 'root_controllers': 'cpu memory pids'}
        r.atomic(self.state_root / 'public/restoration.json', {'issues': [], 'before': before, 'unit': self.state['unit']})
        with patch.object(r, 'snapshot', return_value=before), patch('builtins.print'):
            self.assertTrue(r.verify())
            self.group.rename(self.cg / 'removed')
            self.assertFalse(r.verify())
        with patch.object(r, 'snapshot', return_value=dict(before, root_controllers='cpuset cpu memory pids')), patch('builtins.print'):
            self.assertTrue(r.verify())

    def test_start_command_has_expiry_cleanup_and_no_policy_mutations(self):
        # Host operations are fully mocked. Only temporary local state is written.
        self.state_root.rmdir() if not list(self.state_root.iterdir()) else None
        fresh = self.root / 'fresh'
        account = Mock(pw_gid=3000, pw_name='task')
        commands = []
        def launch(*args):
            commands.append(args)
            r.atomic(fresh / 'public/authority.json', {'authored': True})
            return ''
        with patch.object(r, 'ROOT', fresh), patch.object(r, 'inspect', return_value={}), patch.object(r.pwd, 'getpwuid', return_value=account), patch.object(r.os, 'chown'), patch.object(r, 'command', side_effect=launch), patch('builtins.print'):
            r.start(3000, 'explicit task authorisation')
        invocation = commands[0]
        self.assertIn('RuntimeMaxSec=10800', invocation)
        self.assertIn('KillMode=control-group', invocation)
        self.assertIn('DelegateSubgroup=supervisor', invocation)
        self.assertTrue(any(x.startswith('ExecStopPost=') for x in invocation))
        self.assertNotIn('sudo', ' '.join(invocation))
        self.assertNotIn('governor', ' '.join(invocation))
        with patch.object(r, 'ROOT', fresh), patch.object(r, 'inspect', return_value={}), patch.object(r.pwd, 'getpwuid', return_value=account):
            with self.assertRaises(FileExistsError):
                r.start(3000, 'same task')

    def trusted_state(self):
        identifier = str(uuid.uuid4())
        source = b'authored helper'
        (self.state_root / 'helper.py').write_bytes(source)
        value = dict(self.state, schema=r.SCHEMA, id=identifier,
                     unit='emuella-measurement-reservation-' + identifier + '.service',
                     boot=r.read('/proc/sys/kernel/random/boot_id'),
                     helper_sha256=hashlib.sha256(source).hexdigest())
        r.atomic(self.state_root / 'journal.json', value)
        real_stat = Path.lstat
        def root_stat(path):
            info = real_stat(path)
            return types.SimpleNamespace(st_mode=info.st_mode, st_uid=0)
        return value, root_stat

    def test_recovery_rejects_boot_and_helper_identity_changes(self):
        value, root_stat = self.trusted_state()
        with patch.object(Path, 'lstat', root_stat):
            self.assertEqual(REAL_LOAD()['id'], value['id'])
            (self.state_root / 'helper.py').write_bytes(b'changed')
            with self.assertRaisesRegex(ValueError, 'identity changed'):
                REAL_LOAD()
            (self.state_root / 'helper.py').write_bytes(b'authored helper')
            value['boot'] = 'other-boot'
            r.atomic(self.state_root / 'journal.json', value)
            with self.assertRaisesRegex(ValueError, 'another schema or boot'):
                REAL_LOAD()

    def test_recovery_rejects_symlink_or_writable_journal(self):
        _, root_stat = self.trusted_state()
        with patch.object(Path, 'lstat', root_stat):
            (self.state_root / 'journal.json').chmod(0o666)
            with self.assertRaisesRegex(ValueError, 'unsafe'):
                REAL_LOAD()
            (self.state_root / 'journal.json').unlink()
            (self.state_root / 'journal.json').symlink_to(self.root / 'unrelated')
            with self.assertRaisesRegex(ValueError, 'unsafe'):
                REAL_LOAD()

    def test_atomic_receipt_refuses_colliding_symlink_without_touching_target(self):
        target = self.root / 'untouched'
        target.write_text('original')
        path = self.state_root / 'receipt.json'
        temporary = path.with_name(path.name + '.fixed.new')
        temporary.symlink_to(target)
        with patch.object(r.uuid, 'uuid4', return_value='fixed'):
            with self.assertRaises(FileExistsError):
                r.atomic(path, {'value': 1})
        self.assertEqual(target.read_text(), 'original')
        self.assertTrue(temporary.is_symlink())

    def test_interrupted_journal_write_does_not_obstruct_repeated_recovery(self):
        path = self.mutation('cpuset.cpus.exclusive', '', '0-7,16-23')
        r.save(self.state)  # Last complete write-ahead record before interruption.
        partial = self.state_root / 'journal.json.killed-writer.new'
        partial.write_text('{partial write')
        # Also retain the former fixed name: neither is consumed or deleted.
        legacy = self.state_root / 'journal.json.new'
        legacy.write_text('{legacy partial')
        self.assertFalse(r.restore())
        self.assertEqual(r.read(path), '')
        self.assertTrue(json.loads(r.read(self.state_root / 'public/restoration.json'))['cleanup_executed'])
        self.assertFalse(r.restore())
        self.assertEqual(partial.read_text(), '{partial write')
        self.assertEqual(legacy.read_text(), '{legacy partial')

    def test_unprivileged_probe_child_moves_both_directions(self):
        destinations = []
        def write(path, value):
            destinations.append(path)
            return len(value)
        class Exit(Exception):
            pass
        with patch.object(r.os, 'fork', return_value=0), patch.object(Path, 'write_text', write), patch.object(r.os, 'sched_setaffinity') as affinity, patch.object(r.os, 'sched_getaffinity', return_value={0}), patch.object(r.os, '_exit', side_effect=Exit):
            with self.assertRaises(Exit):
                r.admission_probe(self.state)
        self.assertEqual(destinations, [self.group / 'workers/cgroup.procs', self.group / 'controller/cgroup.procs'])
        self.assertEqual([c.args[1] for c in affinity.call_args_list], [{0}, r.HOUSE])

    def test_verify_waits_for_systemd_reconciliation_with_a_bound(self):
        self.group.rename(self.cg / 'removed')
        before = {'policy': {}, 'root_controllers': 'cpu memory pids'}
        r.atomic(self.state_root / 'public/restoration.json', {'issues': [], 'before': before, 'unit': self.state['unit']})
        after = dict(before, root_controllers='cpuset cpu memory pids')
        with patch.object(r, 'snapshot', side_effect=[after, before]), patch.object(r.time, 'monotonic', side_effect=[0, 0, 1]), patch.object(r.time, 'sleep') as sleep, patch('builtins.print'):
            self.assertFalse(r.verify(wait=2))
            sleep.assert_called_once_with(0.2)

    def test_restrictive_umask_keeps_controller_path_and_receipts_accessible(self):
        account = Mock(pw_gid=3000, pw_name='task')
        for creation_mask in (0o077, 0o777):
            fresh = self.root / f'umask-{creation_mask}'
            def launch(*args):
                # Test the permissions already published at service launch.
                self.assertEqual(fresh.stat().st_mode & 0o777, 0o755)
                self.assertEqual((fresh / 'public').stat().st_mode & 0o777, 0o755)
                self.assertEqual((fresh / 'control').stat().st_mode & 0o777, 0o700)
                self.assertEqual((fresh / 'journal.json').stat().st_mode & 0o777, 0o644)
                r.atomic(fresh / 'public/authority.json', {'authored': True})
                return ''
            old = os.umask(creation_mask)
            try:
                with patch.object(r, 'ROOT', fresh), patch.object(r, 'inspect', return_value={}), patch.object(r.pwd, 'getpwuid', return_value=account), patch.object(r.os, 'chown'), patch.object(r, 'command', side_effect=launch), patch('builtins.print'):
                    r.start(3000, 'explicit task authorisation')
                self.assertEqual((fresh / 'public/authority.json').stat().st_mode & 0o777, 0o644)
            finally:
                self.assertEqual(os.umask(old), creation_mask)

    def retirement_state(self):
        self.group.rename(self.cg / 'removed')
        self.state.update(id=str(uuid.uuid4()), cleanup_executed=True)
        (self.state_root / 'helper.py').write_text('authored retained helper')
        r.save(self.state)
        r.atomic(self.state_root / 'public/restoration.json',
                 {'issues': [], 'before': self.state['before'], 'unit': self.state['unit']})
        real_stat = Path.lstat
        def root_stat(path):
            value = real_stat(path)
            return types.SimpleNamespace(st_mode=value.st_mode, st_uid=0)
        return root_stat

    def test_retire_preserves_failed_attempt_after_verified_restoration(self):
        root_stat = self.retirement_state()
        self.state_root.chmod(0o700)
        (self.state_root / 'public').chmod(0o700)
        original = (self.state_root / 'journal.json').read_bytes()
        with patch.object(Path, 'lstat', root_stat), patch.object(r, 'command', return_value='inactive'), patch.object(r, 'verify', return_value=False) as verify, patch('builtins.print'):
            self.assertEqual(r.retire_failed(), 0)
        verify.assert_called_once_with(wait=20)
        archive = self.state_root.with_name(self.state_root.name + '.failed-' + self.state['id'])
        self.assertFalse(self.state_root.exists())
        self.assertEqual((archive / 'journal.json').read_bytes(), original)
        self.assertEqual(archive.stat().st_mode & 0o777, 0o755)
        self.assertEqual((archive / 'public').stat().st_mode & 0o777, 0o755)
        receipt = json.loads((archive / 'retirement.json').read_text())
        self.assertEqual(receipt['original_modes']['.'], 0o700)
        self.assertFalse(receipt['automatic_restart'])

    def test_retire_refuses_ready_or_active_or_unrestored_attempt(self):
        self.retirement_state()
        for key, value in [('ready', True), ('cleanup_executed', False)]:
            original = self.state.get(key)
            self.state[key] = value
            with patch.object(r, 'command', return_value='inactive'), patch.object(r, 'verify', return_value=False), self.assertRaises(ValueError):
                r.retire_failed()
            self.state[key] = original
        self.state['cleanup_executed'] = True
        with patch.object(r, 'command', return_value='active'), self.assertRaisesRegex(ValueError, 'stopped'):
            r.retire_failed()
        with patch.object(r, 'command', return_value='inactive'), patch.object(r, 'verify', return_value=True), self.assertRaisesRegex(ValueError, 'restoration'):
            r.retire_failed()
        self.assertTrue(self.state_root.exists())

    def test_retire_refuses_archive_collision_and_unsafe_receipt(self):
        root_stat = self.retirement_state()
        archive = self.state_root.with_name(self.state_root.name + '.failed-' + self.state['id'])
        archive.mkdir()
        with patch.object(r, 'command', return_value='inactive'), patch.object(r, 'verify', return_value=False), self.assertRaises(FileExistsError):
            r.retire_failed()
        archive.rmdir()
        (self.state_root / 'public/restoration.json').chmod(0o666)
        with patch.object(Path, 'lstat', root_stat), patch.object(r, 'command', return_value='inactive'), patch.object(r, 'verify', return_value=False), self.assertRaisesRegex(ValueError, 'unsafe'):
            r.retire_failed()
        self.assertTrue(self.state_root.exists())

    def test_partial_start_failure_stops_only_owned_unit(self):
        account = Mock(pw_gid=3000, pw_name='task')
        fresh = self.root / 'partial'
        with patch.object(r, 'ROOT', fresh), patch.object(r, 'inspect', return_value={}), patch.object(r.pwd, 'getpwuid', return_value=account), patch.object(r.os, 'chown'), patch.object(r, 'command', side_effect=subprocess.TimeoutExpired('systemd-run', 30)), patch.object(r.subprocess, 'run', return_value=subprocess.CompletedProcess([], 0, '', '')) as stop:
            with self.assertRaises(subprocess.TimeoutExpired):
                r.start(3000, 'authorised')
        args = stop.call_args.args[0]
        self.assertEqual(args[:2], ['/usr/bin/systemctl', 'stop'])
        self.assertTrue(args[2].startswith('emuella-measurement-reservation-'))

    def balanced_partition(self, condition='balanced'):
        patch.object(r, 'CONDITION', condition).start()
        self.state.update(condition=condition, partition_mode='root')
        self.state['before']['isolated'] = ''
        self.partition()
        self.put(self.group / 'workers/cpuset.cpus.partition', 'root')
        self.put(self.group / 'cpuset.cpus.partition', 'member')
        self.put(self.group / 'cgroup.procs', '')
        self.put(self.group / 'cpuset.cpus.effective', r.mask(r.HOUSE))
        self.put(self.group / 'supervisor/cpuset.cpus.effective', r.mask(r.HOUSE))
        self.put(self.cg / 'cpuset.cpus.isolated', '')
        self.put(self.cg / 'user.slice/session.scope/cpuset.cpus.effective', r.mask(r.HOUSE))

    def test_balanced_exclusion_checks_worker_ancestor_supervisor_and_descendants(self):
        self.check_balanced_exclusion_checks_worker_ancestor_supervisor_and_descendants('balanced')

    def test_balanced_aa_exclusion_checks_worker_ancestor_supervisor_and_descendants(self):
        self.check_balanced_exclusion_checks_worker_ancestor_supervisor_and_descendants('balanced-aa')

    def check_balanced_exclusion_checks_worker_ancestor_supervisor_and_descendants(self, condition):
        self.balanced_partition(condition)
        r.verify_partition(self.state)
        for path, value in [
                (self.group / 'workers/cpuset.cpus.partition', 'isolated'),
                (self.group / 'workers/cpuset.cpus.partition', 'root invalid (test)'),
                (self.group / 'workers/cpuset.cpus.exclusive.effective', '0-7'),
                (self.group / 'cpuset.cpus.partition', 'root'),
                (self.group / 'cpuset.cpus.effective', '0-31'),
                (self.group / 'cgroup.procs', '123'),
                (self.group / 'supervisor/cpuset.cpus.effective', '0-31'),
                (self.group / 'controller/cpuset.cpus.effective', '0-31'),
                (self.cg / 'user.slice/session.scope/cpuset.cpus.effective', '0-31'),
                (self.cg / 'cpuset.cpus.isolated', '0-7,16-23')]:
            with self.subTest(path=path, value=value):
                original = path.read_text()
                path.write_text(value)
                with self.assertRaises(ValueError):
                    r.verify_partition(self.state)
                path.write_text(original)
        self.put(self.group / 'workers/child/cgroup.procs', '')
        with self.assertRaisesRegex(ValueError, 'invalid or occupied'):
            r.verify_partition(self.state)

    def test_balanced_configures_root_partition_and_restores_originals(self):
        self.check_balanced_configures_root_partition_and_restores_originals('balanced')

    def test_balanced_aa_configures_root_partition_and_restores_originals(self):
        self.check_balanced_configures_root_partition_and_restores_originals('balanced-aa')

    def check_balanced_configures_root_partition_and_restores_originals(self, condition):
        self.balanced_partition(condition)
        self.put(self.group / 'cpuset.cpus.exclusive', '')
        self.put(self.group / 'cgroup.subtree_control', '')
        for child in ('supervisor', 'controller', 'workers'):
            for field in ('cpuset.cpus', 'cpuset.mems'):
                self.put(self.group / child / field, '')
        self.put(self.group / 'workers/cpuset.cpus.exclusive', '')
        self.put(self.group / 'workers/cpuset.cpus.partition', 'member')
        with patch.object(Path, 'mkdir'), patch.object(r, 'delegate_procs'), patch.object(r, 'command', side_effect=['/' + self.state['unit'], 'one']):
            r.configure(self.state)
        self.assertEqual(r.read(self.group / 'workers/cpuset.cpus.partition'), 'root')
        self.assertFalse(r.restore())
        self.assertEqual(r.read(self.group / 'workers/cpuset.cpus.partition'), 'member')
        self.assertEqual(r.read(self.group / 'cpuset.cpus.exclusive'), '')
        receipt = json.loads(r.read(self.state_root / 'public/restoration.json'))
        self.assertEqual((receipt['condition'], receipt['partition_mode']), (condition, 'root'))
        self.assertFalse(r.restore())  # Repeated recovery keeps the original state.
        self.group.rename(self.cg / 'removed')
        with patch.object(r, 'snapshot', return_value=self.state['before']), patch('builtins.print'):
            self.assertFalse(r.verify())

    def test_balanced_descendants_inherit_only_when_cpuset_disabled_for_children(self):
        self.check_balanced_descendants_inherit_only_when_cpuset_disabled_for_children('balanced')

    def test_balanced_aa_descendants_inherit_only_when_cpuset_disabled_for_children(self):
        self.check_balanced_descendants_inherit_only_when_cpuset_disabled_for_children('balanced-aa')

    def check_balanced_descendants_inherit_only_when_cpuset_disabled_for_children(self, condition):
        self.balanced_partition(condition)
        session = self.cg / 'user.slice/session.scope'
        (session / 'cpuset.cpus.effective').unlink()
        self.put(self.cg / 'user.slice/cgroup.subtree_control', 'cpu memory')
        self.put(session / 'cgroup.subtree_control', '')
        (session / 'app').mkdir()
        r.verify_partition(self.state)
        self.put(self.cg / 'user.slice/cgroup.subtree_control', 'cpuset cpu memory')
        with self.assertRaisesRegex(ValueError, 'inheritance is unproved'):
            r.verify_partition(self.state)

    def test_balanced_start_binds_copy_commands_mode_and_short_lease(self):
        fresh = self.root / 'balanced'
        account = Mock(pw_gid=3000, pw_name='task')
        def launch(*args):
            r.atomic(fresh / 'public/authority.json', {'authored': True})
            return ''
        retained = self.state_root / 'public/authority.json'
        retained.write_text('historical isolated receipt')
        with patch.object(r, 'CONDITION', 'balanced'), patch.object(r, 'ROOT', fresh), patch.object(r, 'inspect', return_value={}), patch.object(r.pwd, 'getpwuid', return_value=account), patch.object(r.os, 'chown'), patch.object(r, 'command', side_effect=launch) as launch_command, patch('builtins.print'):
            r.start(3000, 'balanced owner authority')
        invocation = launch_command.call_args.args
        self.assertIn('RuntimeMaxSec=1800', invocation)
        self.assertEqual(invocation[-3:], ('--condition', 'balanced', 'serve'))
        self.assertIn('ExecStopPost=/usr/bin/python3 -I ' + str(fresh / 'helper.py') + ' --condition balanced restore', invocation)
        journal = json.loads(r.read(fresh / 'journal.json'))
        self.assertEqual(journal['schema'], r.BALANCED_SCHEMA)
        self.assertEqual((journal['condition'], journal['partition_mode']), ('balanced', 'root'))
        self.assertEqual(retained.read_text(), 'historical isolated receipt')

    def test_condition_selection_routes_every_cli_entry_point(self):
        for condition, root in [('isolated', r.ISOLATED_ROOT), ('balanced', r.BALANCED_ROOT),
                                ('balanced-aa', r.BALANCED_AA_ROOT)]:
            for action in ('start', 'serve', 'restore', 'run', 'stop', 'verify', 'retire-failed', 'inspect'):
                function = {'retire-failed': 'retire_failed'}.get(action, action)
                def invoked(*args, **kwargs):
                    self.assertEqual(r.ROOT, root)
                    self.assertEqual(r.CONDITION, condition)
                    return 0
                args = ['--uid', '3000', '--authority', 'explicit authority'] if action == 'start' else []
                with self.subTest(condition=condition, action=action), patch.object(r, 'ROOT'), patch.object(r, 'CONDITION'), patch.object(r, function, side_effect=invoked), patch.object(r.sys, 'argv', ['helper', '--condition', condition, action, *args]), patch('builtins.print'):
                    r.main()

    def test_balanced_journal_requires_schema_and_mode_identity(self):
        value, root_stat = self.trusted_state()
        with patch.object(Path, 'lstat', root_stat), patch.object(r, 'CONDITION', 'balanced'):
            with self.assertRaisesRegex(ValueError, 'schema or boot'):
                REAL_LOAD()
            value.update(schema=r.BALANCED_SCHEMA, condition='balanced', partition_mode='root')
            r.atomic(self.state_root / 'journal.json', value)
            self.assertEqual(REAL_LOAD()['condition'], 'balanced')
            for field, replacement in [('condition', 'isolated'), ('partition_mode', 'isolated')]:
                bad = dict(value, **{field: replacement})
                r.atomic(self.state_root / 'journal.json', bad)
                with self.assertRaisesRegex(ValueError, 'condition or partition'):
                    REAL_LOAD()
            r.atomic(self.state_root / 'journal.json', value)
        with patch.object(Path, 'lstat', root_stat), self.assertRaisesRegex(ValueError, 'schema or boot'):
            REAL_LOAD()

    def test_balanced_verification_rejects_historical_restoration_receipt(self):
        r.atomic(self.state_root / 'public/restoration.json', {'issues': [], 'before': {}, 'unit': self.state['unit']})
        with patch.object(r, 'CONDITION', 'balanced'), self.assertRaisesRegex(ValueError, 'condition or partition'):
            r.verify()

    def test_balanced_partial_failure_keeps_evidence_and_stops_owned_unit(self):
        account = Mock(pw_gid=3000, pw_name='task')
        fresh = self.root / 'balanced-failure'
        with patch.object(r, 'CONDITION', 'balanced'), patch.object(r, 'ROOT', fresh), patch.object(r, 'inspect', return_value={}), patch.object(r.pwd, 'getpwuid', return_value=account), patch.object(r.os, 'chown'), patch.object(r, 'command', side_effect=subprocess.TimeoutExpired('systemd-run', 30)), patch.object(r.subprocess, 'run', return_value=subprocess.CompletedProcess([], 0, '', '')) as stop, patch('builtins.print'):
            with self.assertRaises(subprocess.TimeoutExpired):
                r.start(3000, 'authorised balanced diagnostic')
        journal = json.loads(r.read(fresh / 'journal.json'))
        self.assertEqual(stop.call_args.args[0], ['/usr/bin/systemctl', 'stop', journal['unit']])
        self.assertTrue((fresh / 'public/start-failure.json').exists())
        self.assertFalse((fresh / 'public/authority.json').exists())
        self.assertEqual(journal['partition_mode'], 'root')

    def test_authority_receipt_keeps_historical_schema_and_distinguishes_balanced(self):
        self.state.update(authority='explicit authority', issuer='task', expires_epoch=2000)
        original_read = r.read
        def read(path):
            if str(path) == '/proc/self/cgroup':
                return '0::/' + self.state['unit'] + '/supervisor'
            return original_read(path)
        for condition, schema in [('isolated', 'measurement-stability-qualification/v1'),
                                  ('balanced', 'measurement-balanced-qualification/v1'),
                                  ('balanced-aa', 'measurement-balanced-aa-qualification/v1')]:
            with self.subTest(condition=condition), patch.object(r, 'CONDITION', condition), patch.object(r, 'read', side_effect=read), patch.object(r, 'configure'), patch.object(r, 'verify_partition'), patch.object(r.os, 'pipe', return_value=(123, 124)), patch.object(r.os, 'fork', return_value=42), patch.object(r.os, 'read', return_value=b'1'), patch.object(r.os, 'close'), patch.object(r.os, 'waitpid', return_value=(42, 0)), patch.object(r.time, 'time', return_value=1000):
                self.assertFalse(r.serve())
            receipt = json.loads(r.read(self.state_root / 'public/authority.json'))
            self.assertEqual(receipt['schema'], schema)
            self.assertEqual(receipt['cgroup'], str(self.group / 'workers'))
            self.assertEqual(receipt['worker_cpus'], list(range(8)))
            self.assertEqual(receipt['reserved_cpus'], sorted(r.RESERVED))
            self.assertEqual(receipt['controller_cpus'], sorted(r.HOUSE))
            self.assertEqual(receipt['authority'], 'explicit authority')
            self.assertEqual(receipt['issuer'], 'task')
            self.assertEqual((receipt['valid_from_epoch'], receipt['valid_until_epoch']), (1000, 2000))
            if condition != 'isolated':
                self.assertEqual((receipt['condition'], receipt['partition_mode']), (condition, 'root'))
            else:
                self.assertNotIn('condition', receipt)
                self.assertNotIn('partition_mode', receipt)

    def test_balanced_command_rejects_wrong_journal_before_socket_admission(self):
        with patch.object(r, 'CONDITION', 'balanced'), patch.object(r.os, 'geteuid', return_value=3000), patch.object(r, 'load', side_effect=ValueError('condition differs')), patch.object(r.socket, 'socket') as transport, self.assertRaisesRegex(ValueError, 'condition differs'):
            r.run(['/usr/bin/true'])
        transport.assert_not_called()

    def test_balanced_aa_start_binds_separate_runtime_commands_and_three_hour_lease(self):
        fresh = self.root / r.BALANCED_AA_ROOT.name
        account = Mock(pw_gid=3000, pw_name='task')
        historical = []
        for name in (r.ISOLATED_ROOT.name, r.BALANCED_ROOT.name):
            receipt = self.root / name / 'public/authority.json'
            self.put(receipt, 'retained ' + name)
            historical.append((receipt, receipt.read_bytes()))
        def launch(*args):
            r.atomic(fresh / 'public/authority.json', {'authored': True})
            return ''
        with patch.object(r, 'CONDITION', 'balanced-aa'), patch.object(r, 'ROOT', fresh), patch.object(r, 'inspect', return_value={}), patch.object(r.pwd, 'getpwuid', return_value=account), patch.object(r.os, 'chown'), patch.object(r, 'command', side_effect=launch) as launch_command, patch.object(r.time, 'time', return_value=1000), patch('builtins.print') as output:
            r.start(3000, 'balanced A/A owner authority')
            original = (fresh / 'journal.json').read_bytes()
            with self.assertRaises(FileExistsError):
                r.start(3000, 'balanced A/A owner authority')
            self.assertEqual((fresh / 'journal.json').read_bytes(), original)
        invocation = launch_command.call_args.args
        self.assertIn('RuntimeMaxSec=10800', invocation)
        self.assertEqual(invocation[-3:], ('--condition', 'balanced-aa', 'serve'))
        self.assertIn('ExecStopPost=/usr/bin/python3 -I ' + str(fresh / 'helper.py') + ' --condition balanced-aa restore', invocation)
        self.assertTrue(any('--condition balanced-aa run --' in call.args[0] for call in output.call_args_list))
        journal = json.loads(original)
        self.assertEqual(journal['schema'], 'measurement-balanced-aa-reservation/v1')
        self.assertEqual((journal['condition'], journal['partition_mode']), ('balanced-aa', 'root'))
        self.assertEqual(journal['expires_epoch'], 11800)
        for receipt, content in historical:
            self.assertEqual(receipt.read_bytes(), content)

    def test_balanced_aa_journal_and_restoration_reject_every_other_condition(self):
        value, root_stat = self.trusted_state()
        modes = [('isolated', r.SCHEMA, 'isolated'),
                 ('balanced', r.BALANCED_SCHEMA, 'root'),
                 ('balanced-aa', r.BALANCED_AA_SCHEMA, 'root')]
        for selected, selected_schema, _ in modes:
            for recorded, recorded_schema, partition in modes:
                with self.subTest(selected=selected, recorded=recorded), patch.object(Path, 'lstat', root_stat), patch.object(r, 'CONDITION', selected):
                    record = dict(value, schema=recorded_schema,
                                  condition=recorded, partition_mode=partition)
                    r.atomic(self.state_root / 'journal.json', record)
                    if selected == recorded:
                        self.assertEqual(REAL_LOAD()['condition'], selected)
                        r.validate_condition(record)
                    else:
                        with self.assertRaisesRegex(ValueError, 'schema or boot'):
                            REAL_LOAD()
                        # A forged matching schema cannot bypass condition identity.
                        record['schema'] = selected_schema
                        r.atomic(self.state_root / 'journal.json', record)
                        with self.assertRaisesRegex(ValueError, 'condition or partition'):
                            REAL_LOAD()
                        r.atomic(self.state_root / 'public/restoration.json', record)
                        with self.assertRaisesRegex(ValueError, 'condition or partition'):
                            r.verify()

    def test_balanced_aa_recovery_and_socket_refuse_mismatched_journal(self):
        with patch.object(r, 'CONDITION', 'balanced-aa'), patch.object(r.os, 'geteuid', return_value=3000), patch.object(r, 'load', side_effect=ValueError('condition differs')), patch.object(r.socket, 'socket') as transport, patch.object(r, 'command') as host_command:
            for action in (lambda: r.run(['/usr/bin/true']), r.serve,
                           r.restore, r.stop, r.retire_failed):
                with self.subTest(action=action), self.assertRaisesRegex(ValueError, 'condition differs'):
                    action()
        transport.assert_not_called()
        host_command.assert_not_called()

    def test_balanced_aa_partial_failure_keeps_its_evidence_and_stops_only_owned_unit(self):
        account = Mock(pw_gid=3000, pw_name='task')
        fresh = self.root / 'balanced-aa-failure'
        with patch.object(r, 'CONDITION', 'balanced-aa'), patch.object(r, 'ROOT', fresh), patch.object(r, 'inspect', return_value={}), patch.object(r.pwd, 'getpwuid', return_value=account), patch.object(r.os, 'chown'), patch.object(r, 'command', side_effect=subprocess.TimeoutExpired('systemd-run', 30)), patch.object(r.subprocess, 'run', return_value=subprocess.CompletedProcess([], 0, '', '')) as stop, patch('builtins.print'):
            with self.assertRaises(subprocess.TimeoutExpired):
                r.start(3000, 'authorised balanced A/A')
        journal = json.loads(r.read(fresh / 'journal.json'))
        self.assertEqual(stop.call_args.args[0], ['/usr/bin/systemctl', 'stop', journal['unit']])
        self.assertTrue((fresh / 'public/start-failure.json').exists())
        self.assertFalse((fresh / 'public/authority.json').exists())
        self.assertEqual((journal['condition'], journal['partition_mode']), ('balanced-aa', 'root'))


if __name__ == '__main__':
    unittest.main()
