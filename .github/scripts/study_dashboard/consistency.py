"""Metadata observations and authored review questions with source evidence."""

import json

import pyarrow.parquet as pq

from .config import SCHEMA_VERSION
from .documents import define_metadata, define_section_text, materials
from .rule_review import rule_findings, verification_summary
from .datasets import clean
from .issues import build_review
from .specifications import resource_path


def build_report(
    root, study, specifications, target, revision, validation=None, verification=None
):
    define_path = root / study / "spec/define/define-adam.xml"
    metadata = define_metadata(define_path) if define_path.exists() else {}
    manifest, documents = materials(root, study, target, metadata)
    define_doc = next(
        (d for d in documents if d["path"] == define_path.relative_to(root).as_posix()),
        {},
    )
    define_reading = define_doc.get("reading", "")
    define_original = define_doc.get("original", "")
    findings, checks = [], {"labels": 0, "output_columns": 0, "define_variables": 0}
    repo = "https://github.com/RConsortium/submissions-pilot7-synthetic-data"

    def add(
        domain,
        variable,
        kind,
        title,
        observation,
        source,
        spec_path,
        line,
        recommendation,
    ):
        findings.append(
            {
                "id": f'{study}:{domain}:{variable or "study"}:{kind}',
                "dataset": domain,
                "variable": variable,
                "kind": kind,
                "status": "Needs review",
                "title": title,
                "observation": observation,
                "source": source,
                "spec": {
                    "path": str(spec_path.relative_to(root)),
                    "line": line,
                    "url": f"{repo}/blob/{revision}/{spec_path.relative_to(root)}#L{line}",
                },
                "recommendation": recommendation,
            }
        )

    def defined_at(spec_path, lineage, name):
        """The file and lines writing a variable's rule: its layer, else the entry."""
        definition = lineage.get("definitions", {}).get(name)
        if definition:
            return root / definition["path"], definition
        return spec_path, lineage["spans"].get(name)

    for spec_path, spec, lineage in specifications:
        domain = spec["domain"]
        output_path = resource_path(root, spec_path, lineage.get("resources", {}), "output.path", spec["output"]["path"])
        output_columns = set(pq.read_schema(output_path).names)
        declared = {item["name"]: item for item in spec["columns"]}
        published = metadata.get(domain, {})
        if metadata and not published:
            # Missing name is a question; aliases must be verified by a reviewer.
            add(
                domain,
                "",
                "unclear",
                "Confirm dataset naming against Define-XML",
                f"The specification declares {domain}; no ItemGroupDef with that exact name was found. "
                f'Published names include {", ".join(metadata)}.',
                {
                    "path": str(define_path.relative_to(root)),
                    "section": "Dataset inventory",
                    "excerpt": ", ".join(metadata),
                    "url": define_original,
                },
                spec_path,
                1,
                "Verify the intended dataset alias in the published package and existing comparator.",
            )
        for name in spec["output"]["columns"]:
            checks["output_columns"] += 1
            defined, span = defined_at(spec_path, lineage, name)
            line = (span or {}).get("start", 1)
            if name not in output_columns:
                add(
                    domain,
                    name,
                    "inconsistent",
                    "Declared output column is absent",
                    f"{name} is declared in output.columns but is absent from the derived dataset.",
                    {
                        "path": str(output_path.relative_to(root)),
                        "section": "Dataset schema",
                        "excerpt": ", ".join(sorted(output_columns)),
                        "url": "",
                    },
                    defined,
                    line,
                    "Review the output selection and build evidence.",
                )
            if name not in published:
                continue
            checks["define_variables"] += 1
            item, column = published[name], declared.get(name, {})
            checks["labels"] += 1
            if column.get("label", "").strip() != item["label"].strip():
                add(
                    domain,
                    name,
                    "inconsistent",
                    "Variable label differs from published Define-XML",
                    f'YAML label: {column.get("label", "(missing)")}. '
                    f'Published label: {item["label"]}.',
                    {
                        "path": str(define_path.relative_to(root)),
                        "section": f'{domain}.{name} / {item["oid"]}',
                        "excerpt": define_section_text(item),
                        "url": f"{define_reading}#{domain}.{name}",
                    },
                    defined,
                    line,
                    "Check the original ItemDef and determine whether the difference is intended.",
                )
    if manifest.get("reference_data_alignment") == "not_revalidated":
        spec_path, spec, _ = specifications[0]
        notes = "\n".join(manifest.get("alignment_notes", []))
        add(
            spec["domain"],
            "",
            "unclear",
            "Confirm submission-document version alignment",
            "The retained source manifest records reference_data_alignment as not_revalidated.",
            {
                "path": f"{study}/spec/source/manifest.json",
                "section": "reference_data_alignment / alignment_notes",
                "excerpt": notes or "reference_data_alignment: not_revalidated",
                "url": f"{repo}/blob/{revision}/{study}/spec/source/manifest.json",
            },
            spec_path,
            1,
            "Verify which package version applies before interpreting narrative rules.",
        )
    append_questions(root, study, specifications, documents, findings, revision)
    logic_checks = []
    results = {d["domain"]: d for d in (validation or {}).get("datasets", [])}
    for spec_path, spec, lineage in specifications:
        domain = spec["domain"]
        output_path = resource_path(root, spec_path, lineage.get("resources", {}), "output.path", spec["output"]["path"])
        schema = pq.read_schema(output_path)
        result = results.get(domain)
        if result:
            logic_checks.append(
                {
                    "id": f"{study}:{domain}:execution",
                    "dataset": domain,
                    "variable": "",
                    "comparison": "input_output",
                    "kind": (
                        "executed" if result["build"] == "succeeded" else "inconsistent"
                    ),
                    "status": (
                        "Executed" if result["build"] == "succeeded" else "Needs review"
                    ),
                    "title": "Input -> output execution",
                    "observation": f'yamaa build: {result["build"]}. Independent reference comparison: {result["comparison"]}.',
                    "source": {
                        "path": "",
                        "section": "",
                        "excerpt": "Source-document interpretation is reviewed separately.",
                        "url": "",
                    },
                    "spec": {
                        "path": spec_path.relative_to(root).as_posix(),
                        "line": 1,
                        "url": f"{repo}/blob/{revision}/{spec_path.relative_to(root)}#L1",
                    },
                    "recommendation": "Inspect the linked inputs, rules and output records. Successful execution does not independently verify the intended derivation logic.",
                }
            )
        related = [f for f in findings + logic_checks if f["dataset"] == domain]
        for finding in related:
            name = finding["variable"]
            finding.setdefault(
                "comparison",
                (
                    "input_output"
                    if finding["source"]["path"]
                    == output_path.relative_to(root).as_posix()
                    else "source_documents"
                ),
            )
            defined, span = defined_at(spec_path, lineage, name)
            text = defined.read_text().splitlines()
            if span:
                relative = defined.relative_to(root).as_posix()
                finding["spec"].update(
                    path=relative, line=span["start"],
                    url=f"{repo}/blob/{revision}/{relative}#L{span['start']}",
                )
            finding["spec"]["excerpt"] = (
                "\n".join(text[span["start"] - 1 : span["end"]])
                if span
                else f'Inputs: {", ".join(spec["input"])} -> {domain}\nOutput columns: {", ".join(spec["output"]["columns"])}'
            )
            finding["spec"]["literal"] = bool(span)
            finding["spec"]["end_line"] = span["end"] if span else None
            summary = f"{pq.read_metadata(output_path).num_rows:,} rows; {len(schema)} columns."
            if name and name in schema.names:
                column = pq.read_table(output_path, columns=[name]).column(name)
                samples = []
                for value in column.to_pylist():
                    if (
                        value is not None
                        and (value := str(clean(value))) not in samples
                    ):
                        samples.append(value)
                    if len(samples) == 3:
                        break
                field = schema.field(name)
                label = (field.metadata or {}).get(b"yamaa:label", b"").decode("utf-8")
                summary = f'{name}: {field.type}; {len(column):,} rows; {column.null_count:,} missing. Label: {label or "(not stored)"}. Example values: {json.dumps(samples, ensure_ascii=True)}.'
            elif name:
                summary = f"{name} is absent from the dataset schema. " + summary
            finding["data"] = {
                "path": output_path.relative_to(root).as_posix(),
                "summary": summary,
            }
    # Documented-rule findings were decided in the validation job; they keep their own data.
    findings += rule_findings(study, verification, documents)
    reviewed = [d["dataset"] for d in (verification or {}).get("datasets", [])]
    narrative = "Not comprehensively reviewed; guide review tasks are explicitly marked Not reviewed."
    if reviewed:
        narrative = (
            f"Documented rules reviewed for {', '.join(reviewed)} by the consistency review "
            "workflow; other datasets have guide review tasks only."
        )
    return {
        "schema_version": SCHEMA_VERSION,
        "study": study,
        "revision": revision,
        "findings": findings,
        "logic_checks": logic_checks,
        "review": build_review(root, study, revision, findings + logic_checks),
        "checks": checks,
        "documents": [
            {k: v for k, v in d.items() if k != "sections"} for d in documents
        ],
        "coverage": {
            "metadata": "Output presence checked; Define-XML labels checked where published metadata is available.",
            "define_xml": "available" if metadata else "not_available",
            "narrative": narrative,
            "clinical_judgement": "Requires human review.",
        },
        "verification": verification_summary(study, verification, documents),
        "note": "Automated observations and pending review tasks are not confirmed clinical defects.",
    }


def append_questions(root, study, specifications, documents, findings, revision):
    """Resolve authored questions against retained sources; never invent an audit."""
    path = root / study / "spec/review/questions.json"
    if not path.exists():
        return
    declaration = json.loads(path.read_text())
    if declaration.get("schema_version") != SCHEMA_VERSION:
        raise ValueError(f"{path}: unsupported questions schema_version")
    specs = {item[1]["domain"]: item for item in specifications}
    ids = set()
    for question in declaration.get("questions", []):
        identifier = question["id"]
        if identifier in ids:
            raise ValueError(f"{path}: duplicate question id {identifier}")
        ids.add(identifier)
        domain, variable = question["dataset"], question.get("variable", "")
        if domain not in specs:
            raise ValueError(f"{path}: unknown dataset {domain}")
        spec_path, spec, lineage = specs[domain]
        if variable and variable not in {c["name"] for c in spec["columns"]}:
            raise ValueError(f"{path}: unknown variable {domain}.{variable}")
        document_path = (root / study / question["document"]).resolve()
        document_path.relative_to(root.resolve())
        document = next(
            (
                d
                for d in documents
                if d["path"] == document_path.relative_to(root).as_posix()
            ),
            None,
        )
        section = next(
            (
                s
                for s in (document or {}).get("sections", [])
                if s["id"] == question["section"]
            ),
            None,
        )
        normalize = lambda text: " ".join(text.split())
        excerpt = question["excerpt"]
        found = section is not None and normalize(excerpt) in normalize(section["text"])
        source = {
            "path": document_path.relative_to(root).as_posix(),
            "section": section["title"] if section else question["section"],
            "excerpt": excerpt,
            "url": (
                ((document or {}).get("reading", "") + "#" + question["section"])
                if found
                else ""
            ),
        }
        if document and document.get("original"):
            source["original"] = document["original"] + (
                "#page=" + section["id"].removeprefix("page-")
                if section and section["id"].startswith("page-")
                else ""
            )
        line = lineage["spans"].get(variable, {}).get("start", 1)
        findings.append(
            {
                "id": f"{study}:{identifier}",
                "dataset": domain,
                "variable": variable,
                "kind": "not_reviewed" if found else "missing_evidence",
                "status": "Not reviewed" if found else "Needs review",
                "title": question["title"],
                "observation": (
                    "Review the cited submission rule against the specification and actual records."
                    if found
                    else "The configured source location or excerpt is unavailable or has changed. Verify the source before reviewing this rule."
                ),
                "source": source,
                "spec": {
                    "path": spec_path.relative_to(root).as_posix(),
                    "line": line,
                    "url": f"https://github.com/RConsortium/submissions-pilot7-synthetic-data/blob/{revision}/{spec_path.relative_to(root)}#L{line}",
                },
                "recommendation": question["guidance"],
            }
        )
