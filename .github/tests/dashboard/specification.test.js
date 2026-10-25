import test from "node:test";
import assert from "node:assert/strict";
import { specificationLines } from "../../../docs/assets/dashboard/specification.js";

const specification = {
  text: [
    "domain: ADX",
    "input: {DM: dm.parquet}",
    "output: {columns: [AGE, SEX]}",
    "intermediates:",
    "  - id: LOOKUP",
    "    filter: DM.AGE > 0",
    "columns:",
    "  - name: AGE",
    "    derivation: DM.AGE",
    "  - name: SEX",
    "    derivation: DM.SEX",
    "rows:",
    "  - id: observed",
    "    dataset: DM",
    "    derivations:",
    "      AGE: DM.AGE",
    "      SEX:",
    "        mapping:",
    "          source: DM.SEX",
    "  - id: unrelated",
    "    dataset: OTHER",
    "    derivations:",
    "      OTHER: OTHER.VALUE",
    "verifications:",
    "  - row_count: {min: 1}",
  ].join("\n"),
  lineage: {
    spans: {
      LOOKUP: { start: 5, end: 6, kind: "intermediates" },
      AGE: { start: 8, end: 9, kind: "columns" },
      SEX: { start: 10, end: 11, kind: "columns" },
      observed: { start: 13, end: 19, kind: "rows" },
      unrelated: { start: 20, end: 23, kind: "rows" },
    },
    row_derivations: {
      observed: { AGE: { start: 16, end: 16 }, SEX: { start: 17, end: 19 } },
      unrelated: { OTHER: { start: 23, end: 23 } },
    },
  },
};

test("focused YAML keeps only related column and row entries and preserves every other section", () => {
  const lines = specificationLines(
    specification,
    "spec.AGE",
    new Set(["spec.AGE", "row.observed"]),
    true,
  );
  assert.deepEqual(
    lines.filter((l) => l.visible).map((l) => l.number),
    [1, 2, 3, 4, 5, 6, 7, 8, 9, 12, 13, 14, 15, 16, 24, 25],
  );
  assert.deepEqual(
    lines.filter((l) => l.selected).map((l) => l.number),
    [8, 9, 16],
  );
  assert.equal(lines.map((l) => l.text).join("\n"), specification.text);
  assert.equal(lines[15].node, "spec.AGE");
});

test("selecting a row highlights its full rule and full/cleared views restore all entries", () => {
  const related = new Set(["row.observed", "spec.AGE", "spec.SEX"]);
  const selected = specificationLines(
    specification,
    "row.observed",
    related,
    true,
  );
  assert.deepEqual(
    selected.filter((l) => l.selected).map((l) => l.number),
    [13, 14, 15, 16, 17, 18, 19],
  );
  for (const lines of [
    specificationLines(specification, "row.observed", related, false),
    specificationLines(specification, "", new Set(), true),
  ])
    assert.equal(
      lines.every((l) => l.visible),
      true,
    );
});

test("inline row expressions sharing a source line remain visible for either variable", () => {
  const inline = {
    text: "rows:\n  - id: R\n    derivations: {AGE: DM.AGE, SEX: DM.SEX}",
    lineage: {
      spans: { R: { start: 2, end: 3, kind: "rows" } },
      row_derivations: {
        R: { AGE: { start: 3, end: 3 }, SEX: { start: 3, end: 3 } },
      },
    },
  };
  for (const name of ["AGE", "SEX"]) {
    const node = "spec." + name;
    const lines = specificationLines(
      inline,
      node,
      new Set([node, "row.R"]),
      true,
    );
    assert.equal(lines[2].visible, true);
    assert.equal(lines[2].selected, true);
    assert.equal(lines[2].node, node);
    assert.equal(lines[2].text, "    derivations: {AGE: DM.AGE, SEX: DM.SEX}");
  }
});
