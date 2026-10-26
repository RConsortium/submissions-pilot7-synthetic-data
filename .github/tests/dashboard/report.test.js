import test from "node:test";
import assert from "node:assert/strict";
import {
  consistencyFindings,
  createReport,
} from "../../../docs/assets/dashboard/report.js";
import { createShell } from "../../../docs/assets/dashboard/shell.js";
import { esc, link } from "../../../docs/assets/dashboard/ui.js";

const finding = {
  id: "study:ADX.ASTDT",
  dataset: "ADX",
  variable: "ASTDT",
  kind: "not_reviewed",
  status: "Not reviewed",
  comparison: "source_documents",
  title: "Review imputation",
  observation: "Confirm the partial-date rule.",
  spec: {
    excerpt: "derivation: INPUT.DATE",
    url: "https://example/spec.yaml#L2",
  },
  source: {
    path: "study/guide.pdf",
    section: "Page 5",
    excerpt: "Use <first> day",
    url: "documents/guide.html#page-5",
  },
  data: { path: "study/adx.parquet", summary: "Example values: 2014-01-01" },
  recommendation: "Confirm against the original rule.",
};
const executed = {
  ...finding,
  id: "executed",
  kind: "executed",
  comparison: "input_output",
};

test("the metric and table count review findings and failed logic checks, excluding successful executions", () => {
  const failed = { ...executed, id: "failed", kind: "inconsistent" };
  const report = { findings: [finding], logic_checks: [executed, failed] };
  assert.deepEqual(consistencyFindings(report), [failed, finding]);
  assert.deepEqual(consistencyFindings({ findings: [finding] }), [finding]);
  const html = createShell({
    report,
    model: { metrics: { matched: [1, 2, 3], reference: [1, 2, 3] } },
  }).metrics();
  assert.match(html, /<span><strong>Consistency:<\/strong> 2 findings<\/span>/);
  assert.ok(!html.includes("data-view"));
});

test("the listing traces source citations, specification lines and dataset evidence inline", () => {
  const state = { findingSearch: "", kind: "", comparison: "" };
  const report = {
    findings: [finding],
    logic_checks: [executed],
    documents: [{ path: finding.source.path, available: true }],
  };
  const view = createReport({ report, state, esc, link });
  const html = view.findingsView();
  for (const fragment of [
    "1 of 1 findings",
    '<details class="finding-trace"><summary>Trace evidence</summary>',
    "derivation: INPUT.DATE",
    "https://example/spec.yaml#L2",
    'data-document="study/guide.pdf" data-document-section="page-5"',
    "Use &lt;first&gt; day",
    "Example values: 2014-01-01",
    'data-finding="study:ADX.ASTDT"',
  ])
    assert.ok(html.includes(fragment), fragment);
  assert.ok(!html.includes('data-finding="executed"'));
  state.findingSearch = "first";
  assert.deepEqual(view.findingItems(), [finding]);
  state.comparison = "input_output";
  assert.match(view.findingRows(), /No findings match/);
});
