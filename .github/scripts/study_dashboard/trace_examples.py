"""Small, row-aligned reference examples from the actual verification run.

Examples illustrate a variable's calculations, never determine impact counts.
All comparisons and their complete populations remain in the verification report.
"""

import json
from collections import Counter

from .datasets import clean
from .lineage import build_lineage


class TraceExamples:
    def __init__(self, reference, derived, probe, spec, text, subject_key):
        self.keys = spec["keys"]
        self.subject_key = subject_key
        self.reference = reference.to_dicts()
        self.derived = derived.to_dicts()
        self.probe = probe.to_dicts()
        self.columns = reference.columns
        # A documented-rules specification reads the reference as REF, an intermediate over
        # its base input; both names resolve to the reference columns.
        schemas = {"REF": set(self.columns)}
        if spec.get("base"):
            schemas[spec["base"]] = set(self.columns)
        self.edges = build_lineage(text, spec, schemas)["edges"]
        self.indexes = []
        self.reason = ""
        for rows in (self.reference, self.derived, self.probe):
            index = {}
            for row in rows:
                key = tuple(row.get(k) for k in self.keys)
                if any(value is None for value in key):
                    self.reason = "Subject examples are unavailable because record keys contain missing values."
                if key in index:
                    self.reason = "Subject examples are unavailable because record keys are not unique."
                index[key] = row
            self.indexes.append(index)
        self.rows_by_key = dict(self.indexes[0])
        for key, row in self.indexes[2].items():
            self.rows_by_key.setdefault(key, row)
        self.subject_counts = Counter(str(r.get(subject_key)) for r in self.rows_by_key.values())

    def inputs(self, probes, context):
        seen, pending, names = set(), ["spec." + p["column"] for p in probes], set(context)
        while pending:
            node = pending.pop()
            if node in seen:
                continue
            seen.add(node)
            if node.startswith("REF."):
                names.add(node.removeprefix("REF."))
            pending.extend(self.edges.get(node, []))
        return [n for n in self.columns if n in names and n not in self.keys]

    def variable(self, name, probes, context=(), max_rows=12):
        if self.reason or self.subject_key not in self.keys:
            return {"reason": self.reason or "No subject key is available for these record keys."}
        if not isinstance(context, (list, tuple)) or any(n not in self.columns for n in context):
            raise ValueError(f"{name}: example_columns must name reference columns")
        selected, profiles = [], {}
        for probe in probes:
            candidates = {}
            for pattern in probe["reference"]["patterns"]:
                signature = json.dumps(
                    [pattern[k] for k in ("reference", "observed", "row")], sort_keys=True
                )
                for subject in pattern["subjects"]:
                    candidates.setdefault(str(subject), set()).add(signature)
            ordered = sorted(candidates)
            if ordered:
                first = ordered[0]
                empty = lambda s: all(json.loads(p)[0] in (None, "") for p in candidates[s])
                complementary = [s for s in ordered[1:] if empty(s) != empty(first)]
                second = min(complementary, key=lambda s: (self.subject_counts[s], s)) if complementary else None
                second = second or next((s for s in ordered[1:] if candidates[s] != candidates[first]), None)
                for subject in [first, second or (ordered[1] if len(ordered) > 1 else None)]:
                    if subject and subject not in selected:
                        selected.append(subject)
        if not selected:
            selected = sorted({str(r[self.subject_key]) for r in self.reference
                               if r.get(self.subject_key) is not None})[:2]
        fields = [n for n in self.inputs(probes, context) if n != name]
        # Include probe-only records, and distinguish their absence from a missing value.
        for subject in selected:
            rows = []
            for key, row in self.rows_by_key.items():
                if str(row.get(self.subject_key)) != subject:
                    continue
                ref, derived, probe = (index.get(key) for index in self.indexes)

                def cell(source, column):
                    present = source is not None
                    column_present = present and column in source
                    return {"present": present, "column_present": column_present,
                            "value": clean(source[column]) if column_present else None}

                rows.append({
                    "keys": {k: clean(row.get(k)) for k in self.keys},
                    "inputs": {n: clean(ref.get(n)) if ref else None for n in fields},
                    "reference": cell(ref, name),
                    "derived": cell(derived, name),
                    "calculations": {p["column"]: cell(probe, p["column"]) for p in probes},
                })
            # Keep informative flag or differing records when a subject has many rows.
            def priority(row):
                cells = [row["reference"], *row["calculations"].values()]
                distinct = {json.dumps(c, sort_keys=True) for c in cells}
                return (len(distinct) == 1, not any(c["value"] == "Y" for c in cells))

            retained = sorted(enumerate(rows), key=lambda item: (priority(item[1]), item[0]))[:max_rows]
            profiles[subject] = {
                "id": subject, "total_rows": len(rows),
                "rows": [row for _, row in sorted(retained)],
            }
        return {
            "subject_key": self.subject_key,
            "keys": self.keys,
            "input_columns": fields,
            "calculations": [{"column": p["column"], "reading": p["reading"]} for p in probes],
            "subjects": list(profiles.values()),
            "scope": "Recalculates this variable using reference upstream values; it does not rerun the full analysis pipeline. Reference inputs are shown; other lookups remain in calculation details.",
        }
