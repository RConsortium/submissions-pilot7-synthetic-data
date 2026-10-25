import test from "node:test";
import assert from "node:assert/strict";
import { documentSelection } from "../../../docs/assets/dashboard/source-documents.js";
import {
  readRoute,
  formatRoute,
} from "../../../docs/assets/dashboard/state.js";

const documents = [
  { path: "study/missing.pdf", available: false },
  { path: "study/define.xml", available: true },
  { path: "study/guide.pdf", available: true },
];
test("document selections allow at most two distinct declared files", () => {
  assert.deepEqual(documentSelection([], {}), []);
  assert.deepEqual(documentSelection(documents, {}), [1]);
  assert.deepEqual(
    documentSelection(documents, { document: documents[0].path }),
    [0],
  );
  assert.deepEqual(
    documentSelection(documents, {
      document: documents[2].path,
      compareDocument: documents[1].path,
    }),
    [2, 1],
  );
  assert.deepEqual(
    documentSelection(documents, {
      document: documents[1].path,
      compareDocument: documents[1].path,
    }),
    [1],
  );
  assert.deepEqual(
    documentSelection(documents, {
      document: "https://example.test/file",
      compareDocument: "unknown",
    }),
    [1],
  );
});
test("shared document comparisons retain citations and ignore legacy reading-copy modes", () => {
  const model = {
    id: "study",
    subjects: [],
    tables: {},
    datasets: [{ name: "CUSTOM", inputs: [] }],
  };
  const state = readRoute(
    "#study/materials/CUSTOM?document=study/guide.pdf&compareDocument=study/define.xml&documentSection=page-5&documentMode=reading",
    model,
  );
  assert.equal(state.document, "study/guide.pdf");
  assert.equal(state.compareDocument, "study/define.xml");
  assert.equal(state.documentSection, "page-5");
  assert.equal(state.documentMode, undefined);
  assert.deepEqual(readRoute(formatRoute(state, model), model), state);
});
