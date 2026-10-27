# Consistency issue schema

Design the data before rendering it. The report separates three entities:

| Entity | Meaning | Identity |
| --- | --- | --- |
| Issue | One problem requiring one review decision | Authored dataset/variable/slug |
| Check | One automated observation under a consistency rule | Existing finding ID |
| Evidence | One quotation, specification excerpt or measured comparison | SHA256 of normalized content |

`review-issues.schema.json` validates authored grouping files at
`<study>/spec/review/<dataset>-issues.json`. `review-report.schema.json`
validates the generated `report.json` `review` member. Both use JSON Schema
2020-12, closed objects, explicit versions and constrained text lengths.
The outer dashboard transport remains version 1; `review.schema_version`
versions this independent contract.

## Authored issues

Each issue has a stable slug, variable, short problem title, summary,
expected behavior, observed behavior, and proposed action. Group observations
that need the same decision. A variable can have multiple issues. A check
can support multiple issues, for example when one probe measures both a
codelist discrepancy and missing-value handling. Never group by similar text
or variable name alone.

The declaration inventories every check ID and its SHA256 basis. The basis
already includes the verified quotes, specification text and measured data,
excluding changing repository links. Changed, missing or new checks stop
publication until the grouping is reviewed. This binds editorial claims to
the evidence they describe without rewriting check IDs or adjudications.

Data selectors identify a check, method (`probe`, `copy`, `codelist`),
comparison target (`reference`, `derived`), and probe column where applicable.
They are resolved against the complete check evidence, never a display sample.
Missing selectors fail publication. `impact` marks an issue-specific measurement;
`context` retains a shared or alternative comparison without attributing its
mismatches to this issue. Both are available in the trace.

Optional citation selectors identify a linked check, evidence type, section,
and exact quote when needed. They keep a shared check's unrelated quotations
out of an issue's primary trace. Missing or ambiguous selections fail publication;
the check audit always retains the complete evidence.

Datasets without an authored grouping file retain one issue per check. They
remain visible; a missing declaration must not silently suppress observations.
Successful execution is a metric and does not create an issue.

## Generated contract

`review` contains `schema_version`, `study`, `revision`, `issues`, `checks`,
`evidence`, and `counts`. Issues reference check IDs and evidence IDs; checks
reference their complete evidence. Shared quotations and comparisons appear
once in the evidence registry. A trace includes only its selected data evidence
and its supporting source/specification quotations, deduplicated by content.
Full specification context and check-level adjudication remain expandable.

Issue type is derived from the supporting checks. Agent review is a separate
field: agreed, disputed, mixed, stale, pending, or not reviewed. Agreement is
not resolution. Proposed actions are text; this schema does not manufacture a
human approval or resolved state. Raw findings remain available for audit.

`critical` contains `status` (yes, no, needs_review) and a short `reason`.
Authored issues can explicitly set it; otherwise the generator prioritizes
source, derivation, category and output discrepancies as critical.
An absent source named by Define-XML (CR-2) is a critical source discrepancy,
including when its data impact cannot be measured. CR-6 clauses
quoting only `Significant digits: N` and variable-label differences are
non-critical. The full variable context is not used for that exception because
it can contain a different formula alongside precision metadata. Documentation
gaps and incomplete evidence need review. Criticality does not depend on subject
counts or agent agreement and does not resolve the issue. Ungrouped summaries
retain the full observation; only authored summaries have an editorial length
limit.

Impact is derived from explicitly selected measurements:

- `observed`: at least one selected measurement differs;
- `not_observed`: all selected measurements agree on the compared data;
- `not_measured`: no issue-specific measurement was selected.

Subject counts are the union of the selected measurements' subject identifiers.
Never sum overlapping record counts or infer an affected population from a
document quotation. Each measurement retains its own record denominator and
comparison target. Zero observed mismatches does not prove equivalent rules.
Context comparisons do not contribute to impact or workspace subject selection.

Validation also checks unique identities, reference integrity, dataset/variable
scope, complete check coverage, count consistency, measured-subject unions,
and sorted, nonnegative comparison counts. Invalid data is rejected before the
bundle replaces the previous publication. The browser rejects unsupported
review versions. Existing URLs naming a raw check resolve to its first issue.
