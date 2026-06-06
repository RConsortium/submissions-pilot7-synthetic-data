# DM — Domain Knowledge

## Overview
DM (Demographics) is the master subject table — one row per subject, 810 total.
It is built from the full subject universe in `flat.rds` (every distinct
`subjectkey`) joined to four form-level raw datasets. DM drives cross-domain
validation: USUBJID, RFSTDTC, ARMCD, and ACTARMCD are referenced by every
other SDTM domain and every ADaM dataset.

---

## Raw data sources

| File | Form / Event | Key items | Subject coverage |
|------|-------------|-----------|-----------------|
| `data/raw/flat.rds` | all forms / all events | `startdate` (event date) | 810 subjects; 713 have ≥1 startdate |
| `data/raw/dm.rds` | "1. Demographics and History" (SE_BASELINE) | PTSEX, PTRACE, HISP, OTHERRACE | 388 subjects with DM form data |
| `data/raw/ie.rds` | "Eligibility" (SE_ENROLLMENT) | BDAY, PTAGE, PTBYEAR, CONSENTED | 580 subjects with IE startdate |
| `data/raw/rand.rds` | "3. Randomize" (SE_BASELINE) | PROFILE | 280 subjects (randomized arm) |
| `data/raw/ds.rds` | "Disposition" (SE_DISPOSITION) | CONSENTEDDT, EARLYTERMINATIONDATE | 2 subjects only |
| `data/raw/ae.rds` | "Adverse Event" (SE_ADVERSEEVENTS) | AESDTH, DTHDAT | 9 subjects with AESDTH=Y (5 with DTHDAT) |

**Subject universe**: derived from `flat.rds` via `distinct(subjectkey, studysubjectid)`.
Never restrict to any single form — DM must represent all 810 subjects.

---

## Controlled terminology mappings

### RACE (raw item: PTRACE)
OpenClinica multi-select list MSL_62. Values are comma-separated integer codes
when a subject selects more than one box.

| Coded value | CRF label | CDISC RACE CT term (C74457) |
|-------------|-----------|------------------------------|
| 1 | American Indian/Alaskan Native | AMERICAN INDIAN OR ALASKA NATIVE |
| 2 | Asian | ASIAN |
| 3 | Black/African American | BLACK OR AFRICAN AMERICAN |
| 4 | Native Hawaiian/Pacific Islander | NATIVE HAWAIIAN OR OTHER PACIFIC ISLANDER |
| 5 | White/Caucasian | WHITE |
| 6 | Other (free text in OTHERRACE) | OTHER |
| 1,5 / 2,3 / any comma-separated | Multiple selections | MULTIPLE |
| missing / blank | — | NA |

Distribution in current export (356 subjects with PTRACE):
WHITE=270, AMERICAN INDIAN OR ALASKA NATIVE=25, ASIAN=18,
NATIVE HAWAIIAN OR OTHER PACIFIC ISLANDER=12, BLACK OR AFRICAN AMERICAN=5,
OTHER=3, MULTIPLE=20, NA=457

### SEX (raw item: PTSEX)
OpenClinica CodeList CL_66. Only 43 subjects have PTSEX in the DM form
(most subjects have PTSEXEL instead, which is a read-only carry-forward field).

| Coded value | CDISC SEX CT |
|-------------|--------------|
| M or 1 | M |
| F or 2 | F |
| missing | U |

### ETHNIC (raw item: HISP)
OpenClinica CodeList CL_64 (Yes/No question).

| Coded value | CDISC ETHNIC CT |
|-------------|----------------|
| Y or 1 | HISPANIC OR LATINO |
| N or 0 | NOT HISPANIC OR LATINO |
| missing | NA |

---

## P21 rules and fixes

### Resolved rules

#### CT2002 — RACE value not in RACE extensible codelist
**Root cause**: `dm.R` was passing `toupper(PTRACE)` directly, storing raw
codes ("5", "1,2,5") instead of CDISC CT strings.

**Fix** (`program/sdtm/dm.R`):
```r
map_race <- function(ptrace) {
  race_map <- c(
    "1" = "AMERICAN INDIAN OR ALASKA NATIVE",
    "2" = "ASIAN",
    "3" = "BLACK OR AFRICAN AMERICAN",
    "4" = "NATIVE HAWAIIAN OR OTHER PACIFIC ISLANDER",
    "5" = "WHITE",
    "6" = "OTHER"
  )
  dplyr::case_when(
    is.na(ptrace) | !nzchar(trimws(ptrace)) ~ NA_character_,
    grepl(",", ptrace, fixed = TRUE)         ~ "MULTIPLE",
    ptrace %in% names(race_map)              ~ unname(race_map[ptrace]),
    TRUE                                     ~ NA_character_
  )
}
# In mutate block:
RACE = map_race(PTRACE),
```
**Coverage after fix**: 353 / 810 non-null (457 subjects have no DM form data).

---

#### SD1210 — Missing RFICDTC
**Root cause**: `Disposition.CONSENTEDDT` is present for only 1 subject (SS_DF030).
The other 809 subjects have no consent date in the export.

**Fix** (`program/sdtm/dm.R`):
```r
# Derive eligibility form startdate per subject (SE_ENROLLMENT event)
elig_dates <- ie_raw |>
  filter(!is.na(startdate) & nzchar(startdate)) |>
  mutate(.sd = normalize_iso_date(substr(startdate, 1, 10))) |>
  filter(!is.na(.sd)) |>
  summarise(elig_startdate = min(.sd), .by = subjectkey)

# In subjects pipeline — add left_join(elig_dates, by = "subjectkey")
# In mutate block:
RFICDTC = dplyr::coalesce(normalize_iso_date(CONSENTEDDT), elig_startdate),
```
**Coverage after fix**: 580 / 810 non-null.
**Residual limitation**: 230 subjects have neither CONSENTEDDT nor an
Eligibility form startdate — RFICDTC remains null for them.

---

#### SD0087 / SD0088 / SD1213 / SD1376 — Missing RFSTDTC / RFENDTC
**Root cause**: RFSTDTC was set to RFICDTC, so it inherited the same
near-total nullness. RFENDTC was set only from EARLYTERMINATIONDATE (1 subject).

**Fix** (`program/sdtm/dm.R`):
```r
# Derive first/last event startdate per subject across all forms
visit_dates <- flat |>
  filter(!is.na(startdate) & nzchar(startdate)) |>
  mutate(startdate_ymd = normalize_iso_date(substr(startdate, 1, 10))) |>
  filter(!is.na(startdate_ymd)) |>
  summarise(
    first_visit_dt = min(startdate_ymd),
    last_visit_dt  = max(startdate_ymd),
    .by = subjectkey
  )

# In mutate block:
RFSTDTC  = dplyr::coalesce(RFICDTC, first_visit_dt),
RFENDTC  = dplyr::coalesce(normalize_iso_date(EARLYTERMINATIONDATE), last_visit_dt),
RFPENDTC = dplyr::coalesce(normalize_iso_date(EARLYTERMINATIONDATE), last_visit_dt),
```
**Coverage after fix**: RFSTDTC 713 / 810 non-null.
**Residual limitation**: 97 subjects have no `startdate` in any form — these
subjects appear only as bare subject registrations with no form data.

---

#### SD1255 — DTHFL not "Y" when AE.AESDTH = "Y"
**Root cause**: DM had `DTHDTC = NA_character_` and `DTHFL = NA_character_`
hard-coded — death information was never sourced from AE.

**Fix** (`program/sdtm/dm.R`):
```r
ae_raw <- readRDS("data/raw/ae.rds")

ae_dth <- ae_raw |>
  filter(itemname == "AESDTH" & toupper(value) == "Y") |>
  distinct(subjectkey) |>
  mutate(dth_flag_y = "Y")

ae_dthdat <- ae_raw |>
  filter(itemname == "DTHDAT" & !is.na(value) & nzchar(value)) |>
  mutate(.dt = normalize_iso_date(substr(value, 1, 10))) |>
  filter(!is.na(.dt)) |>
  summarise(dth_dtc = min(.dt), .by = subjectkey)

# After left_join(ae_dth, ae_dthdat) into the subjects pipeline:
DTHDTC = dth_dtc,
DTHFL  = dth_flag_y,
```
**Coverage after fix**: 9 / 810 subjects have DTHFL = "Y"; 5 / 810 also have
DTHDTC (the other 4 have AESDTH = "Y" without a recorded DTHDAT).

---

#### SD1343 — Missing RFXSTDTC for treated subjects
**Root cause**: `RECEIVEDINTERVENTION = No` for all 280 randomized subjects —
no subject actually received study treatment. RFXSTDTC requires a treatment
date from the EX domain, which does not exist. Separately, ACTARMCD was
mirroring ARMCD ("TREATMENT"), falsely implying the subject was treated.

**Fix** (`program/sdtm/dm.R`):
```r
ACTARMCD = dplyr::case_when(
  armcd_map(PROFILE) == "TREATMENT" ~ "NOTTRT",
  TRUE ~ armcd_map(PROFILE)
),
ACTARM = dplyr::case_when(
  arm_map(PROFILE) == "Study Treatment" ~ "Not treated",
  TRUE ~ arm_map(PROFILE)
),
RFXSTDTC = NA_character_,   # no treatment administered
RFXENDTC = NA_character_,
```
**Result**: ACTARMCD = NOTTRT for all 280 TREATMENT subjects; RFXSTDTC
remains null (correct — no treatment given).

---

### Known data limitations

| Rule | Residual count | Reason |
|------|---------------|--------|
| SD1210 RFICDTC null | ~230 subjects | No Eligibility form startdate in export |
| SD1343 RFXSTDTC null | 280 subjects | No EX domain; RECEIVEDINTERVENTION=No for all |
| SD1363/SD1364 ARMCD without TA | 530 SCRNFAIL | TA trial-design dataset not yet built |
| RACE null | 457 subjects | No "1. Demographics and History" form data |
| SEX null / "U" | most subjects | PTSEX only in 43 DM form records; PTSEXEL (read-only) not mappable to SEX CT |
| DTHDTC null when DTHFL=Y | 4 subjects | AESDTH = "Y" recorded on AE but DTHDAT not captured (MGH-021, MGH-038, MGH-041, MGH-121) |

---

## Cross-domain dependencies

| Dependency | Direction | Notes |
|------------|-----------|-------|
| DS.DSDECOD = INFORMED CONSENT OBTAINED | DS must have ≥1 per subject | P21 SD1240 fires on DM when DS lacks a consent record |
| DS coverage | DS must have ≥1 row per DM subject | P21 SD1374 fires on DM when DS has no row for the subject |
| TA.ARMCD | TA must define SCRNFAIL and TREATMENT arms | P21 SD1363/SD1364 fire on DM when TA is absent |
| DM.RFSTDTC | All OCCDS and BDS ADaM datasets join this | RFSTDTC null propagates to all ADAE/ADCM/etc. ASTDY/AENDY |
| DM.USUBJID | All other SDTM domains | Subject universe is authoritative here |
| AE.AESDTH/DTHDAT | AE feeds DM | DM.DTHFL must be "Y" wherever AE.AESDTH = "Y" (P21 SD1255). Rebuild DM after any AE source change. |

---

## Rebuild command

```bash
Rscript program/sdtm/dm.R 2>&1 | grep -v "renv\|out-of-sync\|masked\|built under"
```

Expected output:
```
DM written: 810 rows x 24 cols
```

Sanity checks to run after rebuild:
```r
dm <- readRDS("data/sdtm/dm.rds")
stopifnot(!any(grepl("^[0-9,]+$", dm$RACE, perl=TRUE), na.rm=TRUE))  # no raw codes
cat("RFICDTC non-null:", sum(!is.na(dm$RFICDTC)), "/ 810\n")          # expect 580
cat("RFSTDTC non-null:", sum(!is.na(dm$RFSTDTC)), "/ 810\n")          # expect 713
cat("ACTARMCD values:", paste(sort(unique(dm$ACTARMCD)), collapse=", "), "\n") # NOTTRT, SCRNFAIL
```
