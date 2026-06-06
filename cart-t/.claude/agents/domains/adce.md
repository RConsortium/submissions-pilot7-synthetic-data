# ADCE — Dataset Knowledge

## Overview
ADCE is the OCCDS dataset for clinical events: one row per protocol-defined
clinical event per subject. The only event the study collects is Suspected MI,
so every emitted row has `CECAT = "SUSPECTED MI"` and `CEPRESP = "Y"`. Built
from `data/sdtm/ce.rds` (8 rows × 12 cols after canonicalisation + junk-row
drop in commit `c492afc`) joined to `data/adam/adsl.rds`.

Current output: 8 rows × 21 cols across 8 subjects (every subject contributes
exactly one CE row at the moment).

## Upstream sources
| Source | Variables consumed |
|--------|--------------------|
| `data/sdtm/ce.rds`     | STUDYID, USUBJID, CESEQ, CETERM, CECAT, CESER, CEPRESP, CEOCCUR, CESTDTC |
| `data/adam/adsl.rds`   | SUBJID, SITEID, AGE, SEX, RACE, STRAT1, TRT01P, TRT01A, TRTSDT, SAFFL |

## Key derivations

### Analysis dates: ASTDT / ASTDY
`admiral::derive_vars_dt(new_vars_prefix = "AST", dtc = CESTDTC)` then
`admiral::derive_vars_dy(reference_date = TRTSDT, source_vars =
exprs(ASTDT))`. There is no end date for CE in this study (Suspected MI is a
point event), so AENDT / ASTDY are not derived.

### First-occurrence flag: AOCCFL
`admiral::derive_var_extreme_flag()` ordered by `(ASTDT, CESEQ)` per
`USUBJID`. Every subject currently has exactly one CE row, so AOCCFL is "Y"
for every record; it would matter if MI recurred.

### Analysis record flag: ANL01FL
`"Y"` when `SAFFL = "Y"`; else null. With the corrected ADSL all 8 CE
subjects have `SAFFL = "Y"`, so all 8 ANL01FL are "Y".

### Per-record planned/actual treatment: TRT01P / TRT01A
Inherited verbatim from ADSL — single-period design. No per-record TRTP/TRTA
derived because CE events occur in screening, treatment, or follow-up epochs
and are not analysed per-arm in this pilot.

### Label attachment
`metacore` / `xportr` / `labelled` are not installed in renv. Labels are
attached from `spec/adam/adce.yaml` via:
```r
spec_yaml <- yaml::read_yaml("spec/adam/adce.yaml")
for (v in names(adce)) {
  lab <- spec_yaml$variables[[v]]$label
  if (!is.null(lab) && nzchar(lab)) attr(adce[[v]], "label") <- lab
}
attr(adce, "label") <- spec_yaml$label
```
Same pattern as ADSL and ADAE. Labels carry through to XPT via
`haven::write_xpt` reading the `label` attribute on each column.

## P21 rules and fixes

### Resolved rules

#### AD0018 — Variable label mismatch (14 → 0)
**Root cause**: ADCE was written to RDS / XPT without any `attr(x, "label")`
attached; P21 saw `LABEL=null` for every variable. The 14 flagged variables
were `AGE, ANL01FL, AOCCFL, ASTDT, ASTDY, CECAT, CEOCCUR, CEPRESP, CESEQ,
CESER, CETERM, RACE, SAFFL, SEX` — the eight ADSL-merged columns came in
with labels via the `left_join`, but all native-CE and derived variables
were unlabelled. Dataset-level label was also null (AD0320 territory).
**Fix** (`program/adam/adce.R`): manual label attachment from spec YAML
(see snippet above).
**Coverage after fix**: 21 / 21 columns labeled; dataset label is
`"Clinical Events Analysis Dataset"`.

#### AD0019 — Safety Population Flag null (7 → 0)
**Root cause**: Pre-fix `adsl.rds` had `SAFFL = NA` for screen-failure
subjects, and the `left_join(adsl_vars, by = "USUBJID")` propagated those
NAs into ADCE. ADSL was corrected in commit `2c0f164` (population flags
must be Y/N per ADaMIG).
**Fix**: No code change in ADCE — just rebuild against the corrected ADSL.
The existing `left_join` propagates the corrected Y/N values verbatim.
`convert_blanks_to_na()` does not affect "N" (only blank strings).
**Coverage after fix**: 0 NA, all 8 rows have SAFFL = "Y" because all 8
CE subjects were exposed (CE only emits rows for subjects who actually
had Suspected MI events captured).

#### CT2002 — RACE value not in 'Race' codelist (2 → 0 ADCE-side)
**Root cause**: Pre-fix `adsl.rds` carried RACE = `"1,5,6"` (raw
multi-select coded value joined verbatim) for one CE subject. DM was
corrected to emit `"MULTIPLE"` for multi-select PTRACE per SDTMIG, and
ADSL inherits that value.
**Fix**: No code change in ADCE — just rebuild against the corrected ADSL.
After rebuild ADCE.RACE values are: 3 × `"WHITE"`, 1 × `"MULTIPLE"`, 4 ×
NA. `"MULTIPLE"` is the SDTMIG-prescribed extension for multi-race
subjects (the RACE codelist C74457 is extensible) so P21 may still flag
it, but submission ADRG should call that out as a documented extension —
same as ADAE.
**Coverage after fix**: 0 codelist violations from `"1,5,6"`.

#### AD0503 — *DT must contain 'Date' in the label (1 → 0)
**Root cause**: ASTDT had `LABEL=null` (same root cause as AD0018), so
the "*DT label must contain Date" check could not pass.
**Fix**: Label attachment makes ASTDT carry the spec label `"Analysis
Start Date"`, which contains `"Date"`. ASTDT is the only `*DT` variable
in ADCE.

### Known data limitations
| Rule | Residual count | Reason |
|------|----------------|--------|
| RACE = "MULTIPLE" | 1 row | SDTMIG-prescribed extension for multi-race subjects; race codelist (C74457) is extensible. Document in ADRG. |
| RACE = NA | 4 rows | Subjects with no PTRACE captured in raw DM. Upstream sparsity, not a code defect. |
| AOCCFL = "Y" for every row | 8/8 rows | Every subject currently has exactly one CE event. AOCCFL would only differentiate if MI recurred for any subject in this synthetic export. |
| No CEDECOD / CEBODSYS | n/a | No MedDRA coding workflow in the OpenClinica export (documented in `domains/ce.md`). |

## Cross-dataset dependencies
| Dependency | Direction | Notes |
|------------|-----------|-------|
| `data/sdtm/ce.rds`   | CE → ADCE   | Source of CESEQ, CETERM, CECAT, CESER, CEPRESP, CEOCCUR, CESTDTC. CE was cleaned up in commit `c492afc` (junk rows dropped, CETERM canonicalised). |
| `data/sdtm/dm.rds`   | DM → ADSL → ADCE | RACE / STUDYID / SUBJID flow. CT2002 RACE = `"1,5,6"` fix lives in DM (commit `af211c9`). |
| `data/adam/adsl.rds` | ADSL → ADCE | SUBJID, SITEID, AGE, SEX, RACE, STRAT1, TRT01P, TRT01A, TRTSDT, SAFFL. SAFFL Y/N fix lives in ADSL (commit `2c0f164`). |

## Rebuild command
```bash
Rscript program/adam/adsl.R 2>&1 | grep -v "renv\|out-of-sync\|masked\|built under"
Rscript program/adam/adce.R 2>&1 | grep -v "renv\|out-of-sync\|masked\|built under"
```

Expected output:
```
ADSL written: 810 rows x 35 cols
ADCE written: 8 rows x 21 cols
ADCE XPT exported to data/adam/adce.xpt
```

## Sanity checks
```r
adce <- readRDS("data/adam/adce.rds")
stopifnot(ncol(adce) == 21)
stopifnot(!is.null(attr(adce, "label")))
# Every column has a label
stopifnot(all(vapply(adce, function(x) !is.null(attr(x, "label")), logical(1))))
# *DT labels contain "Date"
for (v in grep("DT$", names(adce), value = TRUE)) {
  stopifnot(grepl("Date", attr(adce[[v]], "label"), fixed = TRUE))
}
# Population flags are Y/N (never NA, never blank)
stopifnot(sum(is.na(adce$SAFFL)) == 0)
stopifnot(all(adce$SAFFL %in% c("Y","N")))
# ANL01FL is Y or null only (never N per ADaMIG analysis-flag rule)
stopifnot(all(is.na(adce$ANL01FL) | adce$ANL01FL == "Y"))
# AOCCFL is Y or null only
stopifnot(all(is.na(adce$AOCCFL) | adce$AOCCFL == "Y"))
# Every USUBJID in ADCE appears in ADSL
adsl <- readRDS("data/adam/adsl.rds")
stopifnot(all(adce$USUBJID %in% adsl$USUBJID))
```
