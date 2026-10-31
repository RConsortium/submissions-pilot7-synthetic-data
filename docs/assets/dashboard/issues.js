/** Concise issues and progressive evidence, rendered from the review schema. */
import { esc } from "./ui.js";

const shorten = (text, n = 240) =>
  text.length > n ? text.slice(0, n) + "..." : text;
const normalize = (text) =>
  String(text ?? "")
    .replace(/\s+/g, " ")
    .trim();
const value = (v) =>
  v == null ? "(missing)" : v === "" ? "(empty)" : String(v);
const plural = (n, noun) => `${n} ${noun}${n === 1 ? "" : "s"}`;

export function readReview(report) {
  const review = report.review;
  if (
    review?.schema_version !== 1 ||
    !Array.isArray(review.issues) ||
    !Array.isArray(review.checks) ||
    !Array.isArray(review.evidence)
  )
    throw new Error(
      "Unsupported consistency review schema. Reload the study report.",
    );
  return review;
}

export function findIssue(report, id) {
  return readReview(report).issues.find(
    (i) => i.id === id || i.aliases?.includes(id) || i.check_ids.includes(id),
  );
}

function comparisonSources(e) {
  return {
    source: e.type === "codelist" ? "Documented codelist"
      : e.method === "copy" ? "Documented source"
      : e.reading === "literal" ? "Documented rule"
      : `Alternative interpretation: ${e.reading || "see calculation details"}`,
    target: e.target === "derived" ? "yamaa output" : "generated ADaM datasets",
  };
}

export function comparisonLabel(e) {
  const { source, target } = comparisonSources(e);
  return `${source} vs ${target}`;
}

export function impactText(issue, report) {
  if (issue.impact.status === "not_measured") return "No issue-specific data comparison";
  const selected = new Set(issue.trace.filter((t) => t.role === "impact").map((t) => t.evidence_id));
  const pairs = new Map();
  for (const e of readReview(report).evidence) {
    if (!selected.has(e.id) || !["comparison", "codelist"].includes(e.type)) continue;
    const label = comparisonLabel(e);
    if (!pairs.has(label)) pairs.set(label, { subjects: new Set(), differs: false });
    const pair = pairs.get(label);
    for (const subject of e.subjects) pair.subjects.add(subject);
    pair.differs ||= e.type === "codelist" ? e.values.length > 0 : e.differ > 0;
  }
  return [...pairs].map(([label, pair]) => `${label}: ${!pair.differs
    ? "no differences in tested data"
    : pair.subjects.size ? `${plural(pair.subjects.size, "subject")} differ${pair.subjects.size === 1 ? "s" : ""}`
    : "differences observed; subject impact unavailable"}`).join("; ");
}

/** The row's one-line impact: measured differences, none in the tested data, or not measured. */
export function impactSummary(issue) {
  const { status, subject_count } = issue.impact;
  if (status === "observed") return subject_count ? `${plural(subject_count, "subject")} differ` : "Differences observed";
  if (status === "not_observed") return "No differences in tested data";
  return "Not measured";
}

export function criticalFinding(issue) {
  return issue.critical || {
    status: "needs_review",
    reason: "Criticality has not been assessed for this issue.",
  };
}

export const CRITICAL_LABELS = {
  yes: "Yes",
  no: "No",
  needs_review: "Needs review",
};

export function citation(e, preview = false, yamlOnly = false) {
  const quote = normalize(e.quote || e.context),
    snippet = shorten(quote);
  const location = e.section.startsWith("page-")
    ? `page ${e.section.slice(5)}`
    : e.section;
  let context;
  if (e.type === "specification" && (e.context_lines || yamlOnly)) {
    const first = e.context_lines?.[0] || e.lines?.[0] || 1;
    let submissionIndent = null;
    context = `<pre class="spec-lines" tabindex="0" aria-label="${esc(e.path.split("/").pop())} source context"><code>${(e.context || e.quote || "")
      .replace(/\r?\n$/, "")
      .split(/\r?\n/)
      .map((line, n) => {
        // Filter metadata only in the derivation comparison; retain original line numbers.
        if (yamlOnly) {
          const indent = line.search(/\S/);
          if (submissionIndent !== null) {
            if (indent < 0 || indent > submissionIndent) return "";
            submissionIndent = null;
          }
          if (/^\s*submission\s*:/.test(line)) {
            submissionIndent = indent;
            return "";
          }
        }
        const number = first + n,
          text = `<span class="context-line-number" aria-hidden="true">${number}</span><span class="context-line-text">${esc(line) || " "}</span>`;
        return e.lines && number >= e.lines[0] && number <= e.lines[1]
          ? `<mark class="context-line">${text}</mark>`
          : `<span class="context-line">${text}</span>`;
      })
      .join("")}</code></pre>`;
  } else context = `<blockquote>${esc(normalize(e.context))}</blockquote>`;
  const contextLocation = e.context_lines ? `Lines ${e.context_lines.join("-")}` : location;
  if (yamlOnly) return `<div class="issue-citation"><p class="quote-source">${esc("ADaM Specification: " + e.path.split("/").pop())}${location ? ", " + esc(location) : ""}</p>${context}${!e.verified ? `<p>Quote not verified: ${esc(e.reason || "source unavailable")}</p>` : ""}<p class="finding-links"><button class="text-link" data-source-evidence="${esc(e.id)}">View source</button></p></div>`;
  // A preview quotes the cited clause in full; a document's longer passage stays one click away.
  return `<div class="issue-citation"><p class="quote-source">${esc((e.type === "specification" ? "Specification: " : "Document: ") + e.path.split("/").pop())}${location ? ", " + esc(location) : ""}</p>${quote ? `<blockquote>${esc(preview ? quote : snippet)}</blockquote>` : '<p class="trace-limit">No quotation was retained for this citation; open the source to read the element.</p>'}${!e.verified ? `<p>Quote not verified: ${esc(e.reason || "source unavailable")}</p>` : ""}<p class="finding-links"><button class="text-link" data-source-evidence="${esc(e.id)}">View source</button></p>${e.context && (normalize(e.context) !== quote || (!preview && quote.length > 240) || e.type === "specification") ? `<details class="issue-context"${preview && e.type === "specification" ? " open" : ""}><summary><span>Full context</span><small>${esc(contextLocation)}</small></summary>${context}</details>` : ""}</div>`;
}

/** A rule ID that states, when selected, what its checks require. */
function ruleLegend(rule) {
  return `<details class="rule-legend" data-popover><summary>${esc(rule.id)}</summary><div class="rule-popover" role="note"><strong>${esc(rule.id)}: ${esc(rule.title)}</strong><p>${esc(rule.statement)}</p></div></details>`;
}

function patterns(e) {
  const { source, target } = comparisonSources(e);
  const pairs = e.patterns.map((p) => {
    const a = p.row === "extra" ? "(no record)" : value(p.reference);
    const b = p.row === "absent" ? "(no record)" : value(p.observed);
    const subjects = p.subjects.slice(0, 3).join(", ");
    return `<li>${esc(target)} <code>${esc(a)}</code>; ${esc(source.toLowerCase())} <code>${esc(b)}</code>: ${plural(p.count, "record")}${subjects ? ` (${esc(subjects)}${p.subjects.length > 3 ? ", ..." : ""})` : ""}</li>`;
  });
  return `<ul class="pattern-list">${pairs.slice(0, 2).join("")}</ul>${pairs.length > 2 ? `<details><summary>${pairs.length - 2} more value pairs</summary><ul class="pattern-list">${pairs.slice(2).join("")}</ul></details>` : ""}`;
}

function measurement(e, role) {
  const context =
    role === "context"
      ? " <small>Context comparison; excluded from issue impact.</small>"
      : "";
  if (e.type === "comparison") {
    return `<div class="issue-measurement"><p><strong>${esc(comparisonLabel(e))}</strong>: ${e.differ} / ${e.compared} records differ.${context}</p>${e.differ ? patterns(e) : ""}<details><summary>Calculation</summary><p>${esc(e.reading)}</p><code>${esc(e.column)}</code></details></div>`;
  }
  if (e.type === "codelist")
    return `<div class="issue-measurement"><p><strong>${esc(comparisonLabel(e))}</strong>, codelist <code>${esc(e.codelist)}</code>:${context}</p><ul class="pattern-list">${e.values.map((v) => `<li><code>${esc(value(v.value))}</code> outside the codelist: ${plural(v.count, "record")}</li>`).join("") || "<li>No values outside the codelist.</li>"}</ul></div>`;
  return `<p>${esc(e.text || "")}</p>`;
}

export function issueSearchText(issue, report) {
  const r = readReview(report),
    checks = r.checks.filter((c) => issue.check_ids.includes(c.id));
  const ids = new Set(checks.flatMap((c) => c.evidence_ids));
  return [
    issue.dataset,
    issue.variable,
    issue.title,
    issue.summary,
    issue.expected,
    issue.observed,
    issue.action,
    issue.review,
    issue.kind,
    issue.comparison,
    CRITICAL_LABELS[criticalFinding(issue).status],
    criticalFinding(issue).reason,
    ...checks.map((c) => JSON.stringify(c)),
    ...r.evidence.filter((e) => ids.has(e.id)).map((e) => JSON.stringify(e)),
  ].join(" ");
}

export function issueTrace(issue, report, { sourcesOnly = false, specificationsOnly = false, auditOnly = false, summaryOnly = false } = {}) {
  if (summaryOnly) {
    const critical = criticalFinding(issue);
    return `<div class="finding-assessment"><p>${esc(issue.summary)}</p><p><strong>Measured impact:</strong> ${esc(impactSummary(issue))}</p><p><strong>Automated criticality assessment: ${esc(CRITICAL_LABELS[critical.status])}.</strong> ${esc(critical.reason)}</p><p>Agent review: ${esc(issue.review.replaceAll("_", " "))}</p><h3>Question for you</h3><p>${esc(issue.action || "What correction or clarification does this finding require?")}</p></div>`;
  }
  const r = readReview(report),
    evidence = new Map(r.evidence.map((e) => [e.id, e]));
  const trace = issue.trace.map((t) => ({
    e: evidence.get(t.evidence_id),
    role: t.role,
  }));
  const quotes = trace.filter(({ e }) =>
    ["document", "specification"].includes(e.type),
  );
  const data = trace.filter(
    ({ e }) => !["document", "specification"].includes(e.type),
  );
  const checks = r.checks.filter((c) => issue.check_ids.includes(c.id));
  const comparisons =
    issue.expected || issue.observed
      ? `<dl class="issue-comparison">${issue.expected ? `<dt>Expected</dt><dd>${esc(issue.expected)}</dd>` : ""}${issue.observed ? `<dt>Observed</dt><dd>${esc(issue.observed)}</dd>` : ""}</dl>`
      : "";
  if (sourcesOnly || specificationsOnly) {
    const kind = sourcesOnly ? "document" : "specification";
    const selected = quotes.filter(({ e }) => e.type === kind);
    // A selected measurement may retain its translated rule only in the audit.
    // Include that exact definition, without unrelated sibling calculations.
    if (specificationsOnly) {
      const columns = new Set(data.filter(({ e }) => e.type === "comparison").map(({ e }) => e.column));
      for (const c of checks) for (const id of c.evidence_ids) {
        const e = evidence.get(id);
        if (e.type === "specification" && columns.has(e.section) && !selected.some((q) => q.e.id === id))
          selected.push({ e });
      }
    }
    const files = new Map();
    for (const { e } of selected) {
      if (!files.has(e.path)) files.set(e.path, []);
      files.get(e.path).push(e);
    }
    const orderedFiles = [...files];
    if (specificationsOnly) orderedFiles.sort(([a], [b]) =>
      Number(b.split("/").pop() === "documented-rules.yaml") -
      Number(a.split("/").pop() === "documented-rules.yaml"));
    const gap = files.size < 2
      ? `<p class="trace-limit">${files.size ? "Only one " : "No "}${sourcesOnly ? "source document" : "YAML specification"} retained for this finding. ${files.size ? "A second side is unavailable; no comparison is inferred." : "There is no retained preview to compare."}</p>`
      : "";
    return `<div class="finding-evidence">${gap}<div class="trace-source-grid" aria-label="${sourcesOnly ? "Source document" : "YAML specification"} comparison">${orderedFiles.map(([path, entries]) => `<section class="trace-source-file" aria-label="${esc(path)}"><p class="trace-scope">${esc(path)}</p>${entries.map((e) => citation(e, true, specificationsOnly)).join("")}</section>`).join("")}</div></div>`;
  }
  const audit = checks
    .map(
      (c) =>
        `<details class="issue-check"><summary>${esc(c.rule?.id || "Check")} &middot; ${esc(c.review.decision.replaceAll("_", " "))}</summary><p><code>${esc(c.id)}</code></p>${c.rule ? `<p>${esc(c.rule.statement)}</p>` : ""}<p>${esc(c.summary)}</p>${c.review.reason ? `<p><strong>Agent assessment:</strong> ${esc(c.review.reason)}</p>` : ""}<details><summary>Complete check evidence</summary>${c.evidence_ids
          .map((id) => {
            const e = evidence.get(id);
            return ["document", "specification"].includes(e.type)
              ? citation(e)
              : measurement(e, "audit");
          })
          .join("")}</details></details>`,
    )
    .join("");
  const critical = criticalFinding(issue);
  if (auditOnly)
    return `<div class="finding-evidence"><p><strong>Automated criticality assessment: ${esc(CRITICAL_LABELS[critical.status])}.</strong> ${esc(critical.reason)}</p><p>Agent review: ${esc(issue.review.replaceAll("_", " "))}</p><details class="issue-checks"><summary>${plural(checks.length, "supporting check")} and agent review</summary>${audit}</details></div>`;
  return `<div class="finding-evidence"><p><strong>Critical finding: ${esc(CRITICAL_LABELS[critical.status])}.</strong> ${esc(critical.reason)}</p><p>Agent review: ${esc(issue.review.replaceAll("_", " "))}</p><section><h4>1. Rule comparison</h4>${comparisons}${quotes.length ? quotes.map(({ e }) => citation(e)).join("") : "<p>No source statements retained for this issue.</p>"}</section><section><h4>2. Data comparison</h4><p>${esc(impactText(issue, report))}</p>${data.length ? data.map(({ e, role }) => measurement(e, role)).join("") : "<p>No issue-specific data comparison.</p>"}</section>${issue.action ? `<section><h4>3. Proposed action</h4><p>${esc(issue.action)}</p></section>` : ""}<section><details class="issue-checks"><summary>${plural(checks.length, "supporting check")} and agent review</summary>${audit}</details></section><button class="text-link" data-finding="${esc(issue.id)}">Open evidence in workspace${issue.impact.subject_count ? ` (${plural(issue.impact.subject_count, "subject")})` : ""}</button></div>`;
}

/** The variable column also identifies findings that apply to a whole dataset. */
export const findingVariable = (issue) => issue.variable || "Dataset-wide";

export function issueRow(issue, report) {
  const checks = readReview(report).checks.filter((c) =>
    issue.check_ids.includes(c.id),
  );
  const rules = [...new Map(checks.filter((c) => c.rule).map((c) => [c.rule.id, c.rule])).values()];
  const critical = criticalFinding(issue);
  const agent = `<small class="agent-review-status">Agent review: ${esc(issue.review.replaceAll("_", " "))}</small>`;
  return `<tr class="review-issue" data-finding-id="${esc(issue.id)}"><td class="issue-dataset">${esc(issue.dataset)}</td><th scope="row" class="issue-variable"><button class="text-link" data-finding="${esc(issue.id)}" aria-label="${esc(issue.dataset + (issue.variable ? "." + issue.variable : ""))}">${esc(findingVariable(issue))}</button><span class="rule-id">${rules.map(ruleLegend).join(", ")}</span></th><td class="issue-critical"><span class="sr-only">Critical finding: </span><span class="status ${critical.status === "yes" ? "attention" : "neutral"}">${esc(CRITICAL_LABELS[critical.status])}</span></td><td class="issue-type"><span class="sr-only">Type: </span><span class="status ${["conflict", "evidence", "inconsistent"].includes(issue.kind) ? "attention" : "neutral"}">${esc(issue.kind.replaceAll("_", " "))}</span></td><td class="issue-impact"><span class="sr-only">Documented rule vs data: </span>${esc(impactSummary(issue))}</td><td class="issue-summary"><h3>${esc(issue.title)}</h3><details class="issue-summary-detail"><summary>${esc(shorten(normalize(issue.summary), 130))}</summary><p>${esc(issue.summary)}</p></details>${issue.action ? `<p class="issue-question"><strong>Question for you:</strong> ${esc(issue.action)}</p>` : ""}${agent}</td><td><button class="button" data-trace-issue="${esc(issue.id)}">Start review</button><small class="human-review-status" data-human-review="${esc(issue.id)}"></small></td></tr>`;
}
