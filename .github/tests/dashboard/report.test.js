// Issues, check aliases and compact traces share the versioned review contract.
import test from "node:test";
import assert from "node:assert/strict";
import {
  consistencyFindings,
  createReport,
} from "../../../docs/assets/dashboard/report.js";
import {
  findIssue,
  impactText,
  issueRow,
  issueTrace,
  readReview,
  criticalFinding,
  comparisonLabel,
} from "../../../docs/assets/dashboard/issues.js";
import { createShell } from "../../../docs/assets/dashboard/shell.js";
import { esc, link } from "../../../docs/assets/dashboard/ui.js";

const source = {
  id: "source",
  type: "document",
  path: "study/guide.pdf",
  section: "page-5",
  quote: "Use <first> day",
  context: "For partial dates: Use <first> day of the month.",
  url: "https://example/guide.pdf",
  verified: true,
};
const spec = {
  id: "spec",
  type: "specification",
  path: "study/spec.yaml",
  section: "DATE",
  quote: "day: 1",
  context: "- name: DATE\n  day: 1",
  lines: [3, 3],
  context_lines: [2, 3],
  url: "https://example/spec.yaml#L2-L3",
  verified: true,
};
const comparison = {
  id: "comparison",
  type: "comparison",
  method: "probe",
  column: "DATE_LITERAL",
  reading: "literal",
  target: "reference",
  compared: 3,
  differ: 2,
  subjects: ["A", "B"],
  patterns: [
    {
      reference: "<value>",
      observed: null,
      row: "matched",
      count: 2,
      subjects: ["A", "B"],
    },
  ],
};
const checks = ["CR-5", "CR-6"].map((rule) => ({
  id: `study:ADX.DATE.${rule}`,
  dataset: "ADX",
  variable: "DATE",
  kind: "conflict",
  title: "Generic rule title",
  summary: "A rule-level observation.",
  rule: {
    id: rule,
    title: "Rule title",
    statement: "Follow the documented date rule.",
  },
  review: { decision: "agree", reason: "The condition differs." },
  evidence_ids: ["source", "spec", "comparison"],
}));
const issue = {
  id: "study:ADX.DATE.partial-date",
  dataset: "ADX",
  variable: "DATE",
  kind: "conflict",
  comparison: "documented_rules",
  title: "Partial-date rule differs",
  summary: "The specification applies a different date rule.",
  expected: "Use the documented day.",
  observed: "A different day is selected.",
  action: "Confirm and align the intended date rule.",
  check_ids: checks.map((c) => c.id),
  trace: [
    { evidence_id: "source", role: "context" },
    { evidence_id: "spec", role: "context" },
    { evidence_id: "comparison", role: "impact" },
  ],
  impact: { status: "observed", subject_count: 2, subjects: ["A", "B"] },
  review: "agreed",
  critical: { status: "yes", reason: "The date derivation differs." },
};
const report = {
  documents: [{ path: source.path, available: true }],
  review: {
    schema_version: 1,
    issues: [issue],
    checks,
    evidence: [source, spec, comparison],
  },
};
const state = () => ({
  findingSearch: "",
  kind: "",
  comparison: "",
  critical: "",
});

test("synthetic workspaces retain development review without claiming reference agreement", () => {
  const html = createShell({
    model: { id: "kn189", title: "KN189", kind: "synthetic", revision: "commit",
      subjects: ["001", "002"], datasets: [{ name: "ADSL" }],
      development: "synthetic/kn189/catalog.json" },
    state: { view: "datasets" }, site: new URL("https://example.test/project/"),
    REPO: "https://github.com/RConsortium/submissions-pilot7-synthetic-data", esc, link,
  }).frame();
  assert.match(html, /href="https:\/\/example.test\/project\/synthetic\/">All synthetic studies/);
  assert.match(html, /data-view="development"[^>]*>Analysis development/);
  assert.match(html, /No independent published reference/);
  assert.match(html, /Human analysis review pending/);
  assert.doesNotMatch(html, /All pilot studies|published submission package|%/);
});

test("the metric and listing count issues separately from supporting checks", () => {
  assert.deepEqual(consistencyFindings(report), [issue]);
  const html = createShell({
    report,
    model: { metrics: { matched: [1, 2, 3], reference: [1, 2, 3] } },
  }).metrics();
  assert.match(html, /Published ADaM reference agreement/);
  assert.match(html, /<strong>100%<\/strong> of reference datasets matched/);
  assert.match(html, /<strong>1<\/strong> finding awaiting review/);
  assert.match(html, /1 critical; 0 non-critical; 0 needing assessment/);
  assert.match(html, /Findings can remain open even when reference agreement is 100%/);
  const listing = createReport({ report, state: state(), esc }).findingsView();
  assert.match(listing, /1 of 1 issue &middot; 2 supporting checks/);
  assert.equal((listing.match(/<tr class="review-issue"/g) || []).length, 1);
  assert.ok(listing.includes("Issue type"));
  assert.ok(listing.includes("Agent review"));
  assert.ok(!listing.includes('id="issue-review"'));
  assert.match(listing, /Dataset \/ variable<\/th><th scope="col">Impact \/ review<\/th><th scope="col">Issue/);
  assert.match(listing, /<th scope="col">Critical finding<\/th>/);
  assert.ok(listing.includes('<th scope="col">Status</th>'));
  assert.match(listing, /class="issue-status"[^]*?class="status attention">Under Review<\/span>/);
});

test("trace shows selected quotes and comparisons once, with full context and check audit expandable", () => {
  const html = issueTrace(issue, report);
  for (const fragment of [
    "Rule comparison",
    "Expected",
    "Observed",
    "Use &lt;first&gt; day",
    'data-document-section="page-5"',
    "Full context",
    "3</span>  day: 1</mark>",
    "2 / 3 records differ",
    "published reference <code>&lt;value&gt;</code>; documented rule <code>(missing)</code>",
    "2 supporting checks and agent review",
    "Proposed action",
    "Complete check evidence",
  ])
    assert.ok(html.includes(fragment), fragment);
  const primary = html.slice(0, html.indexOf('<details class="issue-checks">'));
  assert.equal(
    (primary.match(/Use &lt;first&gt; day<\/blockquote>/g) || []).length,
    1,
  );
  assert.ok(!html.includes("<value>"));
});

test("closed finding rows defer evidence and an opened trace is populated only once", () => {
  const row = issueRow(issue, report);
  assert.match(row, /Partial-date rule differs/);
  assert.ok(!row.includes("finding-evidence"));
  assert.ok(!row.includes("Use &lt;first&gt; day"));
  let html = "",
    writes = 0;
  const host = {
    dataset: {},
    set innerHTML(value) {
      html = value;
      writes++;
    },
  };
  const details = {
    open: false,
    querySelector: () => host,
    closest: () => ({ dataset: { findingId: issue.id } }),
  };
  const view = createReport({ report, state: state(), esc });
  view.expandTrace(details);
  assert.equal(writes, 0);
  details.open = true;
  view.expandTrace(details);
  assert.equal(writes, 1);
  assert.match(html, /Use &lt;first&gt; day/);
  assert.match(html, /2 \/ 3 records differ/);
  details.open = false;
  view.expandTrace(details);
  details.open = true;
  view.expandTrace(details);
  assert.equal(writes, 1);
});

test("an empty finding search does not serialize complete evidence", () => {
  const data = {
    ...report,
    review: {
      ...report.review,
      evidence: [{
        ...source,
        toJSON() { throw Error("Full evidence was serialized"); },
      }],
    },
  };
  const view = createReport({ report: data, state: state(), esc });
  assert.deepEqual(view.findingItems(), [issue]);
  assert.match(view.findingRows(), /1 of 1 issue/);
});

test("search includes check evidence while type and criticality filter independently", () => {
  const s = state(),
    view = createReport({ report, state: s, esc });
  s.findingSearch = "<first>";
  assert.deepEqual(view.findingItems(), [issue]);
  s.critical = "no";
  assert.deepEqual(view.findingItems(), []);
  s.critical = "yes";
  s.kind = "gap";
  assert.match(view.findingRows(), /No issues match/);
  s.kind = "conflict";
  assert.deepEqual(view.findingItems(), [issue]);
});

test("criticality filters all assessments, preserves long issues and handles older reports", () => {
  const issues = ["yes", "no", "needs_review"].map((status) => ({
    ...issue, id: status, critical: { status, reason: `Assessment: ${status}` },
    summary: "Full issue text. ".repeat(40) + "End of issue.",
  }));
  const data = { ...report, review: { ...report.review, issues } };
  const s = state(), view = createReport({ report: data, state: s, esc });
  for (const item of issues) {
    s.critical = item.critical.status;
    assert.deepEqual(view.findingItems(), [item]);
    assert.ok(view.findingRows().includes(item.summary));
  }
  s.critical = "";
  assert.equal(view.findingItems().length, 3);
  assert.equal(criticalFinding({}).status, "needs_review");
  s.findingSearch = "absent";
  assert.match(view.findingRows(), /colspan="6"/);
});

test("workspace drawer resolves old check links to the issue and uses the same evidence", () => {
  assert.equal(findIssue(report, checks[0].id), issue);
  const host = { innerHTML: "" },
    s = { ...state(), evidence: checks[0].id };
  createReport({
    report,
    state: s,
    esc,
    byId: () => host,
    root: () => ({ classList: { toggle() {} } }),
  }).drawer();
  assert.match(host.innerHTML, /Partial-date rule differs/);
  assert.match(host.innerHTML, /Use &lt;first&gt; day/);
  assert.match(host.innerHTML, /Documented rule vs published reference: 2 subjects differ/);
});

test("an exact variable search excludes mentions in another variable's source context", () => {
  const other = { ...issue, id: "other", variable: "OTHER" };
  const data = {
    ...report,
    review: { ...report.review, issues: [issue, other] },
  };
  const s = { ...state(), findingSearch: "ADX.DATE" };
  assert.deepEqual(
    createReport({ report: data, state: s, esc }).findingItems(),
    [issue],
  );
});

test("unmeasured impact stays distinct from zero observed differences and context is labelled", () => {
  assert.equal(
    impactText({
      ...issue,
      impact: { ...issue.impact, status: "not_measured" },
    }),
    "No issue-specific data comparison",
  );
  assert.equal(
    impactText({
      ...issue,
      impact: { ...issue.impact, status: "not_observed" },
    }, { ...report, review: { ...report.review, evidence: [{ ...comparison, differ: 0, subjects: [], patterns: [] }] } }),
    "Documented rule vs published reference: no differences in tested data",
  );
  const contextual = {
    ...issue,
    trace: [{ evidence_id: "comparison", role: "context" }],
  };
  assert.match(
    issueTrace(contextual, report),
    /Context comparison; excluded from issue impact/,
  );
});

test("impact names each compared pair, deduplicates subjects and excludes context", () => {
  const evidence = [
    comparison,
    { ...comparison, id: "repeat", subjects: ["B", "C"] },
    { ...comparison, id: "derived", target: "derived", subjects: ["D"] },
    { ...comparison, id: "context", subjects: ["Z"] },
  ];
  const item = { ...issue, trace: evidence.map((e) => ({ evidence_id: e.id, role: e.id === "context" ? "context" : "impact" })) };
  const data = { ...report, review: { ...report.review, evidence } };
  assert.equal(impactText(item, data), "Documented rule vs published reference: 3 subjects differ; Documented rule vs yamaa output: 1 subject differs");
  assert.equal(comparisonLabel({ ...comparison, method: "copy" }), "Documented source vs published reference");
  assert.equal(comparisonLabel({ ...comparison, type: "codelist", target: "derived" }), "Documented codelist vs yamaa output");
  assert.match(comparisonLabel({ ...comparison, reading: "corrected" }), /Alternative rule \(DATE_LITERAL\) vs published reference/);
});

test("summary retains unassessed findings, zero findings and unavailable references", () => {
  const data = { ...report, review: { ...report.review, issues: [{ ...issue, critical: undefined }] } };
  const model = { metrics: { matched: [0, 0, 0], reference: [0, 0, 0] } };
  const html = createShell({ report: data, model }).metrics();
  assert.match(html, /No official reference/);
  assert.match(html, /0 critical; 0 non-critical; 1 needing assessment/);
  assert.doesNotMatch(html, /NaN|100%<\/strong>|non-critical; 0 needing assessment/);
  const zero = createShell({ model, report: { ...report, review: { ...report.review, issues: [] } } }).metrics();
  assert.match(zero, /<strong>0<\/strong> findings reported/);
  assert.doesNotMatch(zero, /awaiting review/);
});

test("unsupported or missing review versions fail visibly", () => {
  for (const data of [
    {},
    { ...report, review: { ...report.review, schema_version: 2 } },
  ])
    assert.throws(
      () => readReview(data),
      /Unsupported consistency review schema/,
    );
});
