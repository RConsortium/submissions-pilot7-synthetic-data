"""Scoped value, lookup, row-selection and aggregate-local dependency expectations."""

from pathlib import Path
import sys
import unittest

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))
from study_dashboard.lineage import build_lineage
from study_dashboard.references import References


def trace(text, schemas):
    return build_lineage(text, yaml.safe_load(text), schemas)


class LineageTests(unittest.TestCase):
    def test_unused_inputs_and_display_order_do_not_become_value_dependencies(self):
        result = trace(
            """domain: ADSL
input:
  DM: dm.parquet
  EX: {path: ex.parquet, key: [USUBJID]}
  QS: {path: qs.parquet, key: [USUBJID]}
base: DM
filter: "DM.KEEP = 'Y'"
output: {columns: [TRT01AN, TRTSDT], order_by: [{variable: SORT_DATE}]}
columns:
  - {name: USUBJID, derivation: DM.SUBJECT_KEY}
  - name: TRT01AN
    derivation: {mapping: {source: DM.ARM, dict: {Placebo: 0, AGE: 54}}}
  - {name: TRTSDT, derivation: {aggregate: 'MIN(EX.EXSTDTC)'}}
  - {name: SORT_DATE, derivation: QS.QSDTC}
""",
            {
                "DM": {"SUBJECT_KEY", "USUBJID", "ARM", "KEEP"},
                "EX": {"USUBJID", "EXSTDTC"},
                "QS": {"USUBJID", "QSDTC"},
            },
        )
        self.assertEqual(
            result["edges"],
            {
                "spec.SORT_DATE": ["DM.KEEP", "QS.QSDTC", "QS.USUBJID", "spec.USUBJID"],
                "spec.TRT01AN": ["DM.ARM", "DM.KEEP"],
                "spec.TRTSDT": ["DM.KEEP", "EX.EXSTDTC", "EX.USUBJID", "spec.USUBJID"],
                "spec.USUBJID": ["DM.KEEP", "DM.SUBJECT_KEY"],
                "output.TRT01AN": ["spec.TRT01AN"],
                "output.TRTSDT": ["spec.TRTSDT"],
            },
        )
        self.assertEqual(result["output_order"], ["spec.SORT_DATE"])
        self.assertEqual(result["unresolved"], [])

    def test_implicit_keys_match_output_columns_in_columns_and_driver_fields_in_rows(
        self,
    ):
        index = References(
            {
                "input": {"DM": "dm", "EX": {"key": ["USUBJID"]}},
                "base": "DM",
                "columns": [{"name": "USUBJID"}],
            },
            {"DM": {"USUBJID"}, "EX": {"USUBJID", "VALUE"}},
        )
        for row, match in [(False, "spec.USUBJID"), (True, "DM.USUBJID")]:
            with self.subTest(row=row):
                self.assertEqual(
                    index.read("EX.VALUE", driver="DM", row=row),
                    {"EX.VALUE", "EX.USUBJID", match},
                )

    def test_explicit_aggregate_keys_replace_input_defaults_and_retain_filter_fields(
        self,
    ):
        result = trace(
            """domain: ADSL
input: {DM: dm.parquet, EX: {path: ex.parquet, key: [UNUSED_KEY]}}
base: DM
output: {columns: [START]}
columns:
  - {name: USUBJID, derivation: DM.ID}
  - name: START
    derivation:
      aggregate:
        key: {EXKEY: USUBJID}
        filter: 'EX.DOSE > 0'
        expr: 'MIN(EX.DATE)'
""",
            {"DM": {"ID"}, "EX": {"UNUSED_KEY", "EXKEY", "DOSE", "DATE"}},
        )
        self.assertEqual(
            result["edges"],
            {
                "spec.START": ["EX.DATE", "EX.DOSE", "EX.EXKEY", "spec.USUBJID"],
                "spec.USUBJID": ["DM.ID"],
                "output.START": ["spec.START"],
            },
        )
        self.assertEqual(result["unresolved"], [])

    def test_selected_lookup_field_does_not_inherit_sibling_derivations_or_fake_source_fields(
        self,
    ):
        result = trace(
            """domain: ADX
input: {DM: dm.parquet, LB: {path: lb.parquet, key: [UNUSED_KEY]}, OTHER: other.parquet}
base: DM
output: {columns: [RESULT]}
intermediates:
  - id: PICK
    dataset: LB
    key: {SUBJECT: SUBJID}
    filter: "LB.FLAG = 'Y'"
    order_by: [{variable: LB.SEQ}]
    keep: first
    columns: [VALUE, UNUSED]
    derivations:
      VALUE: {derive: 'LB.VALUE * 2'}
      UNUSED: OTHER_LOOKUP.TEXT
  - id: OTHER_LOOKUP
    dataset: OTHER
    key: {SUBJECT: SUBJID}
columns:
  - {name: SUBJID, derivation: DM.ID}
  - {name: RESULT, derivation: PICK.VALUE}
""",
            {
                "DM": {"ID"},
                "LB": {"SUBJECT", "UNUSED_KEY", "VALUE", "FLAG", "SEQ"},
                "OTHER": {"SUBJECT", "TEXT"},
            },
        )
        self.assertEqual(
            result["edges"],
            {
                "intermediate.PICK": ["LB.FLAG", "LB.SEQ", "LB.SUBJECT", "spec.SUBJID"],
                "PICK.UNUSED": ["OTHER_LOOKUP.TEXT", "intermediate.PICK"],
                "PICK.VALUE": ["LB.VALUE", "intermediate.PICK"],
                "intermediate.OTHER_LOOKUP": ["OTHER.SUBJECT", "spec.SUBJID"],
                "OTHER_LOOKUP.SUBJECT": ["OTHER.SUBJECT", "intermediate.OTHER_LOOKUP"],
                "OTHER_LOOKUP.TEXT": ["OTHER.TEXT", "intermediate.OTHER_LOOKUP"],
                "spec.RESULT": ["PICK.VALUE"],
                "spec.SUBJID": ["DM.ID"],
                "output.RESULT": ["spec.RESULT"],
            },
        )
        self.assertEqual(result["unresolved"], [])

    def test_lookup_filter_keeps_hidden_derived_field_dependencies(self):
        result = trace(
            """domain: ADX
input: {LB: lb.parquet, ALT: alt.parquet}
base: LB
output: {columns: [RESULT]}
intermediates:
  - id: PICK
    dataset: LB
    key: [USUBJID]
    columns: [VALUE]
    filter: "KEEP = 'Y'"
    derivations: {KEEP: FLAGS.FLAG}
  - id: FLAGS
    dataset: ALT
    key: [USUBJID]
columns:
  - {name: USUBJID, derivation: LB.USUBJID}
  - {name: RESULT, derivation: PICK.VALUE}
""",
            {"LB": {"USUBJID", "VALUE"}, "ALT": {"USUBJID", "FLAG"}},
        )
        self.assertEqual(
            result["edges"],
            {
                "intermediate.PICK": ["LB.USUBJID", "PICK.KEEP", "spec.USUBJID"],
                "PICK.KEEP": ["FLAGS.FLAG", "intermediate.PICK"],
                "PICK.VALUE": ["LB.VALUE", "intermediate.PICK"],
                "intermediate.FLAGS": ["ALT.USUBJID", "spec.USUBJID"],
                "FLAGS.FLAG": ["ALT.FLAG", "intermediate.FLAGS"],
                "FLAGS.USUBJID": ["ALT.USUBJID", "intermediate.FLAGS"],
                "spec.RESULT": ["PICK.VALUE"],
                "spec.USUBJID": ["LB.USUBJID"],
                "output.RESULT": ["spec.RESULT"],
            },
        )
        self.assertEqual(result["unresolved"], [])

    def test_row_overrides_keep_grouping_and_filters_without_the_overridden_root_source(
        self,
    ):
        result = trace(
            """domain: ADX
input: {DM: dm.parquet, EX: {path: ex.parquet, key: [UNUSED_KEY]}}
base: DM
output: {columns: [VALUE, CODE]}
columns:
  - {name: VALUE, derivation: DM.ORIGINAL}
  - {name: CODE, derivation: "'X'"}
rows:
  - id: grouped
    dataset: EX
    group_by: [EX.SUBJECT]
    filter: 'VALUE > 0'
    derivations: {VALUE: {aggregate: 'SUM(EX.DOSE)'}}
""",
            {"DM": {"ORIGINAL"}, "EX": {"UNUSED_KEY", "SUBJECT", "DOSE"}},
        )
        self.assertEqual(
            result["edges"],
            {
                "row.grouped": ["EX.SUBJECT", "spec.VALUE"],
                "spec.CODE": ["row.grouped"],
                "spec.VALUE": ["EX.DOSE", "row.grouped"],
                "output.VALUE": ["spec.VALUE"],
                "output.CODE": ["spec.CODE"],
            },
        )

    def test_aggregate_local_names_shadow_output_names_and_unused_locals_are_not_traced(
        self,
    ):
        result = trace(
            """domain: ADX
input: {DM: dm.parquet, EX: {path: ex.parquet, key: [USUBJID]}, QS: qs.parquet}
base: DM
output: {columns: [RESULT]}
columns:
  - {name: USUBJID, derivation: DM.ID}
  - {name: END, derivation: QS.QSDTC}
  - name: RESULT
    derivation:
      aggregate:
        derivations:
          END: {type: str, derivation: EX.EXENDTC}
          UNUSED: QS.QSDTC
        expr: 'MAX(END)'
""",
            {"DM": {"ID"}, "EX": {"USUBJID", "EXENDTC"}, "QS": {"QSDTC"}},
        )
        self.assertEqual(
            result["edges"],
            {
                "spec.END": ["QS.QSDTC"],
                "spec.RESULT": ["EX.EXENDTC", "EX.USUBJID", "spec.USUBJID"],
                "spec.USUBJID": ["DM.ID"],
                "output.RESULT": ["spec.RESULT"],
            },
        )
        self.assertEqual(result["unresolved"], [])


if __name__ == "__main__":
    unittest.main()
