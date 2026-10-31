/** Issue listing and workspace evidence use the same validated review model. */
import {
  criticalFinding,
  CRITICAL_LABELS,
  findIssue,
  findingVariable,
  impactText,
  impactSummary,
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

/** One mapping serves input events, repainting and clearing the table filters. */
export const FINDING_FILTERS = {
  "finding-search": "findingSearch",
  "finding-dataset": "datasetSearch",
  "finding-variable": "variableSearch",
  "finding-agent": "agentReview",
  "finding-critical": "critical",
  "finding-kind": "kind",
  "finding-impact": "impactSearch",
  "finding-issue": "issueSearch",
  "finding-review": "yourReview",
};
const COLUMNS = [
  { key: "dataset", label: "Dataset", width: 110 },
  { key: "variable", label: "Variable", width: 145 },
  { key: "critical", label: "Critical finding", width: 135 },
  { key: "type", label: "Type", width: 135 },
  { key: "impact", label: "Documented rule vs data", width: 200, min: 140, max: 640 },
  { key: "issue", label: "Issue", width: 360, min: 240, max: 1600 },
  { key: "evidence", label: "Evidence", width: 165 },
];

export function createReport(ctx) {
  const comparisons = {
    input_output: "Input -> output logic",
    source_documents: "Source documents",
    documented_rules: "Documented rules",
    dataset_define: "Dataset vs Define-XML",
  };
  const allFindings = () => consistencyFindings(ctx.report);
  const draftOf = (issue) => ctx.drafts?.load(ctx.model.id, issue, ctx.report);
  let checkReport, ruleIds;
  function variableText(i) {
    if (checkReport !== ctx.report) {
      checkReport = ctx.report;
      ruleIds = new Map(readReview(checkReport).checks.map((c) => [c.id, c.rule?.id || ""]));
    }
    return [findingVariable(i), ...i.check_ids.map((id) => ruleIds.get(id) || "")].join(" ");
  }
  const matches = (text, query) => !query?.trim() ||
    text.toLowerCase().includes(query.trim().toLowerCase());
  /** Column filters combine; the global evidence search is applied separately. */
  function filtered(i) {
    const { state } = ctx;
    return (
      (!state.kind || i.kind === state.kind) &&
      (!state.comparison || i.comparison === state.comparison) &&
      (!state.critical || criticalFinding(i).status === state.critical) &&
      (!state.agentReview || i.review === state.agentReview) &&
      (!state.yourReview || !ctx.drafts || draftOf(i).status === state.yourReview) &&
      matches(i.dataset, state.datasetSearch) &&
      matches(variableText(i), state.variableSearch) &&
      matches(impactSummary(i), state.impactSearch) &&
      matches(`${i.title} ${i.summary}`, state.issueSearch)
    );
  }
  function findingItems() {
    const { state, report } = ctx,
      q = state.findingSearch.toLowerCase();
    const scope = (i) =>
      [i.dataset, i.variable, `${i.dataset}.${i.variable}`]
        .map((v) => v.toLowerCase())
        .includes(q);
    // Dataset and declared dataset.variable queries stay scoped even without
    // findings, rather than matching another variable's source context.
    const exactScope = q && (allFindings().some(scope) ||
      (ctx.model?.datasets || []).some((d) => d.name.toLowerCase() === q ||
        (ctx.model?.tables?.[d.output]?.columns || []).some(
          (c) => `${d.name}.${c.name}`.toLowerCase() === q)));
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
    return `<div id="review-ledger" class="review-ledger" role="group" aria-label="Your reviews"><span class="field-label">Your reviews</span><strong>${reviewLedger(ctx.drafts, ctx.model.id, allFindings(), ctx.report).counts.reviewed} of ${allFindings().length} reviewed in this study</strong> <span>(${counts.started} of ${counts.listed} listed started)</span>${counts.started ? ` <span class="ledger-detail">(${parts.join("; ")})</span>` : ""}<span class="ledger-actions"><button type="button" class="text-link" data-review-ledger="copy" ${counts.started ? "" : "disabled"}>Copy your reviews</button><button type="button" class="text-link" data-review-ledger="download" ${counts.started ? "" : "disabled"}>Download your reviews</button></span><span class="ledger-feedback" role="status" aria-live="polite"></span></div>`;
  }
  /** Assessment limits remain visible without adding findings or measured impact. */
  function coverageGaps() {
    const items = Array.isArray(ctx.report?.coverage_items) ? ctx.report.coverage_items : [];
    if (!items.length) return "";
    const { esc } = ctx;
    return `<details class="coverage-note coverage-gaps"><summary>Study coverage gaps: ${items.length} check${items.length === 1 ? "" : "s"} not assessed</summary><p>These checks need additional evidence or a supported assessment. They are separate from the findings and do not establish a data discrepancy.</p><ul>${items.map((item) => {
      const scope = [item.dataset, item.variable].filter(Boolean).join(".") || "Study";
      return `<li><strong>${esc(scope)}</strong>: ${esc(item.reason || item.title || "Assessment unavailable.")}</li>`;
    }).join("")}</ul></details>`;
  }
  function findingCount(items) {
    const { esc, state } = ctx,
      count = new Set(items.flatMap((i) => i.check_ids)).size;
    // Existing comparison-scoped links remain visible and can be cleared.
    const comparison = state.comparison ? ` <span class="active-comparison">Comparison: ${esc(comparisons[state.comparison] || state.comparison)} <button type="button" class="text-link" id="clear-finding-comparison" aria-label="Remove comparison filter">Remove</button></span>` : "";
    return `${items.length} of ${allFindings().length} issue${allFindings().length === 1 ? "" : "s"} &middot; ${count} supporting check${count === 1 ? "" : "s"}${comparison}`;
  }
  function findingBody(items) {
    return items.length ? items.map((i) => issueRow(i, ctx.report)).join("") : `<tr><td colspan="${COLUMNS.length}">No issues match. Clear the filters to see all issues.</td></tr>`;
  }
  function columnFilters() {
    const { esc, state } = ctx;
    function input(id, label, placeholder) {
      return `<input id="${id}" type="search" aria-label="Filter ${label}" placeholder="${placeholder}" value="${esc(state[FINDING_FILTERS[id]] || "")}">`;
    }
    function select(id, label, entries, empty = "All") {
      return `<select id="${id}" aria-label="Filter ${label}"><option value="">${empty}</option>${entries.map(([key, text]) => `<option value="${key}" ${state[FINDING_FILTERS[id]] === key ? "selected" : ""}>${esc(text)}</option>`).join("")}</select>`;
    }
    const filters = [
      input("finding-dataset", "Dataset", "Filter..."),
      input("finding-variable", "Variable", "Name or rule"),
      select("finding-critical", "Critical finding", Object.entries(CRITICAL_LABELS)),
      select("finding-kind", "Issue type", KINDS.map((v) => [v, v.replaceAll("_", " ")]), "All types"),
      input("finding-impact", "Documented rule vs data", "Count or result"),
      input("finding-issue", "Issue", "Title or summary"),
      ctx.drafts ? select("finding-review", "Your review", Object.entries(YOUR_REVIEW), "All reviews") : '<span class="sr-only">All evidence</span>',
    ];
    return `<tr class="finding-filters">${COLUMNS.map((c, n) => `<th scope="col" aria-label="${esc(c.label)}" data-label="${c.key === "evidence" ? "Your review" : c.label}"><span class="filter-label">${esc(c.label)}</span>${filters[n]}${c.min ? `<span class="column-resizer" data-resize-column="${c.key}" role="separator" tabindex="0" aria-label="Resize ${c.label} column" aria-orientation="vertical" aria-valuemin="${c.min}" aria-valuemax="${c.max}" aria-valuenow="${ctx.layout?.findingColumns?.[c.key] || c.width}"></span>` : ""}</th>`).join("")}</tr>`;
  }
  function findingTable(items) {
    const { esc } = ctx, widths = ctx.layout?.findingColumns || {},
      custom = Object.keys(widths).length > 0,
      width = (c) => widths[c.key] || c.width,
      total = COLUMNS.reduce((sum, c) => sum + width(c), 0);
    return `<div id="finding-table" class="overview-table consistency-table" data-finding-table role="region" aria-label="Consistency findings" tabindex="0"><table class="review-table" style="width:${custom ? total + "px" : "100%"};min-width:${custom ? 0 : total}px"><colgroup>${COLUMNS.map((c) => `<col data-column="${c.key}"${c.key === "issue" && !custom ? "" : ` style="width:${width(c)}px"`}>`).join("")}</colgroup><thead>${columnFilters()}</thead><tbody>${findingBody(items)}</tbody></table></div>`;
  }
  function findingRows() {
    const items = findingItems();
    return `${datasetStrip()}${ledgerStrip()}<p id="finding-count" class="result-count" role="status">${findingCount(items)}</p>${findingTable(items)}${coverageGaps()}`;
  }
  /** Keep the filter controls, focus, selection and column widths while rows change. */
  function refreshFindings() {
    const host = ctx.byId("finding-results");
    if (!host) return;
    const items = findingItems();
    host.querySelector("tbody").innerHTML = findingBody(items);
    ctx.byId("finding-count").innerHTML = findingCount(items);
    host.querySelector(".finding-datasets").outerHTML = datasetStrip();
    const strip = ctx.byId("review-ledger");
    if (strip) strip.outerHTML = ledgerStrip();
    for (const [id, field] of Object.entries(FINDING_FILTERS)) {
      const control = ctx.byId(id), value = ctx.state[field] || "";
      if (control && control.value !== value) control.value = value;
    }
  }
  /** A short reminder above the finding filters. */
  function howToReview() {
    return `<p class="review-howto">Open <strong>Start review</strong> for the finding's evidence, record both decisions under <strong>Human Review</strong>.</p>`;
  }
  function findingsView() {
    const { state, esc } = ctx;
    return `${howToReview()}<div class="finding-tools"><label class="search-field"><span class="field-label">Search issues</span><input id="finding-search" type="search" value="${esc(state.findingSearch)}" placeholder="Variable, issue, document or rule..."></label><label class="agent-filter"><span class="field-label">Agent review</span><select id="finding-agent" aria-label="Filter Status by agent review"><option value="">All agents</option>${Object.entries(AGENT_REVIEW).map(([key, label]) => `<option value="${key}" ${state.agentReview === key ? "selected" : ""}>${esc(label)}</option>`).join("")}</select></label><button type="button" class="text-link" id="clear-findings">Clear filters</button></div><div id="finding-results">${findingRows()}</div>`;
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
    refreshFindings,
    ledger,
    ledgerStrip,
    drawer,
  };
}
