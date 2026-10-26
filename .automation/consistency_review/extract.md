# Extract derivation claims

You are the extraction agent of the consistency review (`workflow.md`). For the
variables you are given, find every statement of each derivation rule in the
retained submission documents, quote it, compare it clause by clause with the
yamaa specification, and state the rule as a yamaa probe. You propose; the
verifier decides. It checks every quote, runs every probe and assigns each
finding a rule from `rules.yaml`. Never write a count, a verdict, a rule ID or
a data value: only the verifier states those.

## Inputs

- The study, the dataset and your variables, from the orchestrator.
- The yamaa specification under review, `<study>/spec/yamaa/<spec>.yaml`.
- The exact citable text of every retained document, written by the verifier
  to `.build/verification/<study>/sections/<document>.txt`. Each section
  starts with a line `=== <section id>`: `<DATASET>.<VARIABLE>` for a
  Define-XML variable, `page-<n>` for a PDF page. Quote only from these files.
- `.automation/consistency_review/rules.yaml`, which says what each relation
  you choose will be reported as.

Do not edit the specification under review, reference data, retained
documents, Define-XML or any file outside your variables' claims and probe
columns. Return them to the orchestrator; it writes the files.

## For each variable

1. **Find every statement of the rule.** Read the Define-XML section first:
   comment or method, codelist and significant digits. Follow references such
   as "refer to SAP, Section 7.1". Search the data guide and SAP for the
   concept the variable carries (population, baseline, category, duration),
   including table shells and notes. A rule stated in two places is cited
   twice.
2. **Cite verbatim.** A citation is `document` (study-relative path),
   `section` and `quote`. Copy the shortest span that states the rule; only
   whitespace may differ from the section text. Citations are numbered from 1
   in the order you list them.
3. **Split the rule into clauses.** A clause is one condition, source or
   computation. Give each clause both sides, quoted verbatim:
   - `document`: `{"citation": <n>, "quote": "<span of that citation's quote>"}`
   - `spec`: `{"element": "<column, intermediate or row id>", "quote": "<text
     inside that element>"}`. The element may be the variable itself or one it
     reads, such as an intermediate or helper column.
   Choose one `relation`:

   | Relation | Use when | Sides | Reported under |
   | --- | --- | --- | --- |
   | `same` | Both state the same logic. | document, spec | none |
   | `differs` | Both state the clause, differently. | document, spec | CR-6 |
   | `absent_in_spec` | The document states it; the specification has no counterpart. | document | CR-6 |
   | `absent_in_document` | The specification states it; no document does. | spec | CR-7 |
   | `contradicts` | Two document statements of the same clause disagree. | document, `against` | CR-8 |

   `against` has the same form as `document`. Add a one-sentence `note`
   wherever the relation is not obvious from the two quotes. Group clauses
   that share one specification quote; do not split one difference into
   several clauses.
4. **Write the literal probe.** Add a column to
   `<study>/spec/review/<dataset>-probe.yaml`, named after the variable, that
   states the rule exactly as written, even when it looks wrong. Read
   upstream analysis variables from the `REF` intermediate, the published
   reference, so the probe tests this rule alone. Apply documented precision
   with `round_half_away_from_zero`. Keep helper columns prefixed with `_`.
5. **Add readings; never replace the literal one.** When the text is likely a
   typo or omission, or a second document states the rule differently, add a
   column `<VARIABLE>__<READING>` and a probe entry whose `reading` says what
   changed and why, citing the quote that justifies it.
6. **Record open choices.** Every choice the documents leave open goes in
   `interpretations`. A decision for the reviewer goes in `question`.
7. **When the rule cannot be stated in yamaa**, give `not_probed_reason`
   instead of probes and say what the documents leave unstated.

## Claim format

```json
{
  "variable": "TRTSDT",
  "rule": "One sentence restating the documented rule.",
  "citations": [
    {"document": "spec/define/define-adam.xml", "section": "ADSL.TRTSDT", "quote": "SV.SVSTDTC when SV.VISITNUM=3, converted to SAS date"}
  ],
  "clauses": [
    {
      "relation": "differs",
      "document": {"citation": 1, "quote": "SV.SVSTDTC when SV.VISITNUM=3"},
      "spec": {"element": "EX_MINDTC", "quote": "MIN(EX.EXSTDTC)"},
      "note": "The specification reads the first exposure date."
    }
  ],
  "probes": [{"column": "TRTSDT", "reading": "literal"}],
  "interpretations": [],
  "assessment": "What the evidence suggests, without numbers.",
  "question": "The decision a reviewer must make, or empty."
}
```

The claims file wraps the claims as `{"schema_version": 2, "dataset": ...,
"author": {"kind": "agent", "model": ..., "instructions":
".automation/consistency_review/extract.md", "date": ...}, "claims": [...]}`.
The first probe is always the literal reading. Keep both files ASCII; JSON
escapes such as `\u2019` represent non-ASCII document text.

## Follow-up rounds

When the orchestrator sends uncited statements from the adjudicator, or a
`CR-1` reason, you amend existing claims instead of writing new ones. Read the
variable's claim in `<dataset>-claims.json` and keep everything that is still
right, in its order: finding IDs number clauses by position, so a reordered
claim renames findings and voids their decisions. Append each new citation and
clause at the end. When a new statement shows an existing clause is wrong, for
example a clause marked `absent_in_document` that the statement documents,
correct that clause in place, keeping its position, and list its number under
`corrected`; do not append a second clause for the same logic. Never remove or
reorder a citation. Cite each uncited statement and give it the clause its
content calls for: `same` when it restates the specification's logic,
`differs` or `absent_in_spec` when the specification departs from it, and
`contradicts` when it disagrees with another document statement already cited.
Check the statement against its full section yourself; the adjudicator's
reason is a pointer, not evidence. Add a probe reading only when the statement
states the rule differently from every existing probe.

## Return

Return your claims as a JSON array and your probe columns as YAML, plus the
output column names to add. In a follow-up round, return the complete amended
claim for each variable, list what you appended, and list under `corrected`
the number of each clause you corrected in place. List any variable you
could not finish and why.
