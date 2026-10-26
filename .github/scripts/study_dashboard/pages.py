"""Accessible canonical study pages and the static pilot study report."""

import html
import json

REPO = "https://github.com/RConsortium/submissions-pilot7-synthetic-data"
ENGINE = "https://github.com/elong0527/yamaa"
REVIEW = {"Needs review": "attention", "Not reviewed": "neutral"}
UNMATCHED = {
    "Not compared": "a reference is staged but the comparator did not check it",
    "No reference": "no official reference is staged",
}


def study_page(name, entry, report):
    title = entry["title"]
    page = [
        f"---\ntitle: {json.dumps(title)}\nhide:\n  - toc\n---\n",
        f'<div id="study-dashboard" class="study-dashboard" data-study="{name}">',
        f'<h1>{html.escape(title)}</h1><p>{html.escape(entry["description"])}</p>',
    ]
    if report["status"] == "pending":
        reason = report.get("reason", "Study validation has not run.")
        page.append(f"<p>{html.escape(reason)}</p>")
    page.append(
        "<noscript>Enable JavaScript for linked specification and data review.</noscript></div>"
    )
    return "\n".join(page)


def _metric(value):
    """The dashboard's number format (ui.js metric): millions to one decimal."""
    return f"{value / 1e6:.1f}M" if value >= 1e6 else f"{value:,}"


def _share(matched, total):
    if not total:
        return "No official reference"
    return f"{_metric(matched)} / {_metric(total)} ({100 * matched / total:.0f}%)"


def _status(label, tone):
    return f'<span class="report-status {tone}">{html.escape(label)}</span>'


def _comparison(dataset):
    """Validation compares only the default reference path; a configured one may stay unchecked."""
    if dataset["comparison"] == "passed":
        return "Matched", "good"
    if dataset["reference"]:
        return "Not compared", "attention"
    return "No reference", "neutral"


def _load(bundle):
    """Read the staged bundle, so the report states exactly what the dashboard publishes."""
    index = json.loads((bundle / "index.json").read_text())
    studies = []
    for item in index["studies"]:
        catalog = json.loads((bundle / item["id"] / "catalog.json").read_text())
        report = None
        if catalog["status"] != "pending":
            report = json.loads((bundle / item["id"] / catalog["report"]).read_text())
        studies.append((catalog, report))
    return index, studies


def _inputs(catalog):
    """SDTM domains the specifications read, staged SDTM domains, and other lookups."""
    tables = catalog["tables"]
    used = [tables[i["table"]] for d in catalog["datasets"] for i in d["inputs"]]
    used = list({t["path"]: t for t in used}.values())
    sdtm = [t["domain"] for t in used if "/sdtm/" in t["path"]]
    staged = sum("/sdtm/" in t["path"] for t in tables.values())
    lookups = [
        t["name"] for t in used if "/sdtm/" not in t["path"] and "/adam/" not in t["path"]
    ]
    return sdtm, staged, lookups


def _header(index, studies, validated):
    """The method, then only what this run's evidence shows was compared."""
    datasets = [d for c, _ in validated for d in c["datasets"]]
    matched = sum(d["comparison"] == "passed" for d in datasets)
    pending = len(studies) - len(validated)
    result = (
        f" In this run, the study comparators found {matched} of {len(datasets)} "
        "derived datasets equal to their official ADaM datasets."
        if datasets
        else ""
    )
    if pending:
        result += f" {pending} {'study is' if pending == 1 else 'studies are'} pending validation."
    lines = [
        "<h1>Pilot study report</h1>",
        '<p class="report-lede">AI agents draft yamaa specifications from published '
        "submission packages, and the yamaa engine executes them to derive ADaM datasets "
        f"from staged SDTM data.{html.escape(result)}</p>",
    ]
    if validated:
        runs = [c["validation"] for c, _ in validated]
        day = max(r["created_utc"] for r in runs)[:10]
        engine = runs[0]["yamaa_revision"]
        revision = index["revision"]
        lines.append(
            f'<p class="report-provenance">Validated {html.escape(day)} (UTC) at commit '
            f'<a href="{REPO}/tree/{revision}"><code>{revision[:7]}</code></a> with yamaa '
            f'{html.escape(runs[0]["yamaa_version"])} (engine '
            f'<a href="{ENGINE}/tree/{engine}"><code>{engine[:7]}</code></a>).</p>'
        )
    return lines


def _kpis(studies, validated):
    matched = [sum(c["metrics"]["matched"][i] for c, _ in validated) for i in range(3)]
    reference = [sum(c["metrics"]["reference"][i] for c, _ in validated) for i in range(3)]
    items = sum(len(r["findings"]) for _, r in validated)
    tiles = [("Studies", f"{len(validated)} / {len(studies)}", "validated")]
    for i, name in enumerate(["ADaM datasets", "Columns", "Cells"]):
        tiles.append(
            (
                name,
                f"{_metric(matched[i])} / {_metric(reference[i])}",
                f"{100 * matched[i] / reference[i]:.0f}% matched"
                if reference[i]
                else "no official reference",
            )
        )
    tiles.append(("Review items", str(items), "open questions"))
    return [
        '<dl class="report-kpis">'
        + "".join(
            f"<div><dt>{name}</dt><dd>{value}<span>{html.escape(note)}</span></dd></div>"
            for name, value, note in tiles
        )
        + "</dl>"
    ]


def _heads(studies, link=False):
    cells = []
    for catalog, report in studies:
        title = html.escape(catalog["title"])
        if link:
            title = f'<a href="{catalog["id"]}/">{title}</a>'
        pending = "<small>Pending</small>" if report is None else ""
        cells.append(f'<th scope="col">{title}{pending}</th>')
    return "".join(cells)


def _table(labels, studies, rows, link=False, keep=False):
    """Leading label columns, then one column per study; `keep` prints it unbroken."""
    head = "".join(f'<th scope="col">{label}</th>' for label in labels)
    css = "report-table report-keep" if keep else "report-table"
    return (
        f'<div class="{css}"><table class="report-matrix"><thead><tr>'
        f"{head}{_heads(studies, link)}</tr></thead>"
        f"<tbody>{''.join(rows)}</tbody></table></div>"
    )


def _overview(studies):
    """One column per study, so the submission packages compare side by side."""
    facts = {}
    for catalog, report in studies:
        source = catalog["source"]
        label = source.removeprefix("https://github.com/")
        cells = {
            "Scope": html.escape(catalog["description"]),
            "Upstream": f'<a href="{html.escape(source)}">{html.escape(label)}</a>',
            "Review": f'<a href="{catalog["id"]}/">Open review workspace &#8594;</a>',
        }
        if report is None:
            reason = catalog.get("reason", "Study validation has not run.")
            cells["Scope"] += f"<small>Validation pending. {html.escape(reason)}</small>"
        else:
            sdtm, staged, lookups = _inputs(catalog)
            matched, reference = catalog["metrics"]["matched"], catalog["metrics"]["reference"]
            cells |= {
                "Subjects": _metric(len(catalog["subjects"])),
                "SDTM inputs": f"{len(sdtm)} of {staged} staged domains"
                f"<small>{html.escape(', '.join(sdtm))}</small>",
                "Lookup tables": html.escape(", ".join(lookups)),
                "ADaM datasets matched": _share(matched[0], reference[0]),
                "Columns matched": _share(matched[1], reference[1]),
                "Cells matched": _share(matched[2], reference[2]),
                "Documents": html.escape(", ".join(d["name"] for d in report["documents"])),
            }
        facts[catalog["id"]] = cells
    rows = []
    for name in [
        "Scope", "Upstream", "Subjects", "SDTM inputs", "Lookup tables",
        "ADaM datasets matched", "Columns matched", "Cells matched", "Documents", "Review",
    ]:
        values = [facts[c["id"]].get(name, "") for c, _ in studies]
        if any(values):
            css = ' class="report-screen"' if name == "Review" else ""
            rows.append(
                f'<tr{css}><th scope="row">{name}</th>'
                + "".join(f"<td>{value or '-'}</td>" for value in values)
                + "</tr>"
            )
    return ['<h2 id="studies">Studies</h2>', _table(["Study"], studies, rows, link=True)]


def _descriptions(variants):
    """One Define-XML description, or each variant with the studies that publish it."""
    if len(variants) <= 1:
        return html.escape(next(iter(variants), ""))
    return "".join(
        f"{html.escape(text)}<small>{html.escape(', '.join(titles))}</small>"
        for text, titles in variants.items()
    )


def _matrix(studies):
    """One row per ADaM dataset; datasets shared by more studies come first."""
    found, labels = {}, set()
    for catalog, report in studies:
        if report is None:
            continue
        dimensions = {d["domain"]: d for d in catalog["validation"]["datasets"]}
        for dataset in catalog["datasets"]:
            row = found.setdefault(dataset["name"], {"descriptions": {}, "cells": {}})
            label = catalog["tables"][dataset["output"]].get("description", "")
            if label:
                row["descriptions"].setdefault(label, []).append(catalog["title"])
            size = dimensions[dataset["name"]]
            text, tone = _comparison(dataset)
            labels.add(text)
            row["cells"][catalog["id"]] = (
                _status(text, tone)
                + f'<span class="report-dims">{size["rows"]:,} &#215; {size["columns"]}</span>'
            )
    order = sorted(found, key=lambda n: -len(found[n]["cells"]))
    body = [
        f'<tr><th scope="row">{html.escape(name)}</th>'
        f'<td>{_descriptions(found[name]["descriptions"])}</td>'
        + "".join(
            f'<td class="report-cell">{found[name]["cells"].get(c["id"], "-")}</td>'
            for c, _ in studies
        )
        + "</tr>"
        for name in order
    ]
    return [
        '<h2 id="dataset-results">Dataset results</h2>',
        _table(["Dataset", "Description"], studies, body, keep=True),
        '<p class="report-foot">Status with rows &#215; columns of the yamaa output. '
        "Matched: the study comparator found the output equal to the official ADaM "
        "dataset, labels included, under that study's comparison policy. "
        + "".join(f"{k}: {v}. " for k, v in UNMATCHED.items() if k in labels)
        + "A dash means the dataset is not part of that study.</p>",
    ]


def _review(studies, validated):
    items = {}
    for catalog, report in validated:
        for finding in report["findings"]:
            key = (finding["title"], finding["dataset"], finding["variable"])
            items.setdefault(key, {}).setdefault(catalog["id"], []).append(
                finding["status"]
            )
    lines = []
    if items:
        rows = []
        for (title, dataset, variable), statuses in items.items():
            cells = []
            for catalog, _ in studies:
                found = statuses.get(catalog["id"])
                if not found:
                    cells.append("<td>-</td>")
                    continue
                text = found[0] if len(found) == 1 else f"{len(found)} items"
                link = f'{catalog["id"]}/#{catalog["id"]}/overview'
                cells.append(
                    f'<td class="report-cell"><a href="{link}">'
                    f"{_status(text, REVIEW.get(found[0], 'neutral'))}</a></td>"
                )
            target = ".".join(part for part in (dataset, variable) if part)
            rows.append(
                f'<tr><th scope="row">{html.escape(title)}</th>'
                f'<td>{html.escape(target)}</td>{"".join(cells)}</tr>'
            )
        lines.append(_table(["Item", "Target"], studies, rows))
    else:
        lines.append("<p>No open review items.</p>")
    columns = sum(r["checks"]["output_columns"] for _, r in validated)
    labels = sum(r["checks"]["labels"] for _, r in validated)
    differences = sum(
        f["kind"] == "inconsistent" for _, r in validated for f in r["findings"]
    )
    lines.append(
        f'<p class="report-foot">Metadata checks: {columns:,} declared output columns and '
        f"{labels:,} Define-XML labels compared, {differences:,} "
        f'{"inconsistency" if differences == 1 else "inconsistencies"}. Review items are '
        "open questions for a reviewer, not confirmed defects.</p>"
    )
    # The table and its footnote print on one page.
    return [
        '<h2 id="review-items">Open review items</h2>',
        f'<div class="report-keep">{"".join(lines)}</div>',
    ]


def report_page(bundle):
    """A two-page printable summary of every pilot study, from the staged bundle."""
    index, studies = _load(bundle)
    validated = [(c, r) for c, r in studies if r is not None]
    body = [
        *_header(index, studies, validated),
        *(_kpis(studies, validated) if validated else []),
        *_overview(studies),
        *_review(studies, validated),
        *_matrix(studies),
    ]
    evidence = ", ".join(
        f'[{c["title"]}](../evidence/{c["id"]}.json)' for c, _ in studies
    )
    notes = [
        "- **Matched** is regression evidence against the staged official references,",
        "  not regulatory validation. Build success and reference agreement are",
        "  separate results; see the [verification policy](../verification.md).",
        "- Narrative coverage of the submission documents is partial. Open a study's",
        "  review workspace to inspect specifications, records and source documents,",
        "  and see the [review guide](../review.md).",
        f"- Every figure comes from the published evidence records: {evidence}.",
    ]
    return "\n".join(
        [
            "---\ntitle: Pilot study report\nhide:\n  - toc\n---\n",
            '<div class="study-report" markdown="1">',
            "",
            "\n\n".join(body),
            "",
            '<h2 id="reading">Reading this report</h2>',
            "",
            *notes,
            "",
            "</div>",
            "",
        ]
    )
