/** Project parsed YAML locations onto original lines without changing source text. */
export function specificationLines(
  specification,
  selected,
  related,
  onlyRelated,
) {
  const lines = specification.text.split("\n").map((text, i) => ({
    text,
    number: i + 1,
    nodes: [],
    kind: "",
    row: "",
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
  const active =
    onlyRelated &&
    lines.some((line) => line.nodes.some((node) => related.has(node)));
  for (const line of lines) {
    line.node =
      line.nodes.find((n) => n === selected) ||
      line.nodes.find((n) => related.has(n)) ||
      line.nodes[0] ||
      "";
    line.selected =
      Boolean(selected) &&
      (line.nodes.includes(selected) || line.row === selected);
    line.related = !line.selected && line.nodes.some((n) => related.has(n));
    line.visible = true;
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
  }
  return lines;
}
