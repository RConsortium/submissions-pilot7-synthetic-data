import { connectedNodes } from "./lineage.js";
import { filterRows, csvContent } from "./data.js";

/** Components read the live application context at render time. */
export function createWorkspace(ctx) {
  function subjectPicker() {
    const { model, state, esc } = ctx;
    return `<details class="subject-picker" id="subject-picker"><summary id="subject-summary">Subjects <strong>${state.subjects.length} / ${model.subjects.length}</strong><span aria-hidden="true">&#9662;</span></summary><div class="subject-popover"><label class="field-label" for="subject-search">Find a subject</label><input id="subject-search" type="search" placeholder="Search ${esc(model.settings.subject_key)}..."><div class="subject-actions">${[...new Set([model.settings.default_subject_count, 10, 25, 50])].map((n) => `<button data-subject-count="${n}">First ${n}</button>`).join("")}<button data-subject-count="all">Select all</button><button data-subject-count="0">Clear</button><button data-close-subjects>Done</button></div><div class="subject-options">${model.subjects.map((s) => `<label data-subject-option="${esc(s)}"><input type="checkbox" data-subject="${esc(s)}" ${state.subjects.includes(s) ? "checked" : ""}>${esc(s)}</label>`).join("")}</div><p>All records for selected subjects are available. Subject-independent lookup rows stay visible.</p></div></details>`;
  }
  function workspace() {
    const {
      model,
      specification,
      state,
      esc,
      sourceUrl,
      dataset,
      source,
      link,
    } = ctx;
    const d = dataset();
    return `<div class="workspace-toolbar"><label class="select-field">ADaM dataset<select id="dataset-select">${model.datasets.map((x) => `<option ${d.name === x.name ? "selected" : ""}>${x.name}</option>`).join("")}</select></label>${subjectPicker()}<label class="search-field"><span class="field-label">Search records</span><input id="record-search" type="search" placeholder="Subject or value across input and output..." value="${esc(state.rowSearch)}"></label><button class="button" id="clear-selection">Clear highlight</button><button class="button" id="wide-mode" aria-pressed="${document.body.classList.contains("review-wide")}">Widen workspace</button></div><div class="lineage-toolbar"><div id="lineage-summary" role="status">Select an input column, specification block, or output column to follow its connections.</div><span class="lineage-legend"><i class="swatch selected"></i>Selected <i class="swatch related"></i>Related</span></div><div class="review-workbench"><section class="spec-pane pane" aria-labelledby="spec-heading"><header class="pane-header"><div><h2 id="spec-heading">yamaa specification</h2><span id="spec-caption">Complete YAML / ${specification.text.split("\n").length} lines${specification.lineage.unresolved.length ? " / " + specification.lineage.unresolved.length + " unresolved references" : ""}</span></div>${link(sourceUrl(specification.path), "Open source")}</header><div class="spec-scroll" id="spec-scroll" tabindex="0" aria-label="Complete YAML specification">${renderSpec()}</div><footer class="pane-footer">Column dependencies include declared filters, joins and ordering. No contributing-row trace.</footer></section><div class="spec-resizer" id="spec-resizer" role="separator" aria-label="Resize specification panel" aria-orientation="vertical" aria-valuemin="25" aria-valuemax="60" aria-valuenow="36" tabindex="0"></div><div class="data-panes"><section class="pane input-pane" aria-labelledby="input-heading"><header class="pane-header"><div><h2 id="input-heading">Input data</h2><label class="sr-only" for="input-select">Input dataset</label><select id="input-select">${d.inputs.map((x) => `<option value="${x.alias}" ${state.input === x.alias ? "selected" : ""}>${x.alias} / ${model.tables[x.table].path.includes("-yamaa") ? "derived ADaM input" : "SDTM or lookup"}</option>`).join("")}<optgroup label="Other staged inputs">${Object.values(
      model.tables,
    )
      .filter(
        (t) =>
          t.path.includes("/sdtm/") && !d.inputs.some((x) => x.table === t.id),
      )
      .map(
        (t) =>
          `<option value="${t.id}" ${state.input === t.id ? "selected" : ""}>${t.name}</option>`,
      )
      .join(
        "",
      )}</optgroup></select></div><div id="input-actions"></div></header><div id="input-table" class="data-region"></div><footer id="input-footer" class="pane-footer"></footer></section><section class="pane output-pane" aria-labelledby="output-heading"><header class="pane-header"><div><h2 id="output-heading">ADaM output</h2><label class="sr-only" for="output-select">Output dataset type</label><select id="output-select"><option value="derived">yamaa derived</option>${d.reference ? `<option value="reference" ${state.output === "reference" ? "selected" : ""}>Official reference</option>` : ""}</select></div><div id="output-actions"></div></header><div id="output-table" class="data-region"></div><footer id="output-footer" class="pane-footer"></footer></section></div></div><div id="data-status" role="status" class="data-status"></div><div id="evidence-drawer"></div>`;
  }
  function renderSpec() {
    const { specification, esc } = ctx;
    const positions = specification.lineage.spans;
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
        const first = pair && number === pair[1].start;
        return `<div class="spec-line" id="spec-L${number}" ${node ? `data-line-node="${esc(node)}"` : ""}><button class="line-number" ${node ? `data-node="${esc(node)}"` : "disabled"} tabindex="${first ? 0 : -1}" aria-label="${node ? "Select " + esc(node) + " at" : ""} line ${number}">${number}</button><code>${esc(line) || " "}</code></div>`;
      })
      .join("");
  }
  function applyHighlight(scroll = false) {
    const { specification, state, byId, root, dataset } = ctx;
    const related = graphSelection();
    root()
      .querySelectorAll("[data-node],[data-line-node]")
      .forEach((el) => {
        const node = el.dataset.node || el.dataset.lineNode;
        el.classList.toggle("node-selected", node === state.focus);
        el.classList.toggle(
          "node-related",
          node !== state.focus && related.has(node),
        );
        if (el.tagName === "BUTTON" && el.dataset.node)
          el.setAttribute("aria-pressed", String(node === state.focus));
      });
    const summary = byId("lineage-summary");
    if (summary)
      summary.textContent = state.focus
        ? `${state.focus.replace(/^spec\./, "YAML ").replace(/^output\./, "Output ")} selected / ${[...related].filter((n) => !n.startsWith("intermediate.")).length - 1} connected columns and rules. Static dependencies, including context.`
        : "Select an input column, specification block, or output column to follow its connections.";
    if (scroll && state.focus) {
      const node = state.focus.startsWith("output.")
        ? state.focus.replace("output.", "spec.")
        : state.focus;
      const line =
        Array.from(root().querySelectorAll("[data-line-node]")).find(
          (el) => el.dataset.lineNode === node,
        ) ||
        Array.from(root().querySelectorAll("[data-line-node]")).find((el) =>
          related.has(el.dataset.lineNode),
        );
      if (line) {
        const pane = byId("spec-scroll");
        pane.scrollTop = Math.max(0, line.offsetTop - 50);
      }
      for (const id of ["input-table", "output-table"]) {
        const region = byId(id);
        const selectedSpec = state.focus.replace(/^output\./, "spec.");
        const immediate = specification.lineage.edges[selectedSpec] || [];
        const direct =
          id === "input-table"
            ? Array.from(region?.querySelectorAll("th[data-node]") || []).find(
                (el) => immediate.includes(el.dataset.node),
              )
            : null;
        const th =
          direct || region?.querySelector("th.node-selected,th.node-related");
        if (th) {
          const pinned =
            region.querySelector("th:nth-child(2)")?.offsetWidth || 120;
          region.scrollLeft = Math.max(0, th.offsetLeft - pinned - 35);
        }
      }
    }
  }
  function selectFocus(node) {
    const { state, save } = ctx;
    state.focus = state.focus === node ? "" : node;
    save();
    applyHighlight(true);
  }
  function visibleRows(rows) {
    const { inputRows, outputRows, inputMeta, outputMeta, state } = ctx;
    return filterRows(
      rows,
      rows === inputRows ? inputMeta() : outputMeta(),
      state.rowSearch,
      [
        { rows: inputRows, meta: inputMeta() },
        { rows: outputRows, meta: outputMeta() },
      ],
    );
  }
  function tableMarkup(kind, rows, meta) {
    const { state, PAGE, esc, dataset, source } = ctx;
    const filtered = visibleRows(rows),
      key = kind + "Page";
    state[key] = Math.min(
      state[key],
      Math.max(0, Math.ceil(filtered.length / PAGE) - 1),
    );
    const start = state[key] * PAGE,
      shown = filtered.slice(start, start + PAGE);
    const names = meta.columns.map((c) => c.name),
      subject = meta.subject_index ?? -1;
    const order = [
      ...(subject >= 0 ? [subject] : []),
      ...names.map((_, i) => i).filter((i) => i !== subject),
    ];
    const alias = kind === "output" ? "output" : source()?.alias || meta.name;
    return {
      filtered,
      start,
      html: `<table class="review-table"><caption class="sr-only">${kind === "output" ? "Analysis output" : "Input"} records. Column headers select declared lineage.</caption><thead><tr><th scope="col" class="row-number">Row</th>${order.map((i) => `<th scope="col" data-node="${esc(alias + "." + names[i])}"><button data-node="${esc(alias + "." + names[i])}" title="${esc((meta.columns[i].label || meta.columns[i].declared_label || names[i]) + " / " + meta.columns[i].type)}">${esc(names[i])}<small>${esc(meta.columns[i].type)}</small></button></th>`).join("")}</tr></thead><tbody>${shown.length ? shown.map((r) => `<tr><th scope="row" class="row-number">${r[0] + 1}</th>${order.map((i) => `<td data-node="${esc(alias + "." + names[i])}" title="${esc(r[i + 1])}">${r[i + 1] === null ? '<span class="missing" aria-label="Missing value">&#8212;</span>' : esc(r[i + 1])}</td>`).join("")}</tr>`).join("") : `<tr><td colspan="${names.length + 1}" class="empty-rows">${state.subjects.length ? "No records for these subjects and this search. Subjects with no events may have no rows in this dataset." : "No subjects selected. Use the Subjects dropdown to select subjects."}</td></tr>`}</tbody></table>`,
    };
  }
  function paintTables() {
    const {
      model,
      inputRows,
      outputRows,
      state,
      PAGE,
      byId,
      resource,
      inputMeta,
      outputMeta,
      link,
    } = ctx;
    for (const [kind, rows, meta] of [
      ["input", inputRows, inputMeta()],
      ["output", outputRows, outputMeta()],
    ]) {
      if (!meta || !byId(kind + "-table")) continue;
      const result = tableMarkup(kind, rows, meta),
        el = byId(kind + "-table");
      el.innerHTML = result.html;
      el.tabIndex = 0;
      el.setAttribute("role", "region");
      el.setAttribute("aria-label", kind + " data table");
      byId(kind + "-footer").innerHTML =
        `<span>${result.filtered.length ? result.start + 1 : 0}-${Math.min(result.start + PAGE, result.filtered.length)} of ${result.filtered.length.toLocaleString()} selected rows / ${meta.rows.toLocaleString()} total${meta.subject_index === null ? " / subject-independent lookup" : ""}</span><span class="pagination"><button data-page="${kind}" data-step="-1" ${!state[kind + "Page"] ? "disabled" : ""} aria-label="Previous ${kind} rows">&#8592;</button><button data-page="${kind}" data-step="1" ${result.start + PAGE >= result.filtered.length ? "disabled" : ""} aria-label="Next ${kind} rows">&#8594;</button></span>`;
      byId(kind + "-actions").innerHTML =
        `<button class="text-link" data-export="${kind}">Selected CSV</button>${link(resource(meta.download), "Full " + meta.format)}`;
    }
    fitWorkbench();
    byId("data-status").textContent =
      `${state.subjects.length} of ${model.subjects.length} study subjects selected. All matching records are accessible through the row controls. Missing values are shown as a dash. Input and output retain their original values and row order.`;
    applyHighlight();
  }
  function fitWorkbench() {
    const { root } = ctx;
    const el = root()?.querySelector(".review-workbench");
    if (!el) return;
    if (innerWidth > 700) {
      el.style.height =
        Math.max(
          340,
          Math.min(
            1000,
            innerHeight - el.getBoundingClientRect().top - scrollY - 35,
          ),
        ) + "px";
      el.style.minHeight = "340px";
    } else {
      el.style.height = "";
      el.style.minHeight = "";
    }
  }
  function resizeSpec(percent) {
    const { byId, root } = ctx;
    const value = Math.max(25, Math.min(60, percent));
    root().style.setProperty("--spec-width", value + "%");
    byId("spec-resizer")?.setAttribute(
      "aria-valuenow",
      String(Math.round(value)),
    );
  }
  function exportCsv(kind) {
    const {
      model,
      inputRows,
      outputRows,
      state,
      dataset,
      inputMeta,
      outputMeta,
      notice,
    } = ctx;
    const rows = visibleRows(kind === "input" ? inputRows : outputRows),
      meta = kind === "input" ? inputMeta() : outputMeta();
    const csv = csvContent(rows, meta.columns);
    const url = URL.createObjectURL(
      new Blob([csv], { type: "text/csv;charset=utf-8" }),
    );
    const a = document.createElement("a");
    a.href = url;
    a.download = `${model.id}-${state.dataset.toLowerCase()}-${kind}-${state.subjects.length}-subjects.csv`;
    a.click();
    setTimeout(() => URL.revokeObjectURL(url), 1000);
    notice(`${rows.length} selected records exported`);
  }
  function overview() {
    const { model, report, specification, dataset, link } = ctx;
    return `<div class="section-heading"><div><h2>Dataset coverage</h2><p>Validated outputs and their independent official references. Open a dataset to inspect its complete specification and data.</p></div></div><div class="overview-table"><table class="review-table"><thead><tr><th>Dataset</th><th>Output rows</th><th>Columns</th><th>Reference comparison</th><th>Documentation</th></tr></thead><tbody>${model.datasets.map((d) => `<tr><td><button class="text-link" data-dataset="${d.name}">${d.name}</button></td><td>${model.tables[d.output].rows.toLocaleString()}</td><td>${model.tables[d.output].columns.length}</td><td><span class="status ${d.comparison === "passed" ? "good" : "neutral"}">${d.comparison === "passed" ? "Passed" : "Unavailable"}</span></td><td><button class="text-link" data-domain-findings="${d.name}">${report.findings.filter((f) => f.dataset === d.name).length} observations / tasks</button></td></tr>`).join("")}</tbody></table></div><div class="coverage-note"><strong>These are real results.</strong> This study was run with its pinned yamaa engine and configured comparison policy. Narrative document interpretation remains a separate human review activity.</div>`;
  }

  function graphSelection() {
    return connectedNodes(ctx.specification.lineage.edges, ctx.state.focus);
  }

  return {
    subjectPicker,
    workspace,
    renderSpec,
    applyHighlight,
    selectFocus,
    visibleRows,
    tableMarkup,
    paintTables,
    fitWorkbench,
    resizeSpec,
    exportCsv,
    overview,
  };
}
