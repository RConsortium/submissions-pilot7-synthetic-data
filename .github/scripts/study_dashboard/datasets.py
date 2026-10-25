"""Dataset adapters and complete subject-chunked static serialization."""

from datetime import date, datetime
import csv
import gzip
import json
import math
import shutil

import pyarrow as pa
import pyarrow.parquet as pq


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
    text = (
        json.dumps(
            value,
            ensure_ascii=True,
            allow_nan=False,
            separators=(",", ":"),
            default=str,
        )
        + "\n"
    )
    if path.suffix == ".gz":
        path.write_bytes(gzip.compress(text.encode("utf-8"), compresslevel=9, mtime=0))
    else:
        path.write_text(text)


def read_table(path, types=None):
    if path.suffix.lower() == ".parquet":
        return pq.read_table(path)
    if path.suffix.lower() != ".csv":
        raise ValueError(f"Unsupported dashboard dataset format: {path.suffix}")
    with path.open(newline="", encoding="utf-8-sig") as source:
        reader = csv.DictReader(source)
        rows, names = list(reader), reader.fieldnames or []
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
    if rows:
        return pa.Table.from_pylist(rows)
    schema = {"int": pa.int64(), "float": pa.float64()}
    return pa.table(
        {
            name: pa.array([], type=schema.get(types.get(name), pa.string()))
            for name in names
        }
    )


def export_table(path, target, identifier, types=None, *, root, subject_key="USUBJID"):
    table = read_table(path, types)
    columns = table.column_names
    rows = [[clean(v) for v in row.values()] for row in table.to_pylist()]
    subject_index = columns.index(subject_key) if subject_key in columns else None
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
        relative = f"tables/{identifier}/{index}.json.gz"
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
        "path": path.relative_to(root).as_posix(),
        "rows": table.num_rows,
        "columns": fields,
        "subjects": subjects,
        "chunks": chunk_info,
        "subject_index": subject_index,
        "download": download,
        "format": path.suffix.removeprefix(".").upper(),
    }
