#!/usr/bin/env python3
"""One finite, explicitly authorised systemd/cgroup-v2 measurement reservation.

Run privileged entry points with /usr/bin/python3 -I. No project imports, shell
commands, sudoers changes, payload access, or codec launches are implicit.
"""
import argparse
import array
import fcntl
import hashlib
import json
import os
from pathlib import Path
import pwd
import select
import signal
import socket
import stat
import subprocess
import sys
import time
import uuid

ROOT = Path('/run/emuella-measurement-reservation')
ISOLATED_ROOT = ROOT
BALANCED_ROOT = Path('/run/emuella-balanced-measurement-reservation')
BALANCED_AA_ROOT = Path('/run/emuella-balanced-aa-measurement-reservation')
CONDITION = 'isolated'
BALANCED_LEASE = 1800  # Setup included; diagnostic call/time caps are runner-owned.
BALANCED_SCHEMA = 'measurement-balanced-reservation/v1'
BALANCED_AA_SCHEMA = 'measurement-balanced-aa-reservation/v1'
CG = Path('/sys/fs/cgroup')
SYS = Path('/sys/devices/system/cpu')
RESERVED = set(range(8)) | set(range(16, 24))
HOUSE = set(range(32)) - RESERVED
LEASE = 10800  # Includes setup; the separate study observation cap remains 7200 s.
POLICY = ('scaling_driver', 'scaling_governor', 'energy_performance_preference',
          'scaling_min_freq', 'scaling_max_freq')
SCHEMA = 'measurement-stability-reservation/v1'


def select_condition(condition):
    global CONDITION, ROOT
    root = {'isolated': ISOLATED_ROOT, 'balanced': BALANCED_ROOT,
            'balanced-aa': BALANCED_AA_ROOT}[condition]
    CONDITION = condition
    ROOT = root


def condition_args():
    return ['--condition', CONDITION] if CONDITION != 'isolated' else []


def reservation_schema():
    return {'isolated': SCHEMA, 'balanced': BALANCED_SCHEMA,
            'balanced-aa': BALANCED_AA_SCHEMA}[CONDITION]


def validate_condition(state):
    # Journals predating the optional mode have no condition fields.
    if CONDITION != 'isolated':
        if state.get('condition') != CONDITION or state.get('partition_mode') != 'root':
            raise ValueError('reservation condition or partition mode differs')
    elif state.get('condition', 'isolated') != 'isolated' or state.get('partition_mode', 'isolated') != 'isolated':
        raise ValueError('reservation condition or partition mode differs')


def read(path):
    return Path(path).read_text().strip()


def cpus(text):
    result = set()
    for item in text.split(','):
        if item:
            ends = [int(v) for v in item.split('-')]
            result.update(range(ends[0], ends[-1] + 1))
    return result


def mask(values):
    runs = []
    for value in sorted(values):
        if runs and value == runs[-1][-1] + 1:
            runs[-1].append(value)
        else:
            runs.append([value])
    return ','.join(str(run[0]) if len(run) == 1 else f'{run[0]}-{run[-1]}' for run in runs)


def command(*args, timeout=30):
    return subprocess.check_output(args, text=True, stderr=subprocess.PIPE,
                                   timeout=timeout).strip()


def atomic(path, value):
    path = Path(path)
    # A killed writer may leave its temporary behind. Never reuse that name,
    # so recovery can always publish a new journal without deleting old evidence.
    temporary = path.with_name(path.name + '.' + str(uuid.uuid4()) + '.new')
    fd = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o644)
    try:
        with os.fdopen(fd, 'w') as output:
            os.fchmod(output.fileno(), 0o644)  # Explicit contract, independent of sudo umask.
            json.dump(value, output, indent=2)
            output.write('\n')
            output.flush()
            os.fsync(output.fileno())
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def policy():
    return {'cpus': {str(c): {key: read(SYS / f'cpu{c}/cpufreq' / key)
                             for key in POLICY} for c in range(32)},
            'boost': read(SYS / 'cpufreq/boost'),
            'smt': read(SYS / 'smt/control')}


def snapshot():
    return {'policy': policy(), 'online': read(SYS / 'online'),
            'isolated': read(CG / 'cpuset.cpus.isolated'),
            'root_controllers': read(CG / 'cgroup.subtree_control')}


def inspect():
    if int(command('/usr/bin/systemctl', '--version').split()[1]) != 261:
        raise ValueError('this bounded helper supports systemd 261 only')
    if cpus(read(SYS / 'online')) != set(range(32)):
        raise ValueError('expected exactly CPUs 0-31 online')
    for c in range(16):
        if cpus(read(SYS / f'cpu{c}/topology/thread_siblings_list')) != {c, c + 16}:
            raise ValueError('SMT topology differs from the authorised allocation')
    physical = {(read(SYS / f'cpu{c}/topology/physical_package_id'),
                 read(SYS / f'cpu{c}/topology/core_id')) for c in range(16)}
    if len(physical) != 16 or read(CG / 'cpuset.mems.effective') != '0':
        raise ValueError('physical core or NUMA topology differs')
    if 'cpuset' not in read(CG / 'cgroup.controllers').split():
        raise ValueError('cgroup v2 cpuset controller unavailable')
    if read(CG / 'cpuset.cpus.isolated'):
        raise ValueError('an isolated allocation already exists; do not alter it')
    # Root-resident kernel threads are residual interference; ordinary tasks are
    # unsupported. Inspect flags only, never names, arguments or environments.
    for pid in read(CG / 'cgroup.procs').split():
        try:
            fields = read(Path('/proc') / pid / 'stat').rsplit(')', 1)[1].split()
        except FileNotFoundError:
            continue
        if not int(fields[6]) & 0x00200000:  # PF_KTHREAD, stat field 9
            raise ValueError('ordinary process resides in root cgroup')
    return snapshot()


def require_root():
    if os.geteuid() != 0:
        raise PermissionError('run this entry point with sudo /usr/bin/python3 -I')


def load():
    info = ROOT.lstat()
    if not stat.S_ISDIR(info.st_mode) or info.st_uid != 0 or info.st_mode & 0o022:
        raise ValueError('unsafe reservation state directory')
    for name in ('journal.json', 'helper.py'):
        info = (ROOT / name).lstat()
        if not stat.S_ISREG(info.st_mode) or info.st_uid != 0 or info.st_mode & 0o022:
            raise ValueError('unsafe root-owned recovery file')
    state = json.loads(read(ROOT / 'journal.json'))
    schema = reservation_schema()
    if state['schema'] != schema or state['boot'] != read('/proc/sys/kernel/random/boot_id'):
        raise ValueError('recovery journal belongs to another schema or boot')
    validate_condition(state)
    if hashlib.sha256((ROOT / 'helper.py').read_bytes()).hexdigest() != state['helper_sha256']:
        raise ValueError('recovery helper identity changed')
    if state['unit'] != 'emuella-measurement-reservation-' + state['id'] + '.service':
        raise ValueError('unexpected unit identity')
    uuid.UUID(state['id'])
    return state


def save(state):
    atomic(ROOT / 'journal.json', state)


def unit_group(state):
    return CG / state['unit']


def mutate(state, path, value):
    path = Path(path)
    path.relative_to(unit_group(state))
    original = read(path)
    state['changes'].append({'path': str(path), 'original': original, 'applied': value})
    save(state)  # Durable intent before the write, including partial failures.
    path.write_text(value + '\n')
    if read(path) != value:
        raise ValueError('cgroup write did not read back as intended: ' + path.name)


def delegate_procs(state, path):
    info = path.stat()
    state['ownership'].append({'path': str(path), 'uid': info.st_uid,
                               'gid': info.st_gid, 'mode': stat.S_IMODE(info.st_mode)})
    save(state)
    os.chown(path, state['uid'], state['gid'])
    os.chmod(path, 0o600)


def verify_partition(state):
    validate_condition(state)
    group = unit_group(state)
    worker = group / 'workers'
    partition = 'isolated' if CONDITION == 'isolated' else 'root'
    if (read(worker / 'cpuset.cpus.partition') != partition
            or cpus(read(worker / 'cpuset.cpus.effective')) != RESERVED
            or cpus(read(worker / 'cpuset.cpus.exclusive.effective')) != RESERVED
            or read(worker / 'cgroup.procs') or list(worker.glob('*/cgroup.procs'))):
        raise ValueError('worker exclusive partition is invalid or occupied')
    if cpus(read(group / 'controller/cpuset.cpus.effective')) != HOUSE:
        raise ValueError('controller effective placement differs')
    for child in CG.iterdir():
        if child.is_dir() and child != group:
            effective = child / 'cpuset.cpus.effective'
            if not effective.exists() or cpus(read(effective)) & RESERVED:
                raise ValueError('ordinary cgroup exclusion is not established')
    if CONDITION != 'isolated':
        if (read(group / 'cpuset.cpus.partition') != 'member'
                or read(group / 'cgroup.procs')
                or cpus(read(group / 'cpuset.cpus.effective')) != HOUSE
                or cpus(read(group / 'supervisor/cpuset.cpus.effective')) != HOUSE):
            raise ValueError('reservation ancestor or supervisor placement differs')
        if read(CG / 'cpuset.cpus.isolated') != state['before']['isolated']:
            raise ValueError('balanced reservation changed the isolated CPU set')
        # Also inspect descendants: admission must prove every ordinary cgroup's
        # effective allocation, including nested slices and delegated children.
        allocations = {}
        def traversal_failed(error):
            raise error
        for parent, children, _ in os.walk(CG, onerror=traversal_failed):
            for name in children:
                child = Path(parent) / name
                if child == worker:
                    continue
                effective = child / 'cpuset.cpus.effective'
                if effective.exists():
                    allocation = cpus(read(effective))
                else:
                    # A controller disabled for children has no child interface;
                    # those children inherit the previously checked parent set.
                    if ('cpuset' in read(child.parent / 'cgroup.subtree_control').split()
                            or child.parent not in allocations):
                        raise ValueError('ordinary descendant cpuset inheritance is unproved')
                    allocation = allocations[child.parent]
                if allocation & RESERVED:
                    raise ValueError('ordinary descendant cgroup exclusion is not established')
                allocations[child] = allocation
    if policy() != state['before']['policy']:
        raise ValueError('frequency/boost/SMT policy changed')


def configure(state):
    group = unit_group(state)
    actual = command('/usr/bin/systemctl', 'show', state['unit'], '-p', 'ControlGroup', '--value')
    if actual != '/' + state['unit'] or read(group / 'cgroup.procs'):
        raise ValueError('expected empty top-level delegated service')
    state['invocation'] = command('/usr/bin/systemctl', 'show', state['unit'], '-p', 'InvocationID', '--value')
    save(state)
    # systemd 261 has no exclusive-mask property and does not write this field.
    # This single documented delegation-boundary exception is admin-owned here;
    # all other raw settings are strictly below the delegated unit.
    mutate(state, group / 'cpuset.cpus.exclusive', mask(RESERVED))
    original = read(group / 'cgroup.subtree_control')
    state['subtree_original'] = original
    save(state)
    (group / 'cgroup.subtree_control').write_text('+cpuset +cpu +memory +pids\n')
    for name, allocation in (('supervisor', HOUSE), ('controller', HOUSE), ('workers', RESERVED)):
        child = group / name
        if name != 'supervisor':
            child.mkdir()
        mutate(state, child / 'cpuset.cpus', mask(allocation))
        mutate(state, child / 'cpuset.mems', '0')
    mutate(state, group / 'workers/cpuset.cpus.exclusive', mask(RESERVED))
    mutate(state, group / 'workers/cpuset.cpus.partition',
           'isolated' if CONDITION == 'isolated' else 'root')
    for path in (group / 'cgroup.procs', group / 'controller/cgroup.procs', group / 'workers/cgroup.procs'):
        delegate_procs(state, path)
    verify_partition(state)


def drop_user(state):
    account = pwd.getpwuid(state['uid'])
    os.initgroups(account.pw_name, state['gid'])
    os.setresgid(state['gid'], state['gid'], state['gid'])
    os.setresuid(state['uid'], state['uid'], state['uid'])
    os.environ.clear()
    os.environ.update(PATH='/usr/bin:/bin', HOME=account.pw_dir, USER=account.pw_name,
                      LOGNAME=account.pw_name, LANG='C.UTF-8')


def admission_probe(state):
    pid = os.fork()
    if pid == 0:
        try:
            (unit_group(state) / 'workers/cgroup.procs').write_text(str(os.getpid()))
            os.sched_setaffinity(0, {0})
            if os.sched_getaffinity(0) != {0}:
                raise ValueError('probe affinity differs')
            (unit_group(state) / 'controller/cgroup.procs').write_text(str(os.getpid()))
            os.sched_setaffinity(0, HOUSE)
            os._exit(0)
        except BaseException:
            os._exit(1)
    if os.waitpid(pid, 0)[1] != 0:
        raise ValueError('unprivileged round-trip worker admission failed')


def execute_connection(connection):
    """One unprivileged command, with caller stdout/stderr passed as descriptors."""
    descriptors = array.array('i')
    data, ancillary, flags, _ = connection.recvmsg(65536, socket.CMSG_SPACE(8))
    try:
        for level, kind, value in ancillary:
            if level == socket.SOL_SOCKET and kind == socket.SCM_RIGHTS:
                descriptors.frombytes(value[:len(value) - len(value) % descriptors.itemsize])
        if flags & (socket.MSG_TRUNC | socket.MSG_CTRUNC) or len(descriptors) != 2:
            raise ValueError('expected two output descriptors and bounded command')
        request = json.loads(data)
        if set(request) != {'argv', 'cwd'} or not isinstance(request['argv'], list) or not request['argv']:
            raise ValueError('invalid command request')
        if not all(isinstance(arg, str) and '\0' not in arg for arg in request['argv']):
            raise ValueError('invalid command arguments')
        if not Path(request['argv'][0]).is_absolute() or not Path(request['cwd']).is_absolute():
            raise ValueError('absolute executable and working directory required')
        with subprocess.Popen(request['argv'], cwd=request['cwd'], stdin=subprocess.DEVNULL,
                              stdout=descriptors[0], stderr=descriptors[1], start_new_session=True) as process:
            while process.poll() is None:
                readable, _, _ = select.select([connection], [], [], 0.5)
                if readable:
                    # The request is complete. Further data or EOF means abort.
                    os.killpg(process.pid, signal.SIGTERM)
                    try:
                        process.wait(timeout=140)
                    except subprocess.TimeoutExpired:
                        os.killpg(process.pid, signal.SIGKILL)
                        process.wait(timeout=10)
                    raise ValueError('command client disconnected or sent unexpected data')
            connection.send(json.dumps({'returncode': process.returncode}).encode())
            return process.returncode
    finally:
        for fd in descriptors:
            os.close(fd)


def controller(state, ready):
    (unit_group(state) / 'controller/cgroup.procs').write_text(str(os.getpid()))
    drop_user(state)
    os.sched_setaffinity(0, HOUSE)
    admission_probe(state)
    endpoint = ROOT / 'control/control.sock'
    with socket.socket(socket.AF_UNIX, socket.SOCK_SEQPACKET) as listener:
        listener.bind(str(endpoint))
        endpoint.chmod(0o600)
        listener.listen(1)
        os.write(ready, b'1')
        os.close(ready)
        # Exactly one command. RuntimeMaxSec bounds an abandoned listener too.
        connection, _ = listener.accept()
        with connection:
            import struct
            peer = struct.unpack('3i', connection.getsockopt(socket.SOL_SOCKET, socket.SO_PEERCRED, 12))
            if peer[1] != state['uid']:
                raise PermissionError('controller peer uid differs')
            return execute_connection(connection)


def serve():
    require_root()
    state = load()
    if read('/proc/self/cgroup') != '0::/' + state['unit'] + '/supervisor':
        raise ValueError('serve must run inside the owned systemd supervisor')
    with lifecycle_lock():
        configure(state)
    incoming, outgoing = os.pipe()
    pid = os.fork()
    if pid == 0:
        os.close(incoming)
        try:
            code = controller(state, outgoing)
        except BaseException as error:
            print('controller failed: ' + str(error), file=sys.stderr, flush=True)
            code = 1
        os._exit(0 if code == 0 else 1)
    os.close(outgoing)
    if os.read(incoming, 1) != b'1':
        raise ValueError('controller admission probe failed')
    os.close(incoming)
    verify_partition(state)
    now = time.time()
    receipt = {'schema': 'measurement-stability-qualification/v1',
               'authority': state['authority'], 'issuer': state['issuer'], 'approved': True,
               'valid_from_epoch': now, 'valid_until_epoch': state['expires_epoch'],
               'cgroup': str(unit_group(state) / 'workers'), 'worker_cpus': list(range(8)),
               'reserved_cpus': sorted(RESERVED), 'controller_cpus': sorted(HOUSE),
               'residual_interference': 'Shared package and NUMA memory; hard IRQ and root kernel activity remain. No frequency, boost, SMT or IRQ changes.'}
    if CONDITION != 'isolated':
        receipt.update(schema='measurement-' + CONDITION + '-qualification/v1',
                       condition=CONDITION, partition_mode='root')
    atomic(ROOT / 'public/authority.json', receipt)
    state['admission_probe'] = 'passed; no codec or real input invoked'
    state['ready'] = True
    save(state)
    return os.waitpid(pid, 0)[1] != 0


def _restore():
    require_root()
    state = load()
    issues = []
    group = unit_group(state)
    if group.exists():
        current = command('/usr/bin/systemctl', 'show', state['unit'], '-p', 'InvocationID', '--value')
        if state.get('invocation') and current != state['invocation']:
            raise ValueError('unit invocation changed; refusing restoration')
        for name in ('workers', 'controller'):
            if (group / name / 'cgroup.procs').exists() and read(group / name / 'cgroup.procs'):
                raise ValueError('task processes remain; stop the owned unit before recovery')
        for item in reversed(state['ownership']):
            path = Path(item['path'])
            if not path.exists():
                continue
            info = path.stat()
            original = (item['uid'], item['gid'], item['mode'])
            actual = (info.st_uid, info.st_gid, stat.S_IMODE(info.st_mode))
            if actual == original:
                continue
            if actual != (state['uid'], state['gid'], 0o600):
                issues.append('ownership intervened: ' + str(path))
                continue
            os.chown(path, item['uid'], item['gid'])
            os.chmod(path, item['mode'])
        for item in reversed(state['changes']):
            path = Path(item['path'])
            if not path.exists():
                continue
            actual = read(path)
            if actual == item['original']:
                continue
            if actual != item['applied']:
                issues.append('value intervened: ' + str(path))
                continue
            try:
                path.write_text(item['original'] + '\n')
                if read(path) != item['original']:
                    issues.append('restoration read-back differs: ' + str(path))
            except OSError as error:
                issues.append('restoration write failed: ' + path.name + ': ' + str(error))
    if policy() != state['before']['policy']:
        issues.append('frequency/boost/SMT policy differs; not overwritten')
    state['restoration_issues'] = issues
    state['cleanup_executed'] = True
    save(state)
    # Unit/controller files disappear under systemd after ExecStopPost exits.
    receipt = {'issues': issues, 'cleanup_executed': True,
           'final_verification': 'run verify after unit cgroup removal',
           'before': state['before'], 'unit': state['unit']}
    if CONDITION != 'isolated':
        receipt.update(condition=CONDITION, partition_mode='root')
    atomic(ROOT / 'public/restoration.json', receipt)
    return bool(issues)


def lifecycle_lock():
    # The parent directory is root-owned and not user-writable.
    fd = os.open(ROOT / 'lifecycle.lock', os.O_RDWR | os.O_CREAT | os.O_NOFOLLOW, 0o600)
    stream = os.fdopen(fd, 'r+')
    fcntl.flock(stream, fcntl.LOCK_EX)
    return stream


def restore():
    require_root()
    load()
    with lifecycle_lock():
        return _restore()


def start(uid, authority):
    require_root()
    if uid == 0 or not authority.strip() or len(authority) > 2048:
        raise ValueError('non-root uid and explicit authority locator required')
    before = inspect()
    account = pwd.getpwuid(uid)
    ROOT.mkdir(mode=0o700)  # Exclusive; stage state privately before publication.
    ROOT.chmod(0o700)  # mkdir/open modes alone are filtered by the caller's umask.
    (ROOT / 'public').mkdir(mode=0o700)
    (ROOT / 'public').chmod(0o755)
    (ROOT / 'control').mkdir(mode=0o700)
    os.chown(ROOT / 'control', uid, account.pw_gid)
    (ROOT / 'control').chmod(0o700)
    source = Path(__file__).read_bytes()
    (ROOT / 'helper.py').write_bytes(source)
    (ROOT / 'helper.py').chmod(0o444)
    identity = str(uuid.uuid4())
    lease = BALANCED_LEASE if CONDITION == 'balanced' else LEASE
    state = {'schema': reservation_schema(), 'id': identity,
             'unit': 'emuella-measurement-reservation-' + identity + '.service',
             'uid': uid, 'gid': account.pw_gid, 'issuer': account.pw_name,
             'authority': authority, 'boot': read('/proc/sys/kernel/random/boot_id'),
             'helper_sha256': hashlib.sha256(source).hexdigest(), 'before': before,
             'expires_epoch': time.time() + lease, 'changes': [], 'ownership': []}
    if CONDITION != 'isolated':
        state.update(condition=CONDITION, partition_mode='root')
    save(state)
    ROOT.chmod(0o755)  # Controller can now traverse to its private socket directory.
    helper = str(ROOT / 'helper.py')
    args = ['/usr/bin/systemd-run', '--quiet', '--collect', '--unit=' + state['unit'],
            '--slice=-.slice', '-p', 'Type=exec', '-p', 'Delegate=cpuset cpu memory pids',
            '-p', 'DelegateSubgroup=supervisor', '-p', 'AllowedCPUs=0-31',
            '-p', 'CPUAffinity=8-15 24-31', '-p', 'RuntimeMaxSec=' + str(lease),
            '-p', 'TimeoutStopSec=150', '-p', 'KillMode=control-group',
            '-p', 'ExecStopPost=/usr/bin/python3 -I ' + helper +
            (' ' + ' '.join(condition_args()) if condition_args() else '') + ' restore',
            '/usr/bin/python3', '-I', helper, *condition_args(), 'serve']
    try:
        command(*args)
        deadline = time.monotonic() + 30
        while time.monotonic() < deadline:
            if (ROOT / 'public/authority.json').exists():
                print('Reservation ready. Authority: ' + str(ROOT / 'public/authority.json'))
                print('Run exactly one ordinary-user command through this helper ' +
                      ' '.join([*condition_args(), 'run', '--', '/absolute/program', '...']))
                return
            if (ROOT / 'public/restoration.json').exists():
                raise ValueError('setup failed; inspect restoration receipt')
            time.sleep(0.2)
        raise TimeoutError('reservation setup did not become ready')
    except BaseException:
        # An ambiguous systemd-run timeout may still have started the unit.
        # ExecStopPost may already have completed and --collect unloaded the unit.
        # Retain cleanup diagnostics without masking the original setup error.
        cleanup = subprocess.run(['/usr/bin/systemctl', 'stop', state['unit']],
                                 timeout=180, check=False, capture_output=True, text=True)
        atomic(ROOT / 'public/start-failure.json',
               {'stop_returncode': cleanup.returncode, 'stop_stderr': cleanup.stderr,
                'restoration_receipt': str(ROOT / 'public/restoration.json')})
        print('Setup did not become ready; no measurement command was admitted. '
              'Use verify, then retire-failed after resolving any restoration issue.', file=sys.stderr)
        raise


def run(argv):
    if os.geteuid() == 0:
        raise PermissionError('run the measurement command as the ordinary task user')
    if CONDITION != 'isolated':
        load()  # Bind the new mode to its safe, hash-bound journal before admission.
    if argv and argv[0] == '--':
        argv = argv[1:]
    payload = json.dumps({'argv': argv, 'cwd': os.getcwd()}).encode()
    if len(payload) > 65536:
        raise ValueError('command exceeds bounded message size')
    with socket.socket(socket.AF_UNIX, socket.SOCK_SEQPACKET) as client:
        client.connect(str(ROOT / 'control/control.sock'))
        client.sendmsg([payload], [(socket.SOL_SOCKET, socket.SCM_RIGHTS,
                                  array.array('i', [sys.stdout.fileno(), sys.stderr.fileno()]))])
        response = client.recv(4096)
    if not response:
        raise ValueError('controller ended without completion; inspect restoration')
    status = json.loads(response)['returncode']
    restored = verify(wait=160)
    return status if status else restored


def stop():
    require_root()
    state = load()
    if unit_group(state).exists():
        current = command('/usr/bin/systemctl', 'show', state['unit'], '-p', 'InvocationID', '--value')
        if state.get('invocation') and current != state['invocation']:
            raise ValueError('unit invocation changed; refusing to stop')
        command('/usr/bin/systemctl', 'stop', state['unit'], timeout=180)
    elif not state.get('cleanup_executed'):
        restore()
    return verify(wait=20)


def verify(wait=0):
    if not os.access(ROOT, os.X_OK):
        raise PermissionError('runtime directory is not traversable; use the repaired helper retire-failed with sudo')
    deadline = time.monotonic() + wait
    while not (ROOT / 'public/restoration.json').exists() and time.monotonic() < deadline:
        time.sleep(0.2)
    result = json.loads(read(ROOT / 'public/restoration.json'))
    validate_condition(result)
    current = snapshot()
    while time.monotonic() < deadline and ((CG / result['unit']).exists()
            or current['root_controllers'] != result['before']['root_controllers']):
        time.sleep(0.2)
        current = snapshot()
    issues = list(result['issues'])
    if (CG / result['unit']).exists():
        issues.append('owned unit cgroup still exists')
    for key, original in result['before'].items():
        if current[key] != original:
            issues.append(key + ' differs from original; do not overwrite intervening changes')
    report = {'restored': not issues, 'issues': issues, 'observed': current}
    print(json.dumps(report, indent=2))
    return bool(issues)


def retire_failed():
    """Preserve a restored pre-readiness failure; never release or retry a study."""
    require_root()
    state = load()
    with lifecycle_lock():
        state = load()
        if state.get('ready') or (ROOT / 'public/authority.json').exists():
            raise ValueError('a ready reservation cannot be retired as a setup failure')
        active = command('/usr/bin/systemctl', 'show', state['unit'], '-p', 'ActiveState', '--value')
        if active not in ('inactive', 'failed') or unit_group(state).exists():
            raise ValueError('failed unit must be stopped and its cgroup removed first')
        if not state.get('cleanup_executed') or verify(wait=20):
            raise ValueError('restoration must be verified before preserving a failed attempt')
        archive = ROOT.with_name(ROOT.name + '.failed-' + state['id'])
        if archive.exists() or archive.is_symlink():
            raise FileExistsError('failed-attempt archive already exists')
        paths = [ROOT, ROOT / 'public', ROOT / 'journal.json', ROOT / 'helper.py',
                 ROOT / 'public/restoration.json']
        modes = {}
        for path in paths:
            info = path.lstat()
            is_dir = path in (ROOT, ROOT / 'public')
            if (info.st_uid != 0 or info.st_mode & 0o022
                    or not (stat.S_ISDIR(info.st_mode) if is_dir else stat.S_ISREG(info.st_mode))):
                raise ValueError('unsafe failed-attempt evidence path')
            modes[str(path.relative_to(ROOT))] = stat.S_IMODE(info.st_mode)
        atomic(ROOT / 'retirement.json', {'id': state['id'], 'original_modes': modes,
               'restoration_verified': True, 'ready': False, 'archive': str(archive),
               'automatic_restart': False})
        # Only this task's allowlisted metadata becomes readable. Retain all
        # contents and original modes; no recursive chmod, deletion or root control write.
        for path in paths:
            path.chmod(0o755 if path in (ROOT, ROOT / 'public') else
                       0o444 if path.name == 'helper.py' else 0o644)
        ROOT.rename(archive)
    print('Failed attempt retained at ' + str(archive))
    print('No new reservation or measurement was launched.')
    return 0


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--condition', choices=('isolated', 'balanced', 'balanced-aa'), default='isolated',
                        help='balanced and balanced-aa use separate finite load-balanced exclusive reservations')
    commands = parser.add_subparsers(dest='action', required=True)
    launch = commands.add_parser('start')
    launch.add_argument('--uid', type=int, required=True)
    launch.add_argument('--authority', required=True)
    commands.add_parser('inspect')
    for name in ('serve', 'restore', 'stop', 'verify', 'retire-failed'):
        commands.add_parser(name)
    launch = commands.add_parser('run')
    launch.add_argument('argv', nargs=argparse.REMAINDER)
    args = parser.parse_args()
    select_condition(args.condition)
    if args.action == 'inspect':
        print(json.dumps(inspect(), indent=2))
        return 0
    if args.action == 'retire-failed':
        return retire_failed()
    if args.action == 'verify':
        return verify(wait=20)
    if args.action == 'start':
        return start(args.uid, args.authority) or 0
    if args.action == 'run':
        return run(args.argv)
    # start creates one exclusive root; recovery is bound to its unit invocation.
    if args.action in ('serve', 'restore', 'stop'):
        require_root()
    return globals()[args.action]() or 0


if __name__ == '__main__':
    try:
        sys.exit(main())
    except (OSError, ValueError, subprocess.SubprocessError) as error:
        print(str(error), file=sys.stderr)
        sys.exit(1)
