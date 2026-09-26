"""Opt-in forward 5/3 integration assessment contract and offline decisions.

Historical finite contracts and their interpretation remain in their own module.
This module never opens corpus inputs or authorises production selection.
"""
import copy
import hashlib
import json
import math
from pathlib import Path

import finite_confirmation_analysis as finite


SCHEMA = 'classic-forward53-integration-assessment/v1'
PREPARATION = 'classic-forward53-integration-assessment-preparation/v1'
SOURCE_SCHEMA = 'classic-forward53-integration-assessment-source/v1'
REVIEW_SCHEMA = 'classic-forward53-integration-assessment-source-review/v1'
REGISTER_SCHEMA = 'classic-forward53-integration-assessment-endpoint-register/v1'
SOURCE_FIELDS = ('baseline_codec', 'candidate_codec', 'baseline_tree', 'candidate_tree',
                 'baseline_to_candidate_diff_sha256')
REPEATS = (0, 1, 10)
REPEAT_IDS = {index: f'repeat-{index:02}' for index in REPEATS}
CHECKS = (*finite.CHECKS, 'source_review', 'build_provenance', 'build_reproducibility')


def source(manifest):
    text = manifest['source_treatment_text']
    if hashlib.sha256(text.encode('utf-8')).hexdigest() != manifest['source_treatment_sha256']:
        raise ValueError('assessment source treatment digest differs')
    value = json.loads(text)
    if (set(value) != {'schema', 'independent_review', *SOURCE_FIELDS}
            or value['schema'] != SOURCE_SCHEMA
            or value['baseline_codec'] == value['candidate_codec']
            or any(not finite.hex_identity(value[key], 64 if key.endswith('_sha256') else 40)
                   for key in SOURCE_FIELDS)):
        raise ValueError('exact assessment source identities required')
    review = value['independent_review']
    if (set(review) != {'path', 'sha256'} or not isinstance(review['path'], str) or not review['path']
            or hashlib.sha256(manifest['source_review_text'].encode('utf-8')).hexdigest() != review['sha256']):
        raise ValueError('assessment source review digest differs')
    verdict = json.loads(manifest['source_review_text'])
    if (verdict.get('schema') != REVIEW_SCHEMA or verdict.get('verdict') != 'PASS'
            or any(not isinstance(verdict.get(k), str) or not verdict[k].strip()
                   for k in ('reviewer', 'locator'))
            or verdict.get('sources') != {key: value[key] for key in SOURCE_FIELDS}):
        raise ValueError('independent assessment source review must bind all identities')
    if manifest['sources']['baseline_codec'] != value['baseline_codec'] or manifest['sources']['candidate_codec'] != value['candidate_codec']:
        raise ValueError('assessment manifest and source treatment differ')
    return value


def endpoint_policy(value, original, predecessor_sha):
    if (not isinstance(value, dict) or value.get('schema') != REGISTER_SCHEMA
            or value.get('policy') != SCHEMA
            or value.get('predecessor', {}).get('sha256') != predecessor_sha
            or value.get('order') != list(finite.ORDER)
            or value.get('repeats') != [f'endpoint-{i:02}' for i in REPEATS]
            or not isinstance(value.get('endpoints'), list) or len(value['endpoints']) != 28):
        raise ValueError('complete frozen assessment endpoint register required')
    margins = {}
    inherited = ('id', 'case_id', 'operation', 'style', 'workers', 'origin', 'raw_sha256', 'stream_sha256')
    for index, row in enumerate(value['endpoints']):
        previous = original['endpoints'][index]
        primary = index == 0
        expected = dict(operator='<' if primary else '<=', value=-.05 if primary else .01)
        new = row.get('new_upper_relative_99')
        if (any(row.get(field) != previous[field] for field in inherited)
                or row.get('role') != ('sole_primary' if primary else 'secondary')
                or row.get('old_upper_relative_99') != expected
                or row.get('old_absolute_mean_saving_ms') != previous['absolute_mean_saving_ms']
                or row.get('new_absolute_mean_saving_ms') != previous['absolute_mean_saving_ms']
                or not isinstance(new, dict) or new.get('operator') != ('<' if primary else '<=')
                or type(new.get('value')) not in (int, float)
                or not math.isfinite(new['value'])):
            raise ValueError('assessment endpoint identity or inherited predicate differs')
        if primary:
            if new['value'] != -.05:
                raise ValueError('primary gain threshold differs')
        elif not 0 <= new['value'] <= .05:
            raise ValueError('secondary margin exceeds registered +5% allowance')
        else:
            margins[row['id']] = new['value']
    return margins


def derive(v1, digest, register, design, predecessor, predecessor_sha, authority,
           source_text, source_sha, review_text, policy_text, policy_sha):
    original = finite.load_manifest(v1, digest, register, design)
    if finite.sha(predecessor) != predecessor_sha:
        raise ValueError('externally pinned dispatch predecessor differs')
    previous = json.loads(Path(predecessor).read_text())
    if (previous.get('schema') != finite.DISPATCH_SCHEMA
            or previous.get('predecessor_sha256') != digest
            or previous.get('schedule') != original['schedule']
            or previous.get('endpoints') != original['endpoints']
            or previous.get('limits') != original['limits']):
        raise ValueError('complete unchanged parallel dispatch predecessor required')
    finite.dispatch_source(previous)
    if (not isinstance(authority, str) or not authority.strip()
            or hashlib.sha256(policy_text.encode('utf-8')).hexdigest() != policy_sha):
        raise ValueError('separate authority and pinned assessment endpoint register required')
    values = endpoint_policy(json.loads(policy_text), previous, predecessor_sha)
    result = copy.deepcopy(previous)
    result.update(schema=SCHEMA, predecessor_sha256=predecessor_sha, authority=authority,
                  reservation_schema='measurement-balanced-reusable-qualification/v1',
                  condition='balanced-reusable', source_treatment_text=source_text,
                  source_treatment_sha256=source_sha, source_review_text=review_text,
                  assessment_register_text=policy_text, assessment_register_sha256=policy_sha,
                  secondary_upper_relative_99=values)
    treatment = json.loads(source_text)
    result['sources'].update(baseline_codec=treatment['baseline_codec'],
                             candidate_codec=treatment['candidate_codec'])
    source(result)
    # The complete historical 28-endpoint graph is retained. A distinct second
    # build instance supplies three additional sessions after that graph.
    repeat = []
    for index in REPEATS:
        endpoint_id = REPEAT_IDS[index]
        for arm in ('baseline', 'candidate'):
            repeat.append(dict(endpoint_id=endpoint_id, stage='preflight', arm=arm))
        for arm in ('baseline', 'candidate'):
            repeat.append(dict(endpoint_id=endpoint_id, stage='allocation', arm=arm,
                               case_id=original['endpoints'][index]['case_id'],
                               style=original['endpoints'][index]['style'],
                               workers=original['endpoints'][index]['workers']))
        for round_id in range(40):
            for position, arm in enumerate(('baseline', 'candidate') if round_id % 2 == 0 else ('candidate', 'baseline')):
                repeat.append(dict(endpoint_id=endpoint_id, stage='ordinary', arm=arm,
                                   round=round_id, position=position))
    for item in repeat:
        stage = item.pop('stage')
        item.update(index=len(result['schedule']['call_order']),
                    call_id=f'{stage}-{len(result["schedule"][stage]):04}', stage=stage,
                    build_instance='repeat')
        result['schedule'][stage].append(item)
        result['schedule']['call_order'].append(item['call_id'])
    result['repeat_endpoint_order'] = list(REPEATS)
    result['limits'] = dict(finite.limits(), pairs=1360, ordinary_calls=2720,
                            preflight_calls=62, allocation_calls=118, total_calls=2900)
    if len(result['schedule']['call_order']) != 2900:
        raise AssertionError('assessment schedule count differs')
    return result


def ordered(manifest):
    return sorted((row for stage in ('allocation', 'preflight', 'ordinary')
                   for row in manifest['schedule'][stage]), key=lambda row: row['index'])


def decision(session, endpoint_id, margin):
    if not session['valid'] or not session['complete']:
        return dict(disposition=finite.INCOMPLETE, reason='complete valid fixed-count evidence is missing')
    record = session['estimator']['B_over_A']
    output = record['output']
    lower, upper = record['lower'], record['upper']
    saving = (output['baseline_mean_ns']-output['candidate_mean_ns'])/1e6
    primary = endpoint_id in ('endpoint-00', 'repeat-00')
    threshold = -.05 if primary else margin
    if primary and saving < 10:
        disposition, reason = finite.NOT_SELECTED, 'observed mean saving is below 10 ms'
    elif upper is not None and (upper < threshold if primary else upper <= threshold):
        disposition, reason = finite.PASS, 'complete directional bound and absolute gate pass'
    elif lower is not None and (lower >= threshold if primary else lower > threshold):
        disposition, reason = finite.NOT_SELECTED, 'complete interval excludes the required bound'
    else:
        disposition, reason = finite.NOT_QUALIFIED, 'fixed-count interval does not resolve the required bound'
    return dict(disposition=disposition, reason=reason, upper_relative_99=upper,
                required_upper_relative_99=threshold, mean_saving_ms=saving,
                baseline_mean_ns=output['baseline_mean_ns'], candidate_mean_ns=output['candidate_mean_ns'],
                relative_interval_99=output.get('relative_interval_99'),
                relative_change=output['candidate_mean_ns']/output['baseline_mean_ns']-1,
                legacy_timing_verdict=output['verdict'])


def analyse_endpoint(manifest, endpoint_id, rows, estimator):
    import precision_feasibility_analysis as analysis
    if endpoint_id.startswith('repeat-'):
        index = int(endpoint_id[7:])
        if index not in REPEATS:
            raise ValueError('unregistered repeat endpoint')
    else:
        index = int(endpoint_id[9:])
        if endpoint_id != f'endpoint-{index:02}' or index not in range(28):
            raise ValueError('unregistered assessment endpoint')
    count = 160 if endpoint_id == 'endpoint-11' else 40
    session = analysis.analyse_session(rows, estimator, rounds=count)
    margin = manifest['secondary_upper_relative_99'].get(f'endpoint-{index:02}')
    return dict(endpoint_id=endpoint_id, status='analysed' if session['valid'] else 'invalid',
                analysis=session, **decision(session, endpoint_id, margin))


def analyse_attempt(manifest, rows, estimators, *, checks, consumption):
    source(manifest)
    if (manifest['schema'] != SCHEMA or manifest['limits']['total_calls'] != 2900
            or len(ordered(manifest)) != 2900 or manifest['repeat_endpoint_order'] != list(REPEATS)
            or endpoint_policy(json.loads(manifest['assessment_register_text']),
                               manifest, manifest['predecessor_sha256']) != manifest['secondary_upper_relative_99']
            or hashlib.sha256(manifest['assessment_register_text'].encode()).hexdigest() != manifest['assessment_register_sha256']):
        raise ValueError('frozen assessment contract required')
    issues = finite.budget_issues(consumption, caps=manifest['limits'])
    schedule = ordered(manifest)
    if consumption.get('started_calls') != len(rows) or len(rows) > len(schedule) or any(
            row.get('planned') != planned for row, planned in zip(rows, schedule)):
        issues.append('receipts are not the unique assessment schedule prefix')
    for key in CHECKS:
        if checks.get(key) is not True:
            issues.append('mandatory owner check absent or failed: '+key)
    result = dict(schema=SCHEMA, offline_only=True, promotion_authorised=False,
                  disposition=finite.INCOMPLETE, issues=issues, raw_rows=copy.deepcopy(rows),
                  started_calls=len(rows), checks=copy.deepcopy(checks), consumption=copy.deepcopy(consumption),
                  endpoints=[], repeats=[], missing_call_ids=[p['call_id'] for p in schedule[len(rows):]],
                  source_treatment_sha256=manifest['source_treatment_sha256'],
                  assessment_register_sha256=manifest['assessment_register_sha256'])
    if issues:
        return result
    secondary_failures = []
    demonstrated_failures = []
    for endpoint_id in [*(f'endpoint-{i:02}' for i in finite.ORDER), *(REPEAT_IDS[i] for i in REPEATS)]:
        planned = [p for p in schedule if p['endpoint_id'] == endpoint_id]
        retained = rows[planned[0]['index']:planned[-1]['index']+1]
        destination = result['repeats'] if endpoint_id.startswith('repeat-') else result['endpoints']
        if len(retained) != len(planned):
            destination.append(dict(endpoint_id=endpoint_id, status='unstarted' if not retained else 'incomplete',
                                    disposition='UNSTARTED' if not retained else finite.INCOMPLETE))
            continue
        if any(not isinstance(row.get('result'), dict) or row['result'].get('status') != 0
               or row.get('gates_passed') is not True for row in retained):
            destination.append(dict(endpoint_id=endpoint_id, status='invalid', disposition=finite.INCOMPLETE))
            result['issues'].append('failed mandatory call: '+endpoint_id)
            return result
        ordinary = [dict(round=p['round'], position=p['position'],
                         arm='A' if p['arm'] == 'baseline' else 'B', result=row['result'])
                    for row in retained for p in (row['planned'],) if p['stage'] == 'ordinary']
        count = 160 if endpoint_id == 'endpoint-11' else 40
        value = analyse_endpoint(manifest, endpoint_id, ordinary, estimators[count])
        destination.append(value)
        if value['disposition'] == finite.INCOMPLETE:
            result['issues'].append('invalid fixed-count session: '+endpoint_id)
            return result
        if endpoint_id == 'endpoint-00' and value['disposition'] != finite.PASS:
            result['disposition'] = value['disposition']
            if len(rows) > planned[-1]['index']+1:
                result['issues'].append('later calls after primary stop')
                result['disposition'] = finite.INCOMPLETE
            return result
        if value['disposition'] != finite.PASS:
            secondary_failures.append(endpoint_id)
            if value['disposition'] == finite.NOT_SELECTED:
                demonstrated_failures.append(endpoint_id)
    if len(rows) == len(schedule):
        result['disposition'] = (finite.NOT_SELECTED if demonstrated_failures else
                                 finite.NOT_QUALIFIED if secondary_failures else finite.PASS)
        result['reason'] = 'all independent predicates pass' if not secondary_failures else 'secondary predicates fail: '+', '.join(secondary_failures)
    return result
