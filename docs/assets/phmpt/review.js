/** PHMPT review page: one finding at a time, its evidence, every column of a dataset, how to rerun it, and a
 * GitHub discussion for the verdict.
 *
 * Reads ../evidence.json and, when a dataset finding opens, ../columns.json (both written by
 * phmpt/scripts/site/publish.py). Shows names, counts and reasons only; the bundle holds no participant-level
 * data, and a reviewer who wants rows reruns the kit on data fetched from PHMPT.
 *
 * Links: #<finding id> opens a finding; #<finding id>/<COLUMN> opens a dataset at one column; #phmpt/<study>
 * or #phmpt/<study>/<cut> lists that study's or cut's findings. */
import { LINK_LIMIT, reviewDestination } from "../dashboard/review-submit.js";

export const AGREEMENTS = {
  agree: "Agree",
  disagree: "Disagree",
  clarify: "Need clarification",
};
export const KINDS = { dataset: "ADaM dataset", define: "Define-XML", "define-defect": "Defect of the submitted define" };
const REPO = "https://github.com/RConsortium/submissions-pilot7-synthetic-data";
const BLOB = `${REPO}/blob/main/phmpt/`;
const DRAFTS = "phmpt-review-drafts";

/** Where a link points: a finding, a column of a dataset finding, or a study or cut prefix to list. */
export function resolveRoute(findings, hash) {
  const id = decodeURIComponent(String(hash || "").replace(/^#/, ""));
  if (!id) return { kind: "none" };
  const exact = findings.find((f) => f.id === id);
  if (exact) return { kind: "finding", finding: exact };
  const cut = id.lastIndexOf("/");
  const parent = cut > 0 ? findings.find((f) => f.id === id.slice(0, cut) && f.kind === "dataset") : null;
  if (parent) return { kind: "column", finding: parent, column: id.slice(cut + 1) };
  const prefix = id.replace(/\/+$/, "") + "/";
  if (findings.some((f) => f.id.startsWith(prefix))) return { kind: "prefix", text: prefix.replace(/^phmpt\//, "") };
  return { kind: "none" };
}

/** A dataset's column rows as objects ({name, status, cells, redacted, layer, line, note}). */
export function columnRows(table, id) {
  const d = table?.datasets?.[id];
  if (!d) return null;
  return d.columns.map((row) => Object.fromEntries(table.fields.map((f, i) => [f, row[i]])));
}

/** {status: count} in the order of the table's statuses, leaving out those with no column. */
export function columnSummary(table, rows) {
  const n = {};
  for (const r of rows) n[r.status] = (n[r.status] || 0) + 1;
  return Object.keys(table.statuses).filter((s) => n[s]).map((s) => [s, n[s]]);
}

/** Columns with this status (all when empty) whose name contains the text, case-insensitively. */
export function filterColumns(rows, { status = "", text = "" } = {}) {
  const needle = text.trim().toLowerCase();
  return rows.filter((r) => (!status || r.status === status) && (!needle || r.name.toLowerCase().includes(needle)));
}

/** Findings that pass every filter; text matches id, claim or verdict, case-insensitively. */
export function filterFindings(findings, { study = "", kind = "", verdict = "", text = "" } = {}) {
  const needle = text.trim().toLowerCase();
  return findings.filter((f) =>
    (!study || f.study === study) && (!kind || f.kind === kind) && (!verdict || f.verdict === verdict) &&
    (!needle || [f.id, f.claim, f.verdict].some((s) => s.toLowerCase().includes(needle))));
}

/** The record behind a finding: a dataset row, a cut's define, or a defect of the submitted define. */
export function findingRecord(evidence, finding) {
  const cut = evidence.studies[finding.study]?.cuts[finding.cut];
  if (!cut) return null;
  if (finding.kind === "dataset") return cut.datasets.find((d) => d.dataset === finding.dataset) || null;
  return cut.define;
}

/** The assessment as markdown for the discussion body. */
export function reviewBody(evidence, finding, review, pageUrl) {
  if (!Object.hasOwn(AGREEMENTS, review.agreement)) throw Error("Choose Agree, Disagree or Need clarification.");
  const url = new URL(pageUrl);
  url.search = "";
  url.hash = finding.id;
  return [
    `## PHMPT review: \`${finding.id}\``,
    "",
    `**Assessment:** ${AGREEMENTS[review.agreement]}`,
    "",
    review.comment.trim() || "No additional comments.",
    "",
    `**Claim:** ${finding.claim}`,
    `**Verdict reported:** ${finding.verdict}`,
    `**Evidence:** yamaa \`${evidence.meta.yamaa_commit}\`, results at \`${evidence.meta.source_commit}\`, collected ${evidence.meta.collected}`,
    `[Open the finding](${url.href})`,
    "",
    "_Do not paste rows, subject identifiers or program text from PHMPT files; describe the difference instead._",
  ].join("\n");
}

/** A pre-filled GitHub discussion composer for one assessment; the reviewer still selects Start discussion. */
export function discussionLink(reviewUrl, evidence, finding, review, pageUrl) {
  if (!reviewDestination({ review_url: reviewUrl })) throw Error("The review destination is not a GitHub discussions/new link.");
  const title = `PHMPT review: ${finding.id} - ${AGREEMENTS[review.agreement] || ""}`.slice(0, 200);
  const body = reviewBody(evidence, finding, review, pageUrl);
  const url = new URL(reviewUrl);
  url.searchParams.set("title", title);
  url.searchParams.set("body", body);
  if (url.href.length <= LINK_LIMIT) return { url: url.href, title, body, prefilled: true };
  url.searchParams.delete("body");
  return { url: url.href, title, body, prefilled: false };
}

const esc = (s) => String(s ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[c]);
/** Escaped text whose `code` spans render as code (claims and gap titles are written that way). */
const md = (s) => esc(s).replace(/`([^`]+)`/g, "<code>$1</code>");
const n = (x) => Number(x || 0).toLocaleString("en-US");
const counts = (o) => Object.entries(o || {}).map(([k, v]) => `<code>${esc(k)}</code> ${n(v)}`).join(", ");

function readDrafts() {
  try { return JSON.parse(localStorage.getItem(DRAFTS) || "{}"); } catch { return {}; }
}
function saveDraft(id, draft) {
  try { localStorage.setItem(DRAFTS, JSON.stringify({ ...readDrafts(), [id]: draft })); } catch { /* storage is optional */ }
}

export function evidenceRows(evidence, f, rec) {
  if (!rec) return "<p>No record behind this finding.</p>";
  const rows = [];
  if (f.kind === "dataset") {
    rows.push(["Rows x columns", `${n(rec.rows)} x ${n(rec.cols)} submitted; ${n(rec.out_rows)} x ${n(rec.out_cols)} derived`]);
    rows.push(["Cells compared", n(rec.cells)]);
    rows.push(["Cells that differ", n(rec.mismatched_cells) + (Object.keys(rec.mismatched_columns).length ? ` (${counts(rec.mismatched_columns)})` : "")]);
    if (rec.within_tolerance_cells) rows.push(["Equal within 1e-10", n(rec.within_tolerance_cells)]);
    if (rec.space_only_cells) rows.push(["Differ only by spaces", n(rec.space_only_cells)]);
    if (rec.redacted_cells) rows.push(["Redacted to (b)(6), not compared", `${n(rec.redacted_cells)} (${counts(rec.redacted_columns)})`]);
    if (rec.carried_columns.length) rows.push(["Carried from the submitted data, not derived", rec.carried_columns.map((c) => `<code>${esc(c)}</code>`).join(", ")]);
    if (rec.missing_columns.length) rows.push(["Not derived", rec.missing_columns.map((c) => `<code>${esc(c)}</code>`).join(", ")]);
    if (rec.missing_input) rows.push(["Missing input", `${esc(rec.missing_input.missing)}. ${esc(rec.missing_input.reason)}`]);
    if (rec.submitted_defect) rows.push(["Submitted-file defect", `${esc(rec.submitted_defect.defect)}. ${esc(rec.submitted_defect.reason)} ${counts(rec.submitted_defect.cells)}`]);
    if (rec.note) rows.push(["Note", esc(rec.note)]);
    for (const r of rec.reasons) rows.push([r.kind === "missing input" ? "Missing input" : "Known cause, to fix", `${esc(r.reason)} ${counts(r.cells)}`]);
    if (rec.unexplained_columns.length) rows.push(["No recorded reason yet", rec.unexplained_columns.map((c) => `<code>${esc(c)}</code>`).join(", ")]);
    rows.push(["Specification", `<a href="${BLOB}${esc(rec.spec)}">${esc(rec.spec)}</a> (${n(rec.spec_lines)} lines; layers: ${rec.layers.map(esc).join(" &lt; ")})`]);
    if (rec.source) rows.push(["Submitted dataset on PHMPT", `${esc(rec.source.member)}<br><small>in ${esc(rec.source.zip)}</small>`]);
  } else {
    const scoped = rec.received - rec.no_spec;
    rows.push(["Received elements of datasets with a spec", n(scoped)]);
    rows.push(["Reproduced byte for byte", n(rec.identical)]);
    rows.push(["Differ only by defects of the submitted define", n(rec.gap_only)]);
    rows.push(["Differ otherwise", n(rec.unexplained)]);
    if (rec.no_spec) rows.push(["Elements of datasets with no spec yet", `${n(rec.no_spec)} (${rec.no_spec_datasets.map(esc).join(", ")})`]);
    // Bundle schema 1 keeps the key `gaps`; it holds the defects of the submitted define.
    const defect = f.kind === "define-defect" ? f.id.split("/").pop() : null;
    if (defect && evidence.gaps[defect]) {
      const d = evidence.gaps[defect];
      rows.push(["Defect of the submitted define", `${md(d.title)} (owner decision: <a href="https://github.com/elong0527/yamaa/issues/${d.yamaa_issue}">yamaa#${d.yamaa_issue}</a>)`]);
    }
    rows.push(["Received define on PHMPT", `${esc(rec.source.member)}<br><small>in ${esc(rec.source.zip)}</small>`]);
  }
  return `<table><tbody>${rows.map(([k, v]) => `<tr><th scope="row">${esc(k)}</th><td>${v}</td></tr>`).join("")}</tbody></table>`;
}

function mount() {
  const root = document.getElementById("phmpt-review");
  if (!root || root.dataset.mounted) return;
  root.dataset.mounted = "1";
  const reviewUrl = root.dataset.reviewUrl;
  root.innerHTML = "<p>Loading the findings...</p>";
  fetch(new URL("../evidence.json", location.href)).then((r) => {
    if (!r.ok) throw Error(`Cannot load the findings (${r.status}).`);
    return r.json();
  }).then((evidence) => render(root, evidence, reviewUrl)).catch((e) => {
    root.innerHTML = `<p class="phmpt-error">${esc(e.message)}</p>`;
  });
}

function render(root, evidence, reviewUrl) {
  const all = evidence.findings;
  const studies = Object.entries(evidence.studies);
  const verdicts = [...new Set(all.map((f) => f.verdict))].sort();
  const opt = (v, label) => `<option value="${esc(v)}">${esc(label)}</option>`;
  root.innerHTML = `
    <div class="phmpt-filters" role="search">
      <label>Study <select id="phmpt-study">${opt("", "All")}${studies.map(([k, s]) => opt(k, s.title)).join("")}</select></label>
      <label>Kind <select id="phmpt-kind">${opt("", "All")}${Object.entries(KINDS).map(([k, v]) => opt(k, v)).join("")}</select></label>
      <label>Verdict <select id="phmpt-verdict">${opt("", "All")}${verdicts.map((v) => opt(v, v)).join("")}</select></label>
      <label>Search <input id="phmpt-text" type="search" placeholder="ADSL, define, repeated-order..."></label>
    </div>
    <p id="phmpt-count" aria-live="polite"></p>
    <div class="phmpt-layout">
      <ul id="phmpt-list" class="phmpt-list" aria-label="Findings"></ul>
      <section id="phmpt-detail" class="phmpt-detail" aria-live="polite"></section>
    </div>`;
  const $ = (id) => root.querySelector(`#${id}`);
  const filters = () => ({ study: $("phmpt-study").value, kind: $("phmpt-kind").value,
                           verdict: $("phmpt-verdict").value, text: $("phmpt-text").value });
  const list = () => {
    const shown = filterFindings(all, filters());
    $("phmpt-count").textContent = `${shown.length} of ${all.length} findings`;
    $("phmpt-list").innerHTML = shown.map((f) =>
      `<li><a href="#${esc(f.id)}" data-id="${esc(f.id)}"><code>${esc(f.id.replace(/^phmpt\//, ""))}</code><br>` +
      `<span class="phmpt-verdict">${esc(f.verdict)}</span></a></li>`).join("");
  };
  const show = (f, column = "") => {
    if (!f) {
      $("phmpt-detail").innerHTML = "<p>Select a finding to review it.</p>";
      $("phmpt-detail").oninput = null;
      return;
    }
    const st = evidence.studies[f.study], cut = st.cuts[f.cut];
    const draft = readDrafts()[f.id] || { agreement: "", comment: "" };
    $("phmpt-detail").innerHTML = `
      <p class="phmpt-crumbs"><a href="../findings/${esc(f.study)}/">${esc(st.title)}</a> /
        <a href="../${esc(f.page)}">${esc(cut.title)}</a>${f.dataset ? " / " + esc(f.dataset) : ""}</p>
      <h2>${esc(st.title)} ${esc(cut.title)}${f.dataset ? " - " + esc(f.dataset) : ""}</h2>
      <p class="phmpt-claim">${md(f.claim)}</p>
      <h3>Evidence</h3>${evidenceRows(evidence, f, findingRecord(evidence, f))}
      ${f.kind === "dataset" ? '<h3>Columns</h3><div id="phmpt-columns" class="phmpt-columns"><p>Loading the columns...</p></div>' : ""}
      <h3>Reproduce it</h3>
      <p>In the <a href="${REPO}/tree/main/phmpt">phmpt/</a> folder, after <code>sh reproduce.sh setup</code> and
      <code>. .local-run/venv/bin/activate</code> (<a href="${BLOB}reproduce.sh">reproduce.sh</a>).
      The data comes from PHMPT; the differences print on your machine.</p>
      <pre><code>${f.reproduce.map(esc).join("\n")}</code></pre>
      <h3>Your review</h3>
      <fieldset class="phmpt-agreement"><legend>Does the evidence support the claim?</legend>
        ${Object.entries(AGREEMENTS).map(([k, v]) => `<label><input type="radio" name="phmpt-agreement" value="${k}"${draft.agreement === k ? " checked" : ""}> ${v}</label>`).join(" ")}
      </fieldset>
      <label for="phmpt-comment">What you checked and found</label>
      <textarea id="phmpt-comment" rows="5">${esc(draft.comment)}</textarea>
      <p class="phmpt-warning">Do not paste rows, subject identifiers or program text from PHMPT files; describe the difference instead.</p>
      <button type="button" class="md-button md-button--primary" id="phmpt-submit">Submit review on GitHub</button>
      <p id="phmpt-status" aria-live="polite"></p>`;
    const current = () => ({ agreement: root.querySelector("input[name=phmpt-agreement]:checked")?.value || "",
                             comment: $("phmpt-comment").value });
    // One handler on the panel, replaced with each finding, so a draft is saved only under its own finding.
    $("phmpt-detail").oninput = (e) => { if (!e.target.closest(".phmpt-columns")) saveDraft(f.id, current()); };
    $("phmpt-submit").addEventListener("click", () => {
      try {
        const link = discussionLink(reviewUrl, evidence, f, current(), location.href);
        window.open(link.url, "_blank", "noopener");
        $("phmpt-status").textContent = link.prefilled
          ? "GitHub opened with your review. Check it, then select Start discussion."
          : "GitHub opened with the title only: paste the assessment below as the body.";
        if (!link.prefilled) $("phmpt-status").insertAdjacentHTML("beforeend", `<pre>${esc(link.body)}</pre>`);
      } catch (e) {
        $("phmpt-status").textContent = e.message;
      }
    });
    if (f.kind === "dataset") {
      loadColumns().then((table) => {
        const box = $("phmpt-columns");
        if (box) renderColumns(box, table, f, column);
      });
    }
  };
  for (const id of ["phmpt-study", "phmpt-kind", "phmpt-verdict", "phmpt-text"]) $(id).addEventListener("input", list);
  const route = () => {
    const r = resolveRoute(all, location.hash);
    if (r.kind === "prefix") {
      $("phmpt-text").value = r.text;
      list();
      show(null);
      return;
    }
    show(r.finding, r.column);
  };
  window.addEventListener("hashchange", route);
  list();
  route();
}

let columnsLoad;
/** columns.json, fetched once, when the first dataset finding opens; null when it cannot be read. */
function loadColumns() {
  columnsLoad ||= fetch(new URL("../columns.json", location.href)).then((r) => (r.ok ? r.json() : null)).catch(() => null);
  return columnsLoad;
}

/** Every submitted column of one dataset: a filter by result, a search, and a row per column. */
export function columnsTable(table, f, rows, { status = "", text = "" } = {}) {
  const d = table.datasets[f.id];
  const shown = filterColumns(rows, { status, text });
  const spec = (r) => (r.layer === null ? "not derived"
    : `<a href="${BLOB}${esc(d.layers[r.layer])}#L${r.line}">${esc(d.layers[r.layer].split("/").pop())}:${r.line}</a>`);
  const body = shown.map((r) => `<tr data-status="${esc(r.status)}">
      <th scope="row"><a href="#${esc(f.id)}/${esc(r.name)}" title="Link to this column"><code>${esc(r.name)}</code></a></th>
      <td><span class="phmpt-key phmpt-col-${esc(r.status.replace(/ /g, "-"))}"></span> ${esc(table.statuses[r.status] || r.status)}</td>
      <td>${r.cells ? n(r.cells) : ""}</td><td>${r.redacted ? n(r.redacted) : ""}</td><td>${spec(r)}</td>
      <td>${r.note === null ? "" : md(d.notes[r.note])}</td></tr>`).join("");
  return `<p class="phmpt-col-count">${shown.length} of ${rows.length} columns</p>
    <div class="phmpt-col-table"><table>
      <thead><tr><th scope="col">Column</th><th scope="col">Result</th><th scope="col" title="Cells that differ">Differ</th>
      <th scope="col" title="Submitted cells FDA redacted to (b)(6), not compared">Redacted</th><th scope="col">Derived in</th>
      <th scope="col">Recorded reason</th></tr></thead>
      <tbody>${body || '<tr><td colspan="6">No column matches.</td></tr>'}</tbody></table></div>`;
}

function renderColumns(box, table, f, column) {
  const rows = table && columnRows(table, f.id);
  if (!rows) {
    box.innerHTML = "<p>The column list is not available for this dataset.</p>";
    return;
  }
  const state = { status: "", text: column || "" };
  const summary = columnSummary(table, rows);
  box.innerHTML = `
    <p>Every column of the submitted dataset, in its order, with its result. <em>Absent input</em>, <em>carried</em>
    and <em>dataset outside the set</em> columns are outside the analysis set; <em>rows differ</em> means the column is
    equal where rows pair but the dataset has rows on one side only. <em>Derived in</em> opens the spec line that
    derives the column; a column name links to it here.</p>
    <div class="phmpt-col-filters" role="group" aria-label="Show columns by result">
      <button type="button" class="phmpt-chip" data-status="" aria-pressed="true">All ${n(rows.length)}</button>
      ${summary.map(([s, k]) => `<button type="button" class="phmpt-chip" data-status="${esc(s)}" aria-pressed="false">
        <span class="phmpt-key phmpt-col-${esc(s.replace(/ /g, "-"))}"></span>${esc(table.statuses[s])} ${n(k)}</button>`).join("")}
      <label>Column <input type="search" class="phmpt-col-search" value="${esc(state.text)}" placeholder="AVAL"></label>
    </div>
    <div class="phmpt-col-body"></div>`;
  const draw = () => {
    box.querySelector(".phmpt-col-body").innerHTML = columnsTable(table, f, rows, state);
    for (const b of box.querySelectorAll(".phmpt-chip")) b.setAttribute("aria-pressed", String(b.dataset.status === state.status));
  };
  box.querySelector(".phmpt-col-filters").addEventListener("click", (e) => {
    const b = e.target.closest(".phmpt-chip");
    if (b) { state.status = b.dataset.status; draw(); }
  });
  box.querySelector(".phmpt-col-search").addEventListener("input", (e) => { state.text = e.target.value; draw(); });
  draw();
  if (column) box.scrollIntoView({ block: "start" });
}

if (typeof document$ !== "undefined") document$.subscribe(mount);
else if (typeof document !== "undefined") document.addEventListener("DOMContentLoaded", mount);
