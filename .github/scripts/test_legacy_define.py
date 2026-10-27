"""Independent cross-version oracles and mutations; no writer output is captured."""

from pathlib import Path
import tempfile
import unittest
import xml.etree.ElementTree as ET
import yaml

from compare_legacy_define import compare_legacy
from legacy_define import LegacyDocument, NAMESPACES

ROOT = Path(__file__).resolve().parents[2]
FIXTURES = ROOT / ".github/tests/fixtures/legacy-define"
TARGET = {"o": "http://www.cdisc.org/ns/odm/v1.3", "d": "http://www.cdisc.org/ns/def/v2.0"}


class LegacyComparisonTests(unittest.TestCase):
    def comparison(self, edit_source=None, edit_target=None):
        with tempfile.TemporaryDirectory() as directory:
            paths = []
            for name, edit in (("reference.xml", edit_source), ("candidate.xml", edit_target)):
                tree = ET.parse(FIXTURES / name)
                if edit:
                    edit(tree.getroot())
                path = Path(directory) / name
                tree.write(path, encoding="utf-8", xml_declaration=True)
                paths.append(path)
            return compare_legacy(*paths)

    def test_independent_documents_match_supported_fields_but_keep_all_gaps(self):
        result = self.comparison()
        self.assertTrue(result["comparison_completed"])
        self.assertTrue(result["comparable_metadata_equal"])
        self.assertFalse(result["full_reference_reproduced"])
        self.assertFalse(result["byte_identical"])
        self.assertEqual(result["differences"], [])
        expected = {"datasets": 1, "variables": 3, "value_lists": 1, "value_level_entries": 2, "codelists": 1}
        self.assertEqual(result["coverage"], {"reference": expected, "candidate": expected})
        self.assertEqual(result["reference_inventory"]["result_displays"], 1)
        self.assertEqual(result["reference_inventory"]["analysis_results"], 1)
        self.assertEqual(result["field_counts"]["unsupported"], 2)
        self.assertEqual(result["field_counts"]["unresolved"], 1)
        self.assertEqual(result["unresolved"][0]["missing_variables"], ["MISSING"])
        draft = next(g for g in result["unsupported"] if g["kind"] == "draft_analysis_results")
        self.assertIn("proc means data=adsl; var value; run;", draft["xml"])
        self.assertEqual((draft["display_count"], draft["result_count"]), (1, 1))
        order = next(c for c in result["conversions"] if c["rule"] == "relative_value_list_order")
        self.assertEqual((order["reference"], order["expected"]), (["17", "18"], ["1", "2"]))
        label = next(f for f in result["fields"] if f["path"] == "/datasets/ADSL/variables/VALUE/value_level/0/label")
        self.assertEqual((label["status"], label["reference"], label["candidate"]), ("converted", "Test X", "Test X"))
        self.assertEqual(label["reference_object"]["oid"], "I.VALUE.X")
        self.assertEqual(label["candidate_object"]["oid"], "GENERATED.X")
        for field in result["fields"]:
            if field["status"] in {"matched", "converted", "different"}:
                self.assertIsNotNone(field["reference_object"], field["path"])
                self.assertIsNotNone(field["candidate_object"], field["path"])

    def test_mutations_in_each_supported_family_remain_differences(self):
        mutations = [
            ("label", ".//o:ItemDef[@OID='GENERATED.ID']/o:Description/o:TranslatedText", None, "Wrong"),
            ("type", ".//o:ItemDef[@OID='GENERATED.VALUE']", "DataType", "integer"),
            ("length", ".//o:ItemDef[@OID='GENERATED.ID']", "Length", "99"),
            ("precision", ".//o:ItemDef[@OID='GENERATED.VALUE']", "SignificantDigits", "3"),
            ("format", ".//o:ItemDef[@OID='GENERATED.VALUE']", "{" + TARGET["d"] + "}DisplayFormat", "9.2"),
            ("mandatory", ".//o:ItemGroupDef/o:ItemRef", "Mandatory", "No"),
            ("key", ".//o:ItemGroupDef/o:ItemRef", "KeySequence", "3"),
            ("rank", ".//o:CodeList/o:CodeListItem", "Rank", "9"),
            ("decode", ".//o:CodeList/o:CodeListItem/o:Decode/o:TranslatedText", None, "Wrong"),
            ("where", ".//d:WhereClauseDef/o:RangeCheck/o:CheckValue", None, "UNKNOWN"),
            ("comment", ".//d:CommentDef/o:Description/o:TranslatedText", None, "Wrong"),
            ("class", ".//o:ItemGroupDef", "{" + TARGET["d"] + "}Class", "ADAM OTHER"),
            ("standard", ".//o:MetaDataVersion", "{" + TARGET["d"] + "}StandardVersion", "1.1"),
        ]
        for name, xpath, attribute, value in mutations:
            with self.subTest(name=name):
                def edit(root):
                    element = root.find(xpath, TARGET)
                    if attribute:
                        element.set(attribute, value)
                    else:
                        element.text = value
                result = self.comparison(edit_target=edit)
                self.assertFalse(result["comparable_metadata_equal"])
                self.assertTrue(result["differences"])
                self.assertTrue(result["unexpected_differences"])

    def test_inherited_omissions_remain_different_and_keep_parent_evidence(self):
        def inherit(root):
            root.find(".//o:ItemDef[@OID='GENERATED.X']", TARGET).set("SignificantDigits", "1")
        result = self.comparison(edit_target=inherit)
        self.assertFalse(result["comparable_metadata_equal"])
        self.assertEqual(len(result["differences"]), 1)
        self.assertEqual(result["known_gap_difference_count"], 1)
        self.assertEqual(result["unexpected_differences"], [])
        difference = result["differences"][0]
        self.assertEqual((difference["reference"], difference["candidate"]), (None, "1"))
        self.assertEqual(difference["known_gap"]["parent_value"], "1")
        self.assertEqual(result["field_counts"]["different"], 1)

    def test_inheritance_explanation_never_covers_a_wrong_child_or_changed_parent(self):
        def wrong_child(root):
            root.find(".//o:ItemDef[@OID='GENERATED.X']", TARGET).set("SignificantDigits", "9")
        self.assertTrue(self.comparison(edit_target=wrong_child)["unexpected_differences"])

        def changed_parent(root):
            root.find(".//o:ItemDef[@OID='GENERATED.VALUE']", TARGET).set("SignificantDigits", "9")
            wrong_child(root)
        result = self.comparison(edit_target=changed_parent)
        self.assertEqual(result["known_gap_difference_count"], 0)
        self.assertEqual(len(result["unexpected_differences"]), 2)

    def test_legacy_numeric_order_controls_sequence_and_raw_offsets_are_reported(self):
        def reverse_order(root):
            root.find(".//d:ValueListDef/o:ItemRef", NAMESPACES).set("OrderNumber", "99")
        changed = self.comparison(edit_source=reverse_order)
        self.assertFalse(changed["comparable_metadata_equal"])
        self.assertTrue(any("/value_level/" in d["path"] for d in changed["differences"]))

        def offset(root):
            for ref in root.findall(".//d:ValueListDef/o:ItemRef", NAMESPACES):
                ref.set("OrderNumber", str(int(ref.get("OrderNumber")) + 100))
        offset_result = self.comparison(edit_source=offset)
        self.assertTrue(offset_result["comparable_metadata_equal"])
        order = next(c for c in offset_result["conversions"] if c["rule"] == "relative_value_list_order")
        self.assertEqual(order["reference"], ["117", "118"])

    def test_relative_order_does_not_allow_a_mutated_target_order_attribute(self):
        def edit(root):
            root.find(".//d:ValueListDef/o:ItemRef", TARGET).set("OrderNumber", "99")
        result = self.comparison(edit_target=edit)
        self.assertFalse(result["comparable_metadata_equal"])
        self.assertTrue(any(d["path"].endswith("/order") for d in result["differences"]))

    def test_unknown_content_cannot_silently_disappear(self):
        def unknown(root):
            root.find(".//o:ItemDef", NAMESPACES).set("Unexpected", "must remain accounted for")
        result = self.comparison(edit_source=unknown)
        self.assertFalse(result["comparable_metadata_equal"])
        self.assertTrue(any(d["path"].startswith("/unsupported_content") for d in result["differences"]))

    def test_duplicate_text_and_misplaced_known_content_do_not_disappear(self):
        def duplicate(root):
            decode = root.find(".//o:Decode", NAMESPACES)
            ET.SubElement(decode, "{" + NAMESPACES["o"] + "}TranslatedText", {"{http://www.w3.org/XML/1998/namespace}lang": "en"}).text = "Hidden extra decode"
        def misplaced(root):
            item = root.find(".//o:ItemDef", NAMESPACES)
            ET.SubElement(item, "{" + NAMESPACES["o"] + "}ProtocolName").text = "Hidden content"
        def duplicate_globals(root):
            study = root.find("o:Study", NAMESPACES)
            ET.SubElement(study, "{" + NAMESPACES["o"] + "}GlobalVariables")
        for edit in (duplicate, misplaced, duplicate_globals):
            with self.subTest(edit=edit.__name__):
                self.assertFalse(self.comparison(edit_source=edit)["comparable_metadata_equal"])

    def test_unverified_parameter_selectors_are_unresolved_and_not_guessed(self):
        def edit(root):
            root.find(".//o:ItemDef[@OID='I.VALUE.X']", NAMESPACES).set("Name", "UNKNOWN")
        result = self.comparison(edit_source=edit)
        self.assertFalse(result["comparable_metadata_equal"])
        selectors = [x for x in result["unresolved"] if x["reason"] == "No evidenced PARAMCD selector"]
        self.assertEqual(len(selectors), 1)
        self.assertEqual(selectors[0]["oid"], "I.VALUE.X")

    def test_unreferenced_definitions_are_still_reported(self):
        def edit(root):
            md = root.find("o:Study/o:MetaDataVersion", NAMESPACES)
            ET.SubElement(md, "{" + NAMESPACES["o"] + "}ItemDef", {"OID": "UNBOUND", "Name": "UNBOUND", "DataType": "text", "Length": "1"})
        result = self.comparison(edit_source=edit)
        self.assertTrue(any(u.get("oid") == "UNBOUND" for u in result["unresolved"]))
        self.assertFalse(result["full_reference_reproduced"])

    def test_typed_references_are_checked_including_unsupported_analysis_results(self):
        for xpath, attribute, identity in (
            (".//o:CodeListRef", "CodeListOID", "I.ID"),
            (".//a:AnalysisVariable", "ItemOID", "DOES.NOT.EXIST"),
            (".//d:DocumentRef", "leafID", "I.VALUE"),
        ):
            with self.subTest(xpath=xpath):
                def edit(root):
                    root.find(xpath, NAMESPACES).set(attribute, identity)
                with self.assertRaisesRegex(ValueError, "reference"):
                    self.comparison(edit_source=edit)

    def test_conflicting_namespaced_and_ordinary_precision_is_not_ignored(self):
        def edit(root):
            root.find(".//o:ItemDef[@OID='I.VALUE']", NAMESPACES).set("{" + NAMESPACES["d"] + "}SignificantDigits", "9")
        self.assertFalse(self.comparison(edit_source=edit)["comparable_metadata_equal"])

    def test_reference_inventory_and_metadata_are_repeatable(self):
        source = LegacyDocument(FIXTURES / "reference.xml")
        first = source.metadata()
        conversions = list(source.conversions)
        self.assertEqual(source.metadata(), first)
        self.assertEqual(source.conversions, conversions)
        self.assertEqual(source.inventory()["elements"]["ComputationMethod"], 1)

    def test_pilot_01_keeps_derivation_and_historical_metadata_in_each_dataset_yaml(self):
        directory = ROOT / "cdiscpilot01/spec/yamaa"
        project = yaml.safe_load((directory / "project.yaml").read_text())
        self.assertFalse((directory / "submission").exists())
        self.assertEqual(project["adam"]["define_version"], "2.0.0")
        self.assertEqual(project["adam"]["context"], "Other")
        self.assertEqual(project["codelists"], ["codelists.yaml"])
        variables = values = 0
        for filename in project["adam"]["specs"]:
            specification = yaml.safe_load((directory / filename).read_text())
            self.assertEqual(specification["submission"]["mode"], "historical")
            columns = {c["name"]: c for c in specification["columns"]}
            for name in specification["output"]["columns"]:
                column = columns[name]
                # A bare declaration copies its value from the base dataset.
                self.assertTrue("derivation" in column or specification.get("base"))
                self.assertIn("type", column)
                self.assertIn("label", column)
                self.assertIn("data_type", column["submission"])
                self.assertIn("mandatory", column["submission"])
                variables += 1
                for entry in column["submission"].get("value_level", []):
                    self.assertEqual(entry["where"], {"PARAMCD": [entry["id"]]})
                    values += 1
        self.assertEqual((len(project["adam"]["specs"]), variables, values), (10, 415, 903))
        self.assertEqual(len(yaml.safe_load((directory / "codelists.yaml").read_text())["codelists"]), 58)


if __name__ == "__main__":
    unittest.main()
