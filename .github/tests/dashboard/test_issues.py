"""Issue schema boundaries: explicit grouping, evidence attribution and publication integrity."""

from copy import deepcopy
import json
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))
from study_dashboard.issues import build_review, validate_review, validate_shape


def check(suffix, subjects, decision="agree"):
    return {
        "id": f"study:ADSL.V.{suffix}",
        "dataset": "ADSL",
        "variable": "V",
        "comparison": "documented_rules",
        "kind": "conflict",
        "title": "Rule conflict",
        "observation": "The documented rule differs from the reference.",
        "rule": {
            "id": "CR-5",
            "title": "Reference agreement",
            "statement": "Reproduce the reference.",
        },
        "basis_hash": "a" * 64,
        "adjudication": {"decision": decision, "reason": "Reviewed."},
        "documents": [
            {
                "path": "study/SAP.pdf",
                "section": "page-1",
                "quote": "Use V.",
                "context": "Use V.",
                "verified": True,
            }
        ],
        "evidence": {
            "probes": [
                {
                    "column": suffix,
                    "reading": "literal",
                    "reference": {
                        "compared": 10,
                        "differ": len(subjects),
                        "patterns": (
                            [
                                {
                                    "reference": 1,
                                    "observed": 0,
                                    "row": "matched",
                                    "count": len(subjects),
                                    "subjects": subjects,
                                }
                            ]
                            if subjects
                            else []
                        ),
                    },
                }
            ]
        },
    }


def definition(slug, checks, selections):
    return {
        "id": slug,
        "variable": "V",
        "title": "One review decision",
        "summary": "Related observations describe one problem.",
        "expected": "Use the documented rule.",
        "observed": "The rule differs.",
        "action": "Confirm the intended rule.",
        "checks": checks,
        "data": selections,
    }


def select(suffix, role="impact"):
    return {
        "check": f"ADSL.V.{suffix}",
        "kind": "probe",
        "column": suffix,
        "target": "reference",
        "role": role,
    }


class IssueSchemaTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.path = self.root / "study/spec/review/adsl-issues.json"
        self.path.parent.mkdir(parents=True)
        self.checks = [
            check("one", ["A", "B"]),
            check("two", ["B", "C"]),
            check("three", ["Z"], "dispute"),
        ]
        self.declaration = {
            "schema_version": 1,
            "dataset": "ADSL",
            "checks": {f"ADSL.V.{s}": "a" * 64 for s in ("one", "two", "three")},
            "issues": [
                definition(
                    "first",
                    ["ADSL.V.one", "ADSL.V.two"],
                    [select("one"), select("two")],
                ),
                definition(
                    "second",
                    ["ADSL.V.two", "ADSL.V.three"],
                    [select("three", "context")],
                ),
            ],
        }

    def build(self, declaration=None):
        self.path.write_text(json.dumps(declaration or self.declaration))
        return build_review(self.root, "study", "revision", self.checks)

    def test_grouping_is_many_to_many_without_double_counting_subjects_or_sources(self):
        result = self.build()
        first, second = result["issues"]
        self.assertEqual(
            (
                result["counts"],
                first["impact"],
                second["impact"],
                first["review"],
                second["review"],
            ),
            (
                {"issues": 2, "checks": 3, "evidence": 4},
                {"status": "observed", "subject_count": 3, "subjects": ["A", "B", "C"]},
                {"status": "not_measured", "subject_count": 0, "subjects": []},
                "agreed",
                "mixed",
            ),
        )
        self.assertEqual(
            [e["quote"] for e in result["evidence"] if e["type"] == "document"],
            ["Use V."],
        )
        self.assertEqual(len(first["trace"]), 3)

    def test_unmeasured_zero_rows_and_observed_agreement_are_distinct(self):
        self.path.unlink(missing_ok=True)
        zero = check("zero", [])
        empty = deepcopy(zero)
        empty["id"] = "study:ADSL.V.empty"
        empty["evidence"]["probes"][0]["reference"]["compared"] = 0
        unmeasured = deepcopy(zero)
        unmeasured["id"] = "study:ADSL.V.unmeasured"
        unmeasured["evidence"] = {}
        result = build_review(self.root, "study", "revision", [zero, empty, unmeasured])
        self.assertEqual(
            {i["check_ids"][0]: i["impact"]["status"] for i in result["issues"]},
            {
                zero["id"]: "not_observed",
                empty["id"]: "not_measured",
                unmeasured["id"]: "not_measured",
            },
        )

    def test_changed_basis_new_checks_or_removed_checks_stop_publication(self):
        for label in ("basis", "new", "removed"):
            with self.subTest(case=label):
                declaration = deepcopy(self.declaration)
                if label == "basis":
                    declaration["checks"]["ADSL.V.one"] = "b" * 64
                elif label == "new":
                    declaration["checks"]["ADSL.V.new"] = "a" * 64
                else:
                    del declaration["checks"]["ADSL.V.one"]
                with self.assertRaisesRegex(ValueError, "basis|inventory"):
                    self.build(declaration)
        self.checks = []
        with self.assertRaisesRegex(ValueError, "inventory"):
            self.build()

    def test_missing_coverage_wrong_scope_and_invalid_selectors_are_rejected(self):
        for label in (
            "coverage",
            "scope",
            "selector",
            "target",
            "citation",
            "duplicate",
            "unknown field",
            "version",
        ):
            with self.subTest(case=label):
                declaration = deepcopy(self.declaration)
                item = declaration["issues"][0]
                if label == "coverage":
                    declaration["issues"].pop()
                elif label == "scope":
                    item["variable"] = "OTHER"
                elif label == "selector":
                    item["data"][0]["column"] = "absent"
                elif label == "target":
                    item["data"][0]["target"] = "derived"
                elif label == "citation":
                    item["citations"] = [
                        {
                            "check": "ADSL.V.one",
                            "type": "document",
                            "section": "page-99",
                        }
                    ]
                elif label == "duplicate":
                    declaration["issues"].append(deepcopy(item))
                elif label == "unknown field":
                    item["guess"] = "Group by similar words"
                else:
                    declaration["schema_version"] = 2
                with self.assertRaises(ValueError):
                    self.build(declaration)

    def test_output_references_counts_attribution_and_review_are_validated(self):
        original = self.build()
        for label in (
            "count",
            "check",
            "evidence",
            "impact",
            "review",
            "trace",
            "identity",
        ):
            with self.subTest(case=label):
                result = deepcopy(original)
                i = result["issues"][0]
                if label == "count":
                    result["counts"]["issues"] += 1
                elif label == "check":
                    i["check_ids"].append("absent")
                elif label == "evidence":
                    i["trace"][0]["evidence_id"] = "absent"
                elif label == "impact":
                    i["impact"]["subject_count"] = 99
                elif label == "review":
                    i["review"] = "agreed" if i["review"] != "agreed" else "disputed"
                elif label == "trace":
                    i["trace"].append({**i["trace"][0], "role": "impact"})
                else:
                    result["evidence"][0]["quote"] = "Changed"
                with self.assertRaises(ValueError):
                    validate_review(result)

    def test_evidence_links_do_not_change_content_identity_and_old_versions_fail(self):
        result = self.build()
        ids = [e["id"] for e in result["evidence"]]
        self.checks[0]["documents"][0][
            "repository"
        ] = "https://example/new-revision/SAP.pdf"
        self.assertEqual([e["id"] for e in self.build()["evidence"]], ids)
        with self.assertRaises(ValueError):
            validate_shape("report", {**result, "schema_version": 2})

    def test_execution_success_does_not_create_a_review_issue(self):
        executed = {**check("execution", []), "kind": "executed"}
        result = build_review(self.root, "study", "revision", [executed])
        self.assertEqual(result["counts"], {"issues": 0, "checks": 0, "evidence": 0})

    def test_generated_spec_summaries_are_not_quoted_as_literal_source(self):
        for literal in (False, True):
            with self.subTest(literal=literal):
                finding = check("metadata", [])
                finding["rule"] = None
                finding["evidence"] = {}
                finding["spec"] = {
                    "path": "study/spec.yaml",
                    "line": 10,
                    "literal": literal,
                    "excerpt": "- name: V\n  derivation: DM.V",
                }
                result = build_review(self.root, "study", "revision", [finding])
                spans = [
                    e["context_lines"]
                    for e in result["evidence"]
                    if e["type"] == "specification"
                ]
                self.assertEqual(spans, [[10, 11]] if literal else [])


if __name__ == "__main__":
    unittest.main()
