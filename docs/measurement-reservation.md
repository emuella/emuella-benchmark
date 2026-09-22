# Temporary measurement reservation

`scripts/measurement_reservation.py` is an opt-in administrative helper for the
existing [measurement stability protocol](measurement-stability.md). It does not
build a codec, read imagery, launch measurements, alter the comparator or select
a candidate. It needs explicit resource-owner authority for the host scheduling
change and one local `sudo` authentication. This one-shot helper changes no sudoers or
polkit policy. The optional installed reusable launcher below has a separate,
explicitly authorised installation boundary.

The default `isolated` mode retains the existing stability protocol, runtime
directory, schemas and three-hour lease. The explicit `balanced` mode described
below supplies a separate short diagnostic reservation. `balanced-aa` supplies a
three-hour reservation for the identical-production-binary A/A study. Each uses
its own runtime directory and receipts, preserving earlier reservations.

This bounded implementation admits systemd 261, cgroup v2, logical CPUs 0–31,
sibling pairs `n,n+16`, sixteen distinct physical cores and NUMA node 0. It reserves
CPUs **0–7,16–23**; the existing runner uses 0–7 or 0, leaving siblings unused.
The supervisor and controller use **8–15,24–31**. Other ordinary cgroups are
excluded from the reserved CPUs by the kernel partition, with effective sets
checked before admission. No existing slice CPU properties are edited. Root
kernel threads, interrupts, package power/thermals and shared memory remain
possible interference. Frequency/boost, global SMT and IRQ settings are not changed.

## Administrative boundary

The helper creates one top-level transient service using `systemd-run`, with a
three-hour hard runtime limit and a 150-second termination grace period. This
lease includes setup and waiting for the operator; it does not extend the study's
separate two-hour observation cap. Freeze and launch require at least two hours
remaining in the authority receipt. Finish builds and reviews before observation.

```text
systemd root
  ordinary units                  remaining CPUs
  temporary delegated service     member, requested CPUs 0–31
    supervisor                    root, remaining CPUs
    controller                    ordinary user, remaining CPUs
    workers                       isolated, CPUs 0–7,16–23
```

Systemd owns the service and enables the necessary controllers. The helper owns
its delegated descendants. **One explicit API exception is required:** systemd
261 has no exclusive-mask property, so the helper records and writes
`cpuset.cpus.exclusive` at its own service boundary. The inspected v261
implementation does not write that field. All other raw CPU/memory configuration
writes are below the delegation boundary. This is not claimed to be entirely
native systemd partition configuration; other systemd versions fail closed.
See the [systemd v261 implementation](https://github.com/systemd/systemd/blob/v261/src/core/cgroup.c),
[delegation ownership guidance](https://systemd.io/CGROUP_DELEGATION/) and
[kernel partition requirements](https://docs.kernel.org/admin-guide/cgroup-v2.html#cpuset).

The ordinary-user controller starts inside this service. Only the service-root,
controller and worker `cgroup.procs` files are delegated to that user; the host
root `cgroup.procs` and partition controls remain root-owned. A real task-owned,
untimed child moves into the worker partition, applies CPU 0 affinity, moves back
and exits before the authority receipt is published. This checks the
common-ancestor migration permission, which destination writability alone cannot
prove. No codec or real-input invocation occurs in that probe.

A single-use Unix socket accepts one command from the nominated UID and runs it
as that user. The privileged supervisor never accepts arbitrary commands or
runs the requested program. Supplementary groups are initialised, real/effective/
saved UID and GID are dropped, and only a small ordinary-user environment is
constructed. The command receives no stdin; stdout/stderr pass to its caller. Client
disconnection terminates that task command and leads to service cleanup.
Use an absolute executable and working directory. A wrapper script can perform
freeze, the one study and analysis sequentially; the helper adds no rounds.

## Commands for the operator

Read-only compatibility inspection requires no elevation:

```sh
/usr/bin/python3 -I scripts/measurement_reservation.py inspect
```

After reviewing the exact helper source and authority record, run the following
in your own terminal, replacing the authority locator and using the intended
ordinary user's numeric UID. Do not run the later `run` command with sudo.

```sh
sudo /usr/bin/python3 -I scripts/measurement_reservation.py start \
  --uid "$(id -u)" --authority 'REVIEWED-RESOURCE-OWNER-AUTHORITY-LOCATOR'
```

`start` copies this exact helper to a root-owned, hash-bound recovery file under
`/run/emuella-measurement-reservation`, journals original values before writes,
then launches the transient service. Directory and receipt modes are applied
explicitly after creation, so a restrictive sudo umask cannot prevent controller
traversal or ordinary-user receipt verification. The controller socket directory
stays private to the nominated UID; root-owned records remain non-writable to it.
A ready message means the live admission
probe and exclusion checks passed. The receipt is at
`/run/emuella-measurement-reservation/public/authority.json`. The coordinator must
still verify its authority, policy and workload bindings before measurements.

As the ordinary user, execute the prepared command inside the controller:

```sh
/usr/bin/python3 -I /run/emuella-measurement-reservation/helper.py run -- \
  /absolute/path/to/prepared-study-wrapper
```

This command slot is single-use, including failures. To release an unused lease
without running a study, use the same `run` command with `/usr/bin/true`.
Do not consume the slot merely to run a shell status check. The helper's internal
admission probe has already exercised the required migration.

## Restoration and recovery

Command completion, failure, service interruption and runtime expiry all lead to
systemd stopping this task's process group/cgroup and invoking the root-owned
`ExecStopPost` recovery helper. It checks unit invocation identity, requires worker
and controller groups to be empty, revokes the delegated placement permissions
and reverses journalled values only when they still match this helper's applied
values. An intervening value is retained and reported, never overwritten. Cleanup
is idempotent; write-ahead journal entries cover partial setup failures.

The external `run` client waits up to 160 seconds for teardown and verifies
restoration before returning. Standalone `verify` allows twenty seconds for
systemd to garbage-collect the unit and reconcile its controller requirements.
You can also verify restoration as the ordinary user:

```sh
/usr/bin/python3 -I /run/emuella-measurement-reservation/helper.py verify
```

Verification requires removal of the owned unit cgroup, the original isolated CPU
set, original online CPUs and frequency/boost/SMT policy, and original root enabled
controllers. Controller enablement is systemd-owned; the helper does not disable
controllers behind systemd's back. Any residual difference is reported as an
operational blocker, including a controller left enabled by systemd or another
actor. Ordinary temperature/frequency snapshots are not causal evidence.

For explicit early cancellation or recovery, authenticate locally:

```sh
sudo /usr/bin/python3 -I /run/emuella-measurement-reservation/helper.py stop
```

This stops only the recorded invocation and verifies restoration. If another
actor has replaced the unit or changed recorded values, recovery refuses to
clobber them. A host failure/reboot cannot supply an in-process cleanup receipt;
boot identity prevents replaying an old recovery journal. Runtime files disappear
on reboot, so retain receipts in the approved evidence store before reboot.

The root-owned journal, helper hash, authority and restoration files are retained
under `/run/emuella-measurement-reservation`; they are not deleted by cleanup.
A second `start` refuses an existing state directory. Do not delete retained
state to retry. If setup failed **before readiness**, use the repaired helper from
the checkout (the retained runtime helper is the old version):

```sh
sudo /usr/bin/python3 -I scripts/measurement_reservation.py retire-failed
```

This requires a stopped/unloaded unit, no remaining task cgroup, no ready flag or
authority receipt, successful cleanup and full original-snapshot restoration.
It then moves the entire failed-attempt directory to the deterministic sibling
`/run/emuella-measurement-reservation.failed-<attempt-id>`, without deleting files.
The original metadata modes are recorded; only the allowlisted root-owned
metadata and its traversal directories receive the intended readable modes.
Existing archives, unsafe file types/ownership and unresolved restoration fail
closed. No reservation is launched by this command. A later manually invoked
`start` is a separate setup attempt and remains subject to the study's prohibition
on another condition or replacement calls after timing begins.

The first authenticated attempt exposed a permissions defect: the runtime root
was mode 0700 and the controller logged permission denied after dropping root.
Creation modes had been filtered by the invoking environment's umask. Systemd
removed the failed unit before the launch wrapper's secondary stop, producing a
misleading "unit not loaded" message. The repair applies explicit modes, retains
secondary-stop diagnostics in `public/start-failure.json`, and tests restrictive
umasks. That observed failure remains evidence; it is not a timing observation or
a completed restoration claim until its privileged receipt has been verified.

No permanent unit, daemon, timer, scheduler or monitoring trial is installed.

## Explicit balanced diagnostic condition

Place `--condition balanced` **before** the subcommand on every invocation:

```sh
/usr/bin/python3 -I scripts/measurement_reservation.py --condition balanced inspect
sudo /usr/bin/python3 -I scripts/measurement_reservation.py --condition balanced start \
  --uid "$(id -u)" --authority 'REVIEWED-BALANCED-RESOURCE-OWNER-AUTHORITY-LOCATOR'
/usr/bin/python3 -I /run/emuella-balanced-measurement-reservation/helper.py \
  --condition balanced run -- /absolute/path/to/prepared-diagnostic-wrapper
/usr/bin/python3 -I /run/emuella-balanced-measurement-reservation/helper.py \
  --condition balanced verify
```

The fixed runtime directory is `/run/emuella-balanced-measurement-reservation`.
It is created exclusively and retained after completion. Existing contents are
never retired or deleted automatically. The original
`/run/emuella-measurement-reservation` remains untouched. For early cancellation,
use the balanced copy with `--condition balanced stop` under the same privileged
invocation as above. Explicit pre-readiness `retire-failed` has the same guarded
preservation rules, using the selected balanced directory and a sibling archive.

Balanced mode reserves the same CPUs **0–7,16–23**, with supervisor and controller
on **8–15,24–31**, but writes `root` to the worker's
`cpuset.cpus.partition`. The kernel therefore provides ordinary scheduling load
balancing within this exclusive partition. Its service ancestor remains a
`member`; the exclusive masks establish a remote partition beneath that ancestor.
Admission checks require the exact worker effective and exclusive sets, an empty
worker group without children, the ancestor and supervisor on housekeeping CPUs,
and every other descendant cgroup's effective set to exclude the reserved CPUs.
Where cpuset is disabled for children, those children must inherit a checked
parent allocation; a missing interface with the controller enabled fails closed.
The isolated CPU set and frequency/boost/SMT policy must remain unchanged.
See the [kernel cpuset partition contract](https://docs.kernel.org/admin-guide/cgroup-v2.html#cpuset).
Root kernel activity, interrupts and shared package/memory interference remain.

The lease is **1,800 seconds**, including setup and the wait for the single
ordinary-user command, followed by the existing 150-second termination grace.
The diagnostic runner separately enforces its four-call, fifteen-minute and
64 MiB-output limits; the reservation helper does not count diagnostic calls or
enlarge these limits. The existing unprivileged round-trip admission probe and
single-command socket transport are retained.

The root-owned journal uses `measurement-balanced-reservation/v1`; the authority
receipt at `public/authority.json` uses `measurement-balanced-qualification/v1`.
Both explicitly record `condition: "balanced"` and `partition_mode: "root"`.
The authority receipt retains the existing authority/issuer, validity interval,
worker cgroup path, worker CPUs `[0,1,2,3,4,5,6,7]`, reserved CPUs, controller CPUs
and residual-interference fields. It cannot qualify the historical isolated
stability protocol. Balanced restoration receipts also identify the condition and
partition mode. Recovery rejects a mismatching journal/schema/mode, and balanced
verification rejects a historical restoration receipt. Systemd's copied-helper
`serve` and `restore` commands carry the explicit condition argument, preserving
the selected mode through expiry and failure cleanup. Restoration still compares
the original snapshot, validates the unit invocation, and reverses only values
and ownership that match the journalled changes.

## Explicit balanced A/A condition

Place `--condition balanced-aa` **before** the subcommand on every invocation:

```sh
/usr/bin/python3 -I scripts/measurement_reservation.py --condition balanced-aa inspect
sudo /usr/bin/python3 -I scripts/measurement_reservation.py --condition balanced-aa start \
  --uid "$(id -u)" --authority 'REVIEWED-BALANCED-AA-RESOURCE-OWNER-AUTHORITY-LOCATOR'
/usr/bin/python3 -I /run/emuella-balanced-aa-measurement-reservation/helper.py \
  --condition balanced-aa run -- /absolute/path/to/prepared-aa-wrapper
/usr/bin/python3 -I /run/emuella-balanced-aa-measurement-reservation/helper.py \
  --condition balanced-aa verify
```

This condition uses `/run/emuella-balanced-aa-measurement-reservation`, created
exclusively and retained after completion. It neither reuses nor retires either
historical runtime directory. An existing A/A directory prevents a new `start`.
The selected root-owned copied helper carries `--condition balanced-aa` through
systemd's `serve` and `ExecStopPost` recovery commands. For early cancellation:

```sh
sudo /usr/bin/python3 -I /run/emuella-balanced-aa-measurement-reservation/helper.py \
  --condition balanced-aa stop
```

The lease is **10,800 seconds**, including setup and waiting for the single
ordinary-user command, followed by the existing 150-second termination grace.
The A/A runner separately enforces its **7,200-second observation cap**, frozen
call budget and evidence limit. Preparation must leave at least two hours in the
authority receipt at freeze and launch. The diagnostic mode remains limited to
1,800 seconds and retains its original schemas and receipts.

The A/A reservation uses the same `root` worker partition and admission checks as
the balanced diagnostic: CPUs **0–7,16–23** are exclusive, while supervisor,
controller and other ordinary workloads use **8–15,24–31**. Normal scheduling
load balancing remains enabled inside the worker partition. The inherited
exclusion and round-trip migration probes still run before receipt publication.
Frequency/boost, global SMT, IRQ and security settings remain unchanged.

The journal schema is `measurement-balanced-aa-reservation/v1`; the authority
receipt at `public/authority.json` uses `measurement-balanced-aa-qualification/v1`.
Both include `condition: "balanced-aa"` and `partition_mode: "root"`. The receipt
retains the authority, issuer, validity interval, worker cgroup, worker/reserved/
controller CPU sets and residual-interference statement. Restoration receipts
also carry the condition and partition mode. Journal admission, command transport
and recovery reject either historical mode's identity; verification refuses their
restoration receipts. The original snapshot and intervention-safe restoration
rules apply unchanged. A pre-readiness failure can only be preserved with the
selected condition's explicit, guarded `retire-failed` command; this never restarts
a reservation or authorises replacement observations.

## Verification status

Offline tests exercise journal ordering, partial failures, exclusion, admission
failure, privilege dropping, single-command transport, expiry configuration,
intervention-safe restoration and final verification using mocks and authored
processes. Read-only inspection can prove local prerequisite compatibility.
**Privileged setup and restoration still require the first authenticated host
execution.** Neither mocked tests nor read-only inspection establish a live
reservation or completed measurement study. Retain that first execution's actual
receipts, including any failure, before making such claims.

## Installed reusable balanced launcher

The optional installed launcher delegates the **host scheduling capability** to
one fixed ordinary numeric UID under a reviewed standing resource-owner decision.
It does not authorise a particular experiment, input, extra observation, release
or data operation. Every workload still needs its applicable campaign authority;
a per-run locator is retained metadata, never a file to load or a command to run.
In particular, this launcher does not reopen any closed historical attempt.

This is a distinct `balanced-reusable` condition, with
`measurement-balanced-reusable-reservation/v1` journals and
`measurement-balanced-reusable-qualification/v1` authority receipts. Each fresh
UUID gets a persistent directory under `/var/lib/emuella-measurement/leases/`.
The historical isolated, balanced diagnostic and balanced A/A directories and
schemas are unchanged. Do not use this authority receipt to qualify those
historical protocols without an explicit consumer contract change.

The fixed scope is the same balanced `root` partition: reserved CPUs
**0–7,16–23**, ordinary benchmark worker CPUs **0–7**, supervisor/controller CPUs
**8–15,24–31**, and one **10,800-second** lease including setup and waiting, plus
the existing 150-second stop grace. The controller is an ordinary user and can
run arbitrary ordinary-user workloads within its single command slot; this is
not a sandbox for untrusted workloads. There are no caller options for CPU masks,
UID, duration, executable, environment, unit, source directory or recovery path
at the privileged gateway.

Create a new package as the ordinary user from the reviewed candidate:

```sh
/usr/bin/python3 -I scripts/install_measurement_launcher.py package \
  --output /absolute/new-package-directory
```

The printed `package_sha256` binds the manifest, which binds all three Python
source files. Review those exact bytes and record the source revision and package
identity. Then authenticate once for installation:

```sh
sudo /usr/bin/python3 -I /absolute/new-package-directory/install_measurement_launcher.py install \
  --uid NUMERIC-ORDINARY-UID \
  --authority 'REVIEWED-STANDING-RESOURCE-OWNER-DECISION' \
  --package-sha256 PRINTED-PACKAGE-DIGEST
```

When the package remains in a user-writable directory, use a trusted interpreter
bootstrap which reads the installer once, checks its separately reviewed SHA-256,
sets `__file__` to its absolute package path and executes those same checked
bytes. A hash check followed by a separate executable read has a race. The
installer independently reads and hashes each remaining source before copying
those same bytes. Installation requires explicit administrative authority;
ordinary code merge authority alone does not grant an access-policy change.

Installation creates fixed root-owned files in
`/usr/local/libexec/emuella-measurement/`, a root-owned policy with the designated
UID/GID/account, scope and standing authority, persistent lease storage, and
`/etc/sudoers.d/emuella-measurement`. Existing destinations, symlinks, writable
ancestors and non-regular sources are rejected. The installer validates both the
candidate and complete sudoers policy. A rejected published rule is moved into
the installed directory as evidence. Partial installations remain visible and
require administrator diagnosis; they are never overwritten automatically.

Only the installed launcher is passwordless, with four exact sudoers argument
lists and `NOSETENV`. No writable checkout, generic interpreter, service manager,
recovery helper or wildcard command is delegated. The launcher's absolute
`/usr/bin/python3 -I` shebang isolates Python from user module paths; Python and
its standard library are host OS dependencies maintained by the administrator.
The launcher verifies root ownership and ancestor permissions, the package hashes
and the fixed policy at every invocation, clears inherited settings, and uses
absolute administrative executables. The service executes its root-owned,
hash-bound lease copy of the helper. No persistent daemon, timer or unit is
installed.

After installation, start with one UTF-8 authority locator, at most 2,048 bytes,
followed by EOF on standard input (input must finish within ten seconds):

```sh
printf '%s\n' 'THIS-WORKLOAD-AUTHORITY-LOCATOR' | \
  sudo -n /usr/local/libexec/emuella-measurement/measurement_launcher.py start
sudo -n /usr/local/libexec/emuella-measurement/measurement_launcher.py status
```

`status` emits `measurement-launcher-status/v1` JSON with the current lease UUID,
unit, expiry, helper path, installation binding and receipt paths. An unused
installation reports `state: "unused"`. `state: "cleanup-recorded"` means cleanup
ran; only `restoration_verified: true` records a completed gateway verification.
Status does not itself prove live restoration. Start prints readiness messages
and the same status object after admission. An overlapping request fails without
stopping the existing lease.

Use the returned absolute `helper` path as the ordinary user:

```sh
/usr/bin/python3 -I /var/lib/emuella-measurement/leases/LEASE-UUID/helper.py \
  --condition balanced-reusable run -- /absolute/ordinary-user-program
sudo -n /usr/local/libexec/emuella-measurement/measurement_launcher.py verify
```

The ordinary command slot remains single-use on success or failure. The existing
supervisor handles completion, client disconnection and expiry. Explicit
cancellation stops only the journal's owned systemd invocation:

```sh
sudo -n /usr/local/libexec/emuella-measurement/measurement_launcher.py stop
```

A nonblocking root-owned lock serialises administrative operations. Intent is
recorded before setup, so an interrupted or partial start cannot be silently
retried. Before the next start, the gateway verifies cleanup, original host
snapshot and cgroup removal, then retains a root-owned
`public/launcher-verification.json` bound to the exact journal and boot. The
previous helper source, journal, authority and restoration receipts remain in
place. There is no implicit deletion, lease reuse or retention pruning.

Run privileged `verify` after each command, including failures, and before a
planned reboot. A previously verified terminal journal may be carried across a
normal reboot; a fresh lease captures a fresh host snapshot. A reboot with an
unverified or interrupted lease blocks new admission. Changed source identity,
account identity, intervening host state or failed restoration also blocks. An
administrator must investigate the retained evidence and establish the missing
restoration observation; there is no passwordless reset or force override.
A restored lease on the current boot is verified live again before a fresh start.

To revoke the capability, an administrator first stops and verifies any active
lease, then removes only `/etc/sudoers.d/emuella-measurement` and runs `visudo -c`.
For urgent revocation, remove that exact rule first and perform cancellation
under separately authenticated administrative authority. Keep the installed
recovery code and all lease receipts until restoration is proved. Source upgrades,
account/scope changes, prior-boot failure recovery and eventual receipt retention
management require an explicitly reviewed administrative operation. They are not
passwordless actions and this installer never replaces an existing installation.
