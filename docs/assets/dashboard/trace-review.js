/** Expanded, source-backed evidence and an independent human review per issue. */
import { esc, link } from "./ui.js";
import { reviewComment } from "./review-comment.js";
import { reviewDestination, reviewDiscussion } from "./review-submit.js";
import { comparisonLabel, criticalFinding, CRITICAL_LABELS, findIssue, issueTrace, readReview } from "./issues.js";
import { AGREEMENTS, CRITICALITIES, SIDES, createReviewDrafts, draftLabel } from "./review-drafts.js";
import { resolvedReviewReport } from "./review-sources.js";

const plural = (n, word) => `${n} ${word}${n === 1 ? "" : "s"}`;
const display = (value) => value == null ? "(missing)" : value === "" ? "(blank)" : String(value);
const cell = (item) => esc(!item?.present ? "(no record)" : item.column_present === false ? "(variable absent)" : display(item.value));

// Compare record presence, variable presence and typed values independently.
const sameCell = (a, b) => Boolean(a?.present) === Boolean(b?.present) &&
  (!a?.present || (a.column_present !== false) === (b.column_present !== false) &&
    (a.column_present === false || Object.is(a.value, b.value)));

export function subjectDifferenceCells(row, calculations) {
  const differs = calculations.map((p) => !sameCell(row.reference, row.calculations[p.column]));
  const render = (item, different) => `<td${different ? ' class="trace-cell-difference" title="Differs from the compared value"' : ""}>${different ? '<span class="sr-only">Difference: </span>' : ""}${cell(item)}</td>`;
  return render(row.reference, differs.some(Boolean)) + calculations.map((p, i) => render(row.calculations[p.column], differs[i])).join("");
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
  const examples = () => ctx.report.trace_examples?.[`${issue.dataset}.${issue.variable}`];

  function refreshRows(onlyId = "") {
    for (const element of ctx.root()?.querySelectorAll("[data-human-review]") || []) {
      if (onlyId && element.dataset.humanReview !== onlyId) continue;
      const item = findIssue(ctx.report, element.dataset.humanReview);
      if (!item) continue;
      const draft = drafts.load(ctx.model.id, item, ctx.report);
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
  function measures() {
    const pool = new Map(readReview(ctx.report).evidence.map((e) => [e.id, e]));
    return issue.trace.map((t) => ({ ...pool.get(t.evidence_id), role: t.role }))
      .filter((e) => ["comparison", "codelist", "note"].includes(e.type));
  }
  /** The automated assessments a reviewer weighs before deciding. */
  function reviewBasis() {
    const checks = readReview(ctx.report).checks.filter((c) => issue.check_ids.includes(c.id)),
      critical = criticalFinding(issue),
      reasons = [...new Set(checks.map((c) => c.review?.reason).filter(Boolean))],
      notes = measures().filter((e) => e.type === "note"),
      status = issue.review.replaceAll("_", " ");
    const agent = issue.review === "not_reviewed"
      ? "No agent adjudication: this is an authored question."
      : `<strong>Agent review: ${esc(status)}.</strong> ${reasons.length ? esc(reasons.join(" ")) : "The adjudicator recorded no reason."}${issue.review === "stale" ? " The decision predates the current evidence; weigh it accordingly." : ""}`;
    return `<div class="trace-basis" aria-label="Review basis"><p><strong>Automated criticality: ${esc(CRITICAL_LABELS[critical.status])}.</strong> ${esc(critical.reason)}</p><p>${agent}</p>${notes.map((n) => `<p class="trace-limit"><strong>${esc(n.title)}:</strong> ${esc(n.text)}</p>`).join("")}</div>`;
  }
  /** What the measured counts compare: the documented rule as written, not the dataset, which the reference comparison covers. */
  function agreement() {
    const dataset = ctx.model?.datasets?.find((d) => d.name === issue.dataset);
    if (!dataset) return "";
    return dataset.comparison === "passed"
      ? `The yamaa output for ${esc(issue.dataset)} matches the published reference (reference comparison passed), so these counts show where the documented rule, run as written, and the data disagree, not a wrong dataset. `
      : `The ${esc(issue.dataset)} reference comparison is ${esc(String(dataset.comparison || "unavailable"))}; these counts compare the documented rule, run as written, with the data. `;
  }
  function measurements() {
    const referenceMatches = ctx.model?.datasets?.find((d) => d.name === issue.dataset)?.comparison === "passed";
    // A passed reference comparison makes the output comparison redundant here.
    const measured = measures().filter((e) => e.type !== "note" && !(referenceMatches && e.target === "derived"));
    if (!measured.length && measures().some((e) => e.type !== "note")) return `<p class="trace-scope">${agreement()}</p>`;
    if (!measured.length) return '<p class="trace-scope">No issue-specific data comparison: this finding compares source statements or specification text, so its effect on the data was not measured. Decide criticality from the rule itself and from the examples below.</p>';
    return `<div class="trace-measurements">${measured.map((e) => `<article class="trace-measurement"><h4>${esc(comparisonLabel(e))}</h4>${e.type === "comparison"
      ? `<p><strong>${e.differ.toLocaleString()} / ${e.compared.toLocaleString()}</strong> records differ</p><small>${plural(e.subjects.length, "subject")} with differences</small>`
      : `<p>${plural(e.values.length, "value")} outside the documented codelist</p>`}<p class="trace-scope">${e.role === "context" ? "Context only; excluded from this issue's impact." : "Issue-specific measurement."}</p></article>`).join("")}</div><p class="trace-scope">${agreement()}Differences compare calculations with their stated target; they do not establish that the reference is wrong. Each comparison has its own denominator. Zero differences does not prove equivalent rules.</p>`;
  }
  function sampleSubjects() {
    const candidates = examples()?.subjects || [];
    const relevant = candidates.filter((s) => issue.impact.subjects.includes(s.id));
    return (relevant.length ? relevant : candidates).slice(0, 2);
  }
  function sampleView() {
    const data = examples(), choices = sampleSubjects();
    if (!choices.length) return `<p>${esc(data?.reason || "No row-aligned subject example is available for this finding. The source comparisons remain available.")}</p>`;
    if (!choices.some((s) => s.id === subject)) subject = choices[0].id;
    const chosen = choices.find((s) => s.id === subject),
      columns = [...data.keys.filter((k) => k !== data.subject_key), ...data.input_columns],
      headings = data.calculations.map((p, i) => p.reading === "literal" ? "Documented rule as written" : `Alternative interpretation ${i}`);
    const compared = measures().filter((e) => e.type === "comparison"),
      allMatch = compared.length > 0 && compared.every((e) => !e.differ);
    return `<div class="trace-subject-tabs" role="tablist" aria-label="Reference subjects">${choices.map((s, i) => `<button type="button" role="tab" id="trace-subject-${i}" aria-controls="trace-subject-panel" aria-selected="${s.id === subject}" tabindex="${s.id === subject ? 0 : -1}" data-trace-subject="${esc(s.id)}">${esc(s.id)}</button>`).join("")}</div><div id="trace-subject-panel" role="tabpanel" aria-labelledby="trace-subject-${choices.indexOf(chosen)}"><p class="trace-scope">Current reference data and document-based derivations for <strong>${esc(chosen.id)}</strong>. ${chosen.rows.length} of ${chosen.total_rows} subject records shown${chosen.rows.length < chosen.total_rows ? "; informative records retained; the example is abbreviated" : ""}.</p><div class="trace-data-scroll" role="region" aria-label="Subject example calculations" tabindex="0"><table class="trace-data-table"><thead><tr>${columns.map((c) => `<th scope="col">${esc(c)}</th>`).join("")}<th scope="col">Current data: ${esc(issue.variable)} (reference)</th>${headings.map((h) => `<th scope="col">${esc(h)}</th>`).join("")}</tr></thead><tbody>${chosen.rows.map((r) => `<tr>${columns.map((c) => `<td>${esc(display(Object.hasOwn(r.keys, c) ? r.keys[c] : r.inputs[c]))}</td>`).join("")}${subjectDifferenceCells(r, data.calculations)}</tr>`).join("")}</tbody></table></div><p class="trace-scope">Highlighted cells differ between current reference data and a document-based derivation. Missing, blank and absent records remain distinct.</p><div class="trace-reading-notes">${data.calculations.map((p, i) => `<p><strong>${esc(headings[i])}:</strong> ${esc(p.reading === "literal" ? "Applies the documented condition exactly as written." : p.reading)}</p>`).join("")}</div></div><p class="trace-scope">${esc(data.scope)} Examples illustrate this variable's calculations; only the issue-specific measurements above determine its reported impact.</p>${allMatch ? '<p class="trace-limit">No differences were observed in the retained comparisons. These examples illustrate the rules; they do not demonstrate a failure.</p>' : ""}`;
  }
  function reviewForm() {
    const draft = currentDraft(), target = destination();
    function options(name, entries) {
      return `<div class="trace-review-choices">${Object.entries(entries).map(([value, text]) => `<label><input type="radio" name="${name}" value="${value}" ${draft[name] === value ? "checked" : ""}> ${text}</label>`).join("")}</div>`;
    }
    return `<form id="trace-your-review" class="trace-human-review" novalidate><header><h3>Your review</h3><p>Agreement and criticality are separate decisions. Your assessment does not resolve or change the published finding.</p></header><div class="trace-form-body">${draft.stale ? '<p class="trace-limit" role="status">The evidence changed since your previous assessment. Your choices are retained as a draft; review the current evidence before sharing.</p>' : ""}<fieldset><legend>Do you agree with this finding? <small>Required</small></legend>${options("agreement", AGREEMENTS)}</fieldset><fieldset><legend>Is this finding critical? <small>Required</small></legend>${options("criticality", CRITICALITIES)}<p class="trace-scope">Working definition: a critical issue could materially affect analysis results or their interpretation.</p></fieldset><fieldset><legend>Which side is right? <small>Optional</small></legend>${options("side", SIDES)}<p class="trace-scope">Answers the open question for this variable when the finding sets a document against the specification.</p></fieldset><label class="trace-comment-label" for="trace-review-comment">Review comments <small>Optional</small></label><textarea id="trace-review-comment" name="comment" rows="4" maxlength="10000" placeholder="Explain your assessment, suggest a correction, or note missing evidence.">${esc(draft.comment)}</textarea><p class="trace-review-feedback" role="status" aria-live="polite" hidden></p><div class="trace-review-actions"><p class="trace-storage-note">Drafts save automatically in this browser. ${target ? "Submitting opens GitHub with your review filled in; select Start discussion there to publish." : "Copy your assessment to share on GitHub."}</p><div><button class="button primary" type="submit">${target ? "Submit review on GitHub" : "Copy review"}</button>${target ? '<button class="button" type="button" data-trace-copy-comment>Copy review instead</button>' : ""}</div></div><div data-trace-prepared hidden><label for="trace-github-comment">Review text to copy</label><textarea id="trace-github-comment" rows="7" readonly></textarea><p data-trace-comment-stale class="trace-limit" role="status" hidden>Your assessment changed. Submit or copy the review again before posting.</p></div></div></form>`;
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
      ? "Review copied. Paste it into a GitHub discussion or the dataset's Review comments box to publish."
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
    // A claim-level question is shared by every finding of its variable; say so instead of presenting it as this finding's fix.
    const sharedAction = Boolean(issue.action) && group.filter((i) => i.action === issue.action).length > 1,
      fixHeading = sharedAction ? "Open question for this variable" : "Recommended fix",
      fixScope = sharedAction ? `<p class="trace-scope">This question applies to all ${group.filter((i) => i.action === issue.action).length} findings for ${esc(issue.dataset + (issue.variable ? "." + issue.variable : ""))}. Decide this finding on the evidence above.</p>` : "";
    // The footer walks the findings the listing shows when this one is among them, else its variable's findings.
    const listed = ctx.listed?.() || [], inList = listed.some((i) => i.id === issue.id),
      walk = inList ? listed : group, pos = walk.findIndex((i) => i.id === issue.id),
      step = (n, text) => n >= 0 && n < walk.length ? `<button class="button" data-trace-sibling="${esc(walk[n].id)}">${text}${inList ? " in list" : ""}<small hidden></small></button>` : "";
    if (ctx.state && ctx.state.review !== issue.id) { ctx.state.review = issue.id; ctx.save?.(); }
    dialog.dataset.reviewDataset = issue.dataset;
    dialog.innerHTML = `<div class="trace-review-shell"><header class="trace-review-header"><div><p>${esc(ctx.model.title)} / ${esc(issue.dataset)} / Start review</p><h2>${esc(issue.dataset + (issue.variable ? "." + issue.variable : ""))}</h2></div><div><button class="button" data-trace-close aria-label="Close review">Close</button></div></header><div class="trace-review-layout"><aside class="trace-review-nav"><h3>Findings for this variable</h3><nav aria-label="Choose a finding">${group.map((i, n) => `<button data-trace-sibling="${esc(i.id)}" ${i.id === issue.id ? 'aria-current="page"' : ""}><span>${String(n + 1).padStart(2, "0")}</span><span>${esc(i.title)}<small></small></span></button>`).join("")}</nav><h3>On this page</h3><nav aria-label="Evidence sections">${[["trace-finding", "The finding"], ["trace-sources", "Source documents"], ["trace-specifications", "YAML specification"], ["trace-examples", "Example Subject Difference"], ["trace-fix", fixHeading], ["trace-your-review", "Your review"]].map(([id, text]) => `<button data-trace-section="${id}">${text}</button>`).join("")}</nav></aside><div class="trace-scroll"><main class="trace-review-content"><section id="trace-finding"><p class="eyebrow">Finding ${at + 1} of ${group.length} <span class="status neutral">${esc(issue.kind.replaceAll("_", " "))}</span></p><h2 id="trace-review-title" tabindex="-1">${esc(issue.title)}</h2><p class="trace-introduction">${esc(issue.summary)}</p>${reviewBasis()}${measurements()}</section><section id="trace-sources"><h3>1. Source documents</h3><p class="trace-scope">Compare retained source-document statements side by side. Each quotation is the cited clause; View source opens the original document at the cited row or page. Missing comparison evidence is called out below.</p>${issueTrace(issue, ctx.report, { sourcesOnly: true })}</section><section id="trace-specifications"><h3>2. YAML specification</h3><p class="trace-scope">Compare the resolved YAML rules and document-based translations side by side. File names identify each specification; highlighted lines show the cited rule.</p>${issueTrace(issue, resolvedReviewReport(ctx.report, ctx.specifications, issue.dataset), { specificationsOnly: true })}</section><section id="trace-examples"><h3>3. Example Subject Difference</h3><div data-trace-samples>${sampleView()}</div></section><section id="trace-fix"><h3>4. ${fixHeading}</h3>${fixScope}<div class="trace-fix"><p>${esc(issue.action || "The retained evidence does not specify a correction. Confirm the intended rule before changing the specification or documents.")}</p></div></section>${reviewForm()}</main></div></div><footer class="trace-review-footer"><div><small>${inList ? `Finding ${pos + 1} of ${walk.length} in the current list` : "Share your assessment on GitHub"}</small></div><div>${step(pos - 1, "Previous finding")}${step(pos + 1, "Next finding")}<button class="button primary" data-trace-section="trace-your-review">Add your review</button></div></footer></div>`;
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
      else if (target.dataset.traceSibling) { issue = findIssue(ctx.report, target.dataset.traceSibling); render(); dialog.querySelector("h2[tabindex]").focus({ preventScroll: true }); }
      else if (target.dataset.traceSection) jump(target.dataset.traceSection);
      else if (target.dataset.traceSubject) { subject = target.dataset.traceSubject; dialog.querySelector("[data-trace-samples]").innerHTML = sampleView(); jump("trace-examples"); dialog.querySelector('[aria-selected="true"]')?.focus({ preventScroll: true }); }
      else if (target.hasAttribute("data-trace-copy-comment")) void copyForGitHub();
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
