/* Interactive review prototype inside the existing MkDocs Material shell. */
(() => {
"use strict";

const REPO = "https://github.com/RConsortium/submissions-pilot7-synthetic-data";
const icons = {
  grid: '<rect x="3" y="3" width="7" height="7" rx="1.5"/><rect x="14" y="3" width="7" height="7" rx="1.5"/><rect x="3" y="14" width="7" height="7" rx="1.5"/><rect x="14" y="14" width="7" height="7" rx="1.5"/>',
  github: '<path d="M9 19c-4 1-4-2-6-2m12 4v-3.5c.1-1-.3-1.7-.8-2.1 2.7-.3 5.5-1.3 5.5-6a4.7 4.7 0 0 0-1.3-3.3 4.4 4.4 0 0 0-.1-3.3s-1-.3-3.4 1.3a11.6 11.6 0 0 0-6.2 0C6.3 2.5 5.3 2.8 5.3 2.8A4.4 4.4 0 0 0 5.2 6a4.7 4.7 0 0 0-1.3 3.3c0 4.7 2.8 5.7 5.5 6-.5.4-.9 1.2-.8 2.1V21"/>',
  external: '<path d="M14 3h7v7m0-7L10 14"/><path d="M10 3H5a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-5"/>',
  help: '<circle cx="12" cy="12" r="9"/><path d="M9.3 9a2.7 2.7 0 0 1 5.3.7c0 1.8-2.6 2.1-2.6 3.8m0 3h.01"/>',
  shield: '<path d="m12 3 8 3v6c0 4-4.5 7.2-8 9-3.5-1.8-8-5-8-9V6z"/><path d="m8.5 12 2.3 2.3 4.8-5"/>',
  check: '<path d="m5 12 4 4L19 6"/>',
  'check-circle': '<circle cx="12" cy="12" r="9"/><path d="m8 12 2.5 2.5L16 9"/>',
  chevron: '<path d="m9 5 7 7-7 7"/>',
  'arrow-right': '<path d="M4 12h16m-6-6 6 6-6 6"/>',
  database: '<ellipse cx="12" cy="5" rx="8" ry="3"/><path d="M4 5v14c0 1.7 3.6 3 8 3s8-1.3 8-3V5M4 12c0 1.7 3.6 3 8 3s8-1.3 8-3"/>',
  layers: '<path d="m12 3 10 6-10 6L2 9zm-10 12 10 6 10-6M2 12l10 6 10-6"/>',
  people: '<circle cx="9" cy="8" r="3"/><path d="M3 21v-3a6 6 0 0 1 12 0v3m2-16a3 3 0 0 1 0 6m4 10v-3a6 6 0 0 0-4-5"/>',
  clock: '<circle cx="12" cy="12" r="9"/><path d="M12 7v5l3 2"/>',
  file: '<path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><path d="M14 2v6h6M8 13h8m-8 4h5"/>',
  code: '<path d="m8 7-5 5 5 5m8-10 5 5-5 5m-3-14-2 18"/>',
  chart: '<path d="M3 3v18h18M7 15l4-5 4 3 5-7"/>',
  message: '<path d="M21 15a3 3 0 0 1-3 3H8l-5 4V5a3 3 0 0 1 3-3h12a3 3 0 0 1 3 3z"/><path d="M7 7h10M7 12h7"/>',
  download: '<path d="M12 3v12m-4-4 4 4 4-4M4 16v4a1 1 0 0 0 1 1h14a1 1 0 0 0 1-1v-4"/>',
  search: '<circle cx="10" cy="10" r="6"/><path d="m15 15 6 6"/>',
  close: '<path d="m6 6 12 12M6 18 18 6"/>',
  info: '<circle cx="12" cy="12" r="9"/><path d="M12 11v6m0-10h.01"/>',
  book: '<path d="M12 6c-3-3-7-3-10-2v15c4-1 7 0 10 2 3-2 6-3 10-2V4c-3-1-7-1-10 2zm0 0v15"/>',
  branch: '<circle cx="6" cy="5" r="2"/><circle cx="6" cy="19" r="2"/><circle cx="18" cy="5" r="2"/><path d="M6 7v10m12-10c0 8-12 2-12 9"/>',
  flask: '<path d="M9 3h6m-5 0v7L4 20c-.5 1 0 2 1.5 2h13c1.5 0 2-1 1.5-2l-6-10V3M7 15h10"/>',
  play: '<path d="m9 4 12 8-12 8z"/>'
};
function icon(name, cls = "") { return `<svg class="${cls}" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">${icons[name] || icons.file}</svg>`; }
function escapeHtml(value) { return String(value).replace(/[&<>"']/g, c => ({ "&":"&amp;", "<":"&lt;", ">":"&gt;", '"':"&quot;", "'":"&#39;" }[c])); }
function external(url, label, classes = "button") { return `<a class="${classes}" href="${escapeHtml(url)}" target="_blank" rel="noreferrer">${label}${icon("external")}</a>`; }
function badge(label, tone = "green", showIcon = true) { return `<span class="badge ${tone}">${showIcon ? icon(tone === "green" ? "check" : tone === "amber" ? "clock" : "info") : ""}${label}</span>`; }

const datasetInfo = {
  ADSL: ["Subject-level analysis",256,57], ADAE: ["Adverse events",1191,64], ADLBC: ["Laboratory chemistry",35900,77],
  ADLBH: ["Laboratory hematology",23040,76], ADLBHY: ["Liver safety analysis",715,43], ADQSADAS: ["ADAS-Cog assessment",3410,59],
  ADQSCIBC: ["Clinical global impression",1290,48], ADQSNIPX: ["Neuropsychiatric inventory",2890,60], ADTTE: ["Time-to-event analysis",256,34],
  ADVS: ["Vital signs",12200,56], ADADAS: ["ADAS-Cog assessment",3410,59]
};
const studies = [
  { id:"cdiscpilot01", title:"CDISC Pilot 01", short:"CDISC Pilot 01", type:"pilot", tag:"Reference study", description:"Agentic review SDTM to ADaM derivations against the published submission package.", datasets:["ADSL","ADAE","ADLBC","ADLBH","ADLBHY","ADQSADAS","ADQSCIBC","ADQSNIPX","ADTTE","ADVS"], subjects:256, reference:true },
  { id:"submission-pilot3", title:"Submission Pilot 3", short:"Submission Pilot 3", type:"pilot", tag:"Reference study", description:"R Consortium's Pilot 3 submission. Explore five ADaM derivations from staged SDTM and their official references.", datasets:["ADSL","ADAE","ADLBC","ADADAS","ADTTE"], subjects:256, reference:true },
  { id:"submission-pilot5", title:"Submission Pilot 5", short:"Submission Pilot 5", type:"pilot", tag:"Dataset-JSON study", description:"The Dataset-JSON pilot. Review ADaM derivations from SDTM converted from Dataset-JSON 1.1.", datasets:["ADSL","ADAE","ADLBC","ADADAS","ADTTE"], subjects:256, reference:true },
  { id:"submission-pilot6", title:"Submission Pilot 6", short:"Submission Pilot 6", type:"pilot", tag:"Work in progress", description:"Staged SDTM, production ADaM references, and upstream programs. yamaa derivation coverage remains to be established.", datasets:[], subjects:null, reference:true, pending:true },
  { id:"kn189", title:"KN189", short:"KN189", type:"synthetic", tag:"Synthetic study", description:"A synthetic clinical trial study for developing the full workflow, from collected data through submission outputs.", datasets:[], subjects:null, reference:false, pending:true },
  { id:"kn564", title:"KN564", short:"KN564", type:"synthetic", tag:"Synthetic study", description:"A synthetic clinical trial study for developing the full workflow, from collected data through submission outputs.", datasets:[], subjects:null, reference:false, pending:true }
];
const tabs = [["overview","Overview","grid"],["datasets","Datasets","database"],["findings","Documentation review","message"],["materials","Specifications & programs","code"],["evidence","Evidence","shield"]];
const defaults = { dataset:"ADSL", subject:"", specOpen:false, search:"", sort:"study", findingsOnly:false, findingSearch:"", findingDataset:"", rowSearch:"", column:"" };
const state = { study:studies[0], view:"overview", ...defaults };

// Questions are examples, never audit results. One list drives counts and filters.
const findings = [
  {id:"DOC-001",dataset:"ADSL",variable:"TRT01P",source:"Define-XML",path:"spec/define/define-adam.xml",question:"Confirm the treatment label in the yamaa specification matches the published metadata.",review:"Compare planned treatment values and labels with the published codelist. Record the exact section and evidence before deciding whether there is a discrepancy."},
  {id:"DOC-002",dataset:"ADAE",variable:"TRTEMFL",source:"Source specification",path:"spec/source",question:"Confirm the treatment-emergent window in the yamaa rule agrees with the source specification.",review:"Review the start and end boundaries, partial dates, and treatment timing. Confirm the documented rule before proposing a specification change."},
  {id:"DOC-003",dataset:"ADSL",variable:"SAFFL",source:"ADRG / data guide",path:"spec/source",question:"Confirm the population rule and exclusions agree with the submission guide.",review:"Check the safety population definition and exclusions against the guide. Capture supporting evidence and a human review resolution."}
];
function studyFindings() { return state.study.pending ? [] : findings.filter(f=>state.study.datasets.includes(f.dataset)); }
function route(view=state.view, dataset=state.dataset) {
  const params=new URLSearchParams();
  for(const [key,value] of Object.entries(defaults)) {
    if(key!=="dataset" && state[key]!==value) params.set(key,String(state[key]));
  }
  return `#${state.study.id}/${view}${dataset?"/"+dataset:""}${params.size?"?"+params:""}`;
}
function saveView() {
  history.replaceState(null,"",route());
  const input=document.getElementById("share-url");if(input)input.value=location.href;
}

function navigate(view, dataset) {
  if(view === "gallery") { location.assign(studyUrl()); return; }
  location.hash = route(view,dataset||state.dataset);
}
// Resolve relative to the built asset, including a GitHub Pages project prefix.
const assetUrl=Array.from(document.scripts).find(s=>/\/assets\/dashboard\.js(?:\?|$)/.test(s.src))?.src;
const siteUrl=new URL("../",assetUrl||new URL("../../assets/dashboard.js",location.href));
function studyUrl(id="") { return new URL(`studies/${id?id+"/":""}`,siteUrl).href; }
function currentStudy() { return state.study; }
function stats() {
  const s=currentStudy(), n=s.datasets.length;
  const columns=s.datasets.reduce((sum,name)=>sum+datasetInfo[name][2],0);
  const cells=s.datasets.reduce((sum,name)=>sum+datasetInfo[name][1]*datasetInfo[name][2],0);
  const million=value=>(value/1e6).toFixed(1)+"M";
  const values=[
    ["Datasets",n,n,"database"],
    ["Columns",columns.toLocaleString("en-US"),columns.toLocaleString("en-US"),"layers"],
    ["Cells",million(cells),million(cells),"grid"]
  ];
  return `<div class="stats" aria-label="Study comparison and documentation metrics">${values.map(([label,value,total,i])=>`<button class="stat" data-view="datasets"><div class="stat-top">${label}${icon(i)}</div><div class="stat-value">${s.pending?(s.reference?"Pending":"n/a"):`${value}<span class="denominator">/ ${total}</span>`}</div><div class="stat-note">${s.pending?"Reference comparison not available":'<strong>100%</strong> &middot; matched / reference total'}</div></button>`).join("")}<button class="stat findings-stat" data-view="findings"><div class="stat-top">Documentation findings${icon("message")}</div><div class="stat-value">${s.pending?"Not reviewed":studyFindings().length}${s.pending?"":'<span class="finding-open">open</span>'}</div><div class="stat-note">yamaa vs spec, Define-XML & ADRG</div></button></div><div class="metrics-caption">Same metrics as the home page: fully matched / reference total (%). All numbers and findings are illustrative.</div>`;
}
function pipeline() {
  const s=currentStudy();
  if(s.type === "synthetic") return "";
  return `<div class="pipeline" aria-label="Study pipeline"><span class="pipeline-label">Current scope</span><span class="pipeline-stage">${icon("database")}<strong>SDTM</strong><span>Staged inputs</span></span>${icon("arrow-right")}<span class="pipeline-stage">${icon("layers")}<strong>ADaM</strong><span>${s.pending?"References staged":"yamaa output & official reference"}</span></span></div>`;
}
function pageFrame() {
  const s=currentStudy();
  return `<div class="hero"><div class="title-row"><h1>${s.title}</h1><div class="hero-actions"><button class="button" id="copy-view">${icon("branch")}Copy view link</button>${external(`${REPO}/tree/main/${s.id}`,`${icon("github")}Study source`)}<button class="button primary" data-view="evidence">${icon("shield")}View evidence</button></div></div><p>${s.description}</p></div>
    <div class="demo-note">${icon("info")}Design prototype. Metrics, findings and preview rows are illustrative.</div>
    <div id="share-fallback" hidden><label>Link to this view<input id="share-url" type="text" readonly></label></div>${stats()}${pipeline()}
    <nav class="tabs" aria-label="Study sections">${tabs.map(([id,label])=>`<button class="tab ${state.view===id?"active":""}" ${state.view===id?'aria-current="page"':""} data-view="${id}">${label}${id==="findings"&&!s.pending?`<span class="tab-count">${studyFindings().length}</span>`:""}</button>`).join("")}</nav>
    <div class="view-content" id="view-content"></div>${footer()}`;
}
function footer() { return `<div class="footer">Design prototype / illustrative metrics and findings. Source documents remain in the study repository.</div>`; }
function datasetTable() {
  const s=currentStudy(), names=visibleDatasets();
  return `<div class="table-card"><div class="table-scroll" tabindex="0" role="region" aria-label="Dataset verification table"><table><caption class="sr-only">Illustrative dataset build, reference agreement, and open documentation questions</caption><thead><tr><th scope="col">Dataset</th><th scope="col">Rows</th><th scope="col">Columns</th><th scope="col">Build / reference</th><th scope="col">Doc questions</th></tr></thead><tbody>${names.length?names.map(name=>{const [desc,rows,cols]=datasetInfo[name], count=studyFindings().filter(f=>f.dataset===name).length;return `<tr class="dataset-row" data-dataset="${name}"><td><button class="dataset-code" data-dataset="${name}" style="background:none;border:0;padding:0;text-align:left">${icon("database")}<span>${name}<span class="dataset-desc">${desc}</span></span></button></td><td>${rows.toLocaleString("en-US")}</td><td>${cols}</td><td>${badge("Built")} ${badge("Matched")}</td><td>${count?`<button class="small-link" data-finding-dataset="${name}">${count} open ${icon("arrow-right")}</button>`:'<span class="dataset-desc">No example questions</span>'}</td></tr>`;}).join(""):'<tr><td colspan="5">No datasets match these filters. Try another name or clear the filters.</td></tr>'}</tbody></table></div><div class="table-end"><span role="status">Showing ${names.length} of ${s.datasets.length} datasets / illustrative results</span><button class="small-link" data-view="datasets">Explore datasets${icon("arrow-right")}</button></div></div>`;
}
function visibleDatasets() {
  const names=state.study.datasets.filter(n=>(n+" "+datasetInfo[n][0]).toLowerCase().includes(state.search.toLowerCase()) && (!state.findingsOnly || studyFindings().some(f=>f.dataset===n)));
  return names.sort((a,b)=>state.sort==="name"?a.localeCompare(b):state.sort==="rows"?datasetInfo[b][1]-datasetInfo[a][1]:state.sort==="findings"?studyFindings().filter(f=>f.dataset===b).length-studyFindings().filter(f=>f.dataset===a).length:0);
}
function datasetFilters() {
  return `<div class="filter-bar"><label class="search-box">${icon("search")}<input id="dataset-search" type="search" placeholder="Name or description..." aria-label="Find a dataset" value="${escapeHtml(state.search)}"></label><label class="select-wrap">Sort<select id="dataset-sort"><option value="study">Study order</option><option value="name" ${state.sort==="name"?"selected":""}>Name A-Z</option><option value="rows" ${state.sort==="rows"?"selected":""}>Most rows</option><option value="findings" ${state.sort==="findings"?"selected":""}>Most doc questions</option></select></label><label class="checkbox-wrap"><input id="findings-only" type="checkbox" ${state.findingsOnly?"checked":""}>Has doc questions</label><button class="small-link" id="reset-datasets">Clear filters</button></div>`;
}
function assetList() {
  const s=currentStudy();
  const assets=[
    ["Study source documents","SAP, guides & provenance",`${REPO}/tree/main/${s.id}/spec${s.type==="synthetic"?"":"/source"}`,"book"],
    ["yamaa specifications","Project & dataset mappings",`${REPO}/tree/main/${s.id}/spec${s.datasets.length?"/yamaa":""}`,"code"],
    ["Study programs","R, Python & reference programs",`${REPO}/tree/main/${s.id}/program`,"file"],
    ["Define-XML & metadata","Standards and dataset definitions",`${REPO}/tree/main/${s.id}/spec${s.reference?"/define":""}`,"layers"]
  ];
  return `<section class="panel"><div class="panel-heading"><h2>Study materials</h2>${icon("book")}</div><div class="asset-list">${assets.map(([name,note,url,i])=>`<a class="asset-link" href="${escapeHtml(url)}" target="_blank" rel="noreferrer"><span class="asset-icon">${icon(i)}</span><span class="asset-name">${name}<small>${note}</small></span>${icon("external")}</a>`).join("")}</div></section>`;
}
function overview() {
  const s=currentStudy();
  return `<div class="overview-layout"><section><div class="section-heading"><div><h2>${s.pending?"Study coverage":"Dataset verification"}</h2><p>${s.pending?"Available materials and the next derivation steps.":"Compare yamaa-derived ADaM with the published reference."}</p></div>${s.pending?"":`<button class="small-link" data-view="datasets">View all ${s.datasets.length} datasets${icon("arrow-right")}</button>`}</div>${s.pending?pendingView():`${datasetFilters()}<div id="dataset-overview">${datasetTable()}</div>`}<div class="method-note">${icon("shield")}<div><strong>Data agreement and documentation consistency are separate checks.</strong><br>A reference match does not establish that the derivation follows every rule in the submission package.</div></div></section><aside class="overview-right">${assetList()}<div class="review-box"><h3>${icon("message")}Documentation consistency</h3><p>${s.pending?"Not yet reviewed.":`${studyFindings().length} example questions remain open. Review yamaa derivation rules against the source specification, Define-XML, and ADRG.`}</p><button class="small-link" data-view="findings">Review documentation findings${icon("arrow-right")}</button></div></aside></div>`;
}
function pendingView() {
  const s=currentStudy();
  return `<div class="empty-state"><div class="empty-icon">${icon(s.type==="synthetic"?"flask":"branch")}</div><h2>${s.type==="synthetic"?"A pipeline in progress":"yamaa derivation work remains"}</h2><p>${s.type==="synthetic"?"The collected-data source and starter programs are available. This workspace will show SDTM mapping, ADaM derivation, and verification coverage as evidence becomes available.":"SDTM inputs, eight production ADaM references, and upstream programs are staged. yamaa builds and comparisons will appear when specifications and validation evidence are available."}</p>${external(`${REPO}/tree/main/${s.id}`,"Browse available materials","button soft")}</div>`;
}
function datasetSidebar() {
  return `<aside class="dataset-sidebar" aria-label="Dataset browser"><div class="dataset-search">${datasetFilters()}</div><div class="dataset-list" id="dataset-list">${datasetOptions()}</div><div class="dataset-rail-footer">ADaM / ${state.study.datasets.length} active datasets</div></aside>`;
}
function datasetOptions() { const names=visibleDatasets();return names.length?names.map(name=>`<button class="dataset-option ${state.dataset===name?"active":""}" ${state.dataset===name?'aria-current="true"':""} data-dataset="${name}"><span><strong>${name}</strong><small>${datasetInfo[name][0]}</small></span>${state.dataset===name?icon("check-circle"):icon("chevron")}</button>`).join(""):'<div class="no-results" role="status">No matching datasets. <button class="small-link" id="reset-datasets">Clear filters</button></div>'; }

const sampleSubjects=["DEMO-001","DEMO-002","DEMO-003"];
function datasetPreview() {
  const name=state.dataset;
  if(name==="ADAE") return {source:"AE",sourceColumns:["USUBJID","AEDECOD","AESTDTC","AESEV"],sourceRows:[["DEMO-001","HEADACHE","2026-01-12","MILD"],["DEMO-002","NAUSEA","2026-01-16","MODERATE"],["DEMO-003","DIZZINESS","2026-01-18","MILD"]],columns:["USUBJID","AEDECOD","ASTDY","TRTEMFL"],rows:[["DEMO-001","HEADACHE","5","Y"],["DEMO-002","NAUSEA","8","Y"],["DEMO-003","DIZZINESS","10","Y"]],derived:["ASTDY","TRTEMFL"]};
  if(name.startsWith("ADLB")) return {source:"LB",sourceColumns:["USUBJID","LBTESTCD","LBSTRESN","VISIT"],sourceRows:[["DEMO-001","ALT","24","BASELINE"],["DEMO-002","ALT","31","BASELINE"],["DEMO-003","ALT","28","BASELINE"]],columns:["USUBJID","PARAMCD","AVAL","ABLFL"],rows:[["DEMO-001","ALT","24","Y"],["DEMO-002","ALT","31","Y"],["DEMO-003","ALT","28","Y"]],derived:["PARAMCD","AVAL","ABLFL"]};
  if(name==="ADSL") return {source:"DM",sourceColumns:["USUBJID","AGE","SEX","ARM","RFSTDTC"],sourceRows:[["DEMO-001","68","F","PLACEBO","2026-01-08"],["DEMO-002","72","M","ACTIVE","2026-01-09"],["DEMO-003","65","F","ACTIVE","2026-01-09"]],columns:["USUBJID","AGE","TRT01P","SAFFL"],rows:[["DEMO-001","68","Placebo","Y"],["DEMO-002","72","Active","Y"],["DEMO-003","65","Active","Y"]],derived:["TRT01P","SAFFL"]};
  if(name==="ADTTE") return {source:"DS",sourceColumns:["USUBJID","DSDECOD","DSSTDTC"],sourceRows:[["DEMO-001","COMPLETED","2026-06-12"],["DEMO-002","DISCONTINUED","2026-05-03"],["DEMO-003","COMPLETED","2026-06-13"]],columns:["USUBJID","PARAMCD","AVAL","CNSR"],rows:[["DEMO-001","TTDISCON","156","1"],["DEMO-002","TTDISCON","115","0"],["DEMO-003","TTDISCON","156","1"]],derived:["AVAL","CNSR"]};
  return {source:name==="ADVS"?"VS":"QS",sourceColumns:["USUBJID","TESTCD","RESULT","VISIT"],sourceRows:[["DEMO-001","TEST01","24","BASELINE"],["DEMO-002","TEST01","31","BASELINE"],["DEMO-003","TEST01","28","BASELINE"]],columns:["USUBJID","PARAMCD","AVAL","ABLFL"],rows:[["DEMO-001","TEST01","24","Y"],["DEMO-002","TEST01","31","Y"],["DEMO-003","TEST01","28","Y"]],derived:["PARAMCD","AVAL","ABLFL"]};
}
function previewTable(columns,rows,derived=[],focusColumn=state.column) {
  const visible=columns.map((c,i)=>({name:c,index:i})).filter(c=>!focusColumn||c.name==="USUBJID"||c.name===focusColumn);
  const filtered=previewRows(rows);
  return `<div class="table-scroll" tabindex="0" role="region" aria-label="Scrollable sample rows"><table class="preview-table"><caption class="sr-only">Illustrative rows. Select a subject to highlight it across previews.</caption><thead><tr>${visible.map(c=>`<th scope="col" class="${derived.includes(c.name)?"derived-col":""}">${c.name}</th>`).join("")}</tr></thead><tbody>${filtered.length?filtered.map(row=>`<tr data-subject-row="${row[0]}" class="${state.subject===row[0]?"highlighted":""}">${visible.map(c=>`<td class="${derived.includes(c.name)?"derived-col":""}">${c.index===0?`<button class="subject-cell" data-subject="${row[0]}" aria-label="Highlight ${row[0]}" aria-pressed="${state.subject===row[0]}">${row[0]}</button>`:escapeHtml(row[c.index])}</td>`).join("")}</tr>`).join(""):`<tr><td colspan="${visible.length}">No sample rows match. Clear the row search to see all three subjects.</td></tr>`}</tbody></table></div>`;
}
function previewRows(rows) {
  const d=datasetPreview(), query=state.rowSearch.toLowerCase().trim();
  const subjects=new Set([...d.sourceRows,...d.rows].filter(r=>r.join(" ").toLowerCase().includes(query)).map(r=>r[0]));
  return rows.filter(r=>subjects.has(r[0]));
}
function previewPanel(title,path,columns,rows,derived,ref=false,focusColumn=state.column) {
  return `<section class="preview-panel"><div class="preview-header">${icon(ref?"shield":"database")}<h4>${title}</h4><span class="preview-meta">${previewRows(rows).length} / 3 sample rows</span></div>${previewTable(columns,rows,derived,focusColumn)}<div class="preview-footer"><span>${path}</span><span>${ref?"Reference layout / example rows":"Illustrative preview"}</span></div></section>`;
}
function specPanel() {
  return `<section class="spec-panel" ${state.specOpen?"":"hidden"} id="spec-panel"><div class="spec-title"><span>${icon("code")} ${state.dataset.toLowerCase()}.yaml / illustrative excerpt</span><a href="${REPO}/blob/main/${state.study.id}/spec/yamaa/${state.dataset.toLowerCase()}.yaml" target="_blank" rel="noreferrer">Open actual specification ${icon("external")}</a></div><pre><code><span class="code-key">domain:</span> <span class="code-value">${state.dataset}</span>
<span class="code-key">source:</span> <span class="code-value">${datasetPreview().source.toLowerCase()}</span>
<span class="code-key">keys:</span> [USUBJID]
<span class="code-key">columns:</span>
  # Review the actual YAML for complete derivation rules.
  # This abbreviated example demonstrates the panel layout.
  - <span class="code-key">name:</span> <span class="code-value">USUBJID</span>
    <span class="code-key">source:</span> <span class="code-value">USUBJID</span></code></pre></section>`;
}
function datasetsView() {
  if(state.study.pending) return pendingView();
  const [desc,rows,cols]=datasetInfo[state.dataset], d=datasetPreview();
  return `<div class="workspace-toolbar"><div><h2>Dataset review workspace</h2><p>Follow a subject from source data to the analysis dataset.</p></div><div class="toolbar-actions"><label class="select-wrap"><span>Highlight subject</span><select id="subject-select" aria-label="Highlight subject"><option value="">All subjects</option>${sampleSubjects.map(s=>`<option value="${s}" ${state.subject===s?"selected":""}>${s}</option>`).join("")}</select></label><button class="button ${state.specOpen?"soft":""}" id="spec-toggle" aria-controls="spec-panel" aria-expanded="${state.specOpen}">${icon("code")}<span>${state.specOpen?"Hide":"Show"} specification</span></button></div></div>
  <div class="workspace-grid">${datasetSidebar()}<div class="dataset-detail"><header class="detail-header"><span class="detail-icon">${icon("database")}</span><div><h3>${state.dataset} / ${desc}</h3><p>${rows.toLocaleString("en-US")} rows &middot; ${cols} columns &middot; Illustrative dimensions</p></div><div class="detail-badges">${badge("Example build")}${badge("Example match")}</div></header>${studyFindings().some(f=>f.dataset===state.dataset)?`<button class="review-jump" data-finding-dataset="${state.dataset}">${icon("message")}${studyFindings().filter(f=>f.dataset===state.dataset).length} open documentation questions for ${state.dataset}${icon("arrow-right")}</button>`:""}${specPanel()}<div class="filter-bar preview-controls"><label class="search-box">${icon("search")}<input type="search" id="row-search" aria-label="Search sample rows" placeholder="Search sample rows..." value="${escapeHtml(state.rowSearch)}"></label><label class="select-wrap">Focus column<select id="column-select"><option value="">All columns</option>${d.columns.filter(c=>c!=="USUBJID").map(c=>`<option ${state.column===c?"selected":""}>${c}</option>`).join("")}</select></label><button class="small-link" id="reset-preview">Reset preview</button><button class="button" id="download-preview">${icon("download")}Sample CSV</button></div><p class="preview-help">Search finds subjects across source and output values. Column focus applies to both ADaM previews; source columns stay visible for context.</p><div id="preview-tables">${previewTables()}</div></div></div>`;
}
function previewTables() {
  const d=datasetPreview();
  // Source context stays complete when an output variable is in focus.
  const source=previewPanel("Relevant source input",`data/sdtm/${d.source.toLowerCase()}.parquet`,d.sourceColumns,d.sourceRows,[],false,"");
  return `${source}<div class="output-head"><h3>Derived output & reference</h3><span>${icon("check-circle")} Example agreement</span></div><div class="comparison-tables">${previewPanel("yamaa-derived ADaM",`data/adam/${state.dataset.toLowerCase()}-yamaa.parquet`,d.columns,d.rows,d.derived)}${previewPanel("Official ADaM reference",`data/adam/${state.dataset.toLowerCase()}.parquet`,d.columns,d.rows,[],true)}</div><div class="legend"><span><i></i>Derived columns shaded</span><span>Click a subject ID to highlight it across previews</span></div><p class="preview-help" role="status">${previewRows(d.rows).length} of 3 illustrative subjects shown${state.subject?`; ${state.subject} highlighted`:""}. Full dataset totals above are examples.</p>`;
}
function findingsView() {
  const s=currentStudy();
  if(s.pending) return `<div class="empty-state"><div class="empty-icon">${icon("book")}</div><h2>Documentation review not yet run</h2><p>The findings count will be populated by comparing yamaa specifications with the study's source specifications, Define-XML, and ADRG or analysis data guide. An unreviewed study is not recorded as having zero findings.</p>${external(`${REPO}/tree/main/${s.id}/spec`,"Browse source documents","button soft")}</div>`;
  return `<div class="section-heading"><div><h2>Documentation consistency findings</h2><p>Compare yamaa specifications with the published submission package.</p></div>${badge(studyFindings().length+" open / example","amber",false)}</div><div class="method-note findings-note">${icon("info")}<div>These are illustrative review questions. No audit has been performed. Review coverage: <strong>not assessed</strong>. Dataset agreement does not close these questions.</div></div><div class="filter-bar"><label class="search-box">${icon("search")}<input id="finding-search" type="search" aria-label="Search documentation questions" placeholder="Variable, document or question..." value="${escapeHtml(state.findingSearch)}"></label><label class="select-wrap">Dataset<select id="finding-dataset"><option value="">All datasets</option>${[...new Set(studyFindings().map(f=>f.dataset))].map(n=>`<option ${state.findingDataset===n?"selected":""}>${n}</option>`).join("")}</select></label><button class="small-link" id="reset-findings">Clear filters</button></div><div id="finding-results">${findingResults()}</div>`;
}
function findingResults() {
  const s=currentStudy(), items=studyFindings().filter(f=>(!state.findingDataset||f.dataset===state.findingDataset)&&Object.values(f).join(" ").toLowerCase().includes(state.findingSearch.toLowerCase()));
  return `<p class="results-count" role="status">${items.length} of ${studyFindings().length} example questions shown</p><div class="finding-cards">${items.length?items.map(f=>`<article class="finding-card"><div class="finding-heading"><span class="finding-id">${f.id} / ${f.dataset}.${f.variable}</span>${badge("Open example","amber",false)}</div><h3>${f.question}</h3><p class="finding-source">Source: ${external(`${REPO}/${f.path.endsWith(".xml")?"blob":"tree"}/main/${s.id}/${f.path}`,f.source,"small-link")}</p><details><summary>How to review this question</summary><p>${f.review}</p><p>Document section, discrepancy, and resolution are not yet recorded. A human reviewer must confirm evidence before marking a real finding resolved.</p></details><div class="finding-actions"><button class="button" data-review-dataset="${f.dataset}" data-column="${f.variable}">${icon("database")}Explore ${f.dataset}.${f.variable}</button>${external(`${REPO}/blob/main/${s.id}/spec/yamaa/${f.dataset.toLowerCase()}.yaml`,"Open actual YAML","small-link")}</div></article>`).join(""):'<div class="empty-state"><h3>No matching questions</h3><p>Try a dataset name, variable such as SAFFL, or clear the filters.</p></div>'}</div>`;
}

function materialsView() {
  const s=currentStudy();
  const items=[
    ["book","Source documents","Review study requirements, the statistical analysis plan, reviewer guides, and retained provenance.",`${REPO}/tree/main/${s.id}/spec${s.type==="synthetic"?"":"/source"}`,"Browse documents"],
    ["code","Derivation specifications",s.datasets.length?"Browse the yamaa project and per-dataset YAML specifications that define the active derivations.":"Browse available specification materials. yamaa specifications are still to be established.",`${REPO}/tree/main/${s.id}/spec${s.datasets.length?"/yamaa":""}`,"Open specifications"],
    ["file","Programs & reproduction","Inspect the study programs and available instructions for building outputs and checking reference agreement.",`${REPO}/tree/main/${s.id}/program`,"Browse programs"],
    ["layers","Standards metadata","Inspect available dataset metadata and published Define-XML alongside the derivation specification.",`${REPO}/tree/main/${s.id}/spec${s.reference?"/define":""}`,"View metadata"],
    ["database","Study data","Browse the source datasets and staged references in their original repository locations.",`${REPO}/tree/main/${s.id}/data`,"Browse study data"],
    ["message","Review discussions","Use repository issues to review clinical assumptions, clarify derivation rules, and track outstanding work.",`${REPO}/issues`,"Open GitHub issues"]
  ];
  return `<div class="section-heading"><div><h2>Specifications & programs</h2><p>One place to find the documents behind the derivations.</p></div></div><div class="materials-grid">${items.map(([i,title,text,url,label])=>`<section class="material-card">${icon(i)}<h3>${title}</h3><p>${text}</p>${external(url,label)}</section>`).join("")}</div>`;
}
function evidenceView() {
  const s=currentStudy();
  return `<div class="section-heading"><div><h2>Evidence & review</h2><p>Trace a result back to its source, engine, and comparison policy.</p></div><button class="button" id="download-evidence">${icon("download")}Sample evidence</button></div><div class="evidence-grid"><section class="panel"><div class="panel-heading"><h2>Validation record / example</h2>${badge("Illustrative","amber",false)}</div><dl class="evidence-list"><div><dt>Study</dt><dd>${s.title}</dd></div><div><dt>Dataset builds</dt><dd>${s.pending?"Not run":s.datasets.length+" / "+s.datasets.length+" succeeded"}</dd></div><div><dt>Official reference comparisons</dt><dd>${s.pending?"Pending":s.datasets.length+" / "+s.datasets.length+" matched"}</dd></div><div><dt>Source revision</dt><dd><code>Shown from validated evidence</code></dd></div><div><dt>Engine revision</dt><dd><code>Shown from study engine pin</code></dd></div><div><dt>Validation timestamp</dt><dd>Illustrative snapshot</dd></div></dl><div class="evidence-actions">${external(`${REPO}/actions/workflows/yamaa-site.yml`,"Validation workflows","button soft")}</div></section><section class="panel"><div class="panel-heading"><h2>What a comparison establishes</h2>${icon("shield")}</div><div class="evidence-copy"><p>A successful build establishes that the specification executes. Reference agreement establishes that its output matches the staged official reference under the study's comparison policy.</p><ul class="policy-list"><li><b>Numeric tolerance</b> / absolute difference &lt;= 1e-10</li><li><b>Rows and missing values</b> / study-specific policies</li><li><b>Column labels</b> / checked against reference metadata</li><li><b>Coverage</b> / staged references, with remaining work explicit</li></ul><p style="margin-top:16px">This is regression evidence against staged references. It does not establish regulatory validation.</p>${external(`${REPO}/blob/main/docs/verification.md`,"Read verification policy","button soft")}</div></section></div><div class="method-note">${icon("branch")}<div><strong>Production evidence remains tied to the build that published it.</strong><br>The proposed implementation preserves the current safeguards against missing records, mixed revisions, and failed comparisons.</div></div>`;
}
function gallery() {
  return `<div class="breadcrumb"><span class="current">Study portfolio</span></div><div class="eyebrow">PILOT 7 / AGENTIC DATA STANDARDIZATION</div><h1 class="gallery-title">Every study. One review workspace.</h1><p class="gallery-description">Explore derivation coverage, inspect datasets, and follow the evidence behind each result.</p><div class="demo-note">${icon("info")}Design prototype. All displayed build and comparison results are illustrative.</div>${["pilot","synthetic"].map(type=>`<h2 class="gallery-group">${type==="pilot"?"Pilot studies":"Synthetic studies"}</h2><div class="study-cards">${studies.filter(s=>s.type===type).map(s=>`<button class="study-card" data-study="${s.id}"><span class="card-top">${icon(type==="synthetic"?"flask":"layers")}${badge(s.tag,s.pending?"amber":"green",false)}</span><h3>${s.title}</h3><p>${s.description}</p><span class="card-bottom">${s.pending?"Explore available materials":s.datasets.length+" active dataset specifications"}${icon("arrow-right")}</span></button>`).join("")}</div>`).join("")}${footer()}`;
}
function fillIcons() { document.querySelectorAll("[data-icon]").forEach(el=>el.innerHTML=icon(el.dataset.icon)); }
function render() {
  const main=document.getElementById("study-dashboard");
  if(!main) return;
  if(state.view==="gallery") main.innerHTML=gallery();
  else {
    main.innerHTML=pageFrame();
    document.getElementById("view-content").innerHTML=state.view==="overview"?overview():state.view==="datasets"?datasetsView():state.view==="findings"?findingsView():state.view==="materials"?materialsView():evidenceView();
  }
  fillIcons();
}
function readRoute() {
  const [path,query=""]=location.hash.replace(/^#/,"").split("?");
  const [hashStudy,view,dataset]=path.split("/");
  const main=document.getElementById("study-dashboard");
  if(!main) {
    if(studies.some(s=>s.id===hashStudy)) location.replace(studyUrl(hashStudy)+location.hash);
    return;
  }
  const pageStudy=main.dataset.study;
  if(pageStudy==="gallery") { state.view="gallery";render();return; }
  const study=studies.find(s=>s.id===pageStudy)||studies[0];
  if(hashStudy && studies.some(s=>s.id===hashStudy) && hashStudy!==study.id) {
    location.assign(studyUrl(hashStudy)+location.hash);return;
  }
  Object.assign(state,defaults);
  state.study=study;
  state.view=tabs.some(x=>x[0]===view)?view:"overview";
  state.dataset=study.datasets.includes(dataset)?dataset:study.datasets.includes(state.dataset)?state.dataset:study.datasets[0]||"ADSL";
  const params=new URLSearchParams(query);
  for(const key of ["search","findingSearch","rowSearch"]) state[key]=(params.get(key)||"").slice(0,200);
  state.subject=sampleSubjects.includes(params.get("subject"))?params.get("subject"):"";
  state.specOpen=params.get("specOpen")==="true";
  state.findingsOnly=params.get("findingsOnly")==="true";
  state.sort=["study","name","rows","findings"].includes(params.get("sort"))?params.get("sort"):"study";
  state.findingDataset=studyFindings().some(f=>f.dataset===params.get("findingDataset"))?params.get("findingDataset"):"";
  state.column=datasetPreview().columns.filter(c=>c!=="USUBJID").includes(params.get("column"))?params.get("column"):"";
  if(!document.getElementById("toast")) {
    const toast=document.createElement("div");toast.id="toast";toast.className="toast";toast.setAttribute("role","status");toast.setAttribute("aria-live","polite");document.body.appendChild(toast);
  }
  clearTimeout(toastTimer);
  document.getElementById("toast").classList.remove("visible");
  render();
}
function highlightSubject(subject) {
  state.subject=subject;
  const selector=document.getElementById("subject-select");if(selector)selector.value=subject;
  document.querySelectorAll("[data-subject-row]").forEach(el=>el.classList.toggle("highlighted",el.dataset.subjectRow===subject));
  document.querySelectorAll("[data-subject]").forEach(el=>el.setAttribute("aria-pressed",String(el.dataset.subject===subject)));
  saveView();
  const summary=document.querySelector(".preview-help[role=status]");
  if(summary)summary.textContent=`${previewRows(datasetPreview().rows).length} of 3 illustrative subjects shown${subject?`; ${subject} highlighted`:""}. Full dataset totals above are examples.`;
  showToast(subject?`${subject} highlighted across all previews`:"All subject highlights cleared");
}
let toastTimer;
function showToast(message) { const el=document.getElementById("toast");if(!el)return;el.textContent=message;el.classList.add("visible");clearTimeout(toastTimer);toastTimer=setTimeout(()=>el.classList.remove("visible"),2600); }
async function copyView() {
  saveView();
  try { await navigator.clipboard.writeText(location.href); showToast("Link copied with the current filters and selections"); }
  catch {
    document.getElementById("share-fallback").hidden=false;
    const input=document.getElementById("share-url");input.value=location.href;input.focus();input.select();
    showToast("Copy the selected view link");
  }
}
function downloadPreview() {
  const d=datasetPreview(), columns=d.columns.filter(c=>!state.column||c==="USUBJID"||c===state.column);
  const rows=[columns,...previewRows(d.rows).map(row=>columns.map(c=>row[d.columns.indexOf(c)]))];
  const csv=rows.map(row=>row.map(v=>'"'+String(v).replace(/"/g,'""')+'"').join(",")).join("\r\n")+"\r\n";
  const url=URL.createObjectURL(new Blob([csv],{type:"text/csv;charset=utf-8"}));
  const a=document.createElement("a");a.href=url;a.download=`${state.study.id}-${state.dataset.toLowerCase()}-illustrative-preview.csv`;a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);showToast("Illustrative preview downloaded with current row and column filters");
}
function refreshDatasets() {
  const overview=document.getElementById("dataset-overview"), list=document.getElementById("dataset-list");
  if(overview) overview.innerHTML=datasetTable();
  if(list) list.innerHTML=datasetOptions();
  saveView();
}
function downloadEvidence() {
  const report={illustrative:true,purpose:"Dashboard layout review only - no live validation evidence",study:state.study.id,status:state.study.pending?"pending":"example_success",datasets:state.study.datasets.map(domain=>({domain,rows:datasetInfo[domain][1],columns:datasetInfo[domain][2],build:"illustrative_success",comparison:"illustrative_match"}))};
  const url=URL.createObjectURL(new Blob([JSON.stringify(report,null,2)+"\n"],{type:"application/json"}));
  const a=document.createElement("a");a.href=url;a.download=`${state.study.id}-illustrative-evidence.json`;a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);showToast("Illustrative evidence downloaded");
}
document.addEventListener("click",event=>{
  const target=event.target.closest("button,[data-dataset]");if(!target)return;
  if(target.dataset.study){location.assign(studyUrl(target.dataset.study));return;}
  if(target.dataset.findingDataset){state.findingDataset=target.dataset.findingDataset;state.findingSearch="";navigate("findings");return;}
  if(target.dataset.reviewDataset){state.specOpen=true;state.column=target.dataset.column;state.rowSearch="";navigate("datasets",target.dataset.reviewDataset);return;}
  if(target.dataset.view){navigate(target.dataset.view);return;}
  if(target.dataset.dataset){state.column="";navigate("datasets",target.dataset.dataset);return;}
  if(target.dataset.subject){highlightSubject(state.subject===target.dataset.subject?"":target.dataset.subject);return;}
  if(target.id==="all-studies"){navigate("gallery");return;}
  if(target.id==="spec-toggle"){
    state.specOpen=!state.specOpen;document.getElementById("spec-panel").hidden=!state.specOpen;target.setAttribute("aria-expanded",String(state.specOpen));target.querySelector("span").textContent=(state.specOpen?"Hide":"Show")+" specification";target.classList.toggle("soft",state.specOpen);saveView();return;
  }
  if(target.id==="reset-datasets"){state.search="";state.sort="study";state.findingsOnly=false;render();saveView();document.getElementById("dataset-search")?.focus();return;}
  if(target.id==="reset-findings"){state.findingDataset="";state.findingSearch="";render();saveView();document.getElementById("finding-search").focus();return;}
  if(target.id==="reset-preview"){state.rowSearch="";state.column="";state.subject="";render();saveView();document.getElementById("row-search").focus();return;}
  if(target.id==="copy-view"){copyView();return;}
  if(target.id==="download-preview"){downloadPreview();return;}
  if(target.id==="download-evidence")downloadEvidence();
});
document.addEventListener("change",event=>{
  const el=event.target;
  if(el.id==="subject-select")highlightSubject(el.value);
  if(el.id==="dataset-sort"){state.sort=el.value;refreshDatasets();}
  if(el.id==="findings-only"){state.findingsOnly=el.checked;refreshDatasets();}
  if(el.id==="finding-dataset"){state.findingDataset=el.value;document.getElementById("finding-results").innerHTML=findingResults();saveView();}
  if(el.id==="column-select"){state.column=el.value;document.getElementById("preview-tables").innerHTML=previewTables();saveView();}
});
document.addEventListener("input",event=>{
  const el=event.target;
  if(el.id==="dataset-search"){state.search=el.value;refreshDatasets();}
  if(el.id==="finding-search"){state.findingSearch=el.value;document.getElementById("finding-results").innerHTML=findingResults();saveView();}
  if(el.id==="row-search"){state.rowSearch=el.value;document.getElementById("preview-tables").innerHTML=previewTables();saveView();}
});
window.addEventListener("hashchange",()=>{
  readRoute();
  const heading=document.querySelector("#view-content h2");
  if(heading){heading.tabIndex=-1;heading.focus();}
});
if(typeof document$ !== "undefined") document$.subscribe(readRoute);
else readRoute();

})();
