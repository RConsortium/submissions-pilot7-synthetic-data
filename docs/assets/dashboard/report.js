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

export function createReport(ctx) {
  const comparisons = {
    input_output: "Input -> output logic",
    source_documents: "Source documents",
    documented_rules: "Documented rules",
  };
  const allFindings = () => consistencyFindings(ctx.report);
  function findingItems() {
    const { state, report } = ctx,
      q = state.findingSearch.toLowerCase();
    const scope = (i) =>
      [i.dataset, i.variable, `${i.dataset}.${i.variable}`]
        .map((v) => v.toLowerCase())
        .includes(q);
    const exactScope = q && allFindings().some(scope);
    return allFindings().filter(
      (i) =>
        (!state.kind || i.kind === state.kind) &&
        (!state.comparison || i.comparison === state.comparison) &&
        (!state.critical || criticalFinding(i).status === state.critical) &&
        (!q ||
          (exactScope
            ? scope(i)
            : issueSearchText(i, report).toLowerCase().includes(q))),
    );
  }
  function findingRows() {
    const items = findingItems(),
      checks = new Set(items.flatMap((i) => i.check_ids)).size;
    return `<p class="result-count" role="status">${items.length} of ${allFindings().length} issue${allFindings().length === 1 ? "" : "s"} &middot; ${checks} supporting check${checks === 1 ? "" : "s"}</p><div class="overview-table consistency-table" role="region" aria-label="Consistency findings" tabindex="0"><table class="review-table"><thead><tr><th scope="col">Dataset / variable</th><th scope="col">Status</th><th scope="col">Critical finding</th><th scope="col">Type</th><th scope="col">Issue</th><th scope="col">Evidence</th></tr></thead><tbody>${items.length ? items.map((i) => issueRow(i, ctx.report)).join("") : '<tr><td colspan="6">No issues match. Clear the filters to see all issues.</td></tr>'}</tbody></table></div>`;
  }
  function findingsView() {
    const { state, esc } = ctx;
    function select(id, label, entries, selected) {
      return `<label class="select-field">${label}<select id="${id}"><option value="">All</option>${entries.map(([key, text]) => `<option value="${key}" ${selected === key ? "selected" : ""}>${esc(text)}</option>`).join("")}</select></label>`;
    }
    const entries = (values) => values.map((v) => [v, v.replaceAll("_", " ")]);
    return `<div class="report-filters"><label class="search-field"><span class="field-label">Search issues</span><input id="finding-search" type="search" value="${esc(state.findingSearch)}" placeholder="Variable, issue, document or rule..."></label>${select("finding-comparison", "Comparison", Object.entries(comparisons), state.comparison)}${select("finding-kind", "Issue type", entries(KINDS), state.kind)}${select("finding-critical", "Critical finding", Object.entries(CRITICAL_LABELS), state.critical)}<button class="button" id="clear-findings">Clear filters</button></div><div id="finding-results">${findingRows()}</div>`;
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
    host.innerHTML = `<aside class="trace-workspace-note" aria-label="Source evidence"><div><strong>${esc(issue.title)}</strong><p>${esc(impactText(issue, report))}</p></div><button class="button" data-trace-issue="${esc(issue.id)}">Trace evidence</button><button class="text-link" id="close-evidence" aria-label="Close source evidence">Clear finding</button></aside>`;
  }
  return {
    allFindings,
    findingItems,
    findingRows,
    findingsView,
    drawer,
  };
}
