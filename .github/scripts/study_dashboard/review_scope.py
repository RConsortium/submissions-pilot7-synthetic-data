"""Publish dataset/Define-XML discrepancies and reviewed documentation issues."""

import hashlib
import json
import re
from pathlib import PurePosixPath

from .issues import KINDS, impact, review_status, validate_review, validate_shape


def is_adam_define(evidence):
    return (
        evidence["type"] == "document"
        and evidence.get("verified", False)
        and PurePosixPath(evidence["path"]).name.lower()
        in {"define.xml", "define-adam.xml"}
    )


def load_publication(root, study, review, define_path):
    """Bind explicit review decisions to the original XML and current checks."""
    directory = root / study / "spec/review"
    paths = sorted(directory.glob("*-publication.json"))
    if (directory / "publication.json").is_file():
        paths.insert(0, directory / "publication.json")
    checks = {c["id"]: c for c in review["checks"]}
    source_hash = hashlib.sha256(define_path.read_bytes()).hexdigest() if define_path.is_file() else None
    result = {}
    for path in paths:
        declaration = json.loads(path.read_text())
        validate_shape("publication", declaration)
        if declaration["source_sha256"] != source_hash:
            raise ValueError(f"{path}: publication decisions are not bound to the current Define-XML")
        for key, decision in declaration["decisions"].items():
            identifier = key if key.startswith(study + ":") else study + ":" + key
            if identifier not in checks:
                raise ValueError(f"{path}: publication decision names an unknown check: {key}")
            if identifier in result:
                raise ValueError(f"{path}: duplicate publication decision: {key}")
            if decision.get("basis") and decision["basis"].removeprefix("sha256:") != (checks[identifier].get("basis") or "").removeprefix("sha256:"):
                raise ValueError(f"{path}: publication decision basis changed: {key}")
            result[identifier] = decision
    return result


def measured_evidence(linked):
    eligible = set()
    for e in linked:
        if e["type"] == "codelist":
            measured = e["target"] == "reference" and bool(e["values"])
        elif e["type"] == "comparison":
            measured = e["differ"] > 0 and (
                e["method"] == "dataset_define"
                or e["target"] == "reference" and (
                    e["method"] == "copy" or e["reading"] == "literal"
                )
            )
        else:
            measured = False
        if measured:
            eligible.add(e["id"])
    return eligible


def complete_decisions(review, decisions=None):
    """Group repeated scoped checks without discarding their evidence."""
    decisions = {key: dict(value) for key, value in (decisions or {}).items()}
    rules = {}
    for check in review["checks"]:
        rule = (check.get("rule") or {}).get("id")
        if rule in {"CR-2", "CR-3", "CR-5", "CR-8", "CR-9", "CR-10"}:
            default = "metadata:codelist" if rule == "CR-9" else "documented-rule" if rule in {"CR-5", "CR-8", "CR-10"} else "documented-source"
            decision = decisions.setdefault(check["id"], {})
            decision.setdefault("group", default)
            if decision.get("disposition") not in {"exclude", "coverage"}:
                rules.setdefault((check["dataset"], check["variable"], rule), []).append(decision["group"])

    def rule_group(check, identifiers, default):
        for identifier in identifiers:
            groups = set(rules.get((check["dataset"], check["variable"], identifier), []))
            if len(groups) == 1:
                return next(iter(groups))
        return default
    for check in review["checks"]:
        if check["comparison"] != "dataset_define":
            continue
        property_name = re.sub(r"_value_level_\d+$", "", check["id"].rsplit(":", 1)[-1])
        if property_name == "arithmetic_method":
            group = rule_group(check, ["CR-5", "CR-8", "CR-10"], "documented-rule")
        elif property_name in {"predecessor_copy", "predecessor_source"}:
            group = rule_group(check, ["CR-3", "CR-2", "CR-5"], "documented-source")
        elif property_name == "codelist":
            group = rule_group(check, ["CR-9"], "metadata:codelist")
        else:
            group = "metadata:" + property_name
        decisions.setdefault(check["id"], {}).setdefault("group", group)
    return decisions


def project_review(review, decisions=None):
    """Preserve the audit; separate outstanding observations and coverage."""
    decisions = decisions or {}
    evidence = {e["id"]: e for e in review["evidence"]}
    checks = {c["id"]: c for c in review["checks"]}
    selections = {}
    for check in review["checks"]:
        linked = [evidence[key] for key in check["evidence_ids"]]
        defined = any(is_adam_define(e) for e in linked)
        rule = (check.get("rule") or {}).get("id")
        measured = measured_evidence(linked) if defined else set()
        if check["comparison"] == "dataset_define" and defined:
            disposition = "finding"
        elif defined and rule in {"CR-2", "CR-3", "CR-5", "CR-9"}:
            disposition = "finding" if measured or rule == "CR-2" else "exclude"
        elif rule == "CR-8" and sum(is_adam_define(e) for e in linked) >= 2:
            disposition = "clarification"
        elif defined and rule == "CR-10":
            disposition = "coverage"
        else:
            disposition = "exclude"
        decision = decisions.get(check["id"], {})
        disposition = decision.get("disposition", disposition)
        if disposition in {"finding", "clarification"} and not defined:
            raise ValueError(f"{check['id']}: a published observation requires verified Define-XML evidence")
        selections[check["id"]] = (disposition, measured, decision)

    def selected_review(coverage=False):
        issues, groups = [], {}
        projected_checks = {key: dict(value) for key, value in checks.items()}
        for key, (disposition, _, decision) in selections.items():
            if disposition in {"clarification", "coverage"}:
                projected_checks[key]["kind"] = "unclear" if disposition == "coverage" else "gap"
                projected_checks[key]["title"] = decision.get("title", "Clarify the documented rule")
                if decision.get("reason"):
                    projected_checks[key]["summary"] = decision["reason"]
        for issue in review["issues"]:
            retained = [key for key in issue["check_ids"] if selections[key][0] in (
                {"coverage"} if coverage else {"finding", "clarification"}
            )]
            impacts = {t["evidence_id"] for t in issue["trace"] if t["role"] == "impact"}
            retained = [key for key in retained if
                        selections[key][0] != "finding" or decisions.get(key, {}).get("disposition")
                        or checks[key]["comparison"] == "dataset_define"
                        or (checks[key].get("rule") or {}).get("id") == "CR-2"
                        or bool(selections[key][1] & impacts)]
            if not retained:
                continue
            measured = set().union(*(selections[key][1] for key in retained
                                   if selections[key][0] == "finding"))
            selected = [t["evidence_id"] for t in issue["trace"]
                        if t["role"] == "impact" and t["evidence_id"] in measured]
            allowed = {key for cid in retained for key in checks[cid]["evidence_ids"]}
            trace = [{**t, "role": "context"} if t["role"] == "impact"
                     and t["evidence_id"] not in selected else t for t in issue["trace"]
                     if t["evidence_id"] in allowed]
            entry = {**issue, "trace": trace, "check_ids": retained,
                     "impact": impact([evidence[key] for key in selected])}
            overrides = [selections[key][2] for key in retained]
            reasons = list(dict.fromkeys(d["reason"] for d in overrides if d.get("reason")))
            if reasons:
                entry["summary"] = " ".join(reasons)
            if coverage or all(selections[key][0] == "clarification" for key in retained):
                entry["kind"] = "unclear" if coverage else "gap"
                entry["critical"] = {"status": "needs_review", "reason": "Documentation or assessment requires a review decision."}
                entry["title"] = "Clarify the documented rule"
            titles = list(dict.fromkeys(d["title"] for d in overrides if d.get("title")))
            if len(titles) == 1:
                entry["title"] = titles[0]
            group_names = {d["group"] for d in overrides if d.get("group")}
            group = (issue["dataset"], issue["variable"], next(iter(group_names))) if len(group_names) == 1 else None
            if group is not None and group in groups:
                previous = groups[group]
                previous["aliases"] = list(dict.fromkeys([*previous.get("aliases", []), entry["id"], *entry.get("aliases", [])]))
                previous["check_ids"] = list(dict.fromkeys([*previous["check_ids"], *entry["check_ids"]]))
                role_by_id = {t["evidence_id"]: t["role"] for t in previous["trace"]}
                for t in entry["trace"]:
                    if t["role"] == "impact" or t["evidence_id"] not in role_by_id:
                        role_by_id[t["evidence_id"]] = t["role"]
                previous["trace"] = [{"evidence_id": key, "role": role} for key, role in role_by_id.items()]
                previous["impact"] = impact([evidence[key] for key, role in role_by_id.items() if role == "impact"])
                previous["summary"] = " ".join(dict.fromkeys([previous["summary"], entry["summary"]]))
                status = next(status for status in ("yes", "needs_review", "no")
                              if status in {previous["critical"]["status"], entry["critical"]["status"]})
                previous["critical"] = previous["critical"] if previous["critical"]["status"] == status else entry["critical"]
            else:
                issues.append(entry)
                if group is not None:
                    groups[group] = entry
        check_ids = {key for i in issues for key in i["check_ids"]}
        changed = True
        while changed:
            changed = False
            for issue in issues:
                linked = [projected_checks[key] for key in issue["check_ids"]]
                if len({c["comparison"] for c in linked}) > 1:
                    for check in linked:
                        check["comparison"] = "dataset_define"
                    changed = True
        for issue in issues:
            linked = [projected_checks[key] for key in issue["check_ids"]]
            issue["comparison"] = linked[0]["comparison"]
            issue["kind"] = min((c["kind"] for c in linked), key=KINDS.index)
            issue["review"] = review_status(linked)
        retained_checks = [projected_checks[c["id"]] for c in review["checks"] if c["id"] in check_ids]
        evidence_ids = {key for c in retained_checks for key in c["evidence_ids"]}
        result = {**review, "issues": issues, "checks": retained_checks,
                  "evidence": [e for e in review["evidence"] if e["id"] in evidence_ids],
                  "counts": {"issues": len(issues), "checks": len(retained_checks),
                             "evidence": len(evidence_ids)}}
        validate_review(result)
        return result

    return {"review": selected_review(), "coverage": selected_review(True)}


def dataset_define_review(review, decisions=None):
    return project_review(review, decisions)["review"]
