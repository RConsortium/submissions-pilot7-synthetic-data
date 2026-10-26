"""Independent regressions for the pilot metadata comparison and unified specs."""

import importlib.util
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
import xml.etree.ElementTree as ET
import yaml

ROOT = Path(__file__).resolve().parents[2]
REFERENCE = ROOT / "submission-pilot3/spec/define/define-adam.xml"
SOURCE = ROOT / ".github/scripts/define_metadata.py"
spec = importlib.util.spec_from_file_location("pilot3_define_compare", SOURCE)
comparison = importlib.util.module_from_spec(spec)
spec.loader.exec_module(comparison)
NS = {"o": comparison.ODM, "d": "http://www.cdisc.org/ns/def/v2.0"}


class DefineComparisonTests(unittest.TestCase):
    def modified(self, edit):
        with TemporaryDirectory() as directory:
            tree = ET.parse(REFERENCE)
            edit(tree.getroot())
            candidate = Path(directory) / "define.xml"
            tree.write(candidate, encoding="utf-8", xml_declaration=True)
            return comparison.compare(REFERENCE, candidate)

    def test_reference_is_equal_to_itself_with_complete_inventory(self):
        for study in ("submission-pilot3", "submission-pilot5"):
            with self.subTest(study=study):
                reference = ROOT / study / "spec/define/define-adam.xml"
                result = comparison.compare(reference, reference)
                self.assertEqual((result["metadata_equivalent"], result["byte_identical"], result["coverage"], result["differences"]),
                                 (True, True, {"datasets": 5, "variables": 216, "value_level_entries": 15, "codelists": 36}, []))

    def test_changes_to_each_metadata_family_are_detected(self):
        cases = [
            ("variable label", ".//o:ItemDef/o:Description/o:TranslatedText", None, "Changed label"),
            ("variable type", ".//o:ItemDef", "DataType", "float"),
            ("key", ".//o:ItemGroupDef/o:ItemRef", "KeySequence", "9"),
            ("codelist value", ".//o:CodeList/o:CodeListItem", "CodedValue", "NEW_CODE"),
            ("codelist decode", ".//o:CodeList/o:CodeListItem/o:Decode/o:TranslatedText", None, "Changed decode"),
            ("codelist ordering", ".//o:CodeList/o:CodeListItem", "OrderNumber", "999"),
            ("value-level condition", ".//d:WhereClauseDef/o:RangeCheck/o:CheckValue", None, "UNKNOWN_PARAM"),
            ("origin", ".//o:ItemDef/d:Origin", "Type", "Assigned"),
            ("comment", ".//d:CommentDef/o:Description/o:TranslatedText", None, "Changed comment"),
            ("document link", ".//d:leaf", "{" + comparison.XLINK + "}href", "wrong.pdf"),
        ]
        for label, xpath, attribute, value in cases:
            with self.subTest(label=label):
                def edit(root):
                    element = root.find(xpath, NS)
                    if attribute:
                        element.set(attribute, value)
                    else:
                        element.text = value
                result = self.modified(edit)
                self.assertFalse(result["metadata_equivalent"], label)
                self.assertTrue(result["differences"], label)

    def test_shared_method_is_checked_at_every_binding(self):
        root = ET.parse(REFERENCE).getroot()
        expected = len(root.findall(".//o:ItemRef[@MethodOID='MT.ADADAS.AVAL']", NS))
        def edit(root):
            root.find(".//o:MethodDef[@OID='MT.ADADAS.AVAL']/o:Description/o:TranslatedText", NS).text = "Changed algorithm"
        result = self.modified(edit)
        affected = [d for d in result["differences"] if d["path"].endswith("/method/description")]
        self.assertEqual(len(affected), expected)

    def test_value_level_label_is_checked(self):
        def edit(root):
            root.find(".//o:ItemDef[@OID='IT.ADADAS.AVAL.ADADAS.PARAMCD.EQ.ACITM01']/o:Description/o:TranslatedText", NS).text = "Wrong test"
        result = self.modified(edit)
        self.assertEqual(len(result["differences"]), 1)
        self.assertIn("/value_level/0/label", result["differences"][0]["path"])

    def test_renaming_object_ids_preserves_metadata_and_resolves_every_link(self):
        def edit(root):
            identities = {e.get("OID") or e.get("ID") for e in root.iter() if e.get("OID") or e.get("ID")}
            for element in root.iter():
                for key, value in list(element.attrib.items()):
                    if value in identities:
                        element.set(key, "RENAMED." + value)
        result = self.modified(edit)
        self.assertTrue(result["metadata_equivalent"])
        self.assertFalse(result["byte_identical"])

    def test_dangling_links_and_duplicate_ids_are_refused(self):
        for attribute, value in [("ItemOID", "MISSING.ITEM"), ("OID", "IT.ADSL.STUDYID")]:
            with self.subTest(attribute=attribute):
                def edit(root):
                    element = root.find(".//o:ItemGroupDef/o:ItemRef", NS) if attribute == "ItemOID" else root.find(".//o:MethodDef", NS)
                    element.set(attribute, value)
                with self.assertRaises(ValueError):
                    self.modified(edit)

    def test_unused_definitions_and_unknown_attributes_cannot_disappear(self):
        def unused(root):
            metadata = root.find("o:Study/o:MetaDataVersion", NS)
            ET.SubElement(metadata, "{" + comparison.ODM + "}MethodDef", {"OID": "UNUSED", "Name": "Unused method", "Type": "Computation"})
        def unknown(root):
            root.find(".//o:ItemDef", NS).set("Unexpected", "must be accounted for")
        for edit in (unused, unknown):
            with self.subTest(edit=edit.__name__):
                result = self.modified(edit)
                self.assertFalse(result["metadata_equivalent"])
                self.assertTrue(result["differences"])


class UnifiedSpecificationsTests(unittest.TestCase):
    def test_each_pilot_uses_one_dataset_spec_for_derivations_and_submission(self):
        for study in ("submission-pilot3", "submission-pilot5"):
            with self.subTest(study=study):
                directory = ROOT / study / "spec/yamaa"
                project = yaml.safe_load((directory / "project.yaml").read_text())
                self.assertFalse((directory / "submission").exists())
                self.assertEqual(project["adam"]["define"], "../../data/adam/define-yamaa.xml")
                self.assertEqual(project["codelists"], ["codelists.yaml"])
                count = 0
                for filename in project["adam"]["specs"]:
                    self.assertEqual(Path(filename).parent, Path("."))
                    spec = yaml.safe_load((directory / filename).read_text())
                    self.assertIn("submission", spec)
                    columns = {c["name"]: c for c in spec["columns"]}
                    self.assertEqual({name for name, c in columns.items() if "submission" in c}, set(spec["output"]["columns"]))
                    for name in spec["output"]["columns"]:
                        self.assertIn("origins", columns[name]["submission"])
                        self.assertIn("label", columns[name])
                    count += len(spec["output"]["columns"])
                self.assertEqual(count, 216)

    def test_explicit_blank_terms_still_reject_unlisted_values(self):
        try:
            import yamaa
        except ImportError:
            self.skipTest("The pinned engine is installed in study environments, not the shared PyYAML-only job")
        for value, expected in [("", "succeeded"), ("X", "failed")]:
            with self.subTest(value=value), TemporaryDirectory() as directory:
                root = Path(directory)
                (root / "raw.csv").write_text("ID\nP1\n")
                columns = []
                for name in ("ID", "STATUS"):
                    metadata = {"core": "Cond", "mandatory": name == "ID", "length": 8 if name == "ID" else 1,
                                "origins": [{"type": "Predecessor", "description": "RAW." + name}]}
                    if name == "STATUS":
                        metadata["codelist"] = "YN"
                        metadata["origins"] = [{"type": "Assigned"}]
                    columns.append({"name": name, "type": "str", "label": name,
                                    "derivation": "RAW.ID" if name == "ID" else "'" + value + "'",
                                    "submission": metadata})
                declaration = {
                    "yamaa": "1.0", "type": "spec", "model": "ADaM", "domain": "ADSL", "keys": ["ID"],
                    "input": {"RAW": "raw.csv"}, "base": "RAW",
                    "output": {"path": "adsl.csv", "columns": ["ID", "STATUS"]}, "columns": columns,
                    "submission": {"label": "Subject analysis", "class": "SUBJECT LEVEL ANALYSIS DATASET",
                                   "structure": "One record per subject", "repeating": False},
                }
                project = {"yamaa": "1.0", "type": "project", "adam": {"specs": ["adsl.yaml"]},
                           "codelists": [{"codelists": [{"id": "YN", "name": "Local flags", "items": [
                               {"value": "Y", "decode": "Yes"}, {"value": "", "decode": "Blank"}]}]}]}
                (root / "adsl.yaml").write_text(yaml.safe_dump(declaration))
                (root / "project.yaml").write_text(yaml.safe_dump(project))
                result = yamaa.project(root / "project.yaml").run("adam")
                self.assertEqual(result.status, expected)
                if expected == "succeeded":
                    self.assertEqual(result["ADSL"].output.to_pylist(), [{"ID": "P1", "STATUS": ""}])
                else:
                    self.assertEqual([i["condition"] for i in result.issues.to_pylist()], ["allowed_values_failed"])


if __name__ == "__main__":
    unittest.main()
