"""Build complete, subject-chunked static review artifacts from real studies."""

from datetime import date, datetime
import csv
import importlib.util
import json
import math
from pathlib import Path
import shutil
import subprocess
import sys

import pyarrow.parquet as pq
import pyarrow as pa
import yaml

from review_lineage import build_lineage
from review_report import build_report

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / ".github/scripts"))
from study_evidence import catalog, project_specs, validate_reports  # noqa: E402
from build_index_table import _matched, _reference_totals  # noqa: E402


def clean(value):
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    if isinstance(value, float) and not math.isfinite(value):
        return "NaN" if math.isnan(value) else "Infinity" if value > 0 else "-Infinity"
    if isinstance(value, bytes):
        return value.decode("utf-8", errors="replace")
    return value


def write_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(
            value,
            ensure_ascii=True,
            allow_nan=False,
            separators=(",", ":"),
            default=str,
        )
        + "\n"
    )


def read_table(path, types=None):
    if path.suffix.lower() != ".csv":
        return pq.read_table(path)
    with path.open(newline="") as source:
        rows = list(csv.DictReader(source))
    types = types or {}
    for row in rows:
        for name, kind in types.items():
            if row.get(name) in {None, ""}:
                row[name] = None
            else:
                row[name] = (
                    int(row[name])
                    if kind == "int"
                    else float(row[name]) if kind == "float" else row[name]
                )
    return pa.Table.from_pylist(rows)


def export_table(path, target, identifier, types=None):
    table = read_table(path, types)
    columns = table.column_names
    rows = [[clean(v) for v in row.values()] for row in table.to_pylist()]
    subject_index = columns.index("USUBJID") if "USUBJID" in columns else None
    subjects = sorted(
        {
            str(row[subject_index])
            for row in rows
            if subject_index is not None and row[subject_index] is not None
        }
    )
    # A single subject is a natural retrieval unit; groups limit request count.
    groups = [subjects[i : i + 12] for i in range(0, len(subjects), 12)] or [[]]
    lookup = {s: i for i, group in enumerate(groups) for s in group}
    chunks = [[] for _ in groups]
    for index, row in enumerate(rows):
        subject = str(row[subject_index]) if subject_index is not None else None
        chunks[lookup.get(subject, 0)].append([index, *row])
    chunk_info = []
    for index, chunk in enumerate(chunks):
        relative = f"tables/{identifier}/{index}.json"
        write_json(target / relative, chunk)
        chunk_info.append(
            {"url": relative, "subjects": groups[index], "rows": len(chunk)}
        )
    download = f"downloads/{identifier}{path.suffix}"
    (target / "downloads").mkdir(exist_ok=True)
    if path.stat().st_size > 20 * 1024 * 1024 and "-yamaa" in path.name:
        # Compress a downloadable copy; preserve source and reference files.
        pq.write_table(table, target / download, compression="zstd")
    else:
        shutil.copyfile(path, target / download)
    fields = []
    for field in table.schema:
        metadata = field.metadata or {}
        label = metadata.get(b"yamaa:label") or metadata.get(b"label") or b""
        fields.append(
            {
                "name": field.name,
                "type": str(field.type),
                "label": label.decode("utf-8", errors="replace"),
            }
        )
    return {
        "id": identifier,
        "name": path.stem.upper(),
        "path": path.relative_to(ROOT).as_posix(),
        "rows": table.num_rows,
        "columns": fields,
        "subjects": subjects,
        "chunks": chunk_info,
        "subject_index": subject_index,
        "download": download,
        "format": path.suffix.removeprefix(".").upper(),
    }


def reference_name(root, study, spec_path):
    """Use the existing comparator's authored aliases, not a guessed name."""
    module_path = root / study / "program/adam/python/compare.py"
    module_spec = importlib.util.spec_from_file_location(
        "review_comparator", module_path
    )
    module = importlib.util.module_from_spec(module_spec)
    module_spec.loader.exec_module(module)
    return getattr(module, "EXPECTED_NAMES", {}).get(spec_path.stem, spec_path.stem)


def build_review(destination, reports_dir):
    entries = catalog(ROOT)
    reports = {
        name: json.loads((reports_dir / f"{name}.json").read_text()) for name in entries
    }
    validate_reports(ROOT, entries, reports)
    revision = subprocess.check_output(
        ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True
    ).strip()
    if any(report.get("repository_commit") != revision for report in reports.values()):
        raise ValueError(
            "Review data requires reports from the current checkout revision."
        )
    if destination.exists():
        shutil.rmtree(destination)
    destination.mkdir(parents=True, exist_ok=True)
    index = {
        "revision": revision,
        "studies": [],
        "comments": json.loads((Path(__file__).parent / "comments.json").read_text()),
    }
    for study, entry in entries.items():
        target = destination / study
        target.mkdir(exist_ok=True)
        table_cache = {}

        def table(path, types=None):
            path = path.resolve()
            if path not in table_cache:
                identifier = f"t{len(table_cache):03d}"
                table_cache[path] = export_table(path, target, identifier, types)
            return table_cache[path]["id"]

        domains, specifications = [], []
        for domain, spec_path in project_specs(ROOT, study):
            text = spec_path.read_text()
            spec = yaml.safe_load(text)
            sources, schemas = [], {}
            for alias, item in spec["input"].items():
                path = (
                    spec_path.parent
                    / (item["path"] if isinstance(item, dict) else item)
                ).resolve()
                types = item.get("types") if isinstance(item, dict) else None
                sources.append({"alias": alias, "table": table(path, types)})
                schemas[alias] = set(read_table(path, types).column_names)
            output = (spec_path.parent / spec["output"]["path"]).resolve()
            reference = (
                ROOT
                / study
                / "data/adam"
                / f"{reference_name(ROOT, study, spec_path)}.parquet"
            )
            output_id, reference_id = table(output), table(reference)
            lineage = build_lineage(text, spec, schemas)
            relative = f"specs/{domain.lower()}.json"
            spec_record = {
                "domain": domain,
                "text": text,
                "path": spec_path.relative_to(ROOT).as_posix(),
                "columns": spec["columns"],
                "keys": spec.get("keys", []),
                "lineage": lineage,
            }
            write_json(target / relative, spec_record)
            domains.append(
                {
                    "name": domain,
                    "spec": relative,
                    "inputs": sources,
                    "output": output_id,
                    "reference": reference_id,
                    "keys": spec.get("keys", []),
                }
            )
            specifications.append((spec_path, spec, lineage))
        # All staged SDTM files can be explored, including unused inputs.
        for path in sorted((ROOT / study / "data/sdtm").glob("*.parquet")):
            table(path)
        tables = {item["id"]: item for item in table_cache.values()}
        subjects = sorted({s for item in tables.values() for s in item["subjects"]})
        report = build_report(ROOT, study, specifications, target, revision)
        write_json(target / "report.json", report)
        record = {
            "id": study,
            "title": entry["title"],
            "source": entry["source"],
            "revision": revision,
            "validation": reports[study],
            "metrics": {
                "matched": _matched(reports[study]),
                "reference": _reference_totals(ROOT, study),
            },
            "subjects": subjects,
            "datasets": domains,
            "tables": tables,
            "findings": len(report["findings"]),
            "report": "report.json",
        }
        write_json(target / "catalog.json", record)
        index["studies"].append(
            {
                "id": study,
                "title": entry["title"],
                "subjects": len(subjects),
                "datasets": len(domains),
                "findings": len(report["findings"]),
            }
        )
    write_json(destination / "index.json", index)
    return index
