"""The landing page's PHMPT headline: the block between the overview's markers, or nothing."""
import unittest

import phmpt_headline as hook


class Headline(unittest.TestCase):
    def test_the_block_between_the_markers(self):
        page = f"# Overview\n\n{hook.BEGIN}\n<div>154 / 158</div>\n{hook.END}\n\nMore\n"
        self.assertEqual(hook.headline(page), "<div>154 / 158</div>")

    def test_no_markers_no_block(self):
        self.assertEqual(hook.headline("# Overview\n"), "")
        self.assertEqual(hook.headline(f"{hook.END}\n{hook.BEGIN}\n"), "")


if __name__ == "__main__":
    unittest.main()
