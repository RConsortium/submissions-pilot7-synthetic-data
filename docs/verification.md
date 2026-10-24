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

The comparisons keep the repository's established policies:

| Policy | CDISC Pilot 01 | Submission Pilots 3 and 5 |
| --- | --- | --- |
| Numeric tolerance | Absolute difference ≤ `1e-10` | Absolute difference ≤ `1e-10` |
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

The active CDISC Pilot 01 project covers eight datasets. ADQSADAS and
ADQSCIBC still need single-spec implementations and comparisons; they are
not counted as passing. Pilots 3 and 5 cover their five staged official
analysis datasets.

Pilot 6's initial ADSL specification is proposed in PR #104. It adapts shared derivations
from Pilot 3 into a self-contained file, reads Pilot 6's staged SDTM, and
adds COMPLFL from Pilot 6's workbook. Its production ADaM references
are absent from this repository, so no official comparison is claimed.
ADADAS, ADAE, ADLBC, ADLBH, ADNPIX, ADTTE, and ADVS remain outside its active
project. The upstream repository documents anonymous DVC downloads; access
to that S3 endpoint was blocked in the environment used for this update.

## Evidence published with the site

GitHub Actions validates the four study projects before building the site.
Each study page links its JSON record, including the engine revision,
dataset dimensions, build status, comparison status, execution time stamp,
and the Pilot 7 source commit in CI builds. A failed validation job prevents
publication of that source revision.

[View the study results](studies/index.md).

Pending projects are shown explicitly and cannot contribute passing datasets.
Publication rejects failed builds, missing dataset records, unknown comparison
statuses, mixed source commits, and evidence from a different engine pin.
Official studies must pass every reference comparison.
