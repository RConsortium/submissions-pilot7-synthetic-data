"""Review-index boundaries: literal names, row context, source versions, data fidelity."""

from datetime import date
import gzip
import json
from pathlib import Path
import tempfile
import unittest

import pyarrow as pa
import pyarrow.parquet as pq
import yaml

import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))
from study_dashboard.datasets import export_table, read_table
from study_dashboard.lineage import build_lineage, source_locations
from study_dashboard.consistency import build_report
from study_dashboard.documents import define_metadata, document_sections
from study_dashboard.rule_review import rule_findings


class ReviewDataTests(unittest.TestCase):
    def test_declared_input_ordinal_is_a_source_field_and_unknown_names_stay_unresolved(self):
        spec = {'input': {'QS': {'path': 'qs.parquet', 'ordinal': '_ORDER'}},
                'output': {'columns': ['SOURCE_ORDER', 'TYPO']},
                'base': 'QS', 'columns': [
                    {'name': 'SOURCE_ORDER', 'derivation': 'QS._ORDER'},
                    {'name': 'TYPO', 'derivation': 'QS._TYPO'}]}
        lineage = build_lineage(yaml.safe_dump(spec), spec, {'QS': {'QSSEQ'}})
        self.assertEqual(lineage['edges']['spec.SOURCE_ORDER'], ['QS._ORDER'])
        self.assertEqual(lineage['unresolved'], ['QS._TYPO'])

    def test_static_lineage_excludes_mapping_literals_and_includes_context(self):
        text = """domain: ADSL
input:
  DM: {path: dm.parquet}
base: DM
output:
  columns: [TRT, AGE]
intermediates:
  - id: FIRST
    dataset: DM
    key: [USUBJID]
    filter: "DM.ARM <> 'AGE'"
    order_by: [{variable: DM.AGE}]
    keep: first
columns:
  - name: AGE
    derivation: DM.AGE
  - name: TRT
    derivation:
      mapping:
        source: FIRST.ARM
        dict: {Placebo: AGE}
"""
        result = build_lineage(
            text, yaml.safe_load(text), {"DM": {"USUBJID", "AGE", "ARM"}}
        )
        self.assertEqual(
            result["edges"],
            {
                "intermediate.FIRST": ["DM.AGE", "DM.ARM", "DM.USUBJID"],
                "FIRST.USUBJID": ["DM.USUBJID", "intermediate.FIRST"],
                "FIRST.AGE": ["DM.AGE", "intermediate.FIRST"],
                "FIRST.ARM": ["DM.ARM", "intermediate.FIRST"],
                "spec.AGE": ["DM.AGE"],
                "spec.TRT": ["FIRST.ARM"],
                "output.TRT": ["spec.TRT"],
                "output.AGE": ["spec.AGE"],
            },
            "mapping dictionary strings are literal; lookup context affects results",
        )
        self.assertEqual(result["unresolved"], [])
        self.assertEqual(
            text.splitlines()[result["spans"]["TRT"]["start"] - 1], "  - name: TRT"
        )

    def test_row_template_sources_and_self_lookups_are_indexed(self):
        text = """domain: ADX
input: {DM: dm.parquet}
base: DM
output: {columns: [VALUE, BASE]}
intermediates:
  - id: BASE_ROW
    dataset: SELF
    filter: "VALUE > 0"
    keep: first
columns:
  - name: VALUE
  - name: BASE
    derivation: BASE_ROW.VALUE
rows:
  - id: collected
    dataset: DM
    filter: "DM.AGE > 60"
    derivations: {VALUE: DM.AGE}
"""
        r = build_lineage(text, yaml.safe_load(text), {"DM": {"AGE"}})
        self.assertEqual(
            {
                k: r["edges"][k]
                for k in ["spec.VALUE", "spec.BASE", "BASE_ROW.VALUE", "row.collected"]
            },
            {
                "spec.VALUE": ["DM.AGE", "row.collected"],
                "spec.BASE": ["BASE_ROW.VALUE", "row.collected"],
                "BASE_ROW.VALUE": ["intermediate.BASE_ROW", "spec.VALUE"],
                "row.collected": ["DM.AGE"],
            },
            "row-created values retain source and row-selection dependencies",
        )
        self.assertEqual(r["unresolved"], [])

    def test_source_locations_cover_inline_columns_and_individual_row_expressions(self):
        text = """domain: ADX
columns:
  - {name: AGE}
rows:
  - id: collected
    derivations:
      AGE: DM.AGE
      SEX:
        mapping:
          source: DM.SEX
      EMPTY:
  - id: planned
    derivations: {AGE: 65, SEX: F}
verifications:
  - row_count: {min: 1}
"""
        self.assertEqual(
            source_locations(text),
            {
                "spans": {
                    "AGE": {"start": 3, "end": 3, "kind": "columns"},
                    "collected": {"start": 5, "end": 11, "kind": "rows"},
                    "planned": {"start": 12, "end": 13, "kind": "rows"},
                },
                "row_derivations": {
                    "collected": {
                        "AGE": {"start": 7, "end": 7},
                        "SEX": {"start": 8, "end": 10},
                        "EMPTY": {"start": 11, "end": 11},
                    },
                    "planned": {
                        "AGE": {"start": 13, "end": 13},
                        "SEX": {"start": 13, "end": 13},
                    },
                },
                "focus": {},
            },
        )

    def test_focus_locations_keep_inline_output_metadata_and_individual_input_members(
        self,
    ):
        text = """input: {QS: qs.parquet, DM: dm.parquet, EX: ex.parquet}
output: {path: out.parquet, columns: [AGE, SEX]}
base: DM
intermediates:
  - id: USED
    dataset: DM
    derivations:
      AGE: DM.AGE
      SEX: DM.SEX
"""
        self.assertEqual(
            source_locations(text)["focus"],
            {
                "inputs": {
                    "QS": {"start": 1, "end": 1, "start_column": 8, "end_column": 24},
                    "DM": {"start": 1, "end": 1, "start_column": 24, "end_column": 40},
                    "EX": {"start": 1, "end": 1, "start_column": 38, "end_column": 54},
                },
                "sections": {
                    "input": {"start": 1, "end": 1, "whole_line": True},
                    "intermediates": {"start": 4, "end": 9, "whole_line": True},
                },
                "base": "DM",
                "output_columns": {
                    "start": 2,
                    "end": 2,
                    "start_column": 26,
                    "end_column": 47,
                },
                "intermediate_drivers": {"USED": "DM"},
                "intermediate_derivations": {
                    "USED": {
                        "AGE": {"start": 8, "end": 8},
                        "SEX": {"start": 9, "end": 9},
                    }
                },
            },
        )

    def test_complete_chunks_preserve_all_rows_dates_nulls_and_original_order(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "values.parquet"
            target = root / "bundle"
            target.mkdir()
            table = pa.table(
                {
                    "USUBJID": ["S2", "S1", None, "S1"],
                    "VALUE": [1.25, None, float("inf"), -2.0],
                    "DATE": [date(2020, 1, 2), None, None, date(2020, 3, 4)],
                }
            )
            pq.write_table(table, source)
            metadata = export_table(source, target, "sample", root=root)
            rows = sorted(
                [
                    row
                    for c in metadata["chunks"]
                    for row in json.loads(
                        gzip.decompress((target / c["url"]).read_bytes())
                    )
                ]
            )
            self.assertEqual(
                rows,
                [
                    [0, "S2", 1.25, "2020-01-02"],
                    [1, "S1", None, None],
                    [2, None, "Infinity", None],
                    [3, "S1", -2.0, "2020-03-04"],
                ],
            )
            self.assertTrue(pq.read_table(target / metadata["download"]).equals(table))

    def test_csv_keeps_text_ids_and_handles_declared_numeric_missing_values(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "plan.csv"
            path.write_text("USUBJID,VISIT\n001,3\n002,\n")
            self.assertEqual(
                read_table(path, {"VISIT": "int"}).to_pylist(),
                [{"USUBJID": "001", "VISIT": 3}, {"USUBJID": "002", "VISIT": None}],
            )

    def test_documented_rule_findings_keep_their_evidence_and_link_into_retained_documents(self):
        # The verification report is decided in the validation job; the table
        # entry keeps its rule, quotes and adjudication and gains dashboard links.
        side = {
            "role": "states",
            "document": "spec/source/SAP.pdf",
            "section": "page-13",
            "section_title": "Page 13",
            "quote": "BMI>=30",
            "context": "BMI category (BMI<25, BMI 25-<30, BMI>=30)",
            "verified": True,
            "links": {"repository": "https://example/blob/r/study/spec/source/SAP.pdf"},
        }
        pattern = {"reference": "<25", "observed": None, "row": "matched", "count": 1, "subjects": ["01-702-1082"]}
        finding = {
            "id": "ADSL.BMIBLGR1.CR-5",
            "dataset": "ADSL",
            "variable": "BMIBLGR1",
            "rule": {"id": "CR-5", "title": "A documented rule reproduces the reference", "severity": "conflict", "statement": "Rule text."},
            "severity": "conflict",
            "relation": None,
            "summary": "The documented rule differs on 1 of 2 records.",
            "note": "",
            "documents": [side],
            "spec": {"path": "study/spec/yamaa/adsl.yaml", "element": "BMIBLGR1", "quote": None, "lines": None, "element_lines": [7, 9], "excerpt": "- name: BMIBLGR1", "url": "https://example/adsl.yaml#L7-L9"},
            "variable_spec": None,
            "evidence": {"probes": [{"column": "BMIBLGR1", "reading": "literal", "definition": {}, "reference": {"compared": 2, "differ": 1, "patterns": [pattern]}}]},
            "interpretations": [],
            "question": "Which group?",
            "assessment": "",
            "adjudication": {"decision": "agree", "reason": "Right."},
        }
        verification = {"datasets": [{"dataset": "ADSL", "findings": [finding]}]}
        documents = [{"path": "study/spec/source/SAP.pdf", "reading": "documents/study/spec/source/SAP.pdf.html", "original": "documents/study/spec/source/SAP.pdf"}]
        [entry] = rule_findings("study", verification, documents)
        self.assertEqual(
            {k: entry[k] for k in ("id", "comparison", "kind", "status", "title", "source", "spec", "data", "recommendation", "subjects", "adjudication")},
            {
                "id": "study:ADSL.BMIBLGR1.CR-5",
                "comparison": "documented_rules",
                "kind": "conflict",
                "status": "Conflict: CR-5",
                "title": "CR-5 A documented rule reproduces the reference",
                "source": {"path": "study/spec/source/SAP.pdf", "section": "Page 13", "excerpt": side["context"], "url": "documents/study/spec/source/SAP.pdf.html#page-13"},
                "spec": {"path": "study/spec/yamaa/adsl.yaml", "line": 7, "url": "https://example/adsl.yaml#L7-L9", "excerpt": "- name: BMIBLGR1"},
                "data": {"path": "", "summary": "Probe BMIBLGR1 (literal rule): 1 of 2 records differ from the reference."},
                "recommendation": "Which group?",
                "subjects": ["01-702-1082"],
                "adjudication": {"decision": "agree", "reason": "Right."},
            },
            "the table's common fields, for search, the drawer and source links",
        )
        self.assertEqual(
            {k: entry["documents"][0][k] for k in ("path", "name", "section", "reading", "original", "repository")},
            {
                "path": "study/spec/source/SAP.pdf",
                "name": "SAP.pdf",
                "section": "page-13",
                "reading": "documents/study/spec/source/SAP.pdf.html#page-13",
                "original": "documents/study/spec/source/SAP.pdf#page=13",
                "repository": "https://example/blob/r/study/spec/source/SAP.pdf",
            },
            "a quoted page opens in the dashboard copy at that page",
        )

    def test_define_versions_state_derivations_where_each_version_keeps_them(self):
        # Define 1.0 has no MethodDef: its derivation is the ItemDef Comment.
        codelist = '<CodeList OID="CL.GR"><CodeListItem CodedValue="&lt;25&#160;"><Decode><TranslatedText>Normal</TranslatedText></Decode></CodeListItem></CodeList>'
        cases = [
            (
                "1.0",
                '<ItemDef OID="ADSL.BMIGR" Name="BMIGR" DataType="text" Origin="Derived" Comment="Normal if BMIBL &lt;25" def:Label="BMI group"><CodeListRef CodeListOID="CL.GR"/></ItemDef>'
                + codelist
                + '<ItemGroupDef OID="IG.ADSL" Name="ADSL"><ItemRef ItemOID="ADSL.BMIGR"/></ItemGroupDef>',
                {"method": "", "comment": "Normal if BMIBL <25"},
                "Label: BMI group\nData type: text\nOrigin: Derived\nComment: Normal if BMIBL <25\nCodelist CL.GR: <25 = Normal",
            ),
            (
                "2.0",
                '<ItemDef OID="IT.BMIGR" Name="BMIGR" DataType="text" def:CommentOID="COM.GR"><Description><TranslatedText>BMI group</TranslatedText></Description><CodeListRef CodeListOID="CL.GR"/></ItemDef>'
                + codelist
                + '<MethodDef OID="MT.GR" Name="Group"><Description><TranslatedText>Normal if BMIBL &lt;25</TranslatedText></Description></MethodDef>'
                + '<def:CommentDef OID="COM.GR"><Description><TranslatedText>See SAP 9.2</TranslatedText></Description></def:CommentDef>'
                + '<ItemGroupDef OID="IG.ADSL" Name="ADSL"><ItemRef ItemOID="IT.BMIGR" MethodOID="MT.GR"/></ItemGroupDef>',
                {"method": "Normal if BMIBL <25", "comment": "See SAP 9.2"},
                "Label: BMI group\nData type: text\nMethod: Normal if BMIBL <25\nComment: See SAP 9.2\nCodelist CL.GR: <25 = Normal",
            ),
        ]
        for version, body, expected, text in cases:
            with self.subTest(version=version), tempfile.TemporaryDirectory() as tmp:
                define = Path(tmp) / "define-adam.xml"
                define.write_text(
                    '<ODM xmlns="http://www.cdisc.org/ns/odm/v1.3" xmlns:def="http://www.cdisc.org/ns/def/v1.0">'
                    + body
                    + "</ODM>"
                )
                item = define_metadata(define)["ADSL"]["BMIGR"]
                self.assertEqual(
                    {k: item[k] for k in expected}, expected, f"Define {version} derivation text"
                )
                self.assertEqual(
                    {s["id"]: s["text"] for s in document_sections(define, define_metadata(define))},
                    {"ADSL.BMIGR": text},
                    f"Define {version} reading-copy section",
                )

    def test_define_versions_and_report_anchor_actual_source_differences(self):
        for version, definition in [
            (
                "1.0",
                '<ItemDef OID="IT.AGE" Name="AGE" DataType="integer" def:Label="Age in years"/>',
            ),
            (
                "2.0",
                '<ItemDef OID="IT.AGE" Name="AGE" DataType="integer"><Description><TranslatedText>Age in years</TranslatedText></Description></ItemDef>',
            ),
        ]:
            with self.subTest(version=version), tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp)
                study = "study"
                spec_dir = root / study / "spec/yamaa"
                spec_dir.mkdir(parents=True)
                define = root / study / "spec/define/define-adam.xml"
                define.parent.mkdir()
                define.write_text(
                    '<ODM xmlns="http://www.cdisc.org/ns/odm/v1.3" xmlns:def="http://www.cdisc.org/ns/def/v1.0">'
                    + definition
                    + '<ItemGroupDef OID="IG.ADSL" Name="ADSL"><ItemRef ItemOID="IT.AGE"/></ItemGroupDef></ODM>'
                )
                self.assertEqual(
                    define_metadata(define)["ADSL"]["AGE"]["label"], "Age in years"
                )
                out = root / study / "data/adam/adsl.parquet"
                out.parent.mkdir(parents=True)
                pq.write_table(pa.table({"AGE": [65]}), out)
                text = """domain: ADSL
input: {DM: dm.parquet}
output: {path: ../../data/adam/adsl.parquet, columns: [AGE]}
columns:
  - name: AGE
    label: Different age label
    derivation: DM.AGE
"""
                spec = spec_dir / "adsl.yaml"
                spec.write_text(text)
                parsed = yaml.safe_load(text)
                lineage = build_lineage(text, parsed, {"DM": {"AGE"}})
                target = root / "review"
                target.mkdir()
                result = build_report(
                    root, study, [(spec, parsed, lineage)], target, "revision"
                )
                self.assertEqual(
                    [
                        (
                            f["dataset"],
                            f["variable"],
                            f["kind"],
                            f["status"],
                            f["source"]["url"],
                            f["spec"]["line"],
                        )
                        for f in result["findings"]
                    ],
                    [
                        (
                            "ADSL",
                            "AGE",
                            "inconsistent",
                            "Needs review",
                            "documents/study/spec/define/define-adam.xml.html#ADSL.AGE",
                            5,
                        )
                    ],
                )
                self.assertEqual(
                    result["checks"],
                    {"labels": 1, "output_columns": 1, "define_variables": 1},
                )
                self.assertIn(
                    "Not comprehensively reviewed", result["coverage"]["narrative"]
                )
                finding = result["findings"][0]
                self.assertEqual(finding["comparison"], "source_documents")
                self.assertIn("derivation: DM.AGE", finding["spec"]["excerpt"])
                self.assertEqual(
                    finding["data"],
                    {
                        "path": "study/data/adam/adsl.parquet",
                        "summary": 'AGE: int64; 1 rows; 0 missing. Label: (not stored). Example values: ["65"].',
                    },
                )


if __name__ == "__main__":
    unittest.main()
