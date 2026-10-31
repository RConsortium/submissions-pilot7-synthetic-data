"""Bold control and panel names in the guide stay aligned with dashboard labels."""
import html
from pathlib import Path
import re
import unittest

ROOT = Path(__file__).resolve().parents[3]

class GuideLabelsTests(unittest.TestCase):
    def test_guide_control_and_panel_labels_exist_in_dashboard(self):
        code = html.unescape("\n".join(p.read_text() for p in
            (ROOT / "docs/assets/dashboard").glob("*.js")))
        code = " ".join(re.sub("<[^>]*>", " ", code).split()).lower()
        for page in (ROOT / "docs/review").glob("*.md"):
            for raw in re.findall(r"\*\*(.+?)\*\*", page.read_text(), re.S):
                label = " ".join(raw.split())
                # These names append the shared list scope at render time.
                parts = label.split(": ")
                if label.endswith(" in list"):
                    parts = [label[:-8], " in list"]
                with self.subTest(page=page.name, label=label):
                    self.assertTrue(all(part.lower() in code for part in parts),
                                    f"Unknown dashboard UI label: {label}")
