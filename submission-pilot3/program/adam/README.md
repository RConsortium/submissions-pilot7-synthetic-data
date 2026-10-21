# Pilot 3 ADaM derivations

The five specifications in `../../spec/yamaa/` use released **yamaa 0.5.0**.
`../../project.yaml` links their predecessor contracts and runs all targets in
one project run: ADSL, ADAE, ADADAS, ADTTE and ADLBC. The specifications read
only the original SDTM, the reviewed planning/window CSVs and their derived
ADaM predecessors. ADLBC's `CHEMISTRY` intermediate filters LB inside the
specification; no intermediate clinical dataset is prepared by host code.

## Run with R

From the repository root:

```bash
Rscript --vanilla submission-pilot3/program/adam/r/setup.R
Rscript --vanilla submission-pilot3/program/adam/r/run.R
Rscript --vanilla submission-pilot3/program/adam/r/compare.R
Rscript --vanilla submission-pilot3/program/adam/r/tests.R
```

The scripts also work from another working directory. Setup installs the
released source archive into the study's ignored `.r-library` when needed;
source installation requires R 4.4 or later, a C compiler and Rust/Cargo 1.82
or later. R dependencies are `arrow`, `jsonlite` and `yaml`. No development
checkout or historical `admiral` dependency stack is substituted.

## Outputs and explicit export

The project saves raw engine artifacts under `../../data/adam/<dataset>-yamaa-raw.parquet` and its
run reports under `../../log/yamaa-*`. The R runner then exports
`../../data/adam/<dataset>-yamaa.parquet`, retaining the raw artifacts.

Export has two explicit conventions: missing character values become empty
strings, matching the official XPT-derived references, and each variable's
specification label is attached to its saved Parquet field. Numbers, dates,
row identities, row counts and row order are unchanged. Export reads no
reference clinical values or reference labels. Original reference files and
Define-XML are never overwritten. Generated artifacts and reports are ignored
by git.

## Comparison and regression checks

The independent R comparator checks every reference cell, both key sets and
key uniqueness, missing/extra records and columns, logical types, column order
and persisted variable labels. All five reference sizes remain in its totals,
including when an output is missing. It reports exact values, numeric values
accepted only within absolute tolerance `1e-10`, and blank/null differences
separately. Blank/null differences are permitted only in the informational raw
comparison; exported text must match exactly. Missing/extra data or metadata
fail the exported comparison.

The supplied snapshot has these exported exact-cell counts; no numeric
tolerance is needed:

| Dataset | Columns | Exact cells |
| --- | ---: | ---: |
| ADSL | 49 | 12,446/12,446 |
| ADAE | 55 | 65,505/65,505 |
| ADADAS | 40 | 498,520/498,520 |
| ADTTE | 26 | 6,604/6,604 |
| ADLBC | 46 | 1,708,072/1,708,072 |
| Total | 216 | 2,291,147/2,291,147 |

Raw output has 25,388 blank/null differences and lacks the declared field
labels. These are reported explicitly instead of being counted as exact
native matches. The export step resolves them.

Comparison aligns by unique clinical keys. ADSL, ADAE and ADTTE also preserve
reference physical row order; ADADAS and ADLBC have different construction
order. Both differences remain visible in the report. To require identical
physical row order, run:

```bash
Rscript --vanilla submission-pilot3/program/adam/r/compare.R --require-row-order
```

That stricter check currently fails for ADADAS and ADLBC. No output is reordered
by looking up reference row positions.

The regression script tests partial start/end dates, visit-window boundaries,
qualifying first exposure, early chemistry selection and baseline donors,
duplicate/missing/extra identities and columns,
order policy, and tolerance/blank classification. It independently reproduces
the 222 ADADAS planning rows from QS/EX in R and checks the CSV bytes without
writing to the reviewed planning file. The existing Python planning generator
and its CI check remain in place.

Two source-rule corrections accompany the syntax update: ADSL selects its
first exposure only from positive-dose or placebo records, and ADAE end dates
require a collected day, matching the submitted R program's time-only end-date
imputation. The ADAE start imputation flag reads collected date precision using
the current precision words. ADLBC's threshold maximum uses supported
`greatest` over explicit helper columns.

## Optional Python runner

The existing Python route uses the same project and explicit export:

```bash
pip install -r submission-pilot3/program/adam/python/requirements.txt
python3 submission-pilot3/program/adam/python/run.py
python3 submission-pilot3/program/adam/python/compare.py
```

Its comparator checks persisted labels, unique keys, missing/extra data and
column order, with exact/tolerance/blank counts separated. CI executes both
runners and applies the independent R comparison to both.

## Qualification limits and source questions

A snapshot match does not establish complete derivation-logic equivalence.
The original submitted R programs and ADRG are available in
[R Consortium Pilot 3](https://github.com/RConsortium/submissions-pilot3-adam/tree/780d49574129e5522925d7109db5b1175a85e71c).
The assessment leaves these questions visible for study-owner review:

- ADTTE's submitted R program explicitly describes a death-date censoring
  override that its comments say is absent from the written specification.
  The yamaa specification follows the submitted program and reference data.
- ADADAS has dataset label `ADAS-Cog Analysis` in Define-XML and
  `ADAS-COG Analysis Dataset` in the original XPT. ADLBC's original XPT dataset
  label is empty despite the nonempty Define-XML and R export-call labels.
  This workflow verifies variable labels; it does not choose new dataset
  labels or qualify new XPT/Define-XML submission exports.
- The inspected original repository lock names `pilot3utils` 0.0.1, while the
  ADRG names 0.0.2. The historical stack has not been rerun under a guessed
  dependency version.
- The ADRG's wording includes all DM patients in ADSL, while the submitted
  code, Define-XML and references exclude 52 screen failures from 306 DM
  records, leaving 254 ADSL subjects. The specifications follow the latter.
- Physical order policy for ADADAS/ADLBC remains to be agreed. Further edge
  review includes partial exposure dates and imputation bounds, mixed
  treatments, missing-baseline/new-subject planning, LOCF and lab-selection
  ties, missing lab ranges, and complete custom-query boundaries.

These source questions are not established yamaa engine defects. Full logic
and submission-metadata equivalence remain unqualified.
