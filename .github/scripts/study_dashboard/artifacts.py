"""Build a versioned dashboard bundle from catalog entries and verified records."""

from pathlib import Path

from study_artifacts import verify_report_artifacts
from study_evidence import validate_reports

from .config import SCHEMA_VERSION, comments
from .datasets import write_json
from .synthetic import build_synthetic
from .workspace import build_workspace


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
        record = build_workspace(root, destination, study, entry, reports[study], revision,
                                 (verifications or {}).get(study))
        index["studies"].append({
            "id": study, "title": entry["title"], "status": record["status"],
            "subjects": len(record["subjects"]) if record["status"] != "pending" else None,
            "datasets": len(record["datasets"]) if record["status"] != "pending" else None,
            "findings": record.get("findings"), "kind": record["kind"],
        })
    # A concurrent source/output change must never promote partial or mixed evidence.
    verify_report_artifacts(root, entries, reports)
    index["synthetic_studies"] = build_synthetic(root, destination, revision)
    write_json(destination / "index.json", index)
    return index
