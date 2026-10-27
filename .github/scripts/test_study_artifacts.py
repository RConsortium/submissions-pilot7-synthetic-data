"""Published successes must describe the exact bytes exported to the dashboard."""

from pathlib import Path
import json
import tempfile
import unittest

from study_artifacts import artifact_snapshot, verify_artifacts
from stage_study_artifacts import stage


class ArtifactTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.files = ['study/spec/yamaa/adsl.yaml', 'study/spec/source/guide.pdf',
                      'study/data/sdtm/dm.parquet', 'study/data/adam/adsl.parquet',
                      'study/data/adam/adsl-yamaa.parquet', '.github/dashboard.json']
        for name in self.files:
            path = self.root / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(b'validated bytes')
        self.report = {'status': 'succeeded', 'artifacts': artifact_snapshot(self.root, 'study')}

    def test_roundtrip_and_exact_cross_job_transfer(self):
        target = self.root / 'transfer'
        stage(self.root, 'study', target, self.report)
        self.assertEqual([p.relative_to(target).as_posix() for p in target.rglob('*') if p.is_file()],
                         ['study/data/adam/adsl-yamaa.parquet'])
        self.assertEqual((target / self.files[4]).read_bytes(), b'validated bytes')
        verify_artifacts(self.root, 'study', self.report)

    def test_source_pipeline_transfers_generated_sdtm_and_hashes_odm_and_extraction(self):
        catalog = self.root / '.github/yamaa-studies.json'
        catalog.write_text(json.dumps({'study': {'prepare': 'program/run.py'}}))
        additions = ['study/data/odm/source.xml', 'study/data/odm/clinical_items.csv',
                     'study/data/sdtm/define.xml', 'study/program/odm/extract.py']
        for name in additions:
            path = self.root / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(b'source pipeline bytes')
        report = {'status': 'succeeded', 'source_pipeline': True,
                  'artifacts': artifact_snapshot(self.root, 'study')}
        for name in additions:
            self.assertIn(name, report['artifacts']['files'])
        target = self.root / 'transfer'
        stage(self.root, 'study', target, report)
        self.assertEqual(sorted(p.relative_to(target).as_posix() for p in target.rglob('*') if p.is_file()),
                         sorted(name for name in self.files + additions if name.startswith('study/data/')))
        (self.root / additions[-1]).write_bytes(b'changed extraction')
        with self.assertRaisesRegex(ValueError, 'artifacts changed'):
            verify_artifacts(self.root, 'study', report)

    def test_tracked_sources_and_ignored_outputs_reject_changed_bytes(self):
        for name in self.files:
            with self.subTest(name=name):
                path = self.root / name
                path.write_bytes(b'changed after validation')
                with self.assertRaisesRegex(ValueError, 'artifacts changed'):
                    verify_artifacts(self.root, 'study', self.report)
                path.write_bytes(b'validated bytes')

    def test_added_and_deleted_files_cannot_reuse_a_success(self):
        path = self.root / 'study/data/adam/new-yamaa.parquet'
        path.touch()
        with self.assertRaisesRegex(ValueError, 'new-yamaa'):
            verify_artifacts(self.root, 'study', self.report)
        path.unlink()
        path = self.root / self.files[0]
        path.unlink()
        with self.assertRaisesRegex(ValueError, 'adsl.yaml'):
            verify_artifacts(self.root, 'study', self.report)

    def test_legacy_records_and_failed_transfers_are_rejected(self):
        with self.assertRaisesRegex(ValueError, 'rerun validation'):
            verify_artifacts(self.root, 'study', {})
        with self.assertRaisesRegex(ValueError, 'failed validation'):
            stage(self.root, 'study', self.root / 'transfer', {'status': 'failed'})

    def test_caches_and_core_reports_do_not_change_clinical_evidence(self):
        for name in ['study/program/adam/python/__pycache__/run.pyc',
                     'study/data/adam/core-report-ADAM.xlsx']:
            path = self.root / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.touch()
        verify_artifacts(self.root, 'study', self.report)
