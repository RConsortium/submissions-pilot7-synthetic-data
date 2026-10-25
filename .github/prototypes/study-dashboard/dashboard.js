/* Static study review: complete data, declared lineage, and cited evidence. */
(() => {
  "use strict";
  const REPO =
    "https://github.com/RConsortium/submissions-pilot7-synthetic-data";
  const asset = Array.from(document.scripts).find((s) =>
    /\/assets\/dashboard\.js(?:\?|$)/.test(s.src),
  );
  const site = new URL("../", asset.src),
    dataRoot = new URL("assets/review-data/", site);
  const cache = new Map();
  let ticket = 0,
    model = null,
    specification = null,
    report = null,
    index = null,
    inputRows = [],
    outputRows = [];
  const state = {
    view: "datasets",
    dataset: "ADSL",
    subjects: [],
    input: "",
    output: "derived",
    focus: "",
    rowSearch: "",
    findingSearch: "",
    kind: "",
    evidence: "",
    inputPage: 0,
    outputPage: 0,
  };
  const PAGE = 40;
  const esc = (v) =>
    String(v ?? "").replace(
      /[&<>"']/g,
      (c) =>
        ({
          "&": "&amp;",
          "<": "&lt;",
          ">": "&gt;",
          '"': "&quot;",
          "'": "&#39;",
        })[c],
    );
  const root = () => document.getElementById("study-dashboard");
  const byId = (id) => document.getElementById(id);
  const resource = (path) => new URL(`${model.id}/${path}`, dataRoot).href;
  const sourceUrl = (path, line) =>
    `${REPO}/blob/${model.revision}/${path}${line ? "#L" + line : ""}`;
  const dataset = () =>
    model.datasets.find((d) => d.name === state.dataset) || model.datasets[0];
  const source = () => dataset().inputs.find((i) => i.alias === state.input);
  const inputMeta = () => model.tables[source()?.table || state.input];
  const outputMeta = () =>
    model.tables[
      dataset()[state.output === "reference" ? "reference" : "output"]
    ];
  const link = (url, label, cls = "text-link") =>
    `<a class="${cls}" href="${esc(url)}" target="_blank" rel="noreferrer">${esc(label)} <span aria-hidden="true">&#8599;</span></a>`;
  function get(url) {
    const key = String(url);
    if (!cache.has(key))
      cache.set(
        key,
        fetch(key, { cache: "no-cache" })
          .then(async (r) => {
            if (!r.ok)
              throw Error(`Cannot load ${new URL(key).pathname} (${r.status})`);
            if (!new URL(key).pathname.endsWith(".json.gz")) return r.json();
            const bytes = new Uint8Array(await r.arrayBuffer());
            // Hosts may apply HTTP content decoding before Fetch exposes bytes.
            if (bytes[0] !== 0x1f || bytes[1] !== 0x8b)
              return JSON.parse(new TextDecoder().decode(bytes));
            if (typeof DecompressionStream === "undefined")
              throw Error(
                "Please use a current browser to load the study data.",
              );
            const stream = new Blob([bytes])
              .stream()
              .pipeThrough(new DecompressionStream("gzip"));
            return new Response(stream).json();
          })
          .catch((e) => {
            cache.delete(key);
            throw e;
          }),
      );
    return cache.get(key);
  }
  function route() {
    const p = new URLSearchParams();
    if (
      state.subjects.length !== 3 ||
      !state.subjects.every((s, i) => s === model.subjects[i])
    )
      p.set(
        "subjects",
        state.subjects.length === model.subjects.length
          ? "all"
          : state.subjects.join(",") || "none",
      );
    for (const k of [
      "input",
      "output",
      "focus",
      "rowSearch",
      "findingSearch",
      "kind",
      "evidence",
    ])
      if (state[k] && !(k === "output" && state[k] === "derived"))
        p.set(k, state[k]);
    return `#${model.id}/${state.view}/${state.dataset}${p.size ? "?" + p : ""}`;
  }
  function save() {
    if (model) history.replaceState(null, "", route());
  }
  function navigate(view) {
    state.view = view;
    location.hash = route();
  }
  function notice(message) {
    let el = byId("review-toast");
    if (!el) {
      el = document.createElement("div");
      el.id = "review-toast";
      el.className = "review-toast";
      el.setAttribute("role", "status");
      document.body.append(el);
    }
    el.textContent = message;
    clearTimeout(notice.timer);
    el.classList.add("visible");
    notice.timer = setTimeout(() => el.classList.remove("visible"), 3000);
  }
  function metric(value) {
    return value >= 1e6
      ? (value / 1e6).toFixed(1) + "M"
      : value.toLocaleString("en-US");
  }
  function metrics() {
    const m = model.metrics;
    return `<div class="metric-strip">${["Datasets", "Columns", "Cells"].map((n, i) => `<span><strong>${n}</strong> ${metric(m.matched[i])} / ${metric(m.reference[i])} <small>${m.reference[i] ? Math.round((100 * m.matched[i]) / m.reference[i]) + "%" : "n/a"}</small></span>`).join("")}<button data-view="findings"><strong>Documentation review</strong> ${report.findings.length} observations / tasks</button></div>`;
  }
  function subjectPicker() {
    return `<details class="subject-picker" id="subject-picker"><summary id="subject-summary">Subjects <strong>${state.subjects.length} / ${model.subjects.length}</strong><span aria-hidden="true">&#9662;</span></summary><div class="subject-popover"><label class="field-label" for="subject-search">Find a subject</label><input id="subject-search" type="search" placeholder="Search USUBJID..."><div class="subject-actions">${[3, 10, 25, 50].map((n) => `<button data-subject-count="${n}">First ${n}</button>`).join("")}<button data-subject-count="all">Select all</button><button data-subject-count="0">Clear</button></div><div class="subject-options">${model.subjects.map((s) => `<label data-subject-option="${esc(s)}"><input type="checkbox" data-subject="${esc(s)}" ${state.subjects.includes(s) ? "checked" : ""}>${esc(s)}</label>`).join("")}</div><p>All records for selected subjects are available. Subject-independent lookup rows stay visible.</p></div></details>`;
  }
  function frame() {
    return `<header class="review-hero"><div><p class="eyebrow">PILOT 7 / SDTM &#8594; ADaM</p><h1>${esc(model.title)}</h1><p>Agentic review SDTM to ADaM derivations against the published submission package.</p></div><div class="hero-actions">${link(model.source, "Study source", "button")}<button class="button" id="copy-view">Copy view link</button><button class="button primary" data-view="findings">Consistency report</button></div></header>${metrics()}<div class="provenance">Real staged inputs and official references. Derived outputs passed the study's existing comparator. <span>Source ${link(`${REPO}/commit/${model.revision}`, model.revision.slice(0, 8))}</span></div><nav class="review-tabs" aria-label="Study sections">${[
      ["datasets", "Review workspace"],
      ["overview", "Dataset overview"],
      ["findings", "Consistency report"],
      ["materials", "Source documents"],
      ["comments", "Comments"],
    ]
      .map(
        ([id, label]) =>
          `<button data-view="${id}" class="${state.view === id ? "active" : ""}" ${state.view === id ? 'aria-current="page"' : ""}>${label}</button>`,
      )
      .join(
        "",
      )}</nav><div id="view-content"></div><div id="share-fallback" hidden><label>Copy this review link<input id="share-url" readonly></label></div><div class="review-footnote">Build success, reference agreement, and documentation consistency are separate checks. ${link(new URL("verification/", site).href, "Verification policy")}</div>`;
  }
  function workspace() {
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
      )}</optgroup></select></div><div id="input-actions"></div></header><div id="input-table" class="data-region"></div><footer id="input-footer" class="pane-footer"></footer></section><section class="pane output-pane" aria-labelledby="output-heading"><header class="pane-header"><div><h2 id="output-heading">ADaM output</h2><label class="sr-only" for="output-select">Output dataset type</label><select id="output-select"><option value="derived">yamaa derived</option><option value="reference" ${state.output === "reference" ? "selected" : ""}>Official reference</option></select></div><div id="output-actions"></div></header><div id="output-table" class="data-region"></div><footer id="output-footer" class="pane-footer"></footer></section></div></div><div id="data-status" role="status" class="data-status"></div><div id="evidence-drawer"></div>`;
  }
  function renderSpec() {
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
  function graphSelection() {
    const edges = specification.lineage.edges,
      upstream = new Set(),
      downstream = new Set();
    function walk(node, direction, seen) {
      if (seen.has(node)) return;
      seen.add(node);
      const adjacent =
        direction === "up"
          ? edges[node] || []
          : Object.keys(edges).filter((k) => edges[k].includes(node));
      for (const n of adjacent) walk(n, direction, seen);
    }
    if (state.focus) {
      walk(state.focus, "up", upstream);
      walk(state.focus, "down", downstream);
    }
    return new Set([...upstream, ...downstream]);
  }
  function applyHighlight(scroll = false) {
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
    state.focus = state.focus === node ? "" : node;
    save();
    applyHighlight(true);
  }
  async function rowsFor(meta) {
    const all = state.subjects.length === model.subjects.length,
      selected = new Set(state.subjects);
    const chunks = meta.chunks.filter(
      (c) =>
        meta.subject_index === null ||
        all ||
        c.subjects.some((s) => selected.has(s)),
    );
    const records = (
      await Promise.all(chunks.map((c) => get(resource(c.url))))
    ).flat();
    return records
      .filter(
        (r) =>
          meta.subject_index === null ||
          all ||
          selected.has(String(r[meta.subject_index + 1])),
      )
      .sort((a, b) => a[0] - b[0]);
  }
  function visibleRows(rows) {
    const q = state.rowSearch.toLowerCase().trim();
    if (!q) return rows;
    const subjects = new Set();
    for (const [records, meta] of [
      [inputRows, inputMeta()],
      [outputRows, outputMeta()],
    ]) {
      if (meta.subject_index === null) continue;
      for (const r of records)
        if (
          r.slice(1).some((v) =>
            String(v ?? "")
              .toLowerCase()
              .includes(q),
          )
        )
          subjects.add(r[meta.subject_index + 1]);
    }
    const meta = rows === inputRows ? inputMeta() : outputMeta();
    return rows.filter(
      (r) =>
        r.slice(1).some((v) =>
          String(v ?? "")
            .toLowerCase()
            .includes(q),
        ) ||
        (meta.subject_index !== null &&
          subjects.has(r[meta.subject_index + 1])),
    );
  }
  function tableMarkup(kind, rows, meta) {
    const filtered = visibleRows(rows),
      key = kind + "Page";
    state[key] = Math.min(
      state[key],
      Math.max(0, Math.ceil(filtered.length / PAGE) - 1),
    );
    const start = state[key] * PAGE,
      shown = filtered.slice(start, start + PAGE);
    const names = meta.columns.map((c) => c.name),
      subject = names.indexOf("USUBJID");
    const order = [
      ...(subject >= 0 ? [subject] : []),
      ...names.map((_, i) => i).filter((i) => i !== subject),
    ];
    const alias = kind === "output" ? "output" : source()?.alias || meta.name;
    return {
      filtered,
      start,
      html: `<table class="review-table"><caption class="sr-only">${kind === "output" ? "Analysis output" : "Input"} records. Column headers select declared lineage.</caption><thead><tr><th scope="col" class="row-number">Row</th>${order.map((i) => `<th scope="col" data-node="${esc(alias + "." + names[i])}"><button data-node="${esc(alias + "." + names[i])}" title="${esc((meta.columns[i].label || names[i]) + " / " + meta.columns[i].type)}">${esc(names[i])}<small>${esc(meta.columns[i].type)}</small></button></th>`).join("")}</tr></thead><tbody>${shown.length ? shown.map((r) => `<tr><th scope="row" class="row-number">${r[0] + 1}</th>${order.map((i) => `<td data-node="${esc(alias + "." + names[i])}" title="${esc(r[i + 1])}">${r[i + 1] === null ? '<span class="missing" aria-label="Missing value">&#8212;</span>' : esc(r[i + 1])}</td>`).join("")}</tr>`).join("") : `<tr><td colspan="${names.length + 1}" class="empty-rows">${state.subjects.length ? "No records for these subjects and this search. Subjects with no events may have no rows in this dataset." : "No subjects selected. Use the Subjects dropdown to select subjects."}</td></tr>`}</tbody></table>`,
    };
  }
  function paintTables() {
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
  async function refreshRows() {
    const token = ++refreshRows.token;
    for (const id of ["input-table", "output-table"])
      if (byId(id))
        byId(id).innerHTML =
          '<p class="loading" role="status">Loading selected study records...</p>';
    try {
      const rows = await Promise.all([
        rowsFor(inputMeta()),
        rowsFor(outputMeta()),
      ]);
      if (token !== refreshRows.token || state.view !== "datasets") return;
      [inputRows, outputRows] = rows;
      paintTables();
    } catch (e) {
      if (token === refreshRows.token) {
        for (const id of ["input-table", "output-table"])
          if (byId(id))
            byId(id).innerHTML =
              `<div class="error-state" role="alert">${esc(e.message)}<button id="retry-data">Retry loading</button></div>`;
      }
    }
  }
  refreshRows.token = 0;
  function fitWorkbench() {
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
    const value = Math.max(25, Math.min(60, percent));
    root().style.setProperty("--spec-width", value + "%");
    byId("spec-resizer")?.setAttribute(
      "aria-valuenow",
      String(Math.round(value)),
    );
  }
  document.addEventListener("pointerdown", (event) => {
    if (event.target.id !== "spec-resizer") return;
    event.preventDefault();
    const grid = root().querySelector(".review-workbench");
    const move = (e) => {
      const box = grid.getBoundingClientRect();
      resizeSpec((100 * (e.clientX - box.left)) / box.width);
    };
    const done = () => {
      document.removeEventListener("pointermove", move);
      document.removeEventListener("pointerup", done);
    };
    document.addEventListener("pointermove", move);
    document.addEventListener("pointerup", done);
  });
  document.addEventListener("keydown", (event) => {
    if (event.target.id !== "spec-resizer") return;
    const value = Number(event.target.getAttribute("aria-valuenow"));
    if (["ArrowLeft", "ArrowRight", "Home", "End"].includes(event.key)) {
      event.preventDefault();
      resizeSpec(
        event.key === "Home"
          ? 25
          : event.key === "End"
            ? 60
            : value + (event.key === "ArrowRight" ? 2 : -2),
      );
    }
  });
  window.addEventListener("resize", fitWorkbench);
  function overview() {
    return `<div class="section-heading"><div><h2>Dataset coverage</h2><p>Validated outputs and their independent official references. Open a dataset to inspect its complete specification and data.</p></div></div><div class="overview-table"><table class="review-table"><thead><tr><th>Dataset</th><th>Output rows</th><th>Columns</th><th>Reference comparison</th><th>Documentation</th></tr></thead><tbody>${model.datasets.map((d) => `<tr><td><button class="text-link" data-dataset="${d.name}">${d.name}</button></td><td>${model.tables[d.output].rows.toLocaleString()}</td><td>${model.tables[d.output].columns.length}</td><td><span class="status good">Passed</span></td><td><button class="text-link" data-domain-findings="${d.name}">${report.findings.filter((f) => f.dataset === d.name).length} observations / tasks</button></td></tr>`).join("")}</tbody></table></div><div class="coverage-note"><strong>These are real results.</strong> The three pilot studies were run with their pinned yamaa engine and existing comparison policies. Narrative document interpretation remains a separate human review activity.</div>`;
  }
  function findingItems() {
    const q = state.findingSearch.toLowerCase();
    return report.findings.filter(
      (f) =>
        (!state.kind || f.kind === state.kind) &&
        [
          f.dataset,
          f.variable,
          f.title,
          f.observation,
          f.source.path,
          f.source.excerpt,
        ]
          .join(" ")
          .toLowerCase()
          .includes(q),
    );
  }
  function findingCards() {
    const items = findingItems();
    return `<p class="result-count" role="status">${items.length} of ${report.findings.length} observations and review tasks</p>${items.length ? items.map((f) => `<article class="finding-card"><div class="finding-top"><span class="status ${f.kind === "inconsistent" ? "attention" : "neutral"}">${esc(f.kind.replaceAll("_", " "))}</span><code>${esc(f.dataset + (f.variable ? "." + f.variable : ""))}</code><span>${f.status}</span></div><h3>${esc(f.title)}</h3><p>${esc(f.observation)}</p><details><summary>Source evidence and review guidance</summary><blockquote>${esc(f.source.excerpt)}</blockquote><p><strong>${esc(f.source.path)}</strong> / ${esc(f.source.section)}</p><p>${esc(f.recommendation)}</p></details><div class="finding-actions"><button class="button primary" data-finding="${esc(f.id)}">Open evidence in workspace</button>${link(f.source.url.startsWith("http") ? f.source.url : resource(f.source.url || "report.json"), "Open source")}${link(f.spec.url, "Specification lines")}</div></article>`).join("") : '<div class="empty-state">No findings match. Clear the filters to see all review tasks.</div>'}`;
  }
  function findingsView() {
    return `<div class="section-heading"><div><h2>Consistency verification report</h2><p>Source-backed observations to help a reviewer verify the package and derivation rules.</p></div>${link(resource("report.json"), "Download report JSON", "button")}</div><div class="coverage-note"><strong>Automated checks completed:</strong> ${report.checks.output_columns} output columns; ${report.checks.labels} exact labels checked against published Define-XML.<br><strong>Interpretation coverage:</strong> ${esc(report.coverage.narrative)} Detected differences require human review.</div><div class="report-filters"><label class="search-field"><span class="field-label">Find a variable, dataset, document or phrase</span><input id="finding-search" type="search" value="${esc(state.findingSearch)}" placeholder="For example: ASTDT, imputation, Define-XML..."></label><label class="select-field">Finding type<select id="finding-kind"><option value="">All types</option>${["inconsistent", "unclear", "missing_evidence", "not_reviewed"].map((k) => `<option value="${k}" ${state.kind === k ? "selected" : ""}>${k.replaceAll("_", " ")}</option>`).join("")}</select></label><button class="button" id="clear-findings">Clear filters</button></div><div id="finding-results">${findingCards()}</div>`;
  }
  function materialsView() {
    return `<div class="section-heading"><div><h2>Submission-package sources</h2><p>Retained original documents and searchable extracted reading copies. Source versions are recorded in the study manifest.</p></div>${link(sourceUrl(`${model.id}/spec/source/manifest.json`), "Source manifest", "button")}</div><div class="material-grid">${report.documents.map((d) => `<article class="material-card"><span class="eyebrow">${esc(d.role?.replaceAll("_", " ") || "SOURCE")}</span><h3>${esc(d.name)}</h3><p>${esc(d.path)}</p><div>${link(resource(d.original), "Original document", "button")}${d.reading ? link(resource(d.reading), "Reading copy", "button") : ""}</div>${d.upstream?.url ? link(d.upstream.url, "Published upstream source") : ""}</article>`).join("")}</div>`;
  }
  function commentsView() {
    const c = index.comments;
    return `<div class="section-heading"><div><h2>Review comments</h2><p>Discuss ${esc(model.title)} / ${state.dataset}. Attach the current view link so reviewers can reproduce your context.</p></div><button class="button" id="copy-comment-context">Copy review context</button></div><div class="coverage-note">Comments are saved in <strong>${esc(c.repo)} GitHub Discussions</strong>, using a separate Pilot 7 thread for each dataset. GitHub sign-in is required to post. The static dashboard does not store comments locally.</div><div id="comments-host"></div><p class="comment-fallback">If the embedded discussion is unavailable, ${link(c.discussion_url, "open GitHub Discussions")} or ${link(issueUrl(), "open a Pilot 7 review issue")}.</p>`;
  }
  function issueUrl() {
    const title = `[Dashboard review] ${model.id} ${state.dataset}${state.focus ? " / " + state.focus : ""}`;
    return `${index.comments.issue_url}?title=${encodeURIComponent(title)}&body=${encodeURIComponent(commentContext())}`;
  }
  function commentContext() {
    return `Study: ${model.id}\nDataset: ${state.dataset}\nSelection: ${state.focus || "none"}\nSubjects: ${state.subjects.length === model.subjects.length ? "all" : state.subjects.join(", ")}\nSource revision: ${model.revision}\nReview link: ${location.href}\n\nObservation:\n\nSupporting evidence:\n`;
  }
  function loadComments() {
    const c = index.comments,
      host = byId("comments-host");
    if (!host) return;
    if (!c.repo_id || !c.category_id) {
      host.innerHTML =
        "<p>GitHub discussion configuration is incomplete. Use the review-issue link below.</p>";
      return;
    }
    const script = document.createElement("script");
    script.src = "https://giscus.app/client.js";
    script.async = true;
    script.crossOrigin = "anonymous";
    for (const [key, value] of Object.entries({
      repo: c.repo,
      "repo-id": c.repo_id,
      category: c.category,
      "category-id": c.category_id,
      mapping: "specific",
      term: c.term_prefix + model.id + "/" + state.dataset,
      strict: "1",
      "reactions-enabled": "1",
      "emit-metadata": "0",
      "input-position": "top",
      theme: document.body.dataset.mdColorScheme === "slate" ? "dark" : "light",
      lang: "en",
      loading: "lazy",
    }))
      script.setAttribute("data-" + key, value);
    host.append(script);
  }
  function drawer() {
    const f = report.findings.find((x) => x.id === state.evidence),
      host = byId("evidence-drawer");
    if (!host) return;
    root().classList.toggle("evidence-open", Boolean(f));
    if (!f) {
      host.innerHTML = "";
      return;
    }
    host.innerHTML = `<aside class="evidence-drawer" aria-label="Source evidence"><header><div><span class="eyebrow">SOURCE EVIDENCE</span><h2>${esc(f.dataset + (f.variable ? "." + f.variable : ""))}</h2></div><button class="button" id="close-evidence" aria-label="Close source evidence">Close</button></header><h3>${esc(f.title)}</h3><p>${esc(f.source.path)} / ${esc(f.source.section)}</p><blockquote>${esc(f.source.excerpt)}</blockquote><p>${esc(f.recommendation)}</p><div class="finding-actions">${link(f.source.url.startsWith("http") ? f.source.url : resource(f.source.url || "report.json"), "Open cited source", "button")}${f.source.original ? link(resource(f.source.original), "Original document", "button") : ""}<button class="button" data-view="comments">Comment on this finding</button></div></aside>`;
  }
  async function renderView() {
    const token = ++ticket,
      d = dataset();
    const loaded = await get(resource(d.spec));
    if (token !== ticket) return;
    specification = loaded;
    if (
      !d.inputs.some((i) => i.alias === state.input) &&
      !model.tables[state.input]
    )
      state.input = d.inputs[0]?.alias;
    if (
      state.focus &&
      !specification.lineage.edges[state.focus] &&
      !Object.values(specification.lineage.edges).some((v) =>
        v.includes(state.focus),
      )
    )
      state.focus = "";
    root().innerHTML = frame();
    byId("view-content").innerHTML =
      state.view === "datasets"
        ? workspace()
        : state.view === "overview"
          ? overview()
          : state.view === "findings"
            ? findingsView()
            : state.view === "materials"
              ? materialsView()
              : commentsView();
    if (state.view === "datasets") {
      await refreshRows();
      if (token === ticket) {
        drawer();
        applyHighlight(true);
      }
    }
    if (state.view === "comments") loadComments();
  }
  async function mount() {
    const main = root();
    if (!main) return;
    const token = ++mount.token;
    ++ticket;
    ++refreshRows.token;
    clearTimeout(notice.timer);
    byId("review-toast")?.classList.remove("visible");
    try {
      index = await get(new URL("index.json", dataRoot));
      if (token !== mount.token) return;
      const page = main.dataset.study;
      if (page === "gallery") {
        main.innerHTML = `<h1>Study review workspaces</h1><p>Explore the complete staged inputs, validated derived outputs, specifications, and submission-package sources.</p><div class="material-grid">${index.studies.map((s) => `<a class="study-card" href="${new URL("studies/" + s.id + "/", site)}"><h2>${esc(s.title)}</h2><p>${s.datasets} datasets / ${s.subjects} subjects</p><span>${s.findings} documentation observations and tasks &#8594;</span></a>`).join("")}</div>`;
        return;
      }
      if (!index.studies.some((s) => s.id === page)) {
        main.innerHTML =
          "<h1>Review workspace pending</h1><p>This study has no validated artifact bundle in this build.</p>";
        return;
      }
      const loadedModel = await get(new URL(page + "/catalog.json", dataRoot));
      if (token !== mount.token) return;
      model = loadedModel;
      const loadedReport = await get(resource(model.report));
      if (token !== mount.token) return;
      report = loadedReport;
      const [path, query = ""] = location.hash.slice(1).split("?"),
        [hashStudy, view, name] = path.split("/");
      if (
        hashStudy &&
        hashStudy !== page &&
        index.studies.some((s) => s.id === hashStudy)
      ) {
        location.assign(
          new URL("studies/" + hashStudy + "/" + location.hash, site),
        );
        return;
      }
      const p = new URLSearchParams(query);
      state.view = [
        "datasets",
        "overview",
        "findings",
        "materials",
        "comments",
      ].includes(view)
        ? view
        : "datasets";
      state.dataset = model.datasets.some((d) => d.name === name)
        ? name
        : model.datasets[0].name;
      const subjects = p.get("subjects");
      state.subjects =
        subjects === "all"
          ? [...model.subjects]
          : subjects === "none"
            ? []
            : subjects
              ? subjects.split(",").filter((s) => model.subjects.includes(s))
              : model.subjects.slice(0, 3);
      for (const k of [
        "input",
        "focus",
        "rowSearch",
        "findingSearch",
        "kind",
        "evidence",
      ])
        state[k] = (p.get(k) || "").slice(0, 500);
      state.output = p.get("output") === "reference" ? "reference" : "derived";
      state.inputPage = 0;
      state.outputPage = 0;
      document.body.classList.add("study-review-page");
      await renderView();
    } catch (e) {
      if (token === mount.token)
        main.innerHTML = `<div class="error-state" role="alert"><h1>Review data could not be loaded</h1><p>${esc(e.message)}</p><button class="button" id="reload-review">Retry</button></div>`;
    }
  }
  mount.token = 0;
  async function updateSubjects(subjects) {
    state.subjects = subjects;
    state.inputPage = 0;
    state.outputPage = 0;
    save();
    byId("subject-summary").innerHTML =
      `Subjects <strong>${subjects.length} / ${model.subjects.length}</strong><span aria-hidden="true">&#9662;</span>`;
    root()
      .querySelectorAll("input[data-subject]")
      .forEach((el) => (el.checked = subjects.includes(el.dataset.subject)));
    await refreshRows();
  }
  async function copy(text) {
    try {
      await navigator.clipboard.writeText(text);
      notice("Review context copied");
    } catch {
      byId("share-fallback").hidden = false;
      const input = byId("share-url");
      input.value = text;
      input.focus();
      input.select();
      notice("Copy the selected review text");
    }
  }
  function exportCsv(kind) {
    const rows = visibleRows(kind === "input" ? inputRows : outputRows),
      meta = kind === "input" ? inputMeta() : outputMeta();
    const protect = (v) => {
      const s = String(v ?? "");
      return typeof v === "string" && /^[=+@\t\r-]/.test(s) ? "'" + s : s;
    };
    const quote = (v) => '"' + protect(v).replaceAll('"', '""') + '"';
    const csv =
      [meta.columns.map((c) => c.name), ...rows.map((r) => r.slice(1))]
        .map((r) => r.map(quote).join(","))
        .join("\r\n") + "\r\n";
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
  document.addEventListener("click", async (event) => {
    const target = event.target.closest("button,[data-line-node]");
    if (!target || !root()?.contains(target)) return;
    if (target.dataset.view) {
      navigate(target.dataset.view);
      return;
    }
    if (target.dataset.node || target.dataset.lineNode) {
      selectFocus(target.dataset.node || target.dataset.lineNode);
      return;
    }
    if (target.dataset.subjectCount) {
      const n = target.dataset.subjectCount;
      await updateSubjects(
        n === "all" ? [...model.subjects] : model.subjects.slice(0, Number(n)),
      );
      return;
    }
    if (target.dataset.dataset) {
      state.dataset = target.dataset.dataset;
      state.input = "";
      state.focus = "";
      navigate("datasets");
      return;
    }
    if (target.dataset.domainFindings) {
      state.findingSearch = target.dataset.domainFindings;
      navigate("findings");
      return;
    }
    if (target.dataset.finding) {
      const f = report.findings.find((x) => x.id === target.dataset.finding);
      state.dataset = f.dataset;
      state.focus = f.variable ? "spec." + f.variable : "";
      state.evidence = f.id;
      state.input = "";
      navigate("datasets");
      return;
    }
    if (target.dataset.page) {
      const k = target.dataset.page + "Page";
      state[k] += Number(target.dataset.step);
      paintTables();
      return;
    }
    if (target.dataset.export) {
      exportCsv(target.dataset.export);
      return;
    }
    if (target.id === "copy-view") {
      save();
      await copy(location.href);
      return;
    }
    if (target.id === "copy-comment-context") {
      await copy(commentContext());
      return;
    }
    if (target.id === "clear-selection") {
      state.focus = "";
      save();
      applyHighlight();
      return;
    }
    if (target.id === "wide-mode") {
      const on = document.body.classList.toggle("review-wide");
      target.setAttribute("aria-pressed", String(on));
      target.textContent = on ? "Restore navigation" : "Widen workspace";
      fitWorkbench();
      return;
    }
    if (target.id === "clear-findings") {
      state.findingSearch = "";
      state.kind = "";
      save();
      byId("finding-search").value = "";
      byId("finding-kind").value = "";
      byId("finding-results").innerHTML = findingCards();
      return;
    }
    if (target.id === "close-evidence") {
      state.evidence = "";
      save();
      drawer();
      return;
    }
    if (target.id === "retry-data") {
      await refreshRows();
      return;
    }
    if (target.id === "reload-review") mount();
  });
  document.addEventListener("change", async (event) => {
    const el = event.target;
    if (!root()?.contains(el)) return;
    if (el.dataset.subject) {
      await updateSubjects(
        el.checked
          ? [...state.subjects, el.dataset.subject].sort()
          : state.subjects.filter((s) => s !== el.dataset.subject),
      );
      return;
    }
    if (el.id === "dataset-select") {
      state.dataset = el.value;
      state.input = "";
      state.focus = "";
      state.evidence = "";
      save();
      await renderView();
      return;
    }
    if (el.id === "input-select") {
      state.input = el.value;
      state.inputPage = 0;
      save();
      await refreshRows();
      return;
    }
    if (el.id === "output-select") {
      state.output = el.value;
      state.outputPage = 0;
      save();
      await refreshRows();
      return;
    }
    if (el.id === "finding-kind") {
      state.kind = el.value;
      save();
      byId("finding-results").innerHTML = findingCards();
    }
  });
  document.addEventListener("input", (event) => {
    const el = event.target;
    if (!root()?.contains(el)) return;
    if (el.id === "subject-search") {
      const q = el.value.toLowerCase();
      root()
        .querySelectorAll("[data-subject-option]")
        .forEach(
          (x) =>
            (x.hidden = !x.dataset.subjectOption.toLowerCase().includes(q)),
        );
    }
    if (el.id === "record-search") {
      state.rowSearch = el.value;
      state.inputPage = 0;
      state.outputPage = 0;
      save();
      paintTables();
    }
    if (el.id === "finding-search") {
      state.findingSearch = el.value;
      save();
      byId("finding-results").innerHTML = findingCards();
    }
  });
  window.addEventListener("hashchange", mount);
  new MutationObserver(() => {
    const iframe = document.querySelector(".giscus-frame");
    if (iframe)
      iframe.contentWindow.postMessage(
        {
          giscus: {
            setConfig: {
              theme:
                document.body.dataset.mdColorScheme === "slate"
                  ? "dark"
                  : "light",
            },
          },
        },
        "https://giscus.app",
      );
  }).observe(document.body, {
    attributes: true,
    attributeFilter: ["data-md-color-scheme"],
  });
  if (typeof document$ !== "undefined") document$.subscribe(mount);
  else mount();
})();
