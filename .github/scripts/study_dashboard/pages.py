"""Accessible canonical study pages with progressively enhanced review content."""

import html
import json


def study_page(name, entry, report):
    title = entry["title"]
    page = [
        f"---\ntitle: {json.dumps(title)}\nhide:\n  - toc\n---\n",
        f'<div id="study-dashboard" class="study-dashboard" data-study="{name}">',
        f'<h1>{html.escape(title)}</h1><p>{html.escape(entry["description"])}</p>',
        "<noscript>Enable JavaScript for linked specification and data review. Static validation evidence remains available below.</noscript></div>",
        '\n<details class="dashboard-fallback" markdown="1">\n<summary>Build evidence and reproduction</summary>\n',
        f'[Study source]({entry["source"]}) - [Download validation record](../evidence/{name}.json).',
        "",
    ]
    if report["status"] == "pending":
        page += [
            "## Validation pending",
            "",
            report.get("reason", "Study validation has not run."),
            "",
        ]
    else:
        page += [
            "| Dataset | Rows | Columns | Build | Official comparison |",
            "| --- | ---: | ---: | --- | --- |",
        ]
        for dataset in report["datasets"]:
            state = "Passed" if dataset["comparison"] == "passed" else "Unavailable"
            page.append(
                f'| {dataset["domain"]} | {dataset["rows"]:,} | {dataset["columns"]} | Succeeded | {state} |'
            )
        page += [
            "",
            "## Reproduce",
            "",
            "```bash",
            f"python .github/scripts/validate_yamaa.py {name}",
            "```",
            "",
            f'Generated: `{report["created_utc"]}`. Engine: `yamaa {report["yamaa_version"]}` at `{report["yamaa_revision"]}`.',
            "",
        ]
    if entry.get("pending"):
        page += ["## Remaining coverage", "", ", ".join(entry["pending"]), ""]
    page += [
        "Reference agreement and documentation consistency are separate checks. See the [verification policy](../verification.md).",
        "",
        "</details>",
        "",
    ]
    return "\n".join(page)


def gallery_page(entries, reports):
    lines = [
        "---\ntitle: Pilot study dashboards\nhide:\n  - toc\n---\n",
        '<div id="study-dashboard" class="study-dashboard" data-study="gallery"><h1>Pilot study dashboards</h1>',
        "<noscript>Use the study links below to explore static validation evidence.</noscript></div>",
        '\n<details class="dashboard-fallback" markdown="1"><summary>Study validation records</summary>\n',
        "| Study | Dataset builds | Official comparisons |",
        "| --- | ---: | --- |",
    ]
    for name, entry in entries.items():
        report = reports[name]
        if report["status"] == "pending":
            builds, comparison = "Pending", "Not run"
        else:
            builds = str(len(report["datasets"]))
            passed = sum(d["comparison"] == "passed" for d in report["datasets"])
            comparison = f"{passed} passed" if passed else "Unavailable"
        lines.append(f'| [{entry["title"]}]({name}.md) | {builds} | {comparison} |')
    return "\n".join([*lines, "", "</details>", ""])
