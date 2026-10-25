/** Synthetic source-development dashboards never claim pilot verification results. */
import { esc, link } from "./ui.js";
const REPO = "https://github.com/RConsortium/submissions-pilot7-synthetic-data";
const bytes = (n) =>
  n >= 1024 ** 2
    ? (n / 1024 ** 2).toFixed(1) + " MiB"
    : n.toLocaleString() + " bytes";
export async function mountSynthetic(main, get, dataRoot, site) {
  const index = await get(new URL("synthetic/index.json", dataRoot));
  if (!main.isConnected) return;
  if (main.dataset.study === "gallery") {
    main.innerHTML = `<h1>Synthetic data dashboards</h1><p>Develop the EDC-to-submission workflow using synthetic trial sources. These workspaces track available material and staging readiness.</p><div class="material-grid">${index.studies.map((s) => `<a class="study-card" href="${new URL("studies/" + s.id + "/", site)}"><h2>${esc(s.title)}</h2><p>${s.archives} source ${s.archives === 1 ? "archive" : "archives"} available</p><span>Explore sources and workflow readiness &#8594;</span></a>`).join("")}</div>`;
    return;
  }
  const study = index.studies.find((s) => s.id === main.dataset.study);
  if (!study) {
    main.innerHTML = "<h1>Synthetic workspace unavailable</h1>";
    return;
  }
  const model = await get(new URL(study.url, dataRoot));
  if (!main.isConnected) return;
  const source = `${REPO}/tree/${model.revision}/${model.id}`;
  main.innerHTML = `<header class="review-hero"><p class="eyebrow">SYNTHETIC DATA / WORKFLOW DEVELOPMENT</p><div class="study-title-row"><h1>${esc(model.title)}</h1><div class="hero-actions"><a class="button" href="${new URL("synthetic/", site)}">All synthetic studies</a>${link(source, "Study source", "button")}</div></div><p>${esc(model.description)}</p></header><div class="synthetic-stage-grid">${model.stages.map((s) => `<article class="material-card"><h2>${esc(s.title)}</h2><span class="status ${s.count ? "neutral" : "attention"}">${s.count ? "Available" : "Not staged"}</span><p>${s.count} ${esc(s.count === 1 ? s.unit.slice(0, -1) : s.unit)}</p></article>`).join("")}</div><div class="coverage-note">This workspace supports source exploration and workflow development. Availability shows which files are staged; it does not assert a successful derivation or reference comparison. Use the pilot dashboards for verification against published submission packages.</div><h2>ODM source inventory</h2>${model.archives.map((a) => `<article class="material-card"><h3>${esc(a.path)}</h3>${a.available ? `<p>${bytes(a.bytes)} compressed / ${a.files.length} source files</p><div class="overview-table"><table class="review-table"><thead><tr><th>Source member</th><th>Uncompressed size</th></tr></thead><tbody>${a.files.map((f) => `<tr><td>${esc(f.name)}</td><td>${bytes(f.bytes)}</td></tr>`).join("")}</tbody></table></div>${link(`${REPO}/blob/${model.revision}/${a.path}`, "Archive in repository", "button")}` : "<p>Source archive is not staged.</p>"}</article>`).join("")}<h2>Development workflow</h2><ol><li>Inspect the ODM source and document its collection structure.</li><li>Author and review mappings into staged SDTM domains.</li><li>Add yamaa specifications and independent ADaM references when available.</li><li>Produce submission metadata and review conformance and derivation evidence.</li></ol>`;
}
