"""Publish observed dataset/Define-XML differences; retain the raw check audit."""

from pathlib import PurePosixPath

from .issues import impact, validate_review


def is_adam_define(evidence):
    return (
        evidence["type"] == "document"
        and evidence.get("verified", False)
        and PurePosixPath(evidence["path"]).name.lower()
        in {"define.xml", "define-adam.xml"}
    )


def dataset_define_review(review):
    """Require a differing literal measurement and Define-XML in the same check."""
    evidence = {e["id"]: e for e in review["evidence"]}
    checks = {c["id"]: c for c in review["checks"]}
    issues = []
    for issue in review["issues"]:
        measured = set()
        for key in issue["check_ids"]:
            linked = [evidence[eid] for eid in checks[key]["evidence_ids"]]
            if not any(is_adam_define(e) for e in linked):
                continue
            for e in linked:
                if e["type"] == "codelist":
                    eligible = e["target"] == "reference" and bool(e["values"])
                elif e["type"] == "comparison":
                    eligible = e["differ"] > 0 and (
                        e["method"] == "dataset_define"
                        or e["target"] == "reference" and (
                            e["method"] == "copy" or e["reading"] == "literal"
                        )
                    )
                else:
                    eligible = False
                if eligible:
                    measured.add(e["id"])
        selected = [t["evidence_id"] for t in issue["trace"]
                    if t["role"] == "impact" and t["evidence_id"] in measured]
        if not selected:
            continue
        trace = [{**t, "role": "context"} if t["role"] == "impact"
                 and t["evidence_id"] not in selected else t for t in issue["trace"]]
        issues.append({**issue, "trace": trace,
                       "impact": impact([evidence[key] for key in selected])})
    check_ids = {key for i in issues for key in i["check_ids"]}
    retained_checks = [c for c in review["checks"] if c["id"] in check_ids]
    evidence_ids = {key for c in retained_checks for key in c["evidence_ids"]}
    retained_evidence = [e for e in review["evidence"] if e["id"] in evidence_ids]
    result = {**review, "issues": issues, "checks": retained_checks,
              "evidence": retained_evidence,
              "counts": {"issues": len(issues), "checks": len(retained_checks),
                         "evidence": len(retained_evidence)}}
    validate_review(result)
    return result
