#!/usr/bin/env python3
"""Generate Pilot 3 Define-XML and fail unless schema, metadata and data checks pass."""

import argparse
from collections import Counter
from datetime import date, datetime
import json
from pathlib import Path
import shutil

from lxml import etree
import pyarrow.parquet as pq
import yamaa

from compare import DATASETS, compare_domain
from define_compare import Document, compare

STUDY = Path(__file__).resolve().parents[3]
ROOT = STUDY.parent
DESTINATION = ROOT / ".build/pilot3-define"
PROJECT = STUDY / "spec/yamaa/submission/project.yaml"
REFERENCE = STUDY / "spec/define/define-adam.xml"
CREATED = "2023-05-01T17:47:59"


def audit_data(document, directory):
    """Check every declared bound against the unchanged derived artifacts.

    This is an independent export audit, not a replacement for yamaa's run
    checks. In particular, blank text is not silently treated as a null.
    """
    metadata = document.metadata()
    conflicts = []
    value_level_rows = {}
    for domain, dataset in metadata["datasets"].items():
        table = pq.read_table(directory / f"{domain.lower()}.parquet")
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


def generate(schema_root):
    # Build and compare the original pipeline first. The submission layers do
    # not alter the production derivations, references, or comparison policy.
    runs = yamaa.project(STUDY / "spec/yamaa/project.yaml").run("adam")
    if runs.status != "succeeded":
        raise ValueError(str(runs.issues.to_pylist()))
    runs.save()
    datasets = [compare_domain(name) for name in DATASETS]
    if not all(result["ok"] for result in datasets):
        raise ValueError("ADaM reference comparison failed")

    directory = DESTINATION / "data"
    directory.mkdir(parents=True, exist_ok=True)
    for name in DATASETS:
        shutil.copyfile(STUDY / f"data/adam/{name}-yamaa.parquet", directory / f"{name}.parquet")
    shutil.copyfile(STUDY / "spec/source/adrg.pdf", directory / "adrg.pdf")
    check = yamaa.project(PROJECT).check()
    if check.status != "succeeded":
        raise ValueError(str(check.issues.to_pylist()))
    submission = yamaa.project(PROJECT).submission("adam", created=CREATED)
    if submission.status != "succeeded":
        raise ValueError(str(submission.issues.to_pylist()))
    submission.save()
    candidate = directory / "define.xml"

    # Use the authoritative, local schema bundle; never follow network imports.
    parser = etree.XMLParser(no_network=True, resolve_entities=False)
    xsd = schema_root / "define/2.1/define2-1-0.xsd"
    schema = etree.XMLSchema(etree.parse(str(xsd), parser))
    schema.assertValid(etree.parse(str(candidate), parser))
    comparison = compare(REFERENCE, candidate)
    data = audit_data(Document(candidate), directory)
    reference_data = audit_data(Document(REFERENCE), directory)
    return {
        "status": "succeeded" if comparison["metadata_equivalent"] and data["conformant"] else "incomplete",
        "yamaa_version": yamaa.__version__, "composition_succeeded": True,
        "xml_schema_valid": True, "candidate": candidate.relative_to(ROOT).as_posix(),
        "datasets": datasets, "comparison": comparison, "data_audit": data,
        "reference_data_audit": reference_data,
        "limits": [
            "The candidate is a metadata-only Define-XML 2.1 export, not a 2.0 reproduction.",
            "The unchanged Parquet artifacts are copied into the candidate package; no XPT transport is generated.",
            "The metadata layers pass check and composition; their run is not claimed to pass data verification.",
            "A schema-valid XML document can still disagree with the reference or its datasets.",
        ],
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--schemas", type=Path, required=True,
                        help="rust/tests/schemas directory from the pinned yamaa source checkout")
    args = parser.parse_args()
    DESTINATION.mkdir(parents=True, exist_ok=True)
    report_path = DESTINATION / "report.json"
    # Remove earlier success evidence and XML before attempting a fresh build.
    report_path.unlink(missing_ok=True)
    (DESTINATION / "data/define.xml").unlink(missing_ok=True)
    report = {"status": "failed", "composition_succeeded": False, "xml_schema_valid": False}
    try:
        report = generate(args.schemas.resolve())
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
