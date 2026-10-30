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
  assert.match(html, /No independent generated ADaM comparison datasets/);
  assert.match(html, /Human analysis review pending/);
  assert.doesNotMatch(html, /All pilot studies|published submission package|%/);
});

test("the metric and listing count issues separately from supporting checks", () => {
  assert.deepEqual(consistencyFindings(report), [issue]);
  const html = createShell({
    report,
    model: { metrics: { matched: [1, 2, 3], reference: [1, 2, 3] } },
  }).metrics();
  assert.match(html, /Generated ADaM dataset agreement/);
  assert.match(html, /<strong>100%<\/strong> of generated ADaM datasets matched/);
  assert.match(html, /<strong>1<\/strong> finding awaiting review/);
  assert.match(html, /1 critical; 0 non-critical; 0 needing assessment/);
  assert.match(html, /Findings can remain open even when generated ADaM dataset agreement is 100%/);
  const listing = createReport({ report, state: state(), esc }).findingsView();
  assert.match(listing, /1 of 1 issue &middot; 2 supporting checks/);
  assert.equal((listing.match(/<tr class="review-issue"/g) || []).length, 1);
  assert.ok(listing.includes("Issue type"));
  assert.ok(!listing.includes("Agent review: agreed"));
  assert.ok(listing.includes('id="finding-agent"'));
  assert.ok(!listing.includes('id="issue-review"'));
  assert.deepEqual([...listing.matchAll(/<th scope="col">([^<]+)<\/th>/g)].map((m) => m[1]), [
    "Dataset / variable", "Status", "Critical finding", "Type", "Documented rule vs data", "Issue", "Evidence",
  ]);
  assert.ok(listing.includes('<th scope="col">Status</th>'));
  assert.match(listing, /class="issue-status"[^]*?class="status attention">Under Review<\/span>/);
  assert.deepEqual([...issueRow(issue, report).matchAll(/<td class="([^"]+)"/g)].map((m) => m[1]), [
    "issue-status", "issue-critical", "issue-type", "issue-impact", "issue-summary",
  ]);
  for (const name of ["issue-critical", "issue-type"]) {
    const cell = listing.match(new RegExp(`<td class="${name}">([^]*?)</td>`))[1];
    assert.equal((cell.match(/class="status /g) || []).length, 1);
    assert.doesNotMatch(cell, /<p|<small/);
  }
  assert.ok(!listing.includes(issue.critical.reason));
  // The row states the measured impact in one line; the comparison labels stay in the review.
  assert.ok(listing.includes("2 subjects differ"));
  assert.ok(!listing.includes("Documented rule vs generated ADaM datasets"));
});

test("trace shows selected quotes and comparisons once, with full context and check audit expandable", () => {
  const html = issueTrace(issue, report);
  for (const fragment of [
    "1. Rule comparison",
    "2. Data comparison",
    "3. Proposed action",
    "Expected",
    "Observed",
    "Use &lt;first&gt; day",
    'data-source-evidence="source"',
    "Full context",
    '3</span><span class="context-line-text">  day: 1</span></mark>',
    "2 / 3 records differ",
    "generated ADaM datasets <code>&lt;value&gt;</code>; documented rule <code>(missing)</code>",
    "2 supporting checks and agent review",
    "Proposed action",
    "Complete check evidence",
    "The date derivation differs.",
    "Agent review: agreed",
  ])
    assert.ok(html.includes(fragment), fragment);
  const primary = html.slice(0, html.indexOf('<details class="issue-checks">'));
  assert.equal(
    (primary.match(/Use &lt;first&gt; day<\/blockquote>/g) || []).length,
    1,
  );
  assert.ok(!html.includes("<value>"));
  assert.ok(html.indexOf("1. Rule comparison") < html.indexOf("2. Data comparison"));
  assert.ok(html.indexOf("2. Data comparison") < html.indexOf("3. Proposed action"));
  assert.match(primary, /Documented rule vs generated ADaM datasets: 2 subjects differ/);
  // Each citation opens its source through one link; line numbers stay in the source view.
  assert.equal(
    (html.match(/data-source-evidence=/g) || []).length,
    (html.match(/<button class="text-link" data-source-evidence="[^"]+">View source<\/button>/g) || []).length,
  );
  assert.doesNotMatch(html, /Source lines|Source file/);
});

test("source context preserves indentation, blank lines and escaped code with accurate line numbers", () => {
  const html = issueTrace(issue, {
    ...report,
    review: {
      ...report.review,
      evidence: [source, {
        ...spec,
        context: '- name: DATE\n\n  when: "DATE < END & VALID"\n',
        context_lines: [2, 4],
      }, comparison],
    },
  }, { specificationsOnly: true });
  assert.doesNotMatch(html, /<details|<blockquote|issue-comparison/);
  assert.match(html, /tabindex="0" aria-label="spec.yaml source context"/);
  assert.match(html, /<span class="context-line-text">  when: &quot;DATE &lt; END &amp; VALID&quot;<\/span>/);
  assert.match(html, /<mark class="context-line"><span class="context-line-number" aria-hidden="true">3<\/span><span class="context-line-text"> <\/span><\/mark>/);
  assert.equal((html.match(/class="context-line-number"/g) || []).length, 3);
  assert.doesNotMatch(html, /class="line-number"|>5<\/span>/);
});

test("each rule ID opens its title and statement, once and in check order", () => {
  const row = issueRow(issue, report);
  const legend = (id) => `<details class="rule-legend" data-popover><summary>${id}</summary><div class="rule-popover" role="note"><strong>${id}: Rule title</strong><p>Follow the documented date rule.</p></div></details>`;
  assert.ok(row.includes(`<span class="rule-id">${legend("CR-5")}, ${legend("CR-6")}</span>`), row);
  assert.doesNotMatch(row, /title="CR-|Generic rule title/);
});

test("finding rows open a separate evidence page without rendering complete evidence", () => {
  const row = issueRow(issue, report);
  assert.match(row, /data-trace-issue="study:ADX.DATE.partial-date"/);
  assert.doesNotMatch(row, /finding-evidence|Use &lt;first&gt; day|finding-trace/);
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
  assert.match(view.findingRows(), /colspan="7"/);
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
    root: () => ({ classList: { remove() {} } }),
  }).drawer();
  assert.match(host.innerHTML, /Partial-date rule differs/);
  assert.match(host.innerHTML, /data-trace-issue="study:ADX.DATE.partial-date"/);
  assert.match(host.innerHTML, /Documented rule vs generated ADaM datasets: 2 subjects differ/);
});

test("former issue links resolve to the combined source-pair row and trace", () => {
  const combined = { ...issue, aliases: ["former-issue"], check_ids: checks.map((c) => c.id) };
  const data = { ...report, review: { ...report.review, issues: [combined] } };
  for (const id of [combined.id, "former-issue", ...combined.check_ids])
    assert.equal(findIssue(data, id), combined);
  const host = { innerHTML: "" };
  createReport({
    report: data, state: { ...state(), evidence: "former-issue" }, esc,
    byId: () => host, root: () => ({ classList: { remove() {} } }),
  }).drawer();
  assert.match(host.innerHTML, /data-trace-issue="study:ADX.DATE.partial-date"/);
  assert.doesNotMatch(host.innerHTML, /finding-evidence/);
});

test("an exact variable search excludes other variables even when it has no findings", () => {
  const other = { ...issue, id: "other", variable: "OTHER" };
  const model = { datasets: [{ name: "ADX", output: "adx" }],
    tables: { adx: { columns: [{ name: "DATE" }, { name: "OTHER" }] } } };
  for (const [label, issues, expected] of [
    ["variable with a finding", [issue, other], [issue]],
    ["declared variable without a finding", [other], []],
  ]) {
    const data = { ...report, review: { ...report.review, issues } };
    const s = { ...state(), findingSearch: "ADX.DATE" };
    assert.deepEqual(createReport({ model, report: data, state: s, esc }).findingItems(), expected, label);
  }
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
    "Documented rule vs generated ADaM datasets: no differences in tested data",
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
  assert.equal(impactText(item, data), "Documented rule vs generated ADaM datasets: 3 subjects differ; Documented rule vs yamaa output: 1 subject differs");
  assert.equal(comparisonLabel({ ...comparison, method: "copy" }), "Documented source vs generated ADaM datasets");
  assert.equal(comparisonLabel({ ...comparison, type: "codelist", target: "derived" }), "Documented codelist vs yamaa output");
  assert.match(comparisonLabel({ ...comparison, reading: "corrected" }), /Alternative interpretation: corrected vs generated ADaM datasets/);
});

test("summary retains unassessed findings, zero findings and unavailable references", () => {
  const data = { ...report, review: { ...report.review, issues: [{ ...issue, critical: undefined }] } };
  const model = { metrics: { matched: [0, 0, 0], reference: [0, 0, 0] } };
  const html = createShell({ report: data, model }).metrics();
  assert.match(html, /No generated ADaM comparison datasets/);
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

test("document previews exclude YAML and expose missing comparison evidence", () => {
  const html = issueTrace(issue, report, { sourcesOnly: true });
  assert.match(html, /Document: guide.pdf/);
  // The quotation is the cited clause, unhighlighted; its longer passage stays collapsed.
  assert.match(html, /<blockquote>Use &lt;first&gt; day<\/blockquote>/);
  assert.match(html, /<details class="issue-context"><summary><span>Full context<\/span><small>page 5<\/small><\/summary><blockquote>For partial dates: Use &lt;first&gt; day of the month.<\/blockquote><\/details>/);
  assert.doesNotMatch(html, /<mark/);
  assert.match(html, /Only one source document/);
  assert.doesNotMatch(html, /Specification:|spec-lines|Expected<\/dt>/);
  const yaml = issueTrace(issue, report, { specificationsOnly: true });
  assert.match(yaml, /Specification: spec.yaml/);
  assert.match(yaml, /class="spec-lines"/);
  assert.doesNotMatch(yaml, /Document: guide.pdf/);
});


test("YAML comparison includes the selected translated rule but no sibling calculation", () => {
  const translation = { ...spec, id: "translation", path: "study/documented-rules.yaml", section: comparison.column };
  const unrelated = { ...spec, id: "unrelated", path: "study/other.yaml", section: "OTHER" };
  const data = { ...report, review: { ...report.review,
    evidence: [...report.review.evidence, translation, unrelated],
    checks: report.review.checks.map((c) => ({ ...c, evidence_ids: [...c.evidence_ids, translation.id, unrelated.id] })),
  } };
  const html = issueTrace(issue, data, { specificationsOnly: true });
  assert.match(html, /Specification: documented-rules.yaml/);
  assert.ok(html.indexOf('aria-label="study/documented-rules.yaml"') < html.indexOf(`aria-label="${spec.path}"`));
  assert.doesNotMatch(html, /other.yaml|Only one YAML/);
  assert.equal((html.match(/class="trace-source-file"/g) || []).length, 2);
});

test("YAML comparison omits prose and submission blocks while preserving derivation source lines", () => {
  const context = '- name: ADT\n  submission:\n    label: Analysis date\n    origins:\n      - type: Derived\n  derivation:\n    value: AE.AESTDT\n  submission: {length: 8}\n  label: Date';
  const rule = { ...spec, context, context_lines: [10, 18], lines: [15, 16] };
  const translation = { ...rule, id: "translation", path: "study/documented-rules.yaml", section: comparison.column };
  const data = { ...report, review: { ...report.review,
    evidence: [source, rule, comparison, translation],
    checks: report.review.checks.map((c) => ({ ...c, evidence_ids: [...c.evidence_ids, translation.id] })),
  } };
  const html = issueTrace(issue, data, { specificationsOnly: true });
  assert.equal((html.match(/class="trace-source-file"/g) || []).length, 2);
  assert.doesNotMatch(html, /<blockquote|<details|issue-comparison|submission:|Analysis date|origins:|Derived|length:/);
  assert.match(html, /<mark class="context-line"><span class="context-line-number" aria-hidden="true">16<\/span><span class="context-line-text">    value: AE.AESTDT<\/span>/);
  assert.match(html, />18<\/span><span class="context-line-text">  label: Date/);
  assert.equal(data.review.evidence[1].context, context);
});

test("findings by dataset count the current filters and mark the selected dataset", () => {
  const other = {
    ...issue, id: "other", dataset: "ADY", variable: "FLAG",
    summary: "Label copied from ADZ.",
    critical: { status: "no", reason: "Label only." },
  };
  const data = { ...report, review: { ...report.review, issues: [issue, other] } };
  const s = state(),
    view = createReport({ report: data, state: s, esc,
      model: { datasets: [{ name: "ADY" }, { name: "ADX" }, { name: "ADZ" }] } });
  const chips = (html) => [...html.matchAll(
    /data-finding-dataset="([^"]*)" aria-pressed="(true|false)">[^<]*<span class="chip-count">(\d+)<\/span>/g,
  )].map((m) => [m[1], m[2], Number(m[3])]);
  assert.deepEqual(chips(view.findingRows()), [
    ["", "true", 2], ["ADY", "false", 1], ["ADX", "false", 1], ["ADZ", "false", 0],
  ]);
  s.critical = "yes";
  s.findingSearch = "adx";
  const html = view.findingRows();
  assert.deepEqual(chips(html), [
    ["", "false", 1], ["ADY", "false", 0], ["ADX", "true", 1], ["ADZ", "false", 0],
  ]);
  assert.match(html, /aria-label="Findings by dataset"/);
  assert.match(html, /1 of 2 issues/);
  assert.ok(html.indexOf("finding-datasets") < html.indexOf("result-count"));
  // A zero-count dataset chip lists nothing, not issues whose text mentions the name.
  s.critical = "";
  s.findingSearch = "ADZ";
  const empty = view.findingRows();
  assert.deepEqual(chips(empty), [
    ["", "false", 2], ["ADY", "false", 1], ["ADX", "false", 1], ["ADZ", "true", 0],
  ]);
  assert.match(empty, /0 of 2 issues/);
  assert.match(empty, /No issues match/);
  const bare = createReport({ report: data, state: state(), esc }).findingRows();
  assert.deepEqual(chips(bare).map(([name]) => name), ["", "ADX", "ADY"]);
});

test("your reviews strip counts the listed findings' assessments and the own-review filter narrows the list", () => {
  const other = { ...issue, id: "other", dataset: "ADY", variable: "FLAG" };
  const data = { ...report, review: { ...report.review, issues: [issue, other] } };
  const records = new Map([
    [issue.id, { status: "reviewed", shared: "github", stale: false }],
    [other.id, { status: "draft", shared: "", stale: false }],
  ]);
  const drafts = { load: (study, i) => records.get(i.id) || { status: "unreviewed", shared: "", stale: false } };
  const s = state(),
    view = createReport({ report: data, state: s, esc, drafts, model: { id: "study", datasets: [] } });
  let html = view.findingRows();
  assert.match(html, /Your reviews<\/span><strong>2 of 2<\/strong> listed/);
  assert.match(html, /1 with both decisions; 1 draft; 1 opened in GitHub or copied/);
  assert.match(html, /data-review-ledger="copy" >Copy your reviews/);
  s.yourReview = "draft";
  html = view.findingRows();
  assert.match(html, /1 of 2 issues/);
  assert.match(html, /data-finding-id="other"/);
  assert.doesNotMatch(html, /data-finding-id="study:ADX/);
  assert.match(html, /<strong>1 of 1<\/strong> listed/);
  assert.deepEqual(view.ledger().counts, { listed: 1, started: 1, drafts: 1, reviewed: 0, shared: 0, stale: 0 });
  assert.match(view.findingsView(), /id="finding-review"/);
  records.clear();
  assert.match(createReport({ report: data, state: state(), esc, drafts, model: { id: "study" } }).findingRows(),
    /<strong>0 of 2<\/strong> listed<span class="ledger-actions"><button type="button" class="text-link" data-review-ledger="copy" disabled>/);
  // Without a drafts store there is no ledger and no own-review filter.
  const bare = createReport({ report: data, state: state(), esc });
  assert.doesNotMatch(bare.findingRows() + bare.findingsView(), /review-ledger|finding-review/);
});

test("the listing puts critical findings first, then those needing assessment, keeping report order within each", () => {
  const second = { ...issue, id: "second", variable: "B", critical: { status: "needs_review", reason: "Gap." } },
    third = { ...issue, id: "third", variable: "C", critical: { status: "yes", reason: "Rule differs." } },
    fourth = { ...issue, id: "fourth", variable: "D", critical: { status: "no", reason: "Label only." } },
    fifth = { ...issue, id: "fifth", variable: "E", critical: { status: "needs_review", reason: "Gap." } };
  const data = { ...report, review: { ...report.review, issues: [second, fourth, issue, third, fifth] } };
  const view = createReport({ report: data, state: state(), esc });
  assert.deepEqual(view.findingItems().map((i) => i.id), [issue.id, "third", "second", "fifth", "fourth"]);
  const html = view.findingRows();
  assert.ok(html.indexOf('data-finding-id="third"') < html.indexOf('data-finding-id="second"'));
});

test("the findings tab explains the two decisions and the types before the filters, linking the guide when the site is known", () => {
  const html = createReport({ report, state: state(), esc, site: "https://example.org/project/" }).findingsView();
  assert.ok(html.indexOf("review-howto") < html.indexOf("report-filters"));
  for (const fragment of ["How to review a finding", "Do you agree with this finding?", "Is this finding critical?",
    "Conflict: documents disagree", "Agent agreement is not resolution.", 'href="https://example.org/project/review/findings/"'])
    assert.ok(html.includes(fragment), fragment);
  assert.doesNotMatch(createReport({ report, state: state(), esc }).findingsView(), /href="[^"]*review\/findings/);
});

test("the documented-rule column states subjects, no differences or not measured, without reordering a criticality", () => {
  const measuredIssue = { ...issue, id: "measured", variable: "M", critical: { status: "needs_review", reason: "Gap." },
      impact: { status: "observed", subject_count: 3, subjects: ["A", "B", "C"] } },
    none = { ...issue, id: "none", variable: "N", critical: { status: "needs_review", reason: "Gap." },
      impact: { status: "not_observed", subject_count: 0, subjects: [] } },
    unmeasured = { ...issue, id: "unmeasured", variable: "U", critical: { status: "needs_review", reason: "Gap." },
      impact: { status: "not_measured", subject_count: 0, subjects: [] } };
  const data = { ...report, review: { ...report.review, issues: [unmeasured, none, measuredIssue, issue] } };
  const view = createReport({ report: data, state: state(), esc });
  assert.deepEqual(view.findingItems().map((i) => i.id), [issue.id, "unmeasured", "none", "measured"]);
  const html = view.findingRows();
  assert.match(html, /data-finding-id="measured"[^]*?<td class="issue-impact"><span class="sr-only">Documented rule vs data: <\/span>3 subjects differ<\/td>/);
  assert.match(html, /data-finding-id="none"[^]*?issue-impact">[^]*?No differences in tested data</);
  assert.match(html, /data-finding-id="unmeasured"[^]*?issue-impact">[^]*?Not measured</);
});

test("disputed, stale and mixed agent reviews list after agreed ones within a criticality and can be filtered", () => {
  const disputed = { ...issue, id: "disputed", variable: "D", review: "disputed" },
    stale = { ...issue, id: "stale", variable: "S", review: "stale", critical: { status: "needs_review", reason: "Gap." } },
    agreed = { ...issue, id: "agreed", variable: "A", review: "agreed", critical: { status: "needs_review", reason: "Gap." } };
  const data = { ...report, review: { ...report.review, issues: [disputed, stale, agreed, issue] } };
  const s = state(), view = createReport({ report: data, state: s, esc });
  assert.deepEqual(view.findingItems().map((i) => i.id), [issue.id, "disputed", "agreed", "stale"]);
  assert.match(view.findingRows(), /data-finding-id="disputed"[^]*?<small class="agent-review-status">Agent review: disputed<\/small>/);
  s.agentReview = "disputed";
  assert.deepEqual(view.findingItems().map((i) => i.id), ["disputed"]);
});

test("the how-to panel stays open until the reviewer has started a review of the study", () => {
  const started = { load: (study, i) => ({ status: i.id === issue.id ? "draft" : "unreviewed", shared: "", stale: false }) },
    none = { load: () => ({ status: "unreviewed", shared: "", stale: false }) };
  assert.match(createReport({ report, state: state(), esc, drafts: none, model: { id: "study" } }).findingsView(), /<details class="review-howto" open>/);
  assert.match(createReport({ report, state: state(), esc, drafts: started, model: { id: "study" } }).findingsView(), /<details class="review-howto"><summary>/);
});
