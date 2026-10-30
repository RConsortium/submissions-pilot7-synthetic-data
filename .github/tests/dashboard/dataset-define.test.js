import test from "node:test";
import assert from "node:assert/strict";
import { readRoute } from "../../../docs/assets/dashboard/state.js";
import { createShell } from "../../../docs/assets/dashboard/shell.js";
import { comparisonLabel, issueTrace } from "../../../docs/assets/dashboard/issues.js";
import { esc, link } from "../../../docs/assets/dashboard/ui.js";

const model = { id: "study", title: "Study", subjects: ["001"],
  settings: { review_scope: "dataset_define" }, datasets: [{ name: "ADSL", inputs: [] }], tables: {} };

test("focused routes cannot switch to reference datasets or retain multisource filters", () => {
  const state = readRoute("#study/define/ADSL?output=reference&comparison=documented_rules&agentReview=agreed&specView=resolved", model);
  assert.equal(state.view, "overview");
  assert.equal(state.output, "derived");
  assert.deepEqual(state.inputs, []);
  assert.deepEqual(state.outputs, []);
  assert.equal(state.comparison, "");
  assert.equal(state.agentReview, "");
  assert.equal(state.specView, "");
  assert.equal(readRoute("", model).view, "overview");
});

test("focused summary shows check coverage without a reference agreement score", () => {
  const report = { scope: "dataset_define", check_counts: { passed: 2, different: 1, not_assessed: 3 },
    review: { schema_version: 1, issues: [], checks: [], evidence: [] } };
  const html = createShell({ model, report, state: { view: "overview" }, site: "https://example.test/",
    REPO: "https://example.test/repo", esc, link }).frame();
  assert.match(html, /2 checks passed; 1 differences; 0 gaps; 3 not assessed/);
  assert.match(html, /Dataset and Define-XML/);
  assert.doesNotMatch(html, /Generated ADaM dataset agreement|Define-XML comparison|Source documents/);
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
