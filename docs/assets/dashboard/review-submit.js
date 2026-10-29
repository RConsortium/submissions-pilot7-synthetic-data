/** A reviewer publishes through GitHub's own discussion composer; the static site holds no credentials. */
import { reviewComment } from "./review-comment.js";

// GitHub documents no limit for prefilled links; browsers and proxies reject very long ones, so stay below 8 KB.
export const LINK_LIMIT = 8000;
const TITLE_LIMIT = 200;

/** The configured GitHub composer, or null when the site keeps the copy-and-paste route. */
export function reviewDestination(config) {
  let url;
  try { url = new URL(config?.review_url || ""); }
  catch { return null; }
  const parts = url.pathname.split("/").filter(Boolean);
  if (url.origin !== "https://github.com" || parts.length < 3 || parts.at(-2) !== "discussions" || parts.at(-1) !== "new") return null;
  return { repo: parts.slice(0, -2).join("/"), url: `${url.origin}/${parts.slice(0, -1).join("/")}` };
}

export function reviewTitle(model, issue) {
  const variable = issue.dataset + (issue.variable ? "." + issue.variable : "");
  const title = `Review: ${model.id} ${variable} - ${issue.title}`;
  return title.length > TITLE_LIMIT ? title.slice(0, TITLE_LIMIT - 3).trimEnd() + "..." : title;
}

function composer(base, title, body) {
  const url = new URL(base);
  url.searchParams.set("title", title);
  if (body) url.searchParams.set("body", body); else url.searchParams.delete("body");
  return url.href;
}

/** Prefill GitHub's new-discussion composer with one assessment; the reviewer still selects Start discussion. */
export function reviewDiscussion(config, model, issue, review, pageUrl) {
  if (!reviewDestination(config)) throw Error("Configure comments.review_url as a GitHub discussions/new link.");
  const body = reviewComment(model, issue, review, pageUrl), title = reviewTitle(model, issue);
  const url = composer(config.review_url, title, body);
  return url.length <= LINK_LIMIT
    ? { url, title, body, prefilled: true }
    : { url: composer(config.review_url, title, ""), title, body, prefilled: false };
}
