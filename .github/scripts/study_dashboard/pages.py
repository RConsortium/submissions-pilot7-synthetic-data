"""Accessible canonical study pages and the static pilot study report."""

import html
import json

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
    """SDTM domains the specifications read and the number of staged SDTM domains."""
    tables = catalog["tables"]
    used = [tables[i["table"]] for d in catalog["datasets"] for i in d["inputs"]]
    used = list({t["path"]: t for t in used}.values())
    sdtm = [t["domain"] for t in used if "/sdtm/" in t["path"]]
    staged = sum("/sdtm/" in t["path"] for t in tables.values())
    return sdtm, staged


def _header(studies, validated):
    """Summarize the agents' work and identify any pending studies."""
    pending = len(studies) - len(validated)
    result = ""
    if pending:
        result += f" {pending} {'study is' if pending == 1 else 'studies are'} pending validation."
    lines = [
        "<h1>Pilot study report</h1>",
        '<p class="report-lede">AI agents create yamaa specifications and derive ADaM '
        "datasets from SDTM data in pilot submission packages. AI agents also check "
        "consistency between the datasets and documents in those packages. "
        f"This report summarizes the findings.{html.escape(result)}</p>",
    ]
    return lines


def _kpis(studies, validated):
    matched = [sum(c["metrics"]["matched"][i] for c, _ in validated) for i in range(3)]
    reference = [sum(c["metrics"]["reference"][i] for c, _ in validated) for i in range(3)]
    items = sum(r["review"]["counts"]["issues"] for _, r in validated)
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


def _table(labels, studies, rows, link=False, keep=False, sections=None):
    """Leading label columns, then one column per study; `keep` prints it unbroken."""
    head = "".join(f'<th scope="col">{label}</th>' for label in labels)
    css = "report-table report-keep" if keep else "report-table"
    body = f"<tbody>{''.join(rows)}</tbody>"
    if sections is not None:
        columns = len(labels) + len(studies)
        body = "".join(
            '<tbody><tr class="report-section">'
            f'<th scope="rowgroup" colspan="{columns}">{title}</th></tr>'
            f"{''.join(items)}</tbody>"
            for title, items in sections if items
        )
    return (
        f'<div class="{css}"><table class="report-matrix"><thead><tr>'
        f"{head}{_heads(studies, link)}</tr></thead>"
        f"{body}</table></div>"
    )


def _overview(studies):
    """One column per study, so the submission packages compare side by side."""
    facts = {}
    for catalog, report in studies:
        source = catalog["source"]
        label = source.removeprefix("https://github.com/")
        cells = {
            "Description": html.escape(catalog["description"]),
            "Source": f'<a href="{html.escape(source)}">{html.escape(label)}</a>',
        }
        if report is None:
            reason = catalog.get("reason", "Study validation has not run.")
            cells["Description"] += f"<small>Validation pending. {html.escape(reason)}</small>"
        else:
            sdtm, staged = _inputs(catalog)
            matched, reference = catalog["metrics"]["matched"], catalog["metrics"]["reference"]
            define = catalog["validation"].get("define_xml", {})
            comparison = define.get("comparison", "not_compared")
            status, tone = {
                "matched": ("Matched", "good"),
                "different": ("Different", "attention"),
                "not_compared": ("Not compared", "neutral"),
            }[comparison]
            adam_version = html.escape(define.get("adam_version") or "-")
            candidate_version = define.get("candidate_version")
            if candidate_version and candidate_version != define.get("adam_version"):
                adam_version += f"<small>Generated: {html.escape(candidate_version)}</small>"
            cells |= {
                "Subjects": _metric(len(catalog["subjects"])),
                "SDTM inputs": f"{len(sdtm)} of {staged} staged domains"
                f"<small>{html.escape(', '.join(sdtm))}</small>",
                "ADaM datasets matched": _share(matched[0], reference[0]),
                "Columns matched": _share(matched[1], reference[1]),
                "Cells matched": _share(matched[2], reference[2]),
                "SDTM Define-XML version": html.escape(define.get("sdtm_version") or "-"),
                "ADaM Define-XML version": adam_version,
                "Define-XML match": _status(status, tone),
                "Documents": html.escape(", ".join(d["name"] for d in report["documents"])),
            }
        facts[catalog["id"]] = cells
    sections = []
    for title, names in [
        ("Study information", ["Description", "Source", "Documents", "Subjects"]),
        ("SDTM", ["SDTM inputs", "SDTM Define-XML version"]),
        ("ADaM", ["ADaM datasets matched", "Columns matched", "Cells matched",
                  "ADaM Define-XML version", "Define-XML match"]),
    ]:
        rows = []
        for name in names:
            values = [facts[c["id"]].get(name, "") for c, _ in studies]
            if any(values):
                label = "Define-XML version" if name.endswith("Define-XML version") else name
                rows.append(
                    f'<tr><th scope="row">{label}</th>'
                    + "".join(f"<td>{value or '-'}</td>" for value in values)
                    + "</tr>"
                )
        sections.append((title, rows))
    return [
        '<h2 id="studies">Studies</h2>',
        _table(["Study"], studies, [], link=True, sections=sections),
        '<p class="report-foot">Versions refer to the published Define-XML. '
        "ADaM matching compares generated metadata with the published source. "
        "Not compared means the study has no Define-XML comparison result.</p>",
    ]


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
            if dataset["name"] == "ADSL":
                label = "Subject-Level Analysis Dataset"
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
        _table(["Dataset", "Description"], studies, body, link=True, keep=True),
        '<p class="report-foot">Status with rows &#215; columns of the yamaa output. '
        "Matched: the study comparator found the output equal to the official ADaM "
        "dataset, labels included, under that study's comparison policy. "
        + "".join(f"{k}: {v}. " for k, v in UNMATCHED.items() if k in labels)
        + "A dash means the dataset is not part of that study.</p>",
    ]


def report_page(bundle):
    """A two-page printable summary of every pilot study, from the staged bundle."""
    _, studies = _load(bundle)
    validated = [(c, r) for c, r in studies if r is not None]
    body = [
        *_header(studies, validated),
        *(_kpis(studies, validated) if validated else []),
        *_overview(studies),
        *_matrix(studies),
    ]
    return "\n".join(
        [
            "---\ntitle: Pilot study report\nhide:\n  - toc\n---\n",
            '<div class="study-report" markdown="1">',
            "",
            "\n\n".join(body),
            "",
            "</div>",
            "",
        ]
    )
