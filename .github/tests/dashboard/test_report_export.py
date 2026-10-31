"""The dashboard report stays small and the separate audit preserves every field."""
import json
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))
from study_dashboard.workspace import export_review_report

class ReportExportTests(unittest.TestCase):
    def test_display_report_excludes_raw_audit_but_audit_is_lossless(self):
        display = {"schema_version": 1, "study": "example", "revision": "abc",
                   "review": {"issues": [], "checks": [], "evidence": []},
                   "coverage_items": [], "trace_examples": {}, "documents": []}
        full = {**display, "findings": [{"id": "raw", "evidence": "x" * 10000}],
                "logic_checks": [{"id": "logic"}], "checks": {"labels": 1},
                "coverage": {"narrative": "Review pending"}}
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory)
            export_review_report(target, full)
            self.assertEqual(json.loads((target / "report.json").read_text()), display)
            self.assertEqual(json.loads((target / "audit.json").read_text()), full)
            self.assertLess((target / "report.json").stat().st_size,
                            (target / "audit.json").stat().st_size / 10)
