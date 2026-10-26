"""Render a consistency review as Markdown from report.json alone.

Every finding shows the rule it cites, quoted; the document statement with the
clause marked inside its full citation and links to the published reading
copy, the original page or XML lines and the repository; the specification
element with line numbers and the quoted lines marked; the data evidence with
record keys; and the adjudication. Nothing here judges a finding.
"""

import re
from pathlib import PurePosixPath

SEVERITIES = ["conflict", "divergence", "gap", "evidence"]
HEADINGS = {"conflict": "Conflicts", "divergence": "Divergences", "gap": "Gaps", "evidence": "Unverified evidence"}
SUBJECTS_SHOWN = 12
SPECIAL = re.compile(r"([\\`*_\[\]<>|#])")


def normalize(text):
    return " ".join(str(text).split())


def escape(value):
    return SPECIAL.sub(r"\\\1", value)


def text(value):
    """Prose that keeps document characters such as * and < literal."""
    return escape(normalize(value))


def span(lines):
    return f"line {lines[0]}" if lines[0] == lines[1] else f"lines {lines[0]}-{lines[1]}"


def code(value):
    value = str(value)
    fence = "``" if "`" in value else "`"
    return f"{fence}{value}{fence}" if value.strip() else "(blank)"


def value(v):
    if v is None:
        return "(missing)"
    if v == "":
        return "(empty)"
    return code(v)


def link(label, url):
    return f"[{label}]({url})" if url else label


def highlight(context, quote):
    """The full citation with the clause in bold, so a reader sees it in place."""
    context, quote = normalize(context), normalize(quote)
    at = context.find(quote)
    if not quote or at < 0 or quote == context:
        return escape(context)
    return f"{escape(context[:at])}**{escape(quote)}**{escape(context[at + len(quote):])}"


def subjects(keys):
    shown = ", ".join(keys[:SUBJECTS_SHOWN])
    more = len(keys) - SUBJECTS_SHOWN
    return shown + (f" and {more} more" if more > 0 else "")


def location(side):
    document, section = side["document"], side["section"]
    name = PurePosixPath(document).name
    links = side.get("links", {})
    if section.startswith("page-"):
        page = section.removeprefix("page-")
        parts = [link(f"{name}, page {page}", links.get("original")), link("reading copy", links.get("reading_copy")), link("repository file", links.get("repository"))]
    else:
        lines = links.get("original_lines")
        parts = [f"{name}, {code(section)}", link("reading copy", links.get("reading_copy")), link(f"XML lines {lines[0]}-{lines[1]}" if lines else "repository file", links.get("repository"))]
    return " | ".join(parts)


def document_block(side):
    heading = {"states": "Document says", "against": "Another statement says"}[side["role"]]
    out = [f"**{heading}** ({location(side)})", ""]
    out.append("> " + highlight(side["context"], side["quote"]))
    if not side["verified"]:
        out += ["", f"Not found: {text(side['reason'])}."]
    return out + [""]


def spec_block(spec, relation):
    if spec["element"] is None:
        return ["**Specification:** no element defines this variable.", ""]
    lines = spec.get("lines")
    if relation == "absent_in_spec":
        heading = f"**Specification has no counterpart.** The variable's definition, {code(spec['element'])}"
    elif spec.get("quote") is not None:
        heading = f"**Specification says** {code(normalize(spec['quote']))} in {code(spec['element'])}"
    else:
        heading = f"**Specification** element {code(spec['element'])}"
    out = [f"{heading} ({code(spec['path'])}, {link(span(lines or spec['element_lines']), spec.get('url'))})", ""]
    out += excerpt(spec, lines)
    if not spec["verified"]:
        out += ["", f"Not found: {text(spec['reason'])}."]
    return out + [""]


def excerpt(spec, marked=None):
    """Specification lines with their numbers; quoted lines carry a > mark."""
    first, last = spec["element_lines"]
    out = ["```text"]
    for number, line in enumerate(spec["excerpt"].splitlines(), first):
        mark = ">" if marked and marked[0] <= number <= marked[1] else " "
        out.append(f"{number:>{len(str(last))}} {mark} {line}")
    return out + ["```"]


def variable_block(spec):
    """The variable's own definition, when the quoted logic sits in an element it reads."""
    summary = f"How {code(spec['element'])} is defined ({span(spec['element_lines'])})"
    return ["<details>", f"<summary>{summary}</summary>", ""] + excerpt(spec) + ["", "</details>", ""]


def pattern_table(patterns, observed_label):
    out = [f"| Reference | {observed_label} | Records | Subjects |", "| --- | --- | ---: | --- |"]
    for p in patterns:
        observed = "(no record)" if p.get("row_absent") else value(p["observed"])
        out.append(f"| {value(p['reference'])} | {observed} | {p['count']} | {subjects(p['subjects'])} |")
    return out + [""]


def evidence_block(evidence):
    out = []
    for probe in evidence.get("probes", []):
        result = probe["reference"]
        reading = "literal reading" if probe["reading"] == "literal" else f"reading: {text(probe['reading'])}"
        if result["differ"]:
            out += [f"**Data:** probe {code(probe['column'])} ({reading}) differs from the reference on {result['differ']} of {result['compared']} records.", ""]
            out += pattern_table(result["patterns"], "Documented rule")
        else:
            out += [f"**Data:** probe {code(probe['column'])} ({reading}) reproduces the reference on all {result['compared']} records.", ""]
    copy = evidence.get("copy")
    if copy:
        result = copy.get("reference")
        if result and result["differ"]:
            out += [f"**Data:** the reference against {code(copy['source'])}, joined on {', '.join(copy['join'])}: {result['differ']} of {result['compared']} records differ.", ""]
            out += pattern_table(result["patterns"], "Documented source")
        elif copy.get("reason"):
            out += [f"**Data:** {text(copy['reason'])}.", ""]
        if copy.get("spec_derivation") is not None and not copy["spec_matches"]:
            out += [f"The specification derives it as {code(copy['spec_derivation'])}.", ""]
    codelist = evidence.get("codelist")
    if codelist:
        for side in ("reference", "derived"):
            if codelist.get(side):
                out += [f"**Data:** {side} values outside codelist {code(codelist['oid'])}.", "", "| Value | Records | Subjects |", "| --- | ---: | --- |"]
                out += [f"| {value(v['value'])} | {v['count']} | {subjects(v['subjects'])} |" for v in codelist[side]] + [""]
    if evidence.get("not_probed_reason"):
        out += [f"**Not probed:** {text(evidence['not_probed_reason'])}", ""]
    return out


def adjudication_line(adjudication):
    decision = adjudication["decision"]
    if decision == "pending":
        return "**Adjudication:** pending."
    if decision == "stale":
        return f"**Adjudication:** stale. The finding changed after it was judged ({adjudication['previous']}: {text(adjudication['reason'])})."
    return f"**Adjudication:** {decision}. {text(adjudication['reason'])}"


def finding_block(finding):
    rule = finding["rule"]
    out = [f'<a id="{finding["id"]}"></a>', "", f"#### {finding['id']}: {rule['title']}", ""]
    out += [f"> **Rule {rule['id']}** ({finding['severity']}): {text(rule['statement'])}", ""]
    summary = text(finding["summary"]) + (f" {text(finding['note'])}" if finding.get("note") else "")
    out += [f"**Finding:** {finding['variable']} ({text(finding['label'])}). {summary}", ""]
    for side in finding["documents"]:
        out += document_block(side)
    if finding["spec"]:
        out += spec_block(finding["spec"], finding.get("relation"))
    if finding.get("variable_spec"):
        out += variable_block(finding["variable_spec"])
    if finding["evidence"]:
        out += evidence_block(finding["evidence"])
    if finding["interpretations"]:
        out += ["**Interpretations recorded by the extraction agent:**", ""] + [f"- {text(i)}" for i in finding["interpretations"]] + [""]
    if finding["question"]:
        out += [f"**Question for the reviewer:** {text(finding['question'])}", ""]
    out += [adjudication_line(finding["adjudication"]), "", "---", ""]
    return out


def dataset_block(dataset):
    summary = dataset["summary"]
    out = [f"## {dataset['dataset']}", ""]
    sources = [f"specification {code(dataset['specification'])}"]
    for key, author in (("claims", "claims_author"), ("probe", None), ("adjudication", "adjudication_author")):
        if dataset.get(key):
            who = dataset.get(author) if author else None
            sources.append(f"{key} {code(dataset[key])}" + (f" ({who['model']}, {who['date']})" if who else ""))
    out += ["Sources: " + "; ".join(sources) + ".", ""]
    verdicts = ", ".join(f"{k.replace('_', ' ')} {v}" for k, v in summary["verdicts"].items() if v)
    out += [f"Variables: {summary['variables']}. Verdicts: {verdicts}.", ""]
    findings = dataset["findings"]
    if findings:
        out += ["| Finding | Rule | Severity | Summary | Adjudication |", "| --- | --- | --- | --- | --- |"]
        out += [
            f"| [{f['id']}](#{f['id']}) | {f['rule']['id']} | {f['severity']} | {text(f['summary'])} | {f['adjudication']['decision']} |"
            for f in findings
        ]
        out.append("")
    for severity in SEVERITIES:
        group = [f for f in findings if f["severity"] == severity]
        if group:
            out += [f"### {HEADINGS[severity]} ({len(group)})", ""]
            for finding in group:
                out += finding_block(finding)
    if dataset.get("missed"):
        out += ["### Statements the adjudicator found uncited", "", "Each is for the next extraction round to cite.", ""]
        for m in dataset["missed"]:
            found = "" if m["verified"] else f" Not found: {text(m['not_found'])}."
            out += [f"**{m['variable']}** ({location(m)})", "", f"> {text(m['quote'])}", "", f"{text(m['reason'])}{found}", ""]
    if dataset.get("orphaned_decisions"):
        out += ["Decisions for findings that no longer exist: " + ", ".join(dataset["orphaned_decisions"]) + ".", ""]
    pending = [r["variable"] for r in dataset["variables"] if r.get("verdict") == "not_reviewed"]
    if pending:
        out += ["### Not yet reviewed", "", "Define-XML states a rule that no claim cites yet: " + ", ".join(pending) + ".", ""]
    return out


def render(report):
    out = [f"# Consistency review: {report['study']}", ""]
    out += [f"Generated by `.github/scripts/verify_derivations.py` at revision {code(report['revision'][:12])} with yamaa {code(report['yamaa_revision'][:12])}.", ""]
    if report["uncommitted_changes"]:
        out += ["Uncommitted changes were present. Repository links point at the revision above; files changed since then resolve once the branch is pushed.", ""]
    out += [f"> {text(report['note'])}", "", "## Summary", ""]
    out += ["| Dataset | Variables | Conflict | Divergence | Gap | Evidence | Agreed | Disputed | Stale | Pending |", "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |"]
    for d in report["datasets"]:
        s = d["summary"]
        f, a = s["findings"], s["adjudication"]
        out.append(f"| [{d['dataset']}](#{d['dataset'].lower()}) | {s['variables']} | {f['conflict']} | {f['divergence']} | {f['gap']} | {f['evidence']} | {a['agree']} | {a['dispute']} | {a['stale']} | {a['pending']} |")
    out.append("")
    cited = {}
    for d in report["datasets"]:
        for rule, count in d["summary"]["rules"].items():
            cited[rule] = cited.get(rule, 0) + count
    out += ["## Rules", "", "Each finding cites one rule of `.automation/consistency_review/rules.yaml`.", ""]
    out += ["| Rule | Severity | Statement | Findings |", "| --- | --- | --- | ---: |"]
    for rule in report["rules"].values():
        out.append(f"| {rule['id']} {text(rule['title'])} | {rule['severity']} | {text(rule['statement'])} | {cited.get(rule['id'], 0)} |")
    out.append("")
    for dataset in report["datasets"]:
        out += dataset_block(dataset)
    return "\n".join(out).rstrip() + "\n"
