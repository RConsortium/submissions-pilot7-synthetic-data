import { esc, link } from "./ui.js";
import { createClient, loadRows } from "./data.js";
import { readRoute, formatRoute } from "./state.js";
import {
  buildGraph,
  changePrimary,
  canonicalNode,
  inputOptions,
  reviewPlan,
  PAGE_SIZES,
} from "./review-model.js";
import { createShell } from "./shell.js";
import { createWorkspace } from "./workspace.js";
import { createReport } from "./report.js";
import { findIssue } from "./issues.js";
import { createTraceReview } from "./trace-review.js";
import { createSourceDocuments } from "./source-documents.js";
import { defineComparisonView } from "./define-comparison.js";
import { createComments } from "./comments.js";
import { createResizing } from "./resize.js";
import { mountSynthetic } from "./synthetic.js";
import { developmentReport, mountDevelopment } from "./synthetic-development.js";

(() => {
  const REPO =
    "https://github.com/RConsortium/submissions-pilot7-synthetic-data";
  const site = new URL("../../", import.meta.url),
    dataRoot = new URL("evidence/dashboard/", site),
    { get } = createClient();
  let ticket = 0,
    model = null,
    specification = null,
    specifications = {},
    graph = {},
    plan = null,
    report = null,
    index = null;
  let development = null;
  let rowsByTable = new Map(),
    rowErrors = new Map(),
    rowsLoading = false;
  const state = {},
    layouts = new Map();
  const root = () => document.getElementById("study-dashboard"),
    byId = (id) => document.getElementById(id);
  const resource = (path) => new URL(`${model.id}/${path}`, dataRoot).href;
  const sourceUrl = (path, line) =>
    `${REPO}/blob/${model.revision}/${path}${line ? "#L" + line : ""}`;
  const dataset = () => model.datasets.find((d) => d.name === state.dataset);
  function save() {
    if (model) history.replaceState(null, "", formatRoute(state, model));
  }
  function navigate(view) {
    traceReview.close(false);
    state.view = view;
    location.hash = formatRoute(state, model);
  }
  const ctx = {
    REPO,
    site,
    state,
    esc,
    link,
    root,
    byId,
    resource,
    sourceUrl,
    dataset,
    save,
    get model() {
      return model;
    },
    get index() {
      return index;
    },
    get report() {
      return report;
    },
    get specification() {
      return specification;
    },
    get graph() {
      return graph;
    },
    get plan() {
      return plan;
    },
    get rowsByTable() {
      return rowsByTable;
    },
    get rowsLoading() {
      return rowsLoading;
    },
    get rowErrors() {
      return rowErrors;
    },
    get layout() {
      if (!layouts.has(model.id))
        layouts.set(model.id, {
          spec: 25,
          inputs: null,
          panels: {},
          columns: {},
        });
      return layouts.get(model.id);
    },
  };
  const { frame } = createShell(ctx),
    { workspace, applyHighlight, paintTables, fitWorkbench, copySpecification } =
      createWorkspace(ctx);
  const { findingRows, findingsView, drawer } = createReport(ctx),
    comments = createComments(ctx),
    { commentsView, loadComments } = comments;
  const traceReview = createTraceReview(ctx, comments);
  const sourceDocuments = createSourceDocuments(ctx),
    { materialsView } = sourceDocuments;
  const resizing = createResizing(ctx, fitWorkbench);
  function updatePlan() {
    plan = reviewPlan(model, state, graph);
  }
  async function refreshRows() {
    const token = ++refreshRows.token,
      requested = plan,
      subjects = [...state.subjects],
      allSubjects = model.subjects;
    const urlFor = (path) => new URL(`${model.id}/${path}`, dataRoot).href;
    for (const region of root()?.querySelectorAll("[data-table-for]") || [])
      region.innerHTML =
        '<p class="loading" role="status">Loading selected study records...</p>';
    rowsLoading = true;
    for (const footer of root()?.querySelectorAll("[data-footer-for]") || [])
      footer.textContent = "Loading records...";
    const ids = [...new Set(requested.panels.map((p) => p.table))];
    const results = await Promise.allSettled(
      ids.map((id) =>
        loadRows(get, urlFor, model.tables[id], subjects, allSubjects),
      ),
    );
    if (token !== refreshRows.token || state.view !== "datasets") return;
    rowsLoading = false;
    rowsByTable = new Map();
    rowErrors = new Map();
    for (let i = 0; i < results.length; i++) {
      const r = results[i];
      if (r.status === "fulfilled") rowsByTable.set(ids[i], r.value);
      else rowErrors.set(ids[i], r.reason.message || String(r.reason));
    }
    paintTables();
  }
  refreshRows.token = 0;
  async function redrawWorkspace(scroll = false, remember = true) {
    const token = ++ticket,
      offset = byId("spec-scroll")?.scrollTop || 0;
    const opened = [...root().querySelectorAll("[data-popover][open]")].map(
      (el) => el.id,
    );
    if (remember) resizing.rememberPanels();
    updatePlan();
    byId("view-content").innerHTML = workspace();
    for (const id of opened) if (byId(id)) byId(id).open = true;
    byId("spec-scroll").scrollTop = offset;
    await refreshRows();
    if (token === ticket) {
      drawer();
      applyHighlight(scroll);
    }
  }
  async function renderView() {
    traceReview.close(false);
    resizing.rememberPanels();
    const token = ++ticket;
    specification = specifications[state.dataset];
    state.pages = {};
    updatePlan();
    root().innerHTML = frame();
    byId("view-content").innerHTML =
      state.view === "datasets"
        ? workspace()
        : state.view === "development" && development
          ? developmentReport(development, dataRoot)
          : state.view === "overview"
            ? findingsView()
            : state.view === "define"
              ? defineComparisonView(model, resource)
              : materialsView();
    if (state.view === "development" && development)
      mountDevelopment(byId("view-content"), development);
    byId("review-comments").innerHTML = commentsView();
    loadComments();
    traceReview.refreshRows();
    if (state.view === "datasets") {
      await refreshRows();
      if (token === ticket) {
        drawer();
        applyHighlight(true);
      }
    }
  }
  async function mount() {
    traceReview.close(false);
    const token = ++mount.token;
    ++ticket;
    ++refreshRows.token;
    const main = root(),
      synthetic = byId("synthetic-dashboard");
    document.body.classList.remove("study-review-page");
    if (synthetic) {
      try {
        await mountSynthetic(synthetic, get, dataRoot, site);
      } catch (e) {
        if (synthetic.isConnected)
          synthetic.innerHTML = `<div class="error-state" role="alert">${esc(e.message)}<button id="reload-synthetic">Retry</button></div>`;
      }
      return;
    }
    if (!main) {
      const [study, view] = location.hash.slice(1).split("/");
      if (study && view) {
        const catalog = await get(new URL("index.json", dataRoot));
        if (
          token === mount.token &&
          [...catalog.studies, ...(catalog.synthetic_studies || []).filter((s) => s.workspace)].some((s) => s.id === study)
        )
          location.replace(
            new URL("studies/" + study + "/" + location.hash, site),
          );
      }
      return;
    }
    try {
      const loadedIndex = await get(new URL("index.json", dataRoot));
      if (token !== mount.token) return;
      index = loadedIndex;
      index = { ...index, studies: [...index.studies,
        ...(index.synthetic_studies || []).filter((s) => s.workspace && !index.studies.some((p) => p.id === s.id))] };
      const id = main.dataset.study;
      if (!index.studies.some((s) => s.id === id)) {
        main.innerHTML =
          "<h1>SDTM -&gt; ADaM pending</h1><p>This study has no validated artifact bundle.</p>";
        return;
      }
      const loadedModel = await get(new URL(id + "/catalog.json", dataRoot));
      if (token !== mount.token) return;
      const loadedDevelopment = loadedModel.development ? await get(new URL(loadedModel.development, dataRoot)) : null;
      if (token !== mount.token) return;
      model = loadedModel;
      development = loadedDevelopment;
      if (model.status === "pending") {
        main.innerHTML = `<h1>${esc(model.title)}</h1><div class="coverage-note"><h2>Validation pending</h2><p>${esc(model.reason)}</p>${link(`${REPO}/tree/${model.revision}/${model.id}`, "Study source")}</div>`;
        return;
      }
      const [loadedReport, loadedSpecs] = await Promise.all([
        get(resource(model.report)),
        Promise.all(
          model.datasets.map(async (d) => [
            d.name,
            await get(resource(d.spec)),
          ]),
        ),
      ]);
      if (token !== mount.token) return;
      report = loadedReport;
      specifications = Object.fromEntries(loadedSpecs);
      graph = buildGraph(model, specifications);
      const [hashStudy] = location.hash.slice(1).split("?")[0].split("/");
      if (
        hashStudy &&
        hashStudy !== id &&
        index.studies.some((s) => s.id === hashStudy)
      ) {
        location.assign(
          new URL("studies/" + hashStudy + "/" + location.hash, site),
        );
        return;
      }
      Object.assign(state, readRoute(location.hash, model));
      document.body.classList.add("study-review-page");
      await renderView();
      if (location.hash.split("?")[0].split("/")[1] === "comments")
        byId("review-comments")?.scrollIntoView({ block: "start" });
    } catch (e) {
      if (token === mount.token)
        main.innerHTML = `<div class="error-state" role="alert"><h1>Review data could not be loaded</h1><p>${esc(e.message)}</p><button class="button" id="reload-review">Retry</button></div>`;
    }
  }
  mount.token = 0;
  function dismissPickers(event) {
    for (const picker of root()?.querySelectorAll("[data-popover][open]") || [])
      if (!picker.contains(event.target)) picker.open = false;
  }
  document.addEventListener("focusin", dismissPickers);
  document.addEventListener("pointerdown", (event) => {
    dismissPickers(event);
    if (root()) resizing.pointer(event);
  });
  document.addEventListener("keydown", (event) => {
    if (!root()) return;
    if (traceReview.isOpen) return;
    if (event.key === "Escape") {
      const opened = [...root().querySelectorAll("[data-popover][open]")];
      for (const picker of opened) picker.open = false;
      if (opened.length) {
        opened[0].querySelector("summary").focus();
        event.preventDefault();
        return;
      }
    }
    if (sourceDocuments.keyboard(event)) return;
    resizing.keyboard(event);
  });
  window.addEventListener("resize", fitWorkbench);
  async function updateSubjects(subjects) {
    state.subjects = [...new Set(subjects)];
    state.pages = {};
    save();
    byId("subject-summary").innerHTML =
      `Subjects <strong>${state.subjects.length} / ${model.subjects.length}</strong><span aria-hidden="true">&#9662;</span>`;
    for (const el of root().querySelectorAll("input[data-subject]"))
      el.checked = state.subjects.includes(el.dataset.subject);
    await refreshRows();
  }
  document.addEventListener("click", async (event) => {
    if (event.target.closest("#reload-synthetic")) {
      mount();
      return;
    }
    const target = event.target.closest("button,[data-line-node]");
    if (!target || !root()?.contains(target)) return;
    if (target.dataset.traceIssue) {
      traceReview.open(target.dataset.traceIssue, target);
      return;
    }
    if (sourceDocuments.click(target)) return;
    if (target.id === "copy-specification") {
      await copySpecification();
      return;
    }
    if (target.dataset.view) {
      navigate(target.dataset.view);
      return;
    }
    if (target.dataset.node || target.dataset.lineNode) {
      const raw = target.dataset.node || target.dataset.lineNode,
        selected =
          target.dataset.canonical || canonicalNode(model, state.dataset, raw),
        clear = selected === plan.focus;
      const owner = target.dataset.outputDataset;
      if (owner && owner !== state.dataset) changePrimary(state, owner);
      state.focus = clear ? "" : raw;
      // A new selection shows its defining source again unless the model is chosen.
      if (state.focus && state.specView !== "resolved") state.specView = "";
      state.relatedOnly = true;
      state.pages = {};
      save();
      if (owner && specification.domain !== owner) await renderView();
      else await redrawWorkspace(target.closest(".spec-line")?.id || true);
      return;
    }
    if (target.hasAttribute("data-close-subjects")) {
      byId("subject-picker").open = false;
      byId("subject-summary").focus();
      return;
    }
    if (target.hasAttribute("data-subject-count")) {
      const count = target.dataset.subjectCount;
      await updateSubjects(
        count === "all"
          ? [...model.subjects]
          : model.subjects.slice(0, Number(count)),
      );
      return;
    }
    if (target.dataset.dataset) {
      state.dataset = target.dataset.dataset;
      state.inputs = null;
      state.outputs = [];
      state.focus = "";
      state.evidence = "";
      navigate("datasets");
      return;
    }
    if (target.dataset.domainFindings) {
      state.findingSearch = target.dataset.domainFindings;
      navigate("overview");
      return;
    }
    if (target.dataset.finding) {
      const f = findIssue(report, target.dataset.finding);
      if (!f) return;
      state.dataset = f.dataset;
      state.focus = f.variable ? "spec." + f.variable : "";
      state.evidence = f.id;
      // Context comparisons never select subjects as an issue's measured impact.
      const subjects = f.impact.subjects.filter((s) =>
        model.subjects.includes(s),
      );
      if (subjects.length) {
        state.subjects = subjects;
        state.pages = {};
      }
      state.inputs = null;
      state.outputs = [];
      state.output = "derived";
      navigate("datasets");
      return;
    }
    if (target.dataset.document) {
      state.document = target.dataset.document;
      state.documentSection = target.dataset.documentSection || "";
      navigate("materials");
      return;
    }
    if (target.dataset.panelPage) {
      state.pages[target.dataset.panelPage] =
        (state.pages[target.dataset.panelPage] || 0) +
        Number(target.dataset.step);
      paintTables();
      return;
    }
    if (target.dataset.panelSize) {
      resizing.panel(target.dataset.panelKey, Number(target.dataset.panelSize));
      return;
    }
    if (target.hasAttribute("data-comment")) {
      byId("review-comments").scrollIntoView({
        behavior: "smooth",
        block: "start",
      });
      return;
    }
    if (target.id === "reset-layout") {
      Object.assign(ctx.layout, {
        spec: 25,
        inputs: null,
        panels: {},
        columns: {},
      });
      await redrawWorkspace(false, false);
      return;
    }
    if (target.id === "clear-selection") {
      state.focus = "";
      state.pages = {};
      save();
      await redrawWorkspace();
      return;
    }
    if (target.id === "clear-findings") {
      state.findingSearch = "";
      state.kind = "";
      state.comparison = "";
      state.critical = "";
      save();
      byId("finding-search").value = "";
      byId("finding-kind").value = "";
      byId("finding-comparison").value = "";
      byId("finding-critical").value = "";
      byId("finding-results").innerHTML = findingRows();
      traceReview.refreshRows();
      return;
    }
    if (target.id === "close-evidence") {
      state.evidence = "";
      save();
      drawer();
      return;
    }
    if (target.hasAttribute("data-retry")) {
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
      resizing.rememberPanels();
      changePrimary(state, el.value);
      state.focus = "";
      state.evidence = "";
      save();
      await renderView();
      return;
    }
    if (el.id === "spec-view") {
      state.specView = el.value;
      save();
      await redrawWorkspace(true, false);
      return;
    }
    if (el.hasAttribute("data-input-dataset")) {
      const id = el.dataset.inputDataset;
      if (!inputOptions(model).some((t) => t.id === id)) return;
      state.inputs = el.checked
        ? [...new Set([...plan.manual, id])]
        : plan.manual.filter((n) => n !== id);
      state.pages = {};
      save();
      await redrawWorkspace();
      return;
    }
    if (el.hasAttribute("data-output-dataset")) {
      const id = el.dataset.outputDataset;
      if (!model.datasets.some((d) => d.name === id)) return;
      state.outputs = el.checked
        ? [...new Set([...state.outputs, id])]
        : state.outputs.filter((n) => n !== id);
      state.pages = {};
      save();
      await redrawWorkspace();
      return;
    }
    if (el.id === "output-select") {
      state.output = el.value === "reference" ? "reference" : "derived";
      state.pages = {};
      save();
      await redrawWorkspace();
      return;
    }
    if (el.id === "column-mode") {
      state.relatedOnly = el.value === "related";
      save();
      paintTables();
      applyHighlight(true);
      return;
    }
    if (el.hasAttribute("data-page-size")) {
      const size = Number(el.value);
      if (!PAGE_SIZES.includes(size)) return;
      state.pageSizes[el.dataset.pageSize] = size;
      state.pages[el.dataset.pageSize] = 0;
      save();
      paintTables();
      return;
    }
    if (
      ["finding-kind", "finding-comparison", "finding-critical"].includes(el.id)
    ) {
      state[
        {
          "finding-kind": "kind",
          "finding-comparison": "comparison",
          "finding-critical": "critical",
        }[el.id]
      ] = el.value;
      save();
      byId("finding-results").innerHTML = findingRows();
      traceReview.refreshRows();
    }
  });
  document.addEventListener("input", (event) => {
    const el = event.target;
    if (!root()?.contains(el)) return;
    if (el.id === "subject-search") {
      const q = el.value.toLowerCase();
      for (const option of root().querySelectorAll("[data-subject-option]"))
        option.hidden = !option.dataset.subjectOption.toLowerCase().includes(q);
    }
    if (el.id === "record-search") {
      state.rowSearch = el.value;
      state.pages = {};
      save();
      paintTables();
    }
    if (el.id === "finding-search") {
      state.findingSearch = el.value;
      save();
      byId("finding-results").innerHTML = findingRows();
      traceReview.refreshRows();
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
