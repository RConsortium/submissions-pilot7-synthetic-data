import { filterRows } from "./data.js";
import {
  PAGE_SIZES,
  inputOptions,
  domainName,
  domainLabel,
  canonicalNode,
  tableNode,
  columnIndexes,
} from "./review-model.js";

/** Shared specification and independently paged, resizable dataset panels. */
export function createWorkspace(ctx) {
  const observedSizes = new WeakMap();
  const sizes = new ResizeObserver((entries) => {
    let changed = false;
    for (const { target } of entries) {
      const size = target.clientWidth + ":" + target.style.height;
      if (observedSizes.get(target) !== size) changed = true;
      observedSizes.set(target, size);
    }
    if (changed) fitWorkbench();
  });
  function subjectPicker() {
    const { model, state, esc } = ctx;
    return `<details class="subject-picker" id="subject-picker" data-popover><summary id="subject-summary">Subjects <strong>${state.subjects.length} / ${model.subjects.length}</strong><span aria-hidden="true">&#9662;</span></summary><div class="subject-popover"><label class="field-label" for="subject-search">Find a subject</label><input id="subject-search" type="search" placeholder="Search ${esc(model.settings.subject_key)}..."><div class="subject-actions">${[...new Set([model.settings.default_subject_count, 10, 25, 50])].map((n) => `<button data-subject-count="${n}">First ${n}</button>`).join("")}<button data-subject-count="all">Select all</button><button data-subject-count="0">Clear</button><button data-close-subjects>Done</button></div><div class="subject-options">${model.subjects.map((s) => `<label data-subject-option="${esc(s)}"><input type="checkbox" data-subject="${esc(s)}" ${state.subjects.includes(s) ? "checked" : ""}>${esc(s)}</label>`).join("")}</div><p>Select any number of subjects. Subject-independent lookup rows stay visible.</p></div></details>`;
  }
  function datasetPicker(kind) {
    const { model, state, plan, esc } = ctx,
      inputs = kind === "input";
    const options = inputs ? inputOptions(model) : model.datasets;
    return `<details class="dataset-picker" id="${kind}-picker" data-popover><summary>Select domain (${inputs ? plan.inputs.length : plan.outputs.length})</summary><div class="dataset-popover"><p>${inputs ? "Linked domains open automatically. Select additional datasets to compare." : "Select additional output datasets. Click an output column to review its specification."}</p>${options
      .map((item) => {
        const id = inputs ? item.id : item.name,
          linked = inputs && plan.linked.includes(id),
          primary = !inputs && id === state.dataset;
        const checked = inputs
          ? plan.manual.includes(id) || linked
          : state.outputs.includes(id) || primary;
        const label = inputs
          ? domainLabel(item)
          : domainLabel({ ...model.tables[item.output], domain: item.name });
        return `<label><input type="checkbox" data-${kind}-dataset="${esc(id)}" ${checked ? "checked" : ""} ${linked || primary ? "disabled" : ""}><span>${esc(label)}${linked ? " <small>Linked</small>" : primary ? " <small>Current specification</small>" : ""}</span></label>`;
      })
      .join("")}</div></details>`;
  }
  function panelMarkup(panel, index) {
    const { model, state, layout, esc } = ctx,
      size = layout.panels[panel.key] || {};
    const title = domainLabel({ ...panel.meta, domain: panel.domain });
    const primary = index === 0,
      region = primary ? panel.kind + "-table" : "table-" + panel.key,
      footer = primary ? panel.kind + "-footer" : "footer-" + panel.key;
    const version =
      panel.kind === "output"
        ? state.output === "reference" && panel.dataset.reference
          ? "Official reference"
          : "yamaa derived"
        : panel.linked
          ? "Linked source"
          : "";
    return `<section class="pane dataset-panel ${panel.kind}-pane" data-panel="${panel.key}" data-domain="${esc(panel.domain)}" id="panel-${panel.key}" style="${size.width ? "width:" + size.width + "px;" : ""}${size.height ? "height:" + size.height + "px;" : ""}" aria-label="${esc(title)} ${panel.kind} dataset"><header class="pane-header"><div><h3>${esc(title)}</h3>${version ? `<span>${version}</span>` : ""}</div><div class="panel-size-buttons"><button data-panel-size="-80" data-panel-key="${panel.key}" aria-label="Narrow ${esc(panel.domain)} ${panel.kind} panel">&#8722;</button><button data-panel-size="80" data-panel-key="${panel.key}" aria-label="Widen ${esc(panel.domain)} ${panel.kind} panel">+</button></div></header><div id="${region}" class="data-region" data-table-for="${panel.key}"></div><footer id="${footer}" class="pane-footer" data-footer-for="${panel.key}"></footer></section>`;
  }
  function group(kind) {
    const { model, state, plan } = ctx,
      panels = kind === "input" ? plan.inputs : plan.outputs;
    return `<section class="dataset-group ${kind}-group" aria-label="${kind === "input" ? "Input" : "Output"} datasets"><header class="dataset-group-header"><h2>${kind === "input" ? "Input datasets" : "Output datasets"}</h2>${datasetPicker(kind)}${kind === "output" ? `<label class="output-version"><span class="sr-only">Output dataset type</span><select id="output-select"><option value="derived">yamaa derived</option>${plan.outputs.some((p) => p.dataset.reference) ? `<option value="reference" ${state.output === "reference" ? "selected" : ""}>Official reference</option>` : ""}</select></label>` : ""}</header><div class="panel-strip" data-panel-count="${panels.length}" style="--panel-count:${Math.max(1, Math.min(panels.length, 4))}">${panels.length ? panels.map(panelMarkup).join("") : '<p class="empty-state">Select input domains to display datasets here.</p>'}</div></section>`;
  }
  function workspace() {
    const { model, specification, state, layout, esc, sourceUrl, link } = ctx;
    return `<div class="workspace-toolbar"><label class="select-field">Specification<select id="dataset-select">${model.datasets.map((d) => `<option value="${d.name}" ${state.dataset === d.name ? "selected" : ""}>${d.name}</option>`).join("")}</select></label>${subjectPicker()}<label class="search-field"><span class="field-label">Search records</span><input id="record-search" type="search" placeholder="Subject or value across displayed datasets..." value="${esc(state.rowSearch)}"></label><label class="select-field">Columns<select id="column-mode"><option value="related" ${state.relatedOnly ? "selected" : ""}>Related columns</option><option value="all" ${!state.relatedOnly ? "selected" : ""}>All columns</option></select></label><button class="button" id="clear-selection">Clear highlight</button><button class="button" id="reset-layout">Reset layout</button></div><div class="lineage-toolbar"><div id="lineage-summary" role="status"></div><span class="lineage-legend"><i class="swatch key"></i>Key / ID <i class="swatch selected"></i>Selected <i class="swatch related"></i>Related</span></div><div class="review-workbench" style="--spec-width:${layout.spec}%;--input-height:${layout.inputs ?? 50}%"><section class="spec-pane pane" aria-labelledby="spec-heading"><header class="pane-header"><div><h2 id="spec-heading">yamaa specification</h2><span id="spec-caption">${state.dataset} / ${specification.text.split("\n").length} lines${specification.lineage.unresolved.length ? " / " + specification.lineage.unresolved.length + " unresolved references" : ""}</span></div>${link(sourceUrl(specification.path), "Open source")}</header><div class="spec-scroll" id="spec-scroll" tabindex="0" aria-label="Complete YAML specification">${renderSpec()}</div><footer class="pane-footer">Declared column dependencies; contributing rows are not traced.</footer></section><div class="spec-resizer" id="spec-resizer" role="separator" aria-label="Resize specification panel" aria-orientation="vertical" aria-valuemin="25" aria-valuemax="60" aria-valuenow="${Math.round(layout.spec)}" tabindex="0"></div><div class="data-panes">${group("input")}<div id="data-resizer" class="data-resizer" role="separator" aria-label="Resize input and output areas" aria-orientation="horizontal" aria-valuemin="25" aria-valuemax="75" aria-valuenow="${Math.round(layout.inputs ?? 50)}" tabindex="0"></div>${group("output")}</div></div><div id="data-status" role="status" class="data-status"></div><div id="evidence-drawer"></div>`;
  }
  function renderSpec() {
    const { specification, esc } = ctx,
      positions = specification.lineage.spans;
    return specification.text
      .split("\n")
      .map((line, i) => {
        const number = i + 1,
          pair = Object.entries(positions).find(
            ([, s]) => number >= s.start && number <= s.end,
          );
        const node = pair
          ? (pair[1].kind === "columns"
              ? "spec."
              : pair[1].kind === "rows"
                ? "row."
                : "intermediate.") + pair[0]
          : "";
        return `<div class="spec-line" id="spec-L${number}" ${node ? `data-line-node="${esc(node)}"` : ""}><button class="line-number" ${node ? `data-node="${esc(node)}"` : "disabled"} tabindex="${pair && number === pair[1].start ? 0 : -1}" aria-label="${node ? "Select " + esc(node) + " at " : ""}line ${number}">${number}</button><code>${esc(line) || " "}</code></div>`;
      })
      .join("");
  }
  function applyHighlight(scroll = false) {
    const { model, state, plan, root, byId } = ctx;
    for (const el of root().querySelectorAll("[data-node],[data-line-node]")) {
      const node =
        el.dataset.canonical ||
        canonicalNode(
          model,
          state.dataset,
          el.dataset.node || el.dataset.lineNode,
        );
      el.classList.toggle("node-selected", node === plan.focus);
      el.classList.toggle(
        "node-related",
        node !== plan.focus && plan.related.has(node),
      );
      if (el.tagName === "BUTTON")
        el.setAttribute("aria-pressed", String(node === plan.focus));
    }
    byId("lineage-summary").textContent = state.focus
      ? `${state.focus.replace(/^output\./, "Output ").replace(/^spec\./, "YAML ")} selected. ${state.relatedOnly ? "Related source datasets and columns are shown." : "Linked columns are highlighted across displayed datasets."}`
      : "Select an output column to reveal connected input datasets and columns. Drag pane edges or column separators to resize.";
    if (scroll && state.focus) {
      const lines = [...root().querySelectorAll("[data-line-node]")];
      const preferred = state.focus.replace(/^output\./, "spec.");
      const line =
        lines.find((el) => el.dataset.lineNode === preferred) ||
        lines.find((el) =>
          plan.related.has(
            canonicalNode(model, state.dataset, el.dataset.lineNode),
          ),
        );
      if (line)
        byId("spec-scroll").scrollTop = Math.max(0, line.offsetTop - 50);
      for (const region of root().querySelectorAll("[data-table-for]")) {
        const target =
          region.querySelector("th.node-selected") ||
          [...region.querySelectorAll("th.node-related")].find(
            (el) =>
              !el.classList.contains("subject-column") &&
              !el.dataset.node.endsWith(".STUDYID"),
          );
        if (target) region.scrollLeft = Math.max(0, target.offsetLeft - 170);
      }
    }
  }
  function tableMarkup(panel, rows, peers) {
    const { model, state, plan, layout, esc } = ctx,
      meta = panel.meta;
    const filtered = filterRows(rows, meta, state.rowSearch, peers),
      size = state.pageSizes[panel.key] || 10;
    const page = Math.max(
      0,
      Math.min(
        state.pages[panel.key] || 0,
        Math.max(0, Math.ceil(filtered.length / size) - 1),
      ),
    );
    state.pages[panel.key] = page;
    const start = page * size,
      shown = filtered.slice(start, start + size),
      indices = columnIndexes(
        model,
        panel,
        plan.related,
        state.relatedOnly,
        plan.focus,
      );
    const current = model.datasets.find((d) => d.name === state.dataset),
      alias = current.inputs.find((i) => i.table === panel.table)?.alias;
    const raw = (name) =>
      panel.kind === "output"
        ? "output." + name
        : alias
          ? alias + "." + name
          : tableNode(model, panel.table, name);
    const canonical = (name) =>
      panel.kind === "output"
        ? `out:${panel.domain}.${name}`
        : tableNode(model, panel.table, name);
    const isKey = (i) =>
      (meta.keys || []).includes(meta.columns[i].name) ||
      i === meta.subject_index;
    const widths = indices.map(
      (i) =>
        layout.columns[panel.key]?.[meta.columns[i].name] ||
        (i === meta.subject_index ? 140 : 120),
    );
    return {
      filtered,
      start,
      size,
      html: `<table class="review-table" style="width:${36 + widths.reduce((a, b) => a + b, 0)}px"><caption class="sr-only">${esc(panel.domain)} ${panel.kind} records. Select column headers to follow declared lineage.</caption><colgroup><col style="width:36px">${indices.map((i, n) => `<col data-column="${esc(meta.columns[i].name)}" style="width:${widths[n]}px">`).join("")}</colgroup><thead><tr><th scope="col" class="row-number">Row</th>${indices
        .map((i, n) => {
          const c = meta.columns[i],
            node = canonical(c.name);
          return `<th scope="col" class="${i === meta.subject_index ? "subject-column " : ""}${isKey(i) ? "key-column" : ""}" data-node="${esc(raw(c.name))}" data-canonical="${esc(node)}"><button data-node="${esc(raw(c.name))}" data-canonical="${esc(node)}" ${panel.kind === "output" ? `data-output-dataset="${esc(panel.domain)}"` : ""} title="${esc((c.label || c.declared_label || c.name) + " / " + c.type)}">${esc(c.name)}${isKey(i) ? `<span class="key-badge">${(meta.keys || []).includes(c.name) ? "Key" : "ID"}</span>` : ""}<small>${esc(c.type)}</small></button><span class="column-resizer" data-resize-column="${esc(c.name)}" role="separator" aria-label="Resize ${esc(panel.domain + "." + c.name)} column" aria-orientation="vertical" aria-valuemin="72" aria-valuemax="640" aria-valuenow="${widths[n]}" tabindex="0"></span></th>`;
        })
        .join(
          "",
        )}</tr></thead><tbody>${shown.length ? shown.map((r) => `<tr><th scope="row" class="row-number">${r[0] + 1}</th>${indices.map((i) => `<td class="${isKey(i) ? "key-column" : ""}" data-canonical="${esc(canonical(meta.columns[i].name))}" title="${esc(r[i + 1])}">${r[i + 1] === null ? '<span class="missing" aria-label="Missing value">&#8212;</span>' : esc(r[i + 1])}</td>`).join("")}</tr>`).join("") : `<tr><td colspan="${indices.length + 1}" class="empty-rows">${state.subjects.length ? "No records for these subjects and this search." : "No subjects selected. Use the Subjects dropdown to select subjects."}</td></tr>`}</tbody></table>`,
    };
  }
  function paintTables() {
    if (ctx.rowsLoading) return;
    const { model, state, plan, rowsByTable, rowErrors, root, esc } = ctx;
    const peers = plan.panels
      .filter((p) => rowsByTable.has(p.table))
      .map((p) => ({ rows: rowsByTable.get(p.table), meta: p.meta }));
    for (const panel of plan.panels) {
      const region = root().querySelector(`[data-table-for="${panel.key}"]`),
        footer = root().querySelector(`[data-footer-for="${panel.key}"]`);
      if (!region) continue;
      if (rowErrors.has(panel.table)) {
        region.innerHTML = `<div class="error-state" role="alert">${esc(rowErrors.get(panel.table))}<button data-retry>Retry loading</button></div>`;
        footer.textContent = "Dataset unavailable; retry to load records.";
        continue;
      }
      const result = tableMarkup(
        panel,
        rowsByTable.get(panel.table) || [],
        peers,
      );
      region.innerHTML = result.html;
      region.tabIndex = 0;
      region.setAttribute("role", "region");
      region.setAttribute(
        "aria-label",
        panel.domain + " " + panel.kind + " data table",
      );
      footer.innerHTML = `<label class="row-size">Rows <select data-page-size="${panel.key}" aria-label="${esc(panel.domain)} ${panel.kind} rows per page">${PAGE_SIZES.map((size) => `<option ${size === result.size ? "selected" : ""}>${size}</option>`).join("")}</select></label><span>${result.filtered.length ? result.start + 1 : 0}-${Math.min(result.start + result.size, result.filtered.length)} of ${result.filtered.length.toLocaleString()} selected rows / ${panel.meta.rows.toLocaleString()} total${panel.meta.subject_index === null ? " / subject-independent lookup" : ""}</span><span class="pagination"><button data-panel-page="${panel.key}" data-step="-1" ${!state.pages[panel.key] ? "disabled" : ""} aria-label="Previous ${esc(panel.domain)} ${panel.kind} rows">&#8592;</button><button data-panel-page="${panel.key}" data-step="1" ${result.start + result.size >= result.filtered.length ? "disabled" : ""} aria-label="Next ${esc(panel.domain)} ${panel.kind} rows">&#8594;</button></span>`;
    }
    fitWorkbench();
    sizes.disconnect();
    for (const card of root().querySelectorAll("[data-panel]"))
      sizes.observe(card);
    applyHighlight();
    ctx.byId("data-status").textContent =
      `${state.subjects.length} of ${model.subjects.length} subjects selected. ${plan.inputs.length} input and ${plan.outputs.length} output datasets displayed. Each table has its own row count and pagination. Missing values are shown as a dash.`;
  }
  function fitWorkbench() {
    const el = ctx.root()?.querySelector(".review-workbench");
    if (!el) return;
    const groups = [...el.querySelectorAll(".dataset-group")];
    const heights = groups.map((group) => {
      const cards = [...group.querySelectorAll("[data-panel]")];
      const cardHeights = cards.map((card) => {
        const region = card.querySelector(".data-region");
        const height = Math.ceil(
          card.querySelector(".pane-header").offsetHeight +
            card.querySelector(".pane-footer").offsetHeight +
            (region.querySelector("table")?.offsetHeight || 90) +
            // Borders and room for the horizontal table scrollbar.
            24,
        );
        card.style.minHeight = height + "px";
        return Math.max(height, parseFloat(card.style.height) || 0);
      });
      return (
        group.querySelector(".dataset-group-header").offsetHeight +
        Math.max(120, ...cardHeights) +
        24
      );
    });
    const panes = el.querySelector(".data-panes");
    if (innerWidth > 700) {
      let [input, output] = heights;
      if (ctx.layout.inputs !== null) {
        const fraction = ctx.layout.inputs / 100;
        const space = Math.max(input / fraction, output / (1 - fraction));
        input = Math.ceil(space * fraction);
        output = Math.ceil(space * (1 - fraction));
      }
      panes.style.gridTemplateRows = `${input}px 8px ${output}px`;
      el.style.height = input + output + 16 + "px";
      el.style.setProperty(
        "--spec-height",
        Math.min(input + output + 16, Math.max(280, innerHeight - 100)) + "px",
      );
    } else {
      panes.style.gridTemplateRows = "";
      el.style.height = "";
    }
  }
  return { workspace, applyHighlight, paintTables, fitWorkbench };
}
