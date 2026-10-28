/** Human assessments stay local and are bound to the evidence reviewed. */
export const AGREEMENTS = {
  agree: "Agree",
  disagree: "Disagree",
  needs_clarification: "Need clarification",
};
export const CRITICALITIES = {
  critical: "Critical",
  not_critical: "Not critical",
  unsure: "Unsure",
};

export function evidenceSignature(issue, report) {
  const checks = report.review.checks.filter((c) => issue.check_ids.includes(c.id));
  return JSON.stringify([
    issue.id, issue.title, issue.summary, issue.expected, issue.observed, issue.action,
    checks.map((c) => [c.id, c.basis]).sort(),
    issue.trace.map((t) => [t.evidence_id, t.role]).sort(),
    report.trace_examples?.[`${issue.dataset}.${issue.variable}`] || null,
  ]);
}

export function createReviewDrafts(storage) {
  const memory = new Map();
  let available = true;
  const key = (study, issue) => `pilot7:human-review:v1:${study}:${issue.id}`;

  function load(study, issue, report) {
    const id = key(study, issue);
    let raw = memory.get(id);
    try { raw ??= JSON.parse(storage.getItem(id) || "null"); }
    catch { available = false; }
    if (!raw || raw.schema_version !== 1) raw = {};
    const signature = evidenceSignature(issue, report),
      stale = Boolean(raw.signature && raw.signature !== signature),
      agreement = Object.hasOwn(AGREEMENTS, raw.agreement) ? raw.agreement : "",
      criticality = Object.hasOwn(CRITICALITIES, raw.criticality) ? raw.criticality : "";
    return {
      schema_version: 1, signature, agreement, criticality,
      comment: typeof raw.comment === "string" ? raw.comment.slice(0, 10000) : "",
      status: !stale && raw.status === "reviewed" && agreement && criticality
        ? "reviewed" : raw.signature ? "draft" : "unreviewed",
      updated_at: typeof raw.updated_at === "string" ? raw.updated_at : "",
      stale,
    };
  }

  function save(study, issue, report, input, complete = false) {
    if (complete && (!Object.hasOwn(AGREEMENTS, input.agreement) ||
      !Object.hasOwn(CRITICALITIES, input.criticality)))
      throw Error("Choose both an agreement assessment and a criticality assessment.");
    const value = {
      schema_version: 1, signature: evidenceSignature(issue, report),
      agreement: Object.hasOwn(AGREEMENTS, input.agreement) ? input.agreement : "",
      criticality: Object.hasOwn(CRITICALITIES, input.criticality) ? input.criticality : "",
      comment: String(input.comment || "").slice(0, 10000),
      status: complete ? "reviewed" : "draft",
      updated_at: new Date().toISOString(),
    };
    const id = key(study, issue);
    memory.set(id, value);
    try { storage.setItem(id, JSON.stringify(value)); available = true; }
    catch { available = false; }
    return { ...value, stale: false };
  }

  return { load, save, get available() { return available; } };
}
