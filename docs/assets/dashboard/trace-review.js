/** Expanded, source-backed evidence and an independent human review per issue. */
import { esc, link } from "./ui.js";
import { reviewComment } from "./review-comment.js";
import { comparisonLabel, findIssue, issueTrace, readReview } from "./issues.js";
import { AGREEMENTS, CRITICALITIES, createReviewDrafts } from "./review-drafts.js";

const plural = (n, word) => `${n} ${word}${n === 1 ? "" : "s"}`;
const label = (draft) => draft.status === "reviewed" ? "Saved locally" : draft.status === "draft" ? "Draft" : "Not reviewed";
const display = (value) => value == null ? "(missing)" : value === "" ? "(blank)" : String(value);
const cell = (item) => esc(!item?.present ? "(no record)" : item.column_present === false ? "(variable absent)" : display(item.value));

export function createTraceReview(ctx, comments) {
  let storage;
  try { storage = window.localStorage; }
  catch { storage = { getItem() { throw Error("Storage unavailable"); }, setItem() { throw Error("Storage unavailable"); } }; }
  const drafts = createReviewDrafts(storage);
  let dialog = null, issue = null, opener = null, overflow = "", subject = "";
  let restoreComments = null;
  const all = () => readReview(ctx.report).issues;
  const siblings = () => all().filter((i) => i.dataset === issue.dataset && i.variable === issue.variable);
  const currentDraft = () => drafts.load(ctx.model.id, issue, ctx.report);
  const examples = () => ctx.report.trace_examples?.[`${issue.dataset}.${issue.variable}`];

  function refreshRows(onlyId = "") {
    for (const element of ctx.root()?.querySelectorAll("[data-human-review]") || []) {
      if (onlyId && element.dataset.humanReview !== onlyId) continue;
      const item = findIssue(ctx.report, element.dataset.humanReview);
      if (!item) continue;
      const draft = drafts.load(ctx.model.id, item, ctx.report);
      element.textContent = draft.status === "unreviewed" ? "" : `Your review: ${label(draft)}${draft.stale ? " (evidence changed)" : ""}`;
    }
  }
  function close(restoreFocus = true) {
    if (!dialog) return;
    const target = opener;
    restoreComments?.(); restoreComments = null;
    dialog.close(); dialog.remove(); dialog = null;
    document.body.style.overflow = overflow;
    if (restoreFocus && target?.isConnected) target.focus({ preventScroll: true });
    refreshRows(issue.id);
  }
  function jump(id) {
    const scroller = dialog.querySelector(".trace-scroll"), section = dialog.querySelector(`#${id}`);
    scroller.scrollTo({ top: scroller.scrollTop + section.getBoundingClientRect().top - scroller.getBoundingClientRect().top - 22,
      behavior: matchMedia("(prefers-reduced-motion: reduce)").matches ? "instant" : "smooth" });
    if (id === "trace-your-review") section.querySelector("input")?.focus({ preventScroll: true });
  }
  function measures() {
    const pool = new Map(readReview(ctx.report).evidence.map((e) => [e.id, e]));
    return issue.trace.map((t) => ({ ...pool.get(t.evidence_id), role: t.role }))
      .filter((e) => ["comparison", "codelist", "note"].includes(e.type));
  }
  function measurements() {
    const measured = measures().filter((e) => e.type !== "note");
    if (!measured.length) return '<p class="trace-scope">No issue-specific data comparison. This finding compares source statements or specification text.</p>';
    return `<div class="trace-measurements">${measured.map((e) => `<article class="trace-measurement"><h4>${esc(comparisonLabel(e))}</h4>${e.type === "comparison"
      ? `<p><strong>${e.differ.toLocaleString()} / ${e.compared.toLocaleString()}</strong> records differ</p><small>${plural(e.subjects.length, "subject")} with differences</small>`
      : `<p>${plural(e.values.length, "value")} outside the documented codelist</p>`}<p class="trace-scope">${e.role === "context" ? "Context only; excluded from this issue's impact." : "Issue-specific measurement."}</p></article>`).join("")}</div><p class="trace-scope">Differences compare calculations with their stated target; they do not establish that the reference is wrong. Each comparison has its own denominator. Zero differences does not prove equivalent rules.</p>`;
  }
  function sampleSubjects() {
    const candidates = examples()?.subjects || [];
    const relevant = candidates.filter((s) => issue.impact.subjects.includes(s.id));
    return (relevant.length ? relevant : candidates).slice(0, 2);
  }
  function sampleView() {
    const data = examples(), choices = sampleSubjects();
    if (!choices.length) return `<p>${esc(data?.reason || "No row-aligned subject example is available for this finding. The source comparisons and complete check audit remain available.")}</p>`;
    if (!choices.some((s) => s.id === subject)) subject = choices[0].id;
    const chosen = choices.find((s) => s.id === subject),
      columns = [...data.keys.filter((k) => k !== data.subject_key), ...data.input_columns],
      headings = data.calculations.map((p, i) => p.reading === "literal" ? "Documented rule as written" : `Alternative interpretation ${i}`);
    const compared = measures().filter((e) => e.type === "comparison"),
      allMatch = compared.length > 0 && compared.every((e) => !e.differ);
    return `<div class="trace-subject-tabs" role="tablist" aria-label="Reference subjects">${choices.map((s, i) => `<button type="button" role="tab" id="trace-subject-${i}" aria-controls="trace-subject-panel" aria-selected="${s.id === subject}" tabindex="${s.id === subject ? 0 : -1}" data-trace-subject="${esc(s.id)}">${esc(s.id)}</button>`).join("")}</div><div id="trace-subject-panel" role="tabpanel" aria-labelledby="trace-subject-${choices.indexOf(chosen)}"><p class="trace-scope">Actual study records for <strong>${esc(chosen.id)}</strong>. ${chosen.rows.length} of ${chosen.total_rows} subject records shown${chosen.rows.length < chosen.total_rows ? "; informative records retained; the example is abbreviated" : ""}.</p><div class="trace-data-scroll" role="region" aria-label="Subject example calculations" tabindex="0"><table class="trace-data-table"><thead><tr>${columns.map((c) => `<th scope="col">${esc(c)}</th>`).join("")}<th scope="col">Reference ${esc(issue.variable)}</th><th scope="col">yamaa output</th>${headings.map((h) => `<th scope="col">${esc(h)}</th>`).join("")}</tr></thead><tbody>${chosen.rows.map((r) => `<tr>${columns.map((c) => `<td>${esc(display(Object.hasOwn(r.keys, c) ? r.keys[c] : r.inputs[c]))}</td>`).join("")}<td>${cell(r.reference)}</td><td>${cell(r.derived)}</td>${data.calculations.map((p) => `<td>${cell(r.calculations[p.column])}</td>`).join("")}</tr>`).join("")}</tbody></table></div><div class="trace-reading-notes">${data.calculations.map((p, i) => `<p><strong>${esc(headings[i])}:</strong> ${esc(p.reading === "literal" ? "Applies the documented condition exactly as written." : p.reading)}</p>`).join("")}</div></div><p class="trace-scope">${esc(data.scope)} Examples illustrate this variable's calculations; only the issue-specific measurements above determine its reported impact.</p>${allMatch ? '<p class="trace-limit">No differences were observed in the retained comparisons. These examples illustrate the rules; they do not demonstrate a failure.</p>' : ""}`;
  }
  function reviewForm() {
    const draft = currentDraft();
    function options(name, entries) {
      return `<div class="trace-review-choices">${Object.entries(entries).map(([value, text]) => `<label><input type="radio" name="${name}" value="${value}" ${draft[name] === value ? "checked" : ""}> ${text}</label>`).join("")}</div>`;
    }
    return `<form id="trace-your-review" class="trace-human-review" novalidate><header><h3>Your review</h3><p>Agreement and criticality are separate decisions. Your assessment does not resolve or change the published finding.</p></header><div class="trace-form-body">${draft.stale ? '<p class="trace-limit" role="status">The evidence changed since your previous assessment. Your choices are retained as a draft; review the current evidence and save again.</p>' : ""}<fieldset><legend>Do you agree with this finding? <small>Required</small></legend>${options("agreement", AGREEMENTS)}</fieldset><fieldset><legend>Is this finding critical? <small>Required</small></legend>${options("criticality", CRITICALITIES)}<p class="trace-scope">Working definition: a critical issue could materially affect analysis results or their interpretation.</p></fieldset><label class="trace-comment-label" for="trace-review-comment">Review comments <small>Optional</small></label><textarea id="trace-review-comment" name="comment" rows="4" maxlength="10000" placeholder="Explain your assessment, suggest a correction, or note missing evidence.">${esc(draft.comment)}</textarea><p class="trace-review-feedback" role="status" aria-live="polite" hidden></p><div class="trace-review-actions"><p class="trace-storage-note">Drafts save in this browser. Publish your assessment through the GitHub comment box below.</p><div><button class="button" type="button" data-trace-local>Save locally</button><button class="button primary" type="submit">Copy review &amp; open GitHub comments</button></div></div></div></form>`;
  }
  function discussionView() {
    return `<section id="trace-discussion" class="trace-discussion"><h3>Share your review on GitHub</h3><p>Publish to the same <strong>${esc(ctx.model.title)} / ${esc(issue.dataset)}</strong> discussion used by the SDTM -&gt; ADaM workspace.</p><p class="trace-scope">Copy your review above, paste it into the comment box below, then select <strong>Comment</strong> to publish. GitHub sign-in is handled by the comment box.</p><p class="trace-share-feedback" role="status" aria-live="polite" hidden></p><div data-trace-prepared hidden><label for="trace-github-comment">Comment to paste</label><textarea id="trace-github-comment" rows="7" readonly></textarea><p data-trace-comment-stale class="trace-limit" role="status" hidden>Your assessment changed. Copy the review again before posting.</p></div><button class="button" type="button" data-trace-open-comments>Open GitHub comments</button><div data-trace-comments hidden></div><p class="trace-scope">Comments are stored in ${link(ctx.index.comments.discussion_url, ctx.index.comments.repo)}. If the embed is unavailable, use that link to open GitHub Discussions.</p></section>`;
  }
  function openComments() {
    const target = dialog.querySelector("[data-trace-comments]");
    target.hidden = false;
    dialog.querySelector("[data-trace-open-comments]").hidden = true;
    if (!restoreComments) restoreComments = comments.attachComments(target, issue.dataset);
    jump("trace-discussion");
  }
  async function copyForGitHub() {
    const active = dialog, id = issue.id;
    let text;
    try { text = reviewComment(ctx.model, issue, currentDraft(), location.href); }
    catch (error) {
      feedback(error.message, true);
      dialog.querySelector(`input[name="${currentDraft().agreement ? "criticality" : "agreement"}"]`)?.focus({ preventScroll: true });
      return;
    }
    if (!save(false)) return;
    const prepared = dialog.querySelector("[data-trace-prepared]"),
      textarea = dialog.querySelector("#trace-github-comment");
    prepared.hidden = false; textarea.value = text;
    dialog.querySelector("[data-trace-comment-stale]").hidden = true;
    let copied = false;
    try { await navigator.clipboard.writeText(text); copied = true; }
    catch { /* The visible, selectable text remains available without clipboard access. */ }
    if (dialog !== active || issue.id !== id) return;
    openComments();
    const status = dialog.querySelector(".trace-share-feedback");
    status.hidden = false;
    dialog.querySelector(".trace-review-feedback").hidden = true;
    status.textContent = copied
      ? "Review copied. Paste it into the GitHub comment box below, then select Comment to publish."
      : "Clipboard access is unavailable. Copy the prepared text below, paste it into the GitHub comment box, then select Comment to publish.";
    if (!copied) { textarea.focus({ preventScroll: true }); textarea.select(); }
  }
  function updateStatus() {
    const draft = currentDraft();
    dialog.querySelector("[data-trace-status]").textContent = `Your review: ${label(draft)}`;
    const group = siblings(), count = group.filter((i) => drafts.load(ctx.model.id, i, ctx.report).status === "reviewed").length;
    dialog.querySelector("[data-trace-progress]").textContent = `${count} of ${group.length} reviews saved locally`;
    for (const button of dialog.querySelectorAll("[data-trace-sibling]")) {
      const other = findIssue(ctx.report, button.dataset.traceSibling);
      button.querySelector("small").textContent = label(drafts.load(ctx.model.id, other, ctx.report));
    }
    const note = dialog.querySelector(".trace-storage-note");
    if (note && !drafts.available) note.textContent = "Browser storage is unavailable. Your draft lasts for this session. Use GitHub comments below to publish it.";
    refreshRows(issue.id);
  }
  function feedback(message, error = false) {
    const element = dialog.querySelector(".trace-review-feedback");
    element.textContent = message; element.hidden = false;
    element.classList.toggle("trace-error", error);
  }
  function save(complete) {
    const form = dialog.querySelector("form"), values = Object.fromEntries(new FormData(form));
    try {
      drafts.save(ctx.model.id, issue, ctx.report, values, complete);
      updateStatus();
      return true;
    } catch (error) {
      feedback(error.message, true);
      form.querySelector(`input[name="${values.agreement ? "criticality" : "agreement"}"]`)?.focus({ preventScroll: true });
      return false;
    }
  }
  function download() {
    const payload = {
      schema_version: 1, study: ctx.model.id, source_revision: ctx.model.revision,
      exported_at: new Date().toISOString(),
      reviews: siblings().map((i) => ({ issue: i.id, dataset: i.dataset, variable: i.variable,
        title: i.title, check_ids: i.check_ids, ...drafts.load(ctx.model.id, i, ctx.report) })),
    };
    const url = URL.createObjectURL(new Blob([JSON.stringify(payload, null, 2)], { type: "application/json" })),
      anchor = document.createElement("a");
    anchor.href = url; anchor.download = `${ctx.model.id}-${issue.dataset}-${issue.variable || "findings"}-review.json`;
    anchor.click(); setTimeout(() => URL.revokeObjectURL(url), 1000);
  }
  function render() {
    restoreComments?.(); restoreComments = null;
    const group = siblings(), at = group.indexOf(issue);
    dialog.innerHTML = `<div class="trace-review-shell"><header class="trace-review-header"><div><p>${esc(ctx.model.title)} / ${esc(issue.dataset)} / Trace evidence</p><h2>${esc(issue.dataset + (issue.variable ? "." + issue.variable : ""))}</h2></div><div><span class="status neutral" data-trace-status></span><button class="button" data-trace-download>Download review</button><button class="button" data-trace-close aria-label="Close trace evidence">Close</button></div></header><div class="trace-review-layout"><aside class="trace-review-nav"><h3>Findings for this variable</h3><nav aria-label="Choose a finding">${group.map((i, n) => `<button data-trace-sibling="${esc(i.id)}" ${i.id === issue.id ? 'aria-current="page"' : ""}><span>${String(n + 1).padStart(2, "0")}</span><span>${esc(i.title)}<small></small></span></button>`).join("")}</nav><h3>On this page</h3><nav aria-label="Evidence sections">${[["trace-finding", "The finding"], ["trace-sources", "What the sources say"], ["trace-examples", "Subject examples"], ["trace-fix", "Recommended fix"], ["trace-your-review", "Your review"], ["trace-discussion", "GitHub comments"]].map(([id, text]) => `<button data-trace-section="${id}">${text}</button>`).join("")}</nav></aside><div class="trace-scroll"><main class="trace-review-content"><section id="trace-finding"><p class="eyebrow">Finding ${at + 1} of ${group.length} <span class="status neutral">${esc(issue.kind.replaceAll("_", " "))}</span></p><h2 id="trace-review-title" tabindex="-1">${esc(issue.title)}</h2><p class="trace-introduction">${esc(issue.summary)}</p>${measurements()}</section><section id="trace-sources"><h3>1. What the sources say</h3>${issueTrace(issue, ctx.report, { sourcesOnly: true })}</section><section id="trace-examples"><h3>2. Follow the subject records</h3><div data-trace-samples>${sampleView()}</div></section><section id="trace-fix"><h3>3. Recommended fix</h3><div class="trace-fix"><p>${esc(issue.action || "The retained evidence does not specify a correction. Confirm the intended rule before changing the specification or documents.")}</p></div></section>${reviewForm()}${discussionView()}<details class="trace-technical"><summary>Supporting details: calculations, technical names and check audit</summary><p>Names containing a double underscore identify alternative review calculations: VARIABLE__READING. They do not add submission variables. The interpretation descriptions above explain what changes.</p>${issueTrace(issue, ctx.report, { auditOnly: true })}<button class="text-link" data-finding="${esc(issue.id)}">Open evidence in workspace${issue.impact.subject_count ? ` (${plural(issue.impact.subject_count, "subject")})` : ""}</button></details></main></div></div><footer class="trace-review-footer"><div><strong data-trace-progress></strong><small>Local saves and GitHub comments are separate</small></div><div>${at > 0 ? `<button class="button" data-trace-sibling="${esc(group[at - 1].id)}">Previous finding<small hidden></small></button>` : ""}${at + 1 < group.length ? `<button class="button" data-trace-sibling="${esc(group[at + 1].id)}">Next finding<small hidden></small></button>` : ""}<button class="button primary" data-trace-section="trace-your-review">Add your review</button></div></footer></div>`;
    updateStatus();
    dialog.querySelector(".trace-scroll").scrollTop = 0;
  }
  function open(id, trigger) {
    const found = findIssue(ctx.report, id);
    if (!found) return;
    close(false); issue = found; opener = trigger; subject = "";
    dialog = document.createElement("dialog"); dialog.className = "trace-review-dialog";
    dialog.setAttribute("aria-labelledby", "trace-review-title");
    ctx.root().append(dialog); render();
    overflow = document.body.style.overflow; document.body.style.overflow = "hidden";
    dialog.addEventListener("cancel", (event) => { event.preventDefault(); close(); });
    dialog.addEventListener("click", (event) => {
      const target = event.target.closest("button");
      if (!target) return;
      if (target.hasAttribute("data-trace-close")) close();
      else if (target.hasAttribute("data-trace-download")) download();
      else if (target.dataset.traceSibling) { issue = findIssue(ctx.report, target.dataset.traceSibling); render(); dialog.querySelector("h2[tabindex]").focus({ preventScroll: true }); }
      else if (target.dataset.traceSection) jump(target.dataset.traceSection);
      else if (target.dataset.traceSubject) { subject = target.dataset.traceSubject; dialog.querySelector("[data-trace-samples]").innerHTML = sampleView(); jump("trace-examples"); dialog.querySelector('[aria-selected="true"]')?.focus({ preventScroll: true }); }
      else if (target.hasAttribute("data-trace-open-comments")) openComments();
      else if (target.hasAttribute("data-trace-local") && save(true)) feedback(drafts.available ? "Assessment saved only in this browser. Use GitHub comments below to publish it." : "Assessment kept only for this session. Use GitHub comments below to publish it.");
    });
    dialog.addEventListener("keydown", (event) => {
      if (!event.target.matches("[data-trace-subject]") || !["ArrowLeft", "ArrowRight", "Home", "End"].includes(event.key)) return;
      event.preventDefault();
      const tabs = [...dialog.querySelectorAll("[data-trace-subject]")], at = tabs.indexOf(event.target),
        next = event.key === "Home" ? 0 : event.key === "End" ? tabs.length - 1 : (at + (event.key === "ArrowRight" ? 1 : -1) + tabs.length) % tabs.length;
      tabs[next].click();
    });
    dialog.addEventListener("input", (event) => { if (event.target.closest("form")) { save(false); dialog.querySelector(".trace-review-feedback").hidden = true; const prepared = dialog.querySelector("[data-trace-prepared]"); if (!prepared.hidden) dialog.querySelector("[data-trace-comment-stale]").hidden = false; } });
    dialog.addEventListener("submit", (event) => {
      event.preventDefault();
      void copyForGitHub();
    });
    dialog.showModal(); dialog.querySelector("[data-trace-close]").focus({ preventScroll: true });
  }
  return { open, close, refreshRows, get isOpen() { return Boolean(dialog); } };
}
