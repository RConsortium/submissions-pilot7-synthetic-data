"""Conservative column dependencies and exact source spans for review navigation.

This is a static index of declared references, not a contributing-row trace.
Only names present in the declared schemas become edges. Literal strings are
excluded; joins, filters, keys and ordering are retained as context dependencies.
"""

import yaml

from .references import References


def source_locations(text):
    """Read positions from YAML nodes instead of guessing with text searches."""
    root = yaml.compose(text)
    sections, row_derivations = {}, {}

    def line_span(start, end):
        last = start.line + 1 + text[start.index : end.index].rstrip().count("\n")
        return {"start": start.line + 1, "end": max(last, end.line)}

    for key, value in root.value:
        if key.value in {"columns", "intermediates", "rows"}:
            for item in value.value:
                fields = {k.value: v for k, v in item.value}
                identifier = fields.get("name" if key.value == "columns" else "id")
                if identifier:
                    sections[identifier.value] = {
                        **line_span(item.start_mark, item.end_mark),
                        "kind": key.value,
                    }
                    derivations = fields.get("derivations")
                    if key.value == "rows" and isinstance(
                        derivations, yaml.MappingNode
                    ):
                        row_derivations[identifier.value] = {
                            name.value: line_span(name.start_mark, expression.end_mark)
                            for name, expression in derivations.value
                        }
    return {"spans": sections, "row_derivations": row_derivations}


def build_lineage(text, spec, input_columns):
    references = References(spec, input_columns)
    edges = {}
    for item in spec.get("intermediates", []):
        identifier, dataset = item["id"], item["dataset"]
        derived = item.get("derivations", {})
        bindings = {name: {f"{identifier}.{name}"} for name in derived}
        bindings.update(
            {f"{dataset}.{name}": {f"{identifier}.{name}"} for name in derived}
        )
        context = references.keys(item.get("key", []), dataset, bindings=bindings)
        for key in ("filter", "order_by", "group_by"):
            context |= references.read(
                item.get(key), donor=dataset, bindings=bindings, join=False
            )
        if item.get("between"):
            context |= references.bounds(item["between"], dataset, None, bindings)
        edges[f"intermediate.{identifier}"] = context
        for name in sorted(references.aliases[identifier] | set(derived)):
            source = (
                references.read(
                    derived[name],
                    donor=dataset,
                    bindings={
                        key: value
                        for key, value in bindings.items()
                        if key not in {name, f"{dataset}.{name}"}
                    },
                    join=False,
                )
                if name in derived
                else references.field(dataset, name)
            )
            edges[f"{identifier}.{name}"] = source | {f"intermediate.{identifier}"}
    templates = spec.get("rows", [])
    for row in templates:
        edges[f'row.{row["id"]}'] = references.read(
            {key: row[key] for key in ("filter", "group_by") if key in row},
            driver=row["dataset"],
            row=True,
        )
    declared = {
        column["name"]: column.get("derivation") for column in spec.get("columns", [])
    }
    root_filter = references.read(spec.get("filter"), driver=references.base)
    for name in sorted(references.local):
        dependencies = set(root_filter)
        if templates:
            for row in templates:
                expression = row.get("derivations", {}).get(name, declared.get(name))
                dependencies |= references.read(
                    expression,
                    driver=row["dataset"],
                    row=name in row.get("derivations", {}),
                ) | {f'row.{row["id"]}'}
        else:
            dependencies |= references.read(declared.get(name), driver=references.base)
        edges[f"spec.{name}"] = dependencies
    for name in spec["output"]["columns"]:
        edges[f"output.{name}"] = {f"spec.{name}"}
    return {
        "edges": {key: sorted(value - {key}) for key, value in edges.items()},
        **source_locations(text),
        "output_order": sorted(
            references.read(spec["output"].get("order_by"), driver=references.base)
        ),
        "unresolved": sorted(references.unresolved),
        "level": "static_column_dependencies",
        "note": "Declared value and relevant lookup/row context dependencies; final display ordering is separate and contributing rows are not traced.",
    }
