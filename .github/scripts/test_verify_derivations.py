"""Consistency review: quotes, rules, verdicts and adjudication are decided, not trusted."""

import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

import consistency_report as cr
import verify_derivations as vd
from study_dashboard.lineage import source_locations

SECTION = "Label: Date of First Exposure to Treatment\nData type: integer\nComment: SV.SVSTDTC when SV.VISITNUM=3,\n converted to SAS date"
DEFINE = "spec/define/define-adam.xml"
INDEX = {DEFINE: {"ADSL.TRTSDT": {"id": "ADSL.TRTSDT", "title": "ADSL.TRTSDT / ADSL.TRTSDT", "text": SECTION}}}
SPEC = """columns:
  - name: EX_MINDTC
    derivation:
      aggregate: "MIN(EX.EXSTDTC)"
  - name: TRTSDT
    derivation:
      impute:
        type: date
        source: EX_MINDTC
        month: 1
        day: 1
"""
RULES = vd.load_rules()


def spec_file():
    return {"path": "s/adsl.yaml", "lines": SPEC.splitlines(), "spans": source_locations(SPEC)["spans"], "keys": ["USUBJID"], "revision": "r"}


def probe(differ, column="X"):
    return {"column": column, "reading": "literal", "reference": {"compared": 3, "differ": differ, "patterns": []}}


def rule(citations=(True,), probes=(), relations=("same",), documented=True):
    return {
        "check": "rule",
        "documented": documented,
        "citations": [{"verified": v} for v in citations],
        "clauses": [{"relation": r} for r in relations],
        "probes": list(probes),
    }


def trtsdt(clauses, probes):
    citation = {"document": DEFINE, "section": "ADSL.TRTSDT", "quote": "SV.SVSTDTC when SV.VISITNUM=3, converted to SAS date"}
    return {
        "dataset": "ADSL",
        "variable": "TRTSDT",
        "label": "Date of First Exposure to Treatment",
        "check": "rule",
        "citations": [vd.verify_citation(INDEX, citation)],
        "clauses": clauses,
        "probes": probes,
        "define": {"comment": "", "text": SECTION},
    }


class CitationTests(unittest.TestCase):
    def test_a_quote_counts_only_verbatim_in_its_cited_section(self):
        cases = [
            ("whitespace differs", "ADSL.TRTSDT", "SV.SVSTDTC when SV.VISITNUM=3, converted to   SAS date", True, None),
            ("word changed", "ADSL.TRTSDT", "SV.SVSTDTC when SV.VISITNUM=1", False, "quote not found in the cited section"),
            ("other section", "ADSL.TRTEDT", "SV.SVSTDTC when SV.VISITNUM=3", False, "document or section not retained"),
        ]
        for label, section, quote, verified, reason in cases:
            with self.subTest(case=label):
                result = vd.verify_citation(INDEX, {"document": DEFINE, "section": section, "quote": quote})
                self.assertEqual((result["verified"], result["reason"]), (verified, reason), label)

    def test_a_specification_quote_is_found_inside_its_element_and_located_to_lines(self):
        cases = [
            ("one line", "EX_MINDTC", "MIN(EX.EXSTDTC)", (True, [4, 4], None)),
            ("across lines", "TRTSDT", "month: 1 day: 1", (True, [10, 11], None)),
            ("in another element", "EX_MINDTC", "month: 1", (False, None, "quote not found in specification element EX_MINDTC")),
            ("no such element", "TRTEDT", "month: 1", (False, None, "specification element TRTEDT not found")),
        ]
        for label, element, quote, expected in cases:
            with self.subTest(case=label):
                side = vd.spec_side(spec_file(), element, quote)
                self.assertEqual((side["verified"], side["lines"], side["reason"]), expected, label)


    def test_a_layered_element_is_read_only_in_the_layer_that_defines_it(self):
        entry = "columns:\n  - name: TRTSDT\n    label: Treatment start\n    derivation: EX_MINDTC\n"
        layered = {**spec_file(), "path": "s/adsl.yaml", "lines": entry.splitlines(),
                   "spans": source_locations(entry)["spans"],
                   "elements": {"TRTSDT": {"path": "spec/yamaa/adsl.yaml", "lines": SPEC.splitlines(),
                                           "span": source_locations(SPEC)["spans"]["TRTSDT"]}}}
        cases = [
            ("rule in its defining layer", "month: 1 day: 1", (True, "spec/yamaa/adsl.yaml", [10, 11])),
            ("text only in another layer", "derivation: EX_MINDTC", (False, "spec/yamaa/adsl.yaml", None)),
        ]
        for label, quote, expected in cases:
            with self.subTest(case=label):
                side = vd.spec_side(layered, "TRTSDT", quote)
                self.assertEqual((side["verified"], side["path"], side["lines"]), expected, label)


class FindingTests(unittest.TestCase):
    def test_each_clause_relation_becomes_a_finding_under_its_rule_with_both_quotes(self):
        clauses = [
            {"relation": "differs", "document": {"citation": 1, "quote": "SV.SVSTDTC when SV.VISITNUM=3"}, "spec": {"element": "EX_MINDTC", "quote": "MIN(EX.EXSTDTC)"}},
            {"relation": "same", "document": {"citation": 1, "quote": "converted to SAS date"}, "spec": {"element": "TRTSDT", "quote": "type: date"}},
            {"relation": "absent_in_document", "spec": {"element": "TRTSDT", "quote": "month: 1 day: 1"}},
            {"relation": "absent_in_spec", "document": {"citation": 1, "quote": "VISITNUM=4"}},
        ]
        record = trtsdt(clauses, [probe(0, "TRTSDT")])
        vd.verify_clauses(record, spec_file())
        record["verdict"] = vd.verdict(record)
        findings = vd.variable_findings(record, RULES, spec_file(), None)
        self.assertEqual(
            (record["verdict"], [(f["id"], f["rule"]["id"], f["summary"], (f["variable_spec"] or {}).get("element")) for f in findings]),
            (
                "missing_evidence",
                [
                    ("ADSL.TRTSDT.CR-6.1", "CR-6", 'Define-XML ADSL.TRTSDT states "SV.SVSTDTC when SV.VISITNUM=3"; the specification states "MIN(EX.EXSTDTC)" in EX_MINDTC.', "TRTSDT"),
                    ("ADSL.TRTSDT.CR-7.3", "CR-7", 'The specification states "month: 1 day: 1" in TRTSDT; no retained document states it.', None),
                    ("ADSL.TRTSDT.CR-1.c4", "CR-1", "Clause 4 quotes text not found where it is cited: clause quote not found in its citation.", None),
                ],
            ),
            "same is no finding; an unverified clause is CR-1 and blocks the verdict",
        )

    def test_a_documented_rule_that_misses_the_reference_names_the_reading_that_resolves_it(self):
        reading = {**probe(0, "TRTSDT__VISIT_4"), "reading": "Visit 4."}
        record = trtsdt([], [probe(2, "TRTSDT"), reading])
        vd.verify_clauses(record, spec_file())
        record["verdict"] = vd.verdict(record)
        [finding] = vd.variable_findings(record, RULES, spec_file(), None)
        self.assertEqual(
            (record["verdict"], finding["id"], finding["severity"], finding["summary"], finding["basis"]),
            (
                "resolved_by_reading",
                "ADSL.TRTSDT.CR-5",
                "conflict",
                "The documented rule, run as written, differs from the reference on 2 of 3 records; reading TRTSDT__VISIT_4 reproduces the reference.",
                'CR-5 | states spec/define/define-adam.xml#ADSL.TRTSDT: "SV.SVSTDTC when SV.VISITNUM=3, converted to SAS date"'
                ' | spec TRTSDT text: "- name: TRTSDT derivation: impute: type: date source: EX_MINDTC month: 1 day: 1"'
                ' | evidence {"probes": [{"column": "TRTSDT", "reading": "literal", "reference": {"compared": 3, "differ": 2, "patterns": []}},'
                ' {"column": "TRTSDT__VISIT_4", "reading": "Visit 4.", "reference": {"compared": 3, "differ": 0, "patterns": []}}]}'
                " | probes TRTSDT, TRTSDT__VISIT_4",
            ),
            "CR-5 cites every quote of the rule, the variable's definition and both probes with their results",
        )

    def test_the_basis_changes_with_the_evidence_but_not_with_a_link(self):
        side = {"role": "states", "document": DEFINE, "section": "ADSL.TRTSDT", "quote": "VISITNUM=3"}
        spec = vd.spec_side(spec_file(), "TRTSDT", "month: 1")
        evidence = {"probes": [{"column": "TRTSDT", "definition": {"excerpt": "SV3.SVSTDTC", "url": "u1"}, "reference": {"differ": 2}}]}
        moved = {"probes": [{"column": "TRTSDT", "definition": {"excerpt": "SV3.SVSTDTC", "url": "u2"}, "reference": {"differ": 2}}]}
        rewritten = {"probes": [{"column": "TRTSDT", "definition": {"excerpt": "SV4.SVSTDTC", "url": "u1"}, "reference": {"differ": 2}}]}
        result = {"probes": [{"column": "TRTSDT", "definition": {"excerpt": "SV3.SVSTDTC", "url": "u1"}, "reference": {"differ": 5}}]}
        original = vd.basis("CR-5", [side], spec, evidence)
        self.assertEqual(
            [vd.basis("CR-5", [side], spec, e) == original for e in (moved, rewritten, result)],
            [True, False, False],
            "a new revision in a link keeps the decision; a changed probe or result makes it stale",
        )

    def test_a_decision_applies_only_to_the_finding_it_judged(self):
        findings = [{"id": "A", "basis": "a"}, {"id": "B", "basis": "b changed"}, {"id": "C", "basis": "c"}]
        decisions = {
            "A": {"finding": "A", "basis": "a", "decision": "agree", "reason": "Right."},
            "B": {"finding": "B", "basis": "b", "decision": "dispute", "reason": "Wrong."},
            "D": {"finding": "D", "basis": "d", "decision": "agree", "reason": "Gone."},
        }
        orphaned = vd.adjudicate(findings, {"decisions": decisions})
        self.assertEqual(
            ([f["adjudication"] for f in findings], orphaned),
            (
                [
                    {"decision": "agree", "reason": "Right."},
                    {"decision": "stale", "previous": "dispute", "reason": "Wrong."},
                    {"decision": "pending"},
                ],
                ["D"],
            ),
            "agreed, stale after a change, pending, and a decision for a removed finding",
        )

    def test_compact_decisions_bind_the_full_basis_and_do_not_trust_a_reported_fingerprint(self):
        # SHA-256 of the UTF-8 text "a", independent of the production helper.
        digest = "sha256:ca978112ca1bbdcafac231b39a23dc4da786eff8147c4e72b9807785afee48bb"
        findings = [
            {"id": "legacy", "basis": "a"},
            {"id": "compact", "basis": "a"},
            {"id": "changed", "basis": "b", "basis_fingerprint": digest},
            {"id": "malformed", "basis": "a"},
        ]
        decisions = {
            name: {"finding": name, "basis": value, "decision": "agree", "reason": "Checked the sources."}
            for name, value in (
                ("legacy", "a"), ("compact", digest),
                ("changed", digest), ("malformed", digest[:-1]),
            )
        }
        self.assertEqual(vd.fingerprint_basis("a"), digest)
        self.assertEqual(vd.adjudicate(findings, {"decisions": decisions}), [])
        self.assertEqual(
            [finding["adjudication"]["decision"] for finding in findings],
            ["agree", "agree", "stale", "stale"],
        )
        self.assertEqual(
            [finding["adjudication"]["reason"] for finding in findings],
            ["Checked the sources."] * 4,
        )


    def test_an_uncited_statement_keeps_the_adjudicators_reason_beside_its_quote_check(self):
        statements = [
            {"variable": "TRTSDT", "document": DEFINE, "section": "ADSL.TRTSDT", "quote": "VISITNUM=3", "reason": "Names visit 3."},
            {"variable": "TRTSDT", "document": DEFINE, "section": "ADSL.TRTSDT", "quote": "VISITNUM=4", "reason": "Names visit 4."},
        ]
        result = vd.missed_statements(statements, INDEX, lambda s: {})
        self.assertEqual(
            [(m["reason"], m["verified"], m["not_found"]) for m in result],
            [("Names visit 3.", True, None), ("Names visit 4.", False, "quote not found in the cited section")],
            "the verification result must not replace the adjudicator's reason",
        )


class VerdictTests(unittest.TestCase):
    def test_each_verdict_follows_from_citations_probes_and_clauses(self):
        copy = lambda status, differ=0, matches=True: {
            "check": "copy",
            "copy": {"status": status, "spec_matches": matches, "reference": {"differ": differ}},
        }
        cases = [
            ("copy agrees", copy("checked"), "consistent"),
            ("copy read elsewhere", copy("checked", matches=False), "equivalent_on_data"),
            ("copy differs", copy("checked", differ=2), "conflict"),
            ("copy names a missing variable", copy("source_variable_missing"), "conflict"),
            ("copy source not unique", copy("not_checkable"), "not_probed"),
            ("rule nobody cited", rule(citations=()), "not_reviewed"),
            ("no rule in any document", rule(citations=(), documented=False), "document_silent"),
            ("one quote unverified", rule(citations=(True, False), probes=[probe(0)]), "missing_evidence"),
            ("cited, no probe", rule(), "not_probed"),
            ("literal agrees, same clauses", rule(probes=[probe(0)]), "consistent"),
            ("literal agrees, clause differs", rule(probes=[probe(0)], relations=("same", "differs")), "equivalent_on_data"),
            ("reading resolves", rule(probes=[probe(4), probe(0)]), "resolved_by_reading"),
            ("no reading resolves", rule(probes=[probe(4), probe(1)]), "conflict"),
        ]
        for label, record, expected in cases:
            with self.subTest(case=label):
                self.assertEqual(vd.verdict(record), expected, label)

    def test_only_an_unqualified_consistent_rule_leaves_the_human_queue(self):
        cases = [
            ("clean", {"verdict": "consistent"}, "checks_agree"),
            ("interpretation", {"verdict": "consistent", "interpretations": ["ENDDT is RFENDT."]}, "needs_human"),
            ("question", {"verdict": "consistent", "question": "Which month?"}, "needs_human"),
            ("codelist", {"verdict": "consistent", "codelist": {"status": "values_outside_codelist"}}, "needs_human"),
            ("dictionary", {"verdict": "consistent", "codelist": {"status": "external_dictionary"}}, "checks_agree"),
            ("equivalent", {"verdict": "equivalent_on_data"}, "needs_human"),
        ]
        for label, record, expected in cases:
            with self.subTest(case=label):
                self.assertEqual(vd.review_status(record), expected, label)


class SourceTests(unittest.TestCase):
    def test_a_plain_copy_resolves_through_intermediates_to_its_input_file(self):
        spec = {
            "input": {"AE": {"path": "../../data/sdtm/ae.parquet"}, "ADSL": {"path": "../../data/adam/adsl-yamaa.parquet"}},
            "intermediates": [{"id": "ADSL_SBJ", "dataset": "ADSL"}, {"id": "SUBJ", "dataset": "ADSL_SBJ"}],
        }
        cases = [
            ("intermediate chain", "SUBJ.AGE", "ADSL.AGE"),
            ("base input", "AE.AETERM", "AE.AETERM"),
            ("expression", "FLOOR(ADSL_SBJ.AGE)", None),
            ("operation", {"mapping": {"source": "AE.AESEV"}}, None),
        ]
        for label, derivation, expected in cases:
            with self.subTest(case=label):
                self.assertEqual(vd.resolve_source(spec, derivation), expected, label)


class CodelistTests(unittest.TestCase):
    def test_coded_values_compare_as_published_and_dictionaries_are_not_enumerated(self):
        cases = [
            ("integer dose", 54.0, "54"),
            ("float noise", 1.2000000000000002, "1.2"),
            ("padded text", "Y\u00a0", "Y"),
        ]
        for label, value, expected in cases:
            with self.subTest(case=label):
                self.assertEqual(vd.code_text(value), expected, label)
        meddra = {"Dictionary": "MedDRA", "Version": "8.0"}
        self.assertEqual(
            vd.codelist_check({"codelist": {"oid": "AEDICT", "items": [], "external": meddra}}, {}, "AEDECOD", "USUBJID"),
            {"oid": "AEDICT", "external": meddra, "status": "external_dictionary"},
            "an external dictionary is not checked value by value",
        )


class ClaimsTests(unittest.TestCase):
    def test_a_malformed_claim_is_refused_before_any_verdict(self):
        clause = {"relation": "differs", "document": {"citation": 1, "quote": "VISITNUM=3"}, "spec": {"element": "EX_MINDTC", "quote": "MIN"}}
        good = {"variable": "TRTSDT", "citations": [{"document": DEFINE, "section": "ADSL.TRTSDT", "quote": "VISITNUM=3"}], "clauses": [clause], "probes": [{"column": "TRTSDT", "reading": "literal"}]}
        cases = [
            ("reading first", {**good, "probes": [{"column": "TRTSDT", "reading": "visit 3"}]}, "must state its literal reading first"),
            ("probe not produced", {**good, "probes": [{"column": "OTHER", "reading": "literal"}]}, "probe column OTHER is not produced"),
            ("unknown relation", {**good, "clauses": [{**clause, "relation": "similar"}]}, "clause 1 relation 'similar'"),
            ("side missing", {**good, "clauses": [{"relation": "differs", "document": clause["document"]}]}, r"clause 1 \(differs\) needs exactly \['document', 'spec'\]"),
            ("no such citation", {**good, "clauses": [{**clause, "document": {"citation": 2, "quote": "x"}}]}, "clause 1 document names no citation"),
            ("nothing to run", {**good, "probes": []}, "needs probes or a not_probed_reason"),
        ]
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "adsl-claims.json"
            for label, claim, message in cases:
                with self.subTest(case=label):
                    path.write_text(json.dumps({"schema_version": 2, "claims": [claim]}))
                    with self.assertRaisesRegex(ValueError, message, msg=label):
                        vd.load_claims(path, {"TRTSDT"})


class RenderTests(unittest.TestCase):
    def test_the_clause_is_marked_inside_its_citation_and_document_characters_stay_literal(self):
        cases = [
            ("inside", "Normal if . < BMIBL <25.  Obese if BMIBL >=30", "Obese if BMIBL >=30", r"Normal if . \< BMIBL \<25. **Obese if BMIBL \>=30**"),
            ("whole quote", "WEIGHTBL / ((HEIGHTBL*100)**2)", "WEIGHTBL / ((HEIGHTBL*100)**2)", r"WEIGHTBL / ((HEIGHTBL\*100)\*\*2)"),
        ]
        for label, context, quote, expected in cases:
            with self.subTest(case=label):
                self.assertEqual(cr.highlight(context, quote), expected, label)

    def test_a_quoted_element_the_specification_no_longer_declares_renders_as_not_found(self):
        side = vd.spec_side(spec_file(), "EVTSRC", "ADAE.AOCC01FL = 'Y'")
        self.assertEqual(cr.spec_block(side, None), [
            "**Specification says** `ADAE.AOCC01FL = 'Y'` in `EVTSRC` (`s/adsl.yaml`)",
            "",
            "Not found: specification element EVTSRC not found.",
            "",
        ])

    def test_quoted_specification_lines_carry_a_mark(self):
        side = vd.spec_side(spec_file(), "TRTSDT", "month: 1 day: 1")
        self.assertEqual(
            cr.excerpt(side, side["lines"]),
            [
                "```text",
                " 5     - name: TRTSDT",
                " 6       derivation:",
                " 7         impute:",
                " 8           type: date",
                " 9           source: EX_MINDTC",
                "10 >         month: 1",
                "11 >         day: 1",
                "```",
            ],
            "the quote spans lines 10 and 11",
        )


@unittest.skipUnless(importlib.util.find_spec("polars"), "polars is installed with a study's engine requirements")
class CompareTests(unittest.TestCase):
    def test_differences_are_grouped_by_value_pair_with_their_subjects(self):
        import polars as pl

        keys = ["USUBJID"]
        reference = pl.DataFrame({"USUBJID": ["1", "2", "3", "4", "5"], "V": [1.0, None, 2.0, 3.0, 3.0]})
        observed = pl.DataFrame({"USUBJID": ["1", "2", "3", "4", "6"], "P": [1.0 + 1e-12, None, 2.5, 4.0, 9.0]})
        values = [
            {"reference": 2.0, "observed": 2.5, "row": "matched", "count": 1, "subjects": ["3"]},
            {"reference": 3.0, "observed": 4.0, "row": "matched", "count": 1, "subjects": ["4"]},
            {"reference": 3.0, "observed": None, "row": "absent", "count": 1, "subjects": ["5"]},
        ]
        cases = [
            ("a probe's extra record differs", True, {"compared": 6, "differ": 4, "patterns": values + [{"reference": None, "observed": 9.0, "row": "extra", "count": 1, "subjects": ["6"]}]}),
            ("a copy source may hold more records", False, {"compared": 5, "differ": 3, "patterns": values}),
        ]
        for label, extra_rows, expected in cases:
            with self.subTest(case=label):
                self.assertEqual(vd.compare(reference, observed, keys, "V", "P", "USUBJID", extra_rows), expected, label)

    def test_null_and_empty_text_stay_distinct(self):
        import polars as pl

        reference = pl.DataFrame({"USUBJID": ["1", "2"], "V": ["", "Y"]})
        observed = pl.DataFrame({"USUBJID": ["1", "2"], "P": [None, "Y"]})
        result = vd.compare(reference, observed, ["USUBJID"], "V", "P", "USUBJID")
        self.assertEqual(
            (result["differ"], result["patterns"][0]["reference"], result["patterns"][0]["observed"]),
            (1, "", None),
            "the CDISC Pilot 01 policy keeps null and empty text distinct",
        )


if __name__ == "__main__":
    unittest.main()
