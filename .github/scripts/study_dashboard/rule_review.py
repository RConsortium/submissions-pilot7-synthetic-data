"""Documented-rule findings from the derivation verification report.

verify_derivations.py runs in the study's validation job, where the pinned
engine is installed, and decides every finding there. This module only reshapes
those findings for the Consistency review table: each keeps its rule, quotes,
evidence and adjudication, takes the table's common fields so search, the
evidence drawer and source links work unchanged, and gains the dashboard's own
links into the retained documents.
"""

import hashlib
from pathlib import PurePosixPath

COMPARISON = "documented_rules"
# Keep full comparisons for issue impact and workspace selection. The browser
# limits the initial display, without discarding records from the artifact.


def document_side(study, side, documents):
    """A quoted statement with links to the dashboard's copy of its document."""
    path = f'{study}/{side["document"]}'
    document = documents.get(path, {})
    section = side["section"]
    original = document.get("original", "")
    if original and section.startswith("page-"):
        original += "#page=" + section.removeprefix("page-")
    links = side.get("links") or {}
    return {
        "role": side["role"],
        "path": path,
        "name": PurePosixPath(path).name,
        "section": section,
        "section_title": side.get("section_title") or section,
        "quote": side["quote"],
        "context": side["context"],
        "verified": side["verified"],
        "reason": side.get("reason"),
        "reading": f'{document["reading"]}#{section}' if document.get("reading") else "",
        "original": original,
        "repository": links.get("repository", ""),
        "lines": links.get("original_lines"),
    }


def comparison(result):
    if not result:
        return None
    return {
        "compared": result["compared"],
        "differ": result["differ"],
        "pattern_count": len(result["patterns"]),
        "patterns": [
            {
                **{k: p[k] for k in ("reference", "observed", "row", "count")},
                "subjects": p["subjects"],
            }
            for p in result["patterns"]
        ],
    }


def evidence(raw):
    """Complete data evidence; only the browser's initial display is shortened."""
    raw = raw or {}
    result = {}
    if raw.get("probes"):
        result["probes"] = [
            {
                "column": p["column"],
                "reading": p["reading"],
                "definition": {
                    k: (p.get("definition") or {}).get(k)
                    for k in ("path", "element", "lines", "quote", "verified", "reason", "element_lines", "excerpt", "url")
                },
                "reference": comparison(p["reference"]),
                "derived": comparison(p.get("derived")),
            }
            for p in raw["probes"]
        ]
    if raw.get("copy"):
        copy = raw["copy"]
        result["copy"] = {
            **{
                k: copy.get(k)
                for k in ("source", "spec_derivation", "spec_source", "spec_matches", "status", "reason", "join")
            },
            "reference": comparison(copy.get("reference")),
        }
    if raw.get("codelist"):
        codelist = raw["codelist"]
        result["codelist"] = {
            "oid": codelist["oid"],
            **{target: codelist[target] for target in ("reference", "derived") if target in codelist},
        }
    if raw.get("not_probed_reason"):
        result["not_probed_reason"] = raw["not_probed_reason"]
    return result


def subjects(raw):
    """Every record key the data evidence names, so the workspace can show them."""
    raw, found = raw or {}, []
    patterns = [p for probe in raw.get("probes", []) for p in probe["reference"]["patterns"]]
    patterns += ((raw.get("copy") or {}).get("reference") or {}).get("patterns", [])
    for pattern in patterns:
        found += pattern["subjects"]
    for value in (raw.get("codelist") or {}).get("reference", []):
        found += value.get("subjects", [])
    return list(dict.fromkeys(found))


def data_summary(raw):
    raw = raw or {}
    parts = []
    for probe in raw.get("probes", []):
        result = probe["reference"]
        name = "literal rule" if probe["reading"] == "literal" else "reading"
        parts.append(f'Documented rule {probe["column"]} ({name}): {result["differ"]} of {result["compared"]} records differ from the reference.')
    copy = raw.get("copy")
    if copy and copy.get("reference"):
        parts.append(f'Reference against {copy["source"]}: {copy["reference"]["differ"]} of {copy["reference"]["compared"]} records differ.')
    elif copy and copy.get("reason"):
        parts.append(f'{copy["reason"]}.')
    codelist = raw.get("codelist")
    if codelist:
        values = ", ".join(f'{v["value"]} ({v["count"]} records)' for v in codelist.get("reference", []))
        parts.append(f'Reference values outside codelist {codelist["oid"]}: {values}.')
    if raw.get("not_probed_reason"):
        parts.append(f'Documented rule not checked: {raw["not_probed_reason"]}')
    return " ".join(parts) or "No data comparison; the finding compares document and specification text."


def rule_findings(study, verification, documents):
    """Consistency-table entries for every finding of the verification report."""
    if not verification:
        return []
    documents = {d["path"]: d for d in documents}
    result = []
    for dataset in verification["datasets"]:
        for finding in dataset["findings"]:
            sides = [document_side(study, d, documents) for d in finding["documents"]]
            spec = finding.get("spec") or {}
            lines = spec.get("lines") or spec.get("element_lines") or [1]
            primary = sides[0] if sides else None
            rule = finding["rule"]
            note = f' {finding["note"]}' if finding.get("note") else ""
            result.append(
                {
                    "id": f'{study}:{finding["id"]}',
                    "dataset": finding["dataset"],
                    "variable": finding["variable"],
                    "comparison": COMPARISON,
                    "kind": finding["severity"],
                    "status": f'{finding["severity"].capitalize()}: {rule["id"]}',
                    "title": f'{rule["id"]} {rule["title"]}',
                    "observation": finding["summary"] + note,
                    "assessment": finding.get("assessment", ""),
                    "note": finding.get("note", ""),
                    "source": {
                        "path": primary["path"] if primary else "",
                        "section": primary["section_title"] if primary else "",
                        "excerpt": primary["context"] if primary else "No retained document states this.",
                        "url": primary["reading"] if primary else "",
                    },
                    "spec": {
                        "path": spec.get("path", ""),
                        "line": lines[0],
                        "url": spec.get("url", ""),
                        "excerpt": spec.get("excerpt") or "",
                    },
                    "data": {"path": "", "summary": data_summary(finding.get("evidence"))},
                    "recommendation": finding.get("question") or finding.get("assessment", ""),
                    "rule": rule,
                    "relation": finding.get("relation"),
                    "documents": sides,
                    "spec_quote": spec or None,
                    "variable_spec": finding.get("variable_spec"),
                    "evidence": evidence(finding.get("evidence")),
                    "subjects": subjects(finding.get("evidence")),
                    "interpretations": finding.get("interpretations", []),
                    "question": finding.get("question", ""),
                    "adjudication": finding["adjudication"],
                    "basis_hash": hashlib.sha256(finding.get("basis", "").encode()).hexdigest(),
                }
            )
    return result


def verification_summary(study, verification, documents):
    """What the tab states about the review: datasets, counts, uncited statements."""
    if not verification:
        return None
    documents = {d["path"]: d for d in documents}
    return {
        "revision": verification["revision"],
        "yamaa_revision": verification["yamaa_revision"],
        "rules": list(verification["rules"].values()),
        "datasets": [
            {
                "dataset": d["dataset"],
                "summary": {k: d["summary"][k] for k in ("findings", "adjudication", "citations")},
                "claims_author": d.get("claims_author"),
                "adjudication_author": d.get("adjudication_author"),
                "missed": [
                    {
                        **document_side(study, {**m, "role": "states", "context": m["quote"]}, documents),
                        # The adjudicator's reason; the quote check is not_found.
                        "variable": m["variable"],
                        "scope": m.get("scope", "variable"),
                        "reason": m.get("reason", ""),
                        "not_found": m.get("not_found"),
                    }
                    for m in d.get("missed", [])
                ],
            }
            for d in verification["datasets"]
        ],
    }
