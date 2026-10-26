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
  readReview,
} from "../../../docs/assets/dashboard/issues.js";
import { createShell } from "../../../docs/assets/dashboard/shell.js";
import { esc } from "../../../docs/assets/dashboard/ui.js";

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
  reviewStatus: "",
});

test("the metric and listing count issues separately from supporting checks", () => {
  assert.deepEqual(consistencyFindings(report), [issue]);
  const html = createShell({
    report,
    model: { metrics: { matched: [1, 2, 3], reference: [1, 2, 3] } },
  }).metrics();
  assert.match(html, /Consistency:<\/strong> 1 issue/);
  const listing = createReport({ report, state: state(), esc }).findingsView();
  assert.match(listing, /1 of 1 issue &middot; 2 supporting checks/);
  assert.equal((listing.match(/<tr class="review-issue"/g) || []).length, 1);
  assert.ok(listing.includes("Issue type"));
  assert.ok(listing.includes("Agent review"));
});

test("trace shows selected quotes and comparisons once, with full context and check audit expandable", () => {
  const html = issueRow(issue, report);
  for (const fragment of [
    "Partial-date rule differs",
    "Rule comparison",
    "Expected",
    "Observed",
    "Use &lt;first&gt; day",
    'data-document-section="page-5"',
    "Full context",
    "3</span>  day: 1</mark>",
    "2 / 3 records differ",
    "reference <code>&lt;value&gt;</code>; rule <code>(missing)</code>",
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

test("search includes check evidence while type and agent review filter independently", () => {
  const s = state(),
    view = createReport({ report, state: s, esc });
  s.findingSearch = "<first>";
  assert.deepEqual(view.findingItems(), [issue]);
  s.reviewStatus = "disputed";
  assert.deepEqual(view.findingItems(), []);
  s.reviewStatus = "agreed";
  s.kind = "gap";
  assert.match(view.findingRows(), /No issues match/);
  s.kind = "conflict";
  assert.deepEqual(view.findingItems(), [issue]);
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
  assert.match(host.innerHTML, /2 subjects with observed differences/);
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
    "Impact not measured",
  );
  assert.equal(
    impactText({
      ...issue,
      impact: { ...issue.impact, status: "not_observed" },
    }),
    "No differences in tested data",
  );
  const contextual = {
    ...issue,
    trace: [{ evidence_id: "comparison", role: "context" }],
  };
  assert.match(
    issueRow(contextual, report),
    /Context comparison; excluded from issue impact/,
  );
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
