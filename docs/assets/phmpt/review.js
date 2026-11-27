/** PHMPT review page: one finding at a time, its evidence, how to rerun it, and a GitHub discussion for the verdict.
 *
 * Reads ../evidence.json (the bundle the yamaa_phmpt export writes). Shows
 * counts and reasons only; the bundle holds no participant-level data, and a
 * reviewer who wants rows reruns the kit on data fetched from PHMPT. */
import { LINK_LIMIT, reviewDestination } from "../dashboard/review-submit.js";

export const AGREEMENTS = {
  agree: "Agree",
  disagree: "Disagree",
  clarify: "Need clarification",
};
export const KINDS = { dataset: "ADaM dataset", define: "Define-XML", "define-gap": "Define engine gap" };
const REPO = "https://github.com/RConsortium/submissions-pilot7-synthetic-data";
const BLOB = `${REPO}/blob/main/phmpt/`;
const DRAFTS = "phmpt-review-drafts";

/** Findings that pass every filter; text matches id, claim or verdict, case-insensitively. */
export function filterFindings(findings, { study = "", kind = "", verdict = "", text = "" } = {}) {
  const needle = text.trim().toLowerCase();
  return findings.filter((f) =>
    (!study || f.study === study) && (!kind || f.kind === kind) && (!verdict || f.verdict === verdict) &&
    (!needle || [f.id, f.claim, f.verdict].some((s) => s.toLowerCase().includes(needle))));
}

/** The record behind a finding: a dataset row, a cut's define, or a define gap. */
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
    `**Evidence:** yamaa \`${evidence.meta.yamaa_commit}\`, export \`${evidence.meta.source_commit}\`, collected ${evidence.meta.collected}`,
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

function evidenceRows(evidence, f, rec) {
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
    for (const r of rec.reasons) rows.push([r.kind === "missing input" ? "Missing input" : "Known cause, to fix", `${esc(r.reason)} ${counts(r.cells)}`]);
    if (rec.unexplained_columns.length) rows.push(["No recorded reason yet", rec.unexplained_columns.map((c) => `<code>${esc(c)}</code>`).join(", ")]);
    rows.push(["Specification", `<a href="${BLOB}${esc(rec.spec)}">${esc(rec.spec)}</a> (${n(rec.spec_lines)} lines; layers: ${rec.layers.map(esc).join(" &lt; ")})`]);
    if (rec.source) rows.push(["Submitted dataset on PHMPT", `${esc(rec.source.member)}<br><small>in ${esc(rec.source.zip)}</small>`]);
  } else {
    const scoped = rec.received - rec.no_spec;
    rows.push(["Received elements of datasets with a spec", n(scoped)]);
    rows.push(["Reproduced byte for byte", n(rec.identical)]);
    rows.push(["Differ only by named engine gaps", n(rec.gap_only)]);
    rows.push(["Differ otherwise", n(rec.unexplained)]);
    if (rec.no_spec) rows.push(["Elements of datasets with no spec yet", `${n(rec.no_spec)} (${rec.no_spec_datasets.map(esc).join(", ")})`]);
    const gap = f.kind === "define-gap" ? f.id.split("/").pop() : null;
    if (gap && evidence.gaps[gap]) {
      const g = evidence.gaps[gap];
      rows.push(["Engine gap", `${esc(gap)}: ${md(g.title)} (<a href="https://github.com/elong0527/yamaa/issues/${g.yamaa_issue}">yamaa#${g.yamaa_issue}</a>)`]);
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
      <label>Search <input id="phmpt-text" type="search" placeholder="ADSL, define, G1..."></label>
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
  const show = (id) => {
    const f = all.find((x) => x.id === id);
    if (!f) { $("phmpt-detail").innerHTML = "<p>Select a finding to review it.</p>"; return; }
    const st = evidence.studies[f.study], cut = st.cuts[f.cut];
    const draft = readDrafts()[f.id] || { agreement: "", comment: "" };
    $("phmpt-detail").innerHTML = `
      <h2>${esc(st.title)} ${esc(cut.title)}${f.dataset ? " - " + esc(f.dataset) : ""}</h2>
      <p class="phmpt-claim">${md(f.claim)}</p>
      <p><a href="../${esc(f.page)}">Open it on the findings page</a></p>
      <h3>Evidence</h3>${evidenceRows(evidence, f, findingRecord(evidence, f))}
      <h3>Reproduce it</h3>
      <p>From the <a href="${REPO}/tree/main/phmpt">phmpt/</a> folder, with yamaa built from <code>yamaa.lock</code>
      (<a href="${BLOB}README.md">setup</a>). The data comes from PHMPT; the differences print on your machine.</p>
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
    $("phmpt-detail").addEventListener("input", () => saveDraft(f.id, current()));
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
  };
  for (const id of ["phmpt-study", "phmpt-kind", "phmpt-verdict", "phmpt-text"]) $(id).addEventListener("input", list);
  const route = () => show(decodeURIComponent(location.hash.slice(1)));
  window.addEventListener("hashchange", route);
  list();
  route();
}

if (typeof document$ !== "undefined") document$.subscribe(mount);
else if (typeof document !== "undefined") document.addEventListener("DOMContentLoaded", mount);
