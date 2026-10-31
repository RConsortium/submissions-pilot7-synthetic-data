"""Synthetic source readiness is distinct from validated pilot derivations."""

import io
import json
from pathlib import Path
import sys
import tarfile
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))
from study_dashboard.synthetic import inventory, build_synthetic
from study_dashboard.domains import domain_labels, domain_keys
from dashboard_nav import study_navigation, synthetic_navigation


class SyntheticTests(unittest.TestCase):
    def test_inventory_reports_sources_and_missing_stages_without_validation_claims(
        self,
    ):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            archive = root / "new-synthetic/data/odm/source.tar.gz"
            archive.parent.mkdir(parents=True)
            with tarfile.open(archive, "w:gz") as target:
                for name, body in [
                    ("data/odm.xml", b"<ODM/>"),
                    ("data/index.html", b"source"),
                    ("data/._odm.xml", b"metadata"),
                ]:
                    member = tarfile.TarInfo(name)
                    member.size = len(body)
                    target.addfile(member, io.BytesIO(body))
            entry = {
                "title": "New synthetic",
                "description": "Develop mappings",
                "archives": ["data/odm/source.tar.gz"],
            }
            result = inventory(root, "new-synthetic", entry, "revision")
            self.assertEqual(result["kind"], "synthetic")
            self.assertEqual([s["count"] for s in result["stages"]], [1, 0, 0, 0])
            self.assertEqual(
                [f["name"] for f in result["archives"][0]["files"]],
                ["data/odm.xml", "data/index.html"],
            )
            self.assertEqual(len(result["archives"][0]["sha256"]), 64)
            self.assertNotIn("validation", result)
            staged = root / "new-synthetic/data/sdtm/dm.csv"
            staged.parent.mkdir(parents=True)
            staged.write_text("USUBJID\n001\n")
            self.assertEqual(
                inventory(root, "new-synthetic", entry, "revision")["stages"][1][
                    "count"
                ],
                1,
            )
            self.assertFalse(
                (root / "data").exists(),
                "inspection must never extract archive members",
            )
            (root / ".github").mkdir()
            (root / ".github/synthetic-studies.json").write_text(
                json.dumps({"new-synthetic": entry})
            )
            (root / ".github/yamaa-studies.json").write_text(
                json.dumps({"pilot": {"title": "Pilot"}})
            )
            destination = root / "bundle"
            records = build_synthetic(root, destination, "revision")
            self.assertEqual(records[0]["archives"], 1)
            self.assertTrue(
                (destination / "synthetic/new-synthetic/catalog.json").exists()
            )
            self.assertEqual(
                synthetic_navigation(root),
                [
                    {"Synthetic data report": "synthetic/index.md"},
                    {"New synthetic": "studies/new-synthetic.md"},
                ],
            )
            self.assertEqual(
                study_navigation(root, []),
                [
                    {"Pilot study report": "studies/index.md"},
                    {"Pilot": "studies/pilot.md#pilot/overview"},
                ],
            )

    def test_domain_names_read_define_1_and_define_2_labels(self):
        for element in [
            '<ItemGroupDef Name="DM" def:Label="Demographics"/>',
            '<ItemGroupDef Name="DM"><Description><TranslatedText>Demographics</TranslatedText></Description></ItemGroupDef>',
        ]:
            with self.subTest(
                element=element
            ), tempfile.TemporaryDirectory() as temporary:
                path = Path(temporary) / "define.xml"
                path.write_text(
                    '<ODM xmlns:def="http://www.cdisc.org/ns/def/v1.0">'
                    + element
                    + "</ODM>"
                )
                self.assertEqual(domain_labels(path), {"DM": "Demographics"})

    def test_domain_keys_use_define_declarations_and_resolve_item_names(self):
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "define.xml"
            self.assertEqual(domain_keys(path), {})
            path.write_text(
                '<ODM xmlns:def="http://www.cdisc.org/ns/def/v1.0">'
                '<ItemGroupDef Name="AE" def:DomainKeys="STUDYID, USUBJID, AESEQ"/>'
                '<ItemGroupDef Name="UNKNOWN"/></ODM>'
            )
            self.assertEqual(
                domain_keys(path),
                {"AE": ["STUDYID", "USUBJID", "AESEQ"], "UNKNOWN": []},
            )
            path.write_text(
                '<ODM xmlns="http://www.cdisc.org/ns/odm/v1.3">'
                '<ItemDef OID="item-one" Name="USUBJID"/>'
                '<ItemDef OID="item-two" Name="AESEQ"/>'
                '<ItemGroupDef Name="AE"><ItemRef ItemOID="item-two" KeySequence="2"/>'
                '<ItemRef ItemOID="item-one" KeySequence="1"/>'
                '<ItemRef ItemOID="not-a-key"/></ItemGroupDef></ODM>'
            )
            self.assertEqual(domain_keys(path), {"AE": ["USUBJID", "AESEQ"]})
