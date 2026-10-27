"""Regression checks for source instance identity and honest artifact handling."""

import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import pyarrow as pa
import pyarrow.parquet as pq
import pyreadstat
import yaml
import yamaa

from engine import export_xpt
from odm.prepare import prepare, reader_copy
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


def event(repeat, result, extra="", form_repeat="1", layout="L1"):
    return f'''<StudyEventData StudyEventOID="SE_AE" StudyEventRepeatKey="{repeat}">
 <FormData FormOID="F_ADVERSEEVENT" FormRepeatKey="{form_repeat}"
 oc:FormName="Adverse Event" oc:FormLayoutOID="{layout}">
 <ItemGroupData ItemGroupOID="IG_ADVER_AE" ItemGroupRepeatKey="1" oc:ItemGroupName="AE">
 <ItemData ItemOID="I_ADVER_AETERM" oc:ItemName="AETERM" Value="{result}"/>{extra}
 </ItemGroupData></FormData></StudyEventData>'''


class NativeODMTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.study = Path(temporary.name)
        self.odm = self.study / "data/odm"
        self.odm.mkdir(parents=True)
        self.source = self.odm / "car-t-openclinica.xml"

    def run_ae(self):
        # Execute the maintained clinical YAML against a small independent ODM.
        spec_path = Path(__file__).resolve().parents[1] / "spec/yamaa/sdtm/ae.yaml"
        spec = yaml.safe_load(spec_path.read_text())
        spec["input"] = {name: str(self.odm / "car-t-utf8.xml") for name in ("ODM", "RAW")}
        spec["output"]["path"] = "ae.parquet"
        spec["output"]["report"] = "ae-report.parquet"
        path = self.study / "ae.yaml"
        path.write_text(yaml.safe_dump(spec, sort_keys=False))
        return yamaa.spec(path).run()

    def test_native_yaml_preserves_event_repeats_without_csv_staging(self):
        self.source.write_bytes(snapshot(event(1, "666") + event(2, "44")))
        inventory = prepare(self.study)
        result = self.run_ae()
        self.assertEqual(result.status, "succeeded", result.issues.to_pylist())
        self.assertEqual([row["AETERM"] for row in result.output.to_pylist()], ["666", "44"])
        self.assertFalse(list(self.study.rglob("*.csv")))
        self.assertEqual(pq.read_table(self.odm / "items.parquet").num_rows, 2)
        self.assertEqual((inventory["subjects"], inventory["items"], inventory["groups"]),
                         (1, 2, 2))

    def test_native_yaml_preserves_form_repeats(self):
        self.source.write_bytes(snapshot(event(1, "first") + event(1, "second", form_repeat="2")))
        prepare(self.study)
        result = self.run_ae()
        self.assertEqual(result.status, "succeeded", result.issues.to_pylist())
        self.assertEqual([row["AETERM"] for row in result.output.to_pylist()], ["first", "second"])

    def test_original_xml_stays_byte_identical_and_only_reader_declaration_changes(self):
        original = snapshot(event(1, "41"))
        self.source.write_bytes(original)
        prepare(self.study)
        self.assertEqual(self.source.read_bytes(), original)
        self.assertEqual((self.odm / "car-t-utf8.xml").read_bytes(),
                         original.replace(b'US-ASCII', b'UTF-8', 1))

    def test_duplicate_item_in_one_true_instance_is_refused(self):
        extra = '<ItemData ItemOID="I_ADVER_AETERM" oc:ItemName="AETERM" Value="44"/>'
        self.source.write_bytes(snapshot(event(1, "666", extra)))
        with self.assertRaisesRegex(ValueError, "Repeated ItemOID within an ODM instance"):
            prepare(self.study)
        # The native item expression also refuses the duplicate on its own.
        result = self.run_ae()
        self.assertEqual(result.status, "failed")
        self.assertIn("odm_not_unique", [row["condition"] for row in result.issues.to_pylist()])

    def test_native_items_use_exact_oid_when_display_names_collide(self):
        extra = '<ItemData ItemOID="I_OTHER" oc:ItemName="AETERM" Value="other"/>'
        self.source.write_bytes(snapshot(event(1, "recorded", extra)))
        prepare(self.study)
        result = self.run_ae()
        self.assertEqual(result.status, "succeeded", result.issues.to_pylist())
        self.assertEqual(result.output.to_pylist()[0]["AETERM"], "recorded")

    def test_layout_collision_is_refused_before_native_grouping(self):
        self.source.write_bytes(snapshot(event(1, "first") + event(1, "second", layout="L2")))
        with self.assertRaisesRegex(ValueError, "Distinct form layouts"):
            prepare(self.study)

    def test_metadata_version_collision_is_refused_before_native_grouping(self):
        document = snapshot(event(1, "first"))
        start = document.index(b"<ClinicalData")
        end = document.index(b"</ClinicalData>") + len(b"</ClinicalData>")
        other = document[start:end].replace(b'"V1"', b'"V2"')
        self.source.write_bytes(document.replace(b"</ODM>", other + b"</ODM>"))
        with self.assertRaisesRegex(ValueError, "Distinct metadata versions"):
            prepare(self.study)

    def test_ascii_declaration_with_non_ascii_bytes_is_not_relabelled(self):
        self.source.write_bytes(snapshot(event(1, "result")).replace(b"result", "caf\u00e9".encode("utf-8")))
        with self.assertRaises(UnicodeDecodeError):
            reader_copy(self.source, self.odm / "reader.xml")
        self.assertFalse((self.odm / "reader.xml").exists())


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
                patch.object(run, "prepare", side_effect=ValueError("invalid source")), \
                patch("sys.argv", ["run.py"]):
            with self.assertRaisesRegex(ValueError, "invalid source"):
                run.main()
        evidence = json.loads(record.read_text())
        self.assertEqual((evidence["status"], evidence["reason"]), ("failed", "invalid source"))


if __name__ == "__main__":
    unittest.main()
