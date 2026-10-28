#!/usr/bin/env python3
"""Reproduce historical Define-XML 2.0 from the pilot's combined specifications."""

import argparse
from collections import Counter
from datetime import date, datetime
import json
import importlib.util
from pathlib import Path
import shutil

from lxml import etree
import pyarrow.parquet as pq
import yamaa
import yaml

from define_metadata import Document, compare

ROOT = Path(__file__).resolve().parents[2]
CREATED = {"cdiscpilot01": "2012-10-18T17:33:04", "submission-pilot3": "2023-05-01T17:47:59", "submission-pilot5": "2025-08-26T06:47:57"}


def audit_data(document, artifacts):
    """Check every declared bound against the project's derived artifacts.

    This is an independent export audit, not a replacement for yamaa's run
    checks. In particular, blank text is not silently treated as a null.
    """
    metadata = document.metadata()
    conflicts = []
    value_level_rows = {}
    for domain, dataset in metadata["datasets"].items():
        table = pq.read_table(artifacts[domain])
        data = table.to_pydict()
        indexes = {}
        selections = {}

        def selected_rows(where):
            key = tuple((c["variable"], c["comparator"], tuple(c["values"])) for c in where)
            if key in selections:
                return selections[key]
            selected = None
            for name, operator, values in key:
                if operator not in {"EQ", "IN", "NE", "NOTIN"}:
                    raise ValueError(f"Unsupported data audit comparator: {operator}")
                if name not in indexes:
                    index = {}
                    for row, value in enumerate(data[name]):
                        index.setdefault(value, set()).add(row)
                    indexes[name] = index
                included = set().union(*(indexes[name].get(value, set()) for value in values))
                if operator in {"NE", "NOTIN"}:
                    included = set(range(table.num_rows)) - included
                selected = included if selected is None else selected & included
            result = sorted(selected) if selected is not None else list(range(table.num_rows))
            selections[key] = result
            return result
        if table.column_names != dataset["column_order"]:
            conflicts.append({"dataset": domain, "check": "column_order"})
        key_names = sorted((v["key_sequence"], name) for name, v in dataset["variables"].items()
                           if v["key_sequence"] is not None)
        keys = list(zip(*(data[name] for _, name in key_names)))
        missing_keys = sum(any(value is None for value in key) for key in keys)
        if missing_keys:
            conflicts.append({"dataset": domain, "check": "missing_keys", "count": missing_keys})
        if len(set(keys)) != len(keys):
            conflicts.append({"dataset": domain, "check": "duplicate_keys", "count": len(keys) - len(set(keys))})
        for name, variable in dataset["variables"].items():
            values = data[name]
            checks = [(variable, range(table.num_rows), "column")]
            for index, entry in enumerate(variable["value_level"]):
                selected = selected_rows(entry["where"])
                value_level_rows[f"{domain}.{name}.{index + 1}"] = len(selected)
                checks.append((entry, selected, f"value_level/{index}"))
            for declaration, selected, scope in checks:
                violations = {}
                for row in selected:
                    value = values[row]
                    if value is None:
                        if declaration["mandatory"] == "Yes":
                            violations.setdefault("not_missing", []).append(value)
                        continue
                    kind = declaration["type"]
                    if kind == "integer" and not isinstance(value, (date, datetime)):
                        try:
                            integer = value == int(value)
                        except (ValueError, TypeError, OverflowError):
                            integer = False
                        if not integer:
                            violations.setdefault("integer_type", []).append(value)
                    if kind == "text":
                        if not isinstance(value, str):
                            violations.setdefault("text_type", []).append(value)
                        elif declaration["length"] and len(value) > int(declaration["length"]):
                            violations.setdefault("max_length", []).append(value)
                    if declaration["codelist"]:
                        codelist = metadata["codelists"][declaration["codelist"]]
                        if not codelist["external"]:
                            try:
                                coded = str(value) if codelist["type"] == "text" else str_numeric(value)
                            except (ValueError, TypeError, ArithmeticError):
                                violations.setdefault("codelist_type", []).append(value)
                                continue
                            allowed = {entry["value"] for entry in codelist["items"]}
                            if coded not in allowed:
                                violations.setdefault("codelist", []).append(value)
                for check, bad in violations.items():
                    counts = Counter(bad)
                    conflicts.append({"dataset": domain, "variable": name, "scope": scope,
                                      "check": check, "count": len(bad),
                                      "examples": [{"value": value, "count": count}
                                                   for value, count in counts.most_common(5)]})
    return {"conformant": not conflicts, "conflicts": conflicts, "value_level_rows": value_level_rows}


def str_numeric(value):
    from decimal import Decimal

    return str(Decimal(str(value)).normalize())


def generate(study_name, schema_root):
    from resolved_specs import process_study, specification_packet

    study = ROOT / study_name
    project_file = study / "spec/yamaa/project.yaml"
    declaration = yaml.safe_load(project_file.read_text())
    process_study(ROOT, study_name, check=True)
    project = yamaa.project(project_file)
    check = project.check()
    if check.status != "succeeded":
        raise ValueError(str(check.issues.to_pylist()))
    runs = project.run("adam")
    if runs.status != "succeeded":
        raise ValueError(str(runs.issues.to_pylist()))
    runs.save()
    module = importlib.util.spec_from_file_location("study_comparator", study / "program/adam/python/compare.py")
    comparator = importlib.util.module_from_spec(module)
    module.loader.exec_module(comparator)
    if hasattr(comparator, "compare_domain"):
        datasets = [comparator.compare_domain(name) for name in comparator.DATASETS]
    else:
        datasets = []
        for name in comparator.DATASETS:
            matched = comparator.compare(name)
            reference_name = getattr(comparator, "EXPECTED_NAMES", {}).get(name, name)
            shape = pq.read_schema(study / "data/adam" / f"{reference_name}.parquet")
            rows = pq.ParquetFile(study / "data/adam" / f"{reference_name}.parquet").metadata.num_rows
            datasets.append({"dataset": name, "ok": matched, "columns": len(shape), "rows": rows, "cells": rows * len(shape)})
    if not all(result["ok"] for result in datasets):
        raise ValueError("ADaM reference comparison failed")

    artifacts = {}
    for relative in declaration["adam"]["specs"]:
        spec_file = (project_file.parent / relative).resolve()
        domain = yaml.safe_load(spec_file.read_text())["domain"]
        # A layered specification inherits its output; the engine names its location.
        packet = specification_packet(ROOT, spec_file)
        artifacts[domain] = ROOT / packet["resources"]["output.path"]
    candidate = (project_file.parent / declaration["adam"]["define"]).resolve()
    for supporting in declaration["adam"].get("documents", []):
        # These studies stage their reviewer guide under its original filename.
        if supporting["kind"] != "supplemental":
            continue
        guide = study / "spec/source" / supporting["link"]
        guide_copy = candidate.parent / supporting["link"]
        if guide_copy.exists() and guide_copy.read_bytes() != guide.read_bytes():
            raise ValueError(f"Refusing to overwrite a different reviewer guide: {guide_copy}")
        shutil.copyfile(guide, guide_copy)
    submission = project.submission("adam", created=CREATED[study_name])
    if submission.status != "succeeded":
        raise ValueError(str(submission.issues.to_pylist()))
    submission.save()
    first_xml = candidate.read_bytes()
    repeated = project.submission("adam", created=CREATED[study_name])
    if repeated.status != "succeeded":
        raise ValueError(str(repeated.issues.to_pylist()))
    repeated.save()
    if candidate.read_bytes() != first_xml:
        raise ValueError("Repeated native composition changed the XML bytes")

    # Use the authoritative, local schema bundle; never follow network imports.
    parser = etree.XMLParser(no_network=True, resolve_entities=False)
    xsd = schema_root / "define/2.0/define2-0-0.xsd"
    schema = etree.XMLSchema(etree.parse(str(xsd), parser))
    schema.assertValid(etree.parse(str(candidate), parser))
    reference = study / "spec/define/define-adam.xml"
    legacy = study_name == "cdiscpilot01"
    if legacy:
        from compare_legacy_define import compare_legacy
        comparison = compare_legacy(reference, candidate)
    else:
        comparison = compare(reference, candidate)
    if comparison["candidate_define_version"] != "2.0.0":
        raise ValueError("The reproduction requires native Define-XML 2.0.0 output")
    data = audit_data(Document(candidate), artifacts)
    reference_artifacts = {domain: study / "data/adam" / f"{domain.lower()}.parquet" for domain in artifacts}
    if legacy:
        from legacy_define import LegacyDocument
        original = LegacyDocument(reference)
        reference_data = audit_data(original, reference_artifacts)
        reference_data["complete"] = not original.unresolved
        reference_data["unresolved_declarations"] = original.unresolved
        reference_data["conformant"] = reference_data["conformant"] and reference_data["complete"]
        matched = comparison["comparable_metadata_equal"]
        approved_scope = not comparison["unexpected_differences"] and not any(
            u["reason"] != "Legacy DomainKeys names variables absent from its dataset" for u in comparison["unresolved"])
    else:
        reference_data = audit_data(Document(reference), reference_artifacts)
        matched = comparison["metadata_equivalent"]
        approved_scope = matched
    result = {
        # Reproducing historical declarations and their truth about the data
        # are separate claims. Preserve the audit failures in full.
        "status": ("compared_with_gaps" if legacy else "succeeded") if approved_scope else "incomplete",
        "study": study_name, "yamaa_version": yamaa.__version__, "derivation_succeeded": True,
        "composition_succeeded": True,
        "deterministic_xml": True,
        "xml_schema_valid": True, "candidate": candidate.relative_to(ROOT).as_posix(),
        "datasets": datasets, "comparison": comparison, "data_audit": data,
        "reference_data_audit": reference_data,
        "metadata_reproduction_matched": matched and not legacy,
        "approved_comparison_scope_satisfied": approved_scope,
        "submission_data_conformant": data["conformant"],
        "historical_package_links": [
            {"dataset": name, "link": dataset["artifact"]["link"],
             "available": (candidate.parent / dataset["artifact"]["link"]).is_file()}
            for name, dataset in Document(candidate).metadata()["datasets"].items()
            if dataset["artifact"]
        ],
        "limits": [
            ("The reference uses Define-XML 1.0 and the candidate uses 2.0. Known differences and unsupported source content are reported; full reproduction is false."
             if legacy else "The candidate reproduces the published Define-XML 2.0 metadata; XML byte identity is reported separately."),
            "One project and one specification per dataset produce both the Parquet data and its Define-XML metadata.",
            "Historical XPT/JSON package links are retained literally; no transport is generated or certified.",
            "Historical metadata is not enforced as a data constraint; executable types, keys and explicit verifications still apply.",
            "A schema-valid XML document can still disagree with the reference or its datasets.",
        ],
    }
    from study_evidence import engine_revision
    result["yamaa_revision"] = engine_revision(ROOT, study_name)
    result["supporting_documents"] = [{"link": d["link"], "available": (candidate.parent / d["link"]).is_file()}
                                      for d in declaration["adam"].get("documents", [])]
    stylesheet = declaration["adam"].get("stylesheet")
    result["stylesheet"] = {"link": stylesheet, "available": bool(stylesheet and (candidate.parent / stylesheet).is_file())}
    if legacy:
        result["full_reference_reproduced"] = False
        result["limits"].extend([
            "Draft ADaMRes displays/results and unbound document leaves are inventoried, not generated.",
            "Value-level optional metadata inherits from its parent in yamaa; the legacy omission differences remain different fields.",
            "An absent LBSEQ in the reference ADLBHY DomainKeys is unresolved, not added to the data or XML.",
            "XML schema validation is not a complete business-rule or regulatory conformance assessment.",
        ])
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("study", choices=CREATED)
    parser.add_argument("--schemas", type=Path, required=True,
                        help="rust/tests/schemas directory from the pinned yamaa source checkout")
    args = parser.parse_args()
    destination = ROOT / ".build" / f"{args.study}-define"
    destination.mkdir(parents=True, exist_ok=True)
    report_path = destination / "report.json"
    # Remove earlier success evidence and XML before attempting a fresh build.
    report_path.unlink(missing_ok=True)
    for name in ("comparison.json", "comparison.html"):
        (destination / name).unlink(missing_ok=True)
    project_file = ROOT / args.study / "spec/yamaa/project.yaml"
    declaration = yaml.safe_load(project_file.read_text())
    (project_file.parent / declaration["adam"]["define"]).resolve().unlink(missing_ok=True)
    report = {"status": "failed", "composition_succeeded": False, "xml_schema_valid": False}
    try:
        report = generate(args.study, args.schemas.resolve())
    except Exception as error:
        report["error"] = str(error)
    report_path.write_text(json.dumps(report, indent=2) + "\n")
    if args.study == "cdiscpilot01" and "comparison" in report:
        from define_report import write_legacy_report
        (destination / "comparison.json").write_text(json.dumps(report["comparison"], indent=2) + "\n")
        write_legacy_report(destination / "comparison.html", report)
    print(f"{report['status']}: {report_path}")
    if "comparison" in report:
        print(f"Metadata differences: {len(report['comparison']['differences'])}")
        print(f"Data conflicts: {len(report['data_audit']['conflicts'])}")
    return int(report["status"] not in {"succeeded", "compared_with_gaps"})


if __name__ == "__main__":
    raise SystemExit(main())
