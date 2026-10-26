/** Documented-rule findings: the rule, both quoted sides, data evidence and adjudication. */
import { esc, link } from "./ui.js";

const normalize = (text) =>
  String(text ?? "")
    .replace(/\s+/g, " ")
    .trim();
const value = (v) =>
  v === null || v === undefined
    ? "(missing)"
    : v === ""
      ? "(empty)"
      : String(v);
const span = ([first, last]) =>
  first === last ? `line ${first}` : `lines ${first}-${last}`;
const where = (section) =>
  section.startsWith("page-") ? `page ${section.slice(5)}` : section;

/** The quoted clause marked inside its full citation, both escaped. */
export function highlight(context, quote) {
  const text = normalize(context),
    part = normalize(quote),
    at = part ? text.indexOf(part) : -1;
  if (at < 0 || part === text) return esc(text);
  return `${esc(text.slice(0, at))}<mark>${esc(part)}</mark>${esc(text.slice(at + part.length))}`;
}

/** Specification lines with their numbers; the quoted lines are marked. */
export function specLines(spec, marked = null) {
  const first = spec.element_lines[0];
  const lines = String(spec.excerpt || "")
    .split("\n")
    .map((line, i) => {
      const number = first + i,
        text = `<span class="line-number">${number}</span>${esc(line)}`;
      return marked && number >= marked[0] && number <= marked[1]
        ? `<mark>${text}</mark>`
        : text;
    });
  return `<pre class="spec-lines">${lines.join("\n")}</pre>`;
}

function specCell(f) {
  const spec = f.spec_quote;
  if (!spec?.element || !spec.excerpt)
    return "<p>No specification text for this finding.</p>";
  const heading =
    f.relation === "absent_in_spec"
      ? `No counterpart. The definition of <code>${esc(spec.element)}</code>:`
      : spec.quote
        ? `Quoted <code>${esc(normalize(spec.quote))}</code> in <code>${esc(spec.element)}</code>:`
        : `Definition of <code>${esc(spec.element)}</code>:`;
  const own = f.variable_spec?.excerpt
    ? `<details><summary>How ${esc(f.variable_spec.element)} is defined</summary>${specLines(f.variable_spec)}</details>`
    : "";
  return `<p>${heading}</p>${specLines(spec, spec.quote ? spec.lines : null)}${link(spec.url, "Specification " + span(spec.lines || spec.element_lines))}${own}`;
}

/** Value pairs as a list, which wraps inside the narrow evidence column. */
function patternList(result, observed) {
  const items = result.patterns.map((p) => {
    const reference = p.row === "extra" ? "(no record)" : value(p.reference),
      other = p.row === "absent" ? "(no record)" : value(p.observed),
      more =
        p.count > p.subjects.length
          ? ` and ${p.count - p.subjects.length} more`
          : "";
    return `<li>Reference <code>${esc(reference)}</code>, ${esc(observed)} <code>${esc(other)}</code>: ${p.count} record${p.count === 1 ? "" : "s"} (${esc(p.subjects.join(", "))}${more})</li>`;
  });
  const hidden =
    (result.pattern_count ?? result.patterns.length) - result.patterns.length;
  if (hidden > 0)
    items.push(
      `<li>${hidden} more value pairs; the verification report lists every pair.</li>`,
    );
  return `<ul class="pattern-list">${items.join("")}</ul>`;
}

function evidenceCell(f) {
  const e = f.evidence || {};
  let out = "";
  for (const p of e.probes || []) {
    const r = p.reference,
      reading =
        p.reading === "literal" ? "literal rule" : `reading: ${p.reading}`;
    out += `<p>Probe <code>${esc(p.column)}</code> (${esc(reading)}): ${r.differ ? `${r.differ} of ${r.compared} records differ from the reference.` : `reproduces the reference on all ${r.compared} records.`}</p>`;
    if (r.differ) out += patternList(r, "documented rule");
    if (p.definition?.excerpt)
      out += `<details><summary>How ${esc(p.column)} states the rule</summary>${specLines(p.definition)}${link(p.definition.url, "Probe " + span(p.definition.element_lines))}</details>`;
  }
  const copy = e.copy;
  if (copy?.reference?.differ) {
    out += `<p>Reference against <code>${esc(copy.source)}</code>: ${copy.reference.differ} of ${copy.reference.compared} records differ.</p>`;
    out += patternList(copy.reference, "documented source");
  } else if (copy?.reason) out += `<p>${esc(copy.reason)}.</p>`;
  if (copy && copy.spec_derivation && !copy.spec_matches)
    out += `<p>The specification derives it as <code>${esc(typeof copy.spec_derivation === "string" ? copy.spec_derivation : JSON.stringify(copy.spec_derivation))}</code>.</p>`;
  if (e.codelist?.reference?.length)
    out += `<p>Reference values outside codelist <code>${esc(e.codelist.oid)}</code>:</p><ul>${e.codelist.reference.map((v) => `<li><code>${esc(value(v.value))}</code>: ${v.count} records (${esc(v.subjects.join(", "))})</li>`).join("")}</ul>`;
  if (e.not_probed_reason)
    out += `<p>Not probed: ${esc(e.not_probed_reason)}</p>`;
  if (!out) out = `<p>${esc(f.data.summary)}</p>`;
  const n = f.subjects?.length || 0;
  return `${out}<button class="text-link" data-finding="${esc(f.id)}">Open evidence in workspace${n ? ` (${n} subject${n === 1 ? "" : "s"})` : ""}</button>`;
}

function documentCell(f) {
  if (!f.documents.length) return "<p>No retained document states this.</p>";
  return f.documents
    .map((d) => {
      const lines = d.lines
        ? `XML lines ${d.lines[0]}-${d.lines[1]}`
        : "Repository file";
      const missing = d.verified
        ? ""
        : `<p>Quote not found: ${esc(d.reason)}.</p>`;
      return `<p class="quote-source">${d.role === "against" ? "Another statement" : "Document"}: ${esc(d.name)}, ${esc(where(d.section))}</p><blockquote>${highlight(d.context, d.quote)}</blockquote>${missing}<p class="finding-links"><button class="text-link" data-document="${esc(d.path)}" data-document-section="${esc(d.section)}">View source</button>${d.repository ? " &middot; " + link(d.repository, lines) : ""}</p>`;
    })
    .join("");
}

function adjudication(a = { decision: "pending" }) {
  if (a.decision === "pending") return "pending.";
  if (a.decision === "stale")
    return `stale. The finding changed after it was judged (${a.previous}).`;
  return `${a.decision}. ${a.reason}`;
}

function statusCell(f) {
  const attention = f.kind === "conflict" || f.kind === "evidence";
  return `<span class="status ${attention ? "attention" : "neutral"}">${esc(f.status)}</span><h3>${esc(f.title)}</h3><p>${esc(f.observation)}</p>`;
}

function assessment(f) {
  const interpretations = f.interpretations?.length
    ? `<ul class="interpretations">${f.interpretations.map((i) => `<li>${esc(i)}</li>`).join("")}</ul>`
    : "";
  const question = f.question
    ? `<p><strong>Question:</strong> ${esc(f.question)}</p>`
    : "";
  return `${interpretations}${question}<p class="adjudication adjudication-${esc(f.adjudication?.decision || "pending")}"><strong>Adjudication:</strong> ${esc(adjudication(f.adjudication))}</p>`;
}

/** A compact finding with its complete trace available within the table. */
export function ruleRow(f) {
  const name = f.dataset + (f.variable ? "." + f.variable : "");
  return `<tr class="rule-finding" data-finding-id="${esc(f.id)}"><th scope="row"><button class="text-link" data-finding="${esc(f.id)}">${esc(name)}</button><span class="rule-id">${esc(f.rule.id)}</span></th><td>Documented rules</td><td>${statusCell(f)}</td><td><details class="finding-trace"><summary>Trace evidence</summary><div class="finding-evidence"><section><h4>Consistency rule</h4><blockquote class="rule-statement">${esc(f.rule.statement)}</blockquote></section><section><h4>yamaa specification</h4>${specCell(f)}</section><section><h4>Source documents</h4>${documentCell(f)}</section><section><h4>Dataset evidence</h4>${evidenceCell(f)}</section><section><h4>Review assessment</h4>${assessment(f)}</section></div></details></td></tr>`;
}

/** Text a reviewer may search for: rule, quotes and adjudication. */
export function ruleSearchText(f) {
  return [
    f.rule.id,
    f.rule.title,
    f.rule.statement,
    f.spec_quote?.quote,
    f.adjudication?.decision,
    f.adjudication?.reason,
    ...f.documents.map((d) => d.context),
  ].join(" ");
}
