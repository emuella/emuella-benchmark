"""Offline contract and retained-observation analysis; no acquisition entry point.

The workspace owns the endpoint register and source design. A digest verifies
their identity, not their correctness or authority. No report from this module
establishes live reservation, rights, source review or resource qualification.
"""
import copy
import hashlib
import json
import math
from pathlib import Path

import precision_feasibility_analysis as analysis

SCHEMA = 'classic-forward53-finite-confirmation/v1'
V2_SCHEMA = 'classic-forward53-finite-confirmation/v2'
ORDER = (0, 2, 1, 3, 10, 11, 4, 5, 6, 7, 8, 9, *range(12, 28))
BASELINE = '975a5e734773578f61abf76d5fddfbd837f3bd7d'
CANDIDATE = 'd60859a8595554be52c8748a8e8c85b69614fea5'
PASS = 'PASSES OFFLINE GATES'
NOT_SELECTED = 'NOT SELECTED'
NOT_QUALIFIED = 'NOT QUALIFIED WITHIN BUDGET'
INCOMPLETE = 'OPERATIONALLY INCOMPLETE'
DECLINED = 'DECLINED BEFORE LAUNCH'
CHECKS = ('source_correctness', 'independent_decode', 'resources', 'output_failure',
          'identity_environment', 'reservation', 'restoration')


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def limits():
    return dict(pairs=1240, ordinary_calls=2480, preflight_calls=56, allocation_calls=112,
                total_calls=2648, wall_seconds=7200, evidence_bytes=2*1024**3,
                build_bytes=30*1024**3, call_timeout_seconds=120,
                start_headroom_seconds=150, start_headroom_bytes=1024**2)


def make_manifest(register_path, source_design_path):
    """Import the owner's complete rows; neither rewrite nor publish their data."""
    register = json.loads(Path(register_path).read_text())
    endpoints = register['endpoints']
    if (register.get('schema') != 'balanced-measurement-stability-endpoint-register/v1'
            or register.get('baseline_codec') != BASELINE or register.get('candidate_codec') != CANDIDATE
            or len(endpoints) != 28):
        raise ValueError('complete original register and frozen source identities required')
    for index, endpoint in enumerate(endpoints):
        primary = index == 0
        if (endpoint['id'] != f'endpoint-{index:02}'
                or endpoint['role'] != ('sole_primary' if primary else 'critical_non_regression')
                or endpoint['upper_relative_99'] != dict(operator='<' if primary else '<=', value=-.05 if primary else .01)
                or endpoint['absolute_mean_saving_ms'] != (dict(operator='>=', value=10) if primary else None)):
            raise ValueError('endpoint identity or mandatory gate differs')
    exceptional = endpoints[11]
    if (exceptional['operation'], exceptional['style'], exceptional['workers']) != ('encode', 1, 8) or not exceptional['case_id'].endswith('-RGB16'):
        raise ValueError('160-pair endpoint must be the registered RGB16 bypass/eight encode')
    allocation = register['unchanged_allocation_matrix']
    if (allocation['initial_calls'], allocation['conditional_calls'], allocation['styles'],
            allocation['workers'], allocation['arms']) != (32, 80, [0, 1], [1, 2, 4, 8], ['baseline', 'candidate']):
        raise ValueError('unchanged allocation matrix required')
    if len(allocation['initial_cases']) != 2 or len(allocation['conditional_cases']) != 5:
        raise ValueError('complete allocation coverage required')
    # The register orders conditional cases PAN16, RGB16, MS16, Tok, Vegas.
    prerequisites = {0: allocation['initial_cases']}
    prerequisites.update({index: [case] for index, case in zip(
        (4, 10, 12, 16, 24), allocation['conditional_cases'])})
    schedule = dict(allocation=[], preflight=[], ordinary=[], call_order=[])

    def append(stage, **fields):
        call_id = f'{stage}-{len(schedule[stage]):04}'
        row = dict(index=len(schedule['call_order']), call_id=call_id, stage=stage, **fields)
        schedule[stage].append(row)
        schedule['call_order'].append(call_id)

    pairs = [160 if i == 11 else 40 for i in range(28)]
    for index in ORDER:
        endpoint_id = endpoints[index]['id']
        for arm in ('baseline', 'candidate'):
            append('preflight', endpoint_id=endpoint_id, arm=arm)
        for case in prerequisites.get(index, []):
            for style in allocation['styles']:
                for workers in allocation['workers']:
                    for arm in allocation['arms']:
                        append('allocation', endpoint_id=endpoint_id, case_id=case,
                               style=style, workers=workers, arm=arm)
        for round_id in range(pairs[index]):
            for position, arm in enumerate(('baseline', 'candidate') if round_id % 2 == 0 else ('candidate', 'baseline')):
                append('ordinary', endpoint_id=endpoint_id, round=round_id, position=position, arm=arm)
    return dict(schema=SCHEMA, register_sha256=sha(register_path), source_design_sha256=sha(source_design_path),
                sources=dict(baseline_codec=BASELINE, candidate_codec=CANDIDATE,
                             comparator_sha256=sha(analysis.COMPARE_SOURCE)),
                endpoints=copy.deepcopy(endpoints), endpoint_order=list(ORDER),
                pairs_per_endpoint=pairs, limits=limits(), schedule=schedule)


def load_manifest(path, expected_sha256, register_path, source_design_path):
    """Verify externally pinned bytes and current owner/source binding before use."""
    if sha(path) != expected_sha256:
        raise ValueError('frozen manifest digest differs')
    manifest = json.loads(Path(path).read_text())
    if manifest != make_manifest(register_path, source_design_path):
        raise ValueError('frozen manifest, source design or comparator binding differs')
    return manifest


def endpoint_decision(session, primary):
    """Directional candidate acceptance; legacy +/-5% verdict stays separate."""
    if not session['valid'] or not session['complete']:
        return dict(disposition=INCOMPLETE, reason='complete valid fixed-count evidence is missing')
    record = session['estimator']['B_over_A']
    output = record['output']
    point = output['candidate_mean_ns']/output['baseline_mean_ns']-1
    saving = (output['baseline_mean_ns']-output['candidate_mean_ns'])/1e6
    lower, upper = record['lower'], record['upper']
    bound_pass = upper is not None and (upper < -.05 if primary else upper <= .01)
    if primary and saving < 10:
        disposition = NOT_SELECTED
        reason = 'observed mean saving is below the 10 ms absolute requirement; no slowdown is implied'
    elif bound_pass:
        disposition, reason = PASS, 'complete directional bound and applicable absolute gate pass'
    elif lower is not None and (lower >= -.05 if primary else lower > .01):
        disposition = NOT_SELECTED
        reason = ('the interval excludes the required primary gain' if primary else
                  'the interval demonstrates regression beyond the critical margin')
    else:
        disposition = NOT_QUALIFIED
        reason = 'the complete fixed-count interval does not resolve the required bound'
    return dict(disposition=disposition, reason=reason, relative_change=point,
                mean_saving_ms=saving, upper_relative_99=upper,
                baseline_mean_ns=output['baseline_mean_ns'], candidate_mean_ns=output['candidate_mean_ns'],
                relative_interval_99=output.get('relative_interval_99'),
                legacy_timing_verdict=output['verdict'])


def analyse_endpoint(index, rows, estimator):
    if type(index) is not int or index not in range(28):
        raise ValueError('registered endpoint index required')
    session = analysis.analyse_session(rows, estimator, rounds=160 if index == 11 else 40)
    return dict(endpoint_id=f'endpoint-{index:02}', status='analysed' if session['valid'] else 'invalid', analysis=session,
                **endpoint_decision(session, index == 0))


def budget_issues(consumption, *, before_start=False):
    """Pure arithmetic on retained counters, never live budget enforcement."""
    caps = limits()
    issues = []
    for key, cap in (('started_calls', caps['total_calls']), ('wall_seconds', caps['wall_seconds']),
                     ('evidence_bytes', caps['evidence_bytes']), ('build_bytes', caps['build_bytes'])):
        value = consumption.get(key)
        if (type(value) not in (int, float) or not math.isfinite(value) or value < 0
                or key != 'wall_seconds' and type(value) is not int):
            issues.append(key+' counter is missing or invalid')
            continue
        extra = dict(started_calls=1, wall_seconds=150, evidence_bytes=1024**2, build_bytes=0)[key] if before_start else 0
        if value+extra > cap:
            issues.append(key+' cap or start headroom exhausted')
    return issues


def analyse_attempt(manifest, rows, estimators, *, checks, consumption, declined_reason=None):
    """Reconcile an already verified manifest and retained prefix of call receipts.

    ``checks`` carries independently reviewed owner evidence, not self-issued
    authority. This offline function never authorises production promotion.
    Every row has ``planned`` equal to its manifest entry and an unedited
    ``result``. Ancillary results also need ``gates_passed: true`` after the
    owner checks exactness, independent receipts, queries and limits.
    """
    schedule = sorted((row for stage in ('allocation', 'preflight', 'ordinary')
                       for row in manifest['schedule'][stage]), key=lambda row: row['index'])
    if manifest['schema'] == V2_SCHEMA:
        predecessor = manifest.get('predecessor_sha256')
        if (not isinstance(predecessor, str) or len(predecessor) != 64
                or any(c not in '0123456789abcdef' for c in predecessor)
                or not isinstance(manifest.get('authority'), str) or not manifest['authority'].strip()
                or manifest.get('reservation_schema') != 'measurement-balanced-reusable-qualification/v1'
                or manifest.get('condition') != 'balanced-reusable'):
            raise ValueError('explicit verified v2 predecessor, authority and condition required')
    if manifest['schema'] not in (SCHEMA, V2_SCHEMA) or manifest['limits'] != limits() or len(schedule) != 2648:
        raise ValueError('verified finite manifest required')
    issues = budget_issues(consumption)
    if consumption.get('started_calls') != len(rows):
        issues.append('start count differs from retained receipt count')
    if len(rows) > len(schedule) or any(row.get('planned') != plan for row, plan in zip(rows, schedule)):
        issues.append('receipts are not the unique frozen schedule prefix')
    observed_endpoints = {row.get('planned', {}).get('endpoint_id') for row in rows}
    observed_call_ids = {row.get('planned', {}).get('call_id') for row in rows}
    result = dict(schema=manifest['schema'], offline_only=True, promotion_authorised=False,
                  disposition=INCOMPLETE, raw_rows=copy.deepcopy(rows), issues=issues,
                  started_calls=consumption.get('started_calls'),
                  endpoints=[dict(endpoint_id=f'endpoint-{i:02}',
                                  status='not_analysed' if f'endpoint-{i:02}' in observed_endpoints else 'unstarted',
                                  disposition='NOT ANALYSED' if f'endpoint-{i:02}' in observed_endpoints else 'UNSTARTED',
                                  baseline_mean_ns=None, candidate_mean_ns=None, relative_interval_99=None) for i in ORDER],
                  missing_call_ids=[row['call_id'] for row in schedule if row['call_id'] not in observed_call_ids],
                  checks=copy.deepcopy(checks), consumption=copy.deepcopy(consumption))
    if manifest['schema'] == V2_SCHEMA:
        result.update(predecessor_sha256=manifest['predecessor_sha256'], authority=manifest['authority'],
                      reservation_schema=manifest['reservation_schema'], condition=manifest['condition'])
    if declined_reason is not None:
        if rows or consumption.get('started_calls') != 0:
            raise ValueError('declined before launch requires zero starts')
        result.update(disposition=DECLINED, reason=declined_reason)
        return result
    if issues:
        return result
    for key in CHECKS:
        if checks.get(key) is not True:
            issues.append('mandatory owner check absent or failed: '+key)
    if issues:
        return result
    for position, index in enumerate(ORDER):
        endpoint_id = f'endpoint-{index:02}'
        planned = [row for row in schedule if row['endpoint_id'] == endpoint_id]
        retained = rows[planned[0]['index']:planned[-1]['index']+1]
        ancillary = [row for row in retained if row['planned']['stage'] != 'ordinary']
        if len(retained) != len(planned) or any(
                not isinstance(row.get('result'), dict)
                or type(row['result'].get('status')) is not int or row['result']['status'] != 0
                or row.get('gates_passed') is not True for row in ancillary):
            result['endpoints'][position].update(disposition=INCOMPLETE)
            result['reason'] = 'missing or failed mandatory calls; all retained rows preserved'
            return result
        ordinary = []
        for row in retained:
            plan = row['planned']
            if plan['stage'] == 'ordinary':
                ordinary.append(dict(round=plan['round'], arm='A' if plan['arm'] == 'baseline' else 'B',
                                     position=plan['position'], result=row.get('result')))
        decision = analyse_endpoint(index, ordinary, estimators[160 if index == 11 else 40])
        result['endpoints'][position] = decision
        if decision['disposition'] != PASS:
            result.update(disposition=decision['disposition'], reason=decision['reason'])
            if len(rows) > planned[-1]['index']+1:
                issues.append('later calls exist after a stopping endpoint; no later inference')
                result['disposition'] = INCOMPLETE
            return result
    result.update(disposition=PASS, reason='all offline gates pass; live bindings and independent evidence still govern qualification')
    return result
