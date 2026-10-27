#!/usr/bin/env python3
"""Render landing-page metrics during the MkDocs build, without editing Markdown.

The table shows fully matched datasets, columns, and cells between the
staged official ADaM references and the yamaa-derived outputs. Numerators
come from validation evidence; denominators come from the staged official
reference parquets (<study>/data/adam/*.parquet, excluding *-yamaa build
outputs).

Usage from the repository root:

    python3 .github/scripts/build_index_table.py

The CLI prints the table for inspection. The MkDocs hook replaces the
pilot-metrics placeholder only in the rendered page. Both use validated
reports from .build/validation and Parquet metadata for reference totals.
"""

import argparse
import json
import os
from pathlib import Path

from study_evidence import catalog, validate_reports
from study_artifacts import verify_report_artifacts
from study_metrics import matched_totals, reference_totals

ROOT = Path(__file__).resolve().parents[2]
REPORTS = ROOT / ".build" / "validation"

BEGIN = "<!-- pilot-metrics:begin -->"
END = "<!-- pilot-metrics:end -->"
HEADER = ["| Study | Status | Datasets | Columns | Cells |",
          "| --- | --- | --- | --- | --- |"]
PENDING_DATASETS = "n/a"


def _percent(matched, total):
    if total <= 0:
        return "n/a"
    return f"{100 * matched / total:.0f}%"


def _millions(value):
    return f"{value / 1e6:.1f}M"


def build_table(root, reports_dir):
    entries = catalog(root)
    reports = {name: json.loads((reports_dir / f"{name}.json").read_text())
               for name in entries}
    validate_reports(root, entries, reports, os.environ.get("GITHUB_SHA"))
    verify_report_artifacts(root, entries, reports)
    rows = []
    total_matched = [0, 0, 0]
    total_reference = [0, 0, 0]
    for name, entry in entries.items():
        if entry.get('category') == 'synthetic':
            continue
        report = reports[name]
        title = entry["title"]
        reference = reference_totals(root, name)
        if not reference[0]:
            if entry["comparison"] == "official":
                raise ValueError(f"{name}: official reference datasets are missing")
            rows.append(f"| [{title}](studies/{name}.md) | Ongoing | "
                        f"{PENDING_DATASETS} | n/a | n/a |")
            continue
        matched = matched_totals(report)
        for i in range(3):
            total_matched[i] += matched[i]
            total_reference[i] += reference[i]
        status = "Done" if matched == reference else "Ongoing"
        rows.append(f"| [{title}](studies/{name}.md) | {status} | "
                    f"{matched[0]} / {reference[0]} ({_percent(matched[0], reference[0])}) | "
                    f"{matched[1]} / {reference[1]} ({_percent(matched[1], reference[1])}) | "
                    f"{_millions(matched[2])} / {_millions(reference[2])} "
                    f"({_percent(matched[2], reference[2])}) |")
    overall = (f"| Overall | - | {total_matched[0]} / {total_reference[0]} "
               f"({_percent(total_matched[0], total_reference[0])}) | "
               f"{total_matched[1]} / {total_reference[1]} "
               f"({_percent(total_matched[1], total_reference[1])}) | "
               f"{_millions(total_matched[2])} / {_millions(total_reference[2])} "
               f"({_percent(total_matched[2], total_reference[2])}) |")
    return HEADER + [overall] + rows


def replace_block(text, table):
    lines = text.split("\n")
    if lines.count(BEGIN) != 1 or lines.count(END) != 1:
        raise ValueError("docs/index.md requires one pair of pilot-metrics markers")
    start = lines.index(BEGIN)
    end = lines.index(END)
    if end < start:
        raise ValueError("pilot-metrics markers are out of order in docs/index.md")
    return "\n".join(lines[:start] + table + lines[end + 1:])


def on_page_markdown(markdown, page, **kwargs):
    """Insert current results into the home page; previews omit the placeholder."""
    if page.file.src_uri != "index.md" or BEGIN not in markdown:
        return markdown
    return replace_block(markdown, build_table(ROOT, REPORTS))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--reports", type=Path, default=REPORTS)
    args = parser.parse_args()
    print("\n".join(build_table(ROOT, args.reports)))


if __name__ == "__main__":
    main()
