"""Build a versioned dashboard bundle from catalog entries and verified records."""

import json
from pathlib import Path

import yaml

from study_artifacts import verify_report_artifacts
from study_evidence import project_specs, validate_reports
from study_metrics import matched_totals, reference_totals

from .config import SCHEMA_VERSION, comments, reference_path, settings, study_path
from .datasets import export_table, write_json
from .lineage import build_lineage
from .consistency import build_report
from .domains import domain_labels
from .synthetic import build_synthetic


def build_bundle(root, destination, entries, reports, revision):
    """Write only into a caller-owned staging directory; publication owns promotion."""
    root, destination = Path(root), Path(destination)
    validate_reports(root, entries, reports, revision)
    verify_report_artifacts(root, entries, reports)
    destination.mkdir(parents=True, exist_ok=True)
    index = {
        "schema_version": SCHEMA_VERSION,
        "revision": revision,
        "studies": [],
        "comments": comments(root),
    }
    for study, entry in entries.items():
        base = study_path(root, study)
        options = settings(root, entry)
        target = destination / study
        target.mkdir()
        validation = reports[study]
        record = {
            "schema_version": SCHEMA_VERSION,
            "id": study,
            "title": entry["title"],
            "description": entry["description"],
            "source": entry["source"],
            "revision": revision,
            "status": validation["status"],
            "validation": validation,
            "settings": options,
            "subjects": [],
            "datasets": [],
            "tables": {},
        }
        if validation["status"] == "pending":
            record["reason"] = validation.get("reason", "Study validation has not run.")
            write_json(target / "catalog.json", record)
            index["studies"].append(
                {
                    "id": study,
                    "title": entry["title"],
                    "status": "pending",
                    "subjects": None,
                    "datasets": None,
                    "findings": None,
                }
            )
            continue
        exported, cache = {}, {}

        def table(path, types=None):
            path = path.resolve()
            key = (path, json.dumps(types or {}, sort_keys=True))
            if key not in cache:
                identifier = f"t{len(cache):03d}"
                exported[identifier] = export_table(
                    path,
                    target,
                    identifier,
                    types,
                    root=root,
                    subject_key=options["subject_key"],
                )
                exported[identifier]["sha256"] = validation["artifacts"]["files"][
                    path.relative_to(root).as_posix()
                ]
                cache[key] = identifier
            return cache[key]

        labels_sdtm = domain_labels(base / "spec/define/define-sdtm.xml")
        labels_adam = domain_labels(base / "spec/define/define-adam.xml")
        specifications = []
        results = {d["domain"]: d for d in validation["datasets"]}
        for domain, spec_path in project_specs(root, study):
            text = spec_path.read_text()
            spec = yaml.safe_load(text)
            inputs, schemas = [], {}
            for alias, item in spec["input"].items():
                relative = item["path"] if isinstance(item, dict) else item
                path = (spec_path.parent / relative).resolve()
                identifier = table(
                    path, item.get("types") if isinstance(item, dict) else None
                )
                inputs.append({"alias": alias, "table": identifier})
                schemas[alias] = {c["name"] for c in exported[identifier]["columns"]}
            output = table((spec_path.parent / spec["output"]["path"]).resolve())
            labels = {c["name"]: c.get("label", "") for c in spec["columns"]}
            for column in exported[output]["columns"]:
                column["declared_label"] = labels.get(column["name"], "")
            exported[output]["domain"] = domain
            exported[output]["description"] = labels_adam.get(domain, "")
            reference = reference_path(root, study, domain, options)
            reference_id = table(reference) if reference.exists() else None
            if results[domain]["comparison"] == "passed" and reference_id is None:
                raise ValueError(
                    f"{study}/{domain}: passed comparison has no independent reference"
                )
            lineage = build_lineage(text, spec, schemas)
            relative = f"specs/{domain.lower()}.json"
            write_json(
                target / relative,
                {
                    "schema_version": SCHEMA_VERSION,
                    "domain": domain,
                    "text": text,
                    "path": spec_path.relative_to(root).as_posix(),
                    "columns": spec["columns"],
                    "keys": spec.get("keys", []),
                    "lineage": lineage,
                },
            )
            record["datasets"].append(
                {
                    "name": domain,
                    "spec": relative,
                    "inputs": inputs,
                    "output": output,
                    "reference": reference_id,
                    "keys": spec.get("keys", []),
                    "build": results[domain]["build"],
                    "comparison": results[domain]["comparison"],
                }
            )
            specifications.append((spec_path, spec, lineage))
        for path in sorted((base / "data/sdtm").glob("*.parquet")):
            table(path)
        for metadata in exported.values():
            metadata.setdefault("domain", metadata["name"].removesuffix("-YAMAA"))
            metadata.setdefault(
                "description",
                (labels_sdtm if "/sdtm/" in metadata["path"] else labels_adam).get(
                    metadata["domain"], ""
                ),
            )
        report = build_report(root, study, specifications, target, revision)
        write_json(target / "report.json", report)
        record.update(
            tables=exported,
            subjects=sorted(
                {s for item in exported.values() for s in item["subjects"]}
            ),
            metrics={
                "matched": matched_totals(validation),
                "reference": reference_totals(root, study),
            },
            findings=len(report["findings"]),
            report="report.json",
        )
        write_json(target / "catalog.json", record)
        index["studies"].append(
            {
                "id": study,
                "title": entry["title"],
                "status": record["status"],
                "subjects": len(record["subjects"]),
                "datasets": len(record["datasets"]),
                "findings": record["findings"],
            }
        )
    # A concurrent source/output change must never promote partial or mixed evidence.
    verify_report_artifacts(root, entries, reports)
    index["synthetic_studies"] = build_synthetic(root, destination, revision)
    write_json(destination / "index.json", index)
    return index
