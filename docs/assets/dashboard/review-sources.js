/** Presentation of retained evidence; original checks and review identities stay intact. */
import { esc, link } from "./ui.js";
import { citation } from "./issues.js";

/** Only the cited Define-XML item and the selected variable's executable YAML. */
export function reviewComparisonEvidence(issue, report, specifications = {}) {
  const ids = new Set(issue.trace.map((t) => t.evidence_id));
  const documents = report.review.evidence.filter((e) => ids.has(e.id) &&
    e.type === "document" && /(?:^|\/)define(?:-adam)?\.xml$/i.test(e.path));
  const specification = Object.values(specifications).find((s) => s.domain === issue.dataset);
  const resolved = specification?.resolved, span = resolved?.lineage?.spans?.[issue.variable];
  if (!span) return documents;
  const context = resolved.text.split(/\r?\n/).slice(span.start - 1, span.end).join("\n");
  return [...documents, { id: `resolved:${issue.dataset}.${issue.variable}`, type: "specification",
    path: resolved.path, section: issue.variable, quote: context, context,
    lines: [span.start, span.end], context_lines: [span.start, span.end], verified: true, url: "" }];
}

export function reviewComparison(issue, report, specifications) {
  const evidence = reviewComparisonEvidence(issue, report, specifications);
  return `<div class="trace-source-grid" aria-label="Define-XML and resolved YAML comparison">${[
    ["document", "Define-XML", "The identified Define-XML item is unavailable for this finding."],
    ["specification", "Resolved YAML", "The resolved YAML item is unavailable for this finding."],
  ].map(([type, label, missing]) => {
    const entries = evidence.filter((e) => e.type === type);
    return `<section class="trace-source-file" aria-label="${label}"><p class="trace-scope">${label}${entries.length ? `: ${esc(entries[0].path)}` : ""}</p>${entries.length ? entries.map((e) => citation(e, true, type === "specification")).join("") : `<p class="trace-limit">${missing}</p>`}</section>`;
  }).join("")}</div>`;
}

export function resolvedReviewReport(report, specifications = {}, dataset = "") {
  return { ...report, review: { ...report.review, evidence: report.review.evidence.map((e) => {
    if (e.type !== "specification") return e;
    const specification = Object.values(specifications).filter((s) => !dataset || s.domain === dataset).find((s) =>
      s.path === e.path || s.documents?.some((d) => d.path === e.path));
    const resolved = specification?.resolved, span = resolved?.lineage?.spans?.[e.section];
    if (!span) return e; // Independent document-based translations keep their own YAML.
    const context = resolved.text.split(/\r?\n/).slice(span.start - 1, span.end).join("\n");
    return { ...e, path: resolved.path, context, quote: context,
      lines: [span.start, span.end], context_lines: [span.start, span.end], url: "" };
  }) } };
}

export function sourcePreview(e, report, specifications, resource) {
  const doc = report.documents?.find((d) => d.path === e.path && d.available);
  if (doc && (doc.view || doc.original)) {
    const pdf = /\.pdf$/i.test(doc.name);
    const fragment = pdf && /^page-\d+$/.test(e.section)
      ? "#page=" + e.section.slice(5) : e.section ? "#" + encodeURIComponent(e.section) : "";
    const theme = /\.xlsx$/i.test(doc.name)
      ? "?theme=" + encodeURIComponent(document.body.dataset.mdColorScheme || "default") : "";
    return `<iframe title="${esc(doc.name)}" src="${esc(resource(doc.view || doc.original) + theme + fragment)}"${pdf ? "" : ' sandbox="allow-scripts"'}></iframe>`;
  }
  const sources = Object.values(specifications).flatMap((s) => [s, s.resolved, ...(s.documents || [])]).filter(Boolean);
  const source = sources.find((s) => s.path === e.path);
  const first = source ? 1 : e.context_lines?.[0] || e.lines?.[0] || 1;
  const text = source?.text ?? e.context ?? e.quote;
  return `${source ? "" : '<p class="trace-limit">Only the retained citation context is available for this file.</p>'}<pre class="spec-lines" tabindex="0"><code>${String(text || "").split(/\r?\n/).map((line, i) => {
    const n = first + i, tag = e.lines && n >= e.lines[0] && n <= e.lines[1] ? "mark" : "span";
    return `<${tag} class="context-line"><span class="context-line-number" aria-hidden="true">${n}</span><span class="context-line-text">${esc(line) || " "}</span></${tag}>`;
  }).join("")}</code></pre>`;
}

export function createReviewSources(ctx) {
  let dialog, opener;
  function close(restoreFocus = true) {
    if (!dialog) return;
    dialog.close(); dialog.remove(); dialog = null;
    if (restoreFocus && opener?.isConnected) opener.focus({ preventScroll: true });
  }
  function open(e, trigger) {
    close(false); opener = trigger;
    dialog = document.createElement("dialog");
    dialog.className = "review-source-dialog";
    dialog.setAttribute("aria-labelledby", "review-source-title");
    dialog.innerHTML = `<header><h2 id="review-source-title">${esc(e.path)}</h2><button class="button" data-source-close>Close source</button></header><div class="review-source-content">${sourcePreview(e, ctx.report, ctx.specifications, ctx.resource)}</div>${e.url || ctx.sourceUrl ? `<footer>${link(e.url || ctx.sourceUrl(e.path, e.lines?.[0]), "Open repository source")}</footer>` : ""}`;
    ctx.root().append(dialog);
    dialog.addEventListener("cancel", (event) => { event.preventDefault(); close(); });
    dialog.querySelector("[data-source-close]").addEventListener("click", () => close());
    dialog.showModal();
    dialog.querySelector("mark")?.scrollIntoView({ block: "center" });
    dialog.querySelector("button").focus({ preventScroll: true });
  }
  return { open, close };
}
