# ADLB — Dataset Knowledge

## Overview
ADLB is the BDS (Basic Data Structure) analysis dataset for laboratory test
results: one row per parameter per analysis timepoint per subject. Built
from `data/sdtm/lb.rds` (950 rows × 23 cols after dedup, CT alignment, and
LBDY derivation in commit `64694f5`) joined to `data/adam/adsl.rds`.

Current output: 950 rows × 30 cols across 169 subjects, 12 distinct PARAMCDs
(AMYLASE, CHOL, CL, CREAT, GFR, HCT, HGB, HOMOCY, RBC, TRIG, UREAN, WBC).

## Upstream sources
| Source | Variables consumed |
|--------|--------------------|
| `data/sdtm/lb.rds`     | STUDYID, USUBJID, LBSEQ, LBTESTCD, LBTEST, LBCAT, LBSTRESN, LBSTRESC, LBSTRESU, LBBLFL, VISIT, VISITNUM, LBDTC |
| `data/adam/adsl.rds`   | SUBJID, SITEID, AGE, SEX, RACE, TRT01P, TRT01A, TRTSDT, SAFFL |

## Key derivations

### Analysis date / day: ADT / ADY
`admiral::derive_vars_dt(new_vars_prefix = "A", dtc = LBDTC)` then
`admiral::derive_vars_dy(reference_date = TRTSDT, source_vars = exprs(ADT))`.
Year-only LBDTC values (`"2026"`) yield NA ADT.

### Parameter trio: PARAMCD / PARAM / PARAMN
- `PARAMCD = LBTESTCD` (CDISC C65047 lab-test codes).
- `PARAM = LBTEST + " (" + LBSTRESU + ")"` when units present.
- `PARAMN = dense_rank(PARAMCD)` — lexical dense rank over distinct codes
  in the dataset. The mapping is dataset-internal, not a fixed lookup.

### Baseline flag: ABLFL
`admiral::derive_var_extreme_flag()` with `order = exprs(desc(LBBLFL %in%
"Y"), ADT, LBSEQ)` — prefers LBBLFL = "Y" records, falls back to latest
pre-TRTSDT record per `(USUBJID, PARAMCD)`.

### Baseline / change: BASE / CHG / PCHG
`admiral::derive_var_base()` carries the ABLFL row's AVAL to every record
in `(USUBJID, PARAMCD)`; `derive_var_chg()` / `derive_var_pchg()` compute
CHG and PCHG (note: these admiral functions take **only** `dataset` — no
`new_var` argument; per `CLAUDE.md:170-173`).

### Analysis record flag: ANL01FL
Currently `"Y"` for every row (placeholder for future analysis-set rules).

### Label attachment
`metacore` / `xportr` / `labelled` are not installed in renv. Labels are
attached from `spec/adam/adlb.yaml` via:
```r
spec_yaml <- yaml::read_yaml("spec/adam/adlb.yaml")
for (v in names(adlb)) {
  lab <- spec_yaml$variables[[v]]$label
  if (!is.null(lab) && nzchar(lab)) attr(adlb[[v]], "label") <- lab
}
attr(adlb, "label") <- spec_yaml$label
```
Same pattern as ADCE / ADCM / ADDS / ADIE. Labels carry through to XPT via
`haven::write_xpt` reading the `label` attribute on each column.

## P21 rules and fixes

### Resolved rules

#### AD0019 — SAFFL subject-population flag value is null (546 → 0)
**Root cause**: The stale `data/adam/adlb.rds` was built before
ADSL.SAFFL was corrected to Y/N. The `left_join(adsl_vars, by = "USUBJID")`
propagated the old `SAFFL = NA` values into 546 ADLB rows.
**Fix**: No code change in ADLB beyond rebuilding against the corrected
ADSL (commit `2c0f164`). The existing `left_join` propagates the
corrected Y/N values verbatim.
**Coverage after fix**: 0 NA. Final distribution: 912 × "Y", 38 × "N"
across 950 rows.

#### AD0018 — Variable label mismatch (29 → 0)
**Root cause**: ADLB was written to RDS / XPT without any
`attr(x, "label")` attached; P21 saw `LABEL=null` for every variable.
The 29 flagged variables included ABLFL, ADT, ADY, AGE, ANL01FL, ANRHI,
ANRIND, ANRLO, ASEQ, AVAL, AVALC, AVALU, AVISIT, AVISITN, BASE, CHG,
PARAM, PARAMCD, PARAMN, PARCAT1, PCHG, RACE, SAFFL, SEX, SITEID, STUDYID,
SUBJID, TRT01A, TRT01P, USUBJID.
**Fix** (`program/adam/adlb.R`): manual label attachment from spec YAML
(see snippet above) plus the dataset-level label
`"Laboratory Test Results Analysis Dataset"` (40 chars — the V5 limit).
**Coverage after fix**: 30 / 30 columns labeled; dataset label set.

#### CT2002 — RACE value not in 'Race' codelist (10 → 0)
**Root cause**: Pre-fix `adsl.rds` carried raw numeric race codes like
`"1"`, `"5"`, `"1,5,6"` (PTRACE CRF values joined verbatim into ADSL).
DM was corrected (commit `af211c9`) to map numeric PTRACE codes through
CDISC RACE terminology with `"MULTIPLE"` for multi-select, and ADSL
inherits that.
**Fix**: No code change in ADLB beyond rebuilding against the corrected
ADSL. After rebuild ADLB.RACE values are the CDISC C74457 strings (WHITE,
BLACK OR AFRICAN AMERICAN, ASIAN, AMERICAN INDIAN OR ALASKA NATIVE,
NATIVE HAWAIIAN OR OTHER PACIFIC ISLANDER, OTHER, MULTIPLE) plus NA for
subjects with no PTRACE captured.
**Coverage after fix**: 0 codelist violations from raw numeric codes.

#### AD0503 — *DT must contain 'Date' in the label (1 → 0)
**Root cause**: ADT had `LABEL=null` (same root cause as AD0018), so the
"*DT label must contain Date" check could not pass.
**Fix**: Label attachment makes ADT carry the spec label
`"Analysis Date"`, which contains `"Date"`. ADT is the only `*DT`
variable in ADLB.

### Known data limitations
| Rule | Residual count | Reason |
|------|----------------|--------|
| ANRLO / ANRHI null | 950 rows | SDTM LB has no reference ranges in the raw export (LBORNRLO / LBORNRHI added as empty NA columns to satisfy SD0057, but actual ranges are absent in the OpenClinica source — only help-text "Normal range" annotations exist). |
| ANRIND null | 950 rows | Requires ANRLO / ANRHI — same root cause. `admiral::derive_var_anrind()` is the documented path once reference ranges are available. |
| ATOXGR not derived | n/a | NCI-CTCAE toxicity grading needs reference ranges + per-test grading rules — blocked on the same data gap. Would use `admiral::derive_var_atoxgr()` once data available. |
| RACE = "MULTIPLE" | varies | SDTMIG-prescribed extension for multi-race subjects; race codelist (C74457) is extensible. Document in ADRG. |
| RACE = NA | 32 subjects | Subjects with no PTRACE captured in raw DM. Upstream sparsity, not a code defect. |
| ADY null for year-only LBDTC | ~61 rows | LBDTC is year-only (`"2026"` from LABDATE follow-up form). Cannot derive a study day from a year alone. |

## Cross-dataset dependencies
| Dependency | Direction | Notes |
|------------|-----------|-------|
| `data/sdtm/lb.rds`   | LB → ADLB   | Source of all measurement variables. LB was cleaned in commit `64694f5` (dedup, CT alignment, LBDY, LBLOBXFL/LBORNRLO/LBORNRHI added). |
| `data/sdtm/dm.rds`   | DM → ADSL → ADLB | RACE flows. CT2002 RACE numeric-code fix lives in DM (commit `af211c9`). |
| `data/adam/adsl.rds` | ADSL → ADLB | SUBJID, SITEID, AGE, SEX, RACE, TRT01P, TRT01A, TRTSDT, SAFFL. SAFFL Y/N fix lives in ADSL (commit `2c0f164`). |

## Rebuild command
```bash
Rscript program/adam/adsl.R 2>&1 | grep -v "renv\|out-of-sync\|masked\|built under"
Rscript program/adam/adlb.R 2>&1 | grep -v "renv\|out-of-sync\|masked\|built under"
```

Expected output:
```
ADSL written: 810 rows x 35 cols
ADLB written: 950 rows x 30 cols
ADLB XPT exported to data/adam/adlb.xpt
```

## Sanity checks
```r
adlb <- readRDS("data/adam/adlb.rds")
stopifnot(ncol(adlb) == 30)
stopifnot(!is.null(attr(adlb, "label")))
# Every column has a label
stopifnot(all(vapply(adlb, function(x) !is.null(attr(x, "label")), logical(1))))
# *DT labels contain "Date"
for (v in grep("DT$", names(adlb), value = TRUE)) {
  stopifnot(grepl("Date", attr(adlb[[v]], "label"), fixed = TRUE))
}
# Population flags are Y/N (never NA, never blank)
stopifnot(sum(is.na(adlb$SAFFL)) == 0)
stopifnot(all(adlb$SAFFL %in% c("Y","N")))
# ABLFL is Y or null only
stopifnot(all(is.na(adlb$ABLFL) | adlb$ABLFL == "Y"))
# ANL01FL is Y or null only (never N per ADaMIG analysis-flag rule)
stopifnot(all(is.na(adlb$ANL01FL) | adlb$ANL01FL == "Y"))
# ABLFL unique per (USUBJID, PARAMCD)
bl <- subset(adlb, ABLFL == "Y")
stopifnot(!anyDuplicated(bl[, c("USUBJID", "PARAMCD")]))
# Every USUBJID in ADLB appears in ADSL
adsl <- readRDS("data/adam/adsl.rds")
stopifnot(all(adlb$USUBJID %in% adsl$USUBJID))
# PARAM, PARAMN are 1-to-1 with PARAMCD
trios <- unique(adlb[, c("PARAMCD","PARAM","PARAMN")])
stopifnot(nrow(trios) == length(unique(adlb$PARAMCD)))
```
