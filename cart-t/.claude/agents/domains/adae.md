# ADAE — Dataset Knowledge

## Overview
ADAE is the OCCDS dataset for adverse events: one row per AE per subject,
carrying SDTM AE qualifiers, ADSL treatment / population / phenotype
context, analysis dates and the standard occurrence flags. Built from
`data/sdtm/ae.rds` (327 rows × 27 cols) joined to `data/adam/adsl.rds`.

Current output: 327 rows × 48 cols across 230 unique subjects.

## Upstream sources
| Source | Variables consumed |
|--------|--------------------|
| `data/sdtm/ae.rds`     | STUDYID, USUBJID, AESEQ, AESPID, AETERM, AEDECOD, AEBODSYS, AESEV, AESER, AEREL, AEOUT, AESTDTC, AEENDTC |
| `data/adam/adsl.rds`   | SUBJID, SITEID, AGE, AGEGR1, SEX, RACE, TRT01P, TRT01PN, TRT01A, TRT01AN, TRTSDT, TRTEDT, STRAT1, STRAT1L, RANDFL, ITTFL, SAFFL |

## Key derivations

### Analysis dates: ASTDT / AENDT / ASTDY / AENDY
`admiral::derive_vars_dt()` on `AESTDTC` / `AEENDTC`; relative days via
`admiral::derive_vars_dy(reference_date = TRTSDT, source_vars =
exprs(ASTDT, AENDT))`. SDTM AE already nulled out `AEENDTC < AESTDTC`
rows so `ASTDT > AENDT` is impossible.

### Per-record treatment: TRTP / TRTPN / TRTA / TRTAN
Single-period study so all four equal the corresponding ADSL
`TRT01x` values.

### Analysis severity / causality: ASEV / AREL
Verbatim copies of `AESEV` / `AEREL` (per OCCDS IG analysis-side
variables). Conservative choice — `AREL` keeps the four raw causality
values (`NOT_RELATED`, `POSSIBLY_RELATED`, `RELATED`, `UNLIKELY_RELATED`)
rather than collapsing into related/not-related; collapsing is a
study-level decision that would need a SAP.

### TRTEMFL
`"Y"` when `ASTDT >= TRTSDT` AND (`TRTEDT` is null OR `ASTDT <= TRTEDT +
30 days`); else null. 54 / 327 AEs flag as treatment-emergent; the rest
either occurred outside the window or for subjects with no `TRTSDT`
(SCRNFAIL).

### First-occurrence flags
`admiral::derive_var_extreme_flag()` ordered by `(ASTDT, AESEQ)` for
`AOCCFL` (per USUBJID), `AOCCPFL` (per USUBJID, AEDECOD), `AOCCSFL`
(per USUBJID, AEBODSYS). AEBODSYS is always null in this pilot so
`AOCCSFL` is effectively first-AE-per-subject.

### Label attachment
`metacore` / `xportr` / `labelled` are not installed in renv. Labels
are attached from `spec/adam/adae.yaml` via:
```r
spec_yaml <- yaml::read_yaml("spec/adam/adae.yaml")
for (v in names(adae)) {
  lab <- spec_yaml$variables[[v]]$label
  if (!is.null(lab) && nzchar(lab)) attr(adae[[v]], "label") <- lab
}
attr(adae, "label") <- spec_yaml$label
```

## P21 rules and fixes

### Resolved rules

#### AD0018 — Variable label mismatch (30 → 0)
**Root cause**: No labels attached to any column except the eight
inherited from `derive_vars_merged()`/`left_join()` ADSL columns. XPT
export written without `attr(x, "label")` → P21 sees `LABEL=null`.
**Fix** (`program/adam/adae.R`): manual label attachment from spec
YAML (see snippet above). Same pattern as ADSL.
**Coverage after fix**: 48 / 48 columns labeled.

#### AD0503 — *DT must contain 'Date' in the label (2 → 0)
**Root cause**: Same as AD0018.
**Fix**: All four `*DT` labels in the spec already contain "Date":
- `ASTDT` → "Analysis Start Date"
- `AENDT` → "Analysis End Date"
- `TRTSDT` → "Date of First Exposure to Treatment"
- `TRTEDT` → "Date of Last Exposure to Treatment"

#### AD0047 — Required variable not present (12 → 0)
**Root cause**: OCCDS-required per-record treatment and population
variables were not derived. Missing list:
1-2. `TRTP`, `TRTPN` — Planned per-record treatment
3-4. `TRTA`, `TRTAN` — Actual per-record treatment
5-6. `TRTSDT`, `TRTEDT` — reference treatment dates (predecessor from ADSL)
7. `ASEV` — Analysis severity
8. `AREL` — Analysis causality
9-10. `RANDFL`, `ITTFL` — Population flags (predecessor from ADSL)
11-12. `AESTDTC`, `AEENDTC` — Predecessor SDTM character dates

Plus `STRAT1` / `STRAT1L` per CART-T study decision (carries phenotype
stratum forward to OCCDS — see `CLAUDE.md`).
**Fix** (`program/adam/adae.R`): added to ADSL merge and to the final
`select()` block.
**Coverage after fix**: 48 cols in ADAE (was 32).

#### CT2002 — RACE value not in 'Race' codelist (10 → 6 residual)
**Root cause**: ADSL.RACE inherited from corrected DM. The DM mapping
correctly emits `"MULTIPLE"` for multi-select PTRACE per SDTMIG
guidance (multiple race codes comma-separated → `"MULTIPLE"`).
However `"MULTIPLE"` is a sponsor-defined extension of the extensible
RACE codelist (C74457), so P21 flags it.
**Fix**: No code change — `"MULTIPLE"` is the SDTMIG-prescribed value
and the codelist is extensible. The downstream-correct behavior is to
leave it. The previous count of 10 will reduce to 6 after the ADSL
rebuild flows through.
**Status**: documented as a known limitation. Submission ADRG should
note that `"MULTIPLE"` is the SDTMIG-blessed extension for multi-race
subjects.

#### AD0361 — ASTDT > AENDT (5 → 0)
**Root cause**: Inherited from SDTM AE — 5 raw rows had `AEENDDAT <
AESTDAT`.
**Fix**: SDTM AE (commit `7a620f3`, rule SD0013) nulls out
`AEENDTC` when `< AESTDTC`. `derive_vars_dt()` therefore returns
`AENDT = NA` for those rows, so the inequality cannot trigger.
**Coverage after fix**: 0 violations.

### Known data limitations
| Rule | Residual count | Reason |
|------|---------------|--------|
| CT2002 RACE = MULTIPLE | 6 rows | SDTMIG-prescribed extension for multi-race subjects; race codelist is extensible. |
| AEBODSYS null | 327 rows | Inherited from SDTM AE — no MedDRA coding workflow in OpenClinica export. Drives `AOCCSFL` to be functionally identical to `AOCCFL`. |
| AEDECOD = uppercased AETERM | 327 rows | Inherited from SDTM AE — synthetic stand-in for MedDRA PT. |
| TRTEMFL null for SCRNFAIL | 56 rows | No `TRTSDT` because the 530 SCRNFAIL subjects were never treated (no exposure data in this study). |
| AREL non-CT values | 311 rows | Inherited from SDTM AE — raw values `NOT_RELATED` / `POSSIBLY_RELATED` / `RELATED` / `UNLIKELY_RELATED` are not the CDISC AEREL CT (`NOT RELATED`, `RELATED`, `NOT APPLICABLE`). Collapsing requires SAP guidance. |

## Cross-dataset dependencies
| Dependency | Direction | Notes |
|------------|-----------|-------|
| `data/sdtm/ae.rds`   | AE → ADAE | Source of all AE qualifiers, dates, and per-record sequence (AESEQ → ASEQ proxy). Rebuild ADAE whenever AE changes. |
| `data/sdtm/dm.rds`   | DM → ADSL → ADAE | RACE / STUDYID / SUBJID flow. CT2002 RACE was fixed in DM (commit `af211c9`); rebuild ADSL then ADAE. |
| `data/adam/adsl.rds` | ADSL → ADAE | TRTSDT/TRTEDT/TRT01x/SAFFL/RANDFL/ITTFL/STRAT1*. Any ADSL pop-flag fix multiplies into ADAE. |

## Rebuild command
```bash
Rscript program/adam/adsl.R 2>&1 | grep -v "renv\|out-of-sync\|masked\|built under"
Rscript program/adam/adae.R 2>&1 | grep -v "renv\|out-of-sync\|masked\|built under"
```

Expected output:
```
ADSL written: 810 rows x 35 cols
ADAE written: 327 rows x 48 cols
ADAE XPT exported to data/adam/adae.xpt
```

## Sanity checks
```r
adae <- readRDS("data/adam/adae.rds")
stopifnot(ncol(adae) == 48)
stopifnot(!is.null(attr(adae, "label")))
stopifnot(all(vapply(adae, function(x) !is.null(attr(x, "label")), logical(1))))
stopifnot(sum(!is.na(adae$ASTDT) & !is.na(adae$AENDT) & adae$ASTDT > adae$AENDT) == 0)
# All *DT labels contain "Date"
for (v in grep("DT$", names(adae), value = TRUE)) {
  stopifnot(grepl("Date", attr(adae[[v]], "label"), fixed = TRUE))
}
# Required variables present
req <- c("STUDYID","USUBJID","AESEQ","AETERM","AEDECOD","ASTDT","AENDT",
         "TRTP","TRTPN","TRTA","TRTAN","TRTSDT","TRTEDT",
         "ASEV","AREL","SAFFL","RANDFL","ITTFL","AOCCFL","TRTEMFL")
stopifnot(all(req %in% names(adae)))
```
