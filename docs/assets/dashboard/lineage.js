/** Traverse declared value and context dependencies without following siblings. */
export function connectedNodes(edges, selection) {
  if (!selection) return new Set();
  const upstream = new Set(),
    downstream = new Set();
  const inverse = new Map();
  for (const [node, inputs] of Object.entries(edges))
    for (const input of inputs) {
      if (!inverse.has(input)) inverse.set(input, []);
      inverse.get(input).push(node);
    }
  function walk(node, adjacent, seen) {
    if (seen.has(node)) return;
    seen.add(node);
    for (const next of adjacent(node)) walk(next, adjacent, seen);
  }
  walk(selection, (n) => edges[n] || [], upstream);
  walk(selection, (n) => inverse.get(n) || [], downstream);
  return new Set([...upstream, ...downstream]);
}
