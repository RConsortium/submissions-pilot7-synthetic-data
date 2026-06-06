# ADIE — Dataset Knowledge

## Overview
ADIE is the OCCDS dataset for Inclusion/Exclusion criteria not met: one row
per failed I/E criterion per subject. Built from `data/sdtm/ie.rds` (20
rows × ~14 cols after the SD fixes in commit `c5b9f8c` — IEORRES semantics
flipped to "criterion NOT met" + EPOCH + IEDY added) left-joined to
`data/adam/adsl.rds`.

Current output: 20 rows × 19 cols across 17 unique subjects (14 screen
failures contributing 17 rows + 3 randomized subjects contributing 3 rows).

## Upstream sources
| Source | Variables consumed |
|--------|--------------------|
| `data/sdtm/ie.rds`     | STUDYID, USUBJID, IESEQ, IETESTCD, IETEST, IECAT, IESCAT, IEORRES, IEDTC, VISIT |
| `data/adam/adsl.rds`   | SUBJID, SITEID, AGE, SEX, RACE, STRAT1, TRT01P, TRTSDT, RANDFL |

## Key derivations

### Analysis date: ADT / ADY
`admiral::derive_vars_dt(new_vars_prefix = "A", dtc = IEDTC)` then
`admiral::derive_vars_dy(reference_date = TRTSDT, source_vars = exprs(ADT))`.
There is no end date for IE (point-in-time criterion failure).

### Screen-failure flag: SCRNFFL
"Y" when `ADSL.RANDFL == "N"` (subject was not randomized); else null. Per
ADaMIG, `RANDFL` is `"Y"`/`"N"` (never `NA`), so the test is on the actual
value, not `is.na()`. Renamed from `SCRNFAILFL` (10 chars, exceeded SAS V5
8-char limit per P21 AD0013 / SD1474).

### Label attachment
`metacore` / `xportr` / `labelled` are not installed in renv. Labels are
attached from `spec/adam/adie.yaml` via:
```r
spec_yaml <- yaml::read_yaml("spec/adam/adie.yaml")
for (v in names(adie)) {
  lab <- spec_yaml$variables[[v]]$label
  if (!is.null(lab) && nzchar(lab)) attr(adie[[v]], "label") <- lab
}
attr(adie, "label") <- spec_yaml$label
```
Same pattern as ADSL / ADAE / ADCE / ADCM / ADDS. Labels carry through to
XPT via `haven::write_xpt` reading the `label` attribute on each column.

## P21 rules and fixes

### Resolved rules

#### AD0013 / SD1474 — Illegal variable name (>8 chars)
**Root cause**: `SCRNFAILFL` is 10 chars; SAS V5 transport limit is 8 chars.
**Fix** (`program/adam/adie.R` + `spec/adam/adie.yaml`): renamed to
`SCRNFFL` (7 chars). No other program references `SCRNFAILFL`
(`grep -r SCRNFAILFL program/ spec/` returned only the ADIE files
before this fix).
**Coverage after fix**: 0 / 19 variable names exceed 8 chars.

#### AD0018 — Variable label mismatch (7 → 0)
**Root cause**: ADIE was written to RDS / XPT without any
`attr(x, "label")` attached; P21 saw `LABEL=null` for every variable. The
seven flagged variables (AGE, RACE, SEX, SITEID, and others) were
unlabelled. Dataset-level label was also null (AD0320 territory).
**Fix** (`program/adam/adie.R`): manual label attachment from spec YAML
(see snippet above).
**Coverage after fix**: 19 / 19 columns labelled; dataset label is
`"Inclusion/Exclusion Analysis Dataset"`.

#### AD0503 — *DT must contain 'Date' in the label (1 → 0)
**Root cause**: ADT had `LABEL=null` (same root cause as AD0018), so the
"*DT label must contain Date" check could not pass.
**Fix**: Label attachment makes ADT carry the spec label `"Analysis Date"`,
which contains `"Date"`. ADT is the only `*DT` variable in ADIE.

#### CT2002 — RACE value not in 'Race' codelist (2 → 0 ADIE-side)
**Root cause**: Pre-fix `adsl.rds` carried raw multi-select coded values
(e.g. `"1"`, `"5"`) for some IE subjects. DM was corrected in commit
`af211c9` to emit `"MULTIPLE"` for multi-select PTRACE per SDTMIG, and
ADSL inherits that value.
**Fix**: No code change in ADIE — just rebuild against the corrected ADSL.
After rebuild ADIE.RACE values are 3 × `"WHITE"`, 1 × `"AMERICAN INDIAN OR
ALASKA NATIVE"`, 16 × NA. No raw `"1"`/`"5"` values remain.
**Coverage after fix**: 0 codelist violations from raw coded values.

### Known data limitations
| Rule | Residual count | Reason |
|------|----------------|--------|
| RACE = NA | 16 rows | Subjects with no PTRACE captured in raw DM. Upstream sparsity, not a code defect. |
| SCRNFFL = NA | 3 rows | 3 ADIE rows are for subjects who were randomized despite having an IE failure recorded — they are not "screen failures" per ADaMIG so SCRNFFL is null. |
| AVISIT often null | n/a | IE.VISIT is null for some entries; carried through verbatim. |

## Cross-dataset dependencies
| Dependency | Direction | Notes |
|------------|-----------|-------|
| `data/sdtm/ie.rds`   | IE → ADIE   | Source of IESEQ, IETESTCD, IETEST, IECAT, IESCAT, IEORRES, IEDTC, VISIT. IE was cleaned up in commit `c5b9f8c` (IEORRES semantics, EPOCH, IEDY). |
| `data/sdtm/dm.rds`   | DM → ADSL → ADIE | RACE / STUDYID / SUBJID flow. CT2002 RACE fix lives in DM (commit `af211c9`). |
| `data/adam/adsl.rds` | ADSL → ADIE | SUBJID, SITEID, AGE, SEX, RACE, STRAT1, TRT01P, TRTSDT, RANDFL. RANDFL Y/N fix lives in ADSL (commit `2c0f164`). |

## Rebuild command
```bash
Rscript program/adam/adsl.R 2>&1 | grep -v "renv\|out-of-sync\|masked\|built under"
Rscript program/adam/adie.R 2>&1 | grep -v "renv\|out-of-sync\|masked\|built under"
```

Expected output:
```
ADSL written: 810 rows x 35 cols
ADIE written: 20 rows x 19 cols
ADIE XPT exported to data/adam/adie.xpt
```

## Sanity checks
```r
adie <- readRDS("data/adam/adie.rds")
stopifnot(ncol(adie) == 19)
stopifnot(!is.null(attr(adie, "label")))
# Every column has a label
stopifnot(all(vapply(adie, function(x) !is.null(attr(x, "label")), logical(1))))
# *DT labels contain "Date"
for (v in grep("DT$", names(adie), value = TRUE)) {
  stopifnot(grepl("Date", attr(adie[[v]], "label"), fixed = TRUE))
}
# No variable name exceeds 8 chars (SAS V5 limit)
stopifnot(all(nchar(names(adie)) <= 8))
# SCRNFFL is Y or null only (never N per ADaMIG analysis-flag rule)
stopifnot(all(is.na(adie$SCRNFFL) | adie$SCRNFFL == "Y"))
# Every USUBJID in ADIE appears in ADSL
adsl <- readRDS("data/adam/adsl.rds")
stopifnot(all(adie$USUBJID %in% adsl$USUBJID))
```
