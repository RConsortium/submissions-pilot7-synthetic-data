# Verification policy

A specification that builds successfully and a dataset that agrees with an
official reference are different results. The study pages show both.

**Published ADaM reference agreement** measures reproduction of the published
datasets under the study's comparison rules. **Consistency review** checks
agreement among documents, derivation rules, and data. Findings can remain open
even when reference agreement is 100%. For example, the generated and published
datasets can contain the same BMI values while a document states a different
formula. The reference comparison passes, and the consistency finding remains
open for review. Each measured finding names the sources it compares.

## What is checked

1. **Specification checks:** yamaa checks the project and its specifications
   before reading study data.
2. **Execution:** every active dataset builds and saves using the pinned
   engine and the staged inputs.
3. **Reference comparison:** the existing study comparator checks the
   derived output against the official ADaM, including column labels.

The comparisons keep the repository's established policies:

| Policy | CDISC Pilot 01 | Submission Pilots 3 and 5 |
| --- | --- | --- |
| Numeric tolerance | Absolute difference <= `1e-10` | Absolute difference <= `1e-10` |
| Text | Exact | Exact after normalizing empty text and null |
| Null and empty text | Distinct | Equivalent |
| Rows | Original row order | Aligned using the comparator's dataset keys |
| Columns | Shape, names, order, Arrow types | Existing comparator's column and value checks |
| Labels | Specification labels against official Parquet metadata | Specification labels against official Parquet metadata |

The migration does not relax these comparisons or regenerate the reference
files. The scripts remain available in each study's `program/adam/python/`
folder. This is regression evidence against the staged references; it is
not regulatory validation or a claim that every possible input is covered.

## Coverage and remaining work

CDISC Pilot 01 covers all ten staged official analysis datasets. ADQSADAS and
ADQSCIBC have single-spec implementations and are included in the project and
reference comparison. Pilots 3 and 5 cover their five staged official analysis
datasets.

## Evidence published with the site

GitHub Actions validates every study in the publication catalog before building the site.
Each study page links its JSON record, including the engine revision,
dataset dimensions, build status, comparison status, execution time stamp,
the Pilot 7 source commit in CI builds, and SHA256 inventories of the validated
inputs, outputs, references, and submission documents. Publication checks these
inventories before and after exporting the dashboard. A failed validation job prevents
publication of that source revision.

The dashboard also publishes source-backed documentation observations and
authored questions. These are distinct from dataset agreement, with partial
narrative coverage stated explicitly. See the [review guide](review.md).

[View the study results](studies/index.md).

Pending projects are shown explicitly and cannot contribute passing datasets.
Publication rejects failed builds, missing dataset records, unknown comparison
statuses, mixed source commits, and evidence from a different engine pin.
Official studies must pass every reference comparison.
