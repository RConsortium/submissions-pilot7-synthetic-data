"""Actual record examples stay aligned and separate from full impact counts."""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))
from study_dashboard.trace_examples import TraceExamples


class Frame:
    def __init__(self, rows):
        self.rows = rows
        self.columns = list(rows[0]) if rows else []

    def to_dicts(self):
        return self.rows


SPEC = {
    "keys": ["SUBJECT", "SEQ"], "base": "REF", "input": {"REF": {}},
    "output": {"columns": ["FLAG", "FLAG__OTHER"]},
    "columns": [
        {"name": "FLAG", "derivation": "REF.INPUT"},
        {"name": "FLAG__OTHER", "derivation": "REF.INPUT"},
    ],
}
TEXT = "columns:\n  - name: FLAG\n    derivation: REF.INPUT\n  - name: FLAG__OTHER\n    derivation: REF.INPUT\n"


class TraceExampleTests(unittest.TestCase):
    def test_inputs_read_through_a_ref_intermediate_over_the_base_input_are_shown(self):
        # Documented-rules specifications name the reference input ADSL_REF and read it as REF.
        spec = {
            "keys": ["SUBJECT"], "base": "ADSL_REF", "input": {"ADSL_REF": {}},
            "intermediates": [{"id": "REF", "dataset": "ADSL_REF", "key": ["SUBJECT"]}],
            "output": {"columns": ["FLAG"]},
            "columns": [{"name": "FLAG", "derivation": {"case": [
                {"when": "REF.REASON <> 'Completed' OR REF.REASON IS NULL", "then": "'Y'"}]}}],
        }
        text = "columns:\n  - name: FLAG\n    derivation:\n      case:\n        - when: REF.REASON <> 'Completed'\n          then: \"'Y'\"\n"
        rows = [{"SUBJECT": "A", "REASON": "Completed", "OTHER": 1, "FLAG": ""}]
        probes = [{"column": "FLAG", "reading": "literal", "reference": {"patterns": []}}]
        result = TraceExamples(Frame(rows), Frame(rows), Frame(rows), spec, text, "SUBJECT").variable("FLAG", probes)
        self.assertEqual(result["input_columns"], ["REASON"])
        self.assertEqual(result["subjects"][0]["rows"][0]["inputs"], {"REASON": "Completed"})

    def test_missing_values_blank_values_and_absent_records_are_distinct(self):
        reference = Frame([
            {"SUBJECT": "A", "SEQ": 1, "INPUT": "", "FLAG": "Y"},
            {"SUBJECT": "A", "SEQ": 2, "INPUT": None, "FLAG": ""},
        ])
        probe = Frame([
            {"SUBJECT": "A", "SEQ": 1, "FLAG": "", "FLAG__OTHER": "Y"},
            {"SUBJECT": "A", "SEQ": 3, "FLAG": "Y", "FLAG__OTHER": ""},
        ])
        probes = [{"column": c, "reading": r, "reference": {"patterns": []}}
                  for c, r in [("FLAG", "literal"), ("FLAG__OTHER", "other")]]
        result = TraceExamples(reference, reference, probe, SPEC, TEXT, "SUBJECT").variable("FLAG", probes)
        rows = result["subjects"][0]["rows"]
        self.assertEqual(rows[0]["inputs"]["INPUT"], "")
        self.assertIsNone(rows[1]["inputs"]["INPUT"])
        self.assertFalse(rows[1]["calculations"]["FLAG"]["present"])
        self.assertFalse(rows[2]["reference"]["present"])
        self.assertEqual(rows[2]["calculations"]["FLAG"]["value"], "Y")
        self.assertEqual(result["input_columns"], ["INPUT"])

    def test_complementary_subjects_are_selected_without_manufacturing_rows(self):
        rows = [{"SUBJECT": s, "SEQ": 1, "INPUT": "x", "FLAG": "Y"} for s in "ABC"]
        probes = [{"column": "FLAG", "reading": "literal", "reference": {"patterns": [
            {"reference": "Y", "observed": "", "row": "matched", "subjects": ["A", "B"]},
            {"reference": "", "observed": "Y", "row": "matched", "subjects": ["C"]},
        ]}}]
        result = TraceExamples(Frame(rows), Frame(rows), Frame(rows), SPEC, TEXT, "SUBJECT").variable("FLAG", probes)
        self.assertEqual([s["id"] for s in result["subjects"]], ["A", "C"])
        self.assertTrue(all(s["total_rows"] == 1 for s in result["subjects"]))

    def test_abbreviated_examples_preserve_total_and_nonunique_keys_are_rejected(self):
        rows = [{"SUBJECT": "A", "SEQ": n, "INPUT": "x", "FLAG": ""} for n in range(20)]
        probe = [{**r, "FLAG": "Y" if r["SEQ"] == 19 else ""} for r in rows]
        probes = [{"column": "FLAG", "reading": "literal", "reference": {"patterns": []}}]
        result = TraceExamples(Frame(rows), Frame(rows), Frame(probe), SPEC, TEXT, "SUBJECT").variable("FLAG", probes, max_rows=3)
        sample = result["subjects"][0]
        self.assertEqual(sample["total_rows"], 20)
        self.assertEqual(len(sample["rows"]), 3)
        self.assertEqual(sample["rows"][-1]["keys"]["SEQ"], 19)
        duplicated = TraceExamples(Frame(rows + rows), Frame(rows), Frame(probe), SPEC, TEXT, "SUBJECT")
        self.assertIn("not unique", duplicated.variable("FLAG", probes)["reason"])


if __name__ == "__main__":
    unittest.main()
