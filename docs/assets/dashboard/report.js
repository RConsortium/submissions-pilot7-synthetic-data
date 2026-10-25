/** Consistency comparisons and retained document viewers. */
export function createReport(ctx) {
  const comparisons = {
    input_output: "Input -> output logic",
    source_documents: "Source documents",
  };
  function allFindings() {
    return [...(ctx.report.logic_checks || []), ...ctx.report.findings];
  }
  function findingItems() {
    const { state } = ctx;
    const q = state.findingSearch.toLowerCase();
    return allFindings().filter((f) =>
      (!state.kind || f.kind === state.kind) &&
      (!state.comparison || f.comparison === state.comparison) &&
      [f.dataset, f.variable, f.title, f.observation, f.source.path,
        f.source.excerpt, f.spec.excerpt, f.data?.summary, comparisons[f.comparison]]
        .join(" ").toLowerCase().includes(q),
    );
  }
  function sourceButton(f, label = "View source") {
    const { report, esc, resource, link } = ctx;
    const doc = report.documents.find((d) => d.path === f.source.path && d.available);
    if (doc) {
      const section = f.source.url.split("#")[1] || "";
      return `<button class="text-link" data-document="${esc(doc.path)}" data-document-section="${esc(section)}" data-document-mode="${doc.name.endsWith('.xml') ? 'reading' : 'original'}">${esc(label)}</button>`;
    }
    return f.source.url ? link(f.source.url.startsWith("http") ? f.source.url : resource(f.source.url), label) : "";
  }
  function findingRows() {
    const { esc, link } = ctx;
    const items = findingItems();
    return `<p class="result-count" role="status">${items.length} of ${allFindings().length} comparisons and review tasks</p><div class="overview-table consistency-table" role="region" aria-label="Consistency comparisons" tabindex="0"><table class="review-table"><thead><tr><th scope="col">Dataset / variable</th><th scope="col">Comparison</th><th scope="col">yamaa specification</th><th scope="col">Observed dataset</th><th scope="col">Source-document information</th><th scope="col">Difference / review status</th></tr></thead><tbody>${items.length ? items.map((f) => `<tr><th scope="row"><button class="text-link" data-finding="${esc(f.id)}">${esc(f.dataset + (f.variable ? "." + f.variable : ""))}</button></th><td>${esc(comparisons[f.comparison] || "Source documents")}</td><td><pre>${esc(f.spec.excerpt || "See specification lines.")}</pre>${link(f.spec.url, "Specification lines")}</td><td><p>${esc(f.data?.summary || "Inspect records in the workspace.")}</p><small>${esc(f.data?.path || "")}</small><button class="text-link" data-finding="${esc(f.id)}">Open evidence in workspace</button></td><td>${f.source.path ? `<p>${esc(f.source.path)} / ${esc(f.source.section)}</p><blockquote>${esc(f.source.excerpt)}</blockquote>${sourceButton(f)}` : esc(f.source.excerpt)}</td><td><span class="status ${f.kind === "inconsistent" ? "attention" : "neutral"}">${esc(f.status)}</span><h3>${esc(f.title)}</h3><p>${esc(f.observation)}</p><p>${esc(f.recommendation)}</p></td></tr>`).join("") : '<tr><td colspan="6">No comparisons match. Clear the filters to see all comparisons and review tasks.</td></tr>'}</tbody></table></div>`;
  }
  function findingsView() {
    const { report, state, esc } = ctx;
    return `<div class="section-heading"><div><h2>Consistency review</h2><p>Compare yamaa input -> output rules and source-document information with the derived datasets.</p></div></div><p class="result-count">Execution and reference agreement are recorded separately. ${esc(report.coverage.narrative)}</p><div class="report-filters"><label class="search-field"><span class="field-label">Find a variable, dataset, document or phrase</span><input id="finding-search" type="search" value="${esc(state.findingSearch)}" placeholder="For example: ASTDT, imputation, Define-XML..."></label><label class="select-field">Comparison<select id="finding-comparison"><option value="">All comparisons</option>${Object.entries(comparisons).map(([key, label]) => `<option value="${key}" ${state.comparison === key ? "selected" : ""}>${esc(label)}</option>`).join("")}</select></label><label class="select-field">Review status<select id="finding-kind"><option value="">All statuses</option>${["inconsistent", "unclear", "missing_evidence", "not_reviewed", "executed"].map((k) => `<option value="${k}" ${state.kind === k ? "selected" : ""}>${k.replaceAll("_", " ")}</option>`).join("")}</select></label><button class="button" id="clear-findings">Clear filters</button></div><div id="finding-results">${findingRows()}</div>`;
  }
  function materialsView() {
    const { model, report, state, esc, resource, sourceUrl, link } = ctx;
    const doc = report.documents.find((d) => d.path === state.document) || report.documents.find((d) => d.available);
    const reading = state.documentMode === "reading" && doc?.reading;
    const path = reading || doc?.view || doc?.original;
    const section = state.documentSection || "";
    const fragment = section ? (doc?.name.endsWith(".pdf") && !reading && /^page-\d+$/.test(section) ? "#page=" + section.slice(5) : "#" + encodeURIComponent(section)) : "";
    return `<div class="section-heading"><div><h2>Source documents</h2><p>View original PDF pages, Excel sheet tables and XML rendered with the publisher's retained stylesheet.</p></div>${link(sourceUrl(`${model.id}/spec/source/manifest.json`), "Source manifest", "button")}</div><div class="report-filters"><label class="select-field">Document<select id="document-select">${report.documents.map((d) => `<option value="${esc(d.path)}" ${d === doc ? "selected" : ""}>${esc(d.name)}${d.available ? "" : " (unavailable)"}</option>`).join("")}</select></label>${doc?.reading ? `<label class="select-field">View<select id="document-mode"><option value="original">${esc(doc.view_label || "Original document")}</option><option value="reading" ${reading ? "selected" : ""}>Extracted reading copy</option></select></label>` : ""}</div>${doc ? `<section class="source-viewer" aria-label="Document viewer"><div class="source-viewer-heading"><h3>${esc(doc.name)}</h3><p>${esc(doc.path)}</p><div class="finding-actions">${doc.available ? link(resource(doc.original), "Original document", "button") : ""}${doc.upstream?.url ? link(doc.upstream.url, "Published upstream source") : ""}</div></div>${doc.available && path ? `<iframe id="source-frame" title="${esc((reading ? "Extracted reading copy" : doc.view_label || "Original document") + ": " + doc.name)}" src="${esc(resource(path) + fragment)}" ${doc.name.endsWith(".pdf") && !reading ? "" : 'sandbox="allow-scripts"'}></iframe>` : '<p class="empty-state">Source unavailable. The declared document is not retained in this package.</p>'}</section>` : '<p class="empty-state">No source documents have been declared for this study.</p>'}`;
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
  return { allFindings, findingItems, findingRows, findingsView, materialsView, drawer };
}
