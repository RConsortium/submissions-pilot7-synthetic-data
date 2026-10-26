/** Concise issues and progressive evidence, rendered from the review schema. */
import { esc, link } from "./ui.js";

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
    (i) => i.id === id || i.check_ids.includes(id),
  );
}

export function impactText(issue) {
  const impact = issue.impact;
  if (impact.status === "not_measured") return "Impact not measured";
  if (impact.status === "not_observed") return "No differences in tested data";
  return `${plural(impact.subject_count, "subject")} with observed differences`;
}

function marked(context, quote) {
  const text = normalize(context),
    part = normalize(quote),
    at = part ? text.indexOf(part) : -1;
  if (at < 0) return esc(text);
  return `${esc(text.slice(0, at))}<mark>${esc(part)}</mark>${esc(text.slice(at + part.length))}`;
}

function citation(e, report) {
  const quote = normalize(e.quote || e.context),
    snippet = shorten(quote);
  const location = e.section.startsWith("page-")
    ? `page ${e.section.slice(5)}`
    : e.section;
  let context;
  if (e.type === "specification" && e.context_lines) {
    const first = e.context_lines[0];
    context = `<pre class="spec-lines">${e.context
      .split("\n")
      .map((line, n) => {
        const number = first + n,
          text = `<span class="line-number">${number}</span>${esc(line)}`;
        return e.lines && number >= e.lines[0] && number <= e.lines[1]
          ? `<mark>${text}</mark>`
          : text;
      })
      .join("\n")}</pre>`;
  } else context = `<blockquote>${marked(e.context, e.quote)}</blockquote>`;
  const source =
    e.type === "document" &&
    report.documents?.some((d) => d.path === e.path && d.available)
      ? `<button class="text-link" data-document="${esc(e.path)}" data-document-section="${esc(e.section)}">View source</button>`
      : "";
  const lines = e.lines ? `lines ${e.lines.join("-")}` : "Source lines";
  return `<div class="issue-citation"><p class="quote-source">${esc(e.type === "specification" ? "Specification" : e.path.split("/").pop())}${location ? ", " + esc(location) : ""}</p><blockquote>${esc(snippet)}</blockquote>${!e.verified ? `<p>Quote not verified: ${esc(e.reason || "source unavailable")}</p>` : ""}<p class="finding-links">${source}${source && e.url ? " &middot; " : ""}${e.url ? link(e.url, lines) : ""}</p>${e.context && (normalize(e.context) !== quote || quote.length > 240 || e.type === "specification") ? `<details><summary>Full context</summary>${context}</details>` : ""}</div>`;
}

function patterns(e) {
  const pairs = e.patterns.map((p) => {
    const a = p.row === "extra" ? "(no record)" : value(p.reference);
    const b = p.row === "absent" ? "(no record)" : value(p.observed);
    const subjects = p.subjects.slice(0, 3).join(", ");
    return `<li>${esc(e.target)} <code>${esc(a)}</code>; rule <code>${esc(b)}</code>: ${plural(p.count, "record")}${subjects ? ` (${esc(subjects)}${p.subjects.length > 3 ? ", ..." : ""})` : ""}</li>`;
  });
  return `<ul class="pattern-list">${pairs.slice(0, 2).join("")}</ul>${pairs.length > 2 ? `<details><summary>${pairs.length - 2} more value pairs</summary><ul class="pattern-list">${pairs.slice(2).join("")}</ul></details>` : ""}`;
}

function measurement(e, role) {
  const context =
    role === "context"
      ? " <small>Context comparison; excluded from issue impact.</small>"
      : "";
  if (e.type === "comparison") {
    const name =
      e.reading === "literal" ? "Documented rule" : e.reading || e.column;
    return `<div class="issue-measurement"><p><strong>${esc(shorten(normalize(name), 100))}</strong> vs ${esc(e.target === "derived" ? "derived output" : "reference")}: ${e.differ} / ${e.compared} records differ.${context}</p>${e.differ ? patterns(e) : ""}<details><summary>Calculation</summary><p>${esc(e.reading)}</p><code>${esc(e.column)}</code></details></div>`;
  }
  if (e.type === "codelist")
    return `<div class="issue-measurement"><p>Codelist <code>${esc(e.codelist)}</code>, ${esc(e.target)}:${context}</p><ul class="pattern-list">${e.values.map((v) => `<li><code>${esc(value(v.value))}</code> outside the codelist: ${plural(v.count, "record")}</li>`).join("") || "<li>No values outside the codelist.</li>"}</ul></div>`;
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
    ...checks.map((c) => JSON.stringify(c)),
    ...r.evidence.filter((e) => ids.has(e.id)).map((e) => JSON.stringify(e)),
  ].join(" ");
}

export function issueTrace(issue, report) {
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
      ? `<section><h4>Rule comparison</h4><dl class="issue-comparison">${issue.expected ? `<dt>Expected</dt><dd>${esc(issue.expected)}</dd>` : ""}${issue.observed ? `<dt>Observed</dt><dd>${esc(issue.observed)}</dd>` : ""}</dl></section>`
      : "";
  const audit = checks
    .map(
      (c) =>
        `<details class="issue-check"><summary>${esc(c.rule?.id || "Check")} &middot; ${esc(c.review.decision.replaceAll("_", " "))}</summary><p><code>${esc(c.id)}</code></p>${c.rule ? `<p>${esc(c.rule.statement)}</p>` : ""}<p>${esc(c.summary)}</p>${c.review.reason ? `<p><strong>Agent assessment:</strong> ${esc(c.review.reason)}</p>` : ""}<details><summary>Complete check evidence</summary>${c.evidence_ids
          .map((id) => {
            const e = evidence.get(id);
            return ["document", "specification"].includes(e.type)
              ? citation(e, report)
              : measurement(e, "audit");
          })
          .join("")}</details></details>`,
    )
    .join("");
  return `<div class="finding-evidence">${comparisons}${quotes.length ? `<section><h4>Source statements</h4>${quotes.map(({ e }) => citation(e, report)).join("")}</section>` : ""}<section><h4>Data comparison</h4>${data.length ? data.map(({ e, role }) => measurement(e, role)).join("") : "<p>No issue-specific data comparison.</p>"}</section>${issue.action ? `<section><h4>Proposed action</h4><p>${esc(issue.action)}</p></section>` : ""}<section><details class="issue-checks"><summary>${plural(checks.length, "supporting check")} and agent review</summary>${audit}</details></section><button class="text-link" data-finding="${esc(issue.id)}">Open evidence in workspace${issue.impact.subject_count ? ` (${plural(issue.impact.subject_count, "subject")})` : ""}</button></div>`;
}

export function issueRow(issue, report) {
  const checks = readReview(report).checks.filter((c) =>
    issue.check_ids.includes(c.id),
  );
  const rules = [...new Set(checks.map((c) => c.rule?.id).filter(Boolean))];
  return `<tr class="review-issue" data-finding-id="${esc(issue.id)}"><th scope="row"><button class="text-link" data-finding="${esc(issue.id)}">${esc(issue.dataset + (issue.variable ? "." + issue.variable : ""))}</button><span class="rule-id">${esc(rules.join(", "))}</span></th><td><h3>${esc(issue.title)}</h3><p>${esc(issue.summary)}</p></td><td><span class="status ${["conflict", "evidence", "inconsistent"].includes(issue.kind) ? "attention" : "neutral"}">${esc(issue.kind.replaceAll("_", " "))}</span><p>${esc(impactText(issue))}</p><small>Agent review: ${esc(issue.review.replaceAll("_", " "))}</small><small>${plural(checks.length, "supporting check")}</small></td><td><details class="finding-trace"><summary>Trace evidence</summary>${issueTrace(issue, report)}</details></td></tr>`;
}
