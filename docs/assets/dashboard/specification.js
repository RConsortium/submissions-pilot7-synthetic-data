/** Project parsed YAML locations onto original lines without changing source text.
 * Until a view is chosen, a layered specification shows the source that
 * writes the selected variable's rule, and otherwise its entry file. */
export function specificationView(specification, view = "", focus = "") {
  if (view === "resolved" && specification.resolved)
    return { ...specification, ...specification.resolved, inspection: true };
  let index = /^source:\d+$/.test(view) ? Number(view.slice(7)) : definingSource(specification, focus);
  if (!specification.documents?.[index]) index = 0;
  return { ...specification, ...(specification.documents?.[index] || {}), sourceIndex: index };
}

/** The index of the source that writes a variable's rule, or 0 for the entry. */
export function definingSource(specification, focus = "") {
  const name = focus.replace(/^(spec|output)\./, "");
  const path = specification.lineage?.definitions?.[name]?.path;
  return Math.max(0, (specification.documents || []).findIndex((d) => path && d.path === path));
}

export function specificationGaps(lines) {
  const gaps = new Map();
  let count = 0;
  for (const line of lines) {
    if (!line.visible) count++;
    else if (count) {
      gaps.set(line.number, count);
      count = 0;
    }
  }
  if (count) gaps.set(lines.length + 1, count);
  return gaps;
}

export function specificationLines(
  specification,
  selected,
  related,
  onlyRelated,
  inputs = new Set(),
) {
  const lines = specification.text.split("\n").map((text, i) => ({
    text,
    number: i + 1,
    nodes: [],
    kind: "",
    row: "",
    lookup: "",
    start: false,
  }));
  const assign = (span, apply) => {
    for (let i = span.start - 1; i < Math.min(span.end, lines.length); i++)
      apply(lines[i], i === span.start - 1);
  };
  for (const [name, span] of Object.entries(specification.lineage.spans)) {
    const prefix =
      span.kind === "columns"
        ? "spec."
        : span.kind === "rows"
          ? "row."
          : "intermediate.";
    const node = prefix + name;
    assign(span, (line, start) =>
      Object.assign(line, {
        nodes: [...line.nodes, node],
        kind: span.kind,
        row: span.kind === "rows" ? node : "",
        lookup: span.kind === "intermediates" ? name : "",
        start: line.start || start,
      }),
    );
  }
  const rowVariables = new Map();
  for (const [row, columns] of Object.entries(
    specification.lineage.row_derivations || {},
  )) {
    rowVariables.set(
      "row." + row,
      Object.keys(columns).map((name) => "spec." + name),
    );
    for (const [name, span] of Object.entries(columns))
      assign(span, (line, start) => {
        if (!line.derivation) line.nodes = [];
        line.nodes.push("spec." + name);
        Object.assign(line, {
          kind: "rows",
          row: "row." + row,
          derivation: true,
          start: line.derivation ? line.start || start : start,
        });
      });
  }
  const focus = specification.lineage.focus || {};
  for (const [lookup, columns] of Object.entries(
    focus.intermediate_derivations || {},
  ))
    for (const [name, span] of Object.entries(columns))
      assign(span, (line, start) => {
        if (!line.derivation) line.nodes = [];
        line.nodes.push(lookup + "." + name);
        Object.assign(line, {
          kind: "intermediates",
          lookup,
          derivation: true,
          start: line.derivation ? line.start || start : start,
        });
      });
  const active =
    onlyRelated &&
    lines.some((line) => line.nodes.some((node) => related.has(node)));
  const inputNames = new Set(inputs),
    lookups = new Set();
  for (const [name, span] of Object.entries(specification.lineage.spans))
    if (
      span.kind === "intermediates" &&
      [...related].some(
        (node) =>
          node === "intermediate." + name || node.startsWith(name + "."),
      )
    )
      lookups.add(name);
  const addDriver = (name) => {
    if (!name) return;
    if (Object.hasOwn(focus.intermediate_drivers || {}, name))
      lookups.add(name);
    else if (Object.hasOwn(focus.inputs || {}, name)) inputNames.add(name);
  };
  for (const [row, driver] of Object.entries(focus.row_drivers || {}))
    if (related.has("row." + row) || selected === "row." + row)
      addDriver(driver);
  if (!Object.keys(focus.row_drivers || {}).length) addDriver(focus.base);
  for (const lookup of lookups) addDriver(focus.intermediate_drivers?.[lookup]);
  for (const line of lines) {
    line.node =
      line.nodes.find((n) => n === selected) ||
      line.nodes.find((n) => related.has(n)) ||
      line.nodes[0] ||
      "";
    line.selected = Boolean(
      selected &&
        (line.nodes.includes(selected) ||
          line.row === selected ||
          (line.lookup && selected === "intermediate." + line.lookup)),
    );
    line.related = !line.selected && line.nodes.some((n) => related.has(n));
    line.visible = true;
    line.displayText = line.text;
    if (active && line.kind === "columns")
      line.visible = line.selected || line.related;
    if (active && line.kind === "rows") {
      const variables = rowVariables.get(line.row) || [];
      const rowRelated =
        related.has(line.row) || variables.some((n) => related.has(n));
      line.visible =
        line.selected ||
        (line.derivation ? line.related : !variables.length || rowRelated);
    }
    if (active && line.kind === "intermediates")
      line.visible =
        lookups.has(line.lookup) &&
        (!line.derivation || line.selected || line.related);
  }
  if (active) {
    const masks = new Map();
    const hide = (span) => {
      if (!span) return;
      assign(span, (line) => {
        if (span.whole_line) {
          line.visible = false;
          return;
        }
        const chars = [...line.text];
        const mask = masks.get(line.number) || new Set();
        const first = line.number === span.start ? span.start_column : 0;
        const last = line.number === span.end ? span.end_column : chars.length;
        for (let i = first; i < last; i++) mask.add(i);
        masks.set(line.number, mask);
      });
    };
    hide(focus.output_columns);
    for (const [name, span] of Object.entries(focus.inputs || {}))
      if (!inputNames.has(name)) hide(span);
    if (!inputNames.size) hide(focus.sections?.input);
    if (!lookups.size) hide(focus.sections?.intermediates);
    for (const line of lines) {
      const mask = masks.get(line.number);
      if (!mask?.size) continue;
      line.displayText = [...line.text].filter((_, i) => !mask.has(i)).join("");
      if (!line.displayText.trim()) line.visible = false;
    }
  }
  return lines;
}
