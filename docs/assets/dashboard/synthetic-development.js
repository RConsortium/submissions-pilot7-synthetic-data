/** Measured development coverage and human review drafts for synthetic studies. */
import { esc } from "./ui.js";

const quantity = (n) => Number(n).toLocaleString("en-US");
const resource = (model, dataRoot, relative) =>
  new URL(`synthetic/${model.id}/${relative}`, dataRoot).href;
const badge = (label, kind = "attention") =>
  `<span class="report-status ${kind}">${esc(label)}</span>`;

function matrix(label, headings, rows) {
  return `<div class="report-table"><table class="report-matrix" aria-label="${esc(label)}"><thead><tr>${headings.map((h) => `<th scope="col">${esc(h)}</th>`).join("")}</tr></thead><tbody>${rows.join("")}</tbody></table></div>`;
}

export function developmentReport(model, dataRoot) {
  const d = model.development;
  if (!d || d.status !== "succeeded")
    return '<h2 id="analysis-development">Analysis development</h2><p>No successful study build is recorded at this revision.</p>';
  const findings = d.review.findings;
  const counts = (kind) => findings.filter((f) => f.kind === kind).length;
  const coverage = matrix("Analysis coverage", ["Analysis", "Support", "Available scope", "Review findings"],
    d.review.coverage.map((c) => `<tr><th scope="row">${esc(c.analysis)}</th><td>${badge(c.status, c.status === "supported" ? "neutral" : "attention")}</td><td>${esc(c.supported_scope)}</td><td>${c.findings.map((id) => `<a href="#finding-${esc(id)}">${esc(id)}</a>`).join(", ")}</td></tr>`));
  const datasets = matrix("Built synthetic datasets", ["Stage", "Dataset", "Records", "Columns", "Independent checks", "Specification"],
    d.datasets.map((r) => `<tr><td>${esc(r.section.toUpperCase())}</td><th scope="row">${esc(r.domain)}</th><td>${quantity(r.rows)}</td><td>${r.columns}</td><td>Keys / subjects: ${esc(r.key_subject_checks)}; XPT read-back: ${esc(r.xpt_roundtrip)}</td><td><a href="${esc(resource(model, dataRoot, r.spec_view))}">View YAML</a></td></tr>`));
  const cohort = matrix("Synthetic cohort", ["Planned treatment", "Subjects", "Safety subjects", "Source-summary deaths"],
    d.summaries.cohort.map((r) => `<tr><th scope="row">${esc(r.TRT01P)}</th><td>${quantity(r.subjects)}</td><td>${quantity(r.safety_subjects)}</td><td>${quantity(r.source_summary_deaths)}</td></tr>`));
  const rows = findings.map((f) => {
    const e = f.evidence;
    const measured = e
      ? `<p><strong>Measured evidence:</strong> ${quantity(e.count)} / ${quantity(e.denominator)} ${esc(e.unit)}; ${quantity(e.subject_count)} distinct subjects.${e.note ? ` ${esc(e.note)}` : ""}</p>${e.examples.length ? `<details><summary>Representative source / derived records (up to 10)</summary><pre>${esc(JSON.stringify(e.examples, null, 2))}</pre><p>The count above uses the full data, not this example list.</p></details>` : ""}`
      : "<p>Impact is not quantified for this documentation or data-availability finding.</p>";
    const quotes = f.citations.map((c) => `<blockquote><p>${esc(c.quote)}</p><footer><a href="${esc(resource(model, dataRoot, `${d.protocol}#L${c.line}`))}">${esc(c.section)} - retained source, line ${c.line}</a></footer></blockquote>`).join("");
    return `<details class="synthetic-finding" id="finding-${esc(f.id)}" data-finding-id="${esc(f.id)}" data-kind="${esc(f.kind)}" data-search="${esc([f.id, f.title, f.summary, f.datasets.join(" ")].join(" ").toLowerCase())}"><summary><strong>${esc(f.id)}: ${esc(f.title)}</strong> ${badge(f.kind)} <span class="synthetic-open">Open - human review pending</span></summary><div class="synthetic-finding-body"><p>${esc(f.summary)}</p><p><strong>Datasets:</strong> ${esc(f.datasets.join(", "))}</p>${measured}${quotes}<p><strong>Proposed action:</strong> ${esc(f.proposed_action)}</p><label>Review decision draft<select data-review-choice="${esc(f.id)}"><option value="">Pending</option>${[...f.choices, "Needs more information", "Other - explain in notes"].map((c) => `<option value="${esc(c)}">${esc(c)}</option>`).join("")}</select></label><label>Review notes<textarea rows="3" data-review-notes="${esc(f.id)}" aria-label="Notes for ${esc(f.id)}"></textarea></label></div></details>`;
  }).join("");
  return `<section class="synthetic-development" aria-label="Analysis development and findings"><h2 id="analysis-development">Analysis development</h2>
    <p>${badge("Build and independent file checks passed", "neutral")} ${badge("Human analysis review pending")}</p>
    <p>${quantity(d.source_subjects)} subjects; ${d.datasets.filter((r) => r.section === "sdtm").length} SDTM and ${d.datasets.filter((r) => r.section === "adam").length} ADaM datasets. Both Define-XML files passed the CDISC 2.1 XSD. Every XPT cell was read back independently and compared with Parquet.</p>
    <p>No independent comparison with generated ADaM datasets is available. The files are development outputs; endpoint source summaries and record candidates remain distinct, and primary efficacy records have not been approved.</p>
    <p class="synthetic-downloads"><a href="${esc(resource(model, dataRoot, d.package))}" download>Download study package</a> <a href="${esc(resource(model, dataRoot, d.report))}">Build evidence JSON</a> <a href="${esc(resource(model, dataRoot, d.protocol))}">Retained protocol and SAP</a> <a href="${esc(resource(model, dataRoot, "define-sdtm.xml"))}">SDTM Define-XML</a> <a href="${esc(resource(model, dataRoot, "define-adam.xml"))}">ADaM Define-XML</a></p>
    ${cohort}<h2 id="analysis-coverage">Analysis coverage</h2>${coverage}
    <h2 id="review-findings">Findings for review</h2><p>${findings.length} open findings: ${counts("gap")} data/metadata gaps, ${counts("conflict")} measured conflicts, and ${counts("decision")} decisions. Agreement and resolution require human review.</p>
    <div class="synthetic-review-controls"><label>Search findings<input type="search" data-findings-search placeholder="Endpoint, dataset, or finding"></label><label>Finding type<select data-findings-kind><option value="all">All</option><option value="gap">Gaps</option><option value="conflict">Conflicts</option><option value="decision">Decisions</option></select></label><button type="button" data-review-export>Export review draft</button></div>
    <p class="report-foot">Draft choices and notes stay in this browser until exported. They do not change the source findings, resolve an issue, or approve the analysis.</p><p data-review-state role="status"></p>
    <div data-findings-list>${rows}</div><h2 id="derived-inventory">Built datasets</h2>${datasets}</section>`;
}

export function mountDevelopment(main, model) {
  if (model.development?.status !== "succeeded") return;
  const storageKey = `pilot7-review:${model.id}:${model.revision}:${model.development.created_utc}`;
  let draft = {};
  try { draft = JSON.parse(localStorage.getItem(storageKey) || "{}"); } catch { /* Storage may be unavailable. */ }
  for (const el of main.querySelectorAll("[data-review-choice], [data-review-notes]")) {
    const id = el.dataset.reviewChoice || el.dataset.reviewNotes;
    el.value = draft[id]?.[el.dataset.reviewChoice ? "choice" : "notes"] || "";
  }
  const filter = () => {
    const search = main.querySelector("[data-findings-search]").value.trim().toLowerCase();
    const kind = main.querySelector("[data-findings-kind]").value;
    for (const el of main.querySelectorAll("[data-finding-id]"))
      el.hidden = (kind !== "all" && el.dataset.kind !== kind) || !el.dataset.search.includes(search);
  };
  main.oninput = main.onchange = (event) => {
    if (event.target.matches("[data-findings-search], [data-findings-kind]")) { filter(); return; }
    const id = event.target.dataset.reviewChoice || event.target.dataset.reviewNotes;
    if (!id) return;
    draft[id] ||= {};
    draft[id][event.target.dataset.reviewChoice ? "choice" : "notes"] = event.target.value;
    try {
      localStorage.setItem(storageKey, JSON.stringify(draft));
      main.querySelector("[data-review-state]").textContent = "Review draft saved in this browser.";
    } catch { main.querySelector("[data-review-state]").textContent = "Browser storage is unavailable. Export this draft before leaving."; }
  };
  main.onclick = (event) => {
    const target = event.target.closest("a[href^='#finding-']");
    if (target) {
      const finding = main.querySelector(target.getAttribute("href"));
      if (finding) { finding.hidden = false; finding.open = true; }
    }
    if (!event.target.closest("[data-review-export]")) return;
    const payload = { schema_version: 1, study: model.id, revision: model.revision,
      build_created_utc: model.development.created_utc,
      state: "human_review_draft_not_applied", exported_utc: new Date().toISOString(), decisions: draft };
    const url = URL.createObjectURL(new Blob([JSON.stringify(payload, null, 2)], { type: "application/json" }));
    const anchor = document.createElement("a");
    anchor.href = url; anchor.download = `${model.id}-review-draft.json`; anchor.click();
    setTimeout(() => URL.revokeObjectURL(url), 1000);
  };
  if (location.hash.startsWith("#finding-")) {
    const finding = [...main.querySelectorAll("[data-finding-id]")].find((el) => `#${el.id}` === location.hash);
    if (finding) { finding.open = true; finding.scrollIntoView(); }
  }
}
