#!/usr/bin/python3 -I
"""Installed, fixed-policy privileged gateway; never invoke from a checkout via sudoers."""
import fcntl
import hashlib
import io
from contextlib import redirect_stdout
import json
import os
from pathlib import Path
import pwd
import select
import stat
import subprocess
import sys
import types
import time
import uuid

INSTALL = Path('/usr/local/libexec/emuella-measurement')
STATE = Path('/var/lib/emuella-measurement')
ACTIONS = ('start', 'status', 'stop', 'verify')
PACKAGE_FILES = ('measurement_launcher.py', 'measurement_reservation.py', 'install_measurement_launcher.py')
VERSION = 1


def trusted(path, directory=False):
    """Reject symlinks, unsafe types and writable ancestors before privileged use."""
    path = Path(path)
    if not path.is_absolute() or '..' in path.parts:
        raise ValueError('absolute canonical trusted path required')
    for candidate in reversed((path, *path.parents)):
        info = candidate.lstat()
        is_dir = candidate != path or directory
        if (info.st_uid != 0 or info.st_mode & 0o022
                or not (stat.S_ISDIR(info.st_mode) if is_dir else stat.S_ISREG(info.st_mode))):
            raise ValueError('unsafe root-owned path: ' + str(candidate))
    return path


def digest(data):
    return hashlib.sha256(data).hexdigest()


def installation():
    if Path(__file__).absolute() != INSTALL / 'measurement_launcher.py':
        raise ValueError('launcher must execute from the fixed installation')
    trusted(Path('/usr/bin/python3').resolve(strict=True))
    manifest_bytes = trusted(INSTALL / 'manifest.json').read_bytes()
    manifest = json.loads(manifest_bytes)
    if manifest.get('version') != VERSION or set(manifest.get('files', {})) != set(PACKAGE_FILES):
        raise ValueError('installation manifest differs')
    sources = {}
    for name, expected in manifest['files'].items():
        sources[name] = trusted(INSTALL / name).read_bytes()
        if digest(sources[name]) != expected:
            raise ValueError('installed source identity differs: ' + name)
    policy_bytes = trusted(INSTALL / 'policy.json').read_bytes()
    policy = json.loads(policy_bytes)
    expected = {'version', 'uid', 'gid', 'user', 'authority', 'package_sha256', 'scope'}
    if set(policy) != expected or policy['version'] != VERSION:
        raise ValueError('installation policy differs')
    account = pwd.getpwuid(policy['uid'])
    if (type(policy['uid']) is not int or policy['uid'] <= 0
            or account.pw_uid != policy['uid'] or account.pw_gid != policy['gid']
            or account.pw_name != policy['user'] or policy['scope'] != scope()
            or policy['package_sha256'] != digest(manifest_bytes)):
        raise ValueError('designated user, resource scope or installation identity changed')
    module = types.ModuleType('installed_reservation')
    module.__file__ = str(INSTALL / 'measurement_reservation.py')
    exec(compile(sources['measurement_reservation.py'], module.__file__, 'exec'), module.__dict__)
    binding = {'version': VERSION, 'package_sha256': digest(manifest_bytes),
               'policy_sha256': digest(policy_bytes), 'standing_authority': policy['authority']}
    return policy, module, binding


def scope():
    return {'condition': 'balanced-reusable', 'partition_mode': 'root',
            'reserved_cpus': '0-7,16-23', 'worker_cpus': '0-7',
            'controller_cpus': '8-15,24-31', 'lease_seconds': 10800,
            'one_active_lease': True, 'ordinary_user_workloads': True}


def lock():
    trusted(STATE, directory=True)
    path = STATE / 'launcher.lock'
    fd = os.open(path, os.O_RDWR | os.O_CREAT | os.O_NOFOLLOW, 0o600)
    stream = os.fdopen(fd, 'r+')
    try:
        trusted(path)
        fcntl.flock(stream, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BaseException:
        stream.close()
        raise
    return stream


def current(module):
    path = STATE / 'current.json'
    if not path.exists() and not path.is_symlink():
        return None
    record = json.loads(trusted(path).read_text())
    if set(record) != {'lease_id', 'installation'}:
        raise ValueError('current lease record differs')
    identity = record['lease_id']
    if str(uuid.UUID(identity)) != identity:
        raise ValueError('noncanonical lease identity')
    module.ROOT = STATE / 'leases' / identity
    module.CONDITION = 'balanced-reusable'
    trusted(module.ROOT, directory=True)
    journal_path = trusted(module.ROOT / 'journal.json')
    journal_bytes = journal_path.read_bytes()
    previous = json.loads(journal_bytes)
    if previous.get('boot') != module.read('/proc/sys/kernel/random/boot_id'):
        receipt = json.loads(trusted(module.ROOT / 'public/launcher-verification.json').read_text())
        if (receipt.get('restored') is not True or receipt.get('lease_id') != identity
                or receipt.get('journal_sha256') != digest(journal_bytes)
                or receipt.get('boot') != previous.get('boot')):
            raise ValueError('previous boot lacks a bound successful terminal verification')
        state = previous
        state['_previous_boot_verified'] = True
    else:
        state = module.load()
    if state.get('id') != identity or state.get('installation') != record['installation']:
        raise ValueError('lease identity or installation binding differs')
    return state


def status(module, state):
    if state is None:
        return {'schema': 'measurement-launcher-status/v1', 'state': 'unused'}
    public = module.ROOT / 'public'
    terminal = public / 'launcher-verification.json'
    verified = False
    if terminal.exists() or terminal.is_symlink():
        receipt = json.loads(trusted(terminal).read_text())
        verified = (receipt.get('restored') is True and receipt.get('lease_id') == state['id']
                    and receipt.get('journal_sha256') == digest(trusted(module.ROOT / 'journal.json').read_bytes()))
    return {'schema': 'measurement-launcher-status/v1', 'lease_id': state['id'],
            'state': 'cleanup-recorded' if state.get('cleanup_executed') else 'active-or-unresolved',
            'ready': state.get('ready', False), 'restoration_verified': verified, 'unit': state['unit'],
            'expires_epoch': state['expires_epoch'], 'installation': state['installation'],
            'helper': str(module.ROOT / 'helper.py'),
            'authority_receipt': str(public / 'authority.json'),
            'restoration_receipt': str(public / 'restoration.json'),
            'verification_receipt': str(public / 'launcher-verification.json')}


def verify(module):
    state = current(module)
    if state.get('_previous_boot_verified'):
        print(json.dumps({'restored': True, 'previous_boot_verified': True, 'lease_id': state['id']}))
        return
    # The helper performs full live snapshot and owned-cgroup verification.
    # It prints its report; retain a separate root-owned durable gate result too.
    output = io.StringIO()
    with redirect_stdout(output):
        result = module.verify(wait=20)
    print(output.getvalue(), end='')
    journal = trusted(module.ROOT / 'journal.json').read_bytes()
    module.atomic(module.ROOT / 'public/launcher-verification.json',
                  {'restored': result == 0, 'lease_id': state['id'], 'boot': state['boot'],
                   'journal_sha256': digest(journal), 'report': json.loads(output.getvalue())})
    if result:
        raise ValueError('restoration unresolved; new admission is blocked')


def authority_input():
    raw = b''
    deadline = time.monotonic() + 10
    while len(raw) <= 2048:
        remaining = deadline - time.monotonic()
        if remaining <= 0 or not select.select([sys.stdin], [], [], remaining)[0]:
            raise ValueError('authority input timed out; supply a locator followed by EOF')
        chunk = os.read(sys.stdin.fileno(), 2049 - len(raw))
        if not chunk:
            break
        raw += chunk
    authority = raw.decode('utf-8').strip()
    if len(raw) > 2048 or not authority or any(ord(c) < 32 for c in authority):
        raise ValueError('one bounded UTF-8 authority locator required on stdin')
    return authority


def dispatch(action, module, policy, binding, authority=None):
    with lock():
        state = current(module)
        if action == 'status':
            print(json.dumps(status(module, state), indent=2))
            return
        if action in ('stop', 'verify'):
            if state is None:
                raise ValueError('no lease has been created')
            if action == 'stop' and not state.get('_previous_boot_verified') and module.stop():
                raise ValueError('restoration unresolved after stop')
            verify(module)
            return
        if state is not None:
            if not state.get('cleanup_executed'):
                raise ValueError('previous lease active or unresolved; stop and verify it first')
            verify(module)
        # Never overlap an older one-shot helper or a retained unresolved unit.
        if any(module.CG.glob('emuella-measurement-reservation-*.service')):
            raise ValueError('another measurement reservation cgroup exists')
        trusted(STATE / 'leases', directory=True)
        identity = str(uuid.uuid4())
        module.ROOT = STATE / 'leases' / identity
        module.CONDITION = 'balanced-reusable'
        if module.ROOT.exists() or module.ROOT.is_symlink():
            raise FileExistsError('fresh lease identity already exists; never replay it')
        # Write intent first: a crash or partial setup blocks, never silently retries.
        module.atomic(STATE / 'current.json', {'lease_id': identity, 'installation': binding})
        module.start(policy['uid'], authority, installation=binding)
        print(json.dumps(status(module, module.load()), indent=2))


def main():
    if len(sys.argv) != 2 or sys.argv[1] not in ACTIONS:
        raise ValueError('exactly one action required: start, status, stop or verify')
    if os.geteuid() != 0:
        raise PermissionError('use the installed launcher through sudo')
    policy, module, binding = installation()
    if os.environ.get('SUDO_UID') != str(policy['uid']):
        raise PermissionError('only the designated sudo caller is admitted')
    # Capture only sudo's numeric caller identity; do not forward caller settings.
    os.environ.clear()
    os.environ.update(PATH='/usr/sbin:/usr/bin:/sbin:/bin', LANG='C.UTF-8', HOME='/root')
    os.chdir('/')
    os.umask(0o077)
    authority = authority_input() if sys.argv[1] == 'start' else None
    dispatch(sys.argv[1], module, policy, binding, authority)
    return 0


if __name__ == '__main__':
    try:
        sys.exit(main())
    except (OSError, ValueError, KeyError, TypeError, subprocess.SubprocessError) as error:
        print(str(error), file=sys.stderr)
        sys.exit(1)
