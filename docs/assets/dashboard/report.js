/** Consistency comparisons and retained document viewers. */
import { reviewSummary, ruleRow, ruleSearchText } from "./rule-findings.js";

const KINDS = [
  "conflict",
  "divergence",
  "gap",
  "evidence",
  "inconsistent",
  "unclear",
  "missing_evidence",
  "not_reviewed",
  "executed",
];
export function createReport(ctx) {
  const comparisons = {
    input_output: "Input -> output logic",
    source_documents: "Source documents",
    documented_rules: "Documented rules",
  };
  function allFindings() {
    return [...(ctx.report.logic_checks || []), ...ctx.report.findings];
  }
  function findingItems() {
    const { state } = ctx;
    const q = state.findingSearch.toLowerCase();
    return allFindings().filter(
      (f) =>
        (!state.kind || f.kind === state.kind) &&
        (!state.comparison || f.comparison === state.comparison) &&
        [
          f.dataset,
          f.variable,
          f.title,
          f.observation,
          f.source.path,
          f.source.excerpt,
          f.spec.excerpt,
          f.data?.summary,
          comparisons[f.comparison],
          f.rule ? ruleSearchText(f) : "",
        ]
          .join(" ")
          .toLowerCase()
          .includes(q),
    );
  }
  function sourceButton(f, label = "View source") {
    const { report, esc, resource, link } = ctx;
    const doc = report.documents.find(
      (d) => d.path === f.source.path && d.available,
    );
    if (doc) {
      const section = f.source.url.split("#")[1] || "";
      return `<button class="text-link" data-document="${esc(doc.path)}" data-document-section="${esc(section)}">${esc(label)}</button>`;
    }
    return f.source.url
      ? link(
          f.source.url.startsWith("http")
            ? f.source.url
            : resource(f.source.url),
          label,
        )
      : "";
  }
  function findingRow(f) {
    const { esc, link } = ctx;
    return `<tr><th scope="row"><button class="text-link" data-finding="${esc(f.id)}">${esc(f.dataset + (f.variable ? "." + f.variable : ""))}</button></th><td>${esc(comparisons[f.comparison] || "Source documents")}</td><td><pre>${esc(f.spec.excerpt || "See specification lines.")}</pre>${link(f.spec.url, "Specification lines")}</td><td><p>${esc(f.data?.summary || "Inspect records in the workspace.")}</p><small>${esc(f.data?.path || "")}</small><button class="text-link" data-finding="${esc(f.id)}">Open evidence in workspace</button></td><td>${f.source.path ? `<p>${esc(f.source.path)} / ${esc(f.source.section)}</p><blockquote>${esc(f.source.excerpt)}</blockquote>${sourceButton(f)}` : esc(f.source.excerpt)}</td><td><span class="status ${f.kind === "inconsistent" ? "attention" : "neutral"}">${esc(f.status)}</span><h3>${esc(f.title)}</h3><p>${esc(f.observation)}</p><p>${esc(f.recommendation)}</p></td></tr>`;
  }
  function findingRows() {
    const items = findingItems();
    return `<p class="result-count" role="status">${items.length} of ${allFindings().length} comparisons and review tasks</p><div class="overview-table consistency-table" role="region" aria-label="Consistency comparisons" tabindex="0"><table class="review-table"><thead><tr><th scope="col">Dataset / variable</th><th scope="col">Comparison</th><th scope="col">yamaa specification</th><th scope="col">Observed dataset</th><th scope="col">Source-document information</th><th scope="col">Difference / review status</th></tr></thead><tbody>${items.length ? items.map((f) => (f.rule ? ruleRow(f) : findingRow(f))).join("") : '<tr><td colspan="6">No comparisons match. Clear the filters to see all comparisons and review tasks.</td></tr>'}</tbody></table></div>`;
  }
  function findingsView() {
    const { report, state, esc } = ctx;
    return `<div class="section-heading"><div><h2>Consistency review</h2><p>Compare yamaa input -> output rules and source-document information with the derived datasets. Each documented-rule finding cites one consistency rule and quotes the document and the specification.</p></div></div><p class="result-count">Execution and reference agreement are recorded separately. ${esc(report.coverage.narrative)}</p>${reviewSummary(report.verification)}<div class="report-filters"><label class="search-field"><span class="field-label">Find a variable, dataset, document or phrase</span><input id="finding-search" type="search" value="${esc(state.findingSearch)}" placeholder="For example: ASTDT, imputation, Define-XML..."></label><label class="select-field">Comparison<select id="finding-comparison"><option value="">All comparisons</option>${Object.entries(
      comparisons,
    )
      .map(
        ([key, label]) =>
          `<option value="${key}" ${state.comparison === key ? "selected" : ""}>${esc(label)}</option>`,
      )
      .join(
        "",
      )}</select></label><label class="select-field">Review status<select id="finding-kind"><option value="">All statuses</option>${KINDS.map((k) => `<option value="${k}" ${state.kind === k ? "selected" : ""}>${k.replaceAll("_", " ")}</option>`).join("")}</select></label><button class="button" id="clear-findings">Clear filters</button></div><div id="finding-results">${findingRows()}</div>`;
  }
  function drawer() {
    const { state, esc, byId, root } = ctx;
    const f = allFindings().find((x) => x.id === state.evidence),
      host = byId("evidence-drawer");
    if (!host) return;
    root().classList.toggle("evidence-open", Boolean(f));
    if (!f) {
      host.innerHTML = "";
      return;
    }
    host.innerHTML = `<aside class="evidence-drawer" aria-label="Source evidence"><header><div><span class="eyebrow">CONSISTENCY EVIDENCE</span><h2>${esc(f.dataset + (f.variable ? "." + f.variable : ""))}</h2></div><button class="button" id="close-evidence" aria-label="Close source evidence">Close</button></header><h3>${esc(f.title)}</h3><p>${esc(f.source.path)} / ${esc(f.source.section)}</p><blockquote>${esc(f.source.excerpt)}</blockquote><p>${esc(f.data?.summary || "")}</p><p>${esc(f.recommendation)}</p><div class="finding-actions">${sourceButton(f, "Open cited source")}<button class="button" data-comment>Comment on this finding</button></div></aside>`;
  }
  return { allFindings, findingItems, findingRows, findingsView, drawer };
}
