#!/usr/bin/env python3
"""Reconstruct retained finite evidence without corpus calls or a live lease."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
import finite_confirmation_live as live
finite = live.finite


def retained_binding(path, digest, v1, register, design, predecessor=None):
    if live.sha(path) != digest:
        raise ValueError('externally pinned preparation digest differs')
    binding = json.loads(path.read_text())
    if binding.get('schema') != live.preparation_schema(binding['manifest']):
        raise ValueError('retained v2 preparation required')
    contract = binding['manifest']
    if contract['schema'] == live.assessment.SCHEMA:
        if predecessor is None:
            raise ValueError('assessment predecessor manifest required for reconstruction')
        expected = live.assessment.derive(v1, binding['config']['contract']['v1_sha256'], register, design,
            predecessor, contract['predecessor_sha256'], binding['config']['authority'], contract['source_treatment_text'],
            contract['source_treatment_sha256'], contract['source_review_text'],
            contract['assessment_register_text'], contract['assessment_register_sha256'])
    elif contract['schema'] == finite.DISPATCH_SCHEMA:
        expected = live.derive_dispatch(v1, contract['predecessor_sha256'], register, design,
            binding['config']['authority'], contract['source_treatment_text'],
            contract['source_treatment_sha256'], contract['source_review_text'])
    else:
        expected = live.derive(v1, contract['predecessor_sha256'], register, design,
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
        builds = binding['builds'][planned.get('build_instance', 'main')] if binding['manifest']['schema'] == live.assessment.SCHEMA else binding['builds']
        build = builds[planned['arm']][mode]['build']
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


def retained_assessment_builds(binding, preparation_sha, path, expected_sha, evidence):
    """Bind approved-store copies to the frozen measured executable receipts."""
    if path is None or expected_sha is None:
        raise ValueError('externally pinned retained assessment builds required')
    path = live.absolute(str(path))
    approved_roots = [live.absolute(root) for root in binding['config']['evidence_roots']]
    if not path.is_file() or not any(path.is_relative_to(root) for root in approved_roots):
        raise ValueError('retained build mapping missing or outside approved evidence roots')
    if live.sha(path) != expected_sha:
        raise ValueError('retained build mapping digest differs')
    mapping = json.loads(path.read_text())
    frozen = binding['build_reproducibility']
    if (set(mapping) != {'schema', 'preparation_sha256', 'build_reproducibility_sha256', 'instances'}
            or mapping['schema'] != 'classic-forward53-integration-retained-builds/v1'
            or mapping['preparation_sha256'] != preparation_sha
            or mapping['build_reproducibility_sha256'] != binding['prerequisites']['build_reproducibility']['sha256']
            or set(mapping['instances']) != {'main', 'repeat'}):
        raise ValueError('retained build mapping identity differs')
    seen = set()
    for instance in ('main', 'repeat'):
        if set(mapping['instances'][instance]) != {'baseline', 'candidate'}:
            raise ValueError('retained build arms differ')
        for arm in ('baseline', 'candidate'):
            if set(mapping['instances'][instance][arm]) != {'ordinary', 'resource'}:
                raise ValueError('retained build modes differ')
            for mode in ('ordinary', 'resource'):
                item = mapping['instances'][instance][arm][mode]
                if set(item) != {'path', 'binary_sha256', 'text_sha256'}:
                    raise ValueError('retained build entry fields differ')
                retained = live.absolute(item['path'])
                if (retained.is_symlink() or not retained.is_file()
                        or not any(retained.is_relative_to(root) for root in approved_roots)
                        or retained in seen):
                    raise ValueError('retained executable missing, duplicated or outside approved evidence roots')
                seen.add(retained)
                measured = binding['builds'][instance][arm][mode]['build']
                original = frozen['instances'][instance][arm][mode]
                if (item['binary_sha256'] != measured['binary_sha256']
                        or item['binary_sha256'] != original['binary_sha256']
                        or item['text_sha256'] != original['text_sha256']
                        or live.sha(retained) != item['binary_sha256']):
                    raise ValueError('retained executable or frozen build identity differs')
                section = subprocess.check_output(['objcopy', '--only-section=.text', '-O', 'binary',
                                                   str(retained), '/dev/stdout'])
                if hashlib.sha256(section).hexdigest() != item['text_sha256']:
                    raise ValueError('retained executable section differs')
                evidence[str(retained)] = item['binary_sha256']
    evidence[str(path)] = expected_sha
    return mapping


def reconstruct(binding, digest, estimators, *, retained_builds=None, retained_builds_sha256=None):
    root = Path(binding['config']['stores']['rareplanes']['output'])
    evidence, issues = {}, []
    rows, started, missing, orphaned, collection_issues = collect_rows(binding, evidence)
    issues.extend(collection_issues)
    launch = read_optional(root/'launch.json', evidence)
    completion = read_optional(root/'completion.json', evidence)
    execution = read_optional(root/'execution-started.json', evidence)
    terminal = read_optional(root/'execution-complete.json', evidence)
    restoration = read_optional(root/'independent-restoration.json', evidence)
    assessment_mode = binding['manifest']['schema'] == live.assessment.SCHEMA
    checks = dict.fromkeys(live.assessment.CHECKS if assessment_mode else finite.CHECKS, False)
    for key in live.prerequisite_keys(binding['manifest']):
        record = binding['prerequisites'][key]
        try:
            live.validate_prerequisite_treatment(binding['manifest'], key, record)
            if live.sha(record['path']) != record['sha256']:
                raise ValueError('prerequisite digest differs')
            evidence[record['path']] = record['sha256']
            if key in checks:
                checks[key] = True
        except (OSError, ValueError) as error:
            issues.append('retained prerequisite '+key+': '+str(error))
    if assessment_mode and checks['build_reproducibility']:
        try:
            if json.loads(Path(binding['prerequisites']['build_reproducibility']['path']).read_text()) != binding['build_reproducibility']:
                raise ValueError('frozen build receipt differs from preparation')
            retained_assessment_builds(binding, digest, retained_builds, retained_builds_sha256, evidence)
        except (OSError, ValueError, KeyError, TypeError, subprocess.SubprocessError) as error:
            checks['build_reproducibility'] = False
            issues.append('retained build reproducibility: '+str(error))
    try:
        if not execution or execution['preparation_sha256'] != digest:
            raise ValueError('bound execution record absent')
        live.verify_retained_restoration(binding, restoration, execution['lease_id'], execution['authority_sha256'])
        checks['restoration'] = runner_restored(root, started, evidence, json.loads(restoration['authority_text'])['controller_cpus'])
        if not checks['restoration']:
            raise ValueError('ordinary runner restoration absent or invalid')
        if (not terminal or terminal['schema'] != live.record_schema(binding) or terminal['lease_id'] != execution['lease_id']
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
    if (not completion or completion.get('schema') != live.record_schema(binding) or completion.get('preparation_sha256') != digest
            or completion.get('started_calls') != len(started)
            or completion.get('missing_call_ids') != binding['manifest']['schedule']['call_order'][len(started):]):
        issues.append('complete bound acquisition accounting absent or inconsistent')
    consumption = dict(consumption, started_calls=len(started))
    result = (live.assessment.analyse_attempt(binding['manifest'], rows, estimators, checks=checks,
              consumption=consumption) if assessment_mode else finite.analyse_attempt(binding['manifest'], rows,
              estimators, checks=checks, consumption=consumption))
    if completion:
        for retained in completion.get('decisions', []):
            recomputed = next((r for r in result['endpoints'] + result.get('repeats', [])
                               if r['endpoint_id'] == retained['endpoint_id']), None)
            if recomputed != retained:
                issues.append('retained endpoint decision was not reproduced: '+retained['endpoint_id'])
        if completion.get('disposition') != result['disposition'] or completion.get('issues'):
            issues.append('acquisition stopped or its disposition differs from complete reconstruction')
    if terminal and terminal.get('error'):
        issues.append('outside execution recorded an operational error: '+terminal['error'])
    result['issues'].extend(issues)
    if result['issues']:
        result['disposition'] = finite.INCOMPLETE
    label = ('integration assessment v1' if assessment_mode else
             'parallel dispatch v1' if binding['manifest']['schema'] == finite.DISPATCH_SCHEMA else 'v2')
    result.update(preparation_sha256=digest, started_receipts=started, missing_terminal_call_ids=missing,
                  orphaned_receipts=orphaned, evidence_sha256=evidence, independent_restoration=restoration,
                  interpretation='Retained '+label+' reconstruction; no corpus invocation, live lease or production authority')
    return result


def report(args):
    binding = retained_binding(args.preparation, args.sha256, args.v1, args.register, args.design,
                               args.predecessor)
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
    result = reconstruct(binding, args.sha256, estimators,
                         retained_builds=args.retained_builds,
                         retained_builds_sha256=args.retained_builds_sha256)
    result['reconstruction_estimators'] = identities
    live.write(output, result)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for key in ('preparation', 'v1', 'register', 'design', 'estimator-40', 'estimator-160', 'output'):
        parser.add_argument('--'+key, type=Path, required=True)
    parser.add_argument('--predecessor', type=Path)
    parser.add_argument('--retained-builds', type=Path)
    parser.add_argument('--retained-builds-sha256')
    parser.add_argument('--sha256', required=True)
    args = parser.parse_args()
    result = report(args)
    return 0 if result['disposition'] == finite.PASS else 1


if __name__ == '__main__':
    sys.exit(main())
