"""Published review scope requires measured differences backed by Define-XML."""

from copy import deepcopy
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))
from study_dashboard.issues import build_review
from study_dashboard.review_scope import complete_decisions, dataset_define_review, project_review


def finding(path="study/spec/define/define-adam.xml", differ=1,
            reading="literal", target="reference", verified=True):
    return {
        "id": "study:ADAE.FLAG.CR-5", "dataset": "ADAE", "variable": "FLAG",
        "kind": "conflict", "comparison": "documented_rules",
        "title": "Rule differs", "observation": "Observed value differs.",
        "rule": {"id": "CR-5", "title": "Rule", "statement": "Follow Define-XML."},
        "documents": [{"path": path, "section": "ADAE.FLAG", "quote": "Flag rule",
                       "context": "Flag rule", "verified": verified}],
        "evidence": {"probes": [{"column": "FLAG", "reading": reading, target: {
            "compared": 2, "differ": differ, "patterns": [{
                "reference": "Y", "observed": "", "row": "matched",
                "count": differ, "subjects": ["01"],
            }] if differ else [],
        }}]},
    }


class ReviewScopeTests(unittest.TestCase):
    def test_reviewed_clarification_has_no_inferred_impact_and_preserves_audit(self):
        with tempfile.TemporaryDirectory() as directory:
            audit = build_review(Path(directory), "study", "revision", [finding()])
        original = deepcopy(audit)
        projected = project_review(audit, {audit["checks"][0]["id"]: {
            "disposition": "clarification", "reason": "The aggregation scope is unstated."}})
        issue = projected["review"]["issues"][0]
        self.assertEqual(issue["kind"], "gap")
        self.assertEqual(issue["impact"]["status"], "not_measured")
        self.assertEqual(issue["critical"]["status"], "needs_review")
        self.assertEqual(audit, original)

    def test_documentation_coverage_is_separate_from_findings(self):
        with tempfile.TemporaryDirectory() as directory:
            audit = build_review(Path(directory), "study", "revision", [finding()])
        result = project_review(audit, {audit["checks"][0]["id"]: {
            "disposition": "coverage", "reason": "The governing SAP is unavailable."}})
        self.assertEqual(result["review"]["counts"]["issues"], 0)
        self.assertEqual(result["coverage"]["counts"]["issues"], 1)
        self.assertEqual(result["coverage"]["issues"][0]["impact"]["status"], "not_measured")

    def test_direct_metadata_and_probe_share_one_issue_with_complete_evidence(self):
        probe = finding()
        direct = {**deepcopy(probe), "id": "study:ADAE:FLAG:arithmetic_method",
                  "comparison": "dataset_define", "kind": "inconsistent", "rule": None,
                  "spec": {"literal": False}, "evidence": {"dataset_check":
                      probe["evidence"]["probes"][0]["reference"]}}
        with tempfile.TemporaryDirectory() as directory:
            audit = build_review(Path(directory), "study", "revision", [probe, direct])
        result = project_review(audit, complete_decisions(audit))
        self.assertEqual(result["review"]["counts"]["issues"], 1)
        self.assertEqual(result["review"]["counts"]["checks"], 2)
        self.assertEqual(result["review"]["issues"][0]["impact"]["subject_count"], 1)

    def test_documented_copies_and_codelists_need_actual_reference_differences(self):
        for kind in ("copy", "codelist"):
            for differs in (True, False):
                with self.subTest(kind=kind, differs=differs):
                    raw = finding(differ=int(differs))
                    if kind == "copy":
                        raw["evidence"] = {"copy": {"source": "AE.FLAG",
                            "reference": raw["evidence"]["probes"][0]["reference"]}}
                    else:
                        raw["evidence"] = {"codelist": {"oid": "FLAG",
                            "reference": [{"value": "X", "count": 1, "subjects": ["01"]}]
                            if differs else []}}
                    with tempfile.TemporaryDirectory() as directory:
                        audit = build_review(Path(directory), "study", "revision", [raw])
                    self.assertEqual(len(dataset_define_review(audit)["issues"]), int(differs))

    def test_only_observed_literal_define_comparisons_become_findings(self):
        with tempfile.TemporaryDirectory() as directory:
            for changes, retained in [
                ({}, True), ({"path": "study/spec/define/define.xml"}, True),
                ({"differ": 0}, False), ({"reading": "alternative"}, False),
                ({"target": "derived"}, False), ({"verified": False}, False),
                ({"path": "study/spec/source/adrg.pdf"}, False),
                ({"path": "study/spec/define/define-sdtm.xml"}, False),
            ]:
                with self.subTest(changes=changes):
                    audit = build_review(Path(directory), "study", "revision", [finding(**changes)])
                    original = deepcopy(audit)
                    published = dataset_define_review(audit)
                    self.assertEqual(published, audit if retained else {
                        **audit, "issues": [], "checks": [], "evidence": [],
                        "counts": {"issues": 0, "checks": 0, "evidence": 0},
                    })
                    self.assertEqual(audit, original)

    def test_impact_excludes_alternatives_and_derived_comparisons(self):
        raw = finding()
        raw["evidence"]["probes"].append(finding(reading="alternative")["evidence"]["probes"][0])
        raw["evidence"]["probes"][-1]["column"] = "FLAG_OTHER"
        with tempfile.TemporaryDirectory() as directory:
            audit = build_review(Path(directory), "study", "revision", [raw])
        published = dataset_define_review(audit)
        roles = {e["reading"]: t["role"] for t in published["issues"][0]["trace"]
                 for e in published["evidence"] if e["id"] == t["evidence_id"]
                 and e["type"] == "comparison"}
        self.assertEqual(roles, {"literal": "impact", "alternative": "context"})

    def test_document_only_and_context_only_issues_are_not_findings(self):
        with tempfile.TemporaryDirectory() as directory:
            audit = build_review(Path(directory), "study", "revision", [finding()])
        for context_only in (True, False):
            with self.subTest(context_only=context_only):
                review = deepcopy(audit)
                review["issues"][0]["trace"] = [
                    {**t, "role": "context"} for t in review["issues"][0]["trace"]
                    if context_only or next(e for e in review["evidence"]
                                            if e["id"] == t["evidence_id"])["type"] == "document"
                ]
                self.assertEqual(dataset_define_review(review)["issues"], [])
