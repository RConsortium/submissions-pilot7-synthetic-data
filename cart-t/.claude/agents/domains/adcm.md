# ADCM — Dataset Knowledge

## Overview
ADCM is the OCCDS dataset for concomitant medications: one row per CM
record per subject. Built from `data/sdtm/cm.rds` (259 rows, RxNorm-coded
medications) joined to `data/adam/adsl.rds`. Drives PREFL / ONTRTFL /
ONGOFL analysis flags from the SDTM CM date qualifiers.

Current output: 259 rows × 27 cols across 259 unique subjects.

## Upstream sources
| Source | Variables consumed |
|--------|--------------------|
| `data/sdtm/cm.rds`     | STUDYID, USUBJID, CMSEQ, CMTRT, CMDECOD, CMINDC, CMDOSE, CMDOSU, CMROUTE, CMSTDTC, CMENDTC, CMENRTPT |
| `data/adam/adsl.rds`   | SUBJID, SITEID, AGE, SEX, RACE, TRT01P, TRT01A, TRTSDT, TRTEDT, SAFFL |

Note: CMRXCUI was removed from SDTM CM in the SD1076 fix (RxNorm CUI is
not in SDTMIG v3.3 CM); ADCM no longer surfaces it either.

## Key derivations

### Analysis dates: ASTDT / AENDT / ASTDY / AENDY
`admiral::derive_vars_dt()` for ASTDT (from CMSTDTC) and AENDT (from
CMENDTC). `admiral::derive_vars_dy()` then produces ASTDY and AENDY
relative to ADSL.TRTSDT (skipping day 0).

### Pre-treatment flag: PREFL
`"Y"` when `ASTDT < ADSL.TRTSDT`; else null.

### On-treatment flag: ONTRTFL
`"Y"` when `ASTDT >= ADSL.TRTSDT` and (`AENDT` missing or `ASTDT <=
ADSL.TRTEDT`); else null.

### Ongoing flag: ONGOFL
`"Y"` when `CM.CMENRTPT == "ONGOING"`; else null. CMENRTPT comes from
the SDTM CM build (raw `ONGOING == "Yes"` -> `CMENRTPT = "ONGOING"`).
The retired SDTM variable `CMENRF` was removed in the SD1078 cleanup —
ADCM now reads CMENRTPT instead.

### Analysis record flag: ANL01FL
`"Y"` when `SAFFL = "Y"`; else null. SAFFL is Y/N (never NA) after the
ADSL fix (commit `2c0f164`).

### Label attachment
`metacore` / `xportr` / `labelled` are not installed in renv. Labels are
attached from `spec/adam/adcm.yaml` via the same pattern as ADSL / ADAE
/ ADCE:
```r
spec_yaml <- yaml::read_yaml("spec/adam/adcm.yaml")
for (v in names(adcm)) {
  lab <- spec_yaml$variables[[v]]$label
  if (!is.null(lab) && nzchar(lab)) attr(adcm[[v]], "label") <- lab
}
attr(adcm, "label") <- spec_yaml$label
```

## P21 rules and fixes

### Resolved rules

#### AD0019 — SAFFL subject-population flag value is null (31 -> 0)
**Root cause**: Pre-fix `adsl.rds` had `SAFFL = NA` for screen-failure
subjects, and the `left_join(adsl_vars)` propagated those NAs into ADCM.
ADSL was corrected in commit `2c0f164` (population flags must be Y/N
per ADaMIG).
**Fix**: Rebuild against corrected ADSL — no code change needed beyond
the left_join.
**Coverage after fix**: 0 NA, 254 SAFFL=Y, 5 SAFFL=N.

#### AD0018 — Variable label mismatch (21 -> 0)
**Root cause**: ADCM was written without `attr(x, "label")` attached;
P21 saw `LABEL=null` on every native and derived variable.
**Fix** (`program/adam/adcm.R`): manual label attachment from
`spec/adam/adcm.yaml` (snippet above). Dataset-level label also set.
**Coverage after fix**: 27 / 27 columns labelled; dataset label is
`"Concomitant Medications Analysis Dataset"`.

#### CT2002 — RACE value not in 'Race' codelist (9 -> 0)
**Root cause**: Pre-fix `adsl.rds` carried `RACE` as raw multi-select
codes (`"1,5,6"`, etc.). DM was corrected to emit `MULTIPLE` per SDTMIG
extension; ADSL inherits.
**Fix**: Rebuild against corrected ADSL — no code change in ADCM.
**Coverage after fix**: ADCM.RACE values are AMERICAN INDIAN OR ALASKA
NATIVE (3), ASIAN (4), MULTIPLE (5), NATIVE HAWAIIAN OR OTHER PACIFIC
ISLANDER (3), OTHER (2), WHITE (142), NA (100). `MULTIPLE` and `OTHER`
are SDTMIG-prescribed extensions for the extensible RACE codelist
(C74457) — document in ADRG (same as ADAE/ADCE).

#### CT2002 — CMROUTE value not in 'Route of Administration' codelist (4 -> 0)
**Root cause**: Pre-fix SDTM CM passed CRF route values verbatim ("Oral",
"Intravaneous", numeric "3").
**Fix**: SDTM CM commit `93f08e1` added `map_route()` to canonicalise to
CDISC ROUTE (C66729). ADCM pulls the corrected CMROUTE from
`data/sdtm/cm.rds`.
**Coverage after fix**: ADCM.CMROUTE values are INTRAVENOUS (3), ORAL
(196), SUBCUTANEOUS (4), TOPICAL (24), NA (32).

#### AD0503 — *DT must contain 'Date' in the label (2 -> 0)
**Root cause**: Same root cause as AD0018 — the four `*DT` variables
(TRTSDT, TRTEDT, ASTDT, AENDT) had `LABEL=null`.
**Fix**: Label attachment makes each `*DT` variable carry the spec
label:
- TRTSDT: `Date of First Exposure to Treatment`
- TRTEDT: `Date of Last Exposure to Treatment`
- ASTDT:  `Analysis Start Date`
- AENDT:  `Analysis End Date`

All contain `Date`.

#### AD0361 — ASTDT > AENDT (1 -> 0)
**Root cause**: SDTM CM SD0013 — subject DF-193 had CMSTDAT `2021-08-05`
and CMENDAT `2021-08-03` (CRF inversion). SDTM CM fix (commit `93f08e1`)
nulled the demonstrably wrong CMENDTC and relied on the SD0021 escape
(CMENRTPT="UNKNOWN") to justify the missing end date.
**Fix**: Rebuild against corrected SDTM CM — no code change in ADCM.
ASTDT / AENDT derive from CMSTDTC / CMENDTC via
`admiral::derive_vars_dt()`, so the null CMENDTC propagates to null
AENDT and the inversion disappears.
**Coverage after fix**: 0 rows where ASTDT > AENDT.

### Known data limitations
| Rule | Residual count | Reason |
|------|----------------|--------|
| RACE = NA | 100 rows | Subjects with no PTRACE captured in raw DM. Upstream sparsity, not a code defect. |
| RACE = "MULTIPLE" / "OTHER" | 5 / 2 rows | SDTMIG-prescribed extensions for multi-race / unmapped raw values; race codelist (C74457) is extensible. Document in ADRG. |
| CMROUTE = NA | 32 rows | Raw "3" / blank in OpenClinica — no CDISC ROUTE equivalent. Documented in `domains/cm.md`. |
| CMDOSU / CMDOSFRM / CMDOSFRQ residuals | per `domains/cm.md` | Upstream "Other" / numeric-coded raw values that have no CDISC CT equivalent. CMDOSFRM / CMDOSFRQ are not surfaced in ADCM (no analysis need); CMDOSU residual NAs flow through. |
| AENDT = NA | 235 rows | CM records where the medication is ongoing (CMENRTPT="ONGOING") or end date is unknown (CMENRTPT="UNKNOWN"). Justified by CMENRTPT per SDTMIG; the missing AENDT is expected for ongoing therapies and triggers `ONTRTFL = "Y"` for any post-TRTSDT start. |

## Cross-dataset dependencies
| Dependency | Direction | Notes |
|------------|-----------|-------|
| `data/sdtm/cm.rds`   | CM -> ADCM  | Source of CMSEQ, CMTRT, CMDECOD, CMINDC, CMDOSE, CMDOSU, CMROUTE, CMSTDTC, CMENDTC, CMENRTPT. CT2002 / SD0013 fixes live in CM commit `93f08e1`. |
| `data/sdtm/dm.rds`   | DM -> ADSL -> ADCM | RACE / STUDYID / SUBJID. CT2002 RACE multi-select fix lives in DM (commit `af211c9`). |
| `data/adam/adsl.rds` | ADSL -> ADCM | SUBJID, SITEID, AGE, SEX, RACE, TRT01P, TRT01A, TRTSDT, TRTEDT, SAFFL. SAFFL Y/N fix lives in ADSL (commit `2c0f164`). |

## Rebuild command
```bash
Rscript program/sdtm/cm.R   2>&1 | grep -v "renv\|out-of-sync\|masked\|built under"
Rscript program/adam/adsl.R 2>&1 | grep -v "renv\|out-of-sync\|masked\|built under"
Rscript program/adam/adcm.R 2>&1 | grep -v "renv\|out-of-sync\|masked\|built under"
```

Expected output:
```
ADCM written: 259 rows x 27 cols
ADCM XPT exported to data/adam/adcm.xpt
```

## Sanity checks
```r
adcm <- readRDS("data/adam/adcm.rds")
stopifnot(ncol(adcm) == 27)
stopifnot(!is.null(attr(adcm, "label")))
# Every column has a label
stopifnot(all(vapply(adcm, function(x) !is.null(attr(x, "label")), logical(1))))
# *DT labels contain "Date"
for (v in grep("DT$", names(adcm), value = TRUE)) {
  stopifnot(grepl("Date", attr(adcm[[v]], "label"), fixed = TRUE))
}
# Population flags are Y/N (never NA)
stopifnot(sum(is.na(adcm$SAFFL)) == 0)
stopifnot(all(adcm$SAFFL %in% c("Y","N")))
# Analysis flags are Y or null only
stopifnot(all(is.na(adcm$ANL01FL) | adcm$ANL01FL == "Y"))
stopifnot(all(is.na(adcm$ONGOFL)  | adcm$ONGOFL  == "Y"))
stopifnot(all(is.na(adcm$PREFL)   | adcm$PREFL   == "Y"))
stopifnot(all(is.na(adcm$ONTRTFL) | adcm$ONTRTFL == "Y"))
# No date inversions
stopifnot(sum(!is.na(adcm$ASTDT) & !is.na(adcm$AENDT) &
              adcm$ASTDT > adcm$AENDT) == 0)
# CMSEQ unique within USUBJID
stopifnot(!anyDuplicated(adcm[, c("USUBJID","CMSEQ")]))
# Every USUBJID in ADCM appears in ADSL
adsl <- readRDS("data/adam/adsl.rds")
stopifnot(all(adcm$USUBJID %in% adsl$USUBJID))
```
