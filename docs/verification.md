# Verification policy

A specification that builds successfully and a dataset that agrees with an
official reference are different results. The study pages show both.

## What is checked

1. **Specification checks:** yamaa checks the project and its specifications
   before reading study data.
2. **Execution:** every active dataset builds and saves using the pinned
   engine and the staged inputs.
3. **Reference comparison:** the existing study comparator checks the
   derived output against the official ADaM, including column labels.

The comparisons preserve the values stored in the submitted references:

| Policy | CDISC Pilot 01 | Submission Pilots 3 and 5 |
| --- | --- | --- |
| Numeric tolerance | Absolute difference <= `1e-10` | Absolute difference <= `1e-10` |
| Text | Exact | Exact |
| Null and empty text | Distinct | Distinct |
| Rows | Original row order | Aligned using the comparator's dataset keys |
| Columns | Shape, names, order, Arrow types | Exact column set and existing value checks |
| Labels | Specification labels against official Parquet metadata | Specification labels against official Parquet metadata |

Pilots 3 and 5 previously treated null and empty text as equivalent. Their
comparators now distinguish them, and the YAML emits submitted blanks directly.
NaN and null also remain distinct. The numeric tolerance is unchanged.
Derivation inputs and outputs cannot use the independent reference ADaM files.
No reference file is regenerated, and no output is repaired after execution.
The scripts remain available in each study's `program/adam/python/`
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
