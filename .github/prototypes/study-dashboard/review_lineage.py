"""Conservative column dependencies and exact source spans for review navigation.

This is a static index of declared references, not a contributing-row trace.
Only names present in the declared schemas become edges. Literal strings are
excluded; joins, filters, keys and ordering are retained as context dependencies.
"""

import re

import yaml


TOKENS = re.compile(
    r"'(?:(?:'')|[^'])*'|\b[A-Za-z_][A-Za-z_0-9]*(?:\.[A-Za-z_][A-Za-z_0-9]*)?\b"
)


def strings(value):
    if isinstance(value, str):
        yield value
    elif isinstance(value, dict):
        for key, item in value.items():
            if key not in {"dict", "label", "type"}:
                yield from strings(item)
    elif isinstance(value, list):
        for item in value:
            yield from strings(item)


def spans(text):
    """Read positions from YAML nodes instead of guessing with text searches."""
    root = yaml.compose(text)
    sections = {}
    for key, value in root.value:
        if key.value in {"columns", "intermediates", "rows"}:
            for item in value.value:
                fields = {k.value: v for k, v in item.value}
                identifier = fields.get("name" if key.value == "columns" else "id")
                if identifier:
                    sections[identifier.value] = {
                        "start": item.start_mark.line + 1,
                        "end": item.end_mark.line,
                        "kind": key.value,
                    }
    return sections


def build_lineage(text, spec, input_columns):
    positions = spans(text)
    local = {c["name"] for c in spec.get("columns", [])}
    templates = spec.get("rows", [])
    local |= {name for row in templates for name in row.get("derivations", {})}
    intermediate = {i["id"]: i for i in spec.get("intermediates", [])}
    aliases = {name: set(columns) for name, columns in input_columns.items()}
    aliases["SELF"] = local | aliases.get(spec.get("base"), set())
    for identifier, item in intermediate.items():
        aliases[identifier] = aliases.get(item.get("dataset"), set()) | set(
            item.get("derivations", {})
        )
    base = spec.get("base")
    if base in aliases:
        aliases[base] |= local
    edges, unresolved = {}, set()

    def references(value, context=None):
        result = set()
        for expression in strings(value):
            for match in TOKENS.finditer(expression):
                token = match.group()
                if token.startswith("'"):
                    continue
                if "." in token:
                    alias, column = token.split(".", 1)
                    if alias in aliases and column in aliases[alias]:
                        result.add(
                            f"spec.{column}"
                            if alias == "SELF"
                            or (
                                alias == base
                                and column not in input_columns.get(alias, set())
                            )
                            else f"{alias}.{column}"
                        )
                    elif alias in aliases:
                        unresolved.add(token)
                elif context and token in input_columns.get(context, set()):
                    result.add(f"{context}.{token}")
                elif token in local:
                    # Function names and quoted literals cannot become edges.
                    if not expression[match.end() :].lstrip().startswith("("):
                        result.add(f"spec.{token}")
        return result

    for item in spec.get("intermediates", []):
        identifier, dataset = item["id"], item.get("dataset")
        context = {k: v for k, v in item.items() if k not in {"id", "dataset", "label"}}
        edges[f"intermediate.{identifier}"] = references(context, dataset)
        for column in aliases[identifier]:
            edges[f"{identifier}.{column}"] = {
                (
                    f"spec.{column}"
                    if dataset == "SELF" and column in local
                    else (
                        f'{spec.get("base")}.{column}'
                        if dataset == "SELF"
                        else f"{dataset}.{column}"
                    )
                ),
                f"intermediate.{identifier}",
            }
            if column in item.get("derivations", {}):
                edges[f"{identifier}.{column}"] |= references(
                    item["derivations"][column], dataset
                )
    for column in spec.get("columns", []):
        edges[f'spec.{column["name"]}'] = references(column.get("derivation"))
    for row in templates:
        node = f'row.{row["id"]}'
        edges[node] = references(row.get("filter"), row.get("dataset"))
        for name, expression in row.get("derivations", {}).items():
            edges.setdefault(f"spec.{name}", set()).update(
                references(expression, row.get("dataset")) | {node}
            )
    # Input grouping keys influence all expressions evaluated in that group.
    input_context = set()
    for alias, item in spec.get("input", {}).items():
        if not isinstance(item, dict):
            continue
        input_context |= references(
            {k: v for k, v in item.items() if k not in {"path", "schema"}}, alias
        )
    output_context = references(
        {
            k: v
            for k, v in spec.get("output", {}).items()
            if k not in {"path", "columns"}
        }
    )
    for name in spec["output"]["columns"]:
        edges[f"output.{name}"] = {f"spec.{name}"} | input_context | output_context
    return {
        "edges": {k: sorted(v - {k}) for k, v in edges.items()},
        "spans": positions,
        "unresolved": sorted(unresolved),
        "level": "static_column_dependencies",
        "note": "Declared value and context dependencies; contributing rows are not traced.",
    }
