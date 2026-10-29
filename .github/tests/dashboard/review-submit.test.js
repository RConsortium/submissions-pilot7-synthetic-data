import test from "node:test";
import assert from "node:assert/strict";
import { LINK_LIMIT, reviewDestination, reviewDiscussion, reviewTitle } from "../../../docs/assets/dashboard/review-submit.js";
import { reviewComment } from "../../../docs/assets/dashboard/review-comment.js";

const config = { review_url: "https://github.com/elong0527/yamaa/discussions/new?category=comments" };
const model = { id: "pilot", revision: "1234567890abcdef" };
const issue = {
  id: "pilot:ADAE.AOCC01FL.selection-rule", dataset: "ADAE", variable: "AOCC01FL",
  title: "Select the dermatologic event", check_ids: ["ADAE.AOCC01FL.CR-5"],
};
const review = { agreement: "agree", criticality: "not_critical", comment: "Reference flags follow the guide." };
const page = "https://example.org/project/studies/pilot/#pilot/overview/ADSL";

test("the composer link keeps the configured category and carries the exact title and assessment", () => {
  const prepared = reviewDiscussion(config, model, issue, review, page);
  const url = new URL(prepared.url);
  assert.equal(url.origin + url.pathname, "https://github.com/elong0527/yamaa/discussions/new");
  assert.equal(url.searchParams.get("category"), "comments");
  assert.equal(url.searchParams.get("title"), "Review: pilot ADAE.AOCC01FL - Select the dermatologic event");
  assert.equal(url.searchParams.get("body"), reviewComment(model, issue, review, page));
  assert.deepEqual(prepared, { url: prepared.url, title: url.searchParams.get("title"), body: url.searchParams.get("body"), prefilled: true });
});

test("missing decisions and a destination that is not a GitHub composer cannot open the composer", () => {
  assert.throws(() => reviewDiscussion(config, model, issue, { ...review, criticality: "" }, page), /Choose both/);
  for (const review_url of ["", "not a url", "https://example.org/x/y/discussions/new", "https://github.com/elong0527/yamaa/issues/new", "https://github.com/discussions/new"]) {
    assert.equal(reviewDestination({ review_url }), null, review_url);
    assert.throws(() => reviewDiscussion({ review_url }, model, issue, review, page), /review_url/, review_url);
  }
  assert.deepEqual(reviewDestination(config), { repo: "elong0527/yamaa", url: "https://github.com/elong0527/yamaa/discussions" });
  assert.deepEqual(reviewDestination({ review_url: "https://github.com/orgs/example/discussions/new?category=q-a" }),
    { repo: "orgs/example", url: "https://github.com/orgs/example/discussions" });
});

test("a review longer than a link allows opens the composer with the title only and keeps the text to paste", () => {
  const prepared = reviewDiscussion(config, model, issue, { ...review, comment: "x".repeat(LINK_LIMIT) }, page);
  const url = new URL(prepared.url);
  assert.equal(prepared.prefilled, false);
  assert.equal(url.searchParams.has("body"), false);
  assert.equal(url.searchParams.get("category"), "comments");
  assert.equal(url.searchParams.get("title"), reviewTitle(model, issue));
  assert.ok(prepared.url.length <= LINK_LIMIT);
  assert.equal(prepared.body, reviewComment(model, issue, { ...review, comment: "x".repeat(LINK_LIMIT) }, page));
});

test("titles name dataset-level findings and stay within GitHub's title length", () => {
  assert.equal(reviewTitle(model, { ...issue, variable: "" }), "Review: pilot ADAE - Select the dermatologic event");
  const long = reviewTitle(model, { ...issue, title: "t".repeat(400) });
  assert.equal(long.length, 200);
  assert.ok(long.startsWith("Review: pilot ADAE.AOCC01FL - tttt") && long.endsWith("..."), long);
});
