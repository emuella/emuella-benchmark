#!/usr/bin/env python3
"""Reconstruct retained finite v2 evidence without corpus calls or a live lease."""
import argparse
import hashlib
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
import finite_confirmation_live as live
finite = live.finite


def retained_binding(path, digest, v1, register, design):
    if live.sha(path) != digest:
        raise ValueError('externally pinned preparation digest differs')
    binding = json.loads(path.read_text())
    if binding.get('schema') != live.PREPARATION:
        raise ValueError('retained v2 preparation required')
    expected = live.derive(v1, binding['manifest']['predecessor_sha256'], register, design,
                           binding['config']['authority'])
    if binding['manifest'] != expected:
        raise ValueError('retained v2 derivation differs')
    return binding


def read_optional(path, evidence):
    if not path.exists():
        return None
    evidence[str(path)] = live.sha(path)
    return json.loads(path.read_text())


def collect_rows(binding, evidence):
    rows, started, missing, orphaned, issues = [], [], [], [], []
    expected_files = set()
    for planned in live.ordered(binding['manifest']):
        item = binding['requests'][planned['call_id']]
        root = Path(binding['config']['stores'][item['store']]['output'])
        start_path, row_path = (root/(planned['call_id']+suffix) for suffix in ('-started.json', '-receipt.json'))
        expected_files.update((start_path, row_path))
        start, row = read_optional(start_path, evidence), read_optional(row_path, evidence)
        if start is None:
            if (root/planned['call_id']).exists():
                orphaned.append(dict(unbound_call_directory=str(root/planned['call_id'])))
                issues.append('worker directory without start: '+planned['call_id'])
            if row is not None:
                orphaned.append(row); issues.append('terminal receipt without start: '+planned['call_id'])
            continue
        started.append(start)
        if start.get('planned') != planned or type(start.get('monotonic_ns')) is not int:
            issues.append('started identity differs: '+planned['call_id'])
        if row is None:
            missing.append(planned['call_id'])
            # Explicit absence, not a replacement observation or altered receipt.
            row = dict(planned=planned, result=dict(status='missing_terminal_receipt'),
                       gates_passed=False, reconstruction='only the original started receipt exists')
        elif row.get('planned') != planned:
            issues.append('terminal identity differs: '+planned['call_id'])
        rows.append(row)
    for info in binding['config']['stores'].values():
        root = Path(info['output'])
        for pattern in ('ordinary-*-*.json', 'allocation-*-*.json', 'preflight-*-*.json'):
            for path in root.glob(pattern):
                if path not in expected_files:
                    orphaned.append(read_optional(path, evidence)); issues.append('unexpected call receipt: '+path.name)
    if [r.get('planned') for r in started] != live.ordered(binding['manifest'])[:len(started)]:
        issues.append('started calls are not the frozen schedule prefix')
    return rows, started, missing, orphaned, issues


def runner_restored(root, started, evidence, controller_cpus):
    original = read_optional(root/'placement-original.json', evidence)
    restored = read_optional(root/'restoration.json', evidence)
    if original is None and restored is None and not started:
        return True  # No ordinary placement began; independent lease restoration still required.
    return bool(original is not None and restored is not None
                and restored.get('restored') is True and restored.get('worker_cgroup_empty') is True
                and restored.get('intervening_change') is False and restored.get('host_policy_changes') is False
                and restored.get('original') == original.get('original') == restored.get('final')
                and restored.get('observed_before_restore') == original.get('intended') == controller_cpus)


def row_checks(binding, rows, launch):
    """Validate retained request/result/environment fields; never reopen inputs."""
    for index, row in enumerate(rows):
        planned, result = row['planned'], row.get('result', {})
        if result.get('status') != 0 or row.get('gates_passed') is not True:
            raise ValueError('failed or incomplete retained call')
        item = binding['requests'][planned['call_id']]
        request = item['request']; observed = result['observation']
        root = Path(binding['config']['stores'][item['store']]['output'])/planned['call_id']
        if json.loads((root/'request.json').read_text()) != request:
            raise ValueError('retained worker request differs')
        for key in ('codec', 'operation', 'case_id', 'round', 'style', 'workers', 'raw_sha256', 'stream_sha256'):
            if observed.get(key) != request[key]:
                raise ValueError('retained result identity differs: '+key)
        mode = 'resource' if planned['stage'] == 'allocation' else 'ordinary'
        build = binding['builds'][planned['arm']][mode]['build']
        if (observed.get('binary_sha256') != build['binary_sha256'] or observed.get('exact') is not True
                or observed.get('boundary') != live.refresh.BOUNDARY):
            raise ValueError('retained binary/boundary/exactness differs')
        for snapshot in ('before', 'after'):
            if live.stability.environment_issues(launch['environment'], row['environment'][snapshot], launch['condition']):
                raise ValueError('retained environment gate failed')
        if row['environment']['issues']:
            raise ValueError('retained environment issues were reported')
        if mode == 'resource':
            # Recompute on a copy: original receipts remain unedited in the report.
            copy = dict(row)
            live.resource_gate(copy, request, rows[index-1] if index else None)
            if copy['resources'] != row.get('resources'):
                raise ValueError('retained resource predicate differs')
        elif (not isinstance(observed.get('samples_ns'), list) or len(observed['samples_ns']) != 1
                or type(observed['samples_ns'][0]) is not int or observed['samples_ns'][0] <= 0
                or any(observed.get(k) is not None for k in ('allocation_diagnostic', 'execution_diagnostic'))):
            raise ValueError('retained ordinary sample differs')
    return True


def reconstruct(binding, digest, estimators):
    root = Path(binding['config']['stores']['rareplanes']['output'])
    evidence, issues = {}, []
    rows, started, missing, orphaned, collection_issues = collect_rows(binding, evidence)
    issues.extend(collection_issues)
    launch = read_optional(root/'launch.json', evidence)
    completion = read_optional(root/'completion.json', evidence)
    execution = read_optional(root/'execution-started.json', evidence)
    terminal = read_optional(root/'execution-complete.json', evidence)
    restoration = read_optional(root/'independent-restoration.json', evidence)
    checks = dict.fromkeys(finite.CHECKS, False)
    for key in live.PREREQUISITES:
        record = binding['prerequisites'][key]
        try:
            if live.sha(record['path']) != record['sha256']:
                raise ValueError('prerequisite digest differs')
            evidence[record['path']] = record['sha256']
            if key in checks:
                checks[key] = True
        except (OSError, ValueError) as error:
            issues.append('retained prerequisite '+key+': '+str(error))
    try:
        if not execution or execution['preparation_sha256'] != digest:
            raise ValueError('bound execution record absent')
        live.verify_retained_restoration(binding, restoration, execution['lease_id'], execution['authority_sha256'])
        checks['restoration'] = runner_restored(root, started, evidence, json.loads(restoration['authority_text'])['controller_cpus'])
        if not checks['restoration']:
            raise ValueError('ordinary runner restoration absent or invalid')
        if (not terminal or terminal['schema'] != live.SCHEMA or terminal['lease_id'] != execution['lease_id']
                or terminal.get('restoration_verified') is not True):
            raise ValueError('outside execution completion absent or restoration failed')
    except (OSError, ValueError, KeyError, TypeError) as error:
        issues.append('restoration: '+str(error))
    try:
        if not launch or launch['preparation_sha256'] != digest or launch['authority_sha256'] != execution['authority_sha256']:
            raise ValueError('bound launch record absent')
        receipt = json.loads(restoration['authority_text'])
        if launch['condition'] != live.common_authority(receipt):
            raise ValueError('launch authority differs from restored lease')
        if receipt['schema'] != live.RESERVATION or receipt['condition'] != 'balanced-reusable' or receipt['partition_mode'] != 'root':
            raise ValueError('retained reservation condition differs')
        checks['reservation'] = True
        checks['identity_environment'] = row_checks(binding, rows, launch)
        checks['resources'] = checks['identity_environment']
    except (OSError, ValueError, KeyError, TypeError) as error:
        issues.append('retained call gates: '+str(error))
    consumption = completion.get('consumption', {}) if completion else {}
    if (not completion or completion.get('schema') != live.SCHEMA or completion.get('preparation_sha256') != digest
            or completion.get('started_calls') != len(started)
            or completion.get('missing_call_ids') != binding['manifest']['schedule']['call_order'][len(started):]):
        issues.append('complete bound acquisition accounting absent or inconsistent')
    consumption = dict(consumption, started_calls=len(started))
    result = finite.analyse_attempt(binding['manifest'], rows, estimators, checks=checks, consumption=consumption)
    if completion:
        for retained in completion.get('decisions', []):
            recomputed = next((r for r in result['endpoints'] if r['endpoint_id'] == retained['endpoint_id']), None)
            if recomputed != retained:
                issues.append('retained endpoint decision was not reproduced: '+retained['endpoint_id'])
        if completion.get('disposition') != result['disposition'] or completion.get('issues'):
            issues.append('acquisition stopped or its disposition differs from complete reconstruction')
    if terminal and terminal.get('error'):
        issues.append('outside execution recorded an operational error: '+terminal['error'])
    result['issues'].extend(issues)
    if result['issues']:
        result['disposition'] = finite.INCOMPLETE
    result.update(preparation_sha256=digest, started_receipts=started, missing_terminal_call_ids=missing,
                  orphaned_receipts=orphaned, evidence_sha256=evidence, independent_restoration=restoration,
                  interpretation='Retained v2 reconstruction; no corpus invocation, live lease or production authority')
    return result


def report(args):
    binding = retained_binding(args.preparation, args.sha256, args.v1, args.register, args.design)
    output = live.absolute(str(args.output))
    if output.parent != Path(binding['config']['stores']['rareplanes']['output']):
        raise ValueError('report must remain in its approved observation root')
    estimators, identities = {}, {}
    for count in (40, 160):
        path = getattr(args, 'estimator_'+str(count))
        identity = live.stability.estimator_identity(path, count)
        original = binding['estimators'][str(count)]
        if any(identity[k] != original[k] for k in ('owner_module_sha256', 'entrypoint_sha256', 'manifest_sha256')):
            raise ValueError('reconstruction comparator differs from frozen owner/wrapper')
        estimators[count], identities[str(count)] = path, identity
    result = reconstruct(binding, args.sha256, estimators)
    result['reconstruction_estimators'] = identities
    live.write(output, result)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for key in ('preparation', 'v1', 'register', 'design', 'estimator-40', 'estimator-160', 'output'):
        parser.add_argument('--'+key, type=Path, required=True)
    parser.add_argument('--sha256', required=True)
    args = parser.parse_args()
    result = report(args)
    return 0 if result['disposition'] == finite.PASS else 1


if __name__ == '__main__':
    sys.exit(main())
