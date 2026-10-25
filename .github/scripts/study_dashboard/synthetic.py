"""Source inventories for synthetic workflow development, separate from verification."""

import hashlib
import json
from pathlib import PurePosixPath
import tarfile

from .config import SCHEMA_VERSION, study_path


def synthetic_catalog(root):
    path = root / ".github/synthetic-studies.json"
    return json.loads(path.read_text()) if path.exists() else {}


def inventory(root, study, entry, revision):
    base = study_path(root, study).resolve()
    archives = []
    for relative in entry.get("archives", []):
        path = (base / relative).resolve()
        path.relative_to(base)
        record = {
            "path": path.relative_to(root).as_posix(),
            "available": path.is_file(),
        }
        if path.is_file():
            digest = hashlib.sha256()
            with path.open("rb") as source:
                for block in iter(lambda: source.read(1024 * 1024), b""):
                    digest.update(block)
            members = []
            # Inspect member headers; never extract the archive or load clinical XML.
            with tarfile.open(path, "r:gz") as archive:
                for member in archive:
                    name = PurePosixPath(member.name)
                    if not member.isfile() or any(
                        part.startswith(".") for part in name.parts
                    ):
                        continue
                    if name.is_absolute() or ".." in name.parts:
                        raise ValueError(
                            f"{path}: archive member is not a relative source path"
                        )
                    members.append({"name": member.name, "bytes": member.size})
            record.update(
                bytes=path.stat().st_size, sha256=digest.hexdigest(), files=members
            )
        archives.append(record)
    stages = [
        {
            "id": "odm",
            "title": "EDC / ODM sources",
            "count": sum(a["available"] for a in archives),
            "unit": "source archives",
        }
    ]
    for name, title, folder, patterns in [
        ("sdtm", "SDTM mapping", "data/sdtm", ("*.parquet", "*.xpt", "*.csv")),
        ("adam", "ADaM derivation", "data/adam", ("*.parquet", "*.xpt", "*.csv")),
        ("define", "Submission metadata", "spec/define", ("*.xml",)),
    ]:
        stages.append(
            {
                "id": name,
                "title": title,
                "count": len(
                    {
                        path
                        for pattern in patterns
                        for path in (base / folder).glob(pattern)
                        if path.is_file()
                    }
                ),
                "unit": "staged files",
            }
        )
    return {
        "schema_version": SCHEMA_VERSION,
        "id": study,
        "title": entry["title"],
        "description": entry["description"],
        "kind": "synthetic",
        "revision": revision,
        "archives": archives,
        "stages": stages,
    }


def build_synthetic(root, destination, revision):
    from .datasets import write_json

    records = []
    for study, entry in synthetic_catalog(root).items():
        record = inventory(root, study, entry, revision)
        write_json(destination / "synthetic" / study / "catalog.json", record)
        records.append(
            {
                "id": study,
                "title": entry["title"],
                "archives": sum(a["available"] for a in record["archives"]),
                "url": f"synthetic/{study}/catalog.json",
            }
        )
    write_json(
        destination / "synthetic/index.json",
        {"schema_version": SCHEMA_VERSION, "revision": revision, "studies": records},
    )
    return records
