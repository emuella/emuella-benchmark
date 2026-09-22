#!/usr/bin/python3 -I
"""Package without privilege; install the reviewed hash-bound package once with sudo."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import pwd
import stat
import subprocess
import sys
import types

FILES = ('measurement_launcher.py', 'measurement_reservation.py', 'install_measurement_launcher.py')
SUDOERS = Path('/etc/sudoers.d/emuella-measurement')


def sha(data):
    return hashlib.sha256(data).hexdigest()


def source_bytes(path):
    info = path.lstat()
    if not stat.S_ISREG(info.st_mode):
        raise ValueError('package sources must be regular files, without symlinks')
    return path.read_bytes()


def package(output):
    if os.geteuid() == 0:
        raise PermissionError('create the package as an ordinary user')
    source = Path(__file__).absolute().parent
    payload = {name: source_bytes(source / name) for name in FILES}
    manifest = {'version': 1, 'files': {name: sha(data) for name, data in payload.items()}}
    output.mkdir(mode=0o700)  # Exclusive; never replace an earlier reviewed package.
    for name, data in payload.items():
        (output / name).write_bytes(data)
        (output / name).chmod(0o644)
    raw = (json.dumps(manifest, sort_keys=True, indent=2) + '\n').encode()
    (output / 'manifest.json').write_bytes(raw)
    print(json.dumps({'package': str(output.absolute()), 'package_sha256': sha(raw)}, indent=2))


def sudoers(uid, launcher):
    if type(uid) is not int or uid <= 0:
        raise ValueError('ordinary numeric UID required')
    return ('# Fixed installed gateway; no interpreter, argument or path wildcards.\n'
            + '\n'.join(f'#{uid} ALL=(root) NOPASSWD: NOSETENV: {launcher} {action}'
                        for action in ('start', 'status', 'stop', 'verify')) + '\n')


def make_directory(path, trusted):
    if path.exists() or path.is_symlink():
        trusted(path, directory=True)
        return
    make_directory(path.parent, trusted)
    path.mkdir(mode=0o755)
    path.chmod(0o755)
    trusted(path, directory=True)


def write_new(path, data, mode):
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, mode)
    with os.fdopen(fd, 'wb') as stream:
        os.fchmod(stream.fileno(), mode)
        stream.write(data)
        stream.flush()
        os.fsync(stream.fileno())


def install(uid, authority, expected):
    if os.geteuid() != 0:
        raise PermissionError('installation requires one authenticated sudo invocation')
    if uid <= 0 or not authority.strip() or len(authority.encode()) > 2048 or any(ord(c) < 32 for c in authority):
        raise ValueError('ordinary UID and bounded standing authority required')
    account = pwd.getpwuid(uid)
    directory = Path(__file__).absolute().parent
    raw = source_bytes(directory / 'manifest.json')
    if sha(raw) != expected:
        raise ValueError('reviewed package manifest digest differs')
    manifest = json.loads(raw)
    if manifest.get('version') != 1 or set(manifest.get('files', {})) != set(FILES):
        raise ValueError('package file set differs')
    payload = {name: source_bytes(directory / name) for name in FILES}
    for name, data in payload.items():
        if sha(data) != manifest['files'][name]:
            raise ValueError('reviewed package source digest differs: ' + name)
    gateway = types.ModuleType('reviewed_gateway')
    gateway.__file__ = str(directory / 'measurement_launcher.py')
    exec(compile(payload['measurement_launcher.py'], gateway.__file__, 'exec'), gateway.__dict__)
    trusted = gateway.trusted
    # The system interpreter may be a distro-owned symlink. Resolve this one
    # known system dependency, then verify its target and all target ancestors.
    trusted(Path('/usr/bin/python3').resolve(strict=True))
    for command in ('/usr/bin/systemctl', '/usr/bin/systemd-run', '/usr/sbin/visudo'):
        trusted(Path(command).resolve(strict=True))
    for path in (gateway.INSTALL, gateway.STATE, SUDOERS):
        if path.exists() or path.is_symlink():
            raise FileExistsError('installation refuses existing destination: ' + str(path))
    os.environ.clear()
    os.environ.update(PATH='/usr/sbin:/usr/bin:/sbin:/bin', LANG='C.UTF-8', HOME='/root')
    os.chdir('/')
    os.umask(0o077)
    # Validate current policy before any installation, and the candidate before
    # publishing the sudoers file. A failed partial installation stays visible.
    subprocess.run(['/usr/sbin/visudo', '-c'], check=True, stdin=subprocess.DEVNULL)
    for parent in (gateway.INSTALL.parent, gateway.STATE.parent, SUDOERS.parent):
        make_directory(parent, trusted)
    gateway.INSTALL.mkdir(mode=0o755)
    gateway.INSTALL.chmod(0o755)
    gateway.STATE.mkdir(mode=0o755)
    gateway.STATE.chmod(0o755)
    (gateway.STATE / 'leases').mkdir(mode=0o755)
    (gateway.STATE / 'leases').chmod(0o755)
    for name, data in payload.items():
        write_new(gateway.INSTALL / name, data, 0o755 if name == 'measurement_launcher.py' else 0o644)
    write_new(gateway.INSTALL / 'manifest.json', raw, 0o644)
    policy = {'version': 1, 'uid': uid, 'gid': account.pw_gid, 'user': account.pw_name,
              'authority': authority, 'package_sha256': expected, 'scope': gateway.scope()}
    write_new(gateway.INSTALL / 'policy.json', (json.dumps(policy, indent=2) + '\n').encode(), 0o644)
    candidate = gateway.INSTALL / 'sudoers.candidate'
    write_new(candidate, sudoers(uid, gateway.INSTALL / 'measurement_launcher.py').encode(), 0o440)
    subprocess.run(['/usr/sbin/visudo', '-cf', str(candidate)], check=True, stdin=subprocess.DEVNULL)
    write_new(SUDOERS, candidate.read_bytes(), 0o440)
    try:
        subprocess.run(['/usr/sbin/visudo', '-c'], check=True, stdin=subprocess.DEVNULL)
    except BaseException:
        # Revoke only the exact file created by this invocation, preserving it
        # inside the trusted package for diagnosis. No earlier file was replaced.
        SUDOERS.rename(gateway.INSTALL / 'sudoers.rejected')
        raise
    print(json.dumps({'installed': str(gateway.INSTALL), 'uid': uid,
                      'package_sha256': expected, 'sudoers': str(SUDOERS)}, indent=2))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest='action', required=True)
    build = commands.add_parser('package')
    build.add_argument('--output', type=Path, required=True)
    setup = commands.add_parser('install')
    setup.add_argument('--uid', type=int, required=True)
    setup.add_argument('--authority', required=True)
    setup.add_argument('--package-sha256', required=True)
    args = parser.parse_args()
    if args.action == 'package':
        package(args.output)
    else:
        install(args.uid, args.authority, args.package_sha256)


if __name__ == '__main__':
    try:
        main()
    except (OSError, ValueError, KeyError, subprocess.SubprocessError) as error:
        print(str(error), file=sys.stderr)
        sys.exit(1)
