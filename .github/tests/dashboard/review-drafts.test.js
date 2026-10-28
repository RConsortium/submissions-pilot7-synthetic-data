import test from "node:test";
import assert from "node:assert/strict";
import { createReviewDrafts } from "../../../docs/assets/dashboard/review-drafts.js";

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
