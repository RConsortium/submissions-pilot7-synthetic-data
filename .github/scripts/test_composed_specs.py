"""Engine-composed parent and include rules remain executable after export."""

import importlib.util
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import yaml

from resolved_specs import execution_project, process_study


@unittest.skipUnless(importlib.util.find_spec("yamaa"), "requires the study's pinned yamaa")
class ExecutableCompositionTests(unittest.TestCase):
    def test_export_combines_layers_applies_overrides_and_executes_the_saved_yaml(self):
        import yamaa

        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary).resolve()

            def write(relative, text):
                path = root / relative
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(text)
                return path

            write("study/data/sdtm/dm.csv", "USUBJID,AGE\nS1,65\nS2,70\n")
            write("study/spec/yamaa/base.yaml", '''yamaa: '1.0'
type: spec
model: ADaM
keys: [USUBJID]
input: {DM: {path: ../../data/sdtm/dm.csv, types: {AGE: int}}}
output: {path: ../../data/adam/adsl.csv, columns: [USUBJID, AGE]}
columns:
  - {name: USUBJID, type: str, label: Subject, derivation: DM.USUBJID}
  - {name: AGE, type: int, label: Age in base, derivation: DM.AGE}
''')
            write("study/spec/yamaa/fragment.yaml", "yamaa: '1.0'\ntype: spec\ncolumns: [{name: AGE, label: Age in fragment}]\n")
            write("study/spec/yamaa/adsl.yaml", '''yamaa: '1.0'
type: spec
domain: ADSL
parent: base.yaml
include: [fragment.yaml]
columns: [{name: AGE, label: Analysis age}]
''')
            write("study/spec/yamaa/project.yaml", "yamaa: '1.0'\ntype: project\nadam: {specs: [adsl.yaml]}\n")
            pin = "a" * 40
            write("study/program/adam/python/requirements.txt",
                  f"yamaa @ git+https://github.com/elong0527/yamaa.git@{pin}\n")
            with patch("resolved_specs.assert_engine_pin", return_value=pin):
                self.assertEqual(process_study(root, "study"), 1)
                self.assertEqual(process_study(root, "study", check=True), 1)
            model = yaml.safe_load((root / "study/spec/yamaa/resolved/adsl.yaml").read_text())
            self.assertEqual((model["type"], "parent" in model, "include" in model), ("spec", False, False))
            self.assertEqual(model["columns"][1], {
                "name": "AGE", "type": "int", "label": "Analysis age", "derivation": "DM.AGE"})
            project = yamaa.project(execution_project(root, "study"))
            self.assertEqual(project.check().status, "succeeded")
            result = project.run("adam")
            self.assertEqual(result.status, "succeeded", result.issues.to_pylist())
            self.assertEqual(result["ADSL"].output.to_pylist(), [
                {"USUBJID": "S1", "AGE": 65}, {"USUBJID": "S2", "AGE": 70}])
