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
    focus: {
      inputs: { DM: { start: 2, end: 2, whole_line: true } },
      sections: {
        input: { start: 2, end: 2, whole_line: true },
        intermediates: { start: 4, end: 6, whole_line: true },
      },
      output_columns: { start: 3, end: 3, whole_line: true },
      row_drivers: { observed: "DM", unrelated: "OTHER" },
    },
  },
};

test("focused YAML keeps related entries and drivers while hiding the output column list and unused lookups", () => {
  const lines = specificationLines(
    specification,
    "spec.AGE",
    new Set(["spec.AGE", "row.observed"]),
    true,
  );
  assert.deepEqual(
    lines.filter((l) => l.visible).map((l) => l.number),
    [1, 2, 7, 8, 9, 12, 13, 14, 15, 16, 24, 25],
  );
  assert.deepEqual(
    lines.filter((l) => l.selected).map((l) => l.number),
    [8, 9, 16],
  );
  assert.equal(lines.map((l) => l.text).join("\n"), specification.text);
  assert.equal(lines[15].node, "spec.AGE");
});

test("focused inline inputs and output retain their used fields and relevant lookup derivations", () => {
  const text = [
    "input: {QS: qs.parquet, DM: dm.parquet, EX: ex.parquet}",
    "output: {path: out.parquet, columns: [AGE, SEX]}",
    "base: DM",
    "intermediates:",
    "  - id: USED",
    "    dataset: DM",
    "    derivations:",
    "      AGE: DM.AGE",
    "      SEX: DM.SEX",
    "  - id: UNUSED",
    "    dataset: EX",
    "columns:",
    "  - name: AGE",
    "    derivation: USED.AGE",
    "  - name: SEX",
    "    derivation: UNUSED.SEX",
    "verifications:",
    "  - row_count: {min: 1}",
  ].join("\n");
  const inline = {
    text,
    lineage: {
      spans: {
        USED: { start: 5, end: 9, kind: "intermediates" },
        UNUSED: { start: 10, end: 11, kind: "intermediates" },
        AGE: { start: 13, end: 14, kind: "columns" },
        SEX: { start: 15, end: 16, kind: "columns" },
      },
      focus: {
        inputs: {
          QS: { start: 1, end: 1, start_column: 8, end_column: 24 },
          DM: { start: 1, end: 1, start_column: 24, end_column: 40 },
          EX: { start: 1, end: 1, start_column: 38, end_column: 54 },
        },
        sections: {
          input: { start: 1, end: 1, whole_line: true },
          intermediates: { start: 4, end: 11, whole_line: true },
        },
        base: "DM",
        output_columns: { start: 2, end: 2, start_column: 26, end_column: 47 },
        intermediate_drivers: { USED: "DM", UNUSED: "EX" },
        intermediate_derivations: {
          USED: { AGE: { start: 8, end: 8 }, SEX: { start: 9, end: 9 } },
        },
      },
    },
  };
  const related = new Set(["spec.AGE", "USED.AGE", "intermediate.USED"]);
  const lines = specificationLines(
    inline,
    "spec.AGE",
    related,
    true,
    new Set(["DM"]),
  );
  assert.deepEqual(
    lines.filter((l) => l.visible).map((l) => l.number),
    [1, 2, 3, 4, 5, 6, 7, 8, 12, 13, 14, 17, 18],
  );
  assert.equal(lines[0].displayText, "input: {DM: dm.parquet}");
  assert.equal(lines[1].displayText, "output: {path: out.parquet}");
  assert.equal(lines[7].node, "USED.AGE");
  assert.equal(lines.map((l) => l.text).join("\n"), text);
  const full = specificationLines(
    inline,
    "spec.AGE",
    related,
    false,
    new Set(["DM"]),
  );
  assert.equal(
    full.every((l) => l.visible),
    true,
  );
  assert.equal(full.map((l) => l.displayText).join("\n"), text);
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
