# ADMH — Dataset Knowledge

## Overview
ADMH is the OCCDS dataset for medical history: one row per medical history
event per subject. Built from `data/sdtm/mh.rds` (607 rows × 20 cols after
the SDTM MH cleanup in commit `1b7369a`) joined to `data/adam/adsl.rds`.

Current output: 607 rows × 25 cols across 256 unique subjects.

## Upstream sources
| Source | Variables consumed |
|--------|--------------------|
| `data/sdtm/mh.rds`     | STUDYID, USUBJID, MHSEQ, MHTERM, MHDECOD, MHBODSYS, MHCAT, MHSCAT, MHSTDTC, MHENDTC, MHENRTPT |
| `data/adam/adsl.rds`   | SUBJID, SITEID, AGE, AGEGR1, SEX, RACE, TRT01P, TRT01A, TRTSDT, SAFFL, ITTFL |

Note: SDTM MH's `MHPRESP`, `MHOCCUR`, `MHSTAT` were dropped upstream (no
source data); `MHENRF` is still emitted but ADMH consumes `MHENRTPT`
instead (same convention used by ADCM with `CMENRTPT`). If a future SDTM
MH refresh drops `MHENRF` entirely, ADMH stays unaffected.

## Key derivations

### Analysis dates: ASTDT / AENDT / ASTDY / AENDY
`admiral::derive_vars_dt(new_vars_prefix = "AST", dtc = MHSTDTC)` then
`admiral::derive_vars_dt(new_vars_prefix = "AEN", dtc = MHENDTC)`; relative
days via `admiral::derive_vars_dy(reference_date = TRTSDT, source_vars =
exprs(ASTDT, AENDT))`. SDTM MH already passes its MHSTDTC/MHENDTC values
through `normalize_iso_date()` so admiral's strict ISO 8601 requirement
is satisfied.

### Ongoing flag: ONGOFL
```r
ONGOFL = dplyr::if_else(!is.na(MHENRTPT) & MHENRTPT == "ONGOING",
                        "Y", NA_character_)
```
SDTM MH wires `MHENRTPT = "ONGOING"` when the raw ONG item is `"1"` (Yes).
Same pattern as ADCM via CMENRTPT.

### Pre-existing history flag: PREHISFL
```r
PREHISFL = dplyr::case_when(
  !is.na(MHENRTPT) & MHENRTPT == "ONGOING"            ~ "Y",
  !is.na(ASTDT) & !is.na(TRTSDT) & ASTDT <= TRTSDT    ~ "Y",
  !is.na(ASTDT) & is.na(TRTSDT)                       ~ "Y",
  TRUE                                                ~ NA_character_
)
```
Captures conditions present at or before study start. Subjects who never
got treatment (no TRTSDT — the 530 SCRNFAIL subjects) still get
PREHISFL="Y" if they have any dated MH row, since their CRF-reported
medical history precedes any hypothetical treatment.

### Label attachment
`metacore` / `xportr` / `labelled` are not installed in renv. Labels are
attached from `spec/adam/admh.yaml` via:
```r
spec_yaml <- yaml::read_yaml("spec/adam/admh.yaml")
for (v in names(admh)) {
  lab <- spec_yaml$variables[[v]]$label
  if (!is.null(lab) && nzchar(lab)) attr(admh[[v]], "label") <- lab
}
attr(admh, "label") <- spec_yaml$label
```
Same pattern as ADCE / ADCM / ADAE / ADLB / ADDS / ADIE.

## P21 rules and fixes

### Resolved rules

#### AD0019 — Population flag null (821 → 0)
**Root cause**: Pre-fix `adsl.rds` had `SAFFL = NA` (214 rows in ADMH) and
`ITTFL = NA` (607 rows in ADMH) for screen-failure / non-ITT subjects.
The `left_join(adsl_vars, by = "USUBJID")` propagated those NAs verbatim.
ADSL was corrected in commit `2c0f164` (population flags must be Y/N per
ADaMIG).
**Fix**: No code change in ADMH for the flags themselves — just rebuild
against the corrected ADSL. The existing `left_join` propagates the
corrected Y/N values verbatim.
**Coverage after fix**: 0 NA in both SAFFL (607 Y) and ITTFL (429 Y,
178 N).

#### AD0018 — Variable label mismatch (16 → 0)
**Root cause**: ADMH was written to RDS / XPT without any `attr(x,
"label")` attached; P21 saw `LABEL=null` for every native or derived
variable. Dataset-level label was also null.
**Fix** (`program/adam/admh.R`): manual label attachment from spec YAML
(see snippet above).
**Coverage after fix**: 25 / 25 columns labeled; dataset label is
`"Medical History Analysis Dataset"`.

#### AD0503 — *DT must contain 'Date' in the label (2 → 0)
**Root cause**: ASTDT and AENDT had `LABEL=null` (same root cause as
AD0018), so the "*DT label must contain Date" check could not pass.
**Fix**: Label attachment makes ASTDT carry `"Analysis Start Date"` and
AENDT carry `"Analysis End Date"`. Both contain `"Date"`.

#### CT2002 — RACE value not in 'Race' codelist (16 → 0)
**Root cause**: Pre-fix `adsl.rds` carried raw multi-select coded
strings like `"1,5,6"` for RACE. DM was corrected (commit `af211c9`) to
emit `"MULTIPLE"` for multi-select PTRACE per SDTMIG, and ADSL inherits
that value.
**Fix**: No code change in ADMH — just rebuild against the corrected
ADSL.
**Coverage after fix**: 0 raw-coded values. RACE distribution is 507 ×
WHITE, 36 × MULTIPLE, 25 × AMERICAN INDIAN OR ALASKA NATIVE, 18 ×
ASIAN, 9 × NATIVE HAWAIIAN OR OTHER PACIFIC ISLANDER, 5 × OTHER, 4 ×
BLACK OR AFRICAN AMERICAN, 3 × NA. `"MULTIPLE"` is the SDTMIG-prescribed
extension for multi-race subjects (the RACE codelist C74457 is
extensible). Document in ADRG — same as ADCE.

#### AD0361 — ASTDT > AENDT (1 → 0)
**Root cause**: SDTM MH had one inverted row (subject DF-506: MHSTDTC
2020-03-03, MHENDTC 2020-02-05). SDTM MH commit `1b7369a` nulled out
the inverted MHENDTC and substituted `MHENRTPT="UNKNOWN" +
MHENTPT="DATE OF LAST ASSESSMENT"`.
**Fix**: No code change in ADMH — just rebuild against the corrected
SDTM MH. With MHENDTC=NA, AENDT is also NA so the inequality cannot
trigger.
**Coverage after fix**: 0 rows with `ASTDT > AENDT`.

### Known data limitations
| Rule / column | Residual count | Reason |
|---------------|----------------|--------|
| MHDECOD all-NA   | 607 rows | No MedDRA-coded layer in synthetic export. Same gap as AE/CE. |
| MHBODSYS all-NA  | 607 rows | Same MedDRA coding gap. |
| ASTDT NA         | 428 rows | Inherited from MHSTDTC sparsity (raw CRF DATE/DIAGNOSED unpopulated). |
| AENDT NA         | 566 rows | Inherited from MHENDTC sparsity (ongoing or unrecorded). |
| ASTDY/AENDY NA   | 428 / 566 rows | Inherited from ASTDT/AENDT NA, or subject has no TRTSDT (SCRNFAIL). |
| RACE = "MULTIPLE" | 36 rows | SDTMIG-prescribed extension for multi-race subjects; race codelist C74457 is extensible. Document in ADRG. |
| RACE = NA         | 3 rows  | Subjects with no PTRACE captured in raw DM. Upstream sparsity, not a code defect. |

## Cross-dataset dependencies
| Dependency | Direction | Notes |
|------------|-----------|-------|
| `data/sdtm/mh.rds`   | MH → ADMH   | Source of MHSEQ, MHTERM, MHDECOD, MHBODSYS, MHCAT, MHSCAT, MHSTDTC, MHENDTC, MHENRTPT. SDTM MH cleanup lives in commit `1b7369a` (relative-timing for SD0021/22, dedup, MHSTDY, SD0013 null-out). |
| `data/sdtm/dm.rds`   | DM → ADSL → ADMH | RACE / STUDYID / SUBJID flow. CT2002 RACE multi-select fix lives in DM (commit `af211c9`). |
| `data/adam/adsl.rds` | ADSL → ADMH | SUBJID, SITEID, AGE, AGEGR1, SEX, RACE, TRT01P, TRT01A, TRTSDT, SAFFL, ITTFL. Population flag Y/N fix lives in ADSL (commit `2c0f164`). |

## Rebuild command
```bash
Rscript program/adam/adsl.R 2>&1 | grep -v "renv\|out-of-sync\|masked\|built under"
Rscript program/adam/admh.R 2>&1 | grep -v "renv\|out-of-sync\|masked\|built under"
```

Expected output:
```
ADSL written: 810 rows x 35 cols
ADMH written: 607 rows x 25 cols
ADMH XPT exported to data/adam/admh.xpt
```

## Sanity checks
```r
admh <- readRDS("data/adam/admh.rds")
stopifnot(ncol(admh) == 25)
stopifnot(!is.null(attr(admh, "label")))
# Every column has a label
stopifnot(all(vapply(admh, function(x) !is.null(attr(x, "label")), logical(1))))
# *DT labels contain "Date"
for (v in grep("DT$", names(admh), value = TRUE)) {
  stopifnot(grepl("Date", attr(admh[[v]], "label"), fixed = TRUE))
}
# Population flags are Y/N (never NA, never blank)
stopifnot(sum(is.na(admh$SAFFL)) == 0)
stopifnot(sum(is.na(admh$ITTFL)) == 0)
stopifnot(all(admh$SAFFL %in% c("Y","N")))
stopifnot(all(admh$ITTFL %in% c("Y","N")))
# Analysis flags are Y or null only
stopifnot(all(is.na(admh$PREHISFL) | admh$PREHISFL == "Y"))
stopifnot(all(is.na(admh$ONGOFL)   | admh$ONGOFL   == "Y"))
# ASTDT never after AENDT
stopifnot(sum(!is.na(admh$ASTDT) & !is.na(admh$AENDT) &
              admh$ASTDT > admh$AENDT) == 0)
# Every USUBJID in ADMH appears in ADSL
adsl <- readRDS("data/adam/adsl.rds")
stopifnot(all(admh$USUBJID %in% adsl$USUBJID))
```
