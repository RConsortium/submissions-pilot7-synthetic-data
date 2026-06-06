# MH — Domain Knowledge

## Overview
MH (Medical History) captures the subject's prior conditions at the start
of the trial. Source is the OpenClinica "1. Demographics and History"
form, with two item groups: `group1` (general medical history — free-text
DIAG plus body-system code) and `group2` (cancer history — coded primary
type, coded subtype, multi-select tumor organ).

Current output: 607 rows x 20 cols across 256 unique subjects.
(180 GENERAL MEDICAL HISTORY rows + 427 CANCER HISTORY rows.)

---

## Raw data sources

| File | Form / Event | Item group | Key items | Subject coverage |
|------|-------------|------------|-----------|------------------|
| `data/raw/dm.rds` | "1. Demographics and History" | group1 | DIAG, BODY, DATE, ONG, STOP | 259 subjects with at least one DIAG |
| `data/raw/dm.rds` | "1. Demographics and History" | group2 | CANCER1, CANCER2, CANCERORG, DIAGNOSED | 333 subjects with a cancer row (214 with CANCER1 populated, 214 with CANCER2) |
| `data/sdtm/dm.rds` | DM output | — | USUBJID, RFSTDTC | 810 subjects (713 with RFSTDTC) |

Raw item value reference (after the build's coverage filter):

| Item | Raw values observed |
|------|---------------------|
| ONG | `"0"`=No (53), `"1"`=Yes (203), blank (73) |
| DATE / STOP | mixed ISO `2024-03-07`, US `06/23/2025`, year-only `2026` — must pass through `normalize_iso_date()` |
| BODY | `"1"`..`"9"` (CL_57) |
| CANCER1 | `"1"`..`"5"` (CL_68) |
| CANCER2 | `"1"`..`"30"` (CL_69) — codes 1–5 collide with CANCER1's codes 1–5 numerically but decode to different terms |
| CANCERORG | comma-separated codes `"1"`..`"10"` (MSL_70 multi-select) |

**Critical**: `ONG` is `"0"` / `"1"` (numeric codes), NOT `"Y"` / `"N"`.
The legacy build had `toupper(ONG) == "Y"` which never matched — that
single bug caused all 134 ongoing-condition rows to be miscategorized
and triggered SD0021 for every row missing MHENDTC.

---

## Controlled terminology mappings

### MHSCAT — from BODY (raw codelist CL_57)

| Coded value | CRF label / MHSCAT |
|-------------|---------------------|
| 1 | Cardiovascular |
| 2 | Respiratory |
| 3 | Gastrointestinal |
| 4 | Genitourinary |
| 5 | Musculoskeletal |
| 6 | Neurological |
| 7 | Endocrinological |
| 8 | Dermatologic/Skin |
| 9 | Hematologic/Lymphatic |

### MHTERM for CANCER HISTORY — from CANCER1 (CL_68)

| Coded value | MHTERM |
|-------------|--------|
| 1 | Carcinoma |
| 2 | Leukemia |
| 3 | Lymphoma |
| 4 | Sarcoma |
| 5 | Myeloma |

### MHTERM for CANCER HISTORY (second row) — from CANCER2 (CL_69)

| Coded value | MHTERM |
|-------------|--------|
| 1 | Adenocarcinoma |
| 2 | Small cell carcinoma |
| 3 | Squamous cell carcinoma |
| 4 | Large cell carcinoma |
| 5 | Transitional cell carcinoma |
| 6 | Undifferentiated carcinoma |
| 7 | Soft tissue sarcoma |
| 8 | Bone sarcoma |
| 9 | Fibroblastic sarcoma |
| 10 | Rhabdomyosarcoma |
| 11 | Gastrointestinal stromal tumor (GIST) |
| 12 | Leiomyosarcoma |
| 13 | Liposarcoma |
| 14 | Osteosarcoma |
| 15 | Ewing's sarcoma |
| 16 | Chondrosarcoma |
| 17 | B-cell lymphoma |
| 18 | T-cell lymphoma |
| 19 | Burkitt's lymphoma |
| 20 | Follicular lymphoma |
| 21 | Mantle cell lymphoma |
| 22 | Acute myeloid leukemia (AML) |
| 23 | Chronic myeloid leukemia (CML) |
| 24 | Acute lymphocytic leukemia (ALL) |
| 25 | Chronic lymphocytic leukemia (CLL) |
| 26 | IgG myeloma |
| 27 | IgA myeloma |
| 28 | IgM myeloma |
| 29 | IgD myeloma |
| 30 | IgE myeloma |

### MHSPID — from CANCERORG (MSL_70 multi-select, decoded and joined)

| Coded value | Decoded |
|-------------|---------|
| 1 | Breast |
| 2 | Colon |
| 3 | Prostate |
| 4 | Stomach |
| 5 | Pancreas |
| 6 | Lung |
| 7 | Esophageal |
| 8 | Colorectal |
| 9 | Cervix |
| 10 | GI Tract |

Multi-select example: `"1,4,7"` -> `"Breast, Stomach, Esophageal"`.

### ONG — ongoing flag (raw codelist CL_60)

| Coded value | Meaning |
|-------------|---------|
| 0 | No |
| 1 | Yes |

---

## P21 rules and fixes

### Resolved rules

#### SD0021 — Missing End Time-Point value (565 -> 0 unjustified)
**Root cause**: Legacy code wrote `MHENRF = ifelse(toupper(ONG)=="Y", "ONGOING", NA)`
but raw ONG values are `"0"`/`"1"`/blank, so `MHENRF` was always NA.
The build never emitted `MHENRTPT` / `MHENTPT` at all, so every missing
MHENDTC was unjustified.

**Fix** (`program/sdtm/mh.R`):
```r
is_ongoing = !is.na(ONG) & trimws(ONG) == "1",
...
MHENRF   = dplyr::if_else(is_ongoing, "ONGOING", NA_character_),
MHENRTPT = dplyr::case_when(
  is_ongoing     ~ "ONGOING",
  is.na(MHENDTC) ~ "UNKNOWN",
  TRUE           ~ NA_character_),
MHENTPT  = dplyr::if_else(is.na(MHENDTC),
                          "DATE OF LAST ASSESSMENT", NA_character_),
```
**Coverage after fix**: 0 rows with `is.na(MHENDTC) & is.na(MHENRTPT)`.
566 of 607 rows missing MHENDTC are now justified (134 ONGOING,
432 UNKNOWN).

#### SD0022 — Missing Start Time-Point value (428 -> 0 unjustified)
**Root cause**: CRF DATE / DIAGNOSED unpopulated; no Start Time-Point
justification was being emitted.

**Fix**:
```r
MHSTRTPT = dplyr::if_else(is.na(MHSTDTC), "UNKNOWN", NA_character_),
MHSTTPT  = dplyr::if_else(is.na(MHSTDTC),
                          "DATE OF FIRST ASSESSMENT", NA_character_),
```
**Coverage after fix**: 0 rows with `is.na(MHSTDTC) & is.na(MHSTRTPT)`.

#### SD1201 — Duplicate records (46 -> 0)
**Root cause**: The build emitted one MHTERM row for raw CANCER1 and a
second MHTERM row for raw CANCER2 using the raw coded value verbatim
(e.g., MHTERM=`"1"`). For 46 subjects with CANCER1=`"1"` AND CANCER2=`"1"`,
both rows had identical MHTERM, MHSTDTC, MHCAT — true duplicates.

**Fix**: Decode CANCER1 (via CL_68) and CANCER2 (via CL_69) BEFORE
emitting rows; the same raw code `"1"` decodes to `"Carcinoma"` (CL_68)
for CANCER1 and `"Adenocarcinoma"` (CL_69) for CANCER2, naturally
resolving the duplicate. Also suppress the CANCER2 row when its decoded
term still equals CANCER1's decoded term, and apply a final
`distinct(USUBJID, MHCAT, MHTERM, MHSTDTC, MHENDTC, MHSCAT)` as a safety
net.

**Coverage after fix**: 0 duplicates on (USUBJID, MHCAT, MHTERM, MHSTDTC, MHENDTC).

#### SD1078 — All-NA permissibles (7 -> 2 documented)
**Before fix**: 7 columns all-NA — MHDECOD, MHBODSYS, MHPRESP, MHOCCUR,
MHSTAT, MHENRF, MHSTDY.

**Fix**:
- MHENRF: now derived from `is_ongoing` (134 non-null).
- MHSTDY: now derived from MHSTDTC vs DM.RFSTDTC (179 non-null).
- MHPRESP, MHOCCUR, MHSTAT: **dropped** — the CRF carries no pre-specified
  questions in this study, and form-completion status is not surfaced in
  the export, so these would be all-NA regardless.

**Remaining all-NA**: MHDECOD, MHBODSYS — MedDRA coding gap. Same
limitation as AE/CE in this synthetic pilot.

#### SD1076 — Model permissible added (2 -> 0)
**Root cause**: MHPRESP and MHOCCUR were added in the build despite no
source data populating them (always NA). P21 flags adding permissible
variables that bring no value.

**Fix**: Dropped both. They can be reintroduced if a future export
provides pre-specified condition data.

#### SD1079 — Variable order (4 -> 0)
**Root cause**: MHBODSYS was placed between MHDECOD and MHCAT (should be
after MHSCAT); MHENRF was placed between MHSTAT and MHSTDTC (should be
after MHENRTPT/MHENTPT).

**Fix**: Final `select()` follows SDTMIG v3.3 MH order:
`STUDYID, DOMAIN, USUBJID, MHSEQ, MHSPID, MHTERM, MHDECOD, MHCAT, MHSCAT,
MHBODSYS, MHSTDTC, MHENDTC, MHSTDY, MHSTRTPT, MHSTTPT, MHENRF, MHENRTPT,
MHENTPT, VISITNUM, VISIT`.

#### SD0013 — MHSTDTC after MHENDTC (1 -> 0)
**Root cause**: CRF data-entry inversion for subject DF-506 — MHSTDTC
2020-03-03 with MHENDTC 2020-02-05.

**Fix**:
```r
MHENDTC = dplyr::if_else(
  !is.na(MHSTDTC) & !is.na(MHENDTC) & MHENDTC < MHSTDTC,
  NA_character_, MHENDTC)
```
The escape via MHENRTPT="UNKNOWN" + MHENTPT="DATE OF LAST ASSESSMENT"
then takes over for that row. Non-fabricating — drops the demonstrably
wrong end date rather than swapping or inventing one.

#### SD1088 — MHSTDY not populated (1 -> 0 unjustified)
**Root cause**: MHSTDY was set to `NA_integer_` unconditionally.

**Fix**:
```r
.d_st = suppressWarnings(as.Date(MHSTDTC)),
.d_rf = suppressWarnings(as.Date(RFSTDTC)),
MHSTDY = dplyr::if_else(
  !is.na(.d_st) & !is.na(.d_rf),
  as.integer(.d_st - .d_rf) + dplyr::if_else(.d_st >= .d_rf, 1L, 0L),
  NA_integer_),
```
**Coverage after fix**: 179 / 607 (every row that has both a parseable
MHSTDTC and a parseable DM.RFSTDTC).

---

### Known data limitations

| Rule | Residual count | Reason |
|------|---------------|--------|
| MHDECOD all-NA | 607 rows | No MedDRA-coded layer in the synthetic export. Same coding gap as AE/CE. Production submission would refresh from MedDRA. |
| MHBODSYS all-NA | 607 rows | Same MedDRA coding gap. |
| MHSTDTC null | 428 rows | Raw DATE / DIAGNOSED unpopulated; justified via MHSTRTPT="UNKNOWN" + MHSTTPT="DATE OF FIRST ASSESSMENT". |
| MHENDTC null | 566 rows | Either ongoing (134 — justified via MHENRF="ONGOING" + MHENRTPT="ONGOING") or simply missing (432 — justified via MHENRTPT="UNKNOWN"). |
| MHSTDY null | 428 rows | MHSTDTC missing or DM.RFSTDTC missing for the subject. |

---

## Cross-domain dependencies

| Dependency | Direction | Notes |
|------------|-----------|-------|
| DM.RFSTDTC | MH reads DM | Required for MHSTDY derivation |
| DM.USUBJID | MH reads DM | USUBJID key alignment via subjectkey link |

**Rebuild order**: DM must be rebuilt before MH when DM changes affect
RFSTDTC or subject coverage.

---

## Rebuild command

```bash
Rscript program/sdtm/mh.R 2>&1 | grep -v "renv\|out-of-sync\|masked\|built under"
```

Expected output:
```
MH written: 607 rows x 20 cols
Unique subjects: 256
MHSTDTC  non-null: 179 / 607
MHENDTC  non-null:  41 / 607
MHENRF   non-null: 134  (ONGOING)
MHENRTPT non-null: 566  (end justified)
MHSTRTPT non-null: 428  (start justified)
MHSTDY   non-null: 179 / 607
Date inversions remaining: 0
Dup-key (USUBJID,MHCAT,MHTERM,MHSTDTC,MHENDTC) duplicates: 0
```

Sanity checks:
```r
mh <- readRDS("data/sdtm/mh.rds")
# No date inversions
stopifnot(sum(!is.na(mh$MHSTDTC) & !is.na(mh$MHENDTC) &
              mh$MHSTDTC > mh$MHENDTC) == 0)
# All missing dates justified
stopifnot(sum(is.na(mh$MHENDTC) & is.na(mh$MHENRTPT)) == 0)
stopifnot(sum(is.na(mh$MHSTDTC) & is.na(mh$MHSTRTPT)) == 0)
# No duplicate natural key
stopifnot(sum(duplicated(mh[, c("USUBJID","MHCAT","MHTERM",
                               "MHSTDTC","MHENDTC")])) == 0)
# Variable order matches SDTMIG v3.3
stopifnot(identical(names(mh),
  c("STUDYID","DOMAIN","USUBJID","MHSEQ","MHSPID","MHTERM","MHDECOD",
    "MHCAT","MHSCAT","MHBODSYS","MHSTDTC","MHENDTC","MHSTDY",
    "MHSTRTPT","MHSTTPT","MHENRF","MHENRTPT","MHENTPT",
    "VISITNUM","VISIT")))
# Dropped permissibles must not reappear
stopifnot(!any(c("MHPRESP","MHOCCUR","MHSTAT") %in% colnames(mh)))
# MHSEQ unique within USUBJID
stopifnot(!anyDuplicated(mh[, c("USUBJID","MHSEQ")]))
# All MH subjects in DM
dm_ids <- readRDS("data/sdtm/dm.rds")$USUBJID
stopifnot(all(mh$USUBJID %in% dm_ids))
```
