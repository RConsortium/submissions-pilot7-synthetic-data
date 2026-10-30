/** Issue listing and workspace evidence use the same validated review model. */
import {
  criticalFinding,
  CRITICAL_LABELS,
  findIssue,
  impactText,
  issueRow,
  issueSearchText,
  readReview,
} from "./issues.js";
import { reviewLedger } from "./review-drafts.js";

export const consistencyFindings = (report) => readReview(report).issues;
const KINDS = [
  "conflict",
  "divergence",
  "gap",
  "evidence",
  "inconsistent",
  "unclear",
  "missing_evidence",
  "not_reviewed",
];
/** The reviewer's own progress, kept in this browser and never part of a shared link. */
export const AGENT_REVIEW = {
  agreed: "Agreed",
  disputed: "Disputed",
  stale: "Stale",
  mixed: "Mixed",
  not_reviewed: "Not adjudicated",
};
export const YOUR_REVIEW = {
  unreviewed: "Not reviewed",
  draft: "Draft",
  reviewed: "Both decisions saved",
};

export function createReport(ctx) {
  const comparisons = {
    input_output: "Input -> output logic",
    source_documents: "Source documents",
    documented_rules: "Documented rules",
  };
  const allFindings = () => consistencyFindings(ctx.report);
  const draftOf = (issue) => ctx.drafts?.load(ctx.model.id, issue, ctx.report);
  /** Comparison, type, criticality and own-review filters; the search is applied separately. */
  function filtered(i) {
    const { state } = ctx;
    return (
      (!state.kind || i.kind === state.kind) &&
      (!state.comparison || i.comparison === state.comparison) &&
      (!state.critical || criticalFinding(i).status === state.critical) &&
      (!state.agentReview || i.review === state.agentReview) &&
      (!state.yourReview || !ctx.drafts || draftOf(i).status === state.yourReview)
    );
  }
  function findingItems() {
    const { state, report } = ctx,
      q = state.findingSearch.toLowerCase();
    const scope = (i) =>
      [i.dataset, i.variable, `${i.dataset}.${i.variable}`]
        .map((v) => v.toLowerCase())
        .includes(q);
    // A dataset name scopes exactly even when it has no issue, so a
    // zero-count dataset chip lists nothing instead of text matches.
    const exactScope = q && (allFindings().some(scope) ||
      (ctx.model?.datasets || []).some((d) => d.name.toLowerCase() === q));
    // Critical findings first, then the ones needing assessment; within each, findings the
    // adjudicating agent disputed, or whose decision is stale or mixed, come last. The report
    // order holds otherwise: a measured count compares the documented rule as written.
    const rank = { yes: 0, needs_review: 1, no: 2 },
      order = (i) => rank[criticalFinding(i).status] * 2 + (["disputed", "stale", "mixed"].includes(i.review) ? 1 : 0);
    return allFindings().filter(
      (i) =>
        filtered(i) &&
        (!q ||
          (exactScope
            ? scope(i)
            : issueSearchText(i, report).toLowerCase().includes(q))),
    ).sort((a, b) => order(a) - order(b));
  }
  /** Filtered issues per dataset, in the study's dataset order, then by first appearance. */
  function datasetCounts() {
    const counts = new Map(
      (ctx.model?.datasets || []).map((d) => [d.name, 0]),
    );
    for (const i of allFindings()) {
      if (!counts.has(i.dataset)) counts.set(i.dataset, 0);
      if (filtered(i)) counts.set(i.dataset, counts.get(i.dataset) + 1);
    }
    return counts;
  }
  /** Dataset chips scope the listing through the exact-name search. */
  function datasetStrip() {
    const { state, esc } = ctx,
      selected = state.findingSearch.trim().toUpperCase(),
      counts = datasetCounts(),
      chip = (name, count, label = name) =>
        `<button type="button" class="dataset-chip" data-finding-dataset="${esc(name)}" aria-pressed="${name.toUpperCase() === selected}">${esc(label)} <span class="chip-count">${count}</span></button>`;
    return `<div class="finding-datasets" role="group" aria-label="Findings by dataset"><span class="field-label">By dataset</span>${chip("", [...counts.values()].reduce((a, b) => a + b, 0), "All")}${[...counts].map(([name, count]) => chip(name, count)).join("")}</div>`;
  }
  /** The reviewer's assessments of the listed findings, with their counts. */
  function ledger() {
    return reviewLedger(ctx.drafts, ctx.model.id, findingItems(), ctx.report);
  }
  /** What this reviewer has done with the listed findings, and the way to hand it over. */
  function ledgerStrip() {
    if (!ctx.drafts) return "";
    const { counts } = ledger(),
      parts = [`${counts.reviewed} with both decisions`, `${counts.drafts} draft${counts.drafts === 1 ? "" : "s"}`];
    if (counts.shared) parts.push(`${counts.shared} opened in GitHub or copied`);
    if (counts.stale) parts.push(`${counts.stale} with changed evidence`);
    return `<div id="review-ledger" class="review-ledger" role="group" aria-label="Your reviews"><span class="field-label">Your reviews</span><strong>${counts.started} of ${counts.listed}</strong> listed${counts.started ? ` <span class="ledger-detail">(${parts.join("; ")})</span>` : ""}<span class="ledger-actions"><button type="button" class="text-link" data-review-ledger="copy" ${counts.started ? "" : "disabled"}>Copy your reviews</button><button type="button" class="text-link" data-review-ledger="download" ${counts.started ? "" : "disabled"}>Download your reviews</button></span><span class="ledger-feedback" role="status" aria-live="polite"></span></div>`;
  }
  function findingRows() {
    const items = findingItems(),
      checks = new Set(items.flatMap((i) => i.check_ids)).size;
    return `${datasetStrip()}${ledgerStrip()}<p class="result-count" role="status">${items.length} of ${allFindings().length} issue${allFindings().length === 1 ? "" : "s"} &middot; ${checks} supporting check${checks === 1 ? "" : "s"}</p><div class="overview-table consistency-table" role="region" aria-label="Consistency findings" tabindex="0"><table class="review-table"><thead><tr><th scope="col">Dataset / variable</th><th scope="col">Status</th><th scope="col">Critical finding</th><th scope="col">Type</th><th scope="col">Documented rule vs data</th><th scope="col">Issue</th><th scope="col">Evidence</th></tr></thead><tbody>${items.length ? items.map((i) => issueRow(i, ctx.report)).join("") : '<tr><td colspan="7">No issues match. Clear the filters to see all issues.</td></tr>'}</tbody></table></div>`;
  }
  /** The two decisions and the finding types, where the reviewer meets them. */
  function howToReview() {
    const { esc } = ctx, guide = ctx.site ? new URL("review/findings/", ctx.site).href : "";
    // Open until the reviewer has started a review of this study, then out of the way.
    const open = !ctx.drafts || reviewLedger(ctx.drafts, ctx.model.id, allFindings(), ctx.report).counts.started === 0;
    return `<details class="review-howto"${open ? " open" : ""}><summary>How to review a finding</summary><div><p>Each row is one finding that asks for two decisions. <strong>Do you agree with this finding?</strong> The ADaM data differs from a verified Define-XML rule in the way the row describes. <strong>Is this finding critical?</strong> A critical issue could materially affect analysis results or their interpretation. Start with <strong>Critical finding: Yes</strong>, then <strong>Needs review</strong>; the automated criticality rates the kind of discrepancy, not the number of subjects.</p><p><strong>Types.</strong> Conflict: documents disagree with the data or with one another. Divergence: a documented rule is expressed differently in the specification. Gap: a rule or clause is undocumented. Evidence: a quoted passage was not found. Inconsistent: an input-to-output check failed. Unclear: a question the checks cannot settle. Missing evidence and not reviewed: authored questions. Agent agreement is not resolution.</p><p>Open <strong>Start review</strong> for the finding's evidence, record both decisions under <strong>Human Review</strong>, then share them on GitHub or hand them over from <strong>Your reviews</strong> above the table.${guide ? ` <a class="text-link" href="${esc(guide)}">Read the full guide</a>` : ""}</p></div></details>`;
  }
  function findingsView() {
    const { state, esc } = ctx;
    function select(id, label, entries, selected) {
      return `<label class="select-field">${label}<select id="${id}"><option value="">All</option>${entries.map(([key, text]) => `<option value="${key}" ${selected === key ? "selected" : ""}>${esc(text)}</option>`).join("")}</select></label>`;
    }
    const entries = (values) => values.map((v) => [v, v.replaceAll("_", " ")]);
    return `${howToReview()}<div class="report-filters"><label class="search-field"><span class="field-label">Search issues</span><input id="finding-search" type="search" value="${esc(state.findingSearch)}" placeholder="Variable, issue, document or rule..."></label>${select("finding-comparison", "Comparison", Object.entries(comparisons), state.comparison)}${select("finding-kind", "Issue type", entries(KINDS), state.kind)}${select("finding-critical", "Critical finding", Object.entries(CRITICAL_LABELS), state.critical)}${select("finding-agent", "Agent review", Object.entries(AGENT_REVIEW), state.agentReview || "")}${ctx.drafts ? select("finding-review", "Your review", Object.entries(YOUR_REVIEW), state.yourReview || "") : ""}<button class="button" id="clear-findings">Clear filters</button></div><div id="finding-results">${findingRows()}</div>`;
  }
  function drawer() {
    const { state, esc, byId, root, report } = ctx;
    const issue = findIssue(report, state.evidence),
      host = byId("evidence-drawer");
    if (!host) return;
    root().classList.remove("evidence-open");
    if (!issue) {
      host.innerHTML = "";
      return;
    }
    host.innerHTML = `<aside class="trace-workspace-note" aria-label="Source evidence"><div><strong>${esc(issue.title)}</strong><p>${esc(impactText(issue, report))}</p></div><button class="button" data-trace-issue="${esc(issue.id)}">Start review</button><button class="text-link" id="close-evidence" aria-label="Close source evidence">Clear finding</button></aside>`;
  }
  return {
    allFindings,
    findingItems,
    findingRows,
    findingsView,
    ledger,
    ledgerStrip,
    drawer,
  };
}
