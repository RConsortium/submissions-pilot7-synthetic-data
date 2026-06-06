# IE — Domain Knowledge

## Overview
IE (Inclusion/Exclusion Exceptions) captures one record per eligibility
criterion failure per subject. A row exists *because* a criterion
evaluation flag came back as failed:

- For an **INCLUSION** criterion, a row exists because the subject did
  NOT meet it (`IEORRES = "N"`, the subject is an exception to that
  criterion).
- For an **EXCLUSION** criterion, a row exists because the subject DID
  meet it (`IEORRES = "Y"`, the subject is an exception in that they
  triggered the exclusion).

The IE form is the "Eligibility" CRF in the OpenClinica export, collected
once per subject at the `SE_ENROLLMENT` study event (which is the
screening visit in this protocol). After filtering to failure rows the
domain has **20 rows × 15 cols** across 17 distinct subjects.

The raw CRF has three criterion-summary items (`INC1EVAL`, `INC2EVAL`,
`EXCEVAL`) that hold an overall pass/fail/pending verdict per
criterion-group. Individual sub-criterion items (CHEMO, LVEF, CREEVAL,
TGVHA, etc.) are not separately mapped — the granularity that survives
into IE is the criterion-group flag.

---

## Raw data sources

| File | Form / Event | Key items | Subject coverage |
|------|-------------|-----------|-----------------|
| `data/raw/ie.rds` | "Eligibility" (`SE_ENROLLMENT`) — itemgroups `INC1`, `INC2`, `INCA`, `EXCT`, `SUMMARY`, `INTRO` | `INC1EVAL`, `INC2EVAL`, `EXCEVAL` (verdict flags); individual criterion items (CHEMO, LVEF, CREEVAL, TGVHA, …) | 15,741 rows total; 559 form repeats; 17 subjects with at least one fail flag |
| `data/sdtm/dm.rds` | DM output | `RFSTDTC` (IEDY anchor) | 713 / 810 RFSTDTC populated; all 17 IE subjects have RFSTDTC |

Verdict-flag value distribution in the raw form (562 form repeats):

| Item | pass | fail | pending |
|------|------|------|---------|
| `INC1EVAL` | 532 | 5 | 22 |
| `INC2EVAL` | 491 | 10 | 58 |
| `EXCEVAL`  | 502 | 5 | 52 |

Only `fail` rows propagate into IE. Pending rows are dropped (treated as
not-yet-evaluated).

---

## Controlled terminology mappings

### IECAT (raw: `itemgroupname`)
| Raw item group | IECAT |
|----------------|-------|
| `INC1`, `INC2`, `INCA` | `INCLUSION` |
| `EXCT` | `EXCLUSION` |

### IESCAT (raw: `itemgroupname`)
| Raw item group | IESCAT |
|----------------|--------|
| `INC1` | `DISEASE HISTORY` |
| `INC2` | `LABS AND ORGAN FUNCTION` |
| `INCA` | `AGE AND CONSENT` |
| `EXCT` | `SAFETY AND INFECTIONS` |

### IEORRES / IESTRESC (CDISC NY codelist, C66742)
Derived from `IECAT`, not copied from a raw item:

| IECAT | IEORRES | IESTRESC |
|-------|---------|----------|
| `INCLUSION` | `N` | `N` |
| `EXCLUSION` | `Y` | `Y` |

### EPOCH (CDISC EPOCH codelist, C99079)
Constant `"SCREENING"` — the Eligibility CRF is collected only at the
`SE_ENROLLMENT` event, which is the screening visit. Unlike CE/DS, IE
does not need to derive EPOCH against `DM.RFSTDTC` / `RFENDTC`.

### IETESTCD / IETEST
Sponsor-controlled, ≤ 8 chars. Current build emits one of three values
based on the criterion-summary flag that failed:

| IETESTCD | IETEST |
|----------|--------|
| `INC1INC1` | `INC1 / INC1EVAL` |
| `INC2INC2` | `INC2 / INC2EVAL` |
| `EXCTEXCE` | `EXCT / EXCEVAL` |

A richer mapping at the sub-criterion level (e.g., `INC1CHEM`,
`INC2LVEF`, `EXCTGVHA`) is feasible if the sub-criterion items per row
become required for a Define-XML codelist, but the failing data only
exists at the summary-flag level today.

---

## P21 rules and fixes

### Resolved rules

#### SD1046 — IESTRESC value not in ('N') when IECAT='INCLUSION' (15 → 0)
**Root cause**: Previous build hard-coded `IEORRES = "Y"` and
`IESTRESC = "Y"` for every row. This is correct for EXCLUSION rows but
inverted for INCLUSION rows — per SDTMIG v3.3, an INCLUSION exception
row exists because the subject did NOT meet the inclusion criterion, so
the result should be `"N"`.

**Fix** (`program/sdtm/ie.R`):
```r
mutate(
  IEORRES  = dplyr::if_else(IECAT == "INCLUSION", "N", "Y"),
  IESTRESC = IEORRES,
  ...
)
```
**Coverage after fix**:
- 15 INCLUSION rows → IEORRES / IESTRESC = `"N"`
- 5 EXCLUSION rows → IEORRES / IESTRESC = `"Y"`

#### SD1077 — Regulatory Expected variable EPOCH not found (1 → 0)
**Root cause**: EPOCH was not derived.

**Fix** (`program/sdtm/ie.R`): Constant `"SCREENING"` for all rows,
since the Eligibility form is only collected at `SE_ENROLLMENT`.
```r
mutate(EPOCH = "SCREENING", ...)
```
**Coverage after fix**: 20 / 20.

#### SD1084 — IEDY null (1 → 0)
**Root cause**: `IEDY` was hard-coded to `NA_integer_`.

**Fix** (`program/sdtm/ie.R`): Join `DM.RFSTDTC` and apply the no-day-0
day-of-study formula used by CE/DS:
```r
left_join(dm |> select(USUBJID, RFSTDTC), by = "USUBJID") |>
mutate(
  IEDY = dplyr::if_else(
    !is.na(IEDTC) & !is.na(RFSTDTC),
    as.integer(as.Date(IEDTC) - as.Date(RFSTDTC)) +
      ifelse(IEDTC >= RFSTDTC, 1L, 0L),
    NA_integer_
  )
)
```
**Coverage after fix**: 20 / 20 IEDY populated. Every IE row has
`IEDY = 1` because RFSTDTC is derived as the earliest study activity
date and the Eligibility form is collected at that same screening
event.

---

### Known data limitations

| Field | Note |
|-------|------|
| IETESTCD granularity | Current build emits criterion-group-level codes only (`INC1INC1`, `INC2INC2`, `EXCTEXCE`). The sub-criterion items (CHEMO, LVEF, etc.) exist in the raw form but are not separately failed/passed per item — only the summary `*EVAL` flag is. |
| IECAT="INCLUSION" rows from item group `INCA` | None present in this synthetic export — all 15 INCLUSION rows are from `INC1` (disease history) or `INC2` (labs/organ function). Mapping is in place for `INCA → AGE AND CONSENT` if `INCA` failures appear in future cuts. |

---

## Cross-domain dependencies

| Dependency | Direction | Notes |
|------------|-----------|-------|
| `DM.RFSTDTC` | DM → IE | needed for IEDY arithmetic |
| `DM` (USUBJID universe) | DM → IE | `make_usubjid()` from `ut_visits.R` ensures format consistency |

**Rebuild order when DM source data changes**:
```
1. Rscript program/sdtm/dm.R
2. Rscript program/sdtm/ie.R
```

---

## Rebuild command

```bash
Rscript program/sdtm/ie.R 2>&1 | grep -v "renv\|out-of-sync\|masked\|built under"
```

Expected output:
```
IE written: 20 rows x 15 cols
IECAT distribution:
EXCLUSION INCLUSION
        5        15
IEORRES by IECAT:
             N  Y
  EXCLUSION  0  5
  INCLUSION 15  0
EPOCH non-null: 20 / 20
IEDY non-null:  20 / 20
IETESTCD lengths (must all be <=8):
 8
20
```

Sanity checks:
```r
ie <- readRDS("data/sdtm/ie.rds")
dm <- readRDS("data/sdtm/dm.rds")

# SD1046: IEORRES encodes whether criterion was MET
stopifnot(all(ie$IEORRES[ie$IECAT == "INCLUSION"] == "N"))
stopifnot(all(ie$IEORRES[ie$IECAT == "EXCLUSION"] == "Y"))
stopifnot(all(ie$IESTRESC == ie$IEORRES))

# SD1077: EPOCH populated
stopifnot(all(ie$EPOCH == "SCREENING"))

# SD1084: IEDY populated for every row with both IEDTC and RFSTDTC
stopifnot(all(!is.na(ie$IEDY)))

# IETESTCD <= 8 chars
stopifnot(all(nchar(ie$IETESTCD) <= 8))

# Every IE USUBJID exists in DM
stopifnot(all(ie$USUBJID %in% dm$USUBJID))
```
