/** Comparison results retain differences, legacy gaps and escaped XML metadata. */
import test from "node:test";
import assert from "node:assert/strict";
import { defineComparisonView } from "../../../docs/assets/dashboard/define-comparison.js";
import { readRoute, formatRoute } from "../../../docs/assets/dashboard/state.js";

const resource = (path) => "https://example.test/project/study/" + path;
const model = {
  id: "study", subjects: [], tables: {}, datasets: [{ name: "ADSL", inputs: [] }],
  define_comparison: {
    evidence: "define/comparison.json",
    reference: { available: true, original: "define/reference.xml", view: "define/reference.html" },
    candidate: { available: true, original: "define/candidate.xml", view: "define/candidate.html" },
  },
  validation: { define_xml: { comparison: "matched", adam_version: "2.0.0", candidate_version: "2.1.0", metadata: {} } },
};
test("comparison routes roundtrip with the selected dataset", () => {
  const state = readRoute("#study/define/ADSL", model);
  assert.equal(state.view, "define");
  assert.equal(formatRoute(state, model), "#study/define/ADSL");
});
test("independent XML panes use bundle URLs and retain version and comparison status", () => {
  const html = defineComparisonView(model, resource);
  assert.match(html, /Metadata matched/);
  assert.match(html, /Define-XML 2.0.0/);
  assert.match(html, /Define-XML 2.1.0/);
  assert.match(html, /src="https:\/\/example.test\/project\/study\/define\/reference.html" sandbox=""/);
  assert.match(html, /src="https:\/\/example.test\/project\/study\/define\/candidate.html" sandbox=""/);
  assert.match(html, /No metadata differences were found/);
});
test("legacy gaps and unequal values remain visible and escaped", () => {
  const legacy = structuredClone(model);
  legacy.validation.define_xml.comparison = "different";
  legacy.validation.define_xml.metadata = {
    full_reference_reproduced: false,
    field_counts: { matched: 2, converted: 1, different: 1, unsupported: 1, unresolved: 1 },
    differences: [{ path: "/datasets/ADSL/<script>", reference: "<img onerror=alert(1)>", candidate: null, known_gap: { reason: "<inherited>" } }],
    unsupported: [{ kind: "legacy_results" }], unresolved: [{ path: "missing reference" }],
  };
  const html = defineComparisonView(legacy, resource);
  assert.match(html, /Metadata differs/);
  assert.match(html, /not fully reproduced/);
  assert.match(html, /Metadata differences \(1\)/);
  assert.match(html, /Unsupported content \(1\)/);
  assert.match(html, /Unresolved source declarations \(1\)/);
  assert.match(html, /&lt;script&gt;/);
  assert.match(html, /&lt;img onerror=alert\(1\)&gt;/);
  assert.match(html, /&lt;inherited&gt;/);
  assert.doesNotMatch(html, /<script>|<img /);
});
test("unavailable evidence never claims a match or embeds a missing resource", () => {
  const html = defineComparisonView({}, resource);
  assert.match(html, /Not compared/);
  assert.match(html, /XML is unavailable/);
  assert.doesNotMatch(html, /<iframe|No metadata differences were found/);
});
