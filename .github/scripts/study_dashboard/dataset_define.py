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
from .documents import attributes, define_metadata, description, document_html, local_name, materials
from .datasets import write_json
from .issues import build_review, digest
from .review_scope import complete_decisions, dataset_define_review

REPO = "https://github.com/RConsortium/submissions-pilot7-synthetic-data"


def missing(value):
    return value is None or isinstance(value, str) and not value.strip() or isinstance(value, float) and math.isnan(value)


def code(value, kind):
    if kind in {"integer", "float", "double"}:
        try:
            return str(Decimal(str(value)).normalize())
        except InvalidOperation:
            pass
    return str(value).strip()


def numeric_equal(left, right):
    try:
        return math.isclose(float(left), float(right), rel_tol=0, abs_tol=1e-10)
    except (TypeError, ValueError, OverflowError):
        return False


def integral(value):
    return missing(value) or math.isfinite(value) and numeric_equal(value, round(value))


def member(value, allowed, kind):
    if kind in {"integer", "float", "double"}:
        return any(numeric_equal(value, candidate) for candidate in allowed)
    return str(value).strip() in {str(candidate).strip() for candidate in allowed}


def legacy_metadata(path, metadata):
    """Read native Define-XML 1.0 declarations without translating their types.

    Legacy value-level ItemDef names are parameter codes. Use that selector
    only when the parent dataset declares PARAMCD and the code is enumerated.
    Unresolvable value-level scope remains coverage, not a guessed condition.
    """
    tree = etree.parse(str(path), etree.XMLParser(resolve_entities=False, no_network=True))
    lists, groups = {}, {}
    for element in tree.iter():
        if not isinstance(element.tag, str) or local_name(element) != "CodeList":
            continue
        attrs = attributes(element)
        lists[attrs["OID"]] = {
            "type": attrs.get("DataType", "text"),
            "external": next((attributes(e) for e in element if local_name(e) == "ExternalCodeList"), None),
            "items": [{"value": e.get("CodedValue", "").strip()}
                      for e in element if local_name(e) in {"CodeListItem", "EnumeratedItem"}],
        }
    for group in tree.iter():
        if not isinstance(group.tag, str) or local_name(group) != "ItemGroupDef":
            continue
        attrs = attributes(group)
        domain = attrs.get("Name", "")
        keys = [k.strip() for k in attrs.get("DomainKeys", "").split(",") if k.strip()]
        variables = {}
        for name, original in metadata.get(domain, {}).items():
            item = {**original,
                    "method": {"description": original["method"] or original["comment"]}
                              if original["method"] or original["comment"] else None,
                    "key_sequence": str(keys.index(name) + 1) if name in keys else None,
                    "codelist": (original.get("codelist") or {}).get("oid")}
            value_level = []
            codes = {entry["value"] for entry in (metadata[domain].get("PARAMCD", {}).get("codelist") or {}).get("items", [])}
            for value in original.get("value_level", []):
                value_level.append({**value,
                    "where": [{"variable": "PARAMCD", "comparator": "EQ", "values": [value["name"]]}]
                             if "PARAMCD" in metadata[domain] and value["name"] in codes else [],
                    "codelist": value.get("codelist_oid"),
                    "method": {"description": value["method"] or value["comment"]}
                              if value["method"] or value["comment"] else None})
            item["value_level"] = value_level
            variables[name] = item
        groups[domain] = {"variables": variables, "column_order": list(variables)}
    return {"datasets": groups, "codelists": lists, "unsupported_content": [], "legacy": True}


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
        return kind != "integer" or all(integral(v) for v in values)
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
    except (SyntaxError, ValueError):
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
        not missing(row[c["variable"]]) and member(row[c["variable"]], c["values"], variables[c["variable"]]["type"])
        for c in clauses
    )]


def method_calculation(text, domain, names, variable):
    """Recognize a small, literal subset; never infer rounding or grouping."""
    text = " ".join((text or "").split()).strip().rstrip(".")
    plain = formula(text, domain, names)
    if plain:
        return plain, None
    missing_rule = re.fullmatch(r"(?:Set(?: " + re.escape(variable) + r")? to missing|Value: null)", text, re.I)
    if missing_rule:
        return lambda row: None, None
    constant = re.fullmatch(r"Set(?: " + re.escape(variable) + r")? to ['\"]?([A-Za-z0-9_]+)['\"]?|Value: ([A-Za-z0-9_]+)", text, re.I)
    if constant:
        value = constant.group(1) or constant.group(2)
        return lambda row: value, None
    quoted = re.fullmatch(r"Set(?: " + re.escape(variable) + r")? to (['\"])(.*?)\1", text, re.I)
    if quoted:
        value = quoted.group(2)
        return lambda row: value, None
    postbaseline = re.fullmatch(r"(.+), for post baseline records", text, re.I)
    if postbaseline and "ABLFL" in names:
        calculation = formula(postbaseline.group(1), domain, names)
        if calculation:
            return calculation, "postbaseline"
    if "ABLFL" in names and re.fullmatch(r"Set " + re.escape(variable) + r" to missing for post baseline records\. Set to ([A-Z0-9_]+)\.([A-Z0-9_]+) where \1\.VISIT=BASELINE and \1\.[A-Z0-9_]+=([A-Z0-9_]+)", text):
        return lambda row: None, "postbaseline"
    return None, None


def predecessor_comparison(root, study, domain, variable, source, table, keys, outputs):
    """Validate an explicitly named source; dataset keys determine row alignment."""
    from verify_derivations import copy_check
    from .domains import domain_keys
    import polars as pl

    # The verifier's copy adapter is shared with the raw audit. The source
    # inventory is independent of generated outputs and is never modified.
    source_domain = source.split(".")[0]
    for section in ("sdtm", "adam"):
        declaration = root / study / f"spec/define/define-{section}.xml"
        declared_keys = domain_keys(declaration).get(source_domain, []) if declaration.is_file() else []
        if declared_keys and all(key in table.column_names for key in declared_keys):
            keys = declared_keys
            break
    spec = {"keys": keys, "columns": [{"name": variable, "derivation": source}]}
    result = copy_check(root / study, spec, {"reference": pl.from_arrow(table)},
                        variable, source, "USUBJID")
    if result.get("status") == "checked" and pa.types.is_date(table.schema.field(variable).type):
        comparison = result["reference"]
        retained, unsupported = [], 0
        for pattern in comparison["patterns"]:
            actual, expected = pattern["reference"], pattern["observed"]
            try:
                if pattern["row"] == "matched" and actual is not None and expected is not None:
                    text = str(expected)
                    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}(?:T\d{2}:\d{2}(?::\d{2}(?:\.\d+)?)?(?:Z|[+-]\d{2}:\d{2})?)?", text):
                        raise ValueError("A complete ISO date or date/time is required")
                    expected_date = datetime.fromisoformat(text.replace("Z", "+00:00")).date() if "T" in text else date.fromisoformat(text)
                    same_date = date.fromisoformat(str(actual)) == expected_date
                else:
                    same_date = False
            except ValueError:
                unsupported += pattern["count"]
                continue
            if not same_date:
                retained.append(pattern)
        result["reference"] = {**comparison, "patterns": retained,
                               "compared": comparison["compared"] - unsupported,
                               "differ": sum(pattern["count"] for pattern in retained)}
        result["unassessed_rows"] = unsupported
    return result


def build_report(root, study, outputs, target, revision, subject_key="USUBJID", documents=None, comparison_keys=None, source_role="current_derived"):
    path = root / study / "spec/define/define-adam.xml"
    relative = path.relative_to(root).as_posix()
    metadata = define_metadata(path) if path.is_file() else {}
    if documents is None:
        _, documents = materials(root, study, target, metadata, only_paths={relative})
    doc = next((d for d in documents if d["path"] == relative), {})
    xml_hash = hashlib.sha256(path.read_bytes()).hexdigest() if path.is_file() else None
    citations, value_scopes = {}, {}
    if path.is_file():
        parsed = etree.parse(str(path), etree.XMLParser(resolve_entities=False, no_network=True))
        lines = path.read_text(encoding=parsed.docinfo.encoding).splitlines()
        elements = {e.get("OID"): e for e in parsed.iter() if e.get("OID")}
        for group in parsed.iter():
            if not isinstance(group.tag, str) or etree.QName(group).localname != "ItemGroupDef":
                continue
            domain = group.get("Name")
            citations[(domain, "")] = [group]
            for ref in group:
                if not isinstance(ref.tag, str) or etree.QName(ref).localname != "ItemRef":
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
                            sum(isinstance(c.tag, str) and etree.QName(c).localname == "WhereClauseRef" for c in value_ref) == 1
                            for value_ref in elements[child.get("ValueListOID")]
                            if isinstance(value_ref.tag, str) and etree.QName(value_ref).localname == "ItemRef"]
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
        aliases = {}
        for (domain, variable), linked in citations.items():
            if variable:
                aliases.setdefault(linked[0].sourceline, []).append(f"{domain}.{variable}")
        numbered.write_text(document_html("Retained ADaM Define-XML source",
            '<ol>' + ''.join(f'<li id="L{n}">' + ''.join(f'<span id="{html.escape(alias)}"></span>' for alias in aliases.get(n, []))
                            + f'<pre>{html.escape(line)}</pre></li>' for n, line in enumerate(lines, 1)) + '</ol>', wide=True))
        doc["source"] = numbered.relative_to(target).as_posix()
        if doc.get("view_label") == "XML source":
            doc["view"] = doc["source"]
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
        if path.is_file():
            root_tag = etree.parse(str(path), etree.XMLParser(resolve_entities=False, no_network=True)).getroot().tag
            normalized = legacy_metadata(path, metadata) if root_tag == "{http://www.cdisc.org/ns/odm/v1.2}ODM" else Document(path).metadata()
        else:
            normalized = None
        reason = "The retained ADaM Define-XML is unavailable." if normalized is None else ""
    except (ValueError, KeyError, AttributeError) as error:
        normalized, reason = None, f"Define-XML cannot be assessed: {error}"
    groups = (normalized or {}).get("datasets", {})
    codelists = (normalized or {}).get("codelists", {})

    coverage_items = []

    def check(domain, variable, key, expected, observed, status="passed", rows=None,
              title=None, noncritical=False, section=None, population=None):
        record = {"id": f"{study}:{domain}:{variable or 'dataset'}:{key}",
                  "dataset": domain, "variable": variable, "check": key,
                  "status": status, "expected": str(expected), "observed": str(observed)}
        checks.append(record)
        if status in {"passed", "not_applicable"}:
            return
        if status == "not_assessed":
            coverage_items.append({"id": record["id"], "dataset": domain,
                                   "variable": variable, "title": title or key.replace("_", " ").capitalize(),
                                   "reason": str(observed), "source": relative})
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
        source = {"dataset": domain, "role": source_role, "path": output.relative_to(root).as_posix(),
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
            bad = [row for row in rows if counts[tuple(row[k] for k in keys)] > 1]
            check(domain, "", "keys", f"Unique keys: {', '.join(keys)}",
                  f"{len(bad)} of {len(rows)} rows have duplicate key combinations.",
                  "different" if bad else "passed", rows=bad)
            incomplete = sum(any(missing(row[k]) or row[k] == "" for k in keys) for row in rows)
            if incomplete:
                check(domain, "", "missing_key_values", "Review incomplete key combinations",
                      f"{incomplete} rows have missing key values. KeySequence alone does not establish a nonmissing-value requirement.", "not_assessed")
        unavailable_labels, external_methods = [], []
        baseline_dates = {}
        baseline_keys = [key for key in ("STUDYID", subject_key, "PARAMCD") if key in table.column_names]
        for row in rows:
            if row.get("ABLFL") == "Y" and not missing(row.get("ADT")):
                identity = tuple(row[key] for key in baseline_keys)
                baseline_dates.setdefault(identity, set()).add(row["ADT"])

        def inspect(var, item, selected, suffix="", section=None):
            values = [row[var] for row in selected]
            field = table.schema.field(var)
            compatible = logical_type(field, item, values)
            bad_type = ([r for r in selected if not integral(r[var])]
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
                    bad = [r for r in selected if not missing(r[var]) and r[var] != "" and not member(r[var], allowed, cl["type"])]
                    check(domain, var, "codelist" + suffix, ", ".join(sorted(allowed)),
                          f"{len(bad)} of {len(selected)} selected rows fall outside {item['codelist']}.",
                          "different" if bad else "passed", rows=bad, section=section, population=len(selected))

        def inspect_method(var, item, selected, suffix=""):
            method = item.get("method")
            text = method.get("description", "") if method else ""
            calculate, predicate = method_calculation(text, domain, set(table.column_names), var)
            if not calculate:
                return False
            if predicate == "postbaseline":
                known, unknown = [], 0
                for row in selected:
                    candidates = baseline_dates.get(tuple(row[key] for key in baseline_keys), set())
                    if len(candidates) != 1 or missing(row.get("ADT")):
                        unknown += 1
                    elif row["ADT"] > next(iter(candidates)):
                        known.append(row)
                if unknown:
                    check(domain, var, "postbaseline_scope" + suffix, text,
                          f"{unknown} records lack an unambiguous baseline/date ordering; their method scope is not assessed.", "not_assessed")
                selected = known
            else:
                selected = [row for row in selected if predicate is None or predicate(row)]
            bad, errors, precision_skipped = [], [], 0
            for row in selected:
                try:
                    expected = calculate(row)
                    actual = row[var]
                    if isinstance(actual, date) and not isinstance(actual, datetime):
                        actual = (actual - date(1960, 1, 1)).days
                    # Numeric capacity is not an instruction to round the
                    # derivation. Preserve missing/nonmissing disagreements;
                    # a numeric difference needs an explicit precision policy.
                    if item.get("significant_digits") and isinstance(actual, (int, float)) and isinstance(expected, (int, float)) and not numeric_equal(actual, expected):
                        try:
                            quantum = 10.0 ** -int(item["significant_digits"])
                        except (TypeError, ValueError, OverflowError):
                            quantum = 0
                        if abs(actual - expected) < quantum:
                            precision_skipped += 1
                            continue
                    equal = (missing(actual) or actual == "") and (missing(expected) or expected == "") or (
                        not missing(actual) and not missing(expected) and (
                            numeric_equal(actual, expected) if isinstance(actual, (int, float)) and isinstance(expected, (int, float)) else actual == expected))
                    if not equal:
                        bad.append({**row, "__dataset_define_expected": expected})
                except (ValueError, TypeError, ZeroDivisionError, OverflowError) as error:
                    errors.append(str(error))
            if errors:
                check(domain, var, "arithmetic_unassessed" + suffix, text,
                      f"{len(errors)} rows could not be evaluated: {errors[0]}", "not_assessed")
            if precision_skipped:
                check(domain, var, "numeric_precision" + suffix, text,
                      f"{precision_skipped} differing numeric comparisons lie within the declared decimal capacity; no equality or rounding algorithm is inferred.", "not_assessed")
            population = len(selected) - len(errors) - precision_skipped
            if population:
                check(domain, var, "arithmetic_method" + suffix, text,
                      f"{len(bad)} of {population} evaluated rows differ at absolute tolerance 1e-10.",
                      "different" if bad else "passed", rows=bad, population=population)
            return True

        def inspect_sources(var, item, selected, suffix=""):
            method = item.get("method")
            explicit_sources = [origin.get("description", "") for origin in item.get("origins", [])
                                if origin.get("type", "").lower() == "predecessor"]
            if method and re.fullmatch(r"[A-Z][A-Z0-9_]*\.[A-Z][A-Z0-9_]*", method["description"]):
                explicit_sources.append(method["description"])
            explicit_sources = list(dict.fromkeys(source for source in explicit_sources
                                                 if re.fullmatch(r"[A-Z][A-Z0-9_]*\.[A-Z][A-Z0-9_]*", source)))
            if not selected:
                return bool(explicit_sources)
            for number, source_name in enumerate(explicit_sources, 1):
                result = predecessor_comparison(root, study, domain, var, source_name, pa.Table.from_pylist(selected, schema=table.schema),
                                                (comparison_keys or {}).get(domain, keys), outputs)
                key_suffix = suffix + ("" if len(explicit_sources) == 1 else f"_{number}")
                if result["status"] == "source_variable_missing":
                    check(domain, var, "predecessor_source" + key_suffix, source_name,
                          result["reason"], "gap", title="Documented source variable is absent")
                elif result["status"] == "checked":
                    comparison = result["reference"]
                    if result.get("unassessed_rows"):
                        check(domain, var, "predecessor_unassessed" + key_suffix, source_name,
                              f"{result['unassessed_rows']} source values require unsupported partial/invalid date conversion.", "not_assessed")
                    key = "predecessor_copy" + key_suffix
                    check(domain, var, key, source_name,
                          f"{comparison['differ']} of {comparison['compared']} records differ from the documented source.",
                          "different" if comparison["differ"] else "passed", title="Documented predecessor copy")
                    if comparison["differ"]:
                        findings[-1]["evidence"] = {"dataset_check": comparison}
                        findings[-1]["basis_hash"] = digest([findings[-1]["basis_hash"], comparison])
                else:
                    check(domain, var, "predecessor_unassessed" + key_suffix, source_name,
                          result.get("reason", "The named source is unavailable or cannot be aligned uniquely."), "not_assessed")
            return bool(explicit_sources)

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
            value_level = item.get("value_level", [])
            selected_ids = set()
            unknown_scope = False
            if not value_level:
                inspect(var, item, rows)
            for number, value_level in enumerate(item.get("value_level", []), 1):
                scope = value_scopes.get((domain, var), [])
                supported = bool(normalized.get("legacy")) or number <= len(scope) and scope[number - 1]
                selected = selected_rows(rows, value_level["where"], variables) if supported and value_level["where"] else None
                if selected is None:
                    unknown_scope = True
                    check(domain, var, f"value_level_{number}", str(value_level["where"]),
                          "Condition unsupported; value-level checks are not assessed.", "not_assessed")
                elif not selected:
                    check(domain, var, f"value_level_{number}", str(value_level["where"]),
                          "No records have the declared value-level condition.", "not_applicable")
                else:
                    selected_ids.update(id(row) for row in selected)
                    inspect(var, value_level, selected, f"_value_level_{number}")
                    sources_assessed = inspect_sources(var, value_level, selected, f"_value_level_{number}")
                    method_assessed = inspect_method(var, value_level, selected, f"_value_level_{number}")
                    if not sources_assessed and not method_assessed and (value_level.get("method") or value_level.get("origins")):
                        check(domain, var, f"value_method_{number}", str(value_level["where"]),
                              "The selected value-level rule is retained, but this method requires additional evidence or unsupported narrative interpretation.", "not_assessed")
            remaining = [] if unknown_scope else [row for row in rows if id(row) not in selected_ids]
            if item.get("value_level") and remaining:
                inspect(var, item, remaining)
            method = item.get("method")
            explicit_sources = inspect_sources(var, item, remaining if item.get("value_level") else rows)
            if inspect_method(var, item, remaining if item.get("value_level") else rows):
                pass
            elif explicit_sources or item.get("value_level"):
                pass
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
    review = build_review(root, study, revision, findings, use_authored=False)
    review = dataset_define_review(review, complete_decisions(review))
    return {"schema_version": 1, "study": study, "revision": revision, "scope": "dataset_define",
            "sources": {"define": {"path": relative, "sha256": xml_hash}, "datasets": sources},
            "findings": findings, "logic_checks": [], "checks": checks, "check_counts": counts,
            "coverage_items": coverage_items,
            "review": review,
            "trace_examples": {}, "documents": [{k: v for k, v in d.items() if k != "sections"} for d in documents],
            "coverage": {"define_xml": "available" if normalized else "not_available",
                         "metadata": "Actual schema, stored labels, logical types, observed text lengths, declared keys, enumerated codelists, supported value-level conditions and literal arithmetic methods over this dataset's columns.",
                         "narrative": "Only +, -, *, / and numeric/date operands are evaluated, at absolute tolerance 1e-10. Methods needing rounding, other datasets, external dictionaries or narrative interpretation remain not assessed. Observed text lengths do not establish SAS allocation."},
            "note": "Findings compare current derived datasets with retained ADaM Define-XML. A passed check does not establish derivation correctness."}
