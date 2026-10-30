# Adjudicate consistency findings

You are the adjudicator of the consistency review (`workflow.md`). You did not
write the claims, and you must not see the extraction agent's reasoning beyond
what the report records. For every finding of one dataset, decide from the
sources themselves whether the finding is right. A person reads your decisions
beside the evidence; a wrong `agree` hides a real issue and a wrong `dispute`
wastes a reviewer's time, so check each one.

## Inputs

- `.build/verification/<study>/report.json`: the dataset's `findings`. Each
  has an `id`, the `rule` it cites with the rule's statement, the quoted
  `documents` and `spec` sides with their locations, the `evidence`, and a
  complete `basis` string and its compact `basis_fingerprint`.
- `.build/verification/<study>/sections/<document>.txt`: the exact text of
  every retained document, one `=== <section id>` block per section.
- The specification under review and `<study>/spec/review/<dataset>-documented-rules.yaml`.
- `.automation/consistency_review/rules.yaml`.

Do not edit claims, probes, specifications, data or documents. Write only
`<study>/spec/review/<dataset>-adjudication.json`.

## Decide each finding

Read each quote in its full section, not only the quoted span. Then:

- **CR-6, CR-7, CR-8 (clauses).** Does the document quote say what the clause
  claims, read in context? Is the specification quote the logic that
  corresponds to it? Is there a real difference, not a paraphrase of the same
  logic? For `absent_in_spec`, search the whole specification for a
  counterpart. For `absent_in_document`, search every section file for a
  statement of it; if you find one, dispute and give its location.
- **CR-5 (documented rule).** Does the literal probe column state the cited
  rule as written, no more and no less? Is each reading justified by a quote?
  Does the difference pattern in the evidence follow from the rule?
- **CR-2, CR-3, CR-4, CR-9.** Is the documented source or codelist the one
  that governs these records? Value-level metadata, derived records or a
  different dataset key can explain a difference; say so when they do.
- **CR-10, CR-11.** Is the rule really incomplete or absent? Search the
  section files before agreeing.
- **CR-1.** Is the quote absent from its location, or present with a typo? A
  CR-1 finding is never `agree` if the statement exists elsewhere; give its
  location.
- **Program lines** (a section `L<first>-L<last>` in a retained program).
  Do the cited lines compute this variable in the final value, read with the
  whole program? A program shows how the reference was computed, never what
  the documents state: dispute a finding that uses program lines as the only
  statement of a documented rule. A CR-8 finding whose `against` side is an
  `adam_program` is valid by design: it shows that the submission's own
  program departs from a document statement. Judge whether the program really
  computes that clause differently, not whether a program may be cited. A
  `reference_reimplementation` in the manifest is a later program, so judge
  only whether its lines support the reading, not the authors' intent.

Decide `agree` when the finding is right as stated, and `dispute` otherwise.
Give a reason of at most two sentences that names the section or line you
relied on. Do not add numbers the evidence does not contain.

## Output

```json
{
  "schema_version": 1,
  "dataset": "ADSL",
  "author": {"kind": "agent", "model": "<model id>", "instructions": ".automation/consistency_review/adjudicate.md", "date": "<YYYY-MM-DD>"},
  "decisions": [
    {"finding": "ADSL.TRTSDT.CR-6.1", "basis": "<copied exactly from the finding's basis_fingerprint>", "decision": "agree", "reason": "Define-XML ADSL.TRTSDT names visit 3; the specification reads MIN(EX.EXSTDTC) in EX_MINDTC."}
  ],
  "missed": [
    {"variable": "TRTEDT", "document": "spec/source/SAP.pdf", "section": "page-9", "quote": "<verbatim>", "reason": "A statement of the rule no finding cites."}
  ]
}
```

Decide every finding exactly once and copy its `basis_fingerprint` unchanged
into the decision's `basis`. It is a SHA-256 fingerprint of the complete basis;
the verifier marks a decision stale when any bound evidence changes. Legacy
decisions containing the complete basis text remain supported. For an older
report without a fingerprint, copy `basis` instead. Start the file from the
report with a short script that writes each finding's `id` and
`basis_fingerprint` (or legacy `basis`), then fill in each decision and reason
by hand. Full quotations and record evidence stay in the report. Use `missed`
for any statement of a rule that no claim cites; quote it verbatim from the
section files. A statement about which records the dataset holds, not how a
variable is derived, names the specification's row rule id (the `id` under
`rows:`, such as `treated-subjects`) as its `variable`. Keep the file ASCII.

## Re-adjudication

After a follow-up extraction round, decide only the findings whose
`adjudication.decision` in `report.json` is `stale` or `pending`; keep every
other decision in `<dataset>-adjudication.json` unchanged. Replace a stale
decision with a new one carrying the finding's current `basis_fingerprint`
(or legacy `basis`), and remove
decisions listed in the dataset's `orphaned_decisions`. Rewrite `missed` to
hold only statements that are still uncited: check each earlier entry against
the findings' quotes, and add any new one you find.

## Return

Return the counts of agreed and disputed findings, the disputed IDs with their
reasons, and the number of missed statements. In a re-adjudication, count only
the findings you decided and say which earlier missed statements are now cited.
