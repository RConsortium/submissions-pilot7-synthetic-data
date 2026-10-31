/** Expanded, source-backed evidence and an independent human review per issue. */
import { esc, link } from "./ui.js";
import { reviewComment } from "./review-comment.js";
import { reviewDestination, reviewDiscussion } from "./review-submit.js";
import { findIssue, readReview, issueTrace } from "./issues.js";
import { AGREEMENTS, CRITICALITIES, SIDES, createReviewDrafts, draftLabel, nextUnreviewed } from "./review-drafts.js";
import { reviewComparison } from "./review-sources.js";

const display = (value) => value == null ? "(missing)" : value === "" ? "(blank)" : String(value);
const cell = (item) => esc(!item?.present ? "(no record)" : item.column_present === false ? "(variable absent)" : display(item.value));

// Compare record presence, variable presence and typed values independently.
const sameCell = (a, b) => Boolean(a?.present) === Boolean(b?.present) &&
  (!a?.present || (a.column_present !== false) === (b.column_present !== false) &&
    (a.column_present === false || Object.is(a.value, b.value)));

export function subjectDifferenceCells(row, calculations, context = "") {
  const differs = calculations.map((p) => !sameCell(row.reference, row.calculations[p.column]));
  const render = (item, different, details = "") => `<td${different ? ' class="trace-cell-difference" title="Differs from the compared value"' : ""}>${different ? '<span class="sr-only">Difference: </span>' : ""}${details}${cell(item)}</td>`;
  return render(row.reference, differs.some(Boolean), context) + calculations.map((p, i) => render(row.calculations[p.column], differs[i])).join("");
}

export function createTraceReview(ctx, sources) {
  let storage;
  try { storage = window.localStorage; }
  catch { storage = { getItem() { throw Error("Storage unavailable"); }, setItem() { throw Error("Storage unavailable"); } }; }
  const drafts = ctx.drafts || createReviewDrafts(storage);
  const destination = () => reviewDestination(ctx.index?.comments);
  let dialog = null, issue = null, opener = null, overflow = "", subject = "";
  const all = () => readReview(ctx.report).issues;
  const siblings = () => all().filter((i) => i.dataset === issue.dataset && i.variable === issue.variable);
  const currentDraft = () => drafts.load(ctx.model.id, issue, ctx.report);
  const next = () => nextUnreviewed(drafts, ctx.model.id, all(), ctx.report, issue.id);
  const examples = () => ctx.report.trace_examples?.[`${issue.dataset}.${issue.variable}`];

  function refreshRows(onlyId = "") {
    for (const element of ctx.root()?.querySelectorAll("[data-human-review]") || []) {
      if (onlyId && element.dataset.humanReview !== onlyId) continue;
      const item = findIssue(ctx.report, element.dataset.humanReview);
      if (!item) continue;
      const draft = drafts.load(ctx.model.id, item, ctx.report);
      element.dataset.reviewStatus = draft.status;
      element.textContent = draft.status === "unreviewed" ? "" : `Your review: ${draftLabel(draft)}${draft.stale ? " (evidence changed)" : ""}`;
    }
    ctx.refreshLedger?.();
  }
  function close(restoreFocus = true) {
    sources?.close(false);
    if (!dialog) return;
    const target = opener;
    dialog.close(); dialog.remove(); dialog = null;
    document.body.style.overflow = overflow;
    // Drop the finding from the link only while the link still names it: a navigation that
    // closes the review has already moved on, and saving would rewrite its destination.
    if (ctx.state?.review) { ctx.state.review = ""; if (location.hash.includes("review=")) ctx.save?.(); }
    if (restoreFocus && target?.isConnected) target.focus({ preventScroll: true });
    refreshRows(issue.id);
  }
  function jump(id) {
    const scroller = dialog.querySelector(".trace-scroll"), section = dialog.querySelector(`#${id}`);
    scroller.scrollTo({ top: scroller.scrollTop + section.getBoundingClientRect().top - scroller.getBoundingClientRect().top - 22,
      behavior: matchMedia("(prefers-reduced-motion: reduce)").matches ? "instant" : "smooth" });
    if (id === "trace-your-review") section.querySelector("input")?.focus({ preventScroll: true });
  }
  function sampleSubjects() {
    const candidates = examples()?.subjects || [];
    const relevant = candidates.filter((s) => issue.impact.subjects.includes(s.id));
    return (relevant.length ? relevant : candidates).slice(0, 2);
  }
  function sampleView() {
    const data = examples(), choices = sampleSubjects();
    if (!choices.length) return `<p>${esc(data?.reason || "No row-aligned subject example is available for this finding.")}</p>`;
    const calculations = data.calculations.filter((p) => p.reading === "literal");
    if (calculations.length !== 1) return '<p class="trace-limit">A single documented-rule calculation is unavailable for this finding.</p>';
    if (!choices.some((s) => s.id === subject)) subject = choices[0].id;
    const chosen = choices.find((s) => s.id === subject),
      columns = [...data.keys.filter((k) => k !== data.subject_key), ...data.input_columns];
    const context = (row) => `<small class="trace-record-context">${columns.map((c) => `${esc(c)}: ${esc(display(Object.hasOwn(row.keys, c) ? row.keys[c] : row.inputs[c]))}`).join("; ")}</small>`;
    return `<div class="trace-subject-tabs" role="tablist" aria-label="Example subjects">${choices.map((s, i) => `<button type="button" role="tab" id="trace-subject-${i}" aria-controls="trace-subject-panel" aria-selected="${s.id === subject}" tabindex="${s.id === subject ? 0 : -1}" data-trace-subject="${esc(s.id)}">${esc(s.id)}</button>`).join("")}</div><div id="trace-subject-panel" role="tabpanel" aria-labelledby="trace-subject-${choices.indexOf(chosen)}"><p class="trace-scope"><strong>${esc(chosen.id)}</strong>: ${chosen.rows.length} of ${chosen.total_rows} subject records shown${chosen.rows.length < chosen.total_rows ? "; the example is abbreviated" : ""}.</p><div class="trace-data-scroll" role="region" aria-label="Subject example calculations" tabindex="0"><table class="trace-data-table"><caption>${esc(issue.dataset + "." + issue.variable)}</caption><thead><tr><th scope="col">ADaM data</th><th scope="col">Documented Rule</th></tr></thead><tbody>${chosen.rows.map((r) => `<tr>${subjectDifferenceCells(r, calculations, context(r))}</tr>`).join("")}</tbody></table></div><p class="trace-scope">Highlighted cells differ between ADaM data and the Define-XML rule as written. Missing values, blank text, absent variables and absent records remain distinct.</p></div>`;
  }
  function reviewForm() {
    const draft = currentDraft(), target = destination();
    function options(name, entries) {
      return `<div class="trace-review-choices">${Object.entries(entries).map(([value, text]) => `<label><input type="radio" name="${name}" value="${value}" ${draft[name] === value ? "checked" : ""}> ${text}</label>`).join("")}</div>`;
    }
    return `<form id="trace-your-review" class="trace-human-review" novalidate><header><h3>Human Review</h3></header><div class="trace-form-body">${draft.stale ? '<p class="trace-limit" role="status">The evidence changed since your previous assessment. Your choices are retained as a draft; review the current evidence before sharing.</p>' : ""}<fieldset><legend>Do you agree with this finding? <small>Required</small></legend>${options("agreement", AGREEMENTS)}</fieldset><fieldset><legend>Is this finding critical? <small>Required</small></legend>${options("criticality", CRITICALITIES)}<p class="trace-scope">Working definition: a critical issue could materially affect analysis results or their interpretation.</p></fieldset><fieldset><legend>Which source is right? <small>Optional</small></legend>${options("side", SIDES)}</fieldset><label class="trace-comment-label" for="trace-review-comment">Comments <small>Optional</small></label><textarea id="trace-review-comment" name="comment" rows="4" maxlength="10000" placeholder="Explain your assessment, suggest a correction, or note missing evidence.">${esc(draft.comment)}</textarea><p class="trace-review-feedback" role="status" aria-live="polite" hidden></p><div class="trace-review-actions"><p class="trace-storage-note">Drafts save automatically in this browser. ${target ? "Submitting opens GitHub with your review filled in; select Start discussion there to publish." : "Copy your assessment to share on GitHub."}</p><div><button class="button primary" type="submit">${target ? "Submit review on GitHub" : "Copy review"}</button></div></div><div data-trace-prepared hidden><label for="trace-github-comment">Review text to copy</label><textarea id="trace-github-comment" rows="7" readonly></textarea><p data-trace-comment-stale class="trace-limit" role="status" hidden>Your assessment changed. Submit or copy the review again before posting.</p></div></div></form>`;
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
    if (!save()) return;
    const prepared = dialog.querySelector("[data-trace-prepared]"),
      textarea = dialog.querySelector("#trace-github-comment");
    prepared.hidden = false; textarea.value = text;
    dialog.querySelector("[data-trace-comment-stale]").hidden = true;
    let copied = false;
    try { await navigator.clipboard.writeText(text); copied = true; }
    catch { /* The visible, selectable text remains available without clipboard access. */ }
    if (dialog !== active || issue.id !== id) return;
    feedback(copied
      ? "Review copied. Paste it into a GitHub discussion or the dataset's Comments box to publish."
      : "Clipboard access is unavailable. Copy the review text below to share on GitHub.");
    if (!copied) { textarea.focus({ preventScroll: true }); textarea.select(); }
    markShared("clipboard");
  }
  function submitOnGitHub() {
    let prepared;
    try { prepared = reviewDiscussion(ctx.index.comments, ctx.model, issue, currentDraft(), location.href); }
    catch (error) {
      feedback(error.message, true);
      dialog.querySelector(`input[name="${currentDraft().agreement ? "criticality" : "agreement"}"]`)?.focus({ preventScroll: true });
      return;
    }
    if (!save()) return;
    // Opened synchronously inside the submit event, so browsers treat the tab as user-initiated.
    const tab = window.open(prepared.url, "_blank");
    if (tab) tab.opener = null;
    dialog.querySelector("#trace-github-comment").value = prepared.body;
    dialog.querySelector("[data-trace-prepared]").hidden = false;
    dialog.querySelector("[data-trace-comment-stale]").hidden = true;
    markShared("github");
    const again = link(prepared.url, tab ? "Open GitHub again" : "Open GitHub");
    if (!prepared.prefilled) {
      navigator.clipboard?.writeText(prepared.body).catch(() => { /* The prepared text stays selectable below. */ });
      feedback(`Your review is longer than a prefilled link allows, so the composer holds the title only. Paste the prepared text below into the discussion on GitHub, then select Start discussion. ${again}`, false, true);
    } else if (tab) feedback(`GitHub opened in a new tab with your review filled in. Sign in if asked, then select Start discussion to publish. ${again}`, false, true);
    else feedback(`Your browser blocked the new tab. ${again} with your review filled in, sign in if asked, then select Start discussion to publish.`, false, true);
  }
  function updateStatus() {
    const advance = dialog.querySelector("[data-trace-next-unreviewed]");
    if (advance) { advance.disabled = !next(); advance.title = next() ? "Continue through the whole study" : "No other unreviewed findings"; }
    for (const button of dialog.querySelectorAll("[data-trace-sibling]")) {
      const other = findIssue(ctx.report, button.dataset.traceSibling);
      button.querySelector("small").textContent = draftLabel(drafts.load(ctx.model.id, other, ctx.report));
    }
    const note = dialog.querySelector(".trace-storage-note");
    if (note && !drafts.available) note.textContent = "Browser storage is unavailable. Your draft lasts for this session. Submit or copy your review to share it on GitHub.";
    refreshRows(issue.id);
  }
  function feedback(message, error = false, html = false) {
    const element = dialog.querySelector(".trace-review-feedback");
    if (html) element.innerHTML = message; else element.textContent = message;
    element.hidden = false;
    element.classList.toggle("trace-error", error);
  }
  /** Record how a complete assessment left this browser; later edits return it to a draft. */
  function markShared(shared) {
    const values = Object.fromEntries(new FormData(dialog.querySelector("form")));
    try { drafts.save(ctx.model.id, issue, ctx.report, { ...values, shared }, true); updateStatus(); }
    catch { /* An incomplete assessment stays a draft. */ }
  }
  function save() {
    const form = dialog.querySelector("form"), values = Object.fromEntries(new FormData(form));
    try {
      // Both decisions chosen is a complete assessment, saved locally until it is shared.
      drafts.save(ctx.model.id, issue, ctx.report, values,
        Object.hasOwn(AGREEMENTS, values.agreement) && Object.hasOwn(CRITICALITIES, values.criticality));
      updateStatus();
      return true;
    } catch (error) {
      feedback(error.message, true);
      form.querySelector(`input[name="${values.agreement ? "criticality" : "agreement"}"]`)?.focus({ preventScroll: true });
      return false;
    }
  }
  function render() {
    const group = siblings(), at = group.indexOf(issue);
    // The footer walks the findings the listing shows when this one is among them, else its variable's findings.
    const listed = ctx.listed?.() || [], inList = listed.some((i) => i.id === issue.id),
      walk = inList ? listed : group, pos = walk.findIndex((i) => i.id === issue.id),
      step = (n, text) => n >= 0 && n < walk.length ? `<button class="button" data-trace-sibling="${esc(walk[n].id)}" aria-label="${text}${inList ? " in list" : ""}"><span aria-hidden="true">${n < pos ? "&larr;" : "&rarr;"}</span><span class="sibling-label">${text}${inList ? " in list" : ""}</span><small hidden></small></button>` : "";
    if (ctx.state && ctx.state.review !== issue.id) { ctx.state.review = issue.id; ctx.save?.(); }
    dialog.dataset.reviewDataset = issue.dataset;
    dialog.innerHTML = `<div class="trace-review-shell"><header class="trace-review-header"><div><p>${esc(ctx.model.title)} / ${esc(issue.dataset)} / Finding review</p><h2>${esc(issue.dataset + (issue.variable ? "." + issue.variable : ""))}</h2></div><div><button class="button" data-trace-close aria-label="Close review">Close</button></div></header><div class="trace-review-layout"><section class="trace-review-nav" aria-label="Review navigation"><h3>Findings for this variable</h3><nav aria-label="Choose a finding">${group.map((i, n) => `<button data-trace-sibling="${esc(i.id)}" ${i.id === issue.id ? 'aria-current="page"' : ""}><span>${String(n + 1).padStart(2, "0")}</span><span>${esc(i.title)}<small></small></span></button>`).join("")}</nav><h3>On this page</h3><nav aria-label="Evidence sections">${[["trace-finding", "The finding"], ["trace-sources", "Define-XML vs. reproduced yamaa specification from ADaM data"], ["trace-examples", "Subject examples"], ["trace-your-review", "Human Review"]].map(([id, text]) => `<button data-trace-section="${id}">${text}</button>`).join("")}</nav></section><div class="trace-scroll"><div class="trace-review-content"><section id="trace-finding"><p class="eyebrow">${group.length > 1 ? `Finding ${at + 1} of ${group.length} for this variable ` : ""}<span class="status neutral">${esc(issue.kind.replaceAll("_", " "))}</span></p><h2 id="trace-review-title" tabindex="-1">${esc(issue.title)}</h2>${issueTrace(issue, ctx.report, { summaryOnly: true })}${issue.expected || issue.observed ? `<dl class="issue-comparison">${issue.expected ? `<dt>Expected behavior</dt><dd>${esc(issue.expected)}</dd>` : ""}${issue.observed ? `<dt>Observed behavior</dt><dd>${esc(issue.observed)}</dd>` : ""}</dl>` : ""}</section><section id="trace-sources"><h3>Define-XML vs. reproduced yamaa specification from ADaM data</h3>${reviewComparison(issue, ctx.report, ctx.specifications)}</section><section id="trace-examples"><h3>Subject examples</h3><div data-trace-samples>${sampleView()}</div></section>${reviewForm()}</div></div></div><footer class="trace-review-footer"><div><small>${inList ? `Finding ${pos + 1} of ${walk.length} in the current list` : "Share your assessment on GitHub"}</small></div><div>${step(pos - 1, "Previous finding")}${step(pos + 1, "Next finding")}<button class="button" data-trace-next-unreviewed>Next not reviewed</button><a class="text-link" href="#trace-your-review" data-trace-section="trace-your-review">Go to Human Review</a></div></footer></div>`;
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
      const target = event.target.closest("button, a[data-trace-section]");
      if (!target) return;
      if (target.hasAttribute("data-trace-close")) close();
      else if (target.dataset.traceSibling) { issue = findIssue(ctx.report, target.dataset.traceSibling); render(); dialog.querySelector("h2[tabindex]").focus({ preventScroll: true }); }
      else if (target.hasAttribute("data-trace-next-unreviewed")) { const found = next(); if (found) { issue = found; render(); dialog.querySelector("h2[tabindex]").focus({ preventScroll: true }); } }
      else if (target.dataset.traceSection) { event.preventDefault(); jump(target.dataset.traceSection); }
      else if (target.dataset.traceSubject) { subject = target.dataset.traceSubject; dialog.querySelector("[data-trace-samples]").innerHTML = sampleView(); jump("trace-examples"); dialog.querySelector('[aria-selected="true"]')?.focus({ preventScroll: true }); }
    });
    dialog.addEventListener("keydown", (event) => {
      if (!event.target.matches("[data-trace-subject]") || !["ArrowLeft", "ArrowRight", "Home", "End"].includes(event.key)) return;
      event.preventDefault();
      const tabs = [...dialog.querySelectorAll("[data-trace-subject]")], at = tabs.indexOf(event.target),
        next = event.key === "Home" ? 0 : event.key === "End" ? tabs.length - 1 : (at + (event.key === "ArrowRight" ? 1 : -1) + tabs.length) % tabs.length;
      tabs[next].click();
    });
    dialog.addEventListener("input", (event) => { if (event.target.closest("form")) { save(); dialog.querySelector(".trace-review-feedback").hidden = true; const prepared = dialog.querySelector("[data-trace-prepared]"); if (!prepared.hidden) dialog.querySelector("[data-trace-comment-stale]").hidden = false; } });
    dialog.addEventListener("submit", (event) => {
      event.preventDefault();
      if (destination()) submitOnGitHub(); else void copyForGitHub();
    });
    dialog.showModal(); dialog.querySelector("[data-trace-close]").focus({ preventScroll: true });
  }
  return { open, close, refreshRows, get isOpen() { return Boolean(dialog); } };
}
