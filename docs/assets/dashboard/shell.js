import { metric } from "./ui.js";
import { consistencyFindings } from "./report.js";

/** Components read the live application context at render time. */
export function createShell(ctx) {
  function metrics() {
    const { model, report } = ctx;
    if (model.kind === "synthetic")
      return `<div class="metric-strip"><span><strong>Subjects:</strong> ${metric(model.subjects.length)}</span><span><strong>ADaM datasets:</strong> ${model.datasets.length}</span><span>No independent published reference</span><span>Human analysis review pending</span></div>`;
    const m = model.metrics;
    return `<div class="metric-strip">${["Datasets", "Columns", "Cells"].map((n, i) => `<span><strong>${n}</strong> ${metric(m.matched[i])} / ${metric(m.reference[i])} <small>${m.reference[i] ? Math.round((100 * m.matched[i]) / m.reference[i]) + "%" : "n/a"}</small></span>`).join("")}<span><strong>Consistency:</strong> ${consistencyFindings(report).length} issue${consistencyFindings(report).length === 1 ? "" : "s"}</span></div>`;
  }
  function frame() {
    const { model, state, site, REPO, esc, link } = ctx;
    const synthetic = model.kind === "synthetic";
    return `<header class="review-hero"><div><p class="eyebrow">PILOT 7 / SDTM &#8594; ADaM</p><div class="study-title-row"><h1>${esc(model.title)}</h1><div class="hero-actions"><a class="button" href="${new URL(synthetic ? "synthetic/" : "studies/", site).href}">${synthetic ? "All synthetic studies" : "All pilot studies"}</a>${link(`${REPO}/tree/${model.revision}/${model.id}`, "Study source", "button")}</div></div><p>${synthetic ? "Review synthetic SDTM inputs, ADaM derivations and pending analysis decisions." : "Review SDTM to ADaM derivations against the published submission package."}</p></div></header>${metrics()}<nav class="review-tabs" aria-label="Study sections">${[
      ["datasets", "SDTM -&gt; ADaM"],
      ...(model.development ? [["development", "Analysis development"]] : []),
      ["overview", "Consistency findings"],
      ["materials", "Source documents"],
    ]
      .map(
        ([id, label]) =>
          `<button data-view="${id}" class="${state.view === id ? "active" : ""}" ${state.view === id ? 'aria-current="page"' : ""}>${label}</button>`,
      )
      .join(
        "",
      )}</nav><div id="view-content"></div><div class="review-footnote">Build success, reference agreement, and documentation consistency are separate checks. ${link(new URL("verification/", site).href, "Verification policy")}</div><section id="review-comments" class="review-comments" aria-label="Review comments"></section>`;
  }

  return { metrics, frame };
}
