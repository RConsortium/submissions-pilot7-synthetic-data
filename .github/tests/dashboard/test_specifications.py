"""Publication of resolved copies, inherited resources and named windows."""

import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import unittest

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))
from study_dashboard.lineage import build_lineage, source_locations
from study_dashboard.specifications import (
    capture_specification, inspection_specification, resource_path,
)


class SpecificationEvidenceTests(unittest.TestCase):
    def test_legacy_reusable_specs_require_fresh_engine_resolution(self):
        for declaration in ["parent: base.yaml", "include: [part.yaml]",
                            "columns: [{copy: {dataset: ADSL, columns: [AGE]}}]",
                            "windows: {W: {order_by: [AGE]}}"]:
            with self.subTest(declaration=declaration), tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp)
                path = root / "spec.yaml"
                path.write_text("domain: TEST\n" + declaration + "\n")
                with self.assertRaisesRegex(ValueError, "rerun validation"):
                    inspection_specification(root, path, {}, {})

    def test_source_changes_and_uninventoried_resources_refuse_publication(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            path = root / "spec.yaml"
            path.write_text("domain: TEST\n")
            record = {"domain": "TEST", "resolved_specification": {
                "schema_version": 1, "model": {"domain": "TEST"},
                "sources": [{"path": "spec.yaml", "text": path.read_text()}],
                "resources": {"input.RAW.path": "raw.csv"},
            }}
            with self.assertRaisesRegex(ValueError, "not inventoried"):
                inspection_specification(root, path, record, {"spec.yaml": "hash"})
            path.write_text("domain: CHANGED\n")
            with self.assertRaisesRegex(ValueError, "source changed"):
                inspection_specification(root, path, record, {"spec.yaml": "hash"})

    def test_copied_columns_share_the_exact_authored_copy_span(self):
        spans = source_locations("""columns:
  - copy:
      dataset: ADSL
      columns: [AGE, SEX]
""")["spans"]
        self.assertEqual(spans, {
            "AGE": {"start": 2, "end": 4, "kind": "columns"},
            "SEX": {"start": 2, "end": 4, "kind": "columns"},
        })

    def test_normalized_handlers_are_literals_even_when_they_name_real_columns(self):
        spec = {"input": {"RAW": "raw.csv"}, "output": {"columns": ["FLAG"]},
                "columns": [{"name": "AGE", "derivation": "RAW.AGE"},
                            {"name": "FLAG", "derivation": {"value": {"flag": {
                                "condition": "RAW.KEEP = 'Y'", "true_value": "AGE",
                                "false_value": "AGE", "missing": "AGE"}}}}]}
        result = build_lineage(yaml.safe_dump(spec), spec, {"RAW": {"AGE", "KEEP"}})
        self.assertEqual(result["edges"]["spec.FLAG"], ["RAW.KEEP"])

    @unittest.skipUnless(importlib.util.find_spec("yamaa"), "requires the study's pinned yamaa")
    def test_pinned_engine_copy_include_and_named_window_publish_the_same_dependencies(self):
        import yamaa

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp).resolve()
            def write(name, text):
                path = root / name
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(text)
                return path

            write("input/dm.csv", "USUBJID,AGE\nS1,70\n")
            write("input/ae.csv", "USUBJID,AESEQ\nS1,2\nS1,1\n")
            producer = write("adsl.yaml", '''yamaa: "1.0"
type: spec
domain: ADSL
keys: [USUBJID]
input: {DM: {path: input/dm.csv, types: {AGE: int}}}
output: {path: adsl.csv, columns: [USUBJID, AGE]}
columns:
  - {name: USUBJID, type: str, label: Subject, derivation: DM.USUBJID}
  - {name: AGE, type: int, label: Age, derivation: DM.AGE}
''')
            write("templates/base.yaml", '''yamaa: "1.0"
type: spec
input:
  AE: {path: ../input/ae.csv, types: {AESEQ: int}}
  ADSL: {path: ../adsl.csv, schema: ../adsl.yaml, key: [USUBJID]}
base: AE
windows:
  EVENT_ORDER: {group_by: [USUBJID], order_by: [AESEQ]}
columns:
  - {name: USUBJID, type: str, derivation: AE.USUBJID}
  - {name: AESEQ, type: int, derivation: AE.AESEQ}
''')
            write("carry.yaml", '''yamaa: "1.0"
type: spec
columns:
  - copy: {dataset: ADSL, columns: [AGE]}
''')
            path = write("spec.yaml", '''yamaa: "1.0"
type: spec
parent: templates/base.yaml
include: [carry.yaml]
domain: ADAE
keys: [USUBJID, AESEQ]
output: {path: adae.csv, columns: [USUBJID, AESEQ, AGE, RN]}
columns:
  - name: RN
    type: int
    derivation: {row_number: {window: EVENT_ORDER}}
''')
            yamaa.spec(producer).run().save()
            run = yamaa.spec(path).run()
            run.save()
            self.assertEqual(run.output.to_pylist(), [
                {"USUBJID": "S1", "AESEQ": 2, "AGE": 70, "RN": 2},
                {"USUBJID": "S1", "AESEQ": 1, "AGE": 70, "RN": 1},
            ])
            packet = capture_specification(root, path, yamaa.spec(path).resolve())
            self.assertNotIn(str(root), json.dumps(packet))
            record = {"domain": "ADAE", "resolved_specification": packet}
            inventory = {p.relative_to(root).as_posix(): "hash" for p in root.rglob("*") if p.is_file()}
            model, sources, resources = inspection_specification(root, path, record, inventory)
            self.assertEqual(resource_path(root, path, resources, "input.AE.path", "unused"), root / "input/ae.csv")
            self.assertTrue({"spec.yaml", "templates/base.yaml", "carry.yaml", "adsl.yaml"}.issubset({s["path"] for s in sources}))
            schemas = {"AE": {"USUBJID", "AESEQ"}, "ADSL": {"USUBJID", "AGE"}}
            graph = build_lineage(path.read_text(), model, schemas)
            self.assertEqual(graph["edges"]["spec.AGE"], ["ADSL.AGE", "ADSL.USUBJID", "spec.USUBJID"])
            self.assertEqual(graph["edges"]["spec.RN"], ["spec.AESEQ", "spec.USUBJID"])
            self.assertEqual(graph["unresolved"], [])
            repository = Path(__file__).resolve().parents[3]
            for study in ["cdiscpilot01", "submission-pilot3", "submission-pilot5"]:
                script = repository / study / "program/adam/python/compare.py"
                module = importlib.util.spec_from_file_location("study_comparison", script)
                comparator = importlib.util.module_from_spec(module)
                module.loader.exec_module(comparator)
                self.assertEqual(comparator._spec_labels(path)["AGE"], "Age", study)
            from verify_derivations import resolve_source
            age = next(c for c in model["columns"] if c["name"] == "AGE")
            self.assertEqual(resolve_source(model, age["derivation"]), "ADSL.AGE")
