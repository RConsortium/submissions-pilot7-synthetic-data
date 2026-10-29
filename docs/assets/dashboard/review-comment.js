/** A reviewer can paste this assessment into the shared GitHub discussion. */
import { AGREEMENTS, CRITICALITIES } from "./review-drafts.js";

export function reviewComment(model, issue, review, pageUrl) {
  if (!Object.hasOwn(AGREEMENTS, review.agreement) ||
      !Object.hasOwn(CRITICALITIES, review.criticality))
    throw Error("Choose both an agreement assessment and a criticality assessment.");
  const url = new URL(pageUrl);
  url.search = "";
  url.searchParams.set("v", model.revision.slice(0, 7));
  const variable = issue.dataset + (issue.variable ? "." + issue.variable : "");
  url.hash = `${model.id}/overview/${issue.dataset}?findingSearch=${encodeURIComponent(variable)}`;
  return [
    `## Review: ${variable} - ${issue.title}`,
    "", `**Agreement:** ${AGREEMENTS[review.agreement]}`,
    `**Criticality:** ${CRITICALITIES[review.criticality]}`,
    "", review.comment.trim() || "No additional comments.",
    "", `**Study:** ${model.id}`,
    `**Finding:** \`${issue.id}\``,
    `**Evidence revision:** \`${model.revision}\``,
    `**Supporting checks:** ${issue.check_ids.map((id) => "`" + id + "`").join(", ")}`,
    `[Open finding context](${url.href})`,
  ].join("\n");
}
