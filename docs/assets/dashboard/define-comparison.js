/** Original and generated XML with the validation job's metadata differences. */
import { esc, link } from "./ui.js";

const value = (v) => esc(JSON.stringify(v, null, 2));

export function defineComparisonView(model, resource) {
  const bundle = model.define_comparison || {},
    evidence = model.validation?.define_xml || {},
    metadata = evidence.metadata || {},
    differences = metadata.differences || [];
  const status = {
    matched: "Metadata matched",
    different: "Metadata differs",
    not_compared: "Not compared",
  }[evidence.comparison] || "Not compared";
  function pane(side, label, version) {
    const doc = bundle[side];
    return `<article class="source-pane define-pane"><h3>${label}</h3>
      <p>Define-XML ${esc(version || "version unavailable")}</p>
      <div class="source-viewer">${doc?.available ? `
        <div class="source-viewer-heading"><span>${esc(doc.view_label || "XML source")}</span>
          ${link(resource(doc.source || doc.view), "Open source", "button")}
          <a class="button" href="${esc(resource(doc.original))}" download>Download XML</a></div>
        <iframe title="${label} Define-XML" src="${esc(resource(doc.view))}" sandbox="allow-scripts"></iframe>`
        : '<p class="empty-state">Compared XML is unavailable. Run study validation to generate current evidence.</p>'}
      </div></article>`;
  }
  function detail(label, entries) {
    return entries?.length ? `<details class="define-detail"><summary>${label} (${entries.length})</summary><pre>${value(entries)}</pre></details>` : "";
  }
  function differenceTable() {
    if (!differences.length)
      return `<p>${evidence.comparison === "matched"
        ? "No metadata differences were found."
        : evidence.comparison === "different"
          ? "No comparable field differences were found. Review unsupported content and unresolved declarations below."
          : "Metadata has not been compared."}</p>`;
    return `<div class="overview-table define-differences" role="region" aria-label="Define-XML metadata differences" tabindex="0">
      <table class="review-table"><thead><tr><th scope="col">Metadata path</th>
        <th scope="col">Original</th><th scope="col">yamaa-generated</th></tr></thead>
      <tbody>${differences.map((d) => `<tr><th scope="row"><code>${esc(d.path)}</code>
        ${d.known_gap?.reason ? `<p>${esc(d.known_gap.reason)}</p>` : ""}</th>
        <td><pre>${d.reference_present === false ? "Not present" : value(d.reference)}</pre></td>
        <td><pre>${d.candidate_present === false ? "Not present" : value(d.candidate)}</pre></td></tr>`).join("")}
      </tbody></table></div>`;
  }
  return `<section class="define-comparison" aria-labelledby="define-heading">
    <h2 id="define-heading">Define-XML comparison</h2><p class="define-status" role="status">${status}</p>
    <p>Compare the original published ADaM Define-XML with the yamaa-generated file.
      Review the rendered documents side by side, or open the XML source with line numbers.</p>
    ${metadata.full_reference_reproduced === false ? '<p class="coverage-note">The original legacy Define-XML is not fully reproduced. Version conversions, unsupported content and unresolved source declarations remain separate from matches.</p>' : ""}
    <div class="source-panes" data-count="2">${pane("reference", "Original", evidence.adam_version)}${pane("candidate", "yamaa-generated", evidence.candidate_version)}</div>
    <h3>Metadata differences (${differences.length})</h3>
    <p>Metadata comparison resolves XML references and applies the recorded version mappings.
      XML byte identity, schema validity and data conformance are separate checks.</p>
    ${metadata.field_counts ? `<p>Field results: ${Object.entries(metadata.field_counts).map(([name, count]) => `${esc(name)}: ${esc(count)}`).join("; ")}.</p>` : ""}
    ${differenceTable()}
    ${detail("Unsupported content", metadata.unsupported)}
    ${detail("Unresolved source declarations", metadata.unresolved)}
    ${detail("Comparison policy", metadata.normalizations || metadata.mapping_policy)}
    ${bundle.evidence ? `<p>${link(resource(bundle.evidence), "Complete comparison evidence")}</p>` : ""}
    </section>`;
}
