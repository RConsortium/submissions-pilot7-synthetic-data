#!/usr/bin/env python3
"""Save and check portable, pinned-engine specification snapshots for each study."""

import argparse
from copy import deepcopy
import hashlib
import importlib.metadata
import json
from pathlib import Path
import subprocess
import tempfile
from urllib.parse import unquote, urlparse

import yaml

from study_evidence import engine_revision

ROOT = Path(__file__).resolve().parents[2]
FORMAT = "pilot7.resolved-specification"


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def snapshot_path(root, path):
    root, path = Path(root).resolve(), Path(path).resolve()
    parts = path.relative_to(root).parts
    if parts[1:3] != ("spec", "yamaa") or "resolved" in parts[3:]:
        raise ValueError(f"{path}: expected a study specification under spec/yamaa")
    return root.joinpath(*parts[:3], "resolved", *parts[3:])


def relocate(root, resolved, portable):
    """Relocate engine path fields only; leave expressions and written paths intact."""
    root = Path(root).resolve()
    result = deepcopy(resolved)

    def location(value):
        if portable:
            return Path(value).resolve().relative_to(root).as_posix()
        path = (root / value).resolve()
        path.relative_to(root)
        return str(path)

    result["entry"] = location(result["entry"])
    if result.get("project"):
        result["project"] = location(result["project"])
    for entry in result["entries"]:
        entry["entry"] = location(entry["entry"])
        entry["layers"] = [location(p) for p in entry["layers"]]
        for origin in entry["origins"].values():
            if origin.get("declaring_source") and origin["source_kind"] != "schema_default":
                origin["declaring_source"] = location(origin["declaring_source"])
        for resource in entry["resources"]:
            for key in ("declaring_source", "base_source", "owning_entry"):
                if resource.get(key):
                    resource[key] = location(resource[key])
            resource["location"]["path"] = location(resource["location"]["path"])
    return result


def assert_engine_pin(root, study):
    """A matching version number alone does not identify the reviewed engine."""
    expected = engine_revision(root, study)
    metadata = importlib.metadata.distribution("yamaa").read_text("direct_url.json")
    source = json.loads(metadata or "{}")
    actual = source.get("vcs_info", {}).get("commit_id")
    if actual is None and source.get("url", "").startswith("file:"):
        directory = Path(unquote(urlparse(source["url"]).path))
        actual = subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=directory, text=True).strip()
    if actual != expected:
        raise ValueError(f"{study}: install yamaa at the requirements pin {expected}")
    return expected


def snapshot(root, study, resolved, revision, version):
    portable = relocate(root, resolved, True)
    inputs = {portable["project"], f"{study}/program/adam/python/requirements.txt"}
    for entry in portable["entries"]:
        inputs.update([entry["entry"], *entry["layers"]])
        inputs.update(o["declaring_source"] for o in entry["origins"].values()
                      if o.get("declaring_source") and o["source_kind"] != "schema_default")
        inputs.update(r["location"]["path"] for r in entry["resources"]
                      if r["role"] not in {"input_data", "output_data", "report"})
    # Project-level codelists and functions are context for every selected spec.
    project = root / portable["project"]
    declaration = yaml.safe_load(project.read_text())
    for key in ("codelists", "functions"):
        inputs.update((project.parent / p).resolve().relative_to(root).as_posix()
                      for p in declaration.get(key, []))
    # A producer schema is a resource, not another resolved entry. Inventory
    # its inherited layers too, even when a copied field's origin is generated.
    pending, visited = list(inputs), set()
    while pending:
        relative = pending.pop()
        if relative in visited:
            continue
        visited.add(relative)
        source = root / relative
        if source.suffix not in {".yaml", ".yml"}:
            continue
        authored = yaml.safe_load(source.read_text())
        if not isinstance(authored, dict):
            continue
        for link in [authored.get("parent"), *(authored.get("include") or [])]:
            if isinstance(link, str):
                dependency = (source.parent / link).resolve().relative_to(root).as_posix()
                inputs.add(dependency)
                pending.append(dependency)
    return {
        "format": FORMAT, "artifact_version": 1,
        "yamaa_revision": revision, "yamaa_version": version,
        "inputs": {p: digest(root / p) for p in sorted(inputs)},
        "resolved": portable,
    }


def load_snapshot(root, path):
    """Read the canonical model without importing yamaa; reject changed inputs."""
    root, path = Path(root).resolve(), Path(path).resolve()
    target = snapshot_path(root, path)
    if not target.is_file():
        raise ValueError(f"{target}: missing resolved snapshot; run resolved_specs.py {path.relative_to(root).parts[0]}")
    inspection = target.with_suffix(".inspection.json")
    if not inspection.is_file():
        raise ValueError(f"{inspection}: missing resolved inspection record; regenerate snapshots")
    record = json.loads(inspection.read_text())
    if (record.get("format"), record.get("artifact_version")) != (FORMAT, 1):
        raise ValueError(f"{target}: unsupported resolved snapshot")
    study = path.relative_to(root).parts[0]
    if record["yamaa_revision"] != engine_revision(root, study):
        raise ValueError(f"{target}: resolved snapshot uses a different engine pin")
    for relative, expected in record["files"].items():
        generated = (root / relative).resolve()
        generated.relative_to(root)
        if not generated.is_file() or digest(generated) != expected:
            raise ValueError(f"{target}: composed specification or project changed: {relative}; regenerate snapshots")
    for relative, expected in record["inputs"].items():
        source = (root / relative).resolve()
        source.relative_to(root)
        if not source.is_file() or digest(source) != expected:
            raise ValueError(f"{target}: resolved snapshot input changed: {relative}; regenerate snapshots")
    resolved = record["resolved"]
    if (resolved.get("format"), resolved.get("artifact_version"), resolved.get("replay")) != (
        "yamaa.resolved-specification", 1, "inspection_only"
    ) or resolved.get("entry") != path.relative_to(root).as_posix():
        raise ValueError(f"{target}: unsupported or misnamed engine resolution")
    return relocate(root, resolved, False)


def specification_packet(root, path):
    from study_dashboard.specifications import capture_specification

    packet = capture_specification(root, path, load_snapshot(root, path))
    target = snapshot_path(root, path)
    # The executable YAML is the specification used by downstream readers.
    # The engine record contributes original-source locations and provenance.
    packet["model"] = yaml.safe_load(target.read_text())
    inspection = target.with_suffix(".inspection.json")
    packet["snapshot"] = {"path": target.relative_to(root).as_posix(), "sha256": digest(target),
                          "inspection_path": inspection.relative_to(root).as_posix(),
                          "inspection_sha256": digest(inspection)}
    return packet


def execution_project(root, study):
    return Path(root) / study / "spec/yamaa/resolved/project.yaml"


def process_study(root, study, check=False):
    """Resolve every declared section; never read clinical data or run project code."""
    import yamaa
    from composed_specs import admit, project as composed_project, specification, write_yaml

    root = Path(root).resolve()
    revision = assert_engine_pin(root, study)
    project_file = root / study / "spec/yamaa/project.yaml"
    declaration = yaml.safe_load(project_file.read_text())
    project = yamaa.project(project_file)
    records = {}
    for section in ("sdtm", "adam", "send"):
        for relative in declaration.get(section, {}).get("specs", []):
            path = (project_file.parent / relative).resolve()
            domain = yaml.safe_load(path.read_text())["domain"]
            record = snapshot(root, study, project.spec(domain).resolve(), revision, yamaa.__version__)
            records[path] = record
    directory = project_file.parent / "resolved"
    producers = {path: snapshot_path(root, path) for path in records}
    expected = {}
    # A sibling directory has the same relative paths to study data, codelists
    # and functions. Check every generated file before promoting any of them.
    with tempfile.TemporaryDirectory(prefix=".resolved-", dir=project_file.parent) as temporary:
        stage = Path(temporary)
        write_yaml(stage / "project.yaml", composed_project(
            declaration, project_file, execution_project(root, study)))
        for path, record in records.items():
            entry = next(e for e in record["resolved"]["entries"]
                         if e["entry"] == path.relative_to(root).as_posix())
            target = producers[path]
            write_yaml(stage / target.relative_to(directory), specification(root, entry, target, producers))
        admit(stage)
        project_hash = digest(stage / "project.yaml")
        for path, record in records.items():
            target = producers[path]
            relative = target.relative_to(directory)
            record["files"] = {target.relative_to(root).as_posix(): digest(stage / relative),
                               execution_project(root, study).relative_to(root).as_posix(): project_hash}
            inspection = stage / relative.with_suffix(".inspection.json")
            inspection.write_text(json.dumps(record, sort_keys=True, ensure_ascii=True, separators=(",", ":")) + "\n")
        expected = {directory / p.relative_to(stage): p.read_text()
                    for p in stage.rglob("*") if p.is_file()}
    existing = {p for p in directory.rglob("*") if p.is_file()} if directory.exists() else set()
    if check:
        changed = existing ^ set(expected)
        changed.update(p for p, text in expected.items() if p.is_file() and p.read_text() != text)
        if changed:
            names = ", ".join(p.relative_to(root).as_posix() for p in sorted(changed))
            raise ValueError(f"{study}: stale or missing resolved snapshots: {names}; run resolved_specs.py {study}")
    else:
        # Resolve the whole project successfully before replacing any snapshots.
        for target, text in expected.items():
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(text, encoding="ascii")
        for obsolete in existing - set(expected):
            obsolete.unlink()
    return len(records)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("studies", nargs="*")
    parser.add_argument("--check", action="store_true", help="Refuse drift without rewriting snapshots")
    args = parser.parse_args()
    studies = args.studies or sorted(p.parent.parent.parent.name for p in ROOT.glob("*/spec/yamaa/project.yaml"))
    for study in studies:
        count = process_study(ROOT, study, args.check)
        print(f"{study}: {'checked' if args.check else 'saved'} {count} resolved specifications", flush=True)


if __name__ == "__main__":
    main()
