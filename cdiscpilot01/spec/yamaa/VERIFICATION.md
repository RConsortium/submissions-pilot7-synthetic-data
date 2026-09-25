# YAMAA Pilot 01 ADaM verification

Executable YAMAA specifications for all 10 CDISC Pilot 01 ADaM datasets.
Every analysis variable is derived by the YAMAA engine from a spec in this
directory. Python's role is orchestration only: running specs in dependency
order, recasting Arrow `large_string` to plain `string` between stages (the
engine reader requires `pa.string()`), joining the YAMAA-derived PREV_AVAL
map back onto LB, and concatenating stage outputs. No analysis variable is
derived in Python.

Each spec's output was strictly compared cell-for-cell against the official
ADaM parquet (`cdiscpilot01/data/adam/` on upstream main).

## Reproduction

Use this directory as the project root. Place the Pilot 01 SDTM parquet
(`cdiscpilot01/data/sdtm/`) at `sdtm/` and the official ADaM parquet
(`cdiscpilot01/data/adam/`) at `expected/`, then:

```
python run_all.py
```

This runs every dataset in dependency order (ADSL -> ADAE -> ADTTE, ADVS,
ADLBH, ADLBC -> ADLBHY, ADQSADAS, ADQSCIBC, ADQSNPIX), promoting predecessor
ADaM outputs into `upstream/` between steps. To run one dataset (its
prerequisites must already exist in `upstream/`):

```
python run_all.py adlbhy
```

Then compare each result:

```
python compare/strict_compare.py <domain> output/<domain>.parquet
```

`run_spec.py` runs a spec with `yamaa_domain`, applies the spec-declared
`output.order_by` (nulls last, matching official row order), restores
official Arrow types (`large_string`/`double`/`date32[day]`), attaches
`yamaa:label` field metadata, and preserves empty strings. This writer step
exists because the YAMAA engine emits plain `string` columns without field
labels and does not implement final-frame ordering.

`compare/strict_compare.py` checks exact row count, file order, column
order, Arrow types, labels, null-vs-empty distinction, and values -- no
sorting, no silent key alignment, no undeclared tolerances.

## Pipelines

Single-spec datasets: `adsl.yaml`, `adae.yaml`, `adtte.yaml`, `advs.yaml`.

**ADLBH / ADLBC** (`run_adlbh.py`, `run_adlbc.py`): the "change from previous
visit" underscore parameters need PREV_AVAL, the AVAL of the previous
scheduled record within (USUBJID, LBTESTCD) ordered by AVISITN, with raw
`BASELINE` and unscheduled records excluded (official behavior treats
`SCREENING 1` as the analysis baseline). `adlbh-prevmap.yaml` /
`adlbc-prevmap.yaml` derive that map natively in YAMAA; the runner joins it
back onto `sdtm/lb.parquet` by (USUBJID, LBTESTCD, LBSEQ) into
`work/lb_h_with_prev.parquet` / `work/lb_with_prev.parquet`, then runs the
main spec.

**ADLBHY** (`run_adlbhy.py`): reads the plain-string recast of the ADLBC
output (`upstream/adlbc.parquet`). Derives BILIHY/TRANSHY/HYLAW natively:
per (subject, visit), BILIHY flags BILI ratio-to-ULN > 1.5, TRANSHY flags the
max ALT/AST ratio > 1.5, HYLAW is 1 only when both are 1. A `COUNT` existence
gate suppresses groups with no ALT/AST/BILI records (grouped row templates
form candidates from every record sharing the grouping keys; the row filter
runs after group reduction).

**ADQSADAS** (`run_adqsadas.py`): five native stages -- window assignment +
closest-to-target selection (s1), ACTOT forward-fill (s2), per-subject
empty-window flags (s2subj), LOCF rows for empty windows (s3), union with
BASE/CHG/PCHG and ADSL covariates (final).

**ADQSCIBC** (`run_adqscibc.py`): ten native stages (s1 through s5j) plus a
concatenation of natural and LOCF rows and a final union spec.

**ADQSNPIX** (`run_adqsnpix.py`): three native stages -- window assignment +
closest-to-target selection (s1), per-subject NPTOTMN values (s2), union of
item rows and derived NPTOTMN rows with BASE/CHG/PCHG (final).

## Results

| Dataset | Rows x Cols | Inputs | Strict result |
|---|---:|---|---|
| ADSL | 254 x 48 | SDTM DM/EX/VS | STRICT PASS |
| ADAE | 1,191 x 55 | SDTM AE + upstream ADSL | STRICT PASS |
| ADTTE | 254 x 26 | upstream ADSL + upstream ADAE | STRICT PASS |
| ADVS | 32,139 x 34 | SDTM VS + upstream ADSL | STRICT PASS |
| ADLBH | 49,932 x 46 | SDTM LB (via prevmap join) + upstream ADSL | STRICT PASS |
| ADLBC | 74,264 x 46 | SDTM LB (via prevmap join) + upstream ADSL | STRICT PASS |
| ADLBHY | 9,954 x 43 | upstream ADLBC | STRICT PASS |
| ADQSADAS | 12,463 x 40 | SDTM QS + upstream ADSL | STRICT PASS |
| ADQSCIBC | 730 x 36 | SDTM QS + upstream ADSL | STRICT PASS |
| ADQSNPIX | 31,140 x 41 | SDTM QS + upstream ADSL | STRICT PASS |

Strict means: exact row count, exact file order, exact column order, exact
Arrow types, exact `yamaa:label` metadata, null-vs-"" kept distinct, and
every cell value exact (floats compared with a declared 1e-10 tolerance;
ADQSNPIX has 768 cells within tolerance, all accepted by the comparator).
