"""Regression checks for source instance identity and honest artifact handling."""

import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import pyarrow as pa
import pyarrow.parquet as pq
import pyreadstat

from engine import export_xpt
from odm.extract import extract
import run


def snapshot(events):
    return ('''<?xml version="1.0" encoding="US-ASCII"?>
<ODM xmlns="http://www.cdisc.org/ns/odm/v1.3"
 xmlns:oc="http://www.openclinica.org/ns/odm_ext_v130/v3.1"
 FileType="Snapshot" ODMVersion="1.3">
 <Study OID="S_TEST"><GlobalVariables><StudyName>Test Site</StudyName>
 <StudyDescription>Test</StudyDescription><ProtocolName>TEST</ProtocolName>
 </GlobalVariables></Study>
 <ClinicalData StudyOID="S_TEST" MetaDataVersionOID="V1">
 <SubjectData SubjectKey="SS_1" oc:StudySubjectID="SITE-01">'''
            + events + "</SubjectData></ClinicalData></ODM>").encode("ascii")


def event(repeat, result, extra=""):
    return f'''<StudyEventData StudyEventOID="SE_LABS" StudyEventRepeatKey="{repeat}">
 <FormData FormOID="F_LABS" oc:FormName="Lab Results">
 <ItemGroupData ItemGroupOID="IG_LABS" ItemGroupRepeatKey="1" oc:ItemGroupName="labs">
 <ItemData ItemOID="I_HCT" oc:ItemName="HEMA" Value="{result}"/>{extra}
 </ItemGroupData></FormData></StudyEventData>'''


class ExtractionTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.study = Path(temporary.name)
        self.odm = self.study / "data/odm"
        self.odm.mkdir(parents=True)
        self.source = self.odm / "car-t-openclinica.xml"

    def test_same_group_key_in_different_event_repeats_preserves_both_results(self):
        import csv
        self.source.write_bytes(snapshot(event(1, "666") + event(2, "44")))
        inventory = extract(self.study)
        with (self.odm / "laboratory.csv").open() as stream:
            rows = list(csv.DictReader(stream))
        self.assertEqual([(r["EVENTREPEAT"], r["GROUPREPEAT"], r["I_HEMA"])
                          for r in rows], [("1", "1", "666"), ("2", "1", "44")])
        self.assertEqual((inventory["subjects"], inventory["items"], inventory["groups"]),
                         (1, 2, 2))

    def test_original_xml_stays_byte_identical_and_only_reader_declaration_changes(self):
        original = snapshot(event(1, "41"))
        self.source.write_bytes(original)
        extract(self.study)
        self.assertEqual(self.source.read_bytes(), original)
        self.assertEqual((self.odm / "car-t-utf8.xml").read_bytes(),
                         original.replace(b'US-ASCII', b'UTF-8', 1))

    def test_duplicate_item_in_one_true_instance_is_refused(self):
        extra = '<ItemData ItemOID="I_HCT" oc:ItemName="HEMA" Value="44"/>'
        self.source.write_bytes(snapshot(event(1, "666", extra)))
        with self.assertRaisesRegex(ValueError, "Repeated items within an ODM instance"):
            extract(self.study)

    def test_sanitized_item_names_cannot_merge_different_source_items(self):
        text = event(1, "41").replace('oc:ItemName="HEMA"', 'oc:ItemName="A-B"')
        text = text.replace('</ItemGroupData>',
                            '<ItemData ItemOID="I_OTHER" oc:ItemName="A_B" Value="9"/></ItemGroupData>')
        self.source.write_bytes(snapshot(text))
        with self.assertRaisesRegex(ValueError, "Item names collide"):
            extract(self.study)


class PublicationTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.base = Path(temporary.name)

    def test_transport_keeps_labels_leading_blanks_sas_dates_and_declared_widths(self):
        from datetime import date
        artifact = self.base / "adtest.parquet"
        pq.write_table(pa.table({"TERM": [" before "],
                                 "ADT": pa.array([date(1960, 1, 2)], type=pa.date32())}), artifact)
        spec = {"domain": "ADTEST", "submission": {"label": "Test Analysis"},
                "output": {"path": str(artifact)}, "columns": [
                    {"name": "TERM", "type": "str", "label": "Reported Term", "submission": {"length": 20}},
                    {"name": "ADT", "type": "date", "label": "Analysis Date", "submission": {"length": 8}}]}
        export_xpt(self.base / "spec.yaml", spec)
        frame, metadata = pyreadstat.read_xport(self.base / "adtest.xpt", disable_datetime_conversion=True)
        self.assertEqual(frame.to_dict("records"), [{"TERM": " before", "ADT": 1.0}])
        self.assertEqual(metadata.column_names_to_labels,
                         {"TERM": "Reported Term", "ADT": "Analysis Date"})
        self.assertEqual(metadata.variable_storage_width["TERM"], 20)

    def test_oversized_transport_value_fails_instead_of_truncating(self):
        artifact = self.base / "test.parquet"
        pq.write_table(pa.table({"TERM": ["X" * 201]}), artifact)
        spec = {"domain": "TEST", "submission": {"label": "Test"},
                "output": {"path": str(artifact)}, "columns": [
                    {"name": "TERM", "type": "str", "label": "Term", "submission": {"length": 200}}]}
        with self.assertRaisesRegex(ValueError, "width exceeds"):
            export_xpt(self.base / "spec.yaml", spec)
        self.assertFalse((self.base / "test.xpt").exists())

    def test_failed_build_replaces_old_success_evidence(self):
        (self.base / "log").mkdir()
        record = self.base / "log/run.json"
        record.write_text('{"status":"succeeded"}')
        with patch.object(run, "STUDY", self.base), \
                patch.object(run, "extract", side_effect=ValueError("invalid source")), \
                patch("sys.argv", ["run.py"]):
            with self.assertRaisesRegex(ValueError, "invalid source"):
                run.main()
        evidence = json.loads(record.read_text())
        self.assertEqual((evidence["status"], evidence["reason"]), ("failed", "invalid source"))


if __name__ == "__main__":
    unittest.main()
