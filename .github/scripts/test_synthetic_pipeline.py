"""Safeguards for structural ODM staging and synthetic publication evidence."""

import csv
import io
import json
from pathlib import Path
import tarfile
import tempfile
import unittest
import zipfile

from synthetic_odm import stage
from synthetic_evidence import artifact_inventory, package, stage_artifacts, verified_report
from study_dashboard.synthetic import development


class SyntheticPipelineTests(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.root = Path(directory.name)

    def archive(self, *, duplicate=False):
        group = ('<ItemGroupData ItemGroupOID="FO.FORM"><ItemGroupData '
                 'ItemGroupOID="IG.NCT.LB" ItemGroupRepeatKey="7">'
                 '<ItemData ItemOID="IT.NCT.LB.HGB"><Value>12.75</Value></ItemData>'
                 '</ItemGroupData></ItemGroupData>')
        subject = ('<SubjectData SubjectKey="001"><StudyEventData StudyEventOID="SE.BASE" '
                   'StudyEventRepeatKey="2">' + group + '</StudyEventData></SubjectData>')
        xml = ('<ODM xmlns="http://www.cdisc.org/ns/odm/v2.0"><Study OID="ST.NCT">'
               '<MetaDataVersion><ItemDef OID="IT.NCT.LB.HGB" Name="Hemoglobin" DataType="integer"/>'
               '<ItemGroupDef OID="IG.NCT.LB"><ItemRef ItemOID="IT.NCT.LB.HGB"/></ItemGroupDef>'
               '<StudyEventDef OID="SE.BASE" Name="Baseline"/></MetaDataVersion></Study>'
               '<ClinicalData>' + subject + (subject if duplicate else '') + '</ClinicalData></ODM>')
        target = self.root / 'kn564/data/odm/kn564_odm.tar.gz'
        target.parent.mkdir(parents=True, exist_ok=True)
        with tarfile.open(target, 'w:gz') as archive:
            member = tarfile.TarInfo('source/odm.xml')
            member.size = len(xml.encode())
            archive.addfile(member, io.BytesIO(xml.encode()))
        return target

    def test_nested_odm_preserves_fraction_and_source_identifiers(self):
        archive = self.archive()
        unchanged = archive.read_bytes()
        report = stage('kn564', self.root)
        with (self.root / 'kn564/data/odm/extracted/lb.csv').open() as source:
            rows = list(csv.DictReader(source))
        self.assertEqual(report['subjects'], 1)
        self.assertEqual(report['group_counts'], {'IG.NCT.LB': 1})
        self.assertEqual(rows[0]['HGB'], '12.75')
        self.assertEqual(rows[0]['EVENTREP'], '2')
        self.assertEqual(rows[0]['GROUPREP'], '7')
        self.assertEqual(rows[0]['USUBJID'], '001')
        self.assertEqual(report['items']['IT.NCT.LB.HGB']['data_type'], 'integer')
        self.assertEqual(archive.read_bytes(), unchanged)

    def test_duplicate_subject_snapshots_fail_instead_of_doubling_records(self):
        self.archive(duplicate=True)
        with self.assertRaisesRegex(ValueError, 'Duplicate subject snapshot'):
            stage('kn564', self.root)

    def evidence(self):
        for name in ['synthetic_odm.py', 'synthetic_checks.py', 'synthetic_evidence.py', 'validate_synthetic.py',
                     'resolved_specs.py', 'study_evidence.py', 'study_dashboard/specifications.py']:
            path = self.root / '.github/scripts' / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text('# fixture\n')
        schema = self.root / '.github/schemas/synthetic-review.schema.json'
        schema.parent.mkdir(parents=True, exist_ok=True)
        schema.write_text('{}')
        source = self.root / 'kn564/spec/yamaa/project.yaml'
        source.parent.mkdir(parents=True)
        source.write_text('yamaa: "1.0"\n')
        output = self.root / 'kn564/data/adam/adsl.xpt'
        output.parent.mkdir(parents=True)
        output.write_bytes(b'transport')
        record = {'status': 'succeeded', 'source_revision': 'commit',
                  'artifacts': artifact_inventory(self.root, 'kn564')}
        path = self.root / '.build/synthetic/kn564/report.json'
        path.parent.mkdir(parents=True)
        path.write_text(json.dumps(record))
        return path

    def test_report_rejects_revision_or_artifact_changes(self):
        self.evidence()
        self.assertEqual(verified_report(self.root, 'kn564', 'commit')['status'], 'succeeded')
        with self.assertRaisesRegex(ValueError, 'different source revision'):
            verified_report(self.root, 'kn564', 'other')
        (self.root / 'kn564/data/adam/adsl.xpt').write_bytes(b'changed')
        with self.assertRaisesRegex(ValueError, 'stale'):
            verified_report(self.root, 'kn564')

    def test_added_or_removed_files_invalidate_evidence(self):
        self.evidence()
        added = self.root / 'kn564/data/adam/new.xpt'
        added.write_bytes(b'new')
        with self.assertRaisesRegex(ValueError, 'stale'):
            verified_report(self.root, 'kn564')
        added.unlink()
        (self.root / 'kn564/spec/yamaa/project.yaml').unlink()
        with self.assertRaisesRegex(ValueError, 'stale'):
            verified_report(self.root, 'kn564')

    def test_missing_or_failed_required_build_cannot_publish(self):
        with self.assertRaisesRegex(ValueError, 'required synthetic validation is missing'):
            development(self.root, 'kn564', self.root / 'bundle', 'commit', required=True)
        path = self.evidence()
        path.write_text(json.dumps({'status': 'failed', 'error': 'fixture failure'}))
        with self.assertRaisesRegex(ValueError, 'failed synthetic validation'):
            development(self.root, 'kn564', self.root / 'bundle', 'commit')

    def test_transfer_and_package_keep_exact_generated_bytes_and_evidence(self):
        self.evidence()
        destination = self.root / 'transfer'
        stage_artifacts(self.root, 'kn564', destination)
        self.assertEqual((destination / 'kn564/data/adam/adsl.xpt').read_bytes(), b'transport')
        self.assertTrue((destination / '.build/synthetic/kn564/report.json').is_file())
        record = verified_report(self.root, 'kn564')
        path = self.root / 'review.zip'
        package(self.root, 'kn564', path, record)
        with zipfile.ZipFile(path) as archive:
            self.assertEqual(archive.read('kn564/data/adam/adsl.xpt'), b'transport')
            self.assertIn('.github/scripts/validate_synthetic.py', archive.namelist())
            self.assertIn('.build/synthetic/kn564/report.json', archive.namelist())
