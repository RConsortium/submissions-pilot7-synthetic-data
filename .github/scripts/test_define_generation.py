"""Artifact lifecycle, indexed audit semantics and escaped legacy report output."""

import json
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest import mock

from compare_legacy_define import compare_legacy
from define_report import write_legacy_report

try:
    import pyarrow as pa
    import pyarrow.parquet as pq
    import generate_define as generation
except ImportError:
    generation = None

FIXTURES = Path(__file__).resolve().parents[1] / "tests/fixtures/legacy-define"


class LegacyReportTests(unittest.TestCase):
    def test_report_shows_gaps_and_escapes_xml_and_reference_values(self):
        comparison = compare_legacy(FIXTURES / "reference.xml", FIXTURES / "candidate.xml")
        comparison["unsupported"][0]["reference_ids"] = ['<script>alert("unsafe")</script>']
        comparison["unsupported"][0]["xml"] = '<img src=x onerror="unsafe">'
        report = {"status": "compared_with_gaps", "xml_schema_valid": True, "deterministic_xml": True,
                  "comparison": comparison, "limits": ["Known gaps remain"]}
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / "comparison.html"
            write_legacy_report(target, report)
            text = target.read_text()
        self.assertIn("not fully reproduced", text)
        self.assertIn("MISSING", text)
        self.assertIn("&lt;script&gt;", text)
        self.assertIn("&lt;img", text)
        self.assertNotIn("<script>", text)
        self.assertNotIn("<img", text)
        self.assertIn("comparison.json", text)


@unittest.skipIf(generation is None, "Audit execution needs the study engine, Arrow and XML dependencies")
class DefineGenerationTests(unittest.TestCase):
    @staticmethod
    def declaration(kind="integer"):
        return {"type": kind, "length": "8", "mandatory": "No", "codelist": None,
                "key_sequence": None, "value_level": []}

    def test_indexed_conditions_keep_null_empty_and_negative_selections(self):
        value = self.declaration()
        clauses = [
            [{"variable": "PARAMCD", "comparator": "EQ", "values": ["X"]}],
            [{"variable": "PARAMCD", "comparator": "NE", "values": ["X"]}],
            [{"variable": "PARAMCD", "comparator": "NOTIN", "values": ["X", "Y"]}],
            [{"variable": "PARAMCD", "comparator": "EQ", "values": ["X"]},
             {"variable": "FLAG", "comparator": "NE", "values": ["skip"]}],
        ]
        value["value_level"] = [{**self.declaration(), "where": where} for where in clauses]
        dataset = {"column_order": ["PARAMCD", "FLAG", "VALUE"],
                   "variables": {"PARAMCD": self.declaration("text"), "FLAG": self.declaration("text"), "VALUE": value}}
        document = SimpleNamespace(metadata=lambda: {"datasets": {"D0": dataset}, "codelists": {}})
        with tempfile.TemporaryDirectory() as directory:
            artifact = Path(directory) / "data.parquet"
            pq.write_table(pa.table({"PARAMCD": ["X", "Y", "X", None, ""],
                                     "FLAG": ["keep", "keep", "skip", "keep", "keep"], "VALUE": [1, 2, 3, 4, 5]}), artifact)
            audit = generation.audit_data(document, {"D0": artifact})
        self.assertEqual(audit, {"conformant": True, "conflicts": [],
                                 "value_level_rows": {"D0.VALUE.1": 2, "D0.VALUE.2": 3, "D0.VALUE.3": 2, "D0.VALUE.4": 1}})

    def test_historical_type_conflicts_are_reported_without_coercion_or_crashes(self):
        dataset = {"column_order": ["VALUE"], "variables": {"VALUE": self.declaration()}}
        document = SimpleNamespace(metadata=lambda: {"datasets": {"D0": dataset}, "codelists": {}})
        with tempfile.TemporaryDirectory() as directory:
            artifact = Path(directory) / "data.parquet"
            pq.write_table(pa.table({"VALUE": ["bad", "2", None]}), artifact)
            audit = generation.audit_data(document, {"D0": artifact})
        self.assertFalse(audit["conformant"])
        self.assertEqual(audit["conflicts"], [{"dataset": "D0", "variable": "VALUE", "scope": "column",
                                             "check": "integer_type", "count": 2,
                                             "examples": [{"value": "bad", "count": 1}, {"value": "2", "count": 1}]}])

    def test_failed_attempt_cannot_leave_success_xml_or_comparison_artifacts(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            spec = root / "cdiscpilot01/spec/yamaa"
            spec.mkdir(parents=True)
            (spec / "project.yaml").write_text("adam:\n  define: ../../data/adam/define-yamaa.xml\n")
            xml = root / "cdiscpilot01/data/adam/define-yamaa.xml"
            xml.parent.mkdir(parents=True)
            xml.write_text("old success")
            result = root / ".build/cdiscpilot01-define"
            result.mkdir(parents=True)
            for name in ("report.json", "comparison.json", "comparison.html"):
                (result / name).write_text("old success")
            with mock.patch.object(generation, "ROOT", root), mock.patch.object(generation, "generate", side_effect=ValueError("forced refusal")), mock.patch("sys.argv", ["generate_define", "cdiscpilot01", "--schemas", str(root / "schemas")]):
                self.assertEqual(generation.main(), 1)
            self.assertFalse(xml.exists())
            self.assertFalse((result / "comparison.json").exists())
            self.assertFalse((result / "comparison.html").exists())
            self.assertEqual(json.loads((result / "report.json").read_text()),
                             {"status": "failed", "composition_succeeded": False, "xml_schema_valid": False, "error": "forced refusal"})


if __name__ == "__main__":
    unittest.main()
