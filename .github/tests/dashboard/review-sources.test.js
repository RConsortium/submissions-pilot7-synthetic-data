import test from "node:test";
import assert from "node:assert/strict";
import { resolvedReviewReport, sourcePreview, reviewComparison, reviewComparisonEvidence } from "../../../docs/assets/dashboard/review-sources.js";

const original = { id: "rule", type: "specification", path: "spec/template.yaml", section: "AGE",
  quote: "obsolete rule", context: "original", lines: [100, 101], verified: true };
const probe = { ...original, id: "probe", path: "study/spec/review/age.yaml" };
const report = { review: { evidence: [original, probe], issues: [{ basis_hash: "unchanged" }] },
  documents: [{ name: "define.xml", path: "study/define.xml", available: true, view: "documents/define.html" },
    { name: "sap.pdf", path: "study/sap.pdf", available: true, original: "documents/sap.pdf" }] };
const specifications = Object.fromEntries(["ADAE", "ADSL"].map((domain) => [domain, {
  domain, path: `study/${domain}.yaml`, documents: [{ path: original.path, text: "original" }],
  resolved: { path: `study/resolved/${domain}.yaml`, text: `domain: ${domain}\n- name: AGE\n  derivation: 'age < 65'\n`,
    lineage: { spans: { AGE: { start: 2, end: 3 } } } },
}]));

test("the first panel pairs only the identified Define-XML item and resolved variable", () => {
  const doc = { id: "define", type: "document", path: "study/spec/define/define-adam.xml",
    section: "ADSL.AGE", quote: "Define age rule", context: "Define age rule", verified: true };
  const adrg = { ...doc, id: "adrg", path: "study/spec/source/adrg.pdf", quote: "Guide rule" };
  const data = { ...report, review: { ...report.review, evidence: [doc, adrg, original, probe] } };
  const issue = { dataset: "ADSL", variable: "AGE", trace: data.review.evidence.map((e) => ({ evidence_id: e.id })) };
  const entries = reviewComparisonEvidence(issue, data, specifications);
  assert.deepEqual(entries.map((e) => [e.type, e.path]), [
    ["document", doc.path], ["specification", "study/resolved/ADSL.yaml"],
  ]);
  const html = reviewComparison(issue, data, specifications);
  assert.equal((html.match(/class="trace-source-file"/g) || []).length, 2);
  assert.match(html, /Define age rule/);
  assert.match(html, /age &lt; 65/);
  assert.doesNotMatch(html, /Guide rule|adrg.pdf|obsolete rule|domain: ADAE/);
  assert.match(reviewComparison(issue, data, {}), /resolved YAML item is unavailable/);
});

test("review shows the selected dataset's resolved rule while preserving independent translations and audit identity", () => {
  const shown = resolvedReviewReport(report, specifications, "ADSL");
  assert.deepEqual(shown.review.evidence[0], { ...original, path: "study/resolved/ADSL.yaml",
    quote: "- name: AGE\n  derivation: 'age < 65'", context: "- name: AGE\n  derivation: 'age < 65'",
    lines: [2, 3], context_lines: [2, 3], url: "" });
  assert.equal(shown.review.evidence[1], probe);
  assert.equal(shown.review.issues, report.review.issues);
  assert.equal(report.review.evidence[0], original);
  assert.deepEqual(resolvedReviewReport(report, {}, "ADSL"), report);
});

test("source previews use rendered XML, PDF pages and escaped complete YAML with resolved line numbers", () => {
  const resource = (path) => "/project/study/" + path;
  const xml = sourcePreview({ path: "study/define.xml", section: "ADSL.AGE" }, report, specifications, resource);
  assert.match(xml, /src="\/project\/study\/documents\/define.html#ADSL.AGE" sandbox="allow-scripts"/);
  const pdf = sourcePreview({ path: "study/sap.pdf", section: "page-5" }, report, specifications, resource);
  assert.match(pdf, /sap.pdf#page=5/);
  assert.doesNotMatch(pdf, /sandbox=/);
  const rule = resolvedReviewReport(report, specifications, "ADSL").review.evidence[0];
  const yaml = sourcePreview(rule, report, specifications, resource);
  assert.match(yaml, /domain: ADSL/);
  assert.match(yaml, /<mark class="context-line"><span class="context-line-number" aria-hidden="true">2/);
  assert.match(yaml, /age &lt; 65/);
  assert.doesNotMatch(yaml, /Only the retained citation/);
  assert.match(sourcePreview(probe, report, specifications, resource), /Only the retained citation context/);
});
