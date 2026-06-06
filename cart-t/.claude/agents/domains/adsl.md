# ADSL — Dataset Knowledge

## Overview
ADSL (Subject-Level Analysis Dataset) is the master one-row-per-subject
analysis table. 810 subjects total: 530 screen failures + 280 randomized
(of which 236 NHM, 27 NHF, 12 HM, 5 HF — see `STRAT1`/`STRAT1L`). Every
other ADaM dataset reads ADSL to inherit treatment variables, reference
dates, and population flags. The flag chain ADSL.SAFFL/ITTFL/RANDFL ->
ADCE/ADCM/ADLB/ADMH/ADQS/ADAE means a defect here multiplies across the
submission.

## Upstream sources
| Source | Variables consumed |
|--------|---------------------|
| `data/sdtm/dm.rds`    | STUDYID, USUBJID, SUBJID, SITEID, AGE, AGEU, SEX, RACE, ETHNIC, COUNTRY, ARMCD, ARM, ACTARMCD, ACTARM, RFSTDTC, RFENDTC, RFXSTDTC, RFXENDTC |
| `data/sdtm/ds.rds`    | DSDECOD, DSSTDTC, DSSEQ, DSTERM (for RANDDT, EOSDT, EOSSTT, DCDECOD, DCREASCD, COMPLFL) |
| `data/sdtm/ae.rds`    | USUBJID presence -> drives SAFFL when TRTSDT is null |
| `data/sdtm/qs.rds`    | USUBJID + QSSTRESN non-null -> drives EFFFL |
| `data/raw/rand.rds`   | PROFILE -> STRAT1 / STRAT1L (phenotype stratum) |

## Key derivations

### TRTSDT / TRTEDT
`as.Date(coalesce(RFXSTDTC, RFSTDTC))` and `as.Date(coalesce(RFXENDTC, RFENDTC))`.
DM was corrected in commit `af211c9` to populate RFSTDTC/RFENDTC from
ut_visits-derived per-subject date extremes; ADSL inherits.

### TRTDURD
`admiral::derive_var_trtdurd(start_date = TRTSDT, end_date = TRTEDT)`.

### RANDDT
Min `DSSTDTC` per subject where `DSDECOD == "RANDOMIZED"`.

### DCDECOD / DCREASCD / EOSSTT
`DCDECOD` = `DSDECOD` from the latest on-study disposition row
(arrange by `dplyr::desc(DSSTDTC), dplyr::desc(DSSEQ)`, slice_head).
`EOSSTT` is a derived three-level enum: `"COMPLETED"` / `"DISCONTINUED"`
/ `"ONGOING"`.

### Population flags (Y/N, never NA)
| Flag | Rule |
|------|------|
| RANDFL  | `!is.na(RANDDT)` |
| SAFFL   | `!is.na(TRTSDT) | !is.na(has_ae)` |
| ITTFL   | `RANDFL == "Y"` (equivalent to randomized) |
| EFFFL   | `RANDFL == "Y" & !is.na(has_qs)` |
| COMPLFL | `EOSSTT == "COMPLETED"` |

All flags must be set to `"N"` (not `NA_character_`) when the condition
is false. Per ADaMIG, population flags carry the `NY` codelist (`Y`/`N`
only) and are never null.

### STRAT1 / STRAT1L
`phenotype_code()` / `phenotype_label()` from `program/sdtm/ut_visits.R`
applied to the raw `rand.PROFILE` item. Null for the 530 screen
failures.

## P21 rules and fixes

### Resolved rules

#### AD0019 — Subject-population flag value is null
**Root cause**: `ifelse(cond, "Y", NA_character_)` produced NA for the
false branch on RANDFL/SAFFL/ITTFL/EFFFL/COMPLFL.
**Fix** (`program/adam/adsl.R`):
```r
RANDFL   = ifelse(!is.na(RANDDT),                  "Y", "N"),
SAFFL    = ifelse(!is.na(TRTSDT) | !is.na(has_ae), "Y", "N"),
ITTFL    = ifelse(!is.na(RANDFL) & RANDFL == "Y",  "Y", "N"),
EFFFL    = ifelse(!is.na(has_qs) &
                    !is.na(RANDFL) & RANDFL == "Y", "Y", "N"),
COMPLFL  = ifelse(!is.na(EOSSTT) & EOSSTT == "COMPLETED", "Y", "N")
```
**Coverage after fix**:
- RANDFL: Y=280, N=530 (was 810 NA)
- ITTFL:  Y=280, N=530 (was 810 NA)
- SAFFL:  Y=769, N=41  (was 482 NA, 328 Y)
- EFFFL:  Y=106, N=704 (was 810 NA)
- COMPLFL: Y=0, N=810  (was 809 NA, 1 Y — the lone "COMPLETED" row in
  raw DS turned out to be after a previous EARLY TERMINATION, so latest
  status is no longer COMPLETED)

#### AD0018 — Variable label mismatch (LABEL=null)
**Root cause**: XPT export lacked variable labels — they were never
attached to the columns in R.
**Fix** (`program/adam/adsl.R`): manual label attachment from spec YAML
because metacore/xportr/labelled aren't installed in renv:
```r
spec_yaml <- yaml::read_yaml("spec/adam/adsl.yaml")
for (v in names(adsl)) {
  lab <- spec_yaml$variables[[v]]$label
  if (!is.null(lab) && nzchar(lab)) attr(adsl[[v]], "label") <- lab
}
attr(adsl, "label") <- spec_yaml$label
```
Spec YAML cleanup: the prior file had unescaped embedded `"..."` strings
in `derivation:` fields that broke YAML parsing — those are now single-
quoted block scalars.

#### AD0320 — Non-standard dataset label
**Root cause**: dataset-level label attribute not set on the data frame.
**Fix**: `attr(adsl, "label") <- spec_yaml$label`. Spec dataset label is
`"Subject-Level Analysis Dataset"` (ADaMIG canonical).

#### AD0503 — *DT must contain 'Date' in the label
**Root cause**: same as AD0018 — no labels.
**Fix**: all four `*DT` labels in the spec already contained "Date":
- TRTSDT -> `Date of First Exposure to Treatment`
- TRTEDT -> `Date of Last Exposure to Treatment`
- RANDDT -> `Date of Randomization`
- EOSDT  -> `End of Study Date`

#### CT2002 — RACE value not in 'Race' codelist
**Root cause**: prior ADSL build had been run before DM was fixed in
commit `af211c9`; ADSL still held raw OpenClinica codes ("1", "1,2,5")
in RACE. The build code itself was correct (RACE flows straight from
DM via the `dm` data.frame in `mutate()` before `select()`); just had
to rebuild.
**Fix**: rebuild ADSL. No code change.
**Coverage after fix**: 353 RACE values map to CT (WHITE=270, AIAN=25,
ASIAN=18, MULTIPLE=20, NHOPI=12, BLACK=5, OTHER=3); 457 stay null
because those subjects have no DM-form data in the export.

### Known data limitations
| Rule | Residual count | Reason |
|------|---------------|--------|
| n/a | RACE NA=457 | 457 subjects have no DM CRF form data — RACE cannot be derived without raw `PTRACE` item. Not a P21 finding (RACE NA is valid). |
| n/a | EOSDT NA for ongoing subjects | RFENDTC is NA for non-disposed subjects. Drives EOSSTT="ONGOING". Not a defect. |
| n/a | TRTSDT / TRTEDT NA for non-randomized | 530 SCRNFAIL subjects never had a treatment date. Drives SAFFL="N" via has_ae fallback. Not a defect. |

## Cross-dataset dependencies
| Dependency | Direction | Notes |
|------------|-----------|-------|
| ADSL.SAFFL  | ADAE/ADCM/ADCE/ADLB/ADMH/ADQS read ADSL | All downstream OCCDS/BDS rebuild needs ADSL.SAFFL = Y/N. The AD0019 fix here cascades. |
| ADSL.ITTFL  | ADQS/ADDS | Same — must inherit Y/N. |
| ADSL.RANDFL | ADAE/ADCM/ADCE | Same. |
| ADSL.TRT01P/TRT01A/TRT01PN/TRT01AN | every downstream dataset | These are required for `derive_vars_merged(adsl, by = "USUBJID")`. |
| ADSL.STRAT1/STRAT1L | every OCCDS downstream | Phenotype stratification carried forward (per CLAUDE.md study decision). |

## Re-build dependency
Every downstream ADaM dataset must be rebuilt after ADSL changes so the
corrected pop flags and labels propagate. Use `program/adam/_run_all.R`.
