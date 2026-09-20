# YAMAA Pilot 01 ADaM verification

Executable YAMAA specifications for all 10 CDISC Pilot 01 ADaM datasets.
Each spec was executed and its output strictly compared cell-for-cell
against the official ADaM parquet (`cdiscpilot01/data/adam/`).

## Reproduction

Use this directory as the project root. Place the Pilot 01 SDTM parquet
(`cdiscpilot01/data/sdtm/`) at `sdtm/` and the official ADaM parquet
(`cdiscpilot01/data/adam/`) at `expected/`. Run in this order
(downstream specs read promoted upstream outputs):

```
python run_spec.py adsl.yaml
python upstream/promote_output.py adsl
python run_spec.py adae.yaml
python upstream/promote_output.py adae
python run_spec.py adtte.yaml
python upstream/build_advs.py    && python run_spec.py advs.yaml
python upstream/build_adlbh.py   && python run_spec.py adlbh.yaml
python upstream/build_adlbc.py   && python run_spec.py adlbc.yaml
python upstream/build_adlbhy.py  && python run_spec.py adlbhy.yaml
python upstream/build_adqsadas.py && python run_spec.py adqsadas.yaml
python upstream/build_adqscibc.py && python run_spec.py adqscibc.yaml
python upstream/build_adqsnpix.py && python run_spec.py adqsnpix.yaml
```

Then compare each result:

```
python compare/strict_compare.py <domain> output/<domain>.parquet
```

`run_spec.py` runs the spec with `yamaa_domain`, applies the
spec-declared `output.order_by`, restores official Arrow types
(`large_string`/`double`/`date32[day]`), attaches `yamaa:label` field
metadata, and preserves empty strings. This writer step exists because
the YAMAA engine emits plain `string` columns without field labels and
does not implement final-frame ordering (upstream yamaa issue #74).

`promote_output.py` copies `output/<domain>.parquet` to
`upstream/<domain>.parquet` rewriting `large_string` as plain `string`,
because the engine rejects `large_string` input columns.

`compare/strict_compare.py` checks exact row count, file order, column
order, Arrow types, labels, null-vs-empty distinction, and values --
no sorting, no silent key alignment, no undeclared tolerances.

## Results

| Dataset | Rows x Cols | Inputs | Strict result |
|---|---:|---|---|
| ADSL | 254 x 48 | SDTM DM/EX/VS | STRICT PASS |
| ADAE | 1,191 x 55 | SDTM AE + upstream ADSL | STRICT PASS |
| ADTTE | 254 x 26 | upstream ADSL + upstream ADAE | STRICT PASS |
| ADVS | 32,139 x 34 | SDTM VS via `upstream/build_advs.py` | STRICT PASS |
| ADLBH | 49,932 x 46 | SDTM LB via `upstream/build_adlbh.py` | STRICT PASS |
| ADLBC | 74,264 x 46 | SDTM LB via `upstream/build_adlbc.py` | STRICT PASS |
| ADLBHY | 9,954 x 43 | generated ADLBC via `upstream/build_adlbhy.py` | STRICT PASS |
| ADQSADAS | 12,463 x 40 | SDTM QS via `upstream/build_adqsadas.py` | STRICT PASS |
| ADQSCIBC | 730 x 36 | SDTM QS via `upstream/build_adqscibc.py` | STRICT PASS |
| ADQSNPIX | 31,140 x 41 | SDTM QS via `upstream/build_adqsnpix.py` | STRICT PASS |

## Honest preprocessing (what YAMAA cannot express)

The drivers in `upstream/` compute, in plain Python/polars, the
derivations YAMAA has no native constructs for. Each driver documents
its rules in its docstring and was verified cell-for-cell against the
official parquet before the spec ran:

- **build_advs.py**: analysis-visit windowing (scheduled visits keep
  `Week n`/Baseline labels; screening/ECG/retrieval/unscheduled visits
  excluded), baseline carried per (subject, param, timepoint), and
  End-of-Treatment duplication of each subject-param-timepoint's latest
  scheduled visit when it is after Week 2 (empirical rule, verified in
  both directions over all 2,794 groups).
- **build_adlbh.py / build_adlbc.py**: End-of-Treatment duplication,
  ANL01FL winner selection (max ALBTRVAL for base rows; max absolute
  rounded AVAL for underscore rows, EOT inheriting through the source
  sequence number), underscore AVAL = (current - previous scheduled
  AVAL) / (0.5 x (A1HI - A1LO)) rounded to one decimal half-away-from-zero
  with SAS-style boundary fuzz, and ANRIND banding.
- **build_adlbhy.py**: Hy's Law parameters from ADLBC -- BILIHY/TRANSHY/
  HYLAW as 1/0 indicators of the >1.5xULN criterion (null-propagated),
  baseline carried as BASE, SHIFT1/SHIFT1N as the baseline-to-visit
  Normal/High shift.
- **build_adqsadas.py / build_adqscibc.py / build_adqsnpix.py**: analysis
  windowing, closest-to-target record selection, ACTOT forward-fill, and
  LOCF/derived-row generation.

The specs themselves declare every analysis column and merge ADSL
covariates through declared lookups. Final row order is spec-declared
(`output.order_by`, applied by the writer) for adsl, adae, adtte, advs,
adlbc, and adlbhy; for adlbh, adqsadas, adqscibc, and adqsnpix the driver
emits rows in official order and the engine preserves it -- the strict
comparator verifies file order either way.
