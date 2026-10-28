"""Render the engine-composed model as authoring YAML and admit it with yamaa."""

from copy import deepcopy
import json
import os
from pathlib import Path
import re

import yaml


def element(document, path):
    """Locate an engine specification path, including named list members."""
    value, parent, key = document, None, None
    for token in re.findall(r"[^.\[\]]+", path):
        parent = value
        if isinstance(parent, list):
            key = int(token) if token.isdigit() else next(
                i for i, item in enumerate(parent)
                if isinstance(item, dict) and item.get("name", item.get("id")) == token)
        else:
            key = token
        value = parent[key]
    return parent, key, value


def ordered_model(entry):
    def ordered(value, pointer=""):
        if isinstance(value, dict):
            return {key: ordered(value[key], pointer + "/" + key.replace("~", "~0").replace("/", "~1"))
                    for key in entry["mapping_order"].get(pointer, list(value))}
        if isinstance(value, list):
            return [ordered(item, f"{pointer}/{i}") for i, item in enumerate(value)]
        return value
    return ordered(entry["specification"])


def specification(root, entry, target, producers):
    """Keep the engine's composition; relocate its declared resource fields."""
    model = ordered_model(entry)
    for resource in entry["resources"]:
        if resource["role"] in {"parent_specification", "included_specification"}:
            continue
        destination = (root / resource["location"]["path"]).resolve()
        if resource["role"] == "producer_schema":
            destination = producers.get(destination, destination)
        parent, key, _ = element(model, resource["spec_path"])
        parent[key] = Path(os.path.relpath(destination, target.parent)).as_posix()
    return model


def project(declaration, source, target):
    result = deepcopy(declaration)
    for field in ("codelists", "functions"):
        if field in result:
            result[field] = [Path(os.path.relpath((source.parent / p).resolve(), target.parent)).as_posix()
                             for p in result[field]]
    for section in ("sdtm", "adam", "send"):
        if "define" in result.get(section, {}):
            result[section]["define"] = Path(os.path.relpath(
                (source.parent / result[section]["define"]).resolve(), target.parent)).as_posix()
    if result.get("environments"):
        raise ValueError("Composed project export does not yet support project environments")
    return result


def write_yaml(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(value, sort_keys=False, allow_unicode=False), encoding="ascii")


def admit(directory):
    """Use engine diagnostics to restore mandatory shorthand, then require success.

    resolve() expands shorthand into normalized classes. SCHEMA-15 refuses
    writing a class whose only field restates its shorthand. Collapse only the
    exact single-field class the engine identifies, preserving its typed value.
    No inheritance, derivation rule or expression is interpreted here.
    """
    import yamaa

    while True:
        checked = yamaa.project(directory / "project.yaml").check()
        if checked.status == "succeeded":
            return
        issues = checked.issues.to_pylist()
        documents, changed, seen = {}, False, set()
        for issue in sorted(issues, key=lambda i: len(i["spec_paths"][0]) if i["spec_paths"] else 0, reverse=True):
            if issue["condition"] != "redundant_long_form":
                continue
            path = Path(issue["file"]).resolve()
            path.relative_to(directory.resolve())
            address = issue["spec_paths"][0]
            if (path, address) in seen:
                continue
            seen.add((path, address))
            if path not in documents:
                documents[path] = yaml.safe_load(path.read_text())
            parent, key, value = element(documents[path], address)
            field = json.loads(issue["context"])["field"]
            if isinstance(value, dict) and set(value) == {field}:
                parent[key] = value[field]
                changed = True
        if not changed:
            raise ValueError(f"Composed project does not pass yamaa check: {issues}")
        for path, document in documents.items():
            write_yaml(path, document)
