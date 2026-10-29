import test from "node:test";
import assert from "node:assert/strict";
import { createReviewDrafts, draftLabel, reviewLedger } from "../../../docs/assets/dashboard/review-drafts.js";

const issue = { dataset: "ADAE", variable: "FLAG", id: "study:ADAE.FLAG.test", title: "A finding", summary: "Review it.",
  check_ids: ["check"], trace: [{ evidence_id: "source", role: "context" }] };
const report = { review: { checks: [{ id: "check", basis: "evidence-a" }] } };
function storage() {
  const data = new Map();
  return { getItem: (k) => data.get(k), setItem: (k, v) => data.set(k, v) };
}
const assessment = { agreement: "agree", criticality: "not_critical", comment: "Keep the documented filter." };

test("human decisions start unselected and incomplete reviews cannot be completed", () => {
  const drafts = createReviewDrafts(storage());
  assert.equal(drafts.load("study", issue, report).agreement, "");
  assert.equal(drafts.load("study", issue, report).criticality, "");
  assert.throws(() => drafts.save("study", issue, report, { agreement: "agree" }, true), /Choose both/);
  assert.equal(drafts.save("study", issue, report, {}, false).status, "draft");
});
test("reviews survive reload, remain scoped to study/issue and never update the published finding", () => {
  const store = storage(), drafts = createReviewDrafts(store), before = JSON.stringify(issue);
  drafts.save("study", issue, report, assessment, true);
  assert.equal(createReviewDrafts(store).load("study", issue, report).status, "reviewed");
  assert.equal(drafts.load("other-study", issue, report).status, "unreviewed");
  assert.equal(drafts.load("study", { ...issue, id: "another-issue" }, report).status, "unreviewed");
  assert.equal(JSON.stringify(issue), before);
});
test("changed evidence or editorial scope returns the saved review to a stale draft", () => {
  const drafts = createReviewDrafts(storage());
  drafts.save("study", issue, report, assessment, true);
  const revised = { review: { checks: [{ id: "check", basis: "evidence-b" }] } };
  const draft = drafts.load("study", issue, revised);
  assert.equal(draft.status, "draft");
  assert.equal(draft.stale, true);
  assert.equal(draft.comment, assessment.comment);
  assert.equal(drafts.load("study", { ...issue, summary: "Changed scope" }, report).stale, true);
  const changedExamples = { ...report, trace_examples: { "ADAE.FLAG": { subjects: ["changed"] } } };
  // Example records are evidence too, independently of unchanged aggregate counts.
  assert.equal(drafts.load("study", issue, changedExamples).stale, true);
  assert.equal(drafts.save("study", issue, revised, draft, true).status, "reviewed");
});
test("blocked storage retains assessments in session memory without claiming persistence", () => {
  const drafts = createReviewDrafts({ getItem() { throw Error("blocked"); }, setItem() { throw Error("blocked"); } });
  drafts.load("study", issue, report);
  assert.equal(drafts.available, false);
  drafts.save("study", issue, report, assessment, true);
  assert.equal(drafts.load("study", issue, report).comment, assessment.comment);
  assert.equal(drafts.available, false);
});
test("malformed or unsupported stored decisions cannot become a completed review", () => {
  for (const raw of ["broken", JSON.stringify({ schema_version: 9 }),
    JSON.stringify({ schema_version: 1, signature: "old", agreement: "invented", criticality: "invented", status: "reviewed" })]) {
    const drafts = createReviewDrafts({ getItem: () => raw });
    const value = drafts.load("study", issue, report);
    assert.equal(value.agreement, "");
    assert.equal(value.criticality, "");
    assert.notEqual(value.status, "reviewed");
  }
});
test("a complete assessment records how it left the browser and returns to a draft when edited", () => {
  const drafts = createReviewDrafts(storage());
  assert.equal(drafts.save("study", issue, report, { ...assessment, shared: "github" }, true).shared, "github");
  assert.equal(draftLabel(drafts.load("study", issue, report)), "Opened in GitHub composer");
  drafts.save("study", issue, report, { ...assessment, shared: "clipboard" }, true);
  assert.equal(draftLabel(drafts.load("study", issue, report)), "Copied for GitHub");
  drafts.save("study", issue, report, { ...assessment, comment: "edited" }, false);
  assert.equal(drafts.load("study", issue, report).shared, "");
  assert.equal(draftLabel(drafts.load("study", issue, report)), "Draft");
  assert.equal(drafts.save("study", issue, report, { ...assessment, shared: "invented" }, true).shared, "");
  assert.equal(draftLabel(drafts.load("study", issue, report)), "Saved locally");
  assert.equal(draftLabel(drafts.load("study", { ...issue, id: "untouched" }, report)), "Not reviewed");
  // The optional side is kept as chosen and never invented.
  assert.equal(drafts.save("study", issue, report, { ...assessment, side: "specification" }, true).side, "specification");
  assert.equal(drafts.load("study", issue, report).side, "specification");
  assert.equal(drafts.save("study", issue, report, { ...assessment, side: "invented" }, true).side, "");
});
test("the ledger counts started, complete, shared and stale assessments of the listed issues", () => {
  const drafts = createReviewDrafts(storage());
  const second = { ...issue, id: "study:ADAE.FLAG.second" }, third = { ...issue, id: "study:ADAE.FLAG.third" };
  drafts.save("study", issue, report, { ...assessment, shared: "github" }, true);
  drafts.save("study", second, report, { agreement: "agree" }, false);
  drafts.save("study", third, report, assessment, true);
  const { counts, entries } = reviewLedger(drafts, "study", [issue, second, third, { ...issue, id: "untouched" }], report);
  assert.deepEqual(counts, { listed: 4, started: 3, drafts: 1, reviewed: 2, shared: 1, stale: 0 });
  assert.equal(entries[3].draft.status, "unreviewed");
  const revised = { review: { checks: [{ id: "check", basis: "evidence-b" }] } };
  assert.deepEqual(reviewLedger(drafts, "study", [issue], revised).counts,
    { listed: 1, started: 1, drafts: 1, reviewed: 0, shared: 0, stale: 1 });
});
