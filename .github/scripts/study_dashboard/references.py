"""Resolve declared expression references and the keys of lookups actually read."""

import re

TOKENS = re.compile(
    r"'(?:(?:'')|[^'])*'|\b[A-Za-z_][A-Za-z_0-9]*(?:\.[A-Za-z_][A-Za-z_0-9]*)?\b"
)
LITERALS = {
    "dict",
    "label",
    "type",
    "nulls",
    "keep",
    "pattern",
    "format",
    "unit",
    "closed",
    "side",
    "separator",
    "method",
    "ties",
    "missing",
    "unmapped",
    "true_value",
    "false_value",
    "unconvertible",
    "invalid",
    "absent",
}


class References:
    def __init__(self, spec, schemas):
        self.spec, self.schemas = spec, schemas
        self.local = {c["name"] for c in spec.get("columns", [])}
        self.local |= {
            name for row in spec.get("rows", []) for name in row.get("derivations", {})
        }
        self.base = spec.get("base") or (
            next(iter(schemas)) if len(schemas) == 1 else None
        )
        self.aliases = {name: set(columns) for name, columns in schemas.items()}
        self.ordinals = {
            (alias, declaration['ordinal'])
            for alias, declaration in spec.get('input', {}).items()
            if isinstance(declaration, dict) and declaration.get('ordinal')
        }
        for alias, ordinal in self.ordinals:
            self.aliases.setdefault(alias, set()).add(ordinal)
        self.aliases["SELF"] = self.local | self.aliases.get(self.base, set())
        intermediates = spec.get("intermediates", [])
        for _ in range(len(intermediates) + 1):
            for item in intermediates:
                columns = self.aliases.get(item.get("dataset"), set()) | set(
                    item.get("derivations", {})
                )
                self.aliases[item["id"]] = (
                    columns & set(item["columns"]) if "columns" in item else columns
                )
        if self.base in self.aliases:
            self.aliases[self.base] |= self.local
        self.unresolved = set()

    def field(self, alias, name):
        if name not in self.aliases.get(alias, set()):
            self.unresolved.add(f"{alias}.{name}")
            return set()
        if alias == "SELF":
            return {f"spec.{name}" if name in self.local else f"{self.base}.{name}"}
        if (alias == self.base and name not in self.schemas.get(alias, set())
                and (alias, name) not in self.ordinals):
            return {f"spec.{name}"}
        return {f"{alias}.{name}"}

    def text(self, expression, donor, driver, bindings, join, row=False):
        result = set()
        for match in TOKENS.finditer(expression):
            token = match.group()
            if token.startswith("'") or expression[match.end() :].lstrip().startswith(
                "("
            ):
                continue
            if token in bindings:
                value = bindings[token]
                result |= value() if callable(value) else value
            elif "." in token:
                alias, name = token.split(".", 1)
                result |= self.field(alias, name)
                if join and alias in self.schemas and alias not in {donor, driver}:
                    declaration = self.spec["input"].get(alias, {})
                    if isinstance(declaration, dict):
                        result |= self.keys(
                            declaration.get("key", []),
                            alias,
                            driver,
                            implicit=True,
                            row=row,
                        )
            elif donor and token in self.aliases.get(donor, set()):
                result |= self.field(donor, token)
            elif token in self.local:
                result.add(f"spec.{token}")
        return result

    def keys(self, keys, donor, driver=None, bindings=None, implicit=False, row=False):
        pairs = (
            keys.items() if isinstance(keys, dict) else ((name, name) for name in keys)
        )
        result = set()
        for name, value in pairs:
            result |= self.read(
                f"{donor}.{name}", donor=donor, bindings=bindings, join=False
            )
            scope = driver if implicit and row else None
            result |= self.read(value, donor=scope, driver=driver, row=row)
            # Preserve a resolvable driver-field match when no column has that name.
            if (
                isinstance(value, str)
                and value not in self.local
                and value in self.schemas.get(driver or self.base, set())
            ):
                result |= self.field(driver or self.base, value)
        return result

    def bounds(self, value, donor, driver, bindings, row=False):
        result = self.read(value.get("value"), driver=driver, row=row)
        for key in ("lower", "upper"):
            if value.get(key):
                result |= self.read(
                    f"{donor}.{value[key]}", donor=donor, bindings=bindings, join=False
                )
        return result

    def local_bindings(self, definitions, donor, driver, parent, join, row=False):
        bindings, cache, active = dict(parent or {}), {}, set()

        def resolve(name):
            if name in active:
                self.unresolved.add(f"aggregate.{name}")
                return set()
            if name not in cache:
                active.add(name)
                definition = definitions[name]
                if isinstance(definition, dict) and "derivation" in definition:
                    definition = definition["derivation"]
                cache[name] = self.read(definition, donor, driver, bindings, join, row)
                active.remove(name)
            return cache[name]

        for name in definitions:
            bindings[name] = lambda name=name: resolve(name)
        return bindings

    def aggregate(self, value, donor, driver, bindings, join, row=False):
        if not isinstance(value, dict):
            return self.read(value, donor, driver, bindings, join, row)
        definitions = value.get("derivations", {})
        raw_bindings = self.local_bindings(
            definitions, donor, driver, bindings, False, row
        )
        raw = self.read(value.get("expr"), donor, driver, raw_bindings, False, row)
        relations = {
            ref.split(".", 1)[0] for ref in raw if ref.split(".", 1)[0] in self.schemas
        }
        relation = next(iter(relations)) if len(relations) == 1 else donor
        scoped = self.local_bindings(definitions, relation, driver, bindings, join, row)
        result = set()
        for key in ("expr", "filter", "group_by", "order_by"):
            result |= self.read(value.get(key), relation, driver, scoped, join, row)
        if relation and (relation != driver or not row) and join:
            declaration = self.spec["input"].get(relation, {})
            fallback = (
                declaration.get("key", []) if isinstance(declaration, dict) else []
            )
            result |= self.keys(
                value.get("key", fallback),
                relation,
                driver,
                implicit="key" not in value,
                row=row,
            )
        if value.get("between") and relation:
            result |= self.bounds(value["between"], relation, driver, scoped, row)
        return result

    def read(self, value, donor=None, driver=None, bindings=None, join=True, row=False):
        bindings = bindings or {}
        if isinstance(value, str):
            return self.text(value, donor, driver, bindings, join, row)
        if isinstance(value, list):
            return set().union(
                *(self.read(v, donor, driver, bindings, join, row) for v in value)
            )
        result = set()
        if isinstance(value, dict):
            for key, item in value.items():
                if key in LITERALS:
                    continue
                if key == "aggregate":
                    result |= self.aggregate(item, donor, driver, bindings, join, row)
                elif key == "between" and donor:
                    result |= self.bounds(item, donor, driver, bindings, row)
                elif key == "str_template" and isinstance(item, dict):
                    for name in re.findall(
                        r"(?<!\{)\{([^{}]+)\}(?!\})", item.get("template", "")
                    ):
                        result |= self.read(name, donor, driver, bindings, join, row)
                else:
                    result |= self.read(item, donor, driver, bindings, join, row)
        return result
