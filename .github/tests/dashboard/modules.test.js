import test from "node:test";
import assert from "node:assert/strict";
import { gzipSync } from "node:zlib";
import {
  readRoute,
  formatRoute,
} from "../../../docs/assets/dashboard/state.js";
import { connectedNodes } from "../../../docs/assets/dashboard/lineage.js";
import {
  decodeResponse,
  createClient,
  loadRows,
  csvContent,
  filterRows,
} from "../../../docs/assets/dashboard/data.js";

const model = {
  id: "new-study",
  subjects: ["001", "002", "003", "004"],
  datasets: [{ name: "CUSTOM" }],
  settings: { default_subject_count: 2 },
};
test("new study defaults and shared routes validate unknown and duplicate selections", () => {
  const state = readRoute("", model);
  assert.equal(state.dataset, "CUSTOM");
  assert.deepEqual(state.subjects, ["001", "002"]);
  assert.equal(formatRoute(state, model), "#new-study/datasets/CUSTOM");
  const custom = readRoute(
    "#new-study/unknown/MISSING?subjects=004,001,004,bad&focus=output.VALUE",
    model,
  );
  assert.equal(custom.view, "datasets");
  assert.equal(custom.dataset, "CUSTOM");
  assert.deepEqual(custom.subjects, ["004", "001"]);
  assert.deepEqual(readRoute(formatRoute(custom, model), model), custom);
  assert.deepEqual(
    readRoute("#new-study/datasets/CUSTOM?subjects=none", model).subjects,
    [],
  );
  assert.deepEqual(
    readRoute("#new-study/datasets/CUSTOM?subjects=all", model).subjects,
    model.subjects,
  );
  assert.equal(
    readRoute("#new-study/datasets/CUSTOM?rowSearch=" + "x".repeat(700), model)
      .rowSearch.length,
    500,
  );
});
test("lineage supports every selection direction, cycles, and excludes unrelated siblings", () => {
  const edges = {
    "spec.A": ["DM.AGE"],
    "output.A": ["spec.A"],
    "spec.B": ["DM.AGE"],
    "output.B": ["spec.B"],
    "spec.C": ["spec.C"],
  };
  assert.deepEqual([...connectedNodes(edges, "output.A")].sort(), [
    "DM.AGE",
    "output.A",
    "spec.A",
  ]);
  assert.deepEqual([...connectedNodes(edges, "DM.AGE")].sort(), [
    "DM.AGE",
    "output.A",
    "output.B",
    "spec.A",
    "spec.B",
  ]);
  assert.deepEqual([...connectedNodes(edges, "spec.A")].sort(), [
    "DM.AGE",
    "output.A",
    "spec.A",
  ]);
  assert.deepEqual([...connectedNodes(edges, "spec.C")], ["spec.C"]);
  assert.equal(connectedNodes(edges, "").size, 0);
});
test("static transport supports raw gzip and decoded bytes, and rejects incompatible releases", async () => {
  const url = "https://example.test/project/evidence/table.json.gz",
    rows = [[0, "001", null]];
  for (const body of [gzipSync(JSON.stringify(rows)), JSON.stringify(rows)])
    assert.deepEqual(await decodeResponse(new Response(body), url), rows);
  await assert.rejects(
    decodeResponse(
      new Response('{"schema_version":2}'),
      "https://example.test/catalog.json",
    ),
    /unsupported/,
  );
  await assert.rejects(
    decodeResponse(new Response("Unavailable", { status: 503 }), url),
    /503/,
  );
  await assert.rejects(
    decodeResponse(new Response("broken"), url),
    SyntaxError,
  );
});
test("failed fetches can retry and successful concurrent reads share one request", async () => {
  let attempts = 0;
  const { get } = createClient(
    async () =>
      new Response(++attempts === 1 ? "Unavailable" : "[]", {
        status: attempts === 1 ? 503 : 200,
      }),
  );
  const url = "https://example.test/rows.json";
  await assert.rejects(get(url), /503/);
  assert.deepEqual(await Promise.all([get(url), get(url)]), [[], []]);
  assert.equal(attempts, 2);
});
test("complete selection restores original order; independent lookups remain visible with no subjects", async () => {
  const table = {
    subject_index: 0,
    chunks: [
      { url: "a", subjects: ["001"] },
      { url: "b", subjects: ["002"] },
    ],
  };
  const chunks = {
    a: [
      [2, "001", "second"],
      [0, "001", "first"],
    ],
    b: [
      [1, "002", "other"],
      [3, null, "missing"],
    ],
  };
  const get = async (url) => chunks[url];
  assert.deepEqual(
    await loadRows(get, (x) => x, table, ["001"], ["001", "002"]),
    [chunks.a[1], chunks.a[0]],
  );
  assert.deepEqual(
    (await loadRows(get, (x) => x, table, ["001", "002"], ["001", "002"])).map(
      (r) => r[0],
    ),
    [0, 1, 2, 3],
  );
  assert.deepEqual(
    await loadRows(get, (x) => x, table, [], ["001", "002"]),
    [],
  );
  assert.equal(
    (await loadRows(get, (x) => x, { ...table, subject_index: null }, [], []))
      .length,
    4,
  );
});
test("CSV exports complete selected records and protects string formulas while keeping negative numbers", () => {
  const csv = csvContent(
    [
      [0, "001", -2, "=SUM(A1)", 'line\n"quote"'],
      [1, "002", null, "-text", "@name"],
    ],
    ["ID", "N", "TEXT", "NOTE"].map((name) => ({ name })),
  );
  assert.ok(csv.includes('"001","-2","\'=SUM(A1)","line\n""quote"""'));
  assert.ok(csv.includes('"002","","\'-text","\'@name"'));
  assert.equal(csv.split("\r\n").length, 4);
});
test("record search links matching subjects across the two tables", () => {
  const input = [
      [0, "001", "headache"],
      [1, "002", "fever"],
    ],
    output = [
      [0, "001", 65],
      [1, "002", 40],
    ],
    meta = { subject_index: 0 };
  assert.deepEqual(
    filterRows(output, meta, "HEADACHE", [
      { rows: input, meta },
      { rows: output, meta },
    ]),
    [output[0]],
  );
});
