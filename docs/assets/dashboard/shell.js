import { metric } from "./ui.js";

/** Components read the live application context at render time. */
export function createShell(ctx) {
  function metrics() {
    const { model, report } = ctx;
    const m = model.metrics;
    return `<div class="metric-strip">${["Datasets", "Columns", "Cells"].map((n, i) => `<span><strong>${n}</strong> ${metric(m.matched[i])} / ${metric(m.reference[i])} <small>${m.reference[i] ? Math.round((100 * m.matched[i]) / m.reference[i]) + "%" : "n/a"}</small></span>`).join("")}<button data-view="findings"><strong>Documentation review</strong> ${report.findings.length} observations / tasks</button></div>`;
  }
  function frame() {
    const { model, state, site, REPO, esc, link } = ctx;
    return `<header class="review-hero"><div><p class="eyebrow">PILOT 7 / SDTM &#8594; ADaM</p><div class="study-title-row"><h1>${esc(model.title)}</h1><div class="hero-actions"><a class="button" href="${new URL("studies/", site).href}">All pilot studies</a>${link(`${REPO}/tree/${model.revision}/${model.id}`, "Study source", "button")}</div></div><p>Review SDTM to ADaM derivations against the published submission package.</p></div></header>${metrics()}<nav class="review-tabs" aria-label="Study sections">${[
      ["datasets", "Review workspace"],
      ["overview", "Dataset overview"],
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
