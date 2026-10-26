import test from "node:test";
import assert from "node:assert/strict";
import { syntheticReport, mountSynthetic } from "../../../docs/assets/dashboard/synthetic.js";

const site = new URL("https://example.test/project-prefix/");
const dataRoot = new URL("evidence/dashboard/", site);
function model(id, staged = 0) {
  return {
    id, title: id.toUpperCase(), description: "Develop mappings <with review>",
    revision: "source-revision",
    archives: [
      { path: `${id}/data/odm/source.tar.gz`, available: true, bytes: 2048,
        files: [{ name: 'source/<ODM & "data">.xml', bytes: 4096 }] },
      { path: `${id}/data/odm/missing.tar.gz`, available: false },
    ],
    stages: [
      { id: "odm", count: 1 }, { id: "sdtm", count: staged },
      { id: "adam", count: 0 }, { id: "define", count: 0 },
    ],
  };
}

test("synthetic overview compares actual inventories and links through report headings", () => {
  const html = syntheticReport([model("kn189"), model("kn564", 2)], site, true);
  assert.match(html, /<dt>Studies<\/dt><dd>2<span>/);
  assert.match(html, /<dt>SDTM files<\/dt><dd>2<span>/);
  assert.match(html, /href="https:\/\/example.test\/project-prefix\/studies\/kn564\/">KN564<\/a>/);
  assert.match(html, /<td>1 \/ 2 available<\/td>/);
  assert.match(html, /Develop mappings &lt;with review&gt;/);
  assert.match(html, /report-status attention">Not staged/);
  assert.doesNotMatch(html, /report-provenance|Reading this report|Open study report|study-card|% matched/);
});

test("individual report preserves archive evidence without counting unavailable members", () => {
  const html = syntheticReport([model("kn189")], site, false);
  assert.match(html, /<h1>KN189 study report<\/h1>/);
  assert.match(html, /<dt>Source members<\/dt><dd>1<span>/);
  assert.match(html, /source\/&lt;ODM &amp; &quot;data&quot;&gt;\.xml/);
  assert.doesNotMatch(html, /<ODM|undefined|NaN/);
  assert.match(html, /blob\/source-revision\/kn189\/data\/odm\/source.tar.gz/);
  assert.match(html, /href="https:\/\/example.test\/project-prefix\/synthetic\/"/);
  assert.match(html, /missing.tar.gz[\s\S]*?Not staged<\/span><\/td><td>-<\/td><td>-<\/td>/);
});

test("empty inventories render explicit availability instead of comparison results", () => {
  assert.match(syntheticReport([], site, true), /No synthetic studies are configured/);
  const empty = model("new-study");
  empty.archives = [];
  empty.stages = [];
  const html = syntheticReport([empty], site, false);
  assert.match(html, /No source archives are declared/);
  assert.match(html, /<dt>Source members<\/dt><dd>0<span>/);
  assert.doesNotMatch(html, /undefined|NaN|Matched/);
});

test("mount loads every study for the overview, handles unknown IDs and avoids detached writes", async () => {
  const records = [model("kn189"), model("kn564")];
  const index = { studies: records.map((m) => ({ id: m.id, url: `synthetic/${m.id}/catalog.json` })) };
  const requests = [];
  const get = async (url) => {
    requests.push(url.href);
    return url.pathname.endsWith("index.json") ? index : records.find((m) => url.pathname.includes(m.id));
  };
  const main = { dataset: { study: "gallery" }, isConnected: true, innerHTML: "fallback" };
  await mountSynthetic(main, get, dataRoot, site);
  assert.equal(requests.length, 3);
  assert.match(main.innerHTML, /KN189/);
  assert.match(main.innerHTML, /KN564/);
  main.dataset.study = "unknown";
  await mountSynthetic(main, get, dataRoot, site);
  assert.match(main.innerHTML, /Synthetic study unavailable/);
  main.dataset.study = "kn189";
  main.innerHTML = "fallback";
  await mountSynthetic(main, async (url) => {
    const value = await get(url);
    if (!url.pathname.endsWith("index.json")) main.isConnected = false;
    return value;
  }, dataRoot, site);
  assert.equal(main.innerHTML, "fallback");
});
