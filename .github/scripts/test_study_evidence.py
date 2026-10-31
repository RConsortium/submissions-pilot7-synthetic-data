"""Regression checks for publication of study validation evidence."""

from copy import deepcopy
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from study_evidence import catalog, engine_revision, reviewed_datasets, validate_reports, validate_verifications
from study_dashboard.config import settings
import validate_yamaa

PIN = 'a' * 40


class EvidenceTests(unittest.TestCase):
    def test_every_official_pilot_uses_shared_review_and_committed_claims(self):
        root = Path(__file__).resolve().parents[2]
        for study, entry in catalog(root).items():
            if entry['comparison'] != 'official':
                continue
            with self.subTest(study=study):
                self.assertNotIn('review_scope', settings(root, entry))
                claimed = {p.stem.removesuffix('-claims').upper()
                           for p in (root / study / 'spec/review').glob('*-claims.json')}
                self.assertEqual(set(reviewed_datasets(root, study)), claimed)

    def test_published_projects_share_one_engine_revision(self):
        root = Path(__file__).resolve().parents[2]
        revisions = {
            engine_revision(root, study) for study in catalog(root)
            if (root / study / 'spec/yamaa/project.yaml').is_file()
        }
        self.assertEqual(len(revisions), 1, 'Publication requires one shared yamaa revision')

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.entries = {'official': {'comparison': 'official'},
                        'proposal': {'comparison': 'optional', 'allow_pending': True}}
        project = self.root / 'official/spec/yamaa'
        project.mkdir(parents=True)
        (project / 'project.yaml').write_text('adam:\n  specs: [adsl.yaml]\n')
        (project / 'adsl.yaml').write_text('domain: ADSL\n')
        req = self.root / 'official/program/adam/python/requirements.txt'
        req.parent.mkdir(parents=True)
        req.write_text(f'git+https://github.com/elong0527/yamaa.git@{PIN}\n')
        self.reports = {
            'official': {'study': 'official', 'repository_commit': 'commit',
                         'status': 'succeeded', 'yamaa_revision': PIN,
                         'datasets': [{'domain': 'ADSL', 'spec': 'official/spec/yamaa/adsl.yaml',
                                       'build': 'succeeded', 'comparison': 'passed',
                                       'rows': 254, 'columns': 50}]},
            'proposal': {'study': 'proposal', 'repository_commit': 'commit',
                         'status': 'pending', 'datasets': []},
        }

    def check(self, reports=None):
        validate_reports(self.root, self.entries, reports or self.reports, 'commit')

    def test_optional_project_can_be_pending(self):
        self.check()

    def test_documented_rule_findings_must_match_this_commit_engine_and_reviewed_datasets(self):
        review = self.root / 'official/spec/review'
        review.mkdir(parents=True)
        report = {'schema_version': 2, 'study': 'official', 'revision': 'commit',
                  'yamaa_revision': PIN, 'datasets': [{'dataset': 'ADSL'}]}
        cases = [
            ('current report', report, None),
            ('no report', None, 'have no verification report'),
            ('another commit', {**report, 'revision': 'earlier-commit'}, 'not from this source commit'),
            ('another engine', {**report, 'yamaa_revision': 'b' * 40}, 'different engine pin'),
            ('another dataset', {**report, 'datasets': [{'dataset': 'ADAE'}]}, 'does not cover exactly'),
            ('older schema', {**report, 'schema_version': 1}, 'unsupported or misnamed'),
        ]
        for label, verification, message in [('claims removed', report, 'without review claims')]:
            with self.subTest(case=label):
                with self.assertRaisesRegex(ValueError, message, msg=label):
                    validate_verifications(self.root, self.entries, self.reports, {'official': verification}, 'commit')
        (review / 'adsl-claims.json').write_text('{}')
        for label, verification, message in cases:
            with self.subTest(case=label):
                verifications = {} if verification is None else {'official': verification}
                if message is None:
                    validate_verifications(self.root, self.entries, self.reports, verifications, 'commit')
                else:
                    with self.assertRaisesRegex(ValueError, message, msg=label):
                        validate_verifications(self.root, self.entries, self.reports, verifications, 'commit')

    def test_official_project_cannot_be_pending(self):
        self.reports['official'].update(status='pending', datasets=[])
        with self.assertRaises(ValueError):
            self.check()

    def test_comparison_must_explicitly_pass(self):
        for value in ('failed', 'unavailable', 'skipped', None):
            with self.subTest(value=value):
                reports = deepcopy(self.reports)
                reports['official']['datasets'][0]['comparison'] = value
                with self.assertRaises(ValueError):
                    self.check(reports)

    def test_missing_and_duplicate_dataset_are_rejected(self):
        for datasets in ([], self.reports['official']['datasets'] * 2):
            reports = deepcopy(self.reports)
            reports['official']['datasets'] = datasets
            with self.assertRaises(ValueError):
                self.check(reports)

    def test_failed_stale_and_mixed_evidence_are_rejected(self):
        for key, value in [('status', 'failed'), ('yamaa_revision', 'b' * 40),
                           ('repository_commit', 'earlier-commit')]:
            reports = deepcopy(self.reports)
            reports['official'][key] = value
            with self.assertRaises(ValueError):
                self.check(reports)
        self.reports['proposal']['repository_commit'] = 'another-commit'
        with self.assertRaises(ValueError):
            validate_reports(self.root, self.entries, self.reports)

    def test_failed_attempt_replaces_old_success_report(self):
        config = self.root / '.github/yamaa-studies.json'
        config.parent.mkdir()
        config.write_text(json.dumps({'missing': {'comparison': 'official'}}))
        report = self.root / 'old-success.json'
        report.write_text(json.dumps({'status': 'succeeded'}))
        with patch.object(validate_yamaa, 'ROOT', self.root), patch(
                'sys.argv', ['validate_yamaa.py', 'missing', '--report', str(report)]):
            self.assertEqual(validate_yamaa.main(), 1)
        self.assertEqual(json.loads(report.read_text())['status'], 'failed')


if __name__ == '__main__':
    unittest.main()
