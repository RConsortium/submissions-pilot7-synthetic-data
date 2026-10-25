import { esc, link } from "./ui.js";
import { createClient, loadRows } from "./data.js";
import { formatRoute, readRoute } from "./state.js";
import { createShell } from "./shell.js";
import { createWorkspace } from "./workspace.js";
import { createReport } from "./report.js";
import { createComments } from "./comments.js";
/* Static study review: complete data, declared lineage, and cited evidence. */
(() => {
  "use strict";
  const REPO =
    "https://github.com/RConsortium/submissions-pilot7-synthetic-data";
  const site = new URL("../../", import.meta.url);
  const dataRoot = new URL("evidence/dashboard/", site);
  const { get } = createClient();
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
  const PAGE = 10;
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
  function route() {
    return formatRoute(state, model);
  }
  function rowsFor(meta) {
    return loadRows(get, resource, meta, state.subjects, model.subjects);
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
  const ctx = {
    state,
    PAGE,
    REPO,
    site,
    esc,
    byId,
    root,
    resource,
    sourceUrl,
    dataset,
    source,
    inputMeta,
    outputMeta,
    link,
    save,
    notice,
    get model() {
      return model;
    },
    get report() {
      return report;
    },
    get index() {
      return index;
    },
    get specification() {
      return specification;
    },
    get inputRows() {
      return inputRows;
    },
    get outputRows() {
      return outputRows;
    },
  };
  const { frame } = createShell(ctx);
  const {
    workspace,
    applyHighlight,
    selectFocus,
    paintTables,
    fitWorkbench,
    resizeSpec,
    overview,
  } = createWorkspace(ctx);
  const { findingCards, findingsView, materialsView, drawer } =
    createReport(ctx);
  const { commentsView, commentContext, loadComments } = createComments(ctx);

  function dismissSubjects(event) {
    const picker = byId("subject-picker");
    if (picker?.open && !picker.contains(event.target)) picker.open = false;
  }
  document.addEventListener("focusin", dismissSubjects);
  document.addEventListener("pointerdown", (event) => {
    dismissSubjects(event);
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
    if (event.key === "Escape" && byId("subject-picker")?.open) {
      byId("subject-picker").open = false;
      byId("subject-summary").focus();
      event.preventDefault();
      return;
    }
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
  async function renderView() {
    const token = ++ticket,
      d = dataset();
    state.inputPage = state.outputPage = 0;
    const loaded = await get(resource(d.spec));
    if (token !== ticket) return;
    specification = loaded;
    if (!d.reference) state.output = "derived";
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
            : materialsView();
    byId("review-comments").innerHTML = commentsView();
    loadComments();
    if (state.view === "datasets") {
      await refreshRows();
      if (token === ticket) {
        drawer();
        applyHighlight(true);
      }
    }
  }
  async function mount() {
    const main = root();
    if (!main) {
      document.body.classList.remove("study-review-page");
      const [legacyStudy, legacyView] = location.hash.slice(1).split("/");
      if (legacyStudy && legacyView) {
        const catalog = await get(new URL("index.json", dataRoot));
        if (catalog.studies.some((s) => s.id === legacyStudy))
          location.replace(
            new URL("studies/" + legacyStudy + "/" + location.hash, site),
          );
      }
      return;
    }
    const token = ++mount.token;
    ++ticket;
    ++refreshRows.token;
    clearTimeout(notice.timer);
    byId("review-toast")?.classList.remove("visible");
    try {
      index = await get(new URL("index.json", dataRoot));
      if (token !== mount.token) return;
      document.body.classList.remove("study-review-page");
      const page = main.dataset.study;
      if (page === "gallery") {
        main.innerHTML = `<h1>Study review workspaces</h1><p>Explore the complete staged inputs, validated derived outputs, specifications, and submission-package sources.</p><div class="material-grid">${index.studies.map((s) => `<a class="study-card" href="${new URL("studies/" + s.id + "/", site)}"><h2>${esc(s.title)}</h2><p>${s.status === "pending" ? "Validation pending" : s.datasets + " datasets / " + s.subjects + " subjects"}</p><span>${s.findings === null ? "Not reviewed" : s.findings + " documentation observations and tasks"} &#8594;</span></a>`).join("")}</div>`;
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
      if (model.status === "pending") {
        main.innerHTML = `<h1>${esc(model.title)}</h1><div class="coverage-note"><h2>Validation pending</h2><p>${esc(model.reason)}</p>${link(model.source, "Study source")}</div>`;
        return;
      }
      const loadedReport = await get(resource(model.report));
      if (token !== mount.token) return;
      report = loadedReport;
      const [hashStudy] = location.hash.slice(1).split("?")[0].split("/");
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
  async function updateSubjects(subjects) {
    state.subjects = [...new Set(subjects)];
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
    if (target.hasAttribute("data-close-subjects")) {
      byId("subject-picker").open = false;
      byId("subject-summary").focus();
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
    if (target.hasAttribute("data-comment")) {
      byId("review-comments").scrollIntoView({
        behavior: "smooth",
        block: "start",
      });
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
