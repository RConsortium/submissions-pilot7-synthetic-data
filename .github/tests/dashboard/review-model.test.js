import test from "node:test";
import assert from "node:assert/strict";
import {
  buildGraph,
  changePrimary,
  reviewPlan,
  tableNode,
  canonicalNode,
  columnIndexes,
  domainLabel,
} from "../../../docs/assets/dashboard/review-model.js";
import {
  readRoute,
  formatRoute,
} from "../../../docs/assets/dashboard/state.js";
const columns = ["USUBJID", "ARM", "AGE"].map((name) => ({ name }));
const table = (id, domain, path, cols = columns) => ({
  id,
  name: domain,
  domain,
  path,
  columns: cols,
  subject_index: 0,
});
const model = {
  id: "study",
  subjects: ["001", "002", "003"],
  settings: { default_subject_count: 3 },
  tables: {
    dm: table("dm", "DM", "study/data/sdtm/dm.parquet"),
    adsl: table("adsl", "ADSL", "study/data/adam/adsl-yamaa.parquet"),
    ae: table("ae", "AE", "study/data/sdtm/ae.parquet", [
      { name: "USUBJID" },
      { name: "ASTDT" },
    ]),
    adae: table("adae", "ADAE", "study/data/adam/adae-yamaa.parquet", [
      { name: "USUBJID" },
      { name: "ARM" },
      { name: "ASTDT" },
    ]),
  },
  datasets: [
    {
      name: "ADSL",
      inputs: [{ alias: "DM", table: "dm" }],
      output: "adsl",
      reference: null,
    },
    {
      name: "ADAE",
      inputs: [
        { alias: "ADSL", table: "adsl" },
        { alias: "AE", table: "ae" },
      ],
      output: "adae",
      reference: null,
    },
  ],
};
const specs = {
  ADSL: {
    lineage: {
      edges: {
        "output.ARM": ["spec.ARM"],
        "spec.ARM": ["DM.ARM"],
        "output.USUBJID": ["spec.USUBJID"],
        "spec.USUBJID": ["DM.USUBJID"],
      },
    },
  },
  ADAE: {
    lineage: {
      edges: {
        "output.ARM": ["spec.ARM"],
        "spec.ARM": ["ADSL.ARM"],
        "output.ASTDT": ["spec.ASTDT"],
        "spec.ASTDT": ["AE.ASTDT", "ADSL.USUBJID"],
      },
    },
  },
};
test("lineage crosses derived input datasets without confusing equal column names", () => {
  const graph = buildGraph(model, specs),
    state = readRoute("#study/datasets/ADAE?focus=output.ARM", model),
    plan = reviewPlan(model, state, graph);
  assert.equal(canonicalNode(model, "ADAE", "ADSL.ARM"), "out:ADSL.ARM");
  assert.equal(tableNode(model, "dm", "ARM"), "table:dm.ARM");
  assert.deepEqual(new Set(plan.linked), new Set(["adsl", "dm"]));
  assert.ok(plan.related.has("table:dm.ARM"));
  assert.ok(!plan.related.has("table:dm.AGE"));
  assert.deepEqual(
    columnIndexes(
      model,
      plan.inputs.find((p) => p.table === "dm"),
      plan.related,
      true,
      plan.focus,
    ),
    [0, 1],
  );
  assert.equal(domainLabel(model.tables.dm), "DM - Demographics");
});
test("current output is not redundantly opened as an automatically linked input", () => {
  const state = readRoute("#study/datasets/ADSL?focus=output.ARM", model),
    plan = reviewPlan(model, state, buildGraph(model, specs));
  assert.deepEqual(plan.linked, ["dm"]);
  assert.equal(plan.inputs.length, 1);
});
test("manual comparisons remain visible, with independent page sizes and validated shared URLs", () => {
  const state = readRoute(
    "#study/datasets/ADAE?inputs=dm,ae,dm,unknown&outputs=ADSL,ADAE,UNKNOWN&sizes=" +
      encodeURIComponent(
        JSON.stringify({ "i-dm": 25, "o-ADSL": 100, "o-ADAE": 13, bad: 50 }),
      ),
    model,
  );
  assert.deepEqual(state.inputs, ["dm", "ae"]);
  assert.deepEqual(state.outputs, ["ADSL"]);
  assert.deepEqual(state.pageSizes, { "i-dm": 25, "o-ADSL": 100 });
  const plan = reviewPlan(model, state, buildGraph(model, specs));
  assert.deepEqual(
    plan.outputs.map((p) => p.domain),
    ["ADAE", "ADSL"],
  );
  assert.deepEqual(readRoute(formatRoute(state, model), model), state);
  assert.deepEqual(
    readRoute("#study/datasets/ADSL?inputs=none", model).inputs,
    [],
  );
  assert.deepEqual(readRoute("#study/datasets/ADSL?input=DM", model).inputs, [
    "dm",
  ]);
  assert.deepEqual(
    readRoute("#study/datasets/ADSL?sizes={broken", model).pageSizes,
    {},
  );
});

test("changing the focused specification preserves already compared outputs", () => {
  const state = { dataset: "ADSL", outputs: ["ADAE"] };
  changePrimary(state, "ADAE");
  assert.deepEqual(state, { dataset: "ADAE", outputs: ["ADSL"] });
  changePrimary(state, "ADSL");
  assert.deepEqual(state, { dataset: "ADSL", outputs: ["ADAE"] });
  changePrimary(state, "NEW");
  assert.deepEqual(state, { dataset: "NEW", outputs: ["ADAE"] });
});

test("related-column views retain declared keys and the subject identifier", () => {
  const panel = {
    kind: "input",
    table: "dm",
    meta: { ...model.tables.dm, keys: ["AGE", "MISSING"] },
  };
  assert.deepEqual(
    columnIndexes(
      model,
      panel,
      new Set(["table:dm.ARM"]),
      true,
      "out:ADSL.ARM",
    ),
    [0, 2, 1],
  );
});
