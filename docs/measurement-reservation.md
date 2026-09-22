# Temporary measurement reservation

`scripts/measurement_reservation.py` is an opt-in administrative helper for the
existing [measurement stability protocol](measurement-stability.md). It does not
build a codec, read imagery, launch measurements, alter the comparator or select
a candidate. It needs explicit resource-owner authority for the host scheduling
change and one local `sudo` authentication. No sudoers or polkit policy is changed.

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

## Verification status

Offline tests exercise journal ordering, partial failures, exclusion, admission
failure, privilege dropping, single-command transport, expiry configuration,
intervention-safe restoration and final verification using mocks and authored
processes. Read-only inspection can prove local prerequisite compatibility.
**Privileged setup and restoration still require the first authenticated host
execution.** Neither mocked tests nor read-only inspection establish a live
reservation or completed measurement study. Retain that first execution's actual
receipts, including any failure, before making such claims.
