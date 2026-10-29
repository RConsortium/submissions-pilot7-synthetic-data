// Subject comparisons preserve typed values and distinguish unavailable cells.
import test from "node:test";
import assert from "node:assert/strict";
import { subjectDifferenceCells } from "../../../docs/assets/dashboard/trace-review.js";
const value = (v) => ({ present: true, column_present: true, value: v });

test("only differing document calculations and their reference are highlighted", () => {
  const html = subjectDifferenceCells({ reference: value(1), derived: value(999),
    calculations: { same: value(1), different: value(2) } },
  [{ column: "same" }, { column: "different" }]);
  assert.equal((html.match(/class="trace-cell-difference"/g) || []).length, 2);
  assert.match(html, /<td>1<\/td>/);
  assert.doesNotMatch(html, /999/);
});

test("blank, missing, absent variables, absent records and typed values differ", () => {
  for (const [a, b, count] of [
    [value(null), value(null), 0], [value(""), value(null), 2],
    [value(1), value("1"), 2],
    [value(null), { present: false, value: null }, 2],
    [value(null), { present: true, column_present: false, value: null }, 2],
    [{ present: false }, { present: false }, 0],
  ]) {
    const html = subjectDifferenceCells({ reference: a, calculations: { rule: b } }, [{ column: "rule" }]);
    assert.equal((html.match(/class="trace-cell-difference"/g) || []).length, count);
  }
});
