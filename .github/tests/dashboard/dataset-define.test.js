import test from "node:test";
import assert from "node:assert/strict";
import { readRoute } from "../../../docs/assets/dashboard/state.js";
import { createShell } from "../../../docs/assets/dashboard/shell.js";
import { comparisonLabel, issueTrace } from "../../../docs/assets/dashboard/issues.js";
import { esc, link } from "../../../docs/assets/dashboard/ui.js";

const model = { id: "study", title: "Study", subjects: ["001"],
  metrics: { matched: [1, 3, 9], reference: [1, 3, 9] }, define_comparison: {},
  settings: { review_scope: "dataset_define" }, datasets: [{ name: "ADSL", inputs: [] }], tables: {} };

test("focused findings keep the full workspace and shareable XML comparison routes", () => {
  const state = readRoute("#study/define/ADSL?output=reference&comparison=documented_rules&agentReview=agreed&specView=resolved", model);
  assert.equal(state.view, "define");
  assert.equal(state.output, "reference");
  assert.equal(state.inputs, null);
  assert.deepEqual(state.outputs, []);
  assert.equal(state.comparison, "");
  assert.equal(state.agentReview, "");
  assert.equal(state.specView, "resolved");
  assert.equal(readRoute("", model).view, "datasets");
});

test("focused findings keep the study summaries and original navigation tabs", () => {
  const report = { scope: "dataset_define", check_counts: { passed: 2, different: 1, not_assessed: 3 },
    review: { schema_version: 1, issues: [], checks: [], evidence: [] } };
  const html = createShell({ model, report, state: { view: "overview" }, site: "https://example.test/",
    REPO: "https://example.test/repo", esc, link }).frame();
  assert.match(html, /100%<\/strong> of generated ADaM datasets matched/);
  assert.match(html, /SDTM -&gt; ADaM/);
  assert.match(html, /Consistency findings/);
  assert.match(html, /Define-XML comparison/);
  assert.match(html, /Source documents/);
  assert.doesNotMatch(html, /Dataset and Define-XML/);
});

test("direct measurement labels name the actual compared sides", () => {
  assert.equal(comparisonLabel({ method: "dataset_define", target: "derived" }), "Define-XML declaration vs current derived dataset");
  const issue = { trace: [], check_ids: [] };
  const report = { review: { schema_version: 1, issues: [], checks: [], evidence: [] } };
  const html = issueTrace(issue, report, { datasetDefineOnly: true });
  assert.match(html, /Current derived dataset/);
  assert.match(html, /Define-XML declaration/);
  assert.doesNotMatch(html, /YAML|second side|specification/i);
});
