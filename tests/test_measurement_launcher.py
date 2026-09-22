"""Authored offline gateway/installer adversarial checks; no sudo or host writes."""
import contextlib
import copy
import hashlib
import importlib.util
import io
import json
import os
from pathlib import Path
import stat
import subprocess
import tempfile
import types
import unittest
import uuid
from unittest.mock import Mock, patch

SCRIPTS = Path(__file__).resolve().parents[1] / 'scripts'


def load(name):
    spec = importlib.util.spec_from_file_location(name, SCRIPTS / (name + '.py'))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


l = load('measurement_launcher')
i = load('install_measurement_launcher')
r = load('measurement_reservation')


class LauncherTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.install = self.root / 'install'
        self.state = self.root / 'state'
        self.install.mkdir()
        self.state.mkdir()
        (self.state / 'leases').mkdir()
        self.addCleanup(patch.stopall)
        patch.object(l, 'INSTALL', self.install).start()
        patch.object(l, 'STATE', self.state).start()
        patch.object(l, '__file__', str(self.install / 'measurement_launcher.py')).start()
        # Ownership is simulated; file type and permission checks stay real.
        real = Path.lstat
        def owned(path, *args, **kwargs):
            info = real(path, *args, **kwargs)
            values = list(info)
            values[4] = 0
            if path not in (self.root, *self.root.parents) and not path.is_relative_to(self.root):
                return info
            if path in self.root.parents:
                values[0] &= ~0o022
            return os.stat_result(values)
        patch.object(Path, 'lstat', owned).start()
        self.account = types.SimpleNamespace(pw_uid=3000, pw_gid=3000, pw_name='task')
        patch.object(l.pwd, 'getpwuid', return_value=self.account).start()

    def package(self):
        files = {name: (SCRIPTS / name).read_bytes() for name in l.PACKAGE_FILES}
        manifest = json.dumps({'version': 1, 'files': {name: l.digest(data) for name, data in files.items()}}).encode()
        for name, data in files.items():
            (self.install / name).write_bytes(data)
        (self.install / 'manifest.json').write_bytes(manifest)
        policy = {'version': 1, 'uid': 3000, 'gid': 3000, 'user': 'task',
                  'authority': 'reviewed standing decision', 'scope': l.scope(),
                  'package_sha256': l.digest(manifest)}
        (self.install / 'policy.json').write_text(json.dumps(policy))
        return policy, manifest

    def journal(self, boot='current'):
        identity = str(uuid.uuid4())
        root = self.state / 'leases' / identity
        root.mkdir()
        (root / 'public').mkdir()
        state = {'id': identity, 'boot': boot, 'installation': {'package': 'reviewed'},
                 'cleanup_executed': True, 'unit': 'owned.service', 'expires_epoch': 1}
        (root / 'journal.json').write_text(json.dumps(state))
        (self.state / 'current.json').write_text(json.dumps({'lease_id': identity, 'installation': state['installation']}))
        module = types.SimpleNamespace(load=Mock(return_value=state), read=Mock(return_value='current'),
                                       verify=Mock(), atomic=r.atomic)
        return module, state, root

    def test_installed_identity_and_fixed_scope(self):
        policy, _ = self.package()
        actual, module, binding = l.installation()
        self.assertEqual(actual, policy)
        self.assertEqual(module.LEASE, 10800)
        self.assertEqual(binding['standing_authority'], policy['authority'])
        self.assertEqual(l.scope()['reserved_cpus'], '0-7,16-23')
        self.assertEqual(l.scope()['controller_cpus'], '8-15,24-31')
        self.assertEqual(l.scope()['worker_cpus'], '0-7')
        (self.install / 'measurement_reservation.py').write_text('raise AssertionError("must not execute")')
        with self.assertRaisesRegex(ValueError, 'identity differs'):
            l.installation()

    def test_source_location_policy_and_user_replacement_rejected(self):
        self.package()
        with patch.object(l, '__file__', str(self.root / 'writable.py')):
            with self.assertRaisesRegex(ValueError, 'fixed installation'):
                l.installation()
        self.account.pw_gid = 4000
        with self.assertRaisesRegex(ValueError, 'designated user'):
            l.installation()
        self.account.pw_gid = 3000
        policy = json.loads((self.install / 'policy.json').read_text())
        policy['scope']['lease_seconds'] = 999999
        (self.install / 'policy.json').write_text(json.dumps(policy))
        with self.assertRaisesRegex(ValueError, 'resource scope'):
            l.installation()

    def test_symlink_writable_file_and_ancestor_rejected(self):
        target = self.install / 'file'
        target.write_text('safe')
        symlink = self.install / 'link'
        symlink.symlink_to(target)
        with self.assertRaisesRegex(ValueError, 'unsafe'):
            l.trusted(symlink)
        target.chmod(0o666)
        with self.assertRaisesRegex(ValueError, 'unsafe'):
            l.trusted(target)
        target.chmod(0o644)
        self.install.chmod(0o777)
        with self.assertRaisesRegex(ValueError, 'unsafe'):
            l.trusted(target)
        with self.assertRaisesRegex(ValueError, 'canonical'):
            l.trusted(self.install / '..' / 'file')

    def test_exact_cli_rejects_privileged_options_before_loading(self):
        for args in ([], ['start', '--uid', '0'], ['start', '/tmp/code'], ['serve'], ['run'],
                     ['stop', '--unit', 'other.service'], ['start', '--duration', '999999']):
            with patch.object(l.sys, 'argv', ['launcher', *args]), patch.object(l, 'installation') as install:
                with self.assertRaises(ValueError):
                    l.main()
                install.assert_not_called()

    def test_caller_environment_never_reaches_dispatch(self):
        self.package()
        def dispatch(*args):
            self.assertEqual(dict(os.environ), {'PATH': '/usr/sbin:/usr/bin:/sbin:/bin',
                                               'LANG': 'C.UTF-8', 'HOME': '/root'})
        with patch.object(l.sys, 'argv', ['launcher', 'status']), patch.object(l.os, 'geteuid', return_value=0), patch.object(l.os, 'chdir'), patch.object(l.os, 'umask'), patch.dict(os.environ, {'SUDO_UID': '3000', 'PYTHONPATH': '/evil', 'SYSTEMD_BUS_ADDRESS': 'evil', 'LD_PRELOAD': '/evil'}, clear=True), patch.object(l, 'dispatch', side_effect=dispatch):
            l.main()
        with patch.object(l.sys, 'argv', ['launcher', 'status']), patch.object(l.os, 'geteuid', return_value=0), patch.dict(os.environ, {'SUDO_UID': '4000'}, clear=True):
            with self.assertRaisesRegex(PermissionError, 'designated'):
                l.main()

    def test_lock_rejects_concurrent_caller_and_symlink(self):
        with l.lock():
            with self.assertRaises(BlockingIOError):
                l.lock()
        (self.state / 'launcher.lock').unlink()
        (self.state / 'launcher.lock').symlink_to(self.install / 'victim')
        with self.assertRaises(OSError):
            l.lock()
        self.assertFalse((self.install / 'victim').exists())

    def test_active_or_unresolved_previous_lease_prevents_start(self):
        module, state, _ = self.journal()
        state['cleanup_executed'] = False
        module.start = Mock()
        with self.assertRaisesRegex(ValueError, 'active or unresolved'):
            l.dispatch('start', module, {'uid': 3000}, {}, 'locator')
        module.start.assert_not_called()
        state['cleanup_executed'] = True
        module.verify.side_effect = lambda **kwargs: (print('{"restored": false}'), 1)[1]
        with self.assertRaisesRegex(ValueError, 'restoration unresolved'):
            l.dispatch('start', module, {'uid': 3000}, {}, 'locator')
        module.start.assert_not_called()

    def test_stop_calls_only_bound_helper_and_verifies(self):
        module, _, _ = self.journal()
        module.stop = Mock(return_value=0)
        module.verify.side_effect = lambda **kwargs: (print('{"restored": true}'), 0)[1]
        with contextlib.redirect_stdout(io.StringIO()):
            l.dispatch('stop', module, {}, {})
        module.stop.assert_called_once_with()
        module.verify.assert_called_once_with(wait=20)

    def test_fresh_uuid_never_replays_existing_lease_directory(self):
        identity = uuid.uuid4()
        (self.state / 'leases' / str(identity)).mkdir()
        module = types.SimpleNamespace(CG=self.root / 'fake-cgroup', atomic=Mock(), start=Mock())
        with patch.object(l.uuid, 'uuid4', return_value=identity), self.assertRaisesRegex(FileExistsError, 'never replay'):
            l.dispatch('start', module, {'uid': 3000}, {}, 'locator')
        module.atomic.assert_not_called()
        module.start.assert_not_called()

    def test_persistent_journal_syncs_file_and_parent_before_return(self):
        kinds = []
        real = os.fsync
        def sync(fd):
            kinds.append(stat.S_IFMT(os.fstat(fd).st_mode))
            real(fd)
        with patch.object(r.os, 'fsync', side_effect=sync):
            r.atomic(self.state / 'durable.json', {'intent': True})
        self.assertEqual(kinds, [stat.S_IFREG, stat.S_IFDIR])

    def test_partial_start_records_intent_and_blocks_retry(self):
        module = types.SimpleNamespace(CG=self.root / 'fake-cgroup', atomic=r.atomic,
                                       start=Mock(side_effect=ValueError('authored setup failure')))
        with self.assertRaisesRegex(ValueError, 'setup failure'):
            l.dispatch('start', module, {'uid': 3000}, {'hash': 'one'}, 'locator')
        intent = json.loads((self.state / 'current.json').read_text())
        self.assertEqual(intent['installation'], {'hash': 'one'})
        self.assertEqual(module.ROOT.name, intent['lease_id'])
        with self.assertRaises(FileNotFoundError):
            l.dispatch('start', module, {'uid': 3000}, {'hash': 'one'}, 'locator')
        self.assertEqual(module.start.call_count, 1)

    def test_old_boot_admits_only_bound_successful_terminal_receipt(self):
        module, state, root = self.journal(boot='old')
        with self.assertRaises(FileNotFoundError):
            l.current(module)
        receipt = {'restored': True, 'lease_id': state['id'], 'boot': 'old',
                   'journal_sha256': l.digest((root / 'journal.json').read_bytes())}
        (root / 'public/launcher-verification.json').write_text(json.dumps(receipt))
        self.assertTrue(l.current(module)['_previous_boot_verified'])
        module.load.assert_not_called()
        with contextlib.redirect_stdout(io.StringIO()):
            l.verify(module)
        module.verify.assert_not_called()
        (root / 'journal.json').write_text(json.dumps(dict(state, cleanup_executed=False)))
        with self.assertRaisesRegex(ValueError, 'terminal verification'):
            l.current(module)

    def test_lease_path_replay_and_identity_mismatch_rejected(self):
        module, state, _ = self.journal()
        state['id'] = str(uuid.uuid4())
        with self.assertRaisesRegex(ValueError, 'identity'):
            l.current(module)
        (self.state / 'current.json').write_text(json.dumps({'lease_id': '../other', 'installation': {}}))
        with self.assertRaises(ValueError):
            l.current(module)

    def test_sudoers_is_numeric_exact_and_has_no_interpreter_or_wildcards(self):
        content = i.sudoers(3000, '/usr/local/libexec/emuella-measurement/measurement_launcher.py')
        rules = content.splitlines()[1:]
        self.assertEqual(len(rules), 4)
        for line, action in zip(rules, l.ACTIONS):
            self.assertEqual(line, '#3000 ALL=(root) NOPASSWD: NOSETENV: /usr/local/libexec/emuella-measurement/measurement_launcher.py ' + action)
        self.assertNotIn('*', content)
        self.assertNotIn('/usr/bin/python', content)
        self.assertTrue((SCRIPTS / 'measurement_launcher.py').read_text().startswith('#!/usr/bin/python3 -I\n'))
        with self.assertRaises(ValueError):
            i.sudoers(0, '/anything')

    def test_installer_rejects_hash_mismatch_before_writes(self):
        self.package()
        with patch.object(i, '__file__', str(self.install / 'install_measurement_launcher.py')), patch.object(i.os, 'geteuid', return_value=0), patch.object(i, 'write_new') as write:
            with self.assertRaisesRegex(ValueError, 'manifest digest'):
                i.install(3000, 'reviewed', 'wrong')
            write.assert_not_called()
        policy, manifest = self.package()
        (self.install / 'measurement_launcher.py').write_text('malicious')
        with patch.object(i, '__file__', str(self.install / 'install_measurement_launcher.py')), patch.object(i.os, 'geteuid', return_value=0), patch.object(i, 'write_new') as write:
            with self.assertRaisesRegex(ValueError, 'source digest'):
                i.install(3000, 'reviewed', l.digest(manifest))
            write.assert_not_called()

    def test_exclusive_installer_file_and_directory_creation(self):
        path = self.install / 'new'
        i.write_new(path, b'reviewed', 0o644)
        with self.assertRaises(FileExistsError):
            i.write_new(path, b'changed', 0o644)
        self.assertEqual(path.read_bytes(), b'reviewed')
        nested = self.root / 'fresh' / 'nested'
        i.make_directory(nested, l.trusted)
        l.trusted(nested, directory=True)
        (self.root / 'evil').symlink_to(self.root / 'fresh', target_is_directory=True)
        with self.assertRaisesRegex(ValueError, 'unsafe'):
            i.make_directory(self.root / 'evil' / 'other', l.trusted)

    def test_bounded_authority_metadata_rejects_controls_oversize_and_timeout(self):
        for raw in (b'valid locator\n', b'$(arbitrary shell text)', b'../not-a-path-to-load'):
            with patch.object(l.os, 'read', side_effect=[raw, b'']), patch.object(l.select, 'select', return_value=([0], [], [])), patch.object(l.sys, 'stdin', Mock()):
                self.assertEqual(l.authority_input(), raw.decode().strip())
        for raw in (b'', b'a' * 2049, b'bad\x00locator', b'bad\nsecond line', b'\xff'):
            with patch.object(l.os, 'read', side_effect=[raw, b'']), patch.object(l.select, 'select', return_value=([0], [], [])), patch.object(l.sys, 'stdin', Mock()):
                with self.assertRaises(ValueError):
                    l.authority_input()
        with patch.object(l.select, 'select', return_value=([], [], [])), patch.object(l.sys, 'stdin', Mock()):
            with self.assertRaisesRegex(ValueError, 'timed out'):
                l.authority_input()

    def test_reusable_start_copies_bound_source_and_uses_fixed_three_hour_service(self):
        root = self.state / 'leases' / str(uuid.uuid4())
        invocations = []
        def command(*args):
            invocations.append(args)
            r.atomic(root / 'public/authority.json', {'authored': True})
            return ''
        binding = {'package_sha256': 'reviewed', 'policy_sha256': 'policy'}
        with patch.object(r, 'ROOT', root), patch.object(r, 'CONDITION', 'balanced-reusable'), patch.object(r, 'require_root'), patch.object(r, 'inspect', return_value={}), patch.object(r.pwd, 'getpwuid', return_value=self.account), patch.object(r.os, 'chown'), patch.object(r, 'command', side_effect=command), contextlib.redirect_stdout(io.StringIO()):
            r.start(3000, 'workload locator', installation=binding)
        journal = json.loads((root / 'journal.json').read_text())
        self.assertEqual(journal['id'], root.name)
        self.assertEqual(journal['installation'], binding)
        self.assertEqual(journal['schema'], 'measurement-balanced-reusable-reservation/v1')
        self.assertEqual(journal['helper_sha256'], l.digest((root / 'helper.py').read_bytes()))
        self.assertIn('RuntimeMaxSec=10800', invocations[0])
        self.assertEqual(invocations[0][-3:], ('--condition', 'balanced-reusable', 'serve'))
        self.assertIn('ExecStopPost=/usr/bin/python3 -I ' + str(root / 'helper.py') + ' --condition balanced-reusable restore', invocations[0])

    def test_installer_publishes_exact_reviewed_files_and_validates_sudoers(self):
        _, manifest = self.package()
        destination = self.root / 'installed'
        state = self.root / 'persistent'
        sudoers = self.root / 'etc' / 'sudoers.d' / 'delegated'
        def execute(code, namespace):
            exec(code, namespace)
            namespace['INSTALL'] = destination
            namespace['STATE'] = state
        checks = []
        def check(argv, **kwargs):
            checks.append(argv)
        with patch.object(i, '__file__', str(self.install / 'install_measurement_launcher.py')), patch.object(i.os, 'geteuid', return_value=0), patch.object(i.os, 'chdir'), patch.object(i.os, 'umask'), patch.dict(os.environ, {}, clear=True), patch.object(i, 'SUDOERS', sudoers), patch.object(i, 'exec', side_effect=execute, create=True), patch.object(i.subprocess, 'run', side_effect=check), contextlib.redirect_stdout(io.StringIO()):
            i.install(3000, 'reviewed', l.digest(manifest))
            with self.assertRaisesRegex(FileExistsError, 'existing destination'):
                i.install(3000, 'reviewed', l.digest(manifest))
        self.assertEqual(len(checks), 3)
        self.assertEqual(checks[1], ['/usr/sbin/visudo', '-cf', str(destination / 'sudoers.candidate')])
        self.assertEqual(sudoers.read_text(), i.sudoers(3000, destination / 'measurement_launcher.py'))
        self.assertEqual(stat.S_IMODE(sudoers.stat().st_mode), 0o440)
        self.assertEqual(json.loads((destination / 'policy.json').read_text())['scope'], l.scope())
        for name in l.PACKAGE_FILES:
            self.assertEqual((destination / name).read_bytes(), (self.install / name).read_bytes())
        self.assertTrue((state / 'leases').is_dir())

    def test_invalid_sudoers_never_remains_delegated(self):
        _, manifest = self.package()
        for failure in (1, 2):
            destination = self.root / ('rejected-install-' + str(failure))
            state = self.root / ('rejected-state-' + str(failure))
            rule = self.root / ('etc-' + str(failure)) / 'sudoers.d' / 'delegated'
            def execute(code, namespace):
                exec(code, namespace)
                namespace['INSTALL'] = destination
                namespace['STATE'] = state
            calls = []
            def check(argv, **kwargs):
                calls.append(argv)
                if len(calls) - 1 == failure:
                    raise subprocess.CalledProcessError(1, argv)
            with self.subTest(failure=failure), patch.object(i, '__file__', str(self.install / 'install_measurement_launcher.py')), patch.object(i.os, 'geteuid', return_value=0), patch.object(i.os, 'chdir'), patch.object(i.os, 'umask'), patch.dict(os.environ, {}, clear=True), patch.object(i, 'SUDOERS', rule), patch.object(i, 'exec', side_effect=execute, create=True), patch.object(i.subprocess, 'run', side_effect=check), self.assertRaises(subprocess.CalledProcessError):
                i.install(3000, 'reviewed', l.digest(manifest))
            self.assertFalse(rule.exists())
            self.assertTrue((destination / 'sudoers.candidate').exists())
            self.assertEqual((destination / 'sudoers.rejected').exists(), failure == 2)

    def test_status_does_not_confuse_cleanup_with_verified_restoration(self):
        module, state, root = self.journal()
        l.current(module)
        self.assertEqual(l.status(module, state)['state'], 'cleanup-recorded')
        self.assertFalse(l.status(module, state)['restoration_verified'])
        module.verify.side_effect = lambda **kwargs: (print('{"restored": true}'), 0)[1]
        with contextlib.redirect_stdout(io.StringIO()):
            l.verify(module)
        self.assertTrue(l.status(module, state)['restoration_verified'])

    def test_reusable_condition_cannot_select_caller_path(self):
        with patch.object(r, '__file__', str(self.root / 'helper.py')):
            with self.assertRaises(ValueError):
                r.select_condition('balanced-reusable')
        self.assertEqual(r.BALANCED_AA_ROOT, Path('/run/emuella-balanced-aa-measurement-reservation'))
        self.assertEqual(r.BALANCED_ROOT, Path('/run/emuella-balanced-measurement-reservation'))


if __name__ == '__main__':
    unittest.main()
