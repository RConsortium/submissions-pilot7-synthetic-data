"""Carry engine-resolved inspection facts from validation into static publication."""

from copy import deepcopy
from pathlib import Path

import yaml


def capture_specification(root, path, resolved):
    """Keep portable facts from resolve(), without resolving the language again.

    The validation worker has the study's pinned engine. The publication worker
    reads its recorded model and exact source texts without importing yamaa.
    """
    root, path = Path(root).resolve(), Path(path).resolve()
    if (resolved.get("format"), resolved.get("artifact_version")) != (
        "yamaa.resolved-specification", 1
    ) or resolved.get("replay") != "inspection_only":
        raise ValueError("Unsupported engine resolved-specification artifact")
    entry = next(e for e in resolved["entries"] if e["entry"] == str(path))

    def relative(value):
        return Path(value).resolve().relative_to(root).as_posix()

    def ordered(value, pointer=""):
        if isinstance(value, dict):
            keys = entry["mapping_order"].get(pointer, list(value))
            return {k: ordered(value[k], pointer + "/" + k.replace("~", "~0").replace("/", "~1"))
                    for k in keys}
        if isinstance(value, list):
            return [ordered(v, f"{pointer}/{i}") for i, v in enumerate(value)]
        return value

    sources = [str(path)]
    for item in resolved["entries"]:
        sources.extend(item["layers"])
        sources.extend(o["declaring_source"] for o in item["origins"].values()
                       if o.get("declaring_source") and o["source_kind"] != "schema_default")
        sources.extend(r["location"]["path"] for r in item["resources"]
                       if r["role"] in {"producer_schema", "parent_specification",
                                        "included_specification", "mapping_dictionary"})
    return {
        "schema_version": 1,
        "model": ordered(entry["specification"]),
        "sources": [{"path": relative(p), "text": Path(p).read_text()}
                    for p in dict.fromkeys(sources)],
        "resources": {r["spec_path"]: relative(r["location"]["path"])
                      for r in entry["resources"]},
        "origins": {pointer: {**origin, "declaring_source":
                              relative(origin["declaring_source"])
                              if origin.get("declaring_source") and origin["source_kind"] != "schema_default"
                              else origin.get("declaring_source")}
                    for pointer, origin in entry["origins"].items()},
    }


def inspection_specification(root, path, record, inventory):
    """Refuse stale or uninventoried sources before using recorded engine facts."""
    packet = record.get("resolved_specification")
    if packet and packet.get("snapshot"):
        from resolved_specs import specification_packet

        current = specification_packet(root, path)
        relative = current["snapshot"]["path"]
        if relative not in inventory or packet != current:
            raise ValueError(f"{path}: resolved snapshot changed after validation")
        packet = current
    if packet is None:
        # Older standalone evidence remains readable. Reusable declarations need
        # fresh engine facts; never approximate inheritance or copy expansion.
        authored = yaml.safe_load(path.read_text())
        if authored.get("parent") or authored.get("include") or authored.get("windows") or any(
            "copy" in c for c in authored.get("columns", [])
        ):
            raise ValueError(f"{path}: rerun validation to record the resolved specification")
        return authored, [{"path": path.relative_to(root).as_posix(), "text": path.read_text()}], {}
    if packet.get("schema_version") != 1:
        raise ValueError(f"{path}: unsupported resolved specification schema_version")
    for source in packet["sources"]:
        location = (root / source["path"]).resolve()
        location.relative_to(root.resolve())
        if source["path"] not in inventory or location.read_text() != source["text"]:
            raise ValueError(f"{path}: resolved specification source changed: {source['path']}")
    for key, relative in packet["resources"].items():
        (root / relative).resolve().relative_to(root.resolve())
        if (key == "output.path" or key.startswith("input.") and key.endswith(".path")) and relative not in inventory:
            raise ValueError(f"{path}: resolved dataset resource is not inventoried: {relative}")
    model = deepcopy(packet["model"])
    if model.get("domain") != record["domain"]:
        raise ValueError(f"{path}: resolved specification has the wrong domain")
    return model, packet["sources"], packet["resources"]


def resource_path(root, path, resources, key, written):
    """Use the engine's location, retaining standalone legacy evidence support."""
    return (root / resources[key]).resolve() if key in resources else (path.parent / written).resolve()


def leaf_writers(packet):
    """The source file that wrote each authored leaf of the composed model.

    When two layers both write a mapping, such as a `submission` class or a
    `case` rule, the ledger keeps the mapping's first writer while the later
    layer writes what is inside it. Only the leaves name the files kept.
    """
    origins = packet.get("origins", {})
    parents = {pointer.rpartition("/")[0] for pointer in origins}
    return {
        pointer: origin["declaring_source"]
        for pointer, origin in origins.items()
        if pointer not in parents and origin.get("declaring_source")
        and origin.get("source_kind") != "schema_default" and not origin.get("generated")
    }


def defining_sources(packet):
    """Name the source file that writes each column's value rule.

    A layered specification spreads one column over several files: the study
    layer derives it, a package layer may override the rule or the label, and
    the entry adds Define-XML metadata. The engine's origin ledger records
    which file wrote each value, so review links follow the rule, not the name.
    A column without a rule of its own, intermediates and row templates are
    located where they are declared.
    """
    origins, model, found = packet.get("origins", {}), packet["model"], {}
    leaves = leaf_writers(packet)
    for key in ("columns", "intermediates", "rows"):
        for index, item in enumerate(model.get(key, [])):
            rule = f"/{key}/{index}/derivation"
            writers = [s for p, s in leaves.items() if key == "columns" and (p == rule or p.startswith(rule + "/"))]
            origin = origins.get(f"/{key}/{index}", {})
            if not writers and origin.get("declaring_source") and origin.get("source_kind") != "schema_default":
                writers = [origin["declaring_source"]]
            if writers:
                found.setdefault(item.get("name") or item.get("id"), writers[0])
    return found


def element_leaves(packet):
    """The source file that wrote each leaf of every column, intermediate and row template.

    Pointers are relative to the element and follow the authored YAML: the
    engine wraps a column's or row template's rule in `value`, which no layer
    writes, so `derivation/impute/day` names the leaf that
    `derivation: {impute: {day: 15}}` writes.
    """
    leaves, found = leaf_writers(packet), {}
    for key, label in (("columns", "name"), ("intermediates", "id"), ("rows", "id")):
        for index, item in enumerate(packet["model"].get(key, [])):
            prefix, written = f"/{key}/{index}/", {}
            for pointer, source in leaves.items():
                if not pointer.startswith(prefix):
                    continue
                parts = pointer[len(prefix):].split("/")
                rule = {"derivation": 1, "derivations": 2}.get(parts[0])
                if rule is not None and parts[rule:rule + 1] == ["value"]:
                    del parts[rule]
                written["/".join(parts)] = source
            found[item[label]] = written
    return found


def field_sources(packet):
    """Name the source files that write each field a column, intermediate or row template keeps.

    A field written in several layers keeps the last one, so text an earlier
    layer wrote for that field is no longer the element's. Each derivation of
    a row template is a field of its own, `derivations/<variable>`, because a
    layer may override one variable's rule in a template another layer declares.
    """
    found = {}
    for element, written in element_leaves(packet).items():
        fields = found[element] = {}
        for pointer, source in written.items():
            parts = pointer.split("/")
            if parts[0] in ("name", "id"):
                continue
            field = "/".join(parts[:2]) if parts[0] == "derivations" and len(parts) > 1 else parts[0]
            fields.setdefault(field, set()).add(source)
    return found
