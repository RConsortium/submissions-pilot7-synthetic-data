#!/usr/bin/env python3
"""Verify yamaa derivations against the submission documents that state them.

Agents propose and this script decides; .automation/consistency_review/
describes the workflow. The extraction agent writes
<study>/spec/review/<dataset>-claims.json (verbatim citations, and clauses that
quote both the document and the specification) and <dataset>-probe.yaml, a
yamaa specification stating each documented rule. The adjudicator writes
<dataset>-adjudication.json. This script trusts none of it: it checks every
quote at its cited location, runs the probes with the pinned engine, compares
them with the published reference and the yamaa output, and turns every
inconsistency into a finding that cites one rule of
.automation/consistency_review/rules.yaml. Copies that Define-XML names, such
as DM.AGE, and codelist values are checked without an agent.

Usage: python .github/scripts/verify_derivations.py cdiscpilot01 [--dataset ADSL]
Writes .build/verification/<study>/report.json, report.md and sections/.
"""

import argparse
import hashlib
import json
import math
import os
import re
import subprocess
from pathlib import Path

import yaml

from consistency_report import render
from study_dashboard.config import reference_path, settings
from study_dashboard.lineage import source_locations
from study_evidence import catalog, engine_revision, project_specs, reviewed_datasets

# polars, yamaa, lxml and the document readers are imported where they are
# used, so the citation, finding and verdict logic stays testable with PyYAML.

ROOT = Path(__file__).resolve().parents[2]
RULES = ROOT / ".automation/consistency_review/rules.yaml"
REPOSITORY = "https://github.com/RConsortium/submissions-pilot7-synthetic-data"
SITE = "https://rconsortium.github.io/submissions-pilot7-synthetic-data"
REPORT_VERSION = 2
CLAIMS_VERSION = 2
ADJUDICATION_VERSION = 1
TOLERANCE = 1e-10  # The CDISC Pilot 01 numeric comparison policy.
DEFINE = "spec/define/define-adam.xml"
COPY = re.compile(r"([A-Z][A-Z0-9]*)\.([A-Z][A-Z0-9_]*)")
QUALIFIED = re.compile(r"([A-Za-z_][A-Za-z0-9_]*)\.([A-Za-z_][A-Za-z0-9_]*)")
# A clause relation and the rule its finding cites; same is no finding.
RELATIONS = {"same": None, "differs": "CR-6", "absent_in_spec": "CR-6", "absent_in_document": "CR-7", "contradicts": "CR-8"}
SIDES = {
    "same": {"document", "spec"},
    "differs": {"document", "spec"},
    "absent_in_spec": {"document"},
    "absent_in_document": {"spec"},
    "contradicts": {"document", "against"},
}
VERDICTS = {
    "consistent": "The documented rule matches the yamaa rule clause by clause, and the probe reproduces the reference.",
    "equivalent_on_data": "The yamaa rule differs from the documented rule, but both give the reference values on this data.",
    "resolved_by_reading": "The rule as written disagrees with the reference; a stated alternative reading reproduces it.",
    "conflict": "The documented rule, and every stated reading, disagrees with the reference.",
    "not_probed": "The rule is cited but not stated as a probe; the reason is recorded.",
    "not_reviewed": "Define-XML states a rule that no claim cites yet.",
    "document_silent": "No retained document states this derivation.",
    "missing_evidence": "A quote was not found at its cited location.",
}


def normalize(text):
    return " ".join(str(text).split())


def jsonable(value):
    if value is None or isinstance(value, (bool, int, str)):
        return value
    if isinstance(value, float):
        return value if math.isfinite(value) else str(value)
    return str(value)


def code_text(value):
    """Codelist comparison text: 54.0 is 54 and 1.2000000000000002 is 1.2."""
    if isinstance(value, float):
        return f"{value:.10g}"
    return str(value).strip()


def load_rules(path=RULES):
    declaration = yaml.safe_load(Path(path).read_text())
    rules = {}
    for rule in declaration["rules"]:
        if rule["id"] in rules or rule["severity"] not in declaration["severities"]:
            raise ValueError(f"{path}: rule {rule['id']} is duplicated or has an unknown severity")
        rules[rule["id"]] = {k: normalize(rule[k]) for k in ("id", "title", "severity", "statement")}
    missing = {r for r in RELATIONS.values() if r} - set(rules)
    if missing:
        raise ValueError(f"{path}: rules {sorted(missing)} are not declared")
    return rules


# Evidence: citable sections and where they are.


def evidence_index(root, study, metadata):
    """Citable sections of the retained documents, by study-relative path."""
    from study_dashboard.documents import document_sections

    base = root / study
    manifest = base / "spec/source/manifest.json"
    entries = json.loads(manifest.read_text()).get("files", []) if manifest.is_file() else []
    paths = [root / entry["path"] for entry in entries]
    paths += [p for p in sorted((base / "spec/define").glob("*.xml")) if p not in paths]
    return {
        path.relative_to(base).as_posix(): {
            section["id"]: section for section in document_sections(path, metadata)
        }
        for path in paths
        if path.is_file()
    }


def write_sections(index, target):
    """The exact citable text, one file per document, for agents to quote from."""
    for document, sections in index.items():
        path = target / f"{document}.txt"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("".join(f"=== {s['id']}\n{s['text'].rstrip()}\n\n" for s in sections.values()))


def element_lines(path, tag, oid):
    """First and last line of a Define-XML element, for a repository link."""
    from lxml import etree

    found = [e for e in etree.parse(str(path)).iter(f"{{*}}{tag}") if e.get("OID") == oid]
    if not found:
        return None
    lines = path.read_bytes().splitlines()

    def opening(element):
        # libxml2 reports the line that ends a start tag; walk back to its "<".
        name = f"<{etree.QName(element).localname}".encode()
        line = element.sourceline
        while line > 1 and name not in lines[line - 1]:
            line -= 1
        return line

    element = found[0]
    start, following = opening(element), element.getnext()
    end = opening(following) - 1 if following is not None else start
    while end > start and not lines[end - 1].strip():
        end -= 1
    return [start, end]


def document_links(root, study, revision, citation, metadata):
    """The published reading copy, the original page or XML lines, and the repository source."""
    document, section = citation["document"], citation["section"]
    path = f"{study}/{document}"
    published = f"{SITE}/evidence/dashboard/{study}/documents/{path}"
    links = {"reading_copy": f"{published}.html#{section}", "repository": f"{REPOSITORY}/blob/{revision}/{path}"}
    if section.startswith("page-"):
        links["original"] = f"{published}#page={section.removeprefix('page-')}"
    elif document.endswith(".xml"):
        domain, _, name = section.partition(".")
        oid = metadata.get(domain, {}).get(name, {}).get("oid")
        tag, oid = ("ItemDef", oid)
        if citation["quote"].startswith("Codelist "):
            tag, oid = "CodeList", citation["quote"].removeprefix("Codelist ").split(":")[0]
        if oid and (lines := element_lines(root / path, tag, oid)):
            links["repository"] += f"#L{lines[0]}-L{lines[1]}"
            links["original_lines"] = lines
    return links


def verify_citation(index, citation):
    """A quote counts only when it is found, verbatim, in its cited section."""
    section = index.get(citation["document"], {}).get(citation["section"])
    if section is None:
        reason = "document or section not retained"
    elif normalize(citation["quote"]) not in normalize(section["text"]):
        reason = "quote not found in the cited section"
    else:
        reason = None
    return {
        **citation,
        "section_title": section["title"] if section else None,
        "verified": reason is None,
        "reason": reason,
    }


def locate_quote(lines, span, quote):
    """Smallest line range inside a specification element that holds the quote."""
    target = normalize(quote)
    for end in range(span["start"], span["end"] + 1):
        if target in normalize(" ".join(lines[span["start"] - 1 : end])):
            start = max(
                s for s in range(span["start"], end + 1)
                if target in normalize(" ".join(lines[s - 1 : end]))
            )
            return [start, end]
    return None


def field_spans(text):
    """Line spans of each field of every column and row template in one YAML file.

    A row template's derivations are spanned one variable at a time, as
    `derivations/<variable>`, the fields field_sources names.
    """
    root = yaml.compose(text)
    found = {}

    def span(key, value):
        start = key.start_mark.line + 1
        return {"start": start, "end": start + text[key.start_mark.index:value.end_mark.index].rstrip().count("\n")}

    for key, value in root.value if isinstance(root, yaml.MappingNode) else []:
        label = {"columns": "name", "rows": "id"}.get(key.value)
        if label is None or not isinstance(value, yaml.SequenceNode):
            continue
        for item in value.value:
            if not isinstance(item, yaml.MappingNode):
                continue
            fields = {k.value: (k, v) for k, v in item.value}
            if label not in fields:
                continue
            spans = {}
            for field, (k, v) in fields.items():
                if field == "derivations" and isinstance(v, yaml.MappingNode):
                    spans.update({f"derivations/{dk.value}": span(dk, dv) for dk, dv in v.value})
                else:
                    spans[field] = span(k, v)
            found[fields[label][1].value] = spans
    return found


def layered_elements(packet):
    """Where each element of a layered specification may be quoted.

    An element is read first in the layer that writes its rule, then in the
    fields other layers still contribute, such as an entry's Define-XML
    metadata or one row template rule a later version replaces. The defining
    layer's own text for a field another layer overrode or cleared is blanked
    for quote search, so it never verifies a quote.
    """
    from study_dashboard.specifications import defining_sources, field_sources

    texts = {source["path"]: source["text"] for source in packet["sources"]}
    located = {path: source_locations(text)["spans"] for path, text in texts.items()}
    fields = {path: field_spans(text) for path, text in texts.items()}
    kept, elements = field_sources(packet), {}
    for element, path in defining_sources(packet).items():
        if element not in located[path]:
            continue
        lines, written, own = texts[path].splitlines(), kept.get(element, {}), fields[path].get(element, {})
        current = {f: f in {"name", "id"} or path in written.get(f, ()) for f in own}
        live = {n for f, s in own.items() if current[f] for n in range(s["start"], s["end"] + 1)}
        stale = {n for f, s in own.items() if not current[f] for n in range(s["start"], s["end"] + 1)} - live
        search = ["" if number in stale else line for number, line in enumerate(lines, 1)]
        candidates = [{"path": path, "lines": lines, "search": search, "span": located[path][element]}]
        for field, sources in sorted(written.items()):
            for source in sorted(sources - {path}):
                span = fields[source].get(element, {}).get(field)
                candidate = {"path": source, "lines": texts[source].splitlines(), "span": span}
                if span and candidate not in candidates:
                    candidates.append(candidate)
        elements[element] = candidates
    return elements


def spec_side(spec_file, element, quote=None):
    """A specification element, and the lines of a quote inside it when given.

    A layered specification's element is read where the composition keeps it,
    as layered_elements lists it. Text a later layer overrode never verifies a
    quote.
    """
    path, lines, spans, revision = spec_file["path"], spec_file["lines"], spec_file["spans"], spec_file["revision"]
    span = spans.get(element) if element else None
    search = lines
    candidates = spec_file.get("elements", {}).get(element, [])
    if candidates:
        chosen = candidates[0]
        if quote is not None:
            chosen = next((c for c in candidates if locate_quote(c.get("search", c["lines"]), c["span"], quote)), chosen)
        path, lines, span = (chosen[k] for k in ("path", "lines", "span"))
        search = chosen.get("search", lines)
    side = {"path": path, "element": element, "quote": quote, "element_lines": None, "lines": None, "excerpt": None, "verified": True, "reason": None}
    if span is None:
        if quote is not None or element is not None:
            side.update(verified=False, reason=f"specification element {element} not found")
        return side
    side.update(element_lines=[span["start"], span["end"]], excerpt="\n".join(lines[span["start"] - 1 : span["end"]]))
    shown = [span["start"], span["end"]]
    if quote is not None:
        found = locate_quote(search, span, quote)
        if found is None:
            side.update(verified=False, reason=f"quote not found in specification element {element}")
        else:
            side["lines"] = shown = found
    side["url"] = f"{REPOSITORY}/blob/{revision}/{path}#L{shown[0]}-L{shown[1]}"
    return side


# Data checks.


def compare(reference, observed, keys, column, observed_column, subject_key, extra_rows=True):
    """Row-aligned agreement of one observed column with a reference column.

    A reference record the observed table lacks is a difference. With
    extra_rows, so is an observed record the reference lacks: a probe must
    reproduce the reference population, not only its values. A copy source
    such as DM rightly holds more records, so copy checks pass False.
    """
    import polars as pl

    left = reference.select([*keys, pl.col(column).alias("_reference")])
    right = observed.select(
        [*keys, pl.col(observed_column).alias("_observed"), pl.lit(True).alias("_present")]
    )
    joined = left.join(right, on=keys, how="left")
    extra = right.join(left.select(keys).unique(), on=keys, how="anti") if extra_rows else right.clear()
    a, b = joined["_reference"], joined["_observed"]
    numeric = a.dtype.is_numeric() and b.dtype.is_numeric()
    if numeric:
        a, b = a.cast(pl.Float64), b.cast(pl.Float64)
    elif a.dtype != b.dtype:
        a, b = a.cast(pl.Utf8), b.cast(pl.Utf8)
    same = (a.is_null() & b.is_null()) | (a == b).fill_null(False)
    if numeric:
        same = same | ((a - b).abs() <= TOLERANCE).fill_null(False)
    same = same & joined["_present"].fill_null(False)
    differing = joined.with_columns(
        _reference=a, _observed=b, _same=same
    ).filter(~pl.col("_same"))
    patterns = {}
    subject = lambda row: row[subject_key] if subject_key in keys else "/".join(str(row[k]) for k in keys)
    for row in differing.iter_rows(named=True):
        present = bool(row["_present"])
        pair = (jsonable(row["_reference"]), jsonable(row["_observed"]) if present else None, "matched" if present else "absent")
        patterns.setdefault(pair, []).append(subject(row))
    for row in extra.iter_rows(named=True):
        patterns.setdefault((None, jsonable(row["_observed"]), "extra"), []).append(subject(row))
    return {
        "compared": joined.height + extra.height,
        "differ": differing.height + extra.height,
        "patterns": [
            {
                "reference": reference_value,
                "observed": observed_value,
                "row": row,
                "count": len(subjects),
                "subjects": subjects,
            }
            for (reference_value, observed_value, row), subjects in sorted(
                patterns.items(), key=lambda item: -len(item[1])
            )
        ],
    }


def resolve_source(spec, derivation):
    """The dataset and variable a plain yamaa copy reads, through intermediates.

    ADSL_SBJ.AGE, where ADSL_SBJ is an intermediate over the ADSL input whose
    file is adsl-yamaa.parquet, resolves to ADSL.AGE. Anything other than a
    plain qualified name resolves to None.
    """
    if isinstance(derivation, dict) and set(derivation) == {"value"}:
        derivation = derivation["value"]
    if not isinstance(derivation, str) or not QUALIFIED.fullmatch(normalize(derivation)):
        return None
    name, variable = normalize(derivation).split(".")
    intermediates = {i["id"]: i["dataset"] for i in spec.get("intermediates", [])}
    seen = set()
    while name in intermediates and name not in seen:
        seen.add(name)
        name = intermediates[name]
    entry = spec.get("input", {}).get(name)
    if isinstance(entry, dict) and entry.get("path"):
        name = Path(entry["path"]).stem.split("-")[0].upper()
    return f"{name}.{variable}"


def copy_check(base, spec, tables, variable, comment, subject_key):
    """Check a Define-XML copy such as DM.AGE without an agent."""
    domain, source_variable = COPY.fullmatch(comment).groups()
    column = next((c for c in spec["columns"] if c["name"] == variable), {})
    derivation = column.get("derivation")
    if isinstance(derivation, dict) and set(derivation) == {"value"}:
        derivation = derivation["value"]
    if derivation is None:
        # Row templates supply the value; one plain source across them is a copy.
        found = {
            str(rule["value"] if isinstance(rule, dict) and set(rule) == {"value"} else rule)
            for row in spec.get("rows", [])
            for rule in [(row.get("derivations") or {}).get(variable)]
            if rule is not None
        }
        derivation = found.pop() if len(found) == 1 else derivation
    resolved = resolve_source(spec, derivation)
    result = {
        "source": comment,
        "spec_derivation": derivation,
        "spec_source": resolved,
        "spec_matches": resolved == comment,
    }
    keys = spec["keys"]
    path = next(
        (
            p
            for p in (
                base / f"data/sdtm/{domain.lower()}.parquet",
                base / f"data/adam/{domain.lower()}.parquet",
            )
            if p.is_file()
        ),
        None,
    )
    if path is None:
        return {**result, "status": "source_unavailable"}
    import polars as pl

    source = pl.read_parquet(path)
    join = [k for k in keys if k in source.columns]
    if source_variable not in source.columns:
        return {**result, "status": "source_variable_missing", "reason": f"{domain} has no variable {source_variable}"}
    if not join:
        return {**result, "status": "not_checkable", "reason": f"{domain} lacks the dataset keys"}
    if source.select(join).is_duplicated().any():
        return {**result, "status": "not_checkable", "reason": f"{domain} has several records per {', '.join(join)}"}
    result.update(status="checked", source_file=path.relative_to(base).as_posix(), join=join)
    for name, table in tables.items():
        if variable in table.columns:
            result[name] = compare(table, source, join, variable, source_variable, subject_key, extra_rows=False)
    return result


def codelist_check(item, tables, variable, subject_key):
    """Published values outside the variable's Define-XML codelist, with their records."""
    if not item.get("codelist"):
        return None
    if item["codelist"].get("external"):
        # A dictionary such as MedDRA is not enumerated in Define-XML.
        return {"oid": item["codelist"]["oid"], "external": item["codelist"]["external"], "status": "external_dictionary"}
    allowed = {c["value"] for c in item["codelist"]["items"]}
    result = {"oid": item["codelist"]["oid"], "values": sorted(allowed)}
    for name, table in tables.items():
        if variable not in table.columns:
            continue
        outside = []
        for (value,), group in sorted(table.group_by(variable), key=lambda g: str(g[0][0])):
            if value is None or value == "" or code_text(value) in allowed:
                continue
            subjects = group[subject_key].unique(maintain_order=True).to_list() if subject_key in group.columns else []
            outside.append({"value": jsonable(value), "count": group.height, "subjects": subjects})
        result[name] = outside
    result["status"] = "values_outside_codelist" if any(result.get(name) for name in tables) else "conforms"
    return result


# Claims and adjudication.


def load_claims(path, probe_columns):
    """The agent's claims, checked for shape; their quotes are checked later."""
    declaration = json.loads(path.read_text())
    if declaration.get("schema_version") != CLAIMS_VERSION:
        raise ValueError(f"{path}: unsupported schema_version")
    claims = {}
    for claim in declaration["claims"]:
        name = claim["variable"]
        if name in claims:
            raise ValueError(f"{path}: duplicate claim for {name}")
        citations = claim.get("citations", [])
        for number, clause in enumerate(claim.get("clauses", []), 1):
            relation = clause.get("relation")
            if relation not in RELATIONS:
                raise ValueError(f"{path}: {name} clause {number} relation {relation!r}")
            given = {side for side in ("document", "spec", "against") if clause.get(side)}
            if given != SIDES[relation]:
                raise ValueError(f"{path}: {name} clause {number} ({relation}) needs exactly {sorted(SIDES[relation])}")
            for side in given - {"spec"}:
                if not 1 <= clause[side].get("citation", 0) <= len(citations):
                    raise ValueError(f"{path}: {name} clause {number} {side} names no citation")
        probes = claim.get("probes", [])
        if probes and probes[0].get("reading") != "literal":
            raise ValueError(f"{path}: {name} must state its literal reading first")
        if not probes and not claim.get("not_probed_reason"):
            raise ValueError(f"{path}: {name} needs probes or a not_probed_reason")
        for probe in probes:
            if probe["column"] not in probe_columns:
                raise ValueError(f"{path}: {name} probe column {probe['column']} is not produced")
        claims[name] = claim
    return declaration, claims


def load_adjudication(path):
    if not path.is_file():
        return None
    declaration = json.loads(path.read_text())
    if declaration.get("schema_version") != ADJUDICATION_VERSION:
        raise ValueError(f"{path}: unsupported schema_version")
    decisions = {}
    for decision in declaration.get("decisions", []):
        if decision["finding"] in decisions or decision["decision"] not in {"agree", "dispute"}:
            raise ValueError(f"{path}: {decision['finding']} is decided twice or not agree/dispute")
        decisions[decision["finding"]] = decision
    return {**declaration, "decisions": decisions}


def adjudicate(findings, adjudication):
    """Attach each decision to the finding it judged; a changed finding makes it stale."""
    decisions = (adjudication or {}).get("decisions", {})
    for finding in findings:
        decision = decisions.get(finding["id"])
        if decision is None:
            finding["adjudication"] = {"decision": "pending"}
        elif decision.get("basis") not in (finding["basis"], fingerprint_basis(finding["basis"])):
            finding["adjudication"] = {"decision": "stale", "previous": decision["decision"], "reason": decision.get("reason", "")}
        else:
            finding["adjudication"] = {"decision": decision["decision"], "reason": decision.get("reason", "")}
    return sorted(set(decisions) - {f["id"] for f in findings})


def missed_statements(statements, index, links):
    """Uncited statements the adjudicator found, with their quotes checked."""
    result = []
    for statement in statements:
        # The adjudicator's reason stays; the quote check is recorded beside it.
        check = verify_citation(index, statement)
        result.append(
            {
                **statement,
                "section_title": check["section_title"],
                "verified": check["verified"],
                "not_found": check["reason"],
                "links": links(statement),
            }
        )
    return result


# Verdicts and findings.


def verdict(record):
    """One deterministic verdict from verified citations and probe results."""
    if record["check"] == "copy":
        copy = record["copy"]
        if copy["status"] == "source_variable_missing":
            return "conflict"
        if copy["status"] != "checked":
            return "not_probed"
        if copy["reference"]["differ"]:
            return "conflict"
        return "consistent" if copy["spec_matches"] else "equivalent_on_data"
    citations = record.get("citations", [])
    if not citations:
        # Define-XML states a rule that no claim has cited yet.
        return "not_reviewed" if record.get("documented") else "document_silent"
    if not all(c["verified"] for c in citations) or not all(c.get("verified", True) for c in record.get("clauses", [])):
        return "missing_evidence"
    probes = record.get("probes", [])
    if not probes:
        return "not_probed"
    literal, *readings = probes
    if literal["reference"]["differ"] == 0:
        clauses = record.get("clauses", [])
        return "consistent" if all(c["relation"] == "same" for c in clauses) else "equivalent_on_data"
    if any(p["reference"]["differ"] == 0 for p in readings):
        return "resolved_by_reading"
    return "conflict"


def review_status(record):
    """Only a consistent rule with no open interpretation leaves the human queue first."""
    agreed = (
        record["verdict"] == "consistent"
        and not record.get("interpretations")
        and not record.get("question")
        and (record.get("codelist") or {}).get("status") != "values_outside_codelist"
    )
    return "checks_agree" if agreed else "needs_human"


def quote_side(citation, quote, role):
    """One document side of a finding: the clause quote inside its full citation."""
    verified = citation["verified"] and normalize(quote) in normalize(citation["quote"])
    return {
        "role": role,
        "document": citation["document"],
        "section": citation["section"],
        "section_title": citation.get("section_title"),
        "quote": quote,
        "context": citation["quote"],
        "links": citation.get("links", {}),
        "verified": verified,
        "reason": None if verified else citation.get("reason") or "clause quote not found in its citation",
    }


def verify_clauses(record, spec_file):
    """Check both quoted sides of every clause at their cited locations."""
    citations = record["citations"]
    for clause in record.get("clauses", []):
        documents = [
            quote_side(citations[clause[role]["citation"] - 1], clause[role]["quote"], {"document": "states", "against": "against"}[role])
            for role in ("document", "against")
            if clause.get(role)
        ]
        spec = spec_side(spec_file, clause["spec"]["element"], clause["spec"]["quote"]) if clause.get("spec") else None
        clause["sides"] = {"documents": documents, "spec": spec}
        clause["verified"] = all(d["verified"] for d in documents) and (spec is None or spec["verified"])


def source_label(side):
    """Define-XML ADSL.TRTSDT, or SAP.pdf page 13."""
    if side["section"].startswith("page-"):
        return f'{Path(side["document"]).name} page {side["section"].removeprefix("page-")}'
    return f'Define-XML {side["section"]}'


def short(quote, limit=90):
    quote = normalize(quote)
    return quote if len(quote) <= limit else quote[: limit - 3].rstrip() + "..."


def stable(value):
    """Evidence without links, which name the revision and change with every commit."""
    if isinstance(value, dict):
        return {k: stable(v) for k, v in value.items() if k not in {"url", "links"}}
    if isinstance(value, list):
        return [stable(v) for v in value]
    return value


def basis(rule, documents, spec, evidence=None, extra=""):
    """Everything a finding asserts; an adjudication judged exactly this text.

    The quotes, the specification element the finding shows, and its evidence,
    such as a probe's definition and its comparison results: a change to any of
    them makes an earlier decision stale.
    """
    parts = [rule] + [f'{d["role"]} {d["document"]}#{d["section"]}: "{normalize(d["quote"])}"' for d in documents]
    if spec and spec.get("quote"):
        parts.append(f'spec {spec["element"]}: "{normalize(spec["quote"])}"')
    if spec and spec.get("excerpt"):
        parts.append(f'spec {spec["element"]} text: "{normalize(spec["excerpt"])}"')
    if evidence:
        parts.append("evidence " + json.dumps(stable(evidence), sort_keys=True, ensure_ascii=True))
    return " | ".join(parts + ([extra] if extra else []))


def fingerprint_basis(value):
    """Bind a compact stored decision to the complete, unchanged basis text."""
    return "sha256:" + hashlib.sha256(value.encode("utf-8")).hexdigest()


def variable_findings(record, rules, spec_file, define_citation):
    """Every inconsistency of one variable, each citing exactly one rule."""
    dataset, name = record["dataset"], record["variable"]
    findings = []

    def add(rule, number, documents, spec, summary, evidence=None, note="", extra="", relation=None):
        # A quote in an element the variable reads is shown with the variable's own definition.
        variable_spec = own if spec and own["element"] and spec["element"] != own["element"] else None
        finding_basis = basis(rule, documents, spec, evidence, extra)
        findings.append(
            {
                "id": f"{dataset}.{name}.{rule}" + (f".{number}" if number else ""),
                "dataset": dataset,
                "variable": name,
                "label": record.get("label", ""),
                "rule": rules[rule],
                "severity": rules[rule]["severity"],
                "relation": relation,
                "summary": summary,
                "documents": documents,
                "spec": spec,
                "variable_spec": variable_spec,
                "evidence": evidence,
                "note": note,
                "interpretations": record.get("interpretations", []),
                "assessment": record.get("assessment", ""),
                "question": record.get("question", ""),
                "basis": finding_basis,
                "basis_fingerprint": fingerprint_basis(finding_basis),
            }
        )

    own = spec_side(spec_file, name if name in spec_file["spans"] or name in spec_file["elements"] else None)
    if record["check"] == "copy":
        copy = record["copy"]
        documents = [quote_side(define_citation(record["define"]["comment"]), record["define"]["comment"], "states")]
        derivation = copy["spec_derivation"] if isinstance(copy["spec_derivation"], str) else None
        quoted = derivation if derivation and normalize(derivation) in normalize(own.get("excerpt", "")) else None
        spec = spec_side(spec_file, own["element"], quoted if own["element"] else None)
        if copy["status"] == "source_variable_missing":
            add("CR-2", 0, documents, spec, f'Define-XML names {copy["source"]} as the source; {copy["reason"]}.', {"copy": copy})
        if copy["status"] == "checked" and copy["reference"]["differ"]:
            reference = copy["reference"]
            add("CR-3", 0, documents, spec, f'The reference differs from {copy["source"]} on {reference["differ"]} of {reference["compared"]} records.', {"copy": copy})
        # Key variables match their source by the join itself.
        if copy["status"] == "checked" and not copy["spec_matches"] and name not in spec_file["keys"]:
            reads = copy["spec_source"] or "a derivation that is not a plain copy"
            add("CR-4", 0, documents, spec, f'Define-XML names {copy["source"]}; the specification reads {reads}.', {"copy": copy})
    if record.get("citations") is not None and record["check"] == "rule":
        citations = record["citations"]
        for number, citation in enumerate(citations, 1):
            if not citation["verified"]:
                side = quote_side(citation, citation["quote"], "states")
                add("CR-1", number, [side], None, f'Citation {number} was not found: {citation["reason"]}.')
        for number, clause in enumerate(record.get("clauses", []), 1):
            relation = clause["relation"]
            documents, spec = clause["sides"]["documents"], clause["sides"]["spec"]
            if not clause["verified"]:
                failed = [d["reason"] for d in documents if not d["verified"]] + ([spec["reason"]] if spec and not spec["verified"] else [])
                add("CR-1", f"c{number}", documents, spec, f"Clause {number} quotes text not found where it is cited: {'; '.join(failed)}.")
                continue
            rule = RELATIONS[relation]
            if rule is None:
                continue
            says = [f'{source_label(d)} states "{short(d["quote"])}"' for d in documents]
            if spec is not None:
                says.append(f'the specification states "{short(spec["quote"])}" in {spec["element"]}')
            if relation == "absent_in_spec":
                summary = f"{says[0]}; the specification has no counterpart."
            elif relation == "absent_in_document":
                summary = f"{says[0][0].upper()}{says[0][1:]}; no retained document states it."
            else:
                summary = f"{says[0]}; {says[1]}."
            if relation == "absent_in_spec":
                spec = own
            add(rule, number, documents, spec, summary, note=clause.get("note", ""), extra=relation, relation=relation)
        verified = all(c["verified"] for c in citations) and all(c["verified"] for c in record.get("clauses", []))
        probes = record.get("probes", [])
        if verified and probes and probes[0]["reference"]["differ"]:
            literal, *readings = probes
            documents = [quote_side(c, c["quote"], "states") for c in citations]
            resolving = [p["column"] for p in readings if p["reference"]["differ"] == 0]
            summary = f'The documented rule, run as written, differs from the reference on {literal["reference"]["differ"]} of {literal["reference"]["compared"]} records'
            summary += f'; reading {resolving[0]} reproduces the reference.' if resolving else "; no stated reading reproduces the reference."
            add("CR-5", 0, documents, own, summary, {"probes": probes}, extra="probes " + ", ".join(p["column"] for p in probes))
        if verified and record.get("not_probed_reason"):
            documents = [quote_side(c, c["quote"], "states") for c in citations]
            add("CR-10", 0, documents, own, "The documented rule cannot be stated as a probe.", {"not_probed_reason": record["not_probed_reason"]}, note=record["not_probed_reason"])
    if record.get("verdict") == "document_silent":
        add("CR-11", 0, [], own, "No retained document states this derivation.")
    codelist = record.get("codelist") or {}
    if codelist.get("status") == "values_outside_codelist":
        line = next(l for l in record["define"]["text"].splitlines() if l.startswith("Codelist "))
        documents = [quote_side(define_citation(line), line, "states")]
        values = sorted({v["value"] for side in ("reference", "derived") for v in codelist.get(side, [])}, key=str)
        add("CR-9", 0, documents, None, f'Values outside codelist {codelist["oid"]}: {", ".join(map(str, values))}.', {"codelist": codelist})
    return findings


def run_probe(path):
    import polars as pl
    import yamaa

    spec = yamaa.spec(path)
    check = spec.check()
    if check.status != "succeeded":
        raise ValueError(f"{path}: {check.issues.to_pylist()}")
    run = spec.run()
    if run.status != "succeeded":
        raise ValueError(f"{path}: {run.issues.to_pylist()}")
    declaration = yaml.safe_load(path.read_text())
    output = (path.parent / declaration["output"]["path"]).resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    run.save()
    return declaration, output, pl.read_parquet(output)


def dataset_report(context, domain, spec_path, derived, reference):
    root, study, metadata, index, revision, subject_key, rules = (
        context[k] for k in ("root", "study", "metadata", "index", "revision", "subject_key", "rules")
    )
    base = root / study
    text = spec_path.read_text()
    spec = yaml.safe_load(text)
    elements = {}
    if spec.get("parent") or spec.get("include") or any("copy" in c for c in spec.get("columns", [])):
        import yamaa
        from study_dashboard.specifications import capture_specification

        packet = capture_specification(root, spec_path, yamaa.spec(spec_path).resolve())
        spec = packet["model"]
        elements = layered_elements(packet)
    spans = source_locations(text)["spans"]
    spec_file = {
        "path": spec_path.relative_to(root).as_posix(),
        "lines": text.splitlines(),
        "spans": spans,
        "elements": elements,
        "keys": spec["keys"],
        "revision": revision,
    }
    columns = {c["name"]: c for c in spec["columns"]}
    tables = {"reference": reference, "derived": derived}
    review = base / "spec/review"
    probe_path = review / f"{domain.lower()}-probe.yaml"
    claims_path = review / f"{domain.lower()}-claims.json"
    adjudication_path = review / f"{domain.lower()}-adjudication.json"
    probe = None
    if probe_path.is_file():
        probe_spec, probe_output, probe = run_probe(probe_path)
        probe_text = probe_path.read_text()
        probe_file = {
            "path": probe_path.relative_to(root).as_posix(),
            "lines": probe_text.splitlines(),
            "spans": source_locations(probe_text)["spans"],
            "revision": revision,
        }
    claims, declaration = {}, None
    if claims_path.is_file():
        declaration, claims = load_claims(claims_path, set(probe.columns) if probe is not None else set())
    from study_dashboard.documents import define_section_text

    define = metadata.get(domain, {})
    names = list(define) + [n for n in spec["output"]["columns"] if n not in define]
    records, findings = [], []
    for name in names:
        item = define.get(name, {})
        record = {
            "dataset": domain,
            "variable": name,
            "label": item.get("label") or (columns.get(name) or {}).get("label", ""),
            "define": {
                "section": f"{domain}.{name}" if item else None,
                "method": item.get("method", ""),
                "comment": item.get("comment", ""),
                "text": define_section_text(item) if item else "",
            },
            "spec": spec_side(spec_file, name if name in spans or name in elements else None),
        }
        record["spec"]["in_output"] = name in spec["output"]["columns"]

        def define_citation(quote, name=name):
            citation = verify_citation(index, {"document": DEFINE, "section": f"{domain}.{name}", "quote": quote})
            citation["links"] = document_links(root, study, revision, citation, metadata)
            return citation

        documented = item.get("method") or item.get("comment") or ""
        claim = claims.get(name)
        if not item:
            record["check"] = "not_in_define"
        elif COPY.fullmatch(documented) and not claim:
            record["check"] = "copy"
            record["copy"] = copy_check(base, spec, tables, name, documented, subject_key)
        else:
            record["check"] = "rule"
        if claim:
            record.update(
                rule=claim.get("rule", ""),
                citations=[verify_citation(index, c) for c in claim.get("citations", [])],
                clauses=[dict(c) for c in claim.get("clauses", [])],
                interpretations=claim.get("interpretations", []),
                assessment=claim.get("assessment", ""),
                question=claim.get("question", ""),
            )
            for citation in record["citations"]:
                citation["links"] = document_links(root, study, revision, citation, metadata)
            if claim.get("not_probed_reason"):
                record["not_probed_reason"] = claim["not_probed_reason"]
            record["probes"] = [
                {
                    **p,
                    "definition": spec_side(probe_file, p["column"]),
                    "reference": compare(reference, probe, probe_spec["keys"], name, p["column"], subject_key),
                    "derived": compare(derived, probe, probe_spec["keys"], name, p["column"], subject_key)
                    if name in derived.columns
                    else None,
                }
                for p in claim.get("probes", [])
            ]
        elif record["check"] == "rule":
            record["citations"] = []
            record["documented"] = bool(documented)
        if record["check"] != "not_in_define":
            if claim:
                verify_clauses(record, spec_file)
            record["codelist"] = codelist_check(item, tables, name, subject_key)
            record["verdict"] = verdict(record)
            record["review_status"] = review_status(record)
            found = variable_findings(record, rules, spec_file, define_citation)
            record["findings"] = [f["id"] for f in found]
            findings += found
        records.append(record)
    unknown = sorted(set(claims) - set(names))
    if unknown:
        raise ValueError(f"{claims_path}: claims for unknown variables {unknown}")
    adjudication = load_adjudication(adjudication_path)
    orphaned = adjudicate(findings, adjudication)
    missed = missed_statements(
        (adjudication or {}).get("missed", []),
        index,
        lambda statement: document_links(root, study, revision, statement, metadata),
    )
    rows = {row["id"] for row in spec.get("rows", [])}
    for statement in missed:
        # Record selection has no rule yet, so no claim can cite it.
        statement["scope"] = "records" if statement["variable"] in rows else "variable"
    judged = [r for r in records if "verdict" in r]
    order = {s: i for i, s in enumerate(["conflict", "divergence", "gap", "evidence"])}
    findings.sort(key=lambda f: order[f["severity"]])
    return {
        "dataset": domain,
        "specification": spec_file["path"],
        "claims": claims_path.relative_to(root).as_posix() if declaration else None,
        "claims_author": declaration.get("author") if declaration else None,
        "probe": probe_path.relative_to(root).as_posix() if probe is not None else None,
        "probe_output": probe_output.relative_to(root).as_posix() if probe is not None else None,
        "adjudication": adjudication_path.relative_to(root).as_posix() if adjudication else None,
        "adjudication_author": adjudication.get("author") if adjudication else None,
        "summary": {
            "variables": len(records),
            "checks": {k: sum(r["check"] == k for r in records) for k in ("copy", "rule", "not_in_define")},
            "verdicts": {k: sum(r["verdict"] == k for r in judged) for k in VERDICTS},
            "review_status": {k: sum(r["review_status"] == k for r in judged) for k in ("needs_human", "checks_agree")},
            "findings": {k: sum(f["severity"] == k for f in findings) for k in order},
            "rules": {k: sum(f["rule"]["id"] == k for f in findings) for k in rules if any(f["rule"]["id"] == k for f in findings)},
            "adjudication": {
                k: sum(f["adjudication"]["decision"] == k for f in findings)
                for k in ("agree", "dispute", "stale", "pending")
            },
            "citations": {
                "total": sum(len(r.get("citations", [])) for r in records),
                "verified": sum(c["verified"] for r in records for c in r.get("citations", [])),
            },
            "probes": sum(len(r.get("probes", [])) for r in records),
        },
        "findings": findings,
        "missed": missed,
        "orphaned_decisions": orphaned,
        "variables": records,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("study")
    scope = parser.add_mutually_exclusive_group()
    scope.add_argument("--dataset", action="append", help="Dataset to verify; repeat for several. Default: every project dataset.")
    scope.add_argument("--reviewed", action="store_true", help="Verify the datasets with committed review claims, as publication does.")
    parser.add_argument("--output", type=Path, help="Report directory. Default: .build/verification/<study>")
    args = parser.parse_args()
    import polars as pl
    import yamaa

    from study_dashboard.documents import define_metadata

    entry = catalog(ROOT)[args.study]
    options = settings(ROOT, entry)
    base = ROOT / args.study
    specs = dict(project_specs(ROOT, args.study))
    domains = reviewed_datasets(ROOT, args.study) if args.reviewed else args.dataset or list(specs)
    if not domains:
        raise SystemExit(f"{args.study}: no dataset has review claims")
    unknown = sorted(set(domains) - set(specs))
    if unknown:
        raise SystemExit(f"{args.study}: unknown datasets {unknown}")
    git = lambda *a: subprocess.run(["git", *a], cwd=ROOT, capture_output=True, text=True, check=True).stdout.strip()
    # The same source commit the dashboard bundle records, so publication can match them.
    revision = os.environ.get("GITHUB_SHA") or git("rev-parse", "HEAD")
    # Repository links point at this revision; local edits are not there yet.
    uncommitted = bool(git("status", "--porcelain", "--", args.study, ".github/scripts", ".automation"))
    define = base / DEFINE
    metadata = define_metadata(define) if define.is_file() else {}
    rules = load_rules()
    output = args.output or ROOT / ".build/verification" / args.study
    index = evidence_index(ROOT, args.study, metadata)
    write_sections(index, output / "sections")
    runs = yamaa.project(base / "spec/yamaa/project.yaml").run("adam")
    if runs.status != "succeeded":
        raise SystemExit(str(runs.issues.to_pylist()))
    context = {
        "root": ROOT,
        "study": args.study,
        "metadata": metadata,
        "index": index,
        "revision": revision,
        "subject_key": options["subject_key"],
        "rules": rules,
    }
    datasets = [
        dataset_report(
            context,
            domain,
            specs[domain],
            pl.DataFrame(runs[domain].output),
            pl.read_parquet(reference_path(ROOT, args.study, domain, options)),
        )
        for domain in domains
    ]
    report = {
        "schema_version": REPORT_VERSION,
        "study": args.study,
        "revision": revision,
        "uncommitted_changes": uncommitted,
        "yamaa_revision": engine_revision(ROOT, args.study),
        "note": "Findings compare retained submission documents, the yamaa specification and data. They are not regulatory validation; each awaits a person's decision.",
        "rules": rules,
        "verdicts": VERDICTS,
        "datasets": datasets,
    }
    output.mkdir(parents=True, exist_ok=True)
    (output / "report.json").write_text(json.dumps(report, ensure_ascii=True, indent=1) + "\n")
    (output / "report.md").write_text(render(report))
    for dataset in datasets:
        print(f'{dataset["dataset"]}: {json.dumps(dataset["summary"])}')
    shown = output.relative_to(ROOT) if output.is_relative_to(ROOT) else output
    print(f"Wrote {shown}/report.json and report.md")


if __name__ == "__main__":
    main()
