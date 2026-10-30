"""Compare actual derived tables with retained Define-XML, without other sources.

Storage types are mapped to logical types. Text length is an observed maximum,
not a SAS allocation check. Narrative methods are never guessed or executed.
"""

from collections import Counter
import ast
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
import hashlib
import html
import json
import math
import operator
import re

import pyarrow as pa
import pyarrow.parquet as pq
from lxml import etree

from define_metadata import Document
from .documents import define_metadata, document_html, materials
from .datasets import write_json
from .issues import build_review, digest

REPO = "https://github.com/RConsortium/submissions-pilot7-synthetic-data"


def missing(value):
    return value is None or isinstance(value, float) and math.isnan(value)


def code(value, kind):
    if kind in {"integer", "float", "double"}:
        try:
            return str(Decimal(str(value)).normalize())
        except InvalidOperation:
            pass
    return str(value)


def logical_type(field, item, values):
    """None means unsupported mapping; false is an observed incompatibility."""
    kind, typ = item["type"], field.type
    if kind == "text":
        return pa.types.is_string(typ) or pa.types.is_large_string(typ)
    if kind in {"integer", "float", "double"}:
        if pa.types.is_date(typ):
            return True if kind == "integer" and re.match(r"^(DATE|YYMMDD|DDMMYY|MMDDYY|E8601DA|IS8601DA)\d*\.", item.get("display_format") or "", re.I) else None
        if not (pa.types.is_integer(typ) or pa.types.is_floating(typ)):
            return False
        return kind != "integer" or all(missing(v) or math.isfinite(v) and int(v) == v for v in values)
    if kind == "date":
        return True if pa.types.is_date(typ) else None
    if kind == "datetime":
        return True if pa.types.is_timestamp(typ) else None
    return None


def formula(text, domain, names):
    """Compile only literal arithmetic over this dataset's columns, without eval."""
    operations = {ast.Add: operator.add, ast.Sub: operator.sub,
                  ast.Mult: operator.mul, ast.Div: operator.truediv}
    try:
        tree = ast.parse(text.strip(), mode="eval")
    except SyntaxError:
        return None

    def compile_node(node):
        if isinstance(node, ast.Constant) and type(node.value) in {int, float}:
            return lambda row: node.value
        if isinstance(node, ast.Attribute) and isinstance(node.value, ast.Name) and node.value.id == domain:
            node = ast.Name(id=node.attr)
        if isinstance(node, ast.Name) and node.id in names:
            def column(row):
                value = row[node.id]
                if missing(value):
                    return None
                if isinstance(value, date) and not isinstance(value, datetime):
                    return (value - date(1960, 1, 1)).days
                if not isinstance(value, (int, float)):
                    raise ValueError("Arithmetic requires numeric or SAS-date operands")
                return value
            return column
        if isinstance(node, ast.BinOp) and type(node.op) in operations:
            left, right, op = compile_node(node.left), compile_node(node.right), operations[type(node.op)]
            def binary(row):
                a, b = left(row), right(row)
                return None if a is None or b is None else op(a, b)
            return binary
        if isinstance(node, ast.UnaryOp) and isinstance(node.op, (ast.UAdd, ast.USub)):
            value = compile_node(node.operand)
            return lambda row: None if value(row) is None else value(row) * (-1 if isinstance(node.op, ast.USub) else 1)
        raise ValueError("Method requires other evidence or an unsupported expression")
    try:
        return compile_node(tree.body)
    except ValueError:
        return None


def selected_rows(rows, clauses, variables):
    """Apply only explicit EQ/IN value-level predicates. Never infer scope."""
    for clause in clauses:
        if (clause["variable"] not in variables or clause["comparator"] not in {"EQ", "IN"}
                or rows and clause["variable"] not in rows[0]):
            return None
    return [row for row in rows if all(
        not missing(row[c["variable"]]) and code(row[c["variable"]], variables[c["variable"]]["type"])
        in {code(v, variables[c["variable"]]["type"]) for v in c["values"]}
        for c in clauses
    )]


def build_report(root, study, outputs, target, revision, subject_key="USUBJID"):
    path = root / study / "spec/define/define-adam.xml"
    relative = path.relative_to(root).as_posix()
    metadata = define_metadata(path) if path.is_file() else {}
    _, documents = materials(root, study, target, metadata, only_paths={relative})
    doc = next((d for d in documents if d["path"] == relative), {})
    xml_hash = hashlib.sha256(path.read_bytes()).hexdigest() if path.is_file() else None
    citations, value_scopes = {}, {}
    if path.is_file():
        parsed = etree.parse(str(path), etree.XMLParser(resolve_entities=False, no_network=True))
        lines = path.read_text(encoding=parsed.docinfo.encoding).splitlines()
        elements = {e.get("OID"): e for e in parsed.iter() if e.get("OID")}
        for group in parsed.iter():
            if etree.QName(group).localname != "ItemGroupDef":
                continue
            domain = group.get("Name")
            citations[(domain, "")] = [group]
            for ref in group:
                if etree.QName(ref).localname != "ItemRef":
                    continue
                item = elements.get(ref.get("ItemOID"))
                if item is None:
                    continue
                linked = [item]
                for child in item:
                    identity = child.get("CodeListOID") or child.get("ValueListOID")
                    if identity in elements:
                        linked.append(elements[identity])
                    if child.get("ValueListOID") in elements:
                        value_scopes[(domain, item.get("Name"))] = [
                            sum(etree.QName(c).localname == "WhereClauseRef" for c in value_ref) == 1
                            for value_ref in elements[child.get("ValueListOID")]
                            if etree.QName(value_ref).localname == "ItemRef"]
                if ref.get("MethodOID") in elements:
                    linked.append(elements[ref.get("MethodOID")])
                pending = list(linked)
                seen = {e.get("OID") for e in linked}
                while pending:
                    for child in pending.pop().iter():
                        for key, identity in child.attrib.items():
                            if (key.rsplit("}", 1)[-1] in {"ItemOID", "CodeListOID", "WhereClauseOID", "MethodOID", "ValueListOID"}
                                    and identity in elements and identity not in seen):
                                seen.add(identity)
                                linked.append(elements[identity])
                                pending.append(elements[identity])
                citations[(domain, item.get("Name"))] = linked
        numbered = target / (doc.get("original", "documents/define-adam.xml") + ".source.html")
        numbered.parent.mkdir(parents=True, exist_ok=True)
        numbered.write_text(document_html("Retained ADaM Define-XML source",
            '<ol>' + ''.join(f'<li id="L{n}"><pre>{html.escape(line)}</pre></li>' for n, line in enumerate(lines, 1)) + '</ol>', wide=True))
        doc["source"] = numbered.relative_to(target).as_posix()
        write_json(target / "documents.json", documents)

    def original_citations(domain, variable):
        result = []
        for element in citations.get((domain, variable), citations.get((domain, ""), [])):
            first = element.sourceline
            tag = etree.QName(element).localname
            closing = re.compile(r"</(?:\w+:)?" + re.escape(tag) + r"\s*>")
            empty = re.compile(r"\s*<(?:\w+:)?" + re.escape(tag) + r"\b[^>]*?/\s*>")
            last = next((n for n in range(first, len(lines) + 1)
                         if closing.search(lines[n - 1]) or n == first and empty.match(lines[n - 1])), first)
            quote = "\n".join(lines[first - 1:last])
            result.append({"path": relative, "section": f"L{first}-L{last}", "quote": quote,
                           "context": quote, "lines": [first, last], "verified": True,
                           "repository": f"{REPO}/blob/{revision}/{relative}#L{first}-L{last}"})
        return result
    findings, checks, sources = [], [], []
    try:
        normalized = Document(path).metadata() if path.is_file() else None
        reason = "The retained ADaM Define-XML is unavailable." if normalized is None else ""
    except (ValueError, KeyError, AttributeError) as error:
        normalized, reason = None, f"Define-XML cannot be assessed: {error}"
    groups = (normalized or {}).get("datasets", {})
    codelists = (normalized or {}).get("codelists", {})

    def check(domain, variable, key, expected, observed, status="passed", rows=None,
              title=None, noncritical=False, section=None, population=None):
        record = {"id": f"{study}:{domain}:{variable or 'dataset'}:{key}",
                  "dataset": domain, "variable": variable, "check": key,
                  "status": status, "expected": str(expected), "observed": str(observed)}
        checks.append(record)
        if status in {"passed", "not_applicable"}:
            return
        source = sources[-1] if sources and sources[-1]["dataset"] == domain else {}
        measurement = None
        if rows is not None:
            values = {}
            for row in rows:
                actual = row.get(variable) if variable else "Invalid key"
                if isinstance(actual, (date, datetime)):
                    actual = actual.isoformat()
                if isinstance(actual, float) and not math.isfinite(actual):
                    actual = str(actual)
                expected_value = row.get("__dataset_define_expected", str(expected))
                signature = json.dumps([actual, expected_value], default=str)
                pattern = values.setdefault(signature, {"reference": actual, "observed": expected_value,
                    "row": "matched", "count": 0, "subjects": set()})
                pattern["count"] += 1
                if row.get(subject_key) is not None:
                    pattern["subjects"].add(str(row[subject_key]))
            measurement = {"compared": population if population is not None else source.get("rows", len(rows)), "differ": len(rows),
                "patterns": [{**p, "subjects": sorted(p["subjects"])} for p in values.values()]}
        title = title or key.replace("_", " ").capitalize()
        findings.append({
            **record, "comparison": "dataset_define",
            "kind": "inconsistent" if status == "different" else "gap" if status == "gap" else "unclear",
            "title": title, "observation": str(observed),
            "documents": original_citations(domain, variable),
            "spec": {"literal": False},
            "data": {"path": source.get("path", ""), "summary": json.dumps(source, sort_keys=True)},
            "evidence": {"dataset_check": measurement} if measurement is not None else {},
            "basis_hash": digest([record, source, xml_hash, measurement]),
            "critical": {"status": "no" if noncritical else "yes" if status == "different" else "needs_review",
                         "reason": "Presentation metadata differs." if noncritical else
                         "The dataset contradicts an explicit Define-XML declaration." if status == "different" else
                         "The two sources do not provide enough evidence for this check."},
            "recommendation": "Review the cited Define-XML declaration and the identified derived file. Confirm the intended metadata or data correction before changing either source.",
        })

    for domain, output in outputs.items():
        output = output.resolve()
        output.relative_to(root.resolve())
        table = pq.read_table(output)
        rows = table.to_pylist()
        source = {"dataset": domain, "role": "current_derived", "path": output.relative_to(root).as_posix(),
                  "sha256": hashlib.sha256(output.read_bytes()).hexdigest(),
                  "rows": table.num_rows, "columns": table.num_columns}
        sources.append(source)
        if normalized is None:
            check(domain, "", "define_unavailable", "Retained ADaM Define-XML", reason, "not_assessed")
            continue
        if normalized["unsupported_content"]:
            check(domain, "", "unsupported_metadata", "Supported Define-XML metadata",
                  "Unsupported XML content remains outside the checks: " + str(normalized["unsupported_content"]), "not_assessed")
        group = groups.get(domain)
        if group is None:
            check(domain, "", "dataset_inventory", "Dataset declared in Define-XML", f"{domain} is absent from Define-XML.", "gap")
            continue
        variables = group["variables"]
        for var in sorted(variables.keys() - set(table.column_names)):
            check(domain, var, "variable_inventory", "Variable present", "Declared variable is absent from the derived dataset.", "different")
        for var in sorted(set(table.column_names) - variables.keys()):
            check(domain, var, "variable_inventory", "Variable documented in Define-XML", "Derived variable is absent from Define-XML.", "gap")
        check(domain, "", "column_order", group["column_order"], table.column_names,
              "passed" if group["column_order"] == table.column_names else "different", noncritical=True)
        keys = [var for var, item in sorted(variables.items(), key=lambda pair: int(pair[1].get("key_sequence") or 0))
                if item.get("key_sequence")]
        if not keys:
            check(domain, "", "keys", "Explicit Define-XML keys", "No key declaration; uniqueness is not assessed.", "not_assessed")
        elif all(key in table.column_names for key in keys):
            counts = Counter(tuple(row[k] for k in keys) for row in rows)
            bad = [row for row in rows if any(missing(row[k]) or row[k] == "" for k in keys)
                   or counts[tuple(row[k] for k in keys)] > 1]
            check(domain, "", "keys", f"Unique nonmissing keys: {', '.join(keys)}",
                  f"{len(bad)} of {len(rows)} rows have duplicate or missing keys.",
                  "different" if bad else "passed", rows=bad)
        unavailable_labels, external_methods = [], []

        def inspect(var, item, selected, suffix="", section=None):
            values = [row[var] for row in selected]
            field = table.schema.field(var)
            compatible = logical_type(field, item, values)
            bad_type = ([r for r in selected if not missing(r[var]) and (not math.isfinite(r[var]) or int(r[var]) != r[var])]
                        if compatible is False and item["type"] == "integer" and pa.types.is_floating(field.type) else None)
            check(domain, var, "logical_type" + suffix, item["type"], str(field.type),
                  "passed" if compatible else "different" if compatible is False else "not_assessed",
                  section=section, rows=bad_type, population=len(selected))
            if item["type"] == "text" and item.get("length"):
                bad = [r for r in selected if not missing(r[var]) and len(str(r[var]).encode("utf-8")) > int(item["length"])]
                check(domain, var, "text_length" + suffix, f"At most {item['length']} UTF-8 bytes",
                      f"{len(bad)} of {len(selected)} selected rows exceed the declared text length.",
                      "different" if bad else "passed", rows=bad, section=section, population=len(selected))
            cl = codelists.get(item.get("codelist"))
            if cl:
                if cl["external"]:
                    check(domain, var, "codelist" + suffix, item["codelist"],
                          "External dictionary is not contained in these two sources.", "not_assessed", section=section)
                else:
                    allowed = {code(e["value"], cl["type"]) for e in cl["items"]}
                    bad = [r for r in selected if not missing(r[var]) and r[var] != "" and code(r[var], cl["type"]) not in allowed]
                    check(domain, var, "codelist" + suffix, ", ".join(sorted(allowed)),
                          f"{len(bad)} of {len(selected)} selected rows fall outside {item['codelist']}.",
                          "different" if bad else "passed", rows=bad, section=section, population=len(selected))

        for var, item in variables.items():
            if var not in table.column_names:
                continue
            field = table.schema.field(var)
            label = (field.metadata or {}).get(b"yamaa:label", (field.metadata or {}).get(b"label"))
            if label is None:
                unavailable_labels.append(var)
            else:
                label = label.decode("utf-8")
                check(domain, var, "label", item["label"], label,
                      "passed" if label == item["label"] else "different", noncritical=True)
            inspect(var, item, rows)
            for number, value_level in enumerate(item.get("value_level", []), 1):
                scope = value_scopes.get((domain, var), [])
                supported = number <= len(scope) and scope[number - 1]
                selected = selected_rows(rows, value_level["where"], variables) if supported and value_level["where"] else None
                if selected is None or not selected:
                    check(domain, var, f"value_level_{number}", str(value_level["where"]),
                          "Condition unsupported or no matching records; value-level checks are not assessed.", "not_assessed")
                else:
                    inspect(var, value_level, selected, f"_value_level_{number}")
            method = item.get("method")
            calculate = formula(method["description"], domain, set(table.column_names)) if method and item["type"] in {"integer", "float", "double"} and not item.get("significant_digits") else None
            if calculate:
                bad, error = [], None
                for row in rows:
                    try:
                        expected = calculate(row)
                        actual = row[var]
                        if isinstance(actual, date) and not isinstance(actual, datetime):
                            actual = (actual - date(1960, 1, 1)).days
                        equal = missing(actual) and missing(expected) or (
                            not missing(actual) and not missing(expected)
                            and math.isclose(actual, expected, rel_tol=0, abs_tol=1e-10))
                        if not equal:
                            bad.append({**row, "__dataset_define_expected": expected})
                    except (ValueError, TypeError, ZeroDivisionError, OverflowError) as exception:
                        error = str(exception)
                        break
                check(domain, var, "arithmetic_method", method["description"],
                      f"Arithmetic check unavailable: {error}" if error else f"{len(bad)} of {len(rows)} rows differ at absolute tolerance 1e-10.",
                      "not_assessed" if error else "different" if bad else "passed", rows=None if error else bad)
            elif method or item.get("origins"):
                external_methods.append(var)
            else:
                check(domain, var, "origin_method", "Documented origin or method", "Neither origin nor method is declared in Define-XML.", "gap")
        if unavailable_labels:
            check(domain, "", "labels_unavailable", "Labels stored in the actual dataset",
                  "Dataset label metadata is unavailable for: " + ", ".join(unavailable_labels), "not_assessed")
        if external_methods:
            check(domain, "", "derivation_verification", "Derivation verification from the two sources",
                  "Methods and origins retained for review; these derivations are not independently recalculated. Variables: " + ", ".join(external_methods), "not_assessed")

    for domain in sorted(groups.keys() - outputs.keys()):
        check(domain, "", "dataset_inventory", "Derived dataset available", "Define-XML declares a dataset outside the current derived output inventory.", "gap")
    counts = dict(Counter(c["status"] for c in checks))
    return {"schema_version": 1, "study": study, "revision": revision, "scope": "dataset_define",
            "sources": {"define": {"path": relative, "sha256": xml_hash}, "datasets": sources},
            "findings": findings, "logic_checks": [], "checks": checks, "check_counts": counts,
            "review": build_review(root, study, revision, findings, use_authored=False),
            "trace_examples": {}, "documents": [{k: v for k, v in d.items() if k != "sections"} for d in documents],
            "coverage": {"define_xml": "available" if normalized else "not_available",
                         "metadata": "Actual schema, stored labels, logical types, observed text lengths, declared keys, enumerated codelists, supported value-level conditions and literal arithmetic methods over this dataset's columns.",
                         "narrative": "Only +, -, *, / and numeric/date operands are evaluated, at absolute tolerance 1e-10. Methods needing rounding, other datasets, external dictionaries or narrative interpretation remain not assessed. Observed text lengths do not establish SAS allocation."},
            "note": "Findings compare current derived datasets with retained ADaM Define-XML. A passed check does not establish derivation correctness."}
