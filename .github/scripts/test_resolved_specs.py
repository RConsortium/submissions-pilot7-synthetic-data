"""Saved resolutions remain portable and reject source, pin and model drift."""

from copy import deepcopy
import json
from pathlib import Path
import shutil
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

import yaml

from composed_specs import project as composed_project, specification, write_yaml
from resolved_specs import digest, execution_project, load_snapshot, process_study, snapshot, snapshot_path, specification_packet
from study_dashboard.specifications import inspection_specification

PIN = "a" * 40


class ResolvedSnapshotTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name).resolve()
        self.path = self.root / "study/spec/yamaa/adae.yaml"
        self.path.parent.mkdir(parents=True)
        self.path.write_text("domain: ADAE\nparent: ../../../spec/yamaa/base.yaml\n")
        self.parent = self.root / "spec/yamaa/base.yaml"
        self.parent.parent.mkdir(parents=True)
        self.parent.write_text("columns: []\n")
        self.project = self.path.parent / "project.yaml"
        self.project.write_text("adam: {specs: [adae.yaml]}\ncodelists: [codes.yaml]\n")
        self.codes = self.path.parent / "codes.yaml"
        self.codes.write_text("codelists: {}\n")
        self.requirements = self.root / "study/program/adam/python/requirements.txt"
        self.requirements.parent.mkdir(parents=True)
        self.requirements.write_text(f"yamaa @ git+https://github.com/elong0527/yamaa.git@{PIN}#subdirectory=python\n")
        self.model = {"domain": "ADAE", "output": {"path": "../../data/adam/adae.parquet"}, "columns": []}
        self.resolved = {
            "format": "yamaa.resolved-specification", "artifact_version": 1,
            "replay": "inspection_only", "entry": str(self.path), "project": str(self.project),
            "entries": [{"entry": str(self.path), "language_version": "1.0",
                         "layers": [str(self.parent), str(self.path)], "mapping_order": {},
                         "origins": {"/domain": {"declaring_source": str(self.path),
                                                  "source_kind": "authored", "generated": False}},
                         "resources": [{"role": "output_data", "spec_path": "output.path",
                                        "location": {"kind": "local", "path": str(self.root / "study/data/adam/adae.parquet")},
                                        "declaring_source": str(self.parent), "base_source": str(self.path),
                                        "owning_entry": str(self.path), "relative_to": "entry",
                                        "written": "../../data/adam/adae.parquet"}],
                         "specification": self.model}],
        }
        self.write_snapshot()

    def test_a_producer_schemas_inherited_layer_is_an_input_even_without_field_origins(self):
        self.path.write_text("domain: ADAE\n")
        producer = self.path.parent / "adsl.yaml"
        producer.write_text("parent: ../../../spec/yamaa/base.yaml\n")
        self.resolved["entries"][0]["layers"] = [str(self.path)]
        self.resolved["entries"][0]["resources"].append({
            "role": "producer_schema", "spec_path": "input.ADSL.schema",
            "location": {"kind": "local", "path": str(producer)}})
        self.model["input"] = {"ADSL": {"schema": "adsl.yaml"}}
        self.write_snapshot()
        self.parent.write_text("columns: [{name: CHANGED}]\n")
        with self.assertRaisesRegex(ValueError, "input changed: spec/yamaa/base.yaml"):
            load_snapshot(self.root, self.path)

    def write_snapshot(self):
        target = snapshot_path(self.root, self.path)
        record = snapshot(self.root, "study", self.resolved, PIN, "test")
        write_yaml(target, specification(self.root, record["resolved"]["entries"][0], target, {}))
        project = execution_project(self.root, "study")
        write_yaml(project, composed_project(yaml.safe_load(self.project.read_text()), self.project, project))
        record["files"] = {target.relative_to(self.root).as_posix(): digest(target),
                           project.relative_to(self.root).as_posix(): digest(project)}
        target.with_suffix(".inspection.json").write_text(
            json.dumps(record, sort_keys=True, ensure_ascii=True, separators=(",", ":")) + "\n")

    def test_relocation_preserves_the_complete_artifact_and_written_paths(self):
        other = self.root / "another-checkout"
        shutil.copytree(self.root / "study", other / "study")
        shutil.copytree(self.root / "spec", other / "spec")
        loaded = load_snapshot(other, other / "study/spec/yamaa/adae.yaml")
        expected = deepcopy(self.resolved)
        expected["entry"] = str(other / self.path.relative_to(self.root))
        expected["project"] = str(other / self.project.relative_to(self.root))
        entry = expected["entries"][0]
        entry["entry"] = expected["entry"]
        entry["layers"] = [str(other / p.relative_to(self.root)) for p in [self.parent, self.path]]
        entry["origins"]["/domain"]["declaring_source"] = expected["entry"]
        resource = entry["resources"][0]
        for key in ["declaring_source", "base_source", "owning_entry"]:
            resource[key] = str(other / Path(resource[key]).relative_to(self.root))
        resource["location"]["path"] = str(other / "study/data/adam/adae.parquet")
        self.assertEqual(loaded, expected)
        self.assertNotIn(str(self.root), snapshot_path(self.root, self.path).read_text())

    def test_changed_or_missing_sources_and_project_context_refuse_a_saved_model(self):
        for source in [self.path, self.parent, self.project, self.codes, self.requirements]:
            original = source.read_text()
            for changed in [original + "# changed\n", None]:
                with self.subTest(source=source.name, changed=changed is not None):
                    if changed is None:
                        source.unlink()
                    else:
                        source.write_text(changed)
                    with self.assertRaises((ValueError, FileNotFoundError)):
                        load_snapshot(self.root, self.path)
                    source.write_text(original)

    def test_missing_snapshot_and_changed_engine_pin_require_regeneration(self):
        target = snapshot_path(self.root, self.path)
        target.unlink()
        with self.assertRaisesRegex(ValueError, "missing resolved snapshot"):
            load_snapshot(self.root, self.path)
        self.write_snapshot()
        self.requirements.write_text(self.requirements.read_text().replace(PIN, "b" * 40))
        with self.assertRaisesRegex(ValueError, "different engine pin"):
            load_snapshot(self.root, self.path)

    def test_snapshot_changes_after_validation_refuse_publication(self):
        output = self.root / "study/data/adam/adae.parquet"
        output.parent.mkdir(parents=True)
        output.write_bytes(b"validated output")
        packet = specification_packet(self.root, self.path)
        record = {"domain": "ADAE", "resolved_specification": packet}
        inventory = {p.relative_to(self.root).as_posix(): "hash" for p in self.root.rglob("*") if p.is_file()}
        saved = yaml.safe_load(snapshot_path(self.root, self.path).read_text())
        self.assertEqual(inspection_specification(self.root, self.path, record, inventory)[0], saved)
        target = snapshot_path(self.root, self.path)
        target.write_text(target.read_text() + "# changed after validation\n")
        with self.assertRaisesRegex(ValueError, "specification or project changed"):
            inspection_specification(self.root, self.path, record, inventory)

    def test_inspection_record_and_composed_project_cannot_change_after_validation(self):
        output = self.root / "study/data/adam/adae.parquet"
        output.parent.mkdir(parents=True)
        output.write_bytes(b"validated output")
        packet = specification_packet(self.root, self.path)
        record = {"domain": "ADAE", "resolved_specification": packet}
        inventory = {p.relative_to(self.root).as_posix(): "hash" for p in self.root.rglob("*") if p.is_file()}
        inspection = snapshot_path(self.root, self.path).with_suffix(".inspection.json")
        for path in [inspection, execution_project(self.root, "study")]:
            with self.subTest(path=path.name):
                original = path.read_text()
                if path == inspection:
                    changed = json.loads(original)
                    changed["yamaa_version"] = "changed after validation"
                    path.write_text(json.dumps(changed))
                else:
                    path.write_text(original + "# changed after validation\n")
                with self.assertRaisesRegex(ValueError, "changed"):
                    inspection_specification(self.root, self.path, record, inventory)
                path.write_text(original)

    def test_engine_comparison_refuses_model_drift_and_obsolete_specs(self):
        engine = SimpleNamespace(__version__="test", project=lambda _: SimpleNamespace(
            spec=lambda _: SimpleNamespace(resolve=lambda: self.resolved),
            check=lambda: SimpleNamespace(status="succeeded")))
        with patch.dict(sys.modules, yamaa=engine), patch("resolved_specs.assert_engine_pin", return_value=PIN):
            self.assertEqual(process_study(self.root, "study", check=True), 1)
            target = snapshot_path(self.root, self.path)
            text = target.read_text().replace("domain: ADAE", "domain: WRONG")
            target.write_text(text)
            with self.assertRaisesRegex(ValueError, "stale or missing"):
                process_study(self.root, "study", check=True)
            process_study(self.root, "study")
            extra = target.with_name("obsolete.yaml")
            extra.write_text("obsolete\n")
            with self.assertRaisesRegex(ValueError, "obsolete.yaml"):
                process_study(self.root, "study", check=True)
            process_study(self.root, "study")
            self.assertFalse(extra.exists())


if __name__ == "__main__":
    unittest.main()
