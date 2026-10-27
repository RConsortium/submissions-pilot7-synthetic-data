"""Build a versioned dashboard bundle from catalog entries and verified records."""

import json
from pathlib import Path

import yaml

from study_artifacts import verify_report_artifacts
from study_evidence import project_specs, validate_reports
from study_metrics import matched_totals, reference_totals

from .config import SCHEMA_VERSION, comments, reference_path, settings, study_path
from .datasets import export_table, write_json
from .lineage import build_lineage, source_locations
from .specifications import defining_sources, inspection_specification, resource_path
from .consistency import build_report
from .domains import domain_labels, domain_keys
from .synthetic import build_synthetic


def build_bundle(root, destination, entries, reports, revision, verifications=None):
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
            # Inspection packets live in each spec document, not in the small
            # catalog every review loads. Keep the full record in CI evidence.
            "validation": {
                **validation,
                "datasets": [
                    {key: value for key, value in dataset.items()
                     if key != "resolved_specification"}
                    for dataset in validation.get("datasets", [])
                ],
            },
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
        keys_sdtm = domain_keys(base / "spec/define/define-sdtm.xml")
        keys_adam = domain_keys(base / "spec/define/define-adam.xml")
        specifications = []
        results = {d["domain"]: d for d in validation["datasets"]}
        for domain, spec_path in project_specs(root, study):
            text = spec_path.read_text()
            spec, sources, resources = inspection_specification(
                root, spec_path, results[domain], validation["artifacts"]["files"]
            )
            inputs, schemas = [], {}
            for alias, item in spec["input"].items():
                relative = item["path"] if isinstance(item, dict) else item
                path = resource_path(root, spec_path, resources, f"input.{alias}.path", relative)
                identifier = table(
                    path, item.get("types") if isinstance(item, dict) else None
                )
                inputs.append({"alias": alias, "table": identifier})
                schemas[alias] = {c["name"] for c in exported[identifier]["columns"]}
            output = table(resource_path(root, spec_path, resources, "output.path", spec["output"]["path"]))
            labels = {c["name"]: c.get("label", "") for c in spec["columns"]}
            for column in exported[output]["columns"]:
                column["declared_label"] = labels.get(column["name"], "")
            exported[output]["domain"] = domain
            exported[output]["description"] = labels_adam.get(domain, "")
            exported[output]["keys"] = spec.get("keys", [])
            exported[output]["key_source"] = spec_path.relative_to(root).as_posix()
            reference = reference_path(root, study, domain, options)
            reference_id = table(reference) if reference.exists() else None
            if results[domain]["comparison"] == "passed" and reference_id is None:
                raise ValueError(
                    f"{study}/{domain}: passed comparison has no independent reference"
                )
            lineage = build_lineage(text, spec, schemas)
            lineage["resources"] = resources
            resolved_text = yaml.safe_dump(spec, sort_keys=False, allow_unicode=False)
            documents = [
                {**source, "lineage": {**lineage, **source_locations(source["text"])}}
                for source in sources
            ]
            # Review links open the layer that writes a variable's rule.
            spans = {d["path"]: d["lineage"]["spans"] for d in documents}
            packet = results[domain].get("resolved_specification")
            lineage["definitions"] = {
                name: {"path": path, **spans[path][name]}
                for name, path in (defining_sources(packet) if packet else {}).items()
                if name in spans.get(path, {})
            }
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
                    "documents": documents,
                    "resolved": {
                        "text": resolved_text,
                        "lineage": {**lineage, **source_locations(resolved_text)},
                    },
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
            sdtm = "/sdtm/" in metadata["path"]
            metadata.setdefault(
                "keys",
                (keys_sdtm if sdtm else keys_adam).get(metadata["domain"], []),
            )
            names = {column["name"] for column in metadata["columns"]}
            metadata["keys"] = [key for key in metadata["keys"] if key in names]
            if metadata["keys"]:
                metadata.setdefault(
                    "key_source",
                    f"{study}/spec/define/define-{'sdtm' if sdtm else 'adam'}.xml",
                )
        report = build_report(
            root,
            study,
            specifications,
            target,
            revision,
            validation,
            (verifications or {}).get(study),
        )
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
            findings=report["review"]["counts"]["issues"],
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
