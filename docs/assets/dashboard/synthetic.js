/** Synthetic source inventory and measured analysis development share the report layout. */
import { esc, link } from "./ui.js";
import { developmentReport, mountDevelopment } from "./synthetic-development.js";

const REPO = "https://github.com/RConsortium/submissions-pilot7-synthetic-data";
const number = (n) => n.toLocaleString("en-US");
const bytes = (n) =>
  n >= 1024 ** 2
    ? (n / 1024 ** 2).toFixed(1) + " MiB"
    : number(n) + " bytes";
const available = (model) => model.archives.filter((a) => a.available);
const count = (model, stage) =>
  model.stages.find((s) => s.id === stage)?.count ?? 0;
const members = (model) => available(model).flatMap((a) => a.files);
const studyUrl = (model, site) => new URL(`studies/${model.id}/`, site).href;
const sourceUrl = (model) => `${REPO}/tree/${model.revision}/${model.id}`;
const status = (staged) =>
  `<span class="report-status ${staged ? "neutral" : "attention"}">${staged ? "Available" : "Not staged"}</span>`;
const stageFiles = (model, id) => {
  const n = count(model, id);
  const unit = "file";
  return `${number(n)} ${unit}${n === 1 ? "" : "s"}`;
};

function table(label, headings, rows) {
  return `<div class="report-table"><table class="report-matrix" aria-label="${esc(label)}"><thead><tr>${headings.map((h) => `<th scope="col">${h}</th>`).join("")}</tr></thead><tbody>${rows.join("")}</tbody></table></div>`;
}

function metrics(models, gallery) {
  const total = (stage) => models.reduce((n, m) => n + count(m, stage), 0);
  const tiles = [
    gallery
      ? ["Studies", models.length, "synthetic workspaces"]
      : ["Source members", members(models[0]).length, "files in available archives"],
    ["ODM sources", total("odm"), "available files and archives"],
    ["SDTM files", total("sdtm"), "staged files"],
    ["ADaM files", total("adam"), "staged files"],
    ["Metadata files", total("define"), "staged Define-XML"],
  ];
  return `<dl class="report-kpis">${tiles.map(([name, value, note]) => `<div><dt>${name}</dt><dd>${number(value)}<span>${note}</span></dd></div>`).join("")}</dl>`;
}

function overview(models, site, gallery) {
  const headings = ["Study", ...models.map((m) =>
    `<a href="${esc(studyUrl(m, site))}">${esc(m.title)}</a>`)];
  const facts = [
    ["Scope", (m) => esc(m.description)],
    ["Study source", (m) => link(sourceUrl(m), m.id)],
    ["ODM archives", (m) => `${available(m).length} / ${m.archives.length} available`],
    ...(models.some((m) => m.source_files?.length) ? [["ODM XML files", (m) => number((m.source_files || []).filter((f) => f.available).length)]] : []),
    ["Source members", (m) => number(members(m).length)],
    ["Compressed size", (m) => bytes(available(m).reduce((n, a) => n + a.bytes, 0))],
  ];
  return `<h2 id="studies">${gallery ? "Studies" : "Study overview"}</h2>${table("Synthetic study overview", headings, facts.map(([name, value]) =>
    `<tr><th scope="row">${name}</th>${models.map((m) => `<td>${value(m)}</td>`).join("")}</tr>`))}`;
}

function readiness(models) {
  const stages = [
    ["odm", "EDC / ODM sources"],
    ["sdtm", "SDTM mapping"],
    ["adam", "ADaM derivation"],
    ["define", "Submission metadata"],
  ];
  return `<h2 id="workflow-readiness">Workflow readiness</h2>${table("Workflow readiness", ["Stage", ...models.map((m) => esc(m.title))], stages.map(([id, title]) =>
    `<tr><th scope="row">${title}</th>${models.map((m) => `<td class="report-cell">${status(count(m, id))}<span class="report-dims">${stageFiles(m, id)}</span></td>`).join("")}</tr>`))}<p class="report-foot">Availability counts staged files. It does not establish a successful derivation, reference agreement, or regulatory validation.</p>`;
}

function inventory(models, gallery) {
  const rows = models.flatMap((m) => m.archives.map((a) =>
    `<tr>${gallery ? `<th scope="row">${esc(m.title)}</th><td>` : '<th scope="row">'}${a.available ? link(`${REPO}/blob/${m.revision}/${a.path}`, a.path) : esc(a.path)}${gallery ? "</td>" : "</th>"}<td>${status(a.available)}</td><td>${a.available ? bytes(a.bytes) : "-"}</td><td>${a.available ? number(a.files.length) : "-"}</td></tr>`));
  let body = rows.length
    ? table("ODM source archives", [...(gallery ? ["Study"] : []), "Archive", "Status", "Compressed size", "Source members"], rows)
    : "<p>No source archives are declared.</p>";
  const files = models.flatMap((m) => (m.source_files || []).map((f) =>
    `<tr><th scope="row">${esc(m.title)}</th><td>${f.available ? link(`${REPO}/blob/${m.revision}/${f.path}`, f.path) : esc(f.path)}</td><td>${status(f.available)}</td><td>${f.available ? bytes(f.bytes) : "-"}</td></tr>`));
  if (files.length) body += table("ODM XML sources", ["Study", "Source file", "Status", "Size"], files);
  if (!gallery) {
    for (const archive of available(models[0])) {
      body += `<h3>${esc(archive.path.split("/").pop())}</h3>`;
      body += archive.files.length
        ? table("Source members in " + archive.path, ["Source member", "Uncompressed size"], archive.files.map((f) =>
          `<tr><th scope="row"><code>${esc(f.name)}</code></th><td>${bytes(f.bytes)}</td></tr>`))
        : "<p>No source files were found in this archive.</p>";
    }
  }
  return `<h2 id="source-inventory">ODM source inventory</h2>${body}<p class="report-foot">The inventory reads archive headers without extracting or loading clinical XML. Original archives remain in the repository at the report revision.</p>`;
}

function workflow() {
  return `<h2 id="development-workflow">Development workflow</h2>${table("Development workflow", ["Stage", "Next work"], [
    ["EDC / ODM sources", "Review collection structure, supplied values and missing source data."],
    ["SDTM mapping", "Review mappings, units, terminology and retained source trace."],
    ["ADaM derivation", "Align analysis decisions and review candidate derivations and independent checks."],
    ["Submission metadata", "Review metadata, conformance, derivation evidence and remaining findings."],
  ].map(([stage, task]) => `<tr><th scope="row">${stage}</th><td>${task}</td></tr>`))}`;
}

export function syntheticReport(models, site, gallery, dataRoot = new URL("evidence/dashboard/", site)) {
  const title = gallery ? "Synthetic data report" : `${models[0].title} study report`;
  return `<h1>${esc(title)}</h1>
    <p class="report-lede">Synthetic clinical trial sources support development of the EDC-to-submission workflow. This report summarizes source archives and staged files${gallery ? " across the synthetic studies" : ` for ${esc(models[0].title)}`}.</p>
    ${!gallery ? `<p class="report-screen"><a href="${esc(new URL("synthetic/", site).href)}">All synthetic studies</a></p>` : ""}
    ${models.length ? `${metrics(models, gallery)}${overview(models, site, gallery)}${!gallery ? developmentReport(models[0], dataRoot) : ""}${readiness(models)}${inventory(models, gallery)}${workflow()}` : "<p>No synthetic studies are configured.</p>"}
    <p class="report-foot">Source members are files inside the available archives, not counts of subjects or clinical records. Reference comparisons are reported separately in the <a href="${esc(new URL("studies/", site).href)}">pilot study report</a>.</p>`;
}

export async function mountSynthetic(main, get, dataRoot, site) {
  const index = await get(new URL("synthetic/index.json", dataRoot));
  if (!main.isConnected) return;
  const gallery = main.dataset.study === "gallery";
  const studies = gallery ? index.studies : index.studies.filter((s) => s.id === main.dataset.study);
  if (!gallery && !studies.length) {
    main.innerHTML = "<h1>Synthetic study unavailable</h1><p>This study has no source inventory.</p>";
    return;
  }
  const models = await Promise.all(studies.map((s) => get(new URL(s.url, dataRoot))));
  if (!main.isConnected) return;
  main.innerHTML = syntheticReport(models, site, gallery, dataRoot);
  if (!gallery) mountDevelopment(main, models[0]);
}
