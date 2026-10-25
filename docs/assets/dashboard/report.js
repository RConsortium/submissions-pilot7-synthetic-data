/** Components read the live application context at render time. */
export function createReport(ctx) {
  function findingItems() {
    const { report, state, dataset, source } = ctx;
    const q = state.findingSearch.toLowerCase();
    return report.findings.filter(
      (f) =>
        (!state.kind || f.kind === state.kind) &&
        [
          f.dataset,
          f.variable,
          f.title,
          f.observation,
          f.source.path,
          f.source.excerpt,
        ]
          .join(" ")
          .toLowerCase()
          .includes(q),
    );
  }
  function findingCards() {
    const { report, state, esc, resource, dataset, source, link } = ctx;
    const items = findingItems();
    return `<p class="result-count" role="status">${items.length} of ${report.findings.length} observations and review tasks</p>${items.length ? items.map((f) => `<article class="finding-card"><div class="finding-top"><span class="status ${f.kind === "inconsistent" ? "attention" : "neutral"}">${esc(f.kind.replaceAll("_", " "))}</span><code>${esc(f.dataset + (f.variable ? "." + f.variable : ""))}</code><span>${f.status}</span></div><h3>${esc(f.title)}</h3><p>${esc(f.observation)}</p><details><summary>Source evidence and review guidance</summary><blockquote>${esc(f.source.excerpt)}</blockquote><p><strong>${esc(f.source.path)}</strong> / ${esc(f.source.section)}</p><p>${esc(f.recommendation)}</p></details><div class="finding-actions"><button class="button primary" data-finding="${esc(f.id)}">Open evidence in workspace</button>${link(f.source.url.startsWith("http") ? f.source.url : resource(f.source.url || "report.json"), "Open source")}${link(f.spec.url, "Specification lines")}</div></article>`).join("") : '<div class="empty-state">No findings match. Clear the filters to see all review tasks.</div>'}`;
  }
  function findingsView() {
    const { report, state, esc, resource, dataset, link } = ctx;
    return `<div class="section-heading"><div><h2>Consistency verification report</h2><p>Source-backed observations to help a reviewer verify the package and derivation rules.</p></div>${link(resource("report.json"), "Download report JSON", "button")}</div><div class="coverage-note"><strong>Automated checks completed:</strong> ${report.checks.output_columns} output columns; ${report.checks.labels} exact labels checked against published Define-XML.<br><strong>Interpretation coverage:</strong> ${esc(report.coverage.narrative)} Published metadata: ${esc(report.coverage.define_xml)}. Detected differences require human review.</div><div class="report-filters"><label class="search-field"><span class="field-label">Find a variable, dataset, document or phrase</span><input id="finding-search" type="search" value="${esc(state.findingSearch)}" placeholder="For example: ASTDT, imputation, Define-XML..."></label><label class="select-field">Finding type<select id="finding-kind"><option value="">All types</option>${["inconsistent", "unclear", "missing_evidence", "not_reviewed"].map((k) => `<option value="${k}" ${state.kind === k ? "selected" : ""}>${k.replaceAll("_", " ")}</option>`).join("")}</select></label><button class="button" id="clear-findings">Clear filters</button></div><div id="finding-results">${findingCards()}</div>`;
  }
  function materialsView() {
    const { model, report, esc, resource, sourceUrl, source, link } = ctx;
    return `<div class="section-heading"><div><h2>Submission-package sources</h2><p>Retained original documents and searchable extracted reading copies. Source versions are recorded in the study manifest.</p></div>${link(sourceUrl(`${model.id}/spec/source/manifest.json`), "Source manifest", "button")}</div><div class="material-grid">${report.documents.map((d) => `<article class="material-card"><span class="eyebrow">${esc(d.role?.replaceAll("_", " ") || "SOURCE")}</span><h3>${esc(d.name)}</h3><p>${esc(d.path)}</p><div>${d.available ? link(resource(d.original), "Original document", "button") : '<span class="status attention">Source unavailable</span>'}${d.reading ? link(resource(d.reading), "Reading copy", "button") : ""}</div>${d.upstream?.url ? link(d.upstream.url, "Published upstream source") : ""}</article>`).join("")}</div>`;
  }
  function drawer() {
    const { report, state, esc, byId, root, resource, dataset, source, link } =
      ctx;
    const f = report.findings.find((x) => x.id === state.evidence),
      host = byId("evidence-drawer");
    if (!host) return;
    root().classList.toggle("evidence-open", Boolean(f));
    if (!f) {
      host.innerHTML = "";
      return;
    }
    host.innerHTML = `<aside class="evidence-drawer" aria-label="Source evidence"><header><div><span class="eyebrow">SOURCE EVIDENCE</span><h2>${esc(f.dataset + (f.variable ? "." + f.variable : ""))}</h2></div><button class="button" id="close-evidence" aria-label="Close source evidence">Close</button></header><h3>${esc(f.title)}</h3><p>${esc(f.source.path)} / ${esc(f.source.section)}</p><blockquote>${esc(f.source.excerpt)}</blockquote><p>${esc(f.recommendation)}</p><div class="finding-actions">${link(f.source.url.startsWith("http") ? f.source.url : resource(f.source.url || "report.json"), "Open cited source", "button")}${f.source.original ? link(resource(f.source.original), "Original document", "button") : ""}<button class="button" data-comment>Comment on this finding</button></div></aside>`;
  }

  return { findingItems, findingCards, findingsView, materialsView, drawer };
}
