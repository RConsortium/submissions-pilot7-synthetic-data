"""Render the legacy comparison as a self-contained, escaped HTML report."""

from collections import Counter
from html import escape
import json


def value(item):
    return escape(json.dumps(item, ensure_ascii=True, sort_keys=True))


def table(headers, rows):
    head = "".join(f"<th>{escape(h)}</th>" for h in headers)
    body = "".join("<tr>" + "".join(f"<td>{cell}</td>" for cell in row) + "</tr>" for row in rows)
    return f"<table><thead><tr>{head}</tr></thead><tbody>{body}</tbody></table>"


def write_legacy_report(destination, report):
    comparison = report.get("comparison", {})
    counts = comparison.get("field_counts", {})
    inventory = comparison.get("reference_inventory", {})
    source = comparison.get("coverage", {}).get("reference", {})
    target = comparison.get("coverage", {}).get("candidate", {})
    pieces = ["<!doctype html><html lang='en'><meta charset='utf-8'><title>CDISC Pilot 01 Define-XML comparison</title>",
              "<style>body{font:16px/1.5 system-ui,sans-serif;max-width:1200px;margin:32px auto;padding:0 20px;color:#172535}"
              "table{border-collapse:collapse;width:100%;margin:16px 0}td,th{padding:8px;border:1px solid #ccd4df;text-align:left;vertical-align:top}"
              "th{background:#edf2f8}pre,code{white-space:pre-wrap;overflow-wrap:anywhere}details{margin:12px 0}"
              ".notice{background:#fff3d7;border-left:5px solid #ab7200;padding:16px}.small{font-size:14px;color:#40566c}</style>",
              "<h1>CDISC Pilot 01: Define-XML 1.0 to 2.0</h1>",
              f"<p>Generation/report status: <strong>{escape(report['status'])}</strong>. "
              f"XML schema valid: <strong>{report.get('xml_schema_valid', False)}</strong>. "
              f"Deterministic: <strong>{report.get('deterministic_xml', False)}</strong>.</p>",
              "<p class='notice'>This is a cross-version metadata comparison. The original 1.0 document is not fully reproduced. "
              "Draft analysis-results metadata, source inconsistencies and inherited metadata differences remain visible. "
              "Schema validity, metadata equality and data conformance are separate results.</p>",
              "<p><a href='comparison.json'>Complete field-level comparison JSON</a> | <a href='report.json'>Generation and data-audit JSON</a></p>",
              "<h2>Coverage</h2>",
              table(["Metadata", "Reference", "Candidate"], [[escape(k), str(source.get(k, 0)), str(target.get(k, 0))]
                    for k in ("datasets", "variables", "value_lists", "value_level_entries", "codelists")]),
              "<h2>Field results</h2>",
              table(["Status", "Count"], [[escape(k), str(counts.get(k, 0))]
                    for k in ("matched", "converted", "different", "unsupported", "unresolved")]),
              "<p>Converted means the values agree after a declared version mapping. Different remains different, "
              "including a known language limitation; those fields are never counted as matches.</p>",
              "<h2>Differences</h2>"]
    delta = comparison.get("differences", [])
    grouped = Counter(d.get("known_gap", {}).get("field", "unexplained") if d.get("known_gap") else "unexplained" for d in delta)
    pieces.append(table(["Difference family", "Fields"], [[escape(k), str(v)] for k, v in sorted(grouped.items())]))
    pieces.append(f"<p>{len(delta)} different fields; {len(comparison.get('unexpected_differences', []))} unexplained. "
                  "The full JSON retains every difference and both values. The table below shows the first 30.</p>")
    pieces.append(table(["Path", "Reference", "Candidate", "Explanation"],
                        [[escape(d["path"]), value(d["reference"]), value(d["candidate"]),
                          escape((d.get("known_gap") or {}).get("reason", "Unexplained difference"))] for d in delta[:30]]))
    pieces.append("<h2>Conversions</h2>")
    pieces.append(table(["Path", "Rule", "Original", "Target mapping"],
                        [[escape(c["path"]), escape(c["rule"]), value(c["reference"]), value(c["expected"])]
                         for c in comparison.get("conversions", [])]))
    pieces.append("<h2>Unresolved source declarations</h2>")
    pieces.extend(f"<pre>{value(u)}</pre>" for u in comparison.get("unresolved", []))
    pieces.append(f"<h2>Unsupported reference content</h2><p>{inventory.get('result_displays', 0)} result displays and "
                  f"{inventory.get('analysis_results', 0)} analysis results use the draft ADaMRes extension.</p>")
    for block in comparison.get("unsupported", []):
        label = block.get("id") or ", ".join(block.get("reference_ids", [])[:2]) or block["kind"]
        detail = {k: v for k, v in block.items() if k != "xml"}
        pieces.append(f"<details><summary>{escape(label)}</summary><pre>{value(detail)}</pre>")
        if "xml" in block:
            pieces.append(f"<pre>{escape(block['xml'])}</pre>")
        pieces.append("</details>")
    pieces.append("<h2>Data checks</h2>")
    pieces.append(table(["Audit", "Conformant", "Represented bounds complete", "Conflict groups"],
                        [[escape(key), str(report.get(key, {}).get("conformant", False)),
                          str(report.get(key, {}).get("complete", True)), str(len(report.get(key, {}).get("conflicts", [])))]
                         for key in ("data_audit", "reference_data_audit")]))
    pieces.append("<p>The data audit checks declared bounds and terminology against the datasets. It is not a complete "
                  "Define-XML business-rule validation. In particular, received Derived origins without MethodDef remain received declarations.</p>")
    pieces.append("<h2>Comparison policy</h2><ul>" + "".join(f"<li>{escape(p)}</li>" for p in comparison.get("mapping_policy", [])) + "</ul>")
    pieces.append("<h2>Limits</h2><ul>" + "".join(f"<li>{escape(p)}</li>" for p in report.get("limits", [])) + "</ul></html>")
    destination.write_text("\n".join(pieces) + "\n")
