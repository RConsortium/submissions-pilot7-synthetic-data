# ADDS — Dataset Knowledge

## Overview
ADDS is the OCCDS dataset for disposition events: one row per disposition
milestone per subject. Built from `data/sdtm/ds.rds` (1,442 rows × 13 cols
across 592 unique subjects) joined to `data/adam/adsl.rds`. Because DS is
generated from three source layers (Disposition form, Eligibility form,
Randomize form — see `domains/ds.md`), ADDS inherits that coverage.

Current output: 1,442 rows × 20 cols across 592 subjects.

## Upstream sources
| Source | Variables consumed |
|--------|--------------------|
| `data/sdtm/ds.rds`     | STUDYID, USUBJID, DSSEQ, DSTERM, DSDECOD, DSCAT, EPOCH, DSSTDTC |
| `data/adam/adsl.rds`   | SUBJID, SITEID, AGE, SEX, RACE, STRAT1, TRT01P, TRT01A, TRTSDT, SAFFL, ITTFL |

## Key derivations

### Analysis dates: ASTDT / ASTDY
`admiral::derive_vars_dt(new_vars_prefix = "AST", dtc = DSSTDTC)` then
`admiral::derive_vars_dy(reference_date = TRTSDT, source_vars =
exprs(ASTDT))`. There is no end date for DS (each row is a milestone), so
AENDT / AENDY are not derived.

### Final-disposition flag: FINALFL
`admiral::derive_var_extreme_flag()` with `mode = "last"`, ordered by
`(ASTDT, DSSEQ)` per `USUBJID`. Marks the chronologically last
disposition row per subject. Y on the last row; null elsewhere.

### Population flags: SAFFL / ITTFL
Inherited verbatim from ADSL. Both are Y/N (never NA) per ADaMIG since
ADSL was fixed in commit `2c0f164`. SAFFL counts: 818 Y / 624 N. ITTFL
counts: 818 Y / 624 N. Because every DS row carries its USUBJID's flag,
totals reflect rows-per-subject not subjects-per-flag.

### Per-record planned/actual treatment: TRT01P / TRT01A
Inherited verbatim from ADSL — single-period design. No per-record TRTP /
TRTA derived because the per-disposition treatment context is ADSL.

### Label attachment
`metacore` / `xportr` / `labelled` are not installed in renv. Labels are
attached from `spec/adam/adds.yaml` via:
```r
spec_yaml <- yaml::read_yaml("spec/adam/adds.yaml")
for (v in names(adds)) {
  lab <- spec_yaml$variables[[v]]$label
  if (!is.null(lab) && nzchar(lab)) attr(adds[[v]], "label") <- lab
}
attr(adds, "label") <- spec_yaml$label
```
Same pattern as ADSL / ADAE / ADCE / ADCM. Labels carry through to XPT
via `haven::write_xpt` reading the `label` attribute on each column.

## P21 rules and fixes

### Resolved rules

#### AD0018 — Variable label mismatch (13 → 0)
**Root cause**: ADDS was written to RDS / XPT without any
`attr(x, "label")` attached; P21 saw `LABEL=null` for every variable.
Examples flagged: AGE, ASTDT, ASTDY, ITTFL, RACE. Dataset-level label
was also null (AD0320 territory).
**Fix** (`program/adam/adds.R`): manual label attachment from spec YAML
(see snippet above).
**Coverage after fix**: 20 / 20 columns labeled; dataset label is
`"Disposition Analysis Dataset"`.

#### AD0019 — ITTFL subject-population flag null (9 → 0)
**Root cause**: Pre-fix `adsl.rds` had `ITTFL = NA` for screen-failure
subjects, and the `left_join(adsl_vars, by = "USUBJID")` propagated those
NAs into ADDS. ADSL was corrected in commit `2c0f164` (population flags
must be Y/N per ADaMIG).
**Fix**: No code change in ADDS — just rebuild against the corrected
ADSL. The existing `left_join` propagates the corrected Y/N values
verbatim. `convert_blanks_to_na()` does not affect "N" (only blank
strings).
**Coverage after fix**: 0 NA; 818 Y rows / 624 N rows.

#### AD0503 — *DT must contain 'Date' in the label (1 → 0)
**Root cause**: ASTDT had `LABEL=null` (same root cause as AD0018), so
the "*DT label must contain Date" check could not pass.
**Fix**: Label attachment makes ASTDT carry the spec label `"Analysis
Start Date"`, which contains `"Date"`. ASTDT is the only `*DT` variable
in ADDS.

#### CT2002 — RACE value not in 'Race' codelist (1 → documented residual)
**Root cause**: Pre-fix `adsl.rds` carried RACE = `"1,5,6"` (raw
multi-select coded value joined verbatim) for some subjects. DM was
corrected in commit `af211c9` to emit `"MULTIPLE"` for multi-select
PTRACE per SDTMIG; ADSL inherits that value.
**Fix**: No code change in ADDS — just rebuild against the corrected
ADSL.
**Coverage after fix**: 0 codelist violations from `"1,5,6"`. RACE
values now: 709 WHITE, 65 AMERICAN INDIAN OR ALASKA NATIVE, 48 ASIAN,
13 BLACK OR AFRICAN AMERICAN, 26 NATIVE HAWAIIAN OR OTHER PACIFIC
ISLANDER, 48 MULTIPLE, 7 OTHER, 526 NA. `"MULTIPLE"` and `"OTHER"` are
SDTMIG-prescribed extensions for the extensible race codelist (C74457)
— document in ADRG.

### Known data limitations
| Rule | Residual count | Reason |
|------|----------------|--------|
| RACE = "MULTIPLE" | 48 rows | SDTMIG-prescribed extension for multi-race subjects; race codelist (C74457) is extensible. Document in ADRG. |
| RACE = "OTHER" | 7 rows | SDTMIG extensible-codelist extension; document in ADRG. |
| RACE = NA | 526 rows | Subjects with no PTRACE captured in raw DM. Upstream sparsity, not a code defect. |
| ASTDT = NA | 1 row | DS row (SS_MGH213 AE early termination) has DSSTDTC = NA per `domains/ds.md` (no EARLYTERMINATIONDATE in source). |
| ASTDY = NA | many rows | TRTSDT is NA for all 530 screen-failure subjects (no treatment date), so ASTDY cannot be computed for those rows. |

## Cross-dataset dependencies
| Dependency | Direction | Notes |
|------------|-----------|-------|
| `data/sdtm/ds.rds`   | DS → ADDS   | Source of DSSEQ, DSTERM, DSDECOD, DSCAT, EPOCH, DSSTDTC. DS was cleaned up in commit `ca60796` (CT2005, SD0022/1118, SD1088, SD1367). |
| `data/sdtm/dm.rds`   | DM → ADSL → ADDS | RACE / STUDYID / SUBJID flow. CT2002 RACE = `"1,5,6"` fix lives in DM (commit `af211c9`). |
| `data/adam/adsl.rds` | ADSL → ADDS | SUBJID, SITEID, AGE, SEX, RACE, STRAT1, TRT01P, TRT01A, TRTSDT, SAFFL, ITTFL. SAFFL/ITTFL Y/N fix lives in ADSL (commit `2c0f164`). |

## Rebuild command
```bash
Rscript program/adam/adsl.R 2>&1 | grep -v "renv\|out-of-sync\|masked\|built under"
Rscript program/adam/adds.R 2>&1 | grep -v "renv\|out-of-sync\|masked\|built under"
```

Expected output:
```
ADSL written: 810 rows x 35 cols
ADDS written: 1442 rows x 20 cols
ADDS XPT exported to data/adam/adds.xpt
```

## Sanity checks
```r
adds <- readRDS("data/adam/adds.rds")
stopifnot(ncol(adds) == 20)
stopifnot(!is.null(attr(adds, "label")))
# Every column has a label
stopifnot(all(vapply(adds, function(x) !is.null(attr(x, "label")), logical(1))))
# *DT labels contain "Date"
for (v in grep("DT$", names(adds), value = TRUE)) {
  stopifnot(grepl("Date", attr(adds[[v]], "label"), fixed = TRUE))
}
# Population flags are Y/N (never NA, never blank)
stopifnot(sum(is.na(adds$SAFFL)) == 0)
stopifnot(sum(is.na(adds$ITTFL)) == 0)
stopifnot(all(adds$SAFFL %in% c("Y","N")))
stopifnot(all(adds$ITTFL %in% c("Y","N")))
# FINALFL is Y or null only (never N per ADaMIG analysis-flag rule)
stopifnot(all(is.na(adds$FINALFL) | adds$FINALFL == "Y"))
# Every USUBJID in ADDS appears in ADSL
adsl <- readRDS("data/adam/adsl.rds")
stopifnot(all(adds$USUBJID %in% adsl$USUBJID))
```
