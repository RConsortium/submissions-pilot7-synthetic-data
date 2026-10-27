import test from "node:test";
import assert from "node:assert/strict";
import { developmentReport } from "../../../docs/assets/dashboard/synthetic-development.js";

const root = new URL("https://example.test/prefix/evidence/dashboard/");
const model = {
  id: "kn564", development: {
    status: "succeeded", source_subjects: 994, package: "kn564-development.zip",
    report: "build-report.json", protocol: "protocol-sap.html",
    datasets: [{ domain: "ADSL", section: "adam", rows: 994, columns: 40,
      key_subject_checks: "passed", xpt_roundtrip: "passed", spec_view: "specs/adsl.yaml" }],
    summaries: { cohort: [{ TRT01P: "Placebo", subjects: 497, safety_subjects: 497, source_summary_deaths: 42 }] },
    review: { coverage: [{ analysis: "Week-52 PRO", status: "unsupported",
      supported_scope: "No measurements in window", findings: ["GAP-PRO52"] }],
      findings: [{ id: "GAP-PRO52", title: "Missing <week 52>", kind: "gap", summary: "A & B",
        datasets: ["ADQS"], choices: ["Provide source", "Exclude with justification"],
        proposed_action: "Resolve before use", evidence: { count: 0, denominator: 17085,
          unit: "records", subject_count: 0, examples: [], note: "Denominator is recorded scores" },
        citations: [{ quote: '<source value="literal">', section: "SAP section 10", line: 432 }] }] },
  },
};

test("development report retains measured zero, unsupported scope and source anchors", () => {
  const html = developmentReport(model, root);
  assert.match(html, /0 \/ 17,085 records; 0 distinct subjects/);
  assert.match(html, /unsupported/);
  assert.match(html, /synthetic\/kn564\/protocol-sap.html#L432/);
  assert.match(html, /synthetic\/kn564\/specs\/adsl.yaml/);
  assert.match(html, /1 open findings: 1 data\/metadata gaps, 0 measured conflicts, and 0 decisions/);
  assert.match(html, /Human analysis review pending/);
  assert.match(html, /Export review draft/);
  assert.match(html, /&lt;source value=&quot;literal&quot;&gt;/);
  assert.doesNotMatch(html, /<source |undefined|NaN/);
});

test("missing or failed builds cannot render success metrics", () => {
  for (const development of [undefined, { status: "failed" }, { status: "not_run" }]) {
    const html = developmentReport({ id: "kn189", development }, root);
    assert.match(html, /No successful study build/);
    assert.doesNotMatch(html, /checks passed|Download study package/);
  }
});
