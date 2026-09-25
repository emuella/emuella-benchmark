"""Authored treatment admission and historical reconstruction; no corpus calls."""
import copy
import hashlib
import json
from pathlib import Path
import re
import tempfile
import unittest
from unittest.mock import patch

import test_finite_confirmation_analysis as authored
import test_finite_confirmation_live as acquisition
import test_finite_confirmation_repairs as retained
import finite_confirmation_live as live
import finite_confirmation_report as report


def source_fixture(root):
    source = dict(schema='classic-forward53-parallel-dispatch-source/v1',
        recorded_production_codec=live.finite.BASELINE, baseline_codec=live.finite.DISPATCH_BASELINE,
        donor_codec=live.finite.CANDIDATE, candidate_codec='c'*40,
        baseline_tree='a'*40, donor_tree='b'*40, candidate_tree='d'*40,
        production_to_candidate_diff_sha256='a'*64, donor_to_candidate_diff_sha256='b'*64,
        recorded_to_baseline_diff_sha256='c'*64)
    review = dict(schema='classic-forward53-parallel-dispatch-source-review/v1', verdict='PASS',
        reviewer='independent authored reviewer', locator='authored review',
        sources={k:source[k] for k in live.finite.SOURCE_FIELDS})
    path = root/'review.json'; path.write_text(json.dumps(review))
    source['independent_review'] = dict(path=str(path), sha256=live.sha(path))
    path = root/'source.json'; path.write_text(json.dumps(source))
    return source, review, path


class DispatchTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(); self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.register = self.root/'register.json'; self.design = self.root/'design.json'; self.v1 = self.root/'v1.json'
        self.register.write_text(json.dumps(authored.register())); self.design.write_text('{}')
        self.original = live.finite.make_manifest(self.register, self.design)
        self.v1.write_text(json.dumps(self.original))
        self.source, self.review, self.path = source_fixture(self.root)
        self.contract = self.derive()

    def derive(self, source=None, review=None):
        text = json.dumps(source or self.source)
        return live.derive_dispatch(self.v1, live.sha(self.v1), self.register, self.design,
            'separate new treatment authority', text, hashlib.sha256(text.encode()).hexdigest(),
            json.dumps(review or self.review))

    def test_exact_inherited_design_and_explicit_new_identity(self):
        before = self.v1.read_bytes()
        for key, value in self.original.items():
            if key not in ('schema', 'sources'):
                self.assertEqual(self.contract[key], value)
        self.assertEqual(self.contract['sources'], dict(self.original['sources'],
            baseline_codec=live.finite.DISPATCH_BASELINE, candidate_codec=self.source['candidate_codec']))
        self.assertEqual(self.contract['schema'], 'classic-forward53-parallel-dispatch/v1')
        self.assertEqual(live.preparation_schema(self.contract), live.DISPATCH_PREPARATION)
        self.assertEqual(self.v1.read_bytes(), before)
        self.assertEqual(len(live.ordered(self.contract)), 2648)
        self.assertEqual(self.contract['pairs_per_endpoint'][11], 160)
        self.assertEqual(self.contract['pairs_per_endpoint'][10], 40)
        old = live.derive(self.v1, live.sha(self.v1), self.register, self.design, 'old authority')
        self.assertEqual(old['sources'], self.original['sources'])
        self.assertNotIn('source_treatment_text', old)

    def test_pinned_receipt_review_and_sources_fail_closed(self):
        for key in live.finite.SOURCE_FIELDS:
            changed = copy.deepcopy(self.source); changed[key] = '0' * len(changed[key])
            with self.subTest(key=key), self.assertRaises(ValueError): self.derive(changed)
        for key, value in [('verdict', 'FAIL'), ('reviewer', ''), ('locator', ''), ('sources', {})]:
            review = dict(self.review, **{key:value})
            source = copy.deepcopy(self.source)
            source['independent_review']['sha256'] = hashlib.sha256(json.dumps(review).encode()).hexdigest()
            with self.subTest(key=key), self.assertRaises(ValueError): self.derive(source, review)
        with self.assertRaisesRegex(ValueError, 'digest'):
            live.source_texts(self.path, '0'*64)
        changed = dict(self.contract, source_treatment_text=self.contract['source_treatment_text']+' ')
        with self.assertRaisesRegex(ValueError, 'digest'): live.finite.dispatch_source(changed)

    def test_old_and_new_schema_cannot_masquerade_as_each_other(self):
        for schema in (live.finite.SCHEMA, live.SCHEMA):
            with self.subTest(schema=schema), self.assertRaisesRegex(ValueError, 'distinct schema'):
                live.finite.analyse_attempt(dict(self.contract, schema=schema), [], {}, checks={}, consumption={})
        old = live.derive(self.v1, live.sha(self.v1), self.register, self.design, 'old authority')
        with self.assertRaises((KeyError, ValueError)):
            live.finite.analyse_attempt(dict(old, schema=live.finite.DISPATCH_SCHEMA), [], {}, checks={}, consumption={})
        path = self.root/'preparation.json'
        path.write_text(json.dumps(dict(schema=live.PREPARATION, manifest=self.contract, config=dict(authority='separate new treatment authority'))))
        with self.assertRaises(ValueError): report.retained_binding(path, live.sha(path), self.v1, self.register, self.design)

    def test_new_source_prerequisites_require_new_treatment_binding(self):
        for key in live.PREREQUISITES:
            if key == 'independent_decode':
                live.validate_prerequisite_treatment(self.contract, key, {})
            else:
                for record in ({}, dict(source_treatment_sha256='0'*64)):
                    with self.assertRaisesRegex(ValueError, 'new source prerequisite'):
                        live.validate_prerequisite_treatment(self.contract, key, record)
                live.validate_prerequisite_treatment(self.contract, key,
                    dict(source_treatment_sha256=self.contract['source_treatment_sha256']))

    def test_full_new_acquisition_uses_new_schema_and_inherited_stop_rules(self):
        case = acquisition.LiveTests(); case.setUp(); self.addCleanup(case.doCleanups)
        case.contract = self.contract
        outcome, calls, completion = case.acquire()
        self.assertEqual(outcome, live.finite.PASS)
        self.assertEqual(completion['schema'], live.finite.DISPATCH_SCHEMA)
        self.assertEqual(len(calls), 2648)
        self.assertEqual(len(completion['decisions']), 28)

    def test_retained_source_review_does_not_need_live_paths(self):
        path = self.root/'preparation.json'
        binding = dict(schema=live.DISPATCH_PREPARATION, manifest=self.contract,
                       config=dict(authority='separate new treatment authority'))
        path.write_text(json.dumps(binding))
        self.path.unlink(); (self.root/'review.json').unlink()
        self.assertEqual(report.retained_binding(path, live.sha(path), self.v1, self.register, self.design), binding)

    def test_source_diff_and_tree_hashes_are_verified(self):
        calls = []
        def git(command):
            args = command[3:]; calls.append(args)
            if args[0] == 'rev-parse':
                return (dict((self.source[k+'_codec'],self.source[k+'_tree'])
                    for k in ('baseline','candidate','donor'))[args[1][:-7]]+'\n').encode()
            if '--name-only' in args:
                return b'docs/forward53-panels.md\ndocs/performance-candidates.md\ndocs/performance-candidates/classic-forward53-panels.patch.txt\n'
            return b'authored full diff\n'
        source = copy.deepcopy(self.source)
        for key in live.finite.SOURCE_FIELDS:
            if key.endswith('_sha256'): source[key] = hashlib.sha256(b'authored full diff\n').hexdigest()
        review = dict(self.review, sources={k:source[k] for k in live.finite.SOURCE_FIELDS})
        source['independent_review']['sha256'] = hashlib.sha256(json.dumps(review).encode()).hexdigest()
        contract = self.derive(source, review)
        config = dict(codec_sources=dict(candidate=str(self.root)))
        with patch.object(live.subprocess, 'check_output', side_effect=git):
            self.assertEqual(live.verify_source_treatment(config, contract), source)
        self.assertEqual(sum('--binary' in c for c in calls), 3)
        with patch.object(live.subprocess, 'check_output', return_value=b'bad tree\n'):
            with self.assertRaisesRegex(ValueError, 'tree differs'): live.verify_source_treatment(config, contract)
        with patch.object(live.subprocess, 'check_output', side_effect=lambda c: b'bad diff' if '--binary' in c else git(c)):
            with self.assertRaisesRegex(ValueError, 'diff differs'): live.verify_source_treatment(config, contract)

    def test_campaign_scratch_marker_cannot_reuse_historical_slug(self):
        scratch = self.root/'classic-forward53-parallel-dispatch'; scratch.mkdir()
        marker = scratch/'.emuella-campaign-scratch.json'
        marker.write_text(json.dumps(dict(kind='emuella-campaign-scratch', schema_version=1,
                                         slug=scratch.name)))
        stores = {name:dict(prepared=str(self.root/name/'prepared'), streams=str(self.root/name/'streams'),
                            output=str(self.root/name/'output')) for name in ('rareplanes','spacenet')}
        config = dict(build_root=str(scratch), stores=stores, evidence_roots=[v['output'] for v in stores.values()],
                      contract=dict(source_treatment=str(self.path)))
        self.assertEqual(live.evidence_roots(config), [Path(p) for p in config['evidence_roots']])
        with self.assertRaisesRegex(ValueError, 'scratch'): live.evidence_roots(dict(config, contract={}))

    def test_historical_v2_byte_regression_and_full_new_reconstruction(self):
        # Golden captured from unmodified 0db3755. Normalise temporary paths and
        # their SHA-256 bindings only; every decision, sample and receipt remains.
        original = report.reconstruct
        case = retained.RepairTests(); case.setUp(); self.addCleanup(case.doCleanups)
        verified = []
        def compare(binding, digest, estimators):
            result = original(binding, digest, estimators)
            if result['issues']:
                return result
            text = json.dumps(result, sort_keys=True, indent=2).replace(str(case.root), 'AUTHORED_ROOT')
            text = re.sub(r'\b[0-9a-f]{64}\b', 'AUTHORED_SHA256', text)
            self.assertEqual(hashlib.sha256(text.encode()).hexdigest(),
                'f1232fa7317f9fdfcad4bb716ccb75dd2587adc4831174b3abfe876744b201b1')
            new = copy.deepcopy(binding)
            new['schema'] = live.DISPATCH_PREPARATION
            new['manifest'] = self.contract
            for key, record in new['prerequisites'].items():
                if key != 'independent_decode': record['source_treatment_sha256'] = self.contract['source_treatment_sha256']
            paths = [case.output/name for name in ('completion.json', 'execution-complete.json')]
            previous = {p:p.read_bytes() for p in paths}
            try:
                for p in paths:
                    value = json.loads(p.read_text()); value['schema'] = live.finite.DISPATCH_SCHEMA
                    p.write_text(json.dumps(value))
                reconstructed = original(new, digest, estimators)
                wrong = copy.deepcopy(new)
                wrong['prerequisites']['source_correctness'].pop('source_treatment_sha256')
                rejected = original(wrong, digest, estimators)
                self.assertEqual(rejected['disposition'], live.finite.INCOMPLETE)
                self.assertTrue(any('new source prerequisite' in issue for issue in rejected['issues']))
            finally:
                for p, data in previous.items(): p.write_bytes(data)
            self.assertEqual(reconstructed['issues'], [])
            self.assertEqual(reconstructed['disposition'], live.finite.PASS)
            self.assertEqual(reconstructed['schema'], live.finite.DISPATCH_SCHEMA)
            self.assertEqual(reconstructed['endpoints'], result['endpoints'])
            self.assertEqual(reconstructed['raw_rows'], result['raw_rows'])
            verified.append(True)
            return result
        with patch.object(report, 'reconstruct', side_effect=compare):
            case.test_complete_retained_v2_report_reproduces_all_28_decisions()
        self.assertEqual(verified, [True])
