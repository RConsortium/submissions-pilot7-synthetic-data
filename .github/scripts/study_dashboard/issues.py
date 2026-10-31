"""Validated review issues over unchanged automated checks and shared evidence."""

from functools import lru_cache
import hashlib
import json
from pathlib import Path
import re

from jsonschema import Draft202012Validator

from .programs import is_program

SCHEMAS = Path(__file__).resolve().parents[2] / "schemas"
CHECK_TITLES = {
    "CR-1": "Source quote could not be verified",
    "CR-2": "Documented source variable is absent",
    "CR-3": "Documented source differs from generated ADaM datasets",
    "CR-4": "Specification uses a different copy source",
    "CR-5": "Define-XML differs from derived ADaM datasets",
    "CR-6": "Specification differs from a documented clause",
    "CR-7": "Specification clause is undocumented",
    "CR-8": "Source documents disagree",
    "CR-9": "Values fall outside the documented codelist",
    "CR-10": "Documented rule is incomplete",
    "CR-11": "Derivation is undocumented",
}
KINDS = [
    "conflict",
    "inconsistent",
    "evidence",
    "missing_evidence",
    "divergence",
    "gap",
    "unclear",
    "not_reviewed",
]


def digest(value):
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, ensure_ascii=True).encode()
    ).hexdigest()


@lru_cache
def validator(name):
    schema = json.loads((SCHEMAS / f"review-{name}.schema.json").read_text())
    Draft202012Validator.check_schema(schema)
    return Draft202012Validator(schema)


def validate_shape(name, value):
    errors = sorted(validator(name).iter_errors(value), key=lambda e: str(list(e.path)))
    if errors:
        first = errors[0]
        raise ValueError(f"review {name} at {list(first.path)}: {first.message}")


def unique(items):
    return sorted({str(item) for item in items})


def measurement_subjects(e):
    entries = e.get("patterns", e.get("values", []))
    return unique(s for p in entries for s in p["subjects"])


def impact(evidence):
    measured = [
        e for e in evidence if e["type"] == "codelist" or e.get("compared", 0) > 0
    ]
    subjects = unique(s for e in measured for s in e["subjects"])
    differs = any(e.get("differ", len(e.get("values", []))) for e in measured)
    return {
        "status": (
            "observed" if differs else "not_observed" if measured else "not_measured"
        ),
        "subject_count": len(subjects),
        "subjects": subjects,
    }


def review_status(checks):
    decisions = {c["review"]["decision"] for c in checks}
    if len(decisions) == 1:
        return {"agree": "agreed", "dispute": "disputed"}.get(
            next(iter(decisions)), next(iter(decisions))
        )
    if "stale" in decisions:
        return "stale"
    return "mixed"


def critical_assessment(checks, pool):
    """Prioritize rule errors separately from impact counts and agent agreement."""
    assessments = []
    for check in checks:
        rule = (check["rule"] or {}).get("id")
        quotes = [
            pool.items[key]["quote"].strip()
            for key in check["evidence_ids"]
            if pool.items[key]["type"] == "document"
        ]
        # Use the clause's exact quotation, never the full variable context:
        # that context can contain both precision metadata and a wrong formula.
        precision_only = rule == "CR-6" and quotes and all(
            re.fullmatch(r"Significant digits:\s*\d+\.?", quote, re.IGNORECASE)
            for quote in quotes
        )
        if precision_only:
            assessments.append(("no", "Only the declared numeric precision differs."))
        elif check["title"] == "Variable label differs from published Define-XML":
            assessments.append(("no", "Only the variable label differs."))
        elif rule in {"CR-2", "CR-3", "CR-4", "CR-5", "CR-6", "CR-8", "CR-9"} or (
            check["comparison"] == "input_output" and check["kind"] == "inconsistent"
        ):
            assessments.append(("yes", "A source, derivation rule, category or output differs."))
        else:
            assessments.append(
                ("needs_review", "Evidence is incomplete or the finding needs a review decision.")
            )
    status = next(
        s for s in ("yes", "needs_review", "no")
        if any(a[0] == s for a in assessments)
    )
    reasons = list(dict.fromkeys(reason for s, reason in assessments if s == status))
    return {"status": status, "reason": " ".join(reasons)}


class Evidence:
    """Content identity deduplicates sources without losing exact quotations."""

    def __init__(self):
        self.items = {}

    def add(self, data):
        identity = {k: v for k, v in data.items() if k != "url"}
        key = "e-" + digest(identity)
        self.items[key] = {"id": key, **data}
        return key

    def citation(self, side, kind):
        if not side or not side.get("path"):
            return None
        section = side.get("section", side.get("element", "")) or ""
        # Program lines read as "adlbc.r, lines 224-226"; other titles keep their identity.
        shown = (side.get("section_title") or section).lower() if is_program(side["path"]) else section
        return self.add(
            {
                "type": kind,
                "title": f'{Path(side["path"]).name}, {shown}',
                "path": side["path"],
                "section": section,
                "quote": side.get("quote") or "",
                "context": side.get("context", side.get("excerpt", "")) or "",
                "lines": side.get("lines"),
                "context_lines": side.get("element_lines"),
                "url": side.get("repository", side.get("url", "")) or "",
                "verified": side.get("verified", True),
                "reason": side.get("reason"),
            }
        )

    def comparison(self, result, method, column, reading, target):
        if result is None:
            return None
        patterns = [
            {**p, "subjects": unique(p["subjects"])} for p in result["patterns"]
        ]
        data = {
            "type": "comparison",
            "method": method,
            "column": column,
            "reading": reading,
            "target": target,
            "compared": result["compared"],
            "differ": result["differ"],
            "patterns": patterns,
        }
        data["subjects"] = measurement_subjects(data)
        return self.add(data)


def check_record(f, pool):
    ids, selectors = [], {}

    def add(key):
        if key and key not in ids:
            ids.append(key)

    for side in f.get("documents", []):
        add(pool.citation(side, "document"))
    for side in (f.get("spec_quote"), f.get("variable_spec")):
        add(pool.citation(side, "specification"))
    if not f.get("rule"):
        source = f.get("source", {})
        url = source.get("url", "")
        add(
            pool.citation(
                {
                    **source,
                    "section": (
                        url.split("#", 1)[1]
                        if "#" in url
                        else source.get("section", "")
                    ),
                    "url": url if url.startswith("https://") else "",
                    "context": source.get("excerpt", ""),
                    "quote": source.get("excerpt", ""),
                },
                "document",
            )
        )
        spec = f.get("spec", {})
        if spec.get("literal", True):
            first = spec.get("line", 1)
            last = (
                spec.get("end_line")
                or first + len(spec.get("excerpt", "").splitlines()) - 1
            )
            add(
                pool.citation(
                    {**spec, "element_lines": [first, max(first, last)]},
                    "specification",
                )
            )
    e = f.get("evidence") or {}
    if e.get("dataset_check") is not None:
        add(pool.comparison(e["dataset_check"], "dataset_define",
                            f["variable"] or "Dataset", f["title"], "derived"))
    for p in e.get("probes", []):
        add(pool.citation(p.get("definition"), "specification"))
        for target in ("reference", "derived"):
            key = pool.comparison(
                p.get(target), "probe", p["column"], p["reading"], target
            )
            if key:
                add(key)
                selectors[("probe", p["column"], target)] = key
    copy = e.get("copy") or {}
    key = pool.comparison(
        copy.get("reference"),
        "copy",
        copy.get("source", "source"),
        "documented source",
        "reference",
    )
    if key:
        add(key)
        selectors[("copy", None, "reference")] = key
    codelist = e.get("codelist") or {}
    for target in ("reference", "derived"):
        if target not in codelist:
            continue
        values = [
            {**v, "subjects": unique(v.get("subjects", []))} for v in codelist[target]
        ]
        key = pool.add(
            {
                "type": "codelist",
                "codelist": codelist["oid"],
                "target": target,
                "values": values,
                "subjects": unique(s for v in values for s in v["subjects"]),
            }
        )
        add(key)
        selectors[("codelist", None, target)] = key
    for title, note in (
        ("Current derived dataset", f.get("data", {}).get("summary")
         if f["comparison"] == "dataset_define" else None),
        ("Documented rule check unavailable", e.get("not_probed_reason")),
        ("Copy source", copy.get("reason")),
    ):
        if note:
            add(pool.add({"type": "note", "title": title, "text": note}))
    rule = f.get("rule")
    raw_review = f.get("adjudication") or {}
    return {
        "id": f["id"],
        "dataset": f["dataset"],
        "variable": f["variable"],
        "kind": f["kind"],
        "comparison": f["comparison"],
        "title": f["title"],
        "summary": f["observation"],
        "rule": {k: rule[k] for k in ("id", "title", "statement")} if rule else None,
        "review": {
            "decision": raw_review.get("decision", "not_reviewed"),
            "reason": raw_review.get("reason", ""),
        },
        "basis": f.get("basis_hash"),
        "evidence_ids": ids,
    }, selectors


def make_issue(study, definition, checks, data, pool, citations=None):
    selected = {item["evidence_id"]: item["role"] for item in data}
    trace = {}
    for c in checks:
        for key in c["evidence_ids"]:
            if pool.items[key]["type"] in {"document", "specification", "note"} and (
                citations is None or key in citations
            ):
                trace.setdefault(key, "context")
    trace.update(selected)
    return {
        "id": f'{study}:{checks[0]["dataset"]}.{definition["variable"]}.{definition["id"]}',
        **({"aliases": definition["aliases"]} if definition.get("aliases") else {}),
        "dataset": checks[0]["dataset"],
        "variable": definition["variable"],
        "kind": min((c["kind"] for c in checks), key=KINDS.index),
        "comparison": checks[0]["comparison"],
        **{
            k: definition[k]
            for k in ("title", "summary", "expected", "observed", "action")
        },
        "check_ids": [c["id"] for c in checks],
        "trace": [{"evidence_id": key, "role": role} for key, role in trace.items()],
        "impact": impact(
            [pool.items[k] for k, role in selected.items() if role == "impact"]
        ),
        "review": review_status(checks),
        "critical": definition.get("critical") or critical_assessment(checks, pool),
    }


def declaration_issues(path, study, checks, selectors, pool):
    declaration = json.loads(path.read_text())
    validate_shape("issues", declaration)
    domain = declaration["dataset"]
    actual = {
        c["id"].removeprefix(study + ":"): c
        for c in checks
        if c["dataset"] == domain and c["rule"]
    }
    if set(actual) != set(declaration["checks"]):
        raise ValueError(f"{path}: issue check inventory changed; review the grouping")
    for key, expected in declaration["checks"].items():
        if actual[key]["basis"] != expected:
            raise ValueError(
                f"{path}: stale issue basis for {key}; review the grouping"
            )
    found, covered, identifiers = [], set(), set()
    for item in declaration["issues"]:
        identity = (item["variable"], item["id"])
        if identity in identifiers:
            raise ValueError(f"{path}: duplicate issue {identity}")
        identifiers.add(identity)
        if any(
            key not in actual or actual[key]["variable"] != item["variable"]
            for key in item["checks"]
        ):
            raise ValueError(f"{path}: issue check outside variable {item['variable']}")
        linked = [actual[key] for key in item["checks"]]
        citations = None
        if "citations" in item:
            citations = []
            for selection in item["citations"]:
                key = selection["check"]
                if key not in item["checks"]:
                    raise ValueError(
                        f"{path}: citation references an unlinked check {key}"
                    )
                candidates = [
                    eid
                    for eid in actual[key]["evidence_ids"]
                    if pool.items[eid]["type"] == selection["type"]
                    and pool.items[eid]["section"] == selection["section"]
                    and (
                        "path" not in selection
                        or pool.items[eid]["path"] == selection["path"]
                    )
                    and (
                        "quote" not in selection
                        or pool.items[eid]["quote"] == selection["quote"]
                    )
                ]
                if len(candidates) != 1:
                    raise ValueError(
                        f"{path}: missing or ambiguous citation {selection}"
                    )
                citations.extend(candidates)
        data = []
        for selection in item["data"]:
            key = selection["check"]
            if key not in item["checks"]:
                raise ValueError(
                    f"{path}: data selector references an unlinked check {key}"
                )
            route = (selection["kind"], selection.get("column"), selection["target"])
            evidence_id = selectors[actual[key]["id"]].get(route)
            if evidence_id is None:
                raise ValueError(f"{path}: unavailable evidence selector {key} {route}")
            if evidence_id in {d["evidence_id"] for d in data}:
                raise ValueError(f"{path}: duplicate data selector in {identity}")
            data.append({"evidence_id": evidence_id, "role": selection["role"]})
        found.append(make_issue(study, item, linked, data, pool, citations))
        covered.update(item["checks"])
    if covered != set(actual) and not declaration.get("allow_ungrouped", False):
        raise ValueError(
            f"{path}: checks missing from issues: {sorted(set(actual) - covered)}"
        )
    return found, {actual[k]["id"] for k in covered}


def source_pair(finding):
    """The two files a verified clause compares, excluding supporting evidence."""
    rule = (finding.get("rule") or {}).get("id")
    documents = finding.get("documents", [])
    if any(not d.get("verified", True) for d in documents):
        return None
    if rule == "CR-8" and len(documents) == 2:
        sides = [("document", d.get("path")) for d in documents]
    elif rule in {"CR-6", "CR-7"} and len(documents) == 1:
        spec = finding.get("spec_quote") or {}
        if not spec.get("verified", True):
            return None
        sides = [("document", documents[0].get("path")),
                 ("specification", spec.get("path"))]
    else:
        return None
    return tuple(sorted(sides)) if all(path for _, path in sides) else None


def fallback_issues(study, checks, originals, pool):
    """Combine clauses only for the same variable and exact source-file pair."""
    groups = {}
    for check in sorted(checks, key=lambda c: c["id"]):
        pair = source_pair(originals[check["id"]])
        key = (check["dataset"], check["variable"], check["comparison"], pair) if pair else check["id"]
        groups.setdefault(key, []).append(check)
    issues = []
    for linked in groups.values():
        findings = [originals[c["id"]] for c in linked]
        first = findings[0]
        definition = {
            "id": "check-" + digest(linked[0]["id"])[:16],
            "variable": linked[0]["variable"],
            "title": CHECK_TITLES.get((first.get("rule") or {}).get("id"), first["title"]),
            "summary": first["observation"],
            "expected": first.get("expected", ""),
            "observed": first.get("observed", ""),
            "action": " ".join(dict.fromkeys(f.get("recommendation", "") for f in findings)),
        }
        if first.get("critical"):
            definition["critical"] = first["critical"]
        if len(linked) > 1:
            pair = source_pair(first)
            definition["title"] += ": " + " vs ".join(Path(path).name for _, path in pair)
            assessments = {f.get("assessment", "") for f in findings}
            definition["summary"] = (
                next(iter(assessments)) if len(assessments) == 1 and "" not in assessments
                else " ".join(dict.fromkeys(f.get("note") or f["observation"] for f in findings))
            )
        selected = dict.fromkeys(
            key for c in linked for key in c["evidence_ids"]
            if pool.items[key]["type"] in {"comparison", "codelist"}
        )
        data = [{"evidence_id": key, "role": "impact"} for key in selected]
        issue = make_issue(study, definition, linked, data, pool)
        if len(linked) > 1:
            issue["aliases"] = [
                f'{study}:{c["dataset"]}.{c["variable"]}.check-{digest(c["id"])[:16]}'
                for c in linked[1:]
            ]
        issues.append(issue)
    return issues


def build_review(root, study, revision, findings, use_authored=True):
    """Honor authored decisions; otherwise group verified clauses by source pair."""
    pool, checks, selectors = Evidence(), [], {}
    for f in findings:
        if f["kind"] == "executed":
            continue
        check, selection = check_record(f, pool)
        checks.append(check)
        selectors[check["id"]] = selection
    issues, covered = [], set()
    for path in sorted((Path(root) / study / "spec/review").glob("*-issues.json")) if use_authored else []:
        domain = path.stem.removesuffix("-issues").upper()
        found, assigned = declaration_issues(path, study, checks, selectors, pool)
        if any(i["dataset"] != domain for i in found):
            raise ValueError(f"{path}: issue dataset does not match filename")
        issues.extend(found)
        covered.update(assigned)
    originals = {f["id"]: f for f in findings}
    issues.extend(fallback_issues(
        study, [c for c in checks if c["id"] not in covered], originals, pool
    ))
    issues.sort(
        key=lambda i: (KINDS.index(i["kind"]), i["dataset"], i["variable"], i["id"])
    )
    result = {
        "schema_version": 1,
        "study": study,
        "revision": revision,
        "issues": issues,
        "checks": checks,
        "evidence": list(pool.items.values()),
        "counts": {
            "issues": len(issues),
            "checks": len(checks),
            "evidence": len(pool.items),
        },
    }
    validate_review(result)
    return result


def validate_review(review):
    """Validate shape and relational/count invariants before publishing any bytes."""
    validate_shape("report", review)
    indexes = {}
    for name in ("issues", "checks", "evidence"):
        items = review[name]
        indexes[name] = {v["id"]: v for v in items}
        if len(indexes[name]) != len(items) or review["counts"][name] != len(items):
            raise ValueError(f"review: duplicate identity or wrong count in {name}")
    checks, evidence = indexes["checks"], indexes["evidence"]
    referenced = set()
    issue_ids = set(indexes["issues"])
    aliases = set()
    for e in evidence.values():
        if e["id"] != "e-" + digest(
            {k: v for k, v in e.items() if k not in {"id", "url"}}
        ):
            raise ValueError(f"review: evidence identity changed in {e['id']}")
        if e["type"] == "comparison":
            if (
                e["differ"] > e["compared"]
                or sum(p["count"] for p in e["patterns"]) != e["differ"]
            ):
                raise ValueError(f"review: invalid comparison counts in {e['id']}")
        if e["type"] in {"comparison", "codelist"} and e[
            "subjects"
        ] != measurement_subjects(e):
            raise ValueError(f"review: invalid measurement subjects in {e['id']}")
        if any(
            p["count"] < len(p["subjects"])
            for p in e.get("patterns", e.get("values", []))
        ):
            raise ValueError(
                f"review: record count smaller than subject count in {e['id']}"
            )
        for line_key in ("lines", "context_lines"):
            if e.get(line_key) and e[line_key][0] > e[line_key][1]:
                raise ValueError(f"review: reversed source lines in {e['id']}")
    for check in checks.values():
        if any(key not in evidence for key in check["evidence_ids"]):
            raise ValueError(f"review: dangling check evidence in {check['id']}")
    for issue in review["issues"]:
        for alias in issue.get("aliases", []):
            if alias in issue_ids or alias in aliases:
                raise ValueError(f"review: duplicate issue alias {alias}")
            aliases.add(alias)
        if any(key not in checks for key in issue["check_ids"]):
            raise ValueError(f"review: dangling issue check in {issue['id']}")
        linked = [checks[key] for key in issue["check_ids"]]
        if len({t["evidence_id"] for t in issue["trace"]}) != len(issue["trace"]):
            raise ValueError(f"review: duplicate trace evidence in {issue['id']}")
        if any(
            (c["dataset"], c["variable"], c["comparison"])
            != (issue["dataset"], issue["variable"], issue["comparison"])
            for c in linked
        ):
            raise ValueError(f"review: issue scope mismatch in {issue['id']}")
        allowed = {key for c in linked for key in c["evidence_ids"]}
        if any(t["evidence_id"] not in allowed for t in issue["trace"]):
            raise ValueError(f"review: dangling issue evidence in {issue['id']}")
        selected = [
            evidence[t["evidence_id"]] for t in issue["trace"] if t["role"] == "impact"
        ]
        if any(e["type"] not in {"comparison", "codelist"} for e in selected) or issue[
            "impact"
        ] != impact(selected):
            raise ValueError(f"review: invalid issue impact in {issue['id']}")
        if issue["review"] != review_status(linked) or issue["kind"] != min(
            (c["kind"] for c in linked), key=KINDS.index
        ):
            raise ValueError(f"review: inconsistent issue assessment in {issue['id']}")
        referenced.update(issue["check_ids"])
    if referenced != set(checks):
        raise ValueError("review: checks missing from issues")
