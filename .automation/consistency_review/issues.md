# Group consistency findings into issues

You are the issue author of the consistency review (`workflow.md`). The
verifier has decided every finding of one dataset and the adjudicator has
judged them. You explain them: group the findings into issues a
biostatistician can read in a minute, each one traced to the documents, the
specification and, where one is retained, the program that computed the
reference. You do not judge findings, and you never change one.

## Inputs

- `.build/verification/<study>/report.json`: the dataset's `findings`, each
  with its `id`, `rule`, quoted `documents` and `spec` sides, `evidence`,
  `adjudication` and `basis_fingerprint`.
- `.build/verification/<study>/sections/<document>.txt`: the citable text.
- `<study>/spec/review/<dataset>-claims.json` and `<dataset>-documented-rules.yaml`.
- `.github/schemas/review-issues.schema.json`, the file format, and
  `cdiscpilot01/spec/review/adsl-issues.json`, a complete example.

Write `<study>/spec/review/<dataset>-issues.json` for the complete audit grouping.
Record the separately reviewed publication scope in
`<study>/spec/review/<dataset>-publication.json`, following
`.github/schemas/review-publication.schema.json`.

## Publication scope

The reviewer-facing findings compare actual ADaM data and metadata with the
original submitted Define-XML. Keep observed discrepancies and verified
contradictory or incomplete rules that prevent assessment. A YAML or program
difference alone stays in the audit. A program may explain an observed result;
it does not establish that a documented requirement was violated.

Inspect original Origin declarations and value-level ItemDefs before declaring
a rule undocumented. A reader or probe limitation is not missing documentation.
Do not turn numeric SignificantDigits metadata into an unstated rounding
algorithm. Put an unavailable referenced SAP or external dictionary in coverage.

Use one publication group for checks describing the same variable and the same
required correction. Preserve independent data, type and length discrepancies
as separate findings. A clarification must not present an assumed probe reading
as measured literal impact. Bind decisions to the original XML hash and current
check basis; changed evidence requires another review.

## Group

1. **Inventory.** `checks` maps every finding `id` of the dataset to its
   `basis_fingerprint` without the `sha256:` prefix. Start it with a short
   script; a missing or stale entry blocks publication.
2. **One issue per problem a reviewer would fix once.** Group the findings of
   one variable that one correction resolves, such as a CR-5 rule difference
   and the CR-6 clause that explains it. Never group across variables. A
   finding that stands alone is its own issue. Every finding belongs to
   exactly one issue; do not set `allow_ungrouped`.
3. **Write for a reader who has not seen the finding.** ASCII only.
   - `title` (at most 96 characters): the problem in plain words, such as
     "Threshold distance formula omits absolute values". Not a rule ID.
   - `summary` (at most 240): what differs, between which sources.
   - `expected`: what the documents state, quoted or closely paraphrased.
   - `observed`: what the specification, reference or program does. A
     count must be one the report states for a selected data selector;
     write "every record" or "all 254 records" only when the evidence says so.
   - `action`: the decision or correction a person should make.
4. **Trace the sources.** Add `citations` selecting, for each linked check,
   the document quote and specification quote that show the problem, and the
   program lines when the check cites a program (`type` `document`, `section`
   `L<first>-L<last>`). A reader should reach the original statement and the
   original code in one step.
5. **Select the data.** For a CR-5 check, select the literal probe against
   the reference as `impact` and each reading probe as `context`, so the
   review shows which reading reproduces the reference. Select copy and
   codelist evidence the same way.
6. **Criticality.** Leave `critical` out unless you can state, from the
   report's own evidence, why the default assessment is wrong; then give
   `status` and a one-sentence `reason`.

A reimplementation (manifest role `reference_reimplementation`) shows how the
reference values can be produced, not what the authors intended. Say which
program it is when an issue relies on it.

## Return

Return the number of published grouped findings, separate coverage gaps and raw
supporting checks. List excluded audit observations and the reason. Do not use
the raw audit total as the headline finding count.
