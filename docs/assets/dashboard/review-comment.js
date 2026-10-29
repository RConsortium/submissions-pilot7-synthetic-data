/** A reviewer can paste this assessment into the shared GitHub discussion. */
import { AGREEMENTS, CRITICALITIES, SIDES, draftLabel } from "./review-drafts.js";

const variableName = (issue) => issue.dataset + (issue.variable ? "." + issue.variable : "");

function contextUrl(model, issue, pageUrl) {
  const url = new URL(pageUrl);
  url.search = "";
  url.searchParams.set("v", model.revision.slice(0, 7));
  url.hash = `${model.id}/overview/${issue.dataset}?findingSearch=${encodeURIComponent(variableName(issue))}`;
  return url.href;
}

export function reviewComment(model, issue, review, pageUrl) {
  if (!Object.hasOwn(AGREEMENTS, review.agreement) ||
      !Object.hasOwn(CRITICALITIES, review.criticality))
    throw Error("Choose both an agreement assessment and a criticality assessment.");
  return [
    `## Review: ${variableName(issue)} - ${issue.title}`,
    "", `**Agreement:** ${AGREEMENTS[review.agreement]}`,
    `**Criticality:** ${CRITICALITIES[review.criticality]}`,
    ...(SIDES[review.side] ? [`**Which side is right:** ${SIDES[review.side]}`] : []),
    "", review.comment.trim() || "No additional comments.",
    "", `**Study:** ${model.id}`,
    `**Finding:** \`${issue.id}\``,
    `**Evidence revision:** \`${model.revision}\``,
    `**Supporting checks:** ${issue.check_ids.map((id) => "`" + id + "`").join(", ")}`,
    `[Open finding context](${contextUrl(model, issue, pageUrl)})`,
  ].join("\n");
}

/** Every assessment the reviewer started in this browser, as one document to hand over. */
export function reviewLedgerDocument(model, entries, counts, pageUrl, context = {}) {
  const lines = [
    `# Review of ${model.title} (${model.id})`,
    "", "**Reviewer:** (add your name)",
    `**Date:** ${context.date || new Date().toISOString().slice(0, 10)}`,
    `**Listed with:** ${context.listing || "no filters"}`,
    `**Evidence revision:** \`${model.revision}\``,
    `**Reviewed in this browser:** ${counts.started} of ${counts.listed} listed findings; ${counts.reviewed} with both decisions, ${counts.drafts} still drafts${counts.stale ? `, ${counts.stale} with changed evidence` : ""}.`,
    "", "These assessments are a reviewer's own record. They do not resolve a finding or approve a dataset.",
  ];
  for (const { issue, draft } of entries) {
    if (draft.status === "unreviewed") continue;
    lines.push("", `## ${variableName(issue)} - ${issue.title}`, "",
      `**Agreement:** ${AGREEMENTS[draft.agreement] || "(not chosen)"}`,
      `**Criticality:** ${CRITICALITIES[draft.criticality] || "(not chosen)"}`,
      ...(SIDES[draft.side] ? [`**Which side is right:** ${SIDES[draft.side]}`] : []),
      `**Status:** ${draftLabel(draft)}${draft.stale ? " (evidence changed)" : ""}`,
      "", draft.comment.trim() || "No additional comments.",
      "", `**Finding:** \`${issue.id}\``,
      `**Supporting checks:** ${issue.check_ids.map((id) => "`" + id + "`").join(", ")}`,
      `[Open finding context](${contextUrl(model, issue, pageUrl)})`);
  }
  return lines.join("\n") + "\n";
}
