"""MkDocs hook: show the PHMPT overview's headline figures on the landing page.

phmpt/scripts/site/build_pages.py writes the figures into docs/phmpt/index.md
between the phmpt-headline markers. The landing page holds only MARK, which
this hook replaces in the rendered page, so no number is written twice and
none is committed to docs/index.md.
"""

from pathlib import Path

MARK = "<!-- phmpt-headline -->"
BEGIN = "<!-- phmpt-headline:begin -->"
END = "<!-- phmpt-headline:end -->"


def headline(overview: str) -> str:
    """The block between the markers of the PHMPT overview, or "" when it has none."""
    start, end = overview.find(BEGIN), overview.find(END)
    if start < 0 or end < start:
        return ""
    return overview[start + len(BEGIN):end].strip()


def on_page_markdown(markdown, page, config, files):
    if page.file.src_uri != "index.md" or MARK not in markdown:
        return markdown
    overview = Path(config["docs_dir"]) / "phmpt" / "index.md"
    block = headline(overview.read_text()) if overview.exists() else ""
    return markdown.replace(MARK, block)
