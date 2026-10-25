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
from study_dashboard.documents import define_metadata


class ReviewDataTests(unittest.TestCase):
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
                "spec.BASE": ["BASE_ROW.VALUE"],
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
