# DS — Domain Knowledge

## Overview
DS (Disposition) captures one record per disposition milestone per subject.
The build uses three source layers in priority order: (1) Disposition-form PD
records (2 subjects), (2) Eligibility-form startdate for all subjects with IE
data (580 subjects), and (3) Randomize-form startdate for all randomized
subjects (280 subjects). Each (subjectkey, DSDECOD) pair is deduplicated,
preferring rows with a non-null DSSTDTC regardless of source layer.

Current output: 1,442 rows × 13 cols, 592 unique subjects.

---

## Raw data sources

| File | Form / Event | Key items | Subject coverage |
|------|-------------|-----------|-----------------|
| `data/raw/ds.rds` | "Disposition" (SE_DISPOSITION), itemgroupname="PD" | CONSENTED, CONSENTEDDT, SCREENED, ELIGIBLE, RANDOMIZED, RECEIVEDINTERVENTION, PRIMARYOUTCOMESCOMPLETE, SECONDARYOUTCOMESCOMPLETE, EARLYTERMINATIONDATE, EARLYTERMINATIONREASON, STATUSONSTUDY, REPORTEDAECOUNT | 2 subjects only |
| `data/raw/ie.rds` | "Eligibility" (SE_ENROLLMENT) | startdate (used as consent/eligibility proxy) | 580 subjects with startdate |
| `data/raw/rand.rds` | "3. Randomize" (SE_BASELINE) | startdate (used as randomization date) | 280 subjects with startdate |
| `data/sdtm/dm.rds` | DM output | RFSTDTC (needed for DSSTDY) | 810 subjects; 713 with RFSTDTC |

---

## Controlled terminology mappings

### DSDECOD — valid values used in this domain

DSDECOD must be from the NCOMPLT (C66727) or PROTMLST (C114118) extensible
codelists depending on DSCAT.

**DSCAT = "PROTOCOL MILESTONE"** — use PROTMLST (C114118):

| DSDECOD value used | CDISC status | Notes |
|--------------------|-------------|-------|
| INFORMED CONSENT OBTAINED | Valid PROTMLST term | |
| ELIGIBILITY CRITERIA MET | Valid PROTMLST term | Replaces "SCREENING COMPLETED" |
| RANDOMIZED | Valid PROTMLST term | |
| TREATMENT STARTED | Valid PROTMLST term | |
| COMPLETED PRIMARY OUTCOMES | Valid PROTMLST term | |
| COMPLETED SECONDARY OUTCOMES | Valid PROTMLST term | |
| ~~SCREENING COMPLETED~~ | **NOT in PROTMLST** | CT2005 — do not use |

**DSCAT = "DISPOSITION EVENT"** — use NCOMPLT (C66727):

| DSDECOD value used | CDISC status | Notes |
|--------------------|-------------|-------|
| ADVERSE EVENT | Valid NCOMPLT term | mapped from "Adverse Event" reason |
| WITHDRAWAL BY SUBJECT | Valid NCOMPLT term | mapped from "Withdrew Consent" |
| DEATH | Valid NCOMPLT term | |
| LACK OF EFFICACY | Valid NCOMPLT term | |
| LOST TO FOLLOW-UP | Valid NCOMPLT term | |
| PHYSICIAN DECISION | Valid NCOMPLT term | |
| PROTOCOL DEVIATION | Valid NCOMPLT term | fallback for unknown reasons |
| STUDY TERMINATED BY SPONSOR | Valid NCOMPLT term | |
| ~~EARLY TERMINATION~~ | **NOT in NCOMPLT** | CT2005 — do not use |

### map_et_reason() — maps free-text EARLYTERMINATIONREASON to NCOMPLT

```r
map_et_reason <- function(reason) {
  reason_u <- toupper(trimws(reason))
  dplyr::case_when(
    is.na(reason_u) | !nzchar(reason_u)          ~ "PROTOCOL DEVIATION",
    grepl("ADVERSE EVENT|AE",       reason_u)    ~ "ADVERSE EVENT",
    grepl("WITHDRAW|CONSENT",       reason_u)    ~ "WITHDRAWAL BY SUBJECT",
    grepl("DEATH|DIED",             reason_u)    ~ "DEATH",
    grepl("LACK.*EFFICACY|EFFICACY",reason_u)    ~ "LACK OF EFFICACY",
    grepl("LOST.*FOLLOW|LTF",       reason_u)    ~ "LOST TO FOLLOW-UP",
    grepl("PHYSICIAN|INVESTIGATOR", reason_u)    ~ "PHYSICIAN DECISION",
    grepl("PROTOCOL",               reason_u)    ~ "PROTOCOL DEVIATION",
    grepl("SPONSOR",                reason_u)    ~ "STUDY TERMINATED BY SPONSOR",
    TRUE                                          ~ "PROTOCOL DEVIATION"
  )
}
```

---

## P21 rules and fixes

### Resolved rules

#### SD1374 — No Disposition record found for subject
**Root cause**: DS only processed `ds_raw` (Disposition form), which has only
2 subjects. 808 of 810 DM subjects had no DS row at all.

**Fix** (`program/sdtm/ds.R`): Added Layers 2 and 3 (see "Three-layer build
pattern" below). DS now covers 592 subjects.

**Coverage after fix**: 592 / 810 subjects have ≥1 DS row.
**Residual limitation**: 218 subjects have no Eligibility startdate and were
not randomized — no date source available for them.

---

#### SD1240 — No Informed Consent record in DS for subject
**Root cause**: Same as SD1374 — DS was not generating rows for most subjects.

**Fix**: Layer 2 generates `DSDECOD = "INFORMED CONSENT OBTAINED"` for all
580 subjects with an Eligibility form startdate, using that startdate as proxy.

**Coverage after fix**: 580 / 810 subjects have a consent row.

---

#### CT2005 — DSDECOD not in controlled terminology codelist
Two violations:
1. `EARLY TERMINATION` — not a valid NCOMPLT term
2. `SCREENING COMPLETED` — not a valid PROTMLST term

**Fix 1** (`map_et_reason`): Map EARLYTERMINATIONREASON free text to specific
NCOMPLT terms (see mapping table above). `status_rows` suppressed — STATUSONSTUDY
"Early Termination" is redundant with et_rows and not CT-compliant.

**Fix 2**: Removed `elig_screen_rows` (SCREENING COMPLETED) from Layer 2.
Replaced with `elig_eligible_rows` (ELIGIBILITY CRITERIA MET), which IS in
PROTMLST and captures the same clinical intent.

---

#### SD0022 / SD1118 — Missing DSSTDTC
**Root cause**: Dedup logic sorted by `.src_priority` first, so Layer-1
Disposition-form rows (which lack a `startdate` for these 2 subjects) were
winning over Layer-2 rows that carried a date.

**Fix** (`program/sdtm/ds.R`): Sort `is.na(DSSTDTC)` ascending before
`.src_priority` in the `arrange()` call — non-null dates always win regardless
of source layer:
```r
arrange(subjectkey, DSDECOD,
        is.na(DSSTDTC),   # FALSE (has date) comes before TRUE (no date)
        .src_priority)
```
**Coverage after fix**: 1,441 / 1,442 rows have non-null DSSTDTC.

---

#### SD1088 — DSSTDY not populated
**Root cause**: DSSTDY was set to `NA_integer_` — never derived.

**Fix** (`program/sdtm/ds.R`): Join `dm$RFSTDTC` onto DS and compute study day:
```r
dm_ref <- dm |> select(USUBJID, RFSTDTC)

# In the mutate block (after left_join(dm_ref, by = "USUBJID")):
DSSTDY = dplyr::if_else(
  !is.na(DSSTDTC) & !is.na(RFSTDTC),
  as.integer(as.Date(DSSTDTC) - as.Date(RFSTDTC)) +
    ifelse(DSSTDTC >= RFSTDTC, 1L, 0L),
  NA_integer_
),
```
**Coverage after fix**: 1,441 / 1,442 rows have non-null DSSTDY (same
coverage as DSSTDTC).

---

#### SD1367 — Multiple disposition events for same DSCAT and EPOCH
**Root cause**: The 2 Disposition-form subjects had 3 rows in SCREENING epoch
(INFORMED CONSENT OBTAINED + ELIGIBILITY CRITERIA MET + SCREENING COMPLETED).

**Fix**: Resolved collaterally by the CT2005 fix — removing SCREENING
COMPLETED rows leaves exactly 2 SCREENING-epoch rows per subject.

---

### Known data limitations

| Rule | Residual count | Reason |
|------|---------------|--------|
| SD1374 no DS record | ~218 subjects | No Eligibility startdate and not randomized — no date source available |
| SD1240 no consent record | ~230 subjects | No Eligibility startdate — same population as above |
| SD0022 DSSTDTC null | 1 row (SS_MGH213 AE early termination) | No EARLYTERMINATIONDATE in source; Disposition form carries no startdate |
| SD1078 DSSCAT all null | 1,442 rows | No subcategory data in synthetic export; Perm variable retained |

---

## Three-layer build pattern

```
Layer 1 (priority 1): Disposition-form PD rows  — 2 subjects, exact CRF dates
Layer 2 (priority 2): Eligibility-form startdate — 580 subjects, proxy dates
Layer 3 (priority 2): Rand-form startdate        — 280 subjects, proxy dates

Dedup: arrange(subjectkey, DSDECOD, is.na(DSSTDTC), .src_priority)
       then distinct(subjectkey, DSDECOD, .keep_all = TRUE)
       → non-null date wins; ties broken by lower src_priority
```

Key milestones generated per layer:

| Layer | DSDECOD | DSCAT | EPOCH | Date source |
|-------|---------|-------|-------|-------------|
| 1 | INFORMED CONSENT OBTAINED | PROTOCOL MILESTONE | SCREENING | CONSENTEDDT |
| 1 | ELIGIBILITY CRITERIA MET | PROTOCOL MILESTONE | SCREENING | Disposition startdate |
| 1 | RANDOMIZED | PROTOCOL MILESTONE | TREATMENT | Disposition startdate |
| 1 | TREATMENT STARTED | PROTOCOL MILESTONE | TREATMENT | Disposition startdate |
| 1 | COMPLETED PRIMARY OUTCOMES | PROTOCOL MILESTONE | TREATMENT | Disposition startdate |
| 1 | COMPLETED SECONDARY OUTCOMES | PROTOCOL MILESTONE | TREATMENT | Disposition startdate |
| 1 | <mapped ET reason> | DISPOSITION EVENT | FOLLOW-UP | EARLYTERMINATIONDATE |
| 2 | INFORMED CONSENT OBTAINED | PROTOCOL MILESTONE | SCREENING | IE startdate |
| 2 | ELIGIBILITY CRITERIA MET | PROTOCOL MILESTONE | SCREENING | IE startdate |
| 3 | RANDOMIZED | PROTOCOL MILESTONE | TREATMENT | rand startdate |

---

## Cross-domain dependencies

| Dependency | Direction | Notes |
|------------|-----------|-------|
| DM.RFSTDTC | DS reads DM | Required for DSSTDY derivation; load `data/sdtm/dm.rds` |
| DS rows per subject | DM validated against DS | P21 SD1374/SD1240 fire on DM when DS has no record |
| DS.DSDECOD = INFORMED CONSENT OBTAINED | DM.RFICDTC cross-check | P21 SD1240 pairs with SD1210 on DM |

**Rebuild order**: DM must be rebuilt before DS when DM changes affect RFSTDTC.

---

## Rebuild command

```bash
Rscript program/sdtm/ds.R 2>&1 | grep -v "renv\|out-of-sync\|masked\|built under"
```

Expected output:
```
DS written: 1442 rows x 13 cols
Unique subjects: 592
DSSTDTC non-null: 1441 / 1442
DSSTDY  non-null: 1441 / 1442
```

Sanity checks:
```r
ds <- readRDS("data/sdtm/ds.rds")
# No invalid DSDECOD values
invalid_decod <- c("EARLY TERMINATION", "SCREENING COMPLETED")
stopifnot(!any(ds$DSDECOD %in% invalid_decod))
# DSSEQ unique within USUBJID
stopifnot(!anyDuplicated(ds[, c("USUBJID", "DSSEQ")]))
# All DS subjects in DM
dm_ids <- readRDS("data/sdtm/dm.rds")$USUBJID
stopifnot(all(ds$USUBJID %in% dm_ids))
```
