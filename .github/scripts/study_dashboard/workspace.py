"""Shared specification, lineage, document and data workspace for every study."""

import json

import yaml

from study_evidence import project_specs
from study_metrics import matched_totals, reference_totals

from .config import SCHEMA_VERSION, reference_path, settings, study_path
from .datasets import export_table, write_json
from .lineage import build_lineage, source_locations
from .specifications import defining_sources, inspection_specification, resource_path
from .consistency import build_report
from .domains import domain_labels, domain_keys
from .define_comparison import export_comparison
from .documents import define_metadata, materials


def build_workspace(root, destination, study, entry, validation, revision, verification=None):
    """Export only caller-verified evidence into the caller's staging directory."""
    base = study_path(root, study)
    options = settings(root, entry)
    target = destination / study
    target.mkdir()
    record = {
        "schema_version": SCHEMA_VERSION,
        "id": study,
        "title": entry["title"],
        "description": entry["description"],
        "source": entry["source"],
        "revision": revision,
        "status": validation["status"],
        "kind": entry.get("category", "pilot"),
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
        return record
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

    define_paths = {}
    for section in ('sdtm', 'adam'):
        path = base / f'spec/define/define-{section}.xml'
        define_paths[section] = path if path.exists() else base / f'data/{section}/define.xml'
    labels_sdtm = domain_labels(define_paths['sdtm'])
    labels_adam = domain_labels(define_paths['adam'])
    keys_sdtm = domain_keys(define_paths['sdtm'])
    keys_adam = domain_keys(define_paths['adam'])
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
        packet = results[domain].get("resolved_specification")
        resolved_path = packet.get("snapshot", {}).get("path") if packet else None
        resolved_text = ((root / resolved_path).read_text() if resolved_path else
                         yaml.safe_dump(spec, sort_keys=False, allow_unicode=False))
        documents = [
            {**source, "lineage": {**lineage, **source_locations(source["text"])}}
            for source in sources
        ]
        # Review links open the layer that writes a variable's rule.
        spans = {d["path"]: d["lineage"]["spans"] for d in documents}
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
                    "path": resolved_path or spec_path.relative_to(root).as_posix(),
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
                define_paths['sdtm' if sdtm else 'adam'].relative_to(root).as_posix(),
            )
    report = build_report(
        root,
        study,
        specifications,
        target,
        revision,
        validation,
        verification,
        review_scope=options.get("review_scope", "full"),
        subject_key=options["subject_key"],
    )
    if options.get("review_scope") == "dataset_define":
        # The finding checker stays scoped; navigation retains the full package.
        focused_documents = {d["path"]: d for d in report["documents"]}
        define_path = define_paths["adam"]
        _, documents = materials(
            root, study, target,
            define_metadata(define_path) if define_path.is_file() else {},
        )
        documents = [
            focused_documents.get(d["path"],
                                  {k: v for k, v in d.items() if k != "sections"})
            for d in documents
        ]
        report["documents"] = documents
        write_json(target / "documents.json", documents)
    write_json(target / "report.json", report)
    if entry.get("category") != "synthetic":
        comparison = export_comparison(root, study, target, validation)
        if comparison is not None:
            record["define_comparison"] = comparison
    record.update(
        tables=exported,
        subjects=sorted(
            {s for item in exported.values() for s in item["subjects"]}
        ),
        metrics={
            "matched": matched_totals(validation),
            "reference": (0, 0, 0) if entry.get('category') == 'synthetic' else reference_totals(root, study),
        },
        findings=report["review"]["counts"]["issues"],
        report="report.json",
    )
    write_json(target / "catalog.json", record)
    return record
