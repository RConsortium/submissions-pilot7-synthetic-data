/** Stable, validated URLs are independent of study-specific rendering. */
export const sections = [
  "datasets",
  "overview",
  "findings",
  "materials",
  "comments",
];
const fields = [
  "input",
  "focus",
  "rowSearch",
  "findingSearch",
  "kind",
  "evidence",
];
export function readRoute(hash, model) {
  const [path, query = ""] = hash.replace(/^#/, "").split("?");
  const [, view, name] = path.split("/"),
    params = new URLSearchParams(query);
  const state = {
    view: sections.includes(view) ? view : "datasets",
    dataset: model.datasets.some((d) => d.name === name)
      ? name
      : model.datasets[0]?.name,
    output: params.get("output") === "reference" ? "reference" : "derived",
    inputPage: 0,
    outputPage: 0,
  };
  const requested = params.get("subjects");
  state.subjects =
    requested === "all"
      ? [...model.subjects]
      : requested === "none"
        ? []
        : requested
          ? [...new Set(requested.split(","))].filter((s) =>
              model.subjects.includes(s),
            )
          : model.subjects.slice(0, model.settings?.default_subject_count ?? 3);
  for (const field of fields)
    state[field] = (params.get(field) || "").slice(0, 500);
  return state;
}
export function formatRoute(state, model) {
  const params = new URLSearchParams(),
    defaults = model.subjects.slice(
      0,
      model.settings?.default_subject_count ?? 3,
    );
  if (
    state.subjects.length !== defaults.length ||
    !state.subjects.every((s, i) => s === defaults[i])
  )
    params.set(
      "subjects",
      state.subjects.length === model.subjects.length && state.subjects.length
        ? "all"
        : state.subjects.join(",") || "none",
    );
  for (const field of [...fields, "output"])
    if (state[field] && !(field === "output" && state[field] === "derived"))
      params.set(field, state[field]);
  return `#${model.id}/${state.view}/${state.dataset}${params.size ? "?" + params : ""}`;
}
