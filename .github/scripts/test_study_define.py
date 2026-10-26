"""Define-XML matches require freshly composed, independently compared metadata."""

import hashlib
from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock

from study_define import check_define, version

ROOT = Path(__file__).resolve().parents[2]


class StudyDefineTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.base = self.root / "study"
        self.project_file = self.base / "spec/yamaa/project.yaml"
        self.project_file.parent.mkdir(parents=True)
        self.project_file.write_text("adam: {define: ../../data/adam/define-yamaa.xml}\n")
        self.reference = self.base / "spec/define/define-adam.xml"
        self.reference.parent.mkdir(parents=True)
        self.reference.write_bytes((ROOT / "submission-pilot3/spec/define/define-adam.xml").read_bytes())
        self.candidate = self.base / "data/adam/define-yamaa.xml"
        self.candidate.parent.mkdir(parents=True)
        self.project = Mock()
        self.project.submission.return_value.status = "succeeded"

    def test_compares_native_output_and_preserves_metadata_differences(self):
        for changed in (False, True):
            with self.subTest(changed=changed):
                xml = self.reference.read_text()
                if changed:
                    xml = xml.replace("Test datasets created", "Changed datasets created", 1)
                    self.assertNotEqual(xml, self.reference.read_text())
                self.project.submission.return_value.save.side_effect = lambda: self.candidate.write_text(xml)
                record = check_define(self.root, "study", self.project)
                self.assertEqual(record["comparison"], "different" if changed else "matched")
                self.assertEqual(record["adam_version"], "2.0.0")
                self.assertEqual(record["candidate_version"], "2.0.0")
                self.assertEqual(record["metadata"]["metadata_equivalent"], not changed)
                self.assertEqual(record["candidate_sha256"], hashlib.sha256(self.candidate.read_bytes()).hexdigest())
                self.assertEqual(record["reference_sha256"], hashlib.sha256(self.reference.read_bytes()).hexdigest())

    def test_no_native_export_is_explicitly_not_compared(self):
        self.project_file.write_text("adam: {specs: [adsl.yaml]}\n")
        self.reference.write_bytes((ROOT / "cdiscpilot01/spec/define/define-adam.xml").read_bytes())
        record = check_define(self.root, "study", self.project)
        self.assertEqual(record["comparison"], "not_compared")
        self.assertEqual(record["adam_version"], "1.0.0")
        self.project.submission.assert_not_called()
        self.assertIsNone(version(self.base / "missing.xml"))

    def test_failed_composition_cannot_reuse_an_old_candidate(self):
        self.candidate.write_bytes(self.reference.read_bytes())
        self.project.submission.return_value.status = "failed"
        with self.assertRaises(ValueError):
            check_define(self.root, "study", self.project)
        self.assertFalse(self.candidate.exists())

    def test_refuses_to_overwrite_the_reference(self):
        self.project_file.write_text("adam: {define: ../define/define-adam.xml}\n")
        original = self.reference.read_bytes()
        with self.assertRaisesRegex(ValueError, "separate from the reference"):
            check_define(self.root, "study", self.project)
        self.assertEqual(self.reference.read_bytes(), original)
        self.project.submission.assert_not_called()
