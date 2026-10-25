/** Original-document tabs with at most two independent viewers. */
export function documentSelection(documents, state) {
  if (!documents.length) return [];
  const requested = documents.findIndex((d) => d.path === state.document);
  const first =
    requested >= 0
      ? requested
      : Math.max(
          0,
          documents.findIndex((d) => d.available),
        );
  const second = documents.findIndex((d) => d.path === state.compareDocument);
  return second >= 0 && second !== first ? [first, second] : [first];
}

export function createSourceDocuments(ctx) {
  const selection = () => documentSelection(ctx.report.documents, ctx.state);
  function tabs(slot, chosen) {
    const { report, esc } = ctx;
    return `<div class="source-file-tabs" role="tablist" aria-label="Document ${slot + 1} files">${report.documents.map((doc, i) => `<button role="tab" id="source-tab-${slot}-${i}" aria-controls="source-panel-${slot}" aria-selected="${i === chosen[slot]}" tabindex="${i === chosen[slot] ? 0 : -1}" data-source-slot="${slot}" data-source-tab="${i}" ${chosen[1 - slot] === i ? 'disabled title="Already open in the other pane"' : ""}>${esc(doc.name)}</button>`).join("")}</div>`;
  }
  function pane(slot, chosen) {
    const { report, state, esc, resource, sourceUrl, link } = ctx;
    const doc = report.documents[chosen[slot]];
    const section = slot === 0 ? state.documentSection : "";
    const fragment = section
      ? doc.name.toLowerCase().endsWith(".pdf") && /^page-\d+$/.test(section)
        ? "#page=" + section.slice(5)
        : "#" + encodeURIComponent(section)
      : "";
    const frame = slot === 0 ? "source-frame" : "source-frame-compare";
    return `<article class="source-pane" data-source-path="${esc(doc.path)}">${tabs(slot, chosen)}<section class="source-viewer" id="source-panel-${slot}" role="tabpanel" aria-labelledby="source-tab-${slot}-${chosen[slot]}"><header class="source-viewer-heading"><h3>${esc(doc.name)}</h3>${doc.available ? link(sourceUrl(doc.path), "Source", "button") : ""}</header>${doc.available && (doc.view || doc.original) ? `<iframe id="${frame}" title="${esc((doc.view_label || "Original file") + ": " + doc.name)}" src="${esc(resource(doc.view || doc.original) + fragment)}" ${doc.name.toLowerCase().endsWith(".pdf") ? "" : 'sandbox="allow-scripts"'}></iframe>` : '<p class="empty-state">Source unavailable. This file is not retained in the package.</p>'}</section></article>`;
  }
  function materialsView() {
    const { report } = ctx;
    const chosen = selection();
    return `<div class="section-heading"><h2>Source documents</h2>${report.documents.length > 1 ? `<button class="button" id="compare-documents" aria-pressed="${chosen.length === 2}">${chosen.length === 2 ? "Close comparison" : "Compare side by side"}</button>` : ""}</div><div id="source-panes" class="source-panes" data-count="${chosen.length}">${chosen.length ? chosen.map((_, slot) => pane(slot, chosen)).join("") : '<p class="empty-state">No source documents have been declared for this study.</p>'}</div>`;
  }
  function refresh(slot) {
    const host = ctx.byId("source-panes");
    if (!host) return;
    const chosen = selection();
    host.dataset.count = chosen.length;
    while (host.children.length > chosen.length) host.lastElementChild.remove();
    chosen.forEach((index, position) => {
      let current = host.children[position];
      if (
        !current ||
        current.dataset.sourcePath !== ctx.report.documents[index].path
      ) {
        const template = document.createElement("template");
        template.innerHTML = pane(position, chosen);
        const replacement = template.content.firstElementChild;
        if (current) current.replaceWith(replacement);
        else host.append(replacement);
        current = replacement;
      } else {
        // Keep the frame and its current PDF page/scroll position intact.
        current.querySelector("[role=tablist]").outerHTML = tabs(
          position,
          chosen,
        );
      }
    });
    const button = ctx.byId("compare-documents");
    if (button) {
      button.textContent =
        chosen.length === 2 ? "Close comparison" : "Compare side by side";
      button.setAttribute("aria-pressed", String(chosen.length === 2));
    }
    if (slot !== undefined)
      ctx.byId(`source-tab-${slot}-${chosen[slot]}`)?.focus();
  }
  function choose(slot, index) {
    const chosen = selection();
    if (
      !ctx.report.documents[index] ||
      ![0, 1].includes(slot) ||
      slot >= chosen.length ||
      chosen[slot] === index ||
      chosen[1 - slot] === index
    )
      return;
    if (slot === 0) {
      ctx.state.document = ctx.report.documents[index].path;
      ctx.state.documentSection = "";
    } else ctx.state.compareDocument = ctx.report.documents[index].path;
    ctx.save();
    refresh(slot);
  }
  function click(target) {
    if (target.id === "compare-documents") {
      const chosen = selection();
      ctx.state.document = ctx.report.documents[chosen[0]].path;
      const next = ctx.report.documents.findIndex(
        (d, i) => i !== chosen[0] && d.available,
      );
      const fallback = ctx.report.documents.findIndex(
        (d, i) => i !== chosen[0],
      );
      ctx.state.compareDocument =
        chosen.length === 2
          ? ""
          : ctx.report.documents[next >= 0 ? next : fallback].path;
      ctx.save();
      refresh();
      return true;
    }
    if (!target.hasAttribute("data-source-tab")) return false;
    choose(Number(target.dataset.sourceSlot), Number(target.dataset.sourceTab));
    return true;
  }
  function keyboard(event) {
    const tab = event.target.closest("[data-source-tab]");
    if (!tab || !["ArrowLeft", "ArrowRight", "Home", "End"].includes(event.key))
      return false;
    event.preventDefault();
    const available = [
      ...tab.parentElement.querySelectorAll("[role=tab]:not(:disabled)"),
    ];
    const current = available.indexOf(tab);
    const next =
      event.key === "Home"
        ? 0
        : event.key === "End"
          ? available.length - 1
          : (current +
              (event.key === "ArrowRight" ? 1 : -1) +
              available.length) %
            available.length;
    choose(
      Number(tab.dataset.sourceSlot),
      Number(available[next].dataset.sourceTab),
    );
    return true;
  }
  return { materialsView, click, keyboard };
}
