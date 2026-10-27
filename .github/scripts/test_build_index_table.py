"""Regression checks for the landing-page metrics table builder."""

from types import SimpleNamespace
import unittest

from build_index_table import BEGIN, END, _millions, _percent, on_page_markdown, reference_cell, replace_block


def _page(src_uri):
    return SimpleNamespace(file=SimpleNamespace(src_uri=src_uri))


class IndexTableTests(unittest.TestCase):
    def test_reference_cell_scopes_counts_and_handles_unavailable_references(self):
        cell = reference_cell([5, 216, 2300000], [5, 216, 2300000])
        self.assertIn("Datasets matching reference: **5 / 5 (100%)**", cell)
        self.assertIn("Cells in matching datasets: 2.3M / 2.3M", cell)
        self.assertEqual(reference_cell([0, 0, 0], [0, 0, 0]), "No official reference")

    def test_percent_uses_whole_percent(self):
        self.assertEqual(_percent(18, 20), "90%")
        self.assertEqual(_percent(771, 847), "91%")
        self.assertEqual(_percent(339, 415), "82%")
        self.assertEqual(_percent(5, 5), "100%")
        self.assertEqual(_percent(0, 0), "n/a")

    def test_millions_use_one_decimal(self):
        self.assertEqual(_millions(13701899), "13.7M")
        self.assertEqual(_millions(13177099), "13.2M")
        self.assertEqual(_millions(2291147), "2.3M")

    def test_replace_block_swaps_markers_for_table(self):
        text = "\n".join(["before", BEGIN, "placeholder link", END, "after"])
        updated = replace_block(text, ["new table"])
        self.assertEqual(updated.split("\n"),
                         ["before", "new table", "after"])

    def test_replace_block_requires_one_marker_pair(self):
        with self.assertRaises(ValueError):
            replace_block("no markers here", ["new table"])
        with self.assertRaises(ValueError):
            replace_block("\n".join([BEGIN, "a", BEGIN, "b", END]), ["new table"])

    def test_hook_leaves_other_pages_untouched(self):
        markdown = "## Dataset results\n\n| table |"
        self.assertEqual(on_page_markdown(markdown, _page("studies/cdiscpilot01.md")),
                         markdown)

    def test_hook_leaves_index_without_placeholder_untouched(self):
        markdown = "# Home\n\nNo metrics block here.\n"
        self.assertEqual(on_page_markdown(markdown, _page("index.md")), markdown)


if __name__ == "__main__":
    unittest.main()
