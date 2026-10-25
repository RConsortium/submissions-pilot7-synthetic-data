/** Dataset identity and cross-specification lineage, independent of DOM rendering. */
import { connectedNodes } from "./lineage.js";
export const PAGE_SIZES = [10, 25, 50, 100];
const fallbacks = {
  DM: "Demographics",
  AE: "Adverse Events",
  EX: "Exposure",
  DS: "Disposition",
  VS: "Vital Signs",
  LB: "Laboratory Test Results",
  QS: "Questionnaires",
  SV: "Subject Visits",
  SC: "Subject Characteristics",
  MH: "Medical History",
  CM: "Concomitant Medications",
  SE: "Subject Elements",
  TA: "Trial Arms",
  TE: "Trial Elements",
  TV: "Trial Visits",
  TI: "Trial Inclusion/Exclusion Criteria",
  TS: "Trial Summary",
  ADSL: "Subject-Level Analysis Dataset",
  AW: "Analysis Windows",
  PLAN: "Planned Observations",
};
export function domainName(meta) {
  return meta.domain || meta.name.replace(/-YAMAA$/, "");
}
export function domainLabel(meta) {
  const domain = domainName(meta),
    description = meta.description || fallbacks[domain];
  return description ? `${domain} - ${description}` : domain;
}
export function inputOptions(model) {
  const declared = new Set(
    model.datasets.flatMap((d) => d.inputs.map((i) => i.table)),
  );
  return Object.values(model.tables)
    .filter((t) => declared.has(t.id) || t.path.includes("/sdtm/"))
    .sort((a, b) => domainName(a).localeCompare(domainName(b)));
}
export function canonicalNode(model, domain, node) {
  if (node.startsWith("table:") || node.startsWith("out:")) return node;
  const dataset = model.datasets.find((d) => d.name === domain);
  const [alias, ...rest] = node.split("."),
    column = rest.join(".");
  if (alias === "output") return `out:${domain}.${column}`;
  const input = dataset.inputs.find((i) => i.alias === alias);
  if (input) return tableNode(model, input.table, column);
  return `${domain}/${node}`;
}
export function tableNode(model, table, column) {
  const producer = model.datasets.find((d) => d.output === table);
  return producer
    ? `out:${producer.name}.${column}`
    : `table:${table}.${column}`;
}
export function buildGraph(model, specs) {
  const graph = {};
  for (const dataset of model.datasets)
    for (const [node, inputs] of Object.entries(
      specs[dataset.name].lineage.edges,
    ))
      graph[canonicalNode(model, dataset.name, node)] = inputs.map((n) =>
        canonicalNode(model, dataset.name, n),
      );
  return graph;
}
export function upstreamNodes(graph, node) {
  const seen = new Set(),
    todo = node ? [node] : [];
  while (todo.length) {
    const next = todo.pop();
    if (seen.has(next)) continue;
    seen.add(next);
    todo.push(...(graph[next] || []));
  }
  return seen;
}
export function manualInputs(model, state) {
  const dataset = model.datasets.find((d) => d.name === state.dataset);
  return state.inputs === null
    ? [dataset.inputs[0]?.table].filter(Boolean)
    : state.inputs;
}
export function reviewPlan(model, state, graph) {
  const current = model.datasets.find((d) => d.name === state.dataset);
  const focus = state.focus
    ? canonicalNode(model, current.name, state.focus)
    : "";
  const related = connectedNodes(graph, focus),
    upstream = upstreamNodes(graph, focus);
  const options = inputOptions(model),
    manual = manualInputs(model, state);
  const linked = options
    .filter(
      (t) =>
        t.id !== current.output &&
        t.columns.some((c) => upstream.has(tableNode(model, t.id, c.name))),
    )
    .map((t) => t.id);
  const inputs = [...new Set([...manual, ...linked])]
    .filter((id) => options.some((t) => t.id === id))
    .map((id) => ({
      key: `i-${id}`,
      kind: "input",
      table: id,
      meta: model.tables[id],
      linked: linked.includes(id),
      domain: domainName(model.tables[id]),
    }));
  const outputs = [...new Set([current.name, ...state.outputs])]
    .map((name) => model.datasets.find((d) => d.name === name))
    .filter(Boolean)
    .map((d) => ({
      key: `o-${d.name}`,
      kind: "output",
      table:
        state.output === "reference" && d.reference ? d.reference : d.output,
      meta: model.tables[
        state.output === "reference" && d.reference ? d.reference : d.output
      ],
      dataset: d,
      domain: d.name,
    }));
  return {
    inputs,
    outputs,
    panels: [...inputs, ...outputs],
    related,
    upstream,
    focus,
    linked,
    manual,
  };
}
export function columnIndexes(model, panel, related, onlyRelated, focus) {
  const relevant = panel.meta.columns
    .map((c, i) => ({
      i,
      node:
        panel.kind === "output"
          ? `out:${panel.domain}.${c.name}`
          : tableNode(model, panel.table, c.name),
    }))
    .filter((c) => related.has(c.node))
    .map((c) => c.i);
  const available =
    focus && onlyRelated && relevant.length
      ? relevant
      : panel.meta.columns.map((_, i) => i);
  const subject = panel.meta.subject_index;
  return [...new Set([...(subject !== null ? [subject] : []), ...available])];
}

/** Focusing an already compared output preserves the comparison set. */
export function changePrimary(state, domain) {
  const visible = [...new Set([state.dataset, ...state.outputs])];
  if (visible.includes(domain))
    state.outputs = visible.filter((name) => name !== domain);
  state.dataset = domain;
}
