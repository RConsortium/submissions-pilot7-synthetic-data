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
CREATED = {"submission-pilot3": "2023-05-01T17:47:59", "submission-pilot5": "2025-08-26T06:47:57"}


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
                selected = []
                for row in range(table.num_rows):
                    matches = []
                    for condition in entry["where"]:
                        value = data[condition["variable"]][row]
                        included = value in condition["values"]
                        op = condition["comparator"]
                        if op not in {"EQ", "IN", "NE", "NOTIN"}:
                            raise ValueError(f"Unsupported data audit comparator: {op}")
                        matches.append(not included if op in {"NE", "NOTIN"} else included)
                    if all(matches):
                        selected.append(row)
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
                    if kind == "integer" and not isinstance(value, (date, datetime)) and value != int(value):
                        violations.setdefault("integer_type", []).append(value)
                    if kind == "text" and declaration["length"] and len(value) > int(declaration["length"]):
                        violations.setdefault("max_length", []).append(value)
                    if declaration["codelist"]:
                        codelist = metadata["codelists"][declaration["codelist"]]
                        if not codelist["external"]:
                            coded = str(value) if codelist["type"] == "text" else str_numeric(value)
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
    study = ROOT / study_name
    project_file = study / "spec/yamaa/project.yaml"
    declaration = yaml.safe_load(project_file.read_text())
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
    datasets = [comparator.compare_domain(name) for name in comparator.DATASETS]
    if not all(result["ok"] for result in datasets):
        raise ValueError("ADaM reference comparison failed")

    artifacts = {}
    for relative in declaration["adam"]["specs"]:
        spec_file = project_file.parent / relative
        spec = yaml.safe_load(spec_file.read_text())
        artifacts[spec["domain"]] = (spec_file.parent / spec["output"]["path"]).resolve()
    candidate = (project_file.parent / declaration["adam"]["define"]).resolve()
    guide = study / "spec/source/adrg.pdf"
    guide_copy = candidate.parent / "adrg.pdf"
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
    comparison = compare(reference, candidate)
    if comparison["candidate_define_version"] != "2.0.0":
        raise ValueError("The reproduction requires native Define-XML 2.0.0 output")
    data = audit_data(Document(candidate), artifacts)
    reference_artifacts = {domain: study / "data/adam" / f"{domain.lower()}.parquet" for domain in artifacts}
    reference_data = audit_data(Document(reference), reference_artifacts)
    return {
        # Reproducing historical declarations and their truth about the data
        # are separate claims. Preserve the audit failures in full.
        "status": "succeeded" if comparison["metadata_equivalent"] else "incomplete",
        "study": study_name, "yamaa_version": yamaa.__version__, "derivation_succeeded": True,
        "composition_succeeded": True,
        "deterministic_xml": True,
        "xml_schema_valid": True, "candidate": candidate.relative_to(ROOT).as_posix(),
        "datasets": datasets, "comparison": comparison, "data_audit": data,
        "reference_data_audit": reference_data,
        "metadata_reproduction_matched": comparison["metadata_equivalent"],
        "submission_data_conformant": data["conformant"],
        "historical_package_links": [
            {"dataset": name, "link": dataset["artifact"]["link"],
             "available": (candidate.parent / dataset["artifact"]["link"]).is_file()}
            for name, dataset in Document(candidate).metadata()["datasets"].items()
            if dataset["artifact"]
        ],
        "limits": [
            "The candidate reproduces the published Define-XML 2.0 metadata; XML byte identity is reported separately.",
            "One project and one specification per dataset produce both the Parquet data and its Define-XML metadata.",
            "Historical XPT/JSON package links are retained literally; no transport is generated or certified.",
            "Historical metadata is not enforced as a data constraint; executable types, keys and explicit verifications still apply.",
            "A schema-valid XML document can still disagree with the reference or its datasets.",
        ],
    }


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
    project_file = ROOT / args.study / "spec/yamaa/project.yaml"
    declaration = yaml.safe_load(project_file.read_text())
    (project_file.parent / declaration["adam"]["define"]).resolve().unlink(missing_ok=True)
    report = {"status": "failed", "composition_succeeded": False, "xml_schema_valid": False}
    try:
        report = generate(args.study, args.schemas.resolve())
    except Exception as error:
        report["error"] = str(error)
    report_path.write_text(json.dumps(report, indent=2) + "\n")
    print(f"{report['status']}: {report_path}")
    if "comparison" in report:
        print(f"Metadata differences: {len(report['comparison']['differences'])}")
        print(f"Data conflicts: {len(report['data_audit']['conflicts'])}")
    return int(report["status"] != "succeeded")


if __name__ == "__main__":
    raise SystemExit(main())
