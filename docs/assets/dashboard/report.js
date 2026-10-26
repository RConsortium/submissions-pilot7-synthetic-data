/** Consistency comparisons and retained document viewers. */
import { ruleRow, ruleSearchText } from "./rule-findings.js";

/** Successful execution is a metric, not an inconsistency finding. */
export function consistencyFindings(report) {
  return [...(report.logic_checks || []), ...report.findings].filter(
    (finding) => finding.kind !== "executed",
  );
}

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
  function allFindings() {
    return consistencyFindings(ctx.report);
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
    return `<tr data-finding-id="${esc(f.id)}"><th scope="row"><button class="text-link" data-finding="${esc(f.id)}">${esc(f.dataset + (f.variable ? "." + f.variable : ""))}</button></th><td>${esc(comparisons[f.comparison] || "Source documents")}</td><td><span class="status ${f.kind === "inconsistent" ? "attention" : "neutral"}">${esc(f.status)}</span><h3>${esc(f.title)}</h3><p>${esc(f.observation)}</p></td><td><details class="finding-trace"><summary>Trace evidence</summary><div class="finding-evidence"><section><h4>yamaa specification</h4><pre>${esc(f.spec.excerpt || "See specification lines.")}</pre>${f.spec.url ? link(f.spec.url, "Specification lines") : ""}</section><section><h4>Source documents</h4>${f.source.path ? `<p>${esc(f.source.path)} / ${esc(f.source.section)}</p><blockquote>${esc(f.source.excerpt)}</blockquote>${sourceButton(f)}` : `<p>${esc(f.source.excerpt)}</p>`}</section><section><h4>Dataset evidence</h4><p>${esc(f.data?.summary || "Inspect records in the workspace.")}</p><small>${esc(f.data?.path || "")}</small><button class="text-link" data-finding="${esc(f.id)}">Open evidence in workspace</button></section>${f.recommendation ? `<section><h4>Review assessment</h4><p>${esc(f.recommendation)}</p></section>` : ""}</div></details></td></tr>`;
  }
  function findingRows() {
    const items = findingItems();
    return `<p class="result-count" role="status">${items.length} of ${allFindings().length} findings</p><div class="overview-table consistency-table" role="region" aria-label="Consistency findings" tabindex="0"><table class="review-table"><thead><tr><th scope="col">Dataset / variable</th><th scope="col">Comparison</th><th scope="col">Finding / status</th><th scope="col">Evidence</th></tr></thead><tbody>${items.length ? items.map((f) => (f.rule ? ruleRow(f) : findingRow(f))).join("") : '<tr><td colspan="4">No findings match. Clear the filters to see all findings.</td></tr>'}</tbody></table></div>`;
  }
  function findingsView() {
    const { state, esc } = ctx;
    return `<div class="report-filters"><label class="search-field"><span class="field-label">Search findings</span><input id="finding-search" type="search" value="${esc(state.findingSearch)}" placeholder="Variable, dataset, document or phrase..."></label><label class="select-field">Comparison<select id="finding-comparison"><option value="">All comparisons</option>${Object.entries(
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
