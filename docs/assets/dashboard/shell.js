import { metric } from "./ui.js";
import { consistencyFindings } from "./report.js";
import { criticalFinding } from "./issues.js";
import { reviewLedger } from "./review-drafts.js";

export const COMPARISON_EXPLANATION = "Generated ADaM dataset agreement measures reproduction of the generated ADaM datasets under the study's comparison rules. Consistency review checks agreement among documents, derivation rules, and data. Findings can remain open even when generated ADaM dataset agreement is 100%.";

/** Components read the live application context at render time. */
export function createShell(ctx) {
  /** The reviewer's own progress over the whole study, kept in this browser. */
  function progress(issues) {
    if (!ctx.drafts) return "";
    const { counts } = reviewLedger(ctx.drafts, ctx.model.id, issues, ctx.report);
    return `<p class="your-progress">Your reviews: <strong>${counts.started} of ${counts.listed}</strong>${counts.reviewed ? ` (${counts.reviewed} with both decisions)` : ""}</p>`;
  }
  function metrics() {
    const { model, report } = ctx;
    if (model.kind === "synthetic")
      return `<div class="metric-strip"><span><strong>Subjects:</strong> ${metric(model.subjects.length)}</span><span><strong>ADaM datasets:</strong> ${model.datasets.length}</span><span>No independent generated ADaM comparison datasets</span><span>Human analysis review pending</span></div>`;
    const m = model.metrics, issues = consistencyFindings(report);
    const counts = { yes: 0, no: 0, needs_review: 0 };
    for (const issue of issues) counts[criticalFinding(issue).status]++;
    const status = m.reference[0]
      ? `<strong>${Math.round(100 * m.matched[0] / m.reference[0])}%</strong> of generated ADaM datasets matched`
      : "No generated ADaM comparison datasets";
    const labels = ["Datasets matching generated ADaM datasets", "Columns in matching datasets", "Cells in matching datasets"];
    return `<div class="review-summaries"><section class="summary-card reference-summary" aria-label="Generated ADaM dataset agreement"><h2>Generated ADaM dataset agreement</h2><p class="summary-value">${status}</p><dl class="summary-metrics">${labels.map((label, i) => `<div><dt>${label}</dt><dd>${metric(m.matched[i])} / ${metric(m.reference[i])}</dd></div>`).join("")}</dl></section><section class="summary-card consistency-summary" aria-label="Consistency review"><h2>Consistency review</h2><p class="summary-value"><strong>${issues.length}</strong> finding${issues.length === 1 ? "" : "s"} ${issues.length ? "awaiting review" : "reported"}</p><p class="critical-counts">${counts.yes} critical; ${counts.no} non-critical; ${counts.needs_review} needing assessment</p>${progress(issues)}<button class="text-link" data-view="overview">View consistency findings</button></section></div><p class="comparison-explanation">${COMPARISON_EXPLANATION}</p>`;
  }
  function frame() {
    const { model, state, site, REPO, esc, link } = ctx;
    const synthetic = model.kind === "synthetic";
    return `<header class="review-hero"><div><p class="eyebrow">PILOT 7 / SDTM &#8594; ADaM</p><div class="study-title-row"><h1>${esc(model.title)}</h1><div class="hero-actions"><a class="button" href="${new URL(synthetic ? "synthetic/" : "studies/", site).href}">${synthetic ? "All synthetic studies" : "All pilot studies"}</a>${link(`${REPO}/tree/${model.revision}/${model.id}`, "Study source", "button")}</div></div><p>${synthetic ? "Review synthetic SDTM inputs, ADaM derivations and pending analysis decisions." : "Review SDTM to ADaM derivations against the published submission package."}</p></div></header>${metrics()}<nav class="review-tabs" aria-label="Study sections">${[
      ["datasets", "SDTM -&gt; ADaM"],
      ...(model.development ? [["development", "Analysis development"]] : []),
      ["overview", "Consistency findings"],
      ...(model.define_comparison ? [["define", "Define-XML comparison"]] : []),
      ["materials", "Source documents"],
    ]
      .map(
        ([id, label]) =>
          `<button data-view="${id}" class="${state.view === id ? "active" : ""}" ${state.view === id ? 'aria-current="page"' : ""}>${label}</button>`,
      )
      .join(
        "",
      )}</nav><div id="view-content"></div><section id="review-comments" class="review-comments" aria-label="Review comments"></section>`;
  }

  return { metrics, frame };
}
