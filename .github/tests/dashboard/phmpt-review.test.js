// PHMPT review page (docs/assets/phmpt/review.js): filtering findings, finding their record,
// and the pre-filled discussion. Seam: the module's pure functions; the evidence below is invented.
import test from "node:test";
import assert from "node:assert/strict";
import { AGREEMENTS, discussionLink, evidenceRows, filterFindings, findingRecord, reviewBody } from "../../../docs/assets/phmpt/review.js";

const evidence = {
  schema_version: 1,
  meta: { yamaa_commit: "abc1234", source_commit: "def567890123", collected: "2026-01-01" },
  gaps: { "repeated-order": { title: "Repeated codelist `OrderNumber`", yamaa_issue: 1 } },
  studies: { s: { title: "Study S", sponsor: "X", product: "Y", cuts: { c1: {
    title: "Cut 1", application: "1", sequence: "S1", over: null,
    datasets: [{ dataset: "ADXX", verdict: "exact" }],
    define: { verdict: "MATCH", received: 10, identical: 9, gap_only: 1, no_spec: 0 } } } } },
  findings: [
    { id: "phmpt/s/c1/ADXX", kind: "dataset", study: "s", cut: "c1", dataset: "ADXX", verdict: "exact",
      claim: "ADXX reproduces the submitted dataset cell for cell.", page: "findings/s/#c1", reproduce: [] },
    { id: "phmpt/s/c1/define/repeated-order", kind: "define-defect", study: "s", cut: "c1", dataset: null,
      verdict: "submitted-define defect", claim: "1 define difference comes from a defect of the submitted define.",
      page: "findings/s/#c1", reproduce: [] },
  ],
};
const page = "https://example.org/site/phmpt/review/?x=1#old";
const review = { agreement: "disagree", comment: "  Checked ADXX.  " };
const destination = "https://github.com/org/repo/discussions/new?category=general";

test("each filter narrows the findings, and text matches id, claim or verdict", () => {
  const cases = [
    [{}, ["phmpt/s/c1/ADXX", "phmpt/s/c1/define/repeated-order"], "no filter"],
    [{ kind: "define-defect" }, ["phmpt/s/c1/define/repeated-order"], "kind"],
    [{ verdict: "exact" }, ["phmpt/s/c1/ADXX"], "verdict"],
    [{ study: "other" }, [], "study"],
    [{ text: " Repeated-ORDER " }, ["phmpt/s/c1/define/repeated-order"], "text in the id, trimmed, any case"],
    [{ text: "CELL FOR CELL" }, ["phmpt/s/c1/ADXX"], "text in the claim"],
  ];
  for (const [filters, ids, label] of cases)
    assert.deepEqual(filterFindings(evidence.findings, filters).map((f) => f.id), ids, label);
});

test("a dataset finding reads its dataset row and a define finding its cut's define", () => {
  assert.equal(findingRecord(evidence, evidence.findings[0]), evidence.studies.s.cuts.c1.datasets[0]);
  assert.equal(findingRecord(evidence, evidence.findings[1]), evidence.studies.s.cuts.c1.define);
  assert.equal(findingRecord(evidence, { ...evidence.findings[0], cut: "missing" }), null);
});

test("the discussion carries the finding, the assessment and the evidence revision", () => {
  const link = discussionLink(destination, evidence, evidence.findings[0], review, page);
  const url = new URL(link.url);
  assert.equal(url.origin + url.pathname, "https://github.com/org/repo/discussions/new");
  assert.equal(url.searchParams.get("category"), "general");
  assert.equal(url.searchParams.get("title"), "PHMPT review: phmpt/s/c1/ADXX - Disagree");
  assert.equal(url.searchParams.get("body"), [
    "## PHMPT review: `phmpt/s/c1/ADXX`", "", "**Assessment:** Disagree", "", "Checked ADXX.", "",
    "**Claim:** ADXX reproduces the submitted dataset cell for cell.",
    "**Verdict reported:** exact",
    "**Evidence:** yamaa `abc1234`, results at `def567890123`, collected 2026-01-01",
    "[Open the finding](https://example.org/site/phmpt/review/#phmpt/s/c1/ADXX)", "",
    "_Do not paste rows, subject identifiers or program text from PHMPT files; describe the difference instead._",
  ].join("\n"));
  assert.equal(link.prefilled, true);
});

test("no assessment, or a destination that is not a discussion composer, opens nothing", () => {
  assert.deepEqual(Object.keys(AGREEMENTS), ["agree", "disagree", "clarify"]);
  assert.throws(() => reviewBody(evidence, evidence.findings[0], { agreement: "", comment: "" }, page), /Choose Agree/);
  assert.throws(() => discussionLink("https://github.com/org/repo/issues/new", evidence, evidence.findings[0], review, page),
    /discussions\/new/);
});

test("an assessment too long for a link opens the composer with the title only", () => {
  const long = { agreement: "agree", comment: "x".repeat(9000) };
  const link = discussionLink(destination, evidence, evidence.findings[0], long, page);
  assert.equal(link.prefilled, false);
  assert.equal(new URL(link.url).searchParams.get("body"), null);
  assert.ok(link.body.includes("x".repeat(9000)));
});

test("a dataset's evidence shows its submitted-file defect and note, and only when present", () => {
  const base = { rows: 2, cols: 3, out_rows: 2, out_cols: 3, cells: 6, mismatched_cells: 1,
    mismatched_columns: { AENDY: 1 }, redacted_columns: {}, carried_columns: [], missing_columns: [],
    missing_input: null, submitted_defect: null, note: null, reasons: [], unexplained_columns: [],
    spec: "s/c1/adxx.yaml", spec_lines: 9, layers: ["s/c1/adxx.yaml"], source: null };
  const plain = evidenceRows(evidence, evidence.findings[0], base);
  assert.ok(!plain.includes("Submitted-file defect") && !plain.includes(">Note<"));
  const html = evidenceRows(evidence, evidence.findings[0], { ...base,
    submitted_defect: { defect: "The submitted cell holds its value three times", reason: "Invented <reason>.",
      decided: "2026-01-01", columns: ["AENDY"], cells: { AENDY: 1 } },
    note: "The program & the file disagree." });
  assert.match(html, /<th scope="row">Submitted-file defect<\/th><td>The submitted cell holds its value three times\. Invented &lt;reason&gt;\. <code>AENDY<\/code> 1<\/td>/);
  assert.match(html, /<th scope="row">Note<\/th><td>The program &amp; the file disagree\.<\/td>/);
});
