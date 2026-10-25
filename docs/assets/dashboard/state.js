/** Validated shareable review state, including compared datasets and table sizes. */
import { inputOptions, PAGE_SIZES } from "./review-model.js";
export const sections = ["datasets", "overview", "findings", "materials"];
const fields = ["focus", "rowSearch", "findingSearch", "kind", "evidence", "comparison", "document", "documentMode", "documentSection"];
const unique = (values) => [...new Set(values)];
export function readRoute(hash, model) {
  const [path, query = ""] = hash.replace(/^#/, "").split("?");
  const [, view, name] = path.split("/"),
    params = new URLSearchParams(query);
  const dataset =
    model.datasets.find((d) => d.name === name) || model.datasets[0];
  const options = inputOptions(model),
    inputIds = new Set(options.map((t) => t.id));
  const requested = params.get("subjects");
  const state = {
    view: view === "findings" ? "overview" : sections.includes(view) ? view : "datasets",
    dataset: dataset.name,
    output: params.get("output") === "reference" ? "reference" : "derived",
    subjects:
      requested === "all"
        ? [...model.subjects]
        : requested === "none"
          ? []
          : requested
            ? unique(requested.split(",")).filter((s) =>
                model.subjects.includes(s),
              )
            : model.subjects.slice(
                0,
                model.settings?.default_subject_count ?? 3,
              ),
    inputs: params.has("inputs")
      ? unique(params.get("inputs").split(",")).filter((id) => inputIds.has(id))
      : null,
    outputs: unique((params.get("outputs") || "").split(",")).filter(
      (n) => n !== dataset.name && model.datasets.some((d) => d.name === n),
    ),
    relatedOnly: params.get("columns") !== "all",
    pageSizes: {},
    pages: {},
  };
  if (state.inputs === null && params.get("input")) {
    const legacy = params.get("input"),
      id = dataset.inputs.find((i) => i.alias === legacy)?.table || legacy;
    if (inputIds.has(id)) state.inputs = [id];
  }
  for (const field of fields)
    state[field] = (params.get(field) || "").slice(0, 500);
  const keys = new Set([
    ...options.map((t) => `i-${t.id}`),
    ...model.datasets.map((d) => `o-${d.name}`),
  ]);
  const sizes = params.get("sizes");
  if (sizes && sizes.length <= 16000)
    try {
      const parsed = JSON.parse(sizes);
      if (parsed && typeof parsed === "object" && !Array.isArray(parsed))
        for (const [key, value] of Object.entries(parsed))
          if (keys.has(key) && PAGE_SIZES.includes(value) && value !== 10)
            state.pageSizes[key] = value;
    } catch {}
  return state;
}
export function formatRoute(state, model) {
  const p = new URLSearchParams(),
    defaults = model.subjects.slice(
      0,
      model.settings?.default_subject_count ?? 3,
    );
  if (
    state.subjects.length !== defaults.length ||
    !state.subjects.every((s, i) => s === defaults[i])
  )
    p.set(
      "subjects",
      state.subjects.length === model.subjects.length && state.subjects.length
        ? "all"
        : state.subjects.join(",") || "none",
    );
  if (state.inputs !== null) p.set("inputs", state.inputs.join(",") || "none");
  if (state.outputs.length) p.set("outputs", state.outputs.join(","));
  if (!state.relatedOnly) p.set("columns", "all");
  const sizes = Object.fromEntries(
    Object.entries(state.pageSizes)
      .filter(([, v]) => v !== 10)
      .sort(([a], [b]) => a.localeCompare(b)),
  );
  if (Object.keys(sizes).length) p.set("sizes", JSON.stringify(sizes));
  for (const field of [...fields, "output"])
    if (state[field] && !(field === "output" && state[field] === "derived"))
      p.set(field, state[field]);
  return `#${model.id}/${state.view}/${state.dataset}${p.size ? "?" + p : ""}`;
}
