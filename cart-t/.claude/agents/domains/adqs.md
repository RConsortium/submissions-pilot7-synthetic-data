# ADQS — Dataset Knowledge

## Overview
ADQS is the BDS analysis dataset for the SF-12 questionnaire — one
record per item or subscale per analysis timepoint per subject. Built
from `data/sdtm/qs.rds` (3,611 rows × 19 cols across 247 SF-12
respondents) joined to `data/adam/adsl.rds`. SF-12 is the only
questionnaire instrument in this pilot; EQ-5D-5L and the Skin
Conditions Questionnaire are absent from the OpenClinica export and
cannot be built.

Current output: 3,611 rows × 27 cols across 247 subjects, 16 distinct
PARAMCDs (12 items + 4 subscales BP / GH / VT / SF). Composite
subscales PF / RP / RE / MH are reserved in the parameter lookup
(PARAMN 13, 14, 19, 20) for forward-compatibility but never emit rows
in this pilot because the raw export only carries the A/S components.

## Upstream sources
| Source | Variables consumed |
|--------|--------------------|
| `data/sdtm/qs.rds`     | STUDYID, USUBJID, QSSEQ, QSTESTCD, QSTEST, QSCAT, QSSCAT, QSSTRESC, QSSTRESN, QSBLFL, VISITNUM, VISIT, QSDTC |
| `data/adam/adsl.rds`   | SUBJID, SITEID, AGE, SEX, RACE, TRT01P, TRT01A, TRTSDT, EFFFL |

## Key derivations

### Analysis dates: ADT / ADY
`admiral::derive_vars_dt(new_vars_prefix = "A", dtc = QSDTC)` then
`admiral::derive_vars_dy(reference_date = TRTSDT, source_vars =
exprs(ADT))`.

### Parameter trio: PARAMCD / PARAM / PARAMN
A dataset-level `(PARAMCD, PARAM, PARAMN)` lookup defined inline in
`program/adam/adqs.R` is merged onto every BDS row via
`admiral::derive_vars_merged(by_vars = exprs(PARAMCD))` so that PARAM
and PARAMN are exact 1-to-1 functions of PARAMCD. PARAM takes the form
`"SF-12 Q01 General Health (SF1201)"` for item rows and
`"SF-12 <subscale label> Subscale (<PARAMCD>)"` for subscale rows.
PARAMN is the canonical SF-12 v1 dictionary index: items SF1201..SF1212
are 1..12; subscales PF/RP/BP/GH/VT/SF/RE/MH are 13..20.

### Baseline: ABLFL / BASE
`ABLFL = "Y"` when SDTM `QSBLFL = "Y"`; else null (analysis flags are
Y/null only per ADaMIG). `BASE` is the AVAL on the ABLFL row carried to
every record within `(USUBJID, PARAMCD)` via
`admiral::derive_var_base()`. `CHG` and `PCHG` from
`admiral::derive_var_chg()` / `derive_var_pchg()` — note these admiral
helpers take only `dataset` (no `new_var` arg, per CLAUDE.md API quirk).

### Analysis-record flag: ANL01FL
`"Y"` when `PARCAT2 = "SUBSCALE" AND AVAL` is not null; else null. The
SF-12 subscale scores are the primary analysis records.

### Label attachment
`metacore` / `xportr` / `labelled` are not installed in renv. Labels
are attached from `spec/adam/adqs.yaml` via
`yaml::read_yaml()` + `attr(x, "label") <-`. Same pattern as ADSL /
ADAE / ADCE / ADCM / ADDS / ADIE / ADLB / ADMH. Labels carry through to
XPT via `haven::write_xpt` reading the `label` attribute on each
column.

## P21 rules and fixes

### Resolved rules

#### AD0146B / AD0147B — PARAM / PARAMN inconsistency per PARAMCD (≈2000 → 0)
**Root cause**: Previous build set `PARAMN = dense_rank(PARAMCD)` with
`.by = USUBJID`, so PARAMN was a per-subject rank rather than a
dataset-wide function of PARAMCD. The same PARAMCD could carry up to 7
distinct PARAMN values across the dataset (depending on which subset of
SF-12 items each subject completed). PARAM was set to `QS.QSTEST` which
was already 1-to-1 per PARAMCD, but the previous label-inheritance
pipeline could still surface this as AD0146B in P21.
**Fix** (`program/adam/adqs.R`): Build a dataset-level
`(PARAMCD, PARAM, PARAMN)` lookup tibble and merge via
`admiral::derive_vars_merged()` by PARAMCD.
```r
param_lookup <- tibble::tribble(
  ~PARAMCD,  ~PARAM,                                          ~PARAMN,
  "SF1201",  "SF-12 Q01 General Health (SF1201)",                  1,
  ...
  "SF12MH",  "SF-12 Mental Health Subscale (SF12MH)",             20
)

adqs <- qs |>
  mutate(PARAMCD = QSTESTCD, ...) |>
  admiral::derive_vars_merged(
    dataset_add = param_lookup,
    by_vars     = exprs(PARAMCD),
    new_vars    = exprs(PARAM, PARAMN)
  )
```
**Coverage after fix**: 16 / 16 PARAMCDs have exactly 1 PARAM and 1
PARAMN. The four reserved subscale PARAMCDs (SF12PF / SF12RP / SF12RE /
SF12MH) emit zero rows in this pilot but are kept in the lookup for
forward-compatibility.

#### AD0018 — Variable label mismatch (26 → 0)
**Root cause**: ADQS was written without `attr(x, "label")` attached on
any column. The 26 flagged variables include `ABLFL`, `ADT`, `ADY`,
`AGE`, `ANL01FL`, plus every other column.
**Fix**: Manual label attachment from spec YAML (same idiom as ADCE) —
`metacore`/`xportr`/`labelled` are not installed in renv.
```r
spec_yaml <- yaml::read_yaml("spec/adam/adqs.yaml")
for (v in names(adqs)) {
  lab <- spec_yaml$variables[[v]]$label
  if (!is.null(lab) && nzchar(lab)) attr(adqs[[v]], "label") <- lab
}
attr(adqs, "label") <- spec_yaml$label
```
The YAML required fixes for parser hygiene before this could be read:
the `ABLFL` and `ANL01FL` derivations started with bare quoted `"Y"`
which YAML treated as the beginning of a mapping key; both are now
block scalars (`derivation: |`).

Dataset label was changed from `"Questionnaire (SF-12) Analysis
Dataset"` to the ADaMIG canonical `"Questionnaire Analysis Dataset"`.

**Coverage after fix**: 27 / 27 columns labelled; dataset label set.

#### AD0503 — *DT must contain 'Date' in the label (1 → 0)
**Root cause**: ADT had `LABEL=null` (same root cause as AD0018), so
"*DT label must contain Date" could not pass.
**Fix**: Label attachment makes ADT carry the spec label
`"Analysis Date"`, which contains `"Date"`. ADT is the only `*DT`
variable in ADQS — there is no end-date for SF-12 (each questionnaire
is a point-in-time administration).

#### CT2002 — RACE value not in 'Race' codelist (10 → 0)
**Root cause**: Prior ADQS build was run before DM (`af211c9`) and
ADSL (`2c0f164`) had their RACE corrections in place. ADQS inherits
RACE via `left_join(adsl_vars, by = "USUBJID")` so it picked up
unmapped raw values (e.g. `"1"`, `"1,2,5"`).
**Fix**: No code change in ADQS — just rebuild against the corrected
ADSL. After rebuild ADQS RACE values are CDISC long forms: WHITE
(1493 rows), NATIVE HAWAIIAN OR OTHER PACIFIC ISLANDER (96), MULTIPLE
(95), AMERICAN INDIAN OR ALASKA NATIVE (48), ASIAN (48), OTHER (21),
plus 1810 NA rows from subjects with no PTRACE.
**Coverage after fix**: 0 raw-coded RACE values; `"MULTIPLE"` is the
SDTMIG-prescribed extension for multi-race subjects (RACE codelist
C74457 is extensible) and is documented in ADRG.

### Known data limitations

| Rule | Residual count | Reason |
|------|----------------|--------|
| SF-12 subscale recomputation | n/a | QSSTRESN passes through from SDTM as-is. Recomputing per SF-12 v1/v2 published algorithm is a separate follow-up (per issue #21 triage). |
| PF / RP / RE / MH subscale rows | 0 emitted | Raw export only carries A/S components; composite subscales never present. PARAMCDs SF12PF / SF12RP / SF12RE / SF12MH reserved in the lookup but unused. |
| RACE = "MULTIPLE" | 95 rows | SDTMIG-prescribed extension; race codelist (C74457) is extensible. Document in ADRG. |
| RACE = NA | 1810 rows | Subjects with no PTRACE captured in raw DM. Upstream sparsity, not a code defect. |

## Cross-dataset dependencies
| Dependency | Direction | Notes |
|------------|-----------|-------|
| `data/sdtm/qs.rds`   | QS → ADQS   | Source of QSTESTCD, QSTEST, QSCAT, QSSCAT, QSSTRESC, QSSTRESN, QSBLFL, VISITNUM, VISIT, QSDTC. QS was canonicalised to CDISC SF-12 v1 short labels in commit `3c55428`. |
| `data/sdtm/dm.rds`   | DM → ADSL → ADQS | RACE / SUBJID / SITEID flow. CT2002 RACE fix lives in DM (commit `af211c9`). |
| `data/adam/adsl.rds` | ADSL → ADQS | SUBJID, SITEID, AGE, SEX, RACE, TRT01P, TRT01A, TRTSDT, EFFFL. SAFFL/EFFFL Y/N fix lives in ADSL (commit `2c0f164`). |

## Rebuild command
```bash
Rscript program/adam/adsl.R 2>&1 | grep -v "renv\|out-of-sync\|masked\|built under"
Rscript program/adam/adqs.R 2>&1 | grep -v "renv\|out-of-sync\|masked\|built under"
```

Expected output:
```
ADSL written: 810 rows x 35 cols
ADQS written: 3611 rows x 27 cols
ADQS XPT exported to data/adam/adqs.xpt
```

## Sanity checks
```r
adqs <- readRDS("data/adam/adqs.rds")
stopifnot(ncol(adqs) == 27)
stopifnot(!is.null(attr(adqs, "label")))
# Every column has a label
stopifnot(all(vapply(adqs, function(x) !is.null(attr(x, "label")), logical(1))))
# *DT labels contain "Date"
for (v in grep("DT$", names(adqs), value = TRUE)) {
  stopifnot(grepl("Date", attr(adqs[[v]], "label"), fixed = TRUE))
}
# PARAM / PARAMN are 1-to-1 with PARAMCD
chk <- aggregate(cbind(PARAM, PARAMN) ~ PARAMCD, adqs,
                 function(v) length(unique(v)))
stopifnot(max(chk$PARAM) == 1L, max(chk$PARAMN) == 1L)
# ABLFL / ANL01FL are Y or null only (never N per ADaMIG analysis-flag rule)
stopifnot(all(is.na(adqs$ABLFL)   | adqs$ABLFL   == "Y"))
stopifnot(all(is.na(adqs$ANL01FL) | adqs$ANL01FL == "Y"))
# Every USUBJID in ADQS appears in ADSL
adsl <- readRDS("data/adam/adsl.rds")
stopifnot(all(adqs$USUBJID %in% adsl$USUBJID))
```
