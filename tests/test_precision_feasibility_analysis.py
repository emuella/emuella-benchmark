"""Authored arithmetic only: no codec workloads or measurement claims."""

import importlib.util
import json
import math
import os
from pathlib import Path
import statistics
import tempfile
import unittest
from unittest.mock import Mock


SPEC = importlib.util.spec_from_file_location(
    "precision_analysis", Path(__file__).resolve().parents[1] / "scripts/precision_feasibility_analysis.py")
analysis = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(analysis)


def rows(a=None, b=None, starting_arm="A"):
    a = a if a is not None else [1_000_000]*20
    b = b if b is not None else a
    initial_order = "AB" if starting_arm == "A" else "BA"
    return [dict(round=r, arm=arm, position=position, started_monotonic_ns=(2*r+position)*1_000_000_000,
                 result=dict(status=0, observation=dict(exact=True, samples_ns=[{"A": a, "B": b}[arm][r]])))
            for r in range(20) for position, arm in enumerate(initial_order if r % 2 == 0 else initial_order[::-1])]


def authored_estimator(payload):
    """Independent fixed-n arithmetic mock; optional real executable tested below."""
    a, b = payload["baseline"], payload["candidate"]
    if len(a) != 20 or len(b) != 20:
        raise ValueError("mock only admits the unchanged twenty-sample input")
    x, y = statistics.mean(a), statistics.mean(b)
    mx, my = (3.287*statistics.stdev(v)/math.sqrt(20) for v in (a, b))
    result = dict(baseline_mean_ns=x, candidate_mean_ns=y, verdict="inconclusive", preserved_field="unchanged")
    if x-mx > 0 and y-my > 0:
        lower, upper = (y-my)/(x+mx)-1, (y+my)/(x-mx)-1
        result.update(relative_change=y/x-1, relative_interval_99=[lower, upper])
        if lower > .05:
            result["verdict"] = "regressed"
        elif upper < -.05:
            result["verdict"] = "improved"
        elif lower >= -.05 and upper <= .05:
            result["verdict"] = "equivalent"
    return result


class FeasibilityTests(unittest.TestCase):
    def analyse(self, values=None, candidate=None, **kwargs):
        return analysis.analyse_session(rows(values, candidate), authored_estimator, **kwargs)

    def test_precise_null_requires_both_directions_in_three_separate_sessions(self):
        values = [999_000, 1_001_000]*10
        estimator = Mock(side_effect=authored_estimator)
        session = analysis.analyse_session(rows(values), estimator)
        self.assertTrue(session["complete"])
        self.assertTrue(session["valid"])
        self.assertEqual(estimator.call_count, 2)
        self.assertEqual(session["vectors_ns"], dict(A=values, B=values))
        for direction in session["estimator"].values():
            self.assertTrue(direction["contains_zero"])
            self.assertLess(direction["width"], .02)
            self.assertTrue(all(direction["excludes_positive"].values()))
            self.assertEqual(direction["output"]["preserved_field"], "unchanged")
        self.assertEqual(analysis.classify_cell([session, session, session]), analysis.DEMONSTRATED)
        for count in (0, 1, 2, 4):
            self.assertEqual(analysis.classify_cell([session]*count), analysis.INCOMPLETE)

    def test_wide_null_is_complete_but_not_demonstrated(self):
        session = self.analyse([800_000, 1_200_000]*10)
        self.assertTrue(session["valid"])
        self.assertTrue(session["estimator"]["B_over_A"]["contains_zero"])
        self.assertFalse(session["estimator"]["B_over_A"]["excludes_positive"]["5%"])
        self.assertEqual(analysis.classify_cell([session]*3), analysis.NOT_DEMONSTRATED)

    def test_narrow_displaced_null_fails_centring(self):
        session = self.analyse([1_000_000]*20, [1_004_000]*20)
        for direction in session["estimator"].values():
            self.assertEqual(direction["width"], 0)
            self.assertTrue(direction["excludes_positive"]["1%"])
            self.assertFalse(direction["contains_zero"])
        self.assertEqual(analysis.classify_cell([session]*3), analysis.NOT_DEMONSTRATED)

    def test_direction_reversal_is_inverse_ratio_not_negation(self):
        a, b = [1_000_000]*20, [1_100_000]*20
        estimator = Mock(side_effect=authored_estimator)
        session = analysis.analyse_session(rows(a, b), estimator)
        self.assertEqual(estimator.call_args_list[0].args[0], dict(baseline=a, candidate=b))
        self.assertEqual(estimator.call_args_list[1].args[0], dict(baseline=b, candidate=a))
        forward = session["estimator"]["B_over_A"]["output"]["relative_change"]
        reverse = session["estimator"]["A_over_B"]["output"]["relative_change"]
        self.assertAlmostEqual(reverse, 1/(1+forward)-1)
        self.assertNotAlmostEqual(reverse, -forward)

    def test_session_displacement_cannot_be_hidden_by_pooling(self):
        a = [1_000_000]*20
        sessions = [self.analyse(a, [centre]*20) for centre in (990_000, 1_000_000, 1_010_000)]
        self.assertEqual(analysis.classify_cell(sessions), analysis.NOT_DEMONSTRATED)
        self.assertEqual([s["vectors_ns"]["B"][0] for s in sessions], [990_000, 1_000_000, 1_010_000])
        self.assertTrue(all(len(d["input"]["baseline"]) == 20 for s in sessions for d in s["estimator"].values()))

    def test_order_and_position_diagnostics_keep_ratio_estimands_distinct(self):
        a = [1_000_000, 1_020_000]*10
        b = [1_020_000, 1_000_000]*10
        session = self.analyse(a, b)
        diagnostic = session["diagnostics"]
        self.assertAlmostEqual(diagnostic["position"]["second_over_first"], .02)
        self.assertAlmostEqual(diagnostic["order_groups"]["AB"]["B_over_A"], .02)
        self.assertAlmostEqual(diagnostic["order_groups"]["BA"]["B_over_A"], 1/1.02-1)
        self.assertAlmostEqual(diagnostic["correlation"], -1)
        self.assertEqual(diagnostic["acquisition_order_ns"], [1_000_000, 1_020_000]*20)
        self.assertAlmostEqual(diagnostic["arms"]["A"]["lag1_correlation"], -1)
        # Arithmetic arm means must not be replaced by averaged pair percentages.
        a = [1_000_000, 2_000_000, 3_000_000, 2_000_000]*5
        b = [900_000, 2_000_000, 3_000_000, 2_000_000]*5
        group = self.analyse(a, b)["diagnostics"]["order_groups"]["AB"]
        self.assertAlmostEqual(group["B_over_A"], -.025)
        self.assertAlmostEqual(group["mean_pair_relative_change"], -.05)

    def test_sample_sd_covariance_and_trends_are_descriptive(self):
        a = [1_000_000 + r*1000 for r in range(20)]
        session = self.analyse(a, [v+200 for v in a])
        diagnostic = session["diagnostics"]
        self.assertAlmostEqual(diagnostic["arms"]["A"]["sample_sd_ns"], statistics.stdev(a))
        self.assertAlmostEqual(diagnostic["sample_covariance_ns2"], statistics.variance(a))
        self.assertAlmostEqual(diagnostic["arms"]["A"]["round_trend"]["slope_ns_per_unit"], 1000)
        self.assertIsNotNone(diagnostic["elapsed_time_trend"])
        self.assertIn("Descriptive only", diagnostic["interpretation"])
        self.assertIsNone(self.analyse()["diagnostics"]["correlation"])

    def test_ba_start_preserves_actual_position_and_order_groups(self):
        a, b = [1_020_000, 1_000_000]*10, [1_000_000, 1_020_000]*10
        session = analysis.analyse_session(rows(a, b, "B"), authored_estimator)
        self.assertTrue(session["valid"], session["issues"])
        self.assertEqual(session["starting_arm"], "B")
        diagnostic = session["diagnostics"]
        self.assertEqual(diagnostic["acquisition_order_ns"], [1_000_000, 1_020_000]*20)
        self.assertAlmostEqual(diagnostic["position"]["second_over_first"], .02)
        self.assertEqual(diagnostic["order_groups"]["BA"]["rounds"], list(range(0, 20, 2)))
        self.assertEqual(diagnostic["order_groups"]["AB"]["rounds"], list(range(1, 20, 2)))
        self.assertAlmostEqual(diagnostic["order_groups"]["AB"]["B_over_A"], .02)
        self.assertAlmostEqual(diagnostic["order_groups"]["BA"]["B_over_A"], 1/1.02-1)
        indices_a = [2*r+int(r % 2 == 0) for r in range(20)]
        expected_slope = statistics.covariance(indices_a, a)/statistics.variance(indices_a)
        self.assertAlmostEqual(diagnostic["arms"]["A"]["execution_order_trend"]["slope_ns_per_unit"], expected_slope)

    def test_relabelling_swaps_directions_without_changing_acquisition_diagnostics(self):
        a, b = [1_000_000+r*1000 for r in range(20)], [1_020_000+r*1000 for r in range(20)]
        forward = analysis.analyse_session(rows(a, b, "A"), authored_estimator)
        reversed_labels = analysis.analyse_session(rows(b, a, "B"), authored_estimator)
        self.assertTrue(reversed_labels["valid"])
        self.assertEqual(forward["estimator"]["B_over_A"], reversed_labels["estimator"]["A_over_B"])
        for key in ("acquisition_order_ns", "position", "acquisition_order_trend", "elapsed_time_trend"):
            self.assertEqual(forward["diagnostics"][key], reversed_labels["diagnostics"][key])
        self.assertEqual(forward["diagnostics"]["order_groups"]["AB"]["rounds"],
                         reversed_labels["diagnostics"]["order_groups"]["BA"]["rounds"])

    def test_failures_missing_duplicates_invalid_order_and_samples_preserve_rows(self):
        cases = []
        cases.append(rows()[:-1])
        cases.append(rows()+[rows()[0]])
        wrong = rows(); wrong[0], wrong[1] = wrong[1], wrong[0]; cases.append(wrong)
        for delta in (dict(status="timeout"), dict(status=1), dict(status=False),
                      dict(observation=dict(exact=False, samples_ns=[1])),
                      dict(observation=dict(exact=True, samples_ns=[1, 2])),
                      dict(observation=dict(exact=True, samples_ns=[True])),
                      dict(observation=dict(exact=True, samples_ns=[0])),
                      dict(observation=dict(exact=True, samples_ns=[2**64])),
                      dict(observation=dict(exact=True, samples_ns=[1], diagnostic_sampling=True)),
                      dict(observation=dict(exact=True, samples_ns=[1], execution_diagnostic={}))):
            changed = rows(); changed[0]["result"].update(delta); cases.append(changed)
        for field, value in (("round", True), ("round", 20), ("arm", "C"), ("position", False)):
            changed = rows(); changed[0][field] = value; cases.append(changed)
        for records in cases:
            with self.subTest(first=records[0]):
                estimator = Mock()
                result = analysis.analyse_session(records, estimator)
                self.assertEqual(result["raw_rows"], records)
                self.assertFalse(result["valid"])
                estimator.assert_not_called()
                self.assertEqual(analysis.classify_cell([result]*3), analysis.INCOMPLETE)
                self.assertEqual(len(result["vectors_ns"]["A"]), 20)
                json.dumps(result, allow_nan=False)
        failed = rows(); failed[0]["result"]["status"] = "timeout"
        self.assertIsNone(analysis.analyse_session(failed, Mock())["vectors_ns"]["A"][0])
        estimator = Mock()
        self.assertFalse(analysis.analyse_session(rows(), estimator, valid=False)["valid"])
        estimator.assert_not_called()

    def test_unbounded_estimator_is_valid_inconclusive_not_precision(self):
        session = self.analyse([1]*19+[20_000_000], [1_000_000]*20)
        self.assertTrue(session["valid"])
        self.assertIsNone(session["estimator"]["B_over_A"]["upper"])
        self.assertEqual(analysis.classify_cell([session]*3), analysis.NOT_DEMONSTRATED)

    def test_estimator_failure_keeps_both_invocations_and_full_output(self):
        invalid = dict(verdict="inconclusive", baseline_mean_ns=1, candidate_mean_ns=1,
                       relative_interval_99=[2, 1], details={"retained": True})
        estimator = Mock(side_effect=[invalid, authored_estimator(dict(baseline=[1]*20, candidate=[1]*20))])
        session = analysis.analyse_session(rows(), estimator)
        self.assertEqual(estimator.call_count, 2)
        self.assertFalse(session["valid"])
        self.assertEqual(session["estimator"]["B_over_A"]["output"], invalid)
        self.assertTrue(session["estimator"]["A_over_B"]["valid"])

    def test_threshold_equality_does_not_exclude_positive_effect(self):
        metrics = analysis.interval_metrics([-.001, .01])
        self.assertFalse(metrics["excludes_positive"]["1%"])
        self.assertTrue(metrics["excludes_positive"]["2%"])


class ProjectionTests(unittest.TestCase):
    def test_real_bucket_boundaries_and_source_parity(self):
        for n, q in ((5, 5.598), (6, 4.774), (20, 3.287), (21, 3.154),
                     (30, 3.154), (31, 3.030), (40, 3.030), (60, 3.030),
                     (61, 2.915), (80, 2.915), (120, 2.915), (121, 2.860), (160, 2.860)):
            self.assertEqual(analysis.critical_value(n), q)
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory)/"compare.rs"
            source.write_text(analysis.COMPARE_SOURCE.read_text().replace("15..=19 => 3.287", "15..=19 => 3.288"))
            with self.assertRaisesRegex(ValueError, "parity"):
                analysis.critical_value(20, source)

    def test_zero_effect_projection_uses_common_mean_and_separate_observed_sds(self):
        a, b = [999_000, 1_001_000]*10, [1_008_000, 1_012_000]*10
        projected = analysis.planning_projections(a, b)
        self.assertEqual(projected["common_mean_ns"], 1_005_000)
        self.assertEqual([v["n_per_arm"] for v in projected["values"]], [20, 40, 80, 160])
        self.assertEqual([v["critical_value"] for v in projected["values"]], [3.287, 3.030, 2.915, 2.860])
        point = projected["values"][0]
        self.assertEqual(point["zero_effect_centre"]["B_over_A"]["relative_change"], 0)
        self.assertAlmostEqual(point["observed_displacement"]["B_over_A"]["relative_change"], .01)
        mx, my = (3.287*statistics.stdev(v)/math.sqrt(20) for v in (a, b))
        self.assertAlmostEqual(point["zero_effect_centre"]["B_over_A"]["upper"], (1_005_000+my)/(1_005_000-mx)-1)
        self.assertEqual(point["observed_displacement"]["B_over_A"]["relative_interval_99"],
                         authored_estimator(dict(baseline=a, candidate=b))["relative_interval_99"])
        widths = [p["zero_effect_centre"]["B_over_A"]["width"] for p in projected["values"]]
        self.assertEqual(widths, sorted(widths, reverse=True))

    @unittest.skipUnless(os.environ.get("PRECISION_ESTIMATOR"), "parent supplies existing comparator executable for integration")
    def test_twenty_sample_projection_matches_actual_unchanged_estimator(self):
        a, b = [999_000, 1_001_000]*10, [1_008_000, 1_012_000]*10
        session = analysis.analyse_session(rows(a, b), Path(os.environ["PRECISION_ESTIMATOR"]))
        self.assertTrue(session["valid"], session["issues"])
        projection = session["projections"]["values"][0]["observed_displacement"]
        for label in ("B_over_A", "A_over_B"):
            record = session["estimator"][label]
            self.assertEqual(record["returncode"], 0)
            self.assertEqual(json.loads(record["stdout"]), record["output"])
            for actual, expected in zip(record["output"]["relative_interval_99"], projection[label]["relative_interval_99"]):
                self.assertAlmostEqual(actual, expected, places=12)


if __name__ == "__main__":
    unittest.main()
