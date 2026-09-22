"""Offline, session-local analysis for precision-feasibility-v1.

The executable estimator owns inference. The arithmetic below supplies descriptive
diagnostics and explicitly conditional planning projections, never extra trials.
"""

import copy
import hashlib
import json
import math
from pathlib import Path
import re
import statistics
import subprocess


ROUNDS = 20
PROJECTION_COUNTS = (20, 40, 80, 160)
COMPARE_SOURCE = Path(__file__).resolve().parents[1] / "src/compare.rs"
CRITICAL_BUCKETS = (
    ("0..=4", 5.598), ("5", 4.774), ("6", 4.317), ("7", 4.030),
    ("8", 3.833), ("9", 3.690), ("10..=14", 3.582), ("15..=19", 3.287),
    ("20..=29", 3.154), ("30..=59", 3.030), ("60..=119", 2.915), ("_", 2.860),
)
DEMONSTRATED = "demonstrated in this limited study"
NOT_DEMONSTRATED = "not consistently demonstrated"
INCOMPLETE = "incomplete/uninterpretable"


def critical_buckets(source=COMPARE_SOURCE):
    """Fail closed if the actual comparator's critical-value table has changed."""
    text = Path(source).read_text()
    match = re.search(r"let t = match values\.len\(\) - 1\s*\{([^}]+)\}", text)
    if match is None:
        raise ValueError("cannot locate comparator critical-value buckets")
    entries = tuple((key, float(value)) for key, value in re.findall(
        r"(\d+\.\.=\d+|\d+|_)\s*=>\s*(\d+\.\d+)\s*,", match[1]))
    if entries != CRITICAL_BUCKETS:
        raise ValueError("comparator critical-value buckets differ; projection parity needs review")
    return entries


def critical_value(n, source=COMPARE_SOURCE):
    if type(n) is not int or n < 2:
        raise ValueError("a sample count of at least two is required")
    df = n - 1
    for key, value in critical_buckets(source):
        if key == "_":
            return value
        bounds = [int(x) for x in key.split("..=")]
        if bounds[0] <= df <= bounds[-1]:
            return value
    raise ValueError("uncovered degrees of freedom")


def _number(value):
    return type(value) in (int, float) and math.isfinite(value)


def interval_metrics(bounds):
    """Relative values are fractions; upper < threshold excludes that slowdown."""
    if bounds is None:
        return dict(lower=None, upper=None, width=None, half_width=None,
                    contains_zero=False, excludes_positive={"1%": False, "2%": False, "5%": False})
    if (not isinstance(bounds, (list, tuple)) or len(bounds) != 2
            or not all(_number(v) for v in bounds) or bounds[0] > bounds[1]):
        raise ValueError("malformed estimator interval")
    lower, upper = bounds
    return dict(lower=lower, upper=upper, width=upper-lower, half_width=(upper-lower)/2,
                contains_zero=lower <= 0 <= upper,
                excludes_positive={label: upper < threshold
                                   for label, threshold in (("1%", .01), ("2%", .02), ("5%", .05))})


def _summary(values):
    mean = statistics.mean(values)
    sd = statistics.stdev(values) if len(values) > 1 else None
    return dict(count=len(values), mean_ns=mean, sample_sd_ns=sd,
                sample_cv=sd/mean if sd is not None and mean != 0 else None)


def _covariance(xs, ys):
    xmean, ymean = statistics.mean(xs), statistics.mean(ys)
    return sum((x-xmean)*(y-ymean) for x, y in zip(xs, ys)) / (len(xs)-1)


def _correlation(xs, ys):
    if len(xs) < 2:
        return None
    denominator = statistics.stdev(xs)*statistics.stdev(ys)
    return _covariance(xs, ys)/denominator if denominator else None


def _trend(xs, ys):
    """Ordinary descriptive slope, with no significance or independence claim."""
    variance = statistics.variance(xs) if len(xs) > 1 else 0
    return dict(slope_ns_per_unit=_covariance(xs, ys)/variance if variance else None,
                correlation=_correlation(xs, ys))


def _order_group(a, b, rounds):
    xs, ys = [a[r] for r in rounds], [b[r] for r in rounds]
    return dict(rounds=list(rounds), A=_summary(xs), B=_summary(ys),
                B_over_A=statistics.mean(ys)/statistics.mean(xs)-1,
                mean_pair_relative_change=statistics.mean(y/x-1 for x, y in zip(xs, ys)))


def diagnostics(a, b, rows):
    rounds = len(a)
    vectors = {"A": a, "B": b}
    ordered = [vectors[row["arm"]][row["round"]] for row in rows]
    first, second = ordered[::2], ordered[1::2]
    arms = {}
    for arm, values in (("A", a), ("B", b)):
        execution_indices = [index for index, row in enumerate(rows) if row["arm"] == arm]
        arms[arm] = dict(_summary(values), ordered_ns=values,
                         lag1_correlation=_correlation(values[:-1], values[1:]),
                         round_trend=_trend(list(range(rounds)), values),
                         execution_order_trend=_trend(execution_indices, values))
    result = dict(
        interpretation="Descriptive only; no significance, independence, stationarity or coverage claim.",
        arms=arms, sample_covariance_ns2=_covariance(a, b), correlation=_correlation(a, b),
        acquisition_order_ns=ordered, acquisition_lag1_correlation=_correlation(ordered[:-1], ordered[1:]),
        acquisition_order_trend=_trend(list(range(2*rounds)), ordered),
        order_groups={order: _order_group(a, b, [row["round"] for row in rows[::2] if row["arm"] == order[0]])
                      for order in ("AB", "BA")},
        position=dict(first=_summary(first), second=_summary(second),
                      second_over_first=statistics.mean(second)/statistics.mean(first)-1),
    )
    # The driver may supply monotonic call-start times. Missing clocks do not
    # invalidate acquisition; ordinal trends remain available and labelled.
    times = [row.get("started_monotonic_ns") for row in rows]
    if all(_number(t) for t in times) and len(set(times)) > 1:
        origin = times[0]
        result["elapsed_time_trend"] = _trend([(t-origin)/1e9 for t in times], ordered)
        result["elapsed_time_trend"]["unit"] = "second since first call start"
        for arm, values in (("A", a), ("B", b)):
            arm_times = [(row["started_monotonic_ns"]-origin)/1e9 for row in rows if row["arm"] == arm]
            arms[arm]["elapsed_time_trend"] = dict(_trend(arm_times, values), unit="second since first call start")
    else:
        result["elapsed_time_trend"] = None
        for arm in arms.values():
            arm["elapsed_time_trend"] = None
    return result


def _project(mean_a, mean_b, sd_a, sd_b, n, q):
    margin_a, margin_b = q*sd_a/math.sqrt(n), q*sd_b/math.sqrt(n)
    def direction(x, y, mx, my):
        bounds = None if x-mx <= 0 or y-my <= 0 else [(y-my)/(x+mx)-1, (y+my)/(x-mx)-1]
        return dict(relative_change=y/x-1, relative_interval_99=bounds, **interval_metrics(bounds))
    return {"B_over_A": direction(mean_a, mean_b, margin_a, margin_b),
            "A_over_B": direction(mean_b, mean_a, margin_b, margin_a)}


def planning_projections(a, b, source=COMPARE_SOURCE):
    """Plug-in planning only: fixed observed SD, iid scaling and no new samples."""
    sa, sb = _summary(a), _summary(b)
    common = (sa["mean_ns"] + sb["mean_ns"])/2
    values = []
    for n in PROJECTION_COUNTS:
        q = critical_value(n, source)
        values.append(dict(
            n_per_arm=n, degrees_of_freedom=n-1, critical_value=q,
            zero_effect_centre=_project(common, common, sa["sample_sd_ns"], sb["sample_sd_ns"], n, q),
            observed_displacement=_project(sa["mean_ns"], sb["mean_ns"], sa["sample_sd_ns"], sb["sample_sd_ns"], n, q),
        ))
    return dict(
        interpretation="Conditional planning projections, not measured precision or evidence that more batches cure bias or dependence.",
        assumptions="Observed sample SDs held fixed; independent stationary batch means and Student-t model; no duplicated or simulated observations.",
        comparator_source_sha256=hashlib.sha256(Path(source).read_bytes()).hexdigest(),
        common_mean_ns=common, observed_arm_summaries={"A": sa, "B": sb}, values=values,
    )


def _estimate(estimator, a, b):
    payload = dict(baseline=a, candidate=b)
    record = dict(input=payload)
    try:
        if callable(estimator):
            output = estimator(copy.deepcopy(payload))
        else:
            process = subprocess.run([str(estimator)], input=json.dumps(payload),
                                     text=True, capture_output=True, timeout=60)
            record.update(returncode=process.returncode, stdout=process.stdout, stderr=process.stderr)
            if process.returncode:
                raise ValueError("estimator exited unsuccessfully")
            output = json.loads(process.stdout)
        record["output"] = output
        if not isinstance(output, dict) or output.get("verdict") not in (
                "improved", "regressed", "equivalent", "inconclusive"):
            raise ValueError("malformed estimator result")
        for key in ("baseline_mean_ns", "candidate_mean_ns"):
            if not _number(output.get(key)) or output[key] <= 0:
                raise ValueError("malformed estimator mean")
        record.update(interval_metrics(output.get("relative_interval_99")))
        record["valid"] = True
    except (OSError, ValueError, TypeError, subprocess.TimeoutExpired) as error:
        record.update(valid=False, error=str(error))
        if isinstance(error, subprocess.TimeoutExpired):
            record.update(stdout=_text(error.stdout), stderr=_text(error.stderr))
    return record


def _text(value):
    return value.decode(errors="replace") if isinstance(value, bytes) else value


def analyse_session(rows, estimator, valid=True, rounds=ROUNDS):
    """Analyse exactly one fixed-size AB/BA session; never pool sessions.

    Raw records survive every failure. Canonical vectors use None for a missing,
    failed or ambiguous arm/round, and no successful subset reaches the estimator.
    The starting arm is inferred from the first round-zero, position-zero row.
    The caller supplies identity/environment validity through ``valid``.
    """
    if type(rounds) is not int or rounds not in (20, 40, 160):
        raise ValueError("only fixed twenty-, forty- or 160-pair sessions are supported")
    result = dict(complete=False, valid=False, issues=[], raw_rows=copy.deepcopy(rows),
                  vectors_ns={"A": [None]*rounds, "B": [None]*rounds},
                  estimator={}, diagnostics=None, projections=None)
    issues = result["issues"]
    if valid is not True:
        issues.append("session identity/environment validity was not established")
    if not isinstance(rows, list):
        issues.append("rows must be a list")
        return result
    if len(rows) != 2*rounds:
        issues.append(f"session requires exactly {2*rounds} observations")
    first = rows[0] if rows and isinstance(rows[0], dict) else {}
    starting_arm = first.get("arm")
    if (starting_arm not in ("A", "B") or type(first.get("round")) is not int or first["round"] != 0
            or type(first.get("position")) is not int or first["position"] != 0):
        starting_arm = None
        issues.append("first observation must declare round zero, position zero and a valid starting arm")
    result["starting_arm"] = starting_arm
    indexed = {}
    for index, row in enumerate(rows):
        if not isinstance(row, dict):
            issues.append(f"row {index}: expected an object")
            continue
        r, arm, position = row.get("round"), row.get("arm"), row.get("position")
        if type(r) is not int or r not in range(rounds) or arm not in ("A", "B"):
            issues.append(f"row {index}: invalid round/arm identity")
            continue
        key = (r, arm)
        indexed.setdefault(key, []).append(row)
        expected_position = int((arm != starting_arm) == (r % 2 == 0))
        if (type(position) is not int or position != expected_position
                or index != 2*r + expected_position):
            issues.append(f"row {index}: acquisition does not match adjacent alternating AB/BA order")
    expected = {(r, arm) for r in range(rounds) for arm in ("A", "B")}
    coverage = set(indexed) == expected and all(len(v) == 1 for v in indexed.values()) and len(rows) == 2*rounds
    result["complete"] = coverage
    if not coverage:
        issues.append("missing, duplicate or extra session observations")
    for (r, arm), records in indexed.items():
        if len(records) != 1:
            continue
        observation = records[0].get("result")
        if not isinstance(observation, dict):
            issues.append(f"{arm}/{r}: missing process result")
            continue
        value = observation.get("observation")
        samples = value.get("samples_ns") if isinstance(value, dict) else None
        if (type(observation.get("status")) is not int or observation["status"] != 0
                or not isinstance(value, dict) or value.get("exact") is not True
                or value.get("diagnostic_sampling") is True
                or value.get("execution_diagnostic") is not None or value.get("allocation_diagnostic") is not None
                or not isinstance(samples, list) or len(samples) != 1
                or type(samples[0]) is not int or not 0 < samples[0] <= 2**64-1):
            issues.append(f"{arm}/{r}: failed or invalid timing observation")
            continue
        result["vectors_ns"][arm][r] = samples[0]
    if issues:
        return result
    a, b = result["vectors_ns"]["A"], result["vectors_ns"]["B"]
    result["estimator"] = {"B_over_A": _estimate(estimator, a, b),
                           "A_over_B": _estimate(estimator, b, a)}
    result["diagnostics"] = diagnostics(a, b, rows)
    try:
        result["projections"] = planning_projections(a, b)
    except ValueError as error:
        issues.append(str(error))
    if not all(direction["valid"] for direction in result["estimator"].values()):
        issues.append("one or both estimator invocations failed")
    result["valid"] = not issues
    return result


def classify_cell(sessions):
    """Three separate sessions, both label directions, width AND centring."""
    if (len(sessions) != 3 or any(not s.get("complete") or not s.get("valid") for s in sessions)):
        return INCOMPLETE
    for session in sessions:
        for label in ("B_over_A", "A_over_B"):
            direction = session.get("estimator", {}).get(label)
            if not direction or not direction.get("valid"):
                return INCOMPLETE
    if all(session["estimator"][label]["contains_zero"]
           and session["estimator"][label]["excludes_positive"]["1%"]
           for session in sessions for label in ("B_over_A", "A_over_B")):
        return DEMONSTRATED
    return NOT_DEMONSTRATED
