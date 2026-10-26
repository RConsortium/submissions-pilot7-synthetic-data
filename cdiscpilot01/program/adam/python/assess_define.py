#!/usr/bin/env python3
"""Assess Define-XML generation without changing study data or reference XML."""

import argparse
from collections import Counter
from copy import deepcopy
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import xml.etree.ElementTree as ET

import yamaa
import yaml

ROOT = Path(__file__).resolve().parents[4]
STUDY = ROOT / "cdiscpilot01"
PROJECT = STUDY / "spec/yamaa/project.yaml"
REFERENCE = STUDY / "spec/define/define-adam.xml"
NS = {
    "odm": "http://www.cdisc.org/ns/odm/v1.2",
    "def": "http://www.cdisc.org/ns/def/v1.0",
    "arm": "http://www.cdisc.org/ns/ADaMRes/DRAFT",
}
CREATED = "2012-10-18T17:33:04"


def reference_inventory():
    """Count dataset variables separately from value-level ItemDef entries."""
    root = ET.parse(REFERENCE).getroot()
    metadata = root.find("odm:Study/odm:MetaDataVersion", NS)
    items = {item.attrib["OID"]: item for item in metadata.findall("odm:ItemDef", NS)}
    datasets = {}
    for group in metadata.findall("odm:ItemGroupDef", NS):
        datasets[group.attrib["Name"]] = [
            items[ref.attrib["ItemOID"]].attrib["Name"]
            for ref in group.findall("odm:ItemRef", NS)
        ]
    value_lists = metadata.findall("def:ValueListDef", NS)
    return {
        "odm_version": root.attrib["ODMVersion"],
        "define_version": metadata.attrib[f"{{{NS['def']}}}DefineVersion"],
        "datasets": datasets,
        "dataset_variables": sum(map(len, datasets.values())),
        "value_lists": len(value_lists),
        "value_level_references": sum(len(v.findall("odm:ItemRef", NS)) for v in value_lists),
        "item_definitions": len(items),
        "codelists": len(metadata.findall("odm:CodeList", NS)),
        "result_displays": len(metadata.findall("arm:AnalysisResultDisplays/arm:ResultDisplay", NS)),
        "analysis_results": len(metadata.findall(".//arm:AnalysisResults", NS)),
    }


def compose(path):
    """Capture the real engine result; never call save on a study target."""
    try:
        result = yamaa.project(path).submission("adam", created=CREATED)
        return {"status": result.status, "issues": result.issues.to_pylist()}
    except yamaa.Error as error:
        return {"status": "failed", "issues": error.issues.to_pylist(), "error": str(error)}


def assess():
    authored = yaml.safe_load(PROJECT.read_text())
    inventory = reference_inventory()
    specs = []
    for name in authored["adam"]["specs"]:
        spec = yaml.safe_load((PROJECT.parent / name).read_text())
        # This inventory reports authored blocks, not inferred provenance or
        # copied-column metadata. The engine makes the composition judgement.
        specs.append({
            "spec": name,
            "domain": spec["domain"],
            "output_columns": len(spec["output"]["columns"]),
            "reference_column_order_matches": (
                spec["output"]["columns"] == inventory["datasets"].get(spec["domain"])
            ),
            "dataset_submission_declared": "submission" in spec,
            "authored_column_submission_blocks": sum(
                "submission" in column for column in spec["columns"]
            ),
        })

    # A diagnostic project bypasses only the missing project fields to expose
    # the next failure. ADaMIG 1.0 is a probe declaration, not an approved
    # standard migration. No dataset/column metadata is invented or imported.
    probe = deepcopy(authored)
    variables = ET.parse(REFERENCE).find("odm:Study/odm:GlobalVariables", NS)
    probe["study"] = {
        key: variables.findtext(f"odm:{element}", namespaces=NS)
        for key, element in {
            "id": "StudyName", "name": "StudyName",
            "description": "StudyDescription", "protocol_name": "ProtocolName",
        }.items()
    }
    probe["adam"]["specs"] = [str((PROJECT.parent / name).resolve())
                              for name in authored["adam"]["specs"]]
    probe["adam"]["standards"] = [{"name": "ADaMIG", "version": "1.0", "status": "Final"}]
    # Define packages must contain their dataset artifacts. This target is
    # beside the derived Parquet files, and compose() never saves it.
    probe["adam"]["define"] = str(STUDY / "data/adam/define-yamaa.xml")
    baseline = compose(PROJECT)
    with TemporaryDirectory(prefix="pilot7-define-") as temporary:
        path = Path(temporary) / "project.yaml"
        path.write_text(yaml.safe_dump(probe, sort_keys=False))
        diagnostic = compose(path)

    return {
        "yamaa_version": yamaa.__version__,
        "project": PROJECT.relative_to(ROOT).as_posix(),
        "reference": REFERENCE.relative_to(ROOT).as_posix(),
        "created": CREATED,
        "reference_inventory": inventory,
        "specifications": specs,
        "unmodified_project": baseline,
        "project_metadata_probe": diagnostic,
        "probe_only_guide": probe["adam"]["standards"],
        "exact_reproduction": "not_demonstrated",
        "limits": [
            "A successful composition is not a comparison with the reference.",
            "yamaa emits Define-XML 2.1; the reference is Define-XML 1.0.",
            "The reference's draft analysis-results extension is outside the yamaa profile.",
            "No save, dataset derivation, XML schema validation, or semantic comparison is performed.",
        ],
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--report", type=Path,
                        default=ROOT / ".build/define/cdiscpilot01-assessment.json")
    args = parser.parse_args()
    report = assess()
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(report, indent=2) + "\n")
    for key in ("unmodified_project", "project_metadata_probe"):
        result = report[key]
        conditions = Counter(issue["condition"] for issue in result["issues"])
        print(f"{key}: {result['status']}; {dict(conditions)}")
    print(f"Exact reproduction: {report['exact_reproduction']}")
    print(f"Report: {args.report}")
    # This assesses composition readiness, not exact XML reproduction.
    return int(report["unmodified_project"]["status"] != "succeeded")


if __name__ == "__main__":
    raise SystemExit(main())
