import test from "node:test";
import assert from "node:assert/strict";
import { reviewComment, reviewLedgerDocument } from "../../../docs/assets/dashboard/review-comment.js";

const model = { id: "pilot", revision: "1234567890abcdef" };
const issue = {
  id: "pilot:ADAE.AOCC01FL.selection-rule", dataset: "ADAE", variable: "AOCC01FL",
  title: "Select the dermatologic event", check_ids: ["ADAE.AOCC01FL.CR-5"],
};
const review = { agreement: "disagree", criticality: "critical", comment: "Confirm intent before changing the rule.\n\nCheck both subjects." };

test("GitHub comment retains independent decisions, rationale and exact evidence identity", () => {
  const text = reviewComment(model, issue, review,
    "https://example.org/project/studies/pilot/?giscus=session#pilot/overview/ADSL");
  for (const fragment of ["**Agreement:** Disagree", "**Criticality:** Critical",
    review.comment, issue.id, model.revision, issue.check_ids[0],
    "https://example.org/project/studies/pilot/?v=1234567#pilot/overview/ADAE?findingSearch=ADAE.AOCC01FL"])
    assert.ok(text.includes(fragment), fragment);
  assert.doesNotMatch(text, /giscus=session|overview\/ADSL/);
});

test("missing or unknown decisions cannot produce a ready-to-publish assessment", () => {
  for (const input of [{}, { ...review, agreement: "unknown" }, { ...review, criticality: "" }])
    assert.throws(() => reviewComment(model, issue, input, "https://example.org/"), /Choose both/);
});

test("optional comments and a dataset-level finding have explicit context", () => {
  const text = reviewComment(model, { ...issue, variable: "" }, { ...review, comment: " " }, "https://example.org/");
  assert.ok(text.includes("No additional comments."));
  assert.ok(text.includes("## Review: ADAE - "));
  assert.ok(text.includes("findingSearch=ADAE)"));
});

test("the ledger document lists every started assessment with its status and skips untouched findings", () => {
  const entries = [
    { issue, draft: { status: "reviewed", shared: "github", stale: false, agreement: "agree", criticality: "critical", comment: "Fix the rule." } },
    { issue: { ...issue, id: "pilot:ADAE.OTHER", variable: "OTHER", title: "Other" },
      draft: { status: "draft", shared: "", stale: true, agreement: "", criticality: "unsure", comment: " " } },
    { issue: { ...issue, id: "pilot:ADAE.NONE" }, draft: { status: "unreviewed", shared: "", stale: false, agreement: "", criticality: "", comment: "" } },
  ];
  const text = reviewLedgerDocument({ ...model, title: "Pilot" }, entries,
    { listed: 3, started: 2, drafts: 1, reviewed: 1, shared: 1, stale: 1 },
    "https://example.org/project/studies/pilot/?giscus=session#pilot/overview/ADSL");
  for (const fragment of ["# Review of Pilot (pilot)", "`1234567890abcdef`",
    "2 of 3 listed findings; 1 with both decisions, 1 still drafts, 1 with changed evidence",
    "## ADAE.AOCC01FL - Select the dermatologic event", "**Status:** Submitted on GitHub", "Fix the rule.",
    "## ADAE.OTHER - Other", "**Agreement:** (not chosen)", "**Criticality:** Unsure", "**Status:** Draft (evidence changed)",
    "No additional comments.", "do not resolve a finding",
    "https://example.org/project/studies/pilot/?v=1234567#pilot/overview/ADAE?findingSearch=ADAE.OTHER"])
    assert.ok(text.includes(fragment), fragment);
  assert.doesNotMatch(text, /ADAE\.NONE|giscus=session/);
});
