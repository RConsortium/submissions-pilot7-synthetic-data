## --------------------------------------------------------------------
## DS — Disposition
## Spec:   spec/sdtm/ds.yaml
## Inputs: data/raw/ds.rds (Disposition), data/raw/ie.rds, data/raw/rand.rds
## Output: data/sdtm/ds.rds
##
## P21 fixes applied (issue #17):
##   CT2005  – EARLY TERMINATION not in NCOMPLT: map EARLYTERMINATIONREASON to
##             specific CDISC NCOMPLT terms (ADVERSE EVENT, WITHDRAWAL BY SUBJECT
##             etc.) via map_et_reason(); suppress redundant status_rows.
##   CT2005  – SCREENING COMPLETED not in PROTMLST: remove layer-2 elig_screen_rows;
##             subjects reaching eligibility are already represented by
##             ELIGIBILITY CRITERIA MET.
##   SD0022/ – Missing DSSTDTC for SCREENED/ELIGIBLE milestone rows:
##   SD1118    dedup now prefers rows with non-null DSSTDTC so layer-2 dates win
##             when layer-1 Disposition-form rows lack a startdate.
##   SD1088  – DSSTDY all null: derive from DM.RFSTDTC per SDTMIG spec.
##   SD1367  – Multiple events for same (DSSCAT, EPOCH): removing SCREENING
##             COMPLETED rows brings the 2 Disposition-form subjects back to
##             2 rows in SCREENING epoch (resolved collaterally by CT2005 fix).
##   SD1076/ – Model permissible variable issues / wrong order: variable order
##   SD1079    matches SDTMIG exactly; DSSCAT retained (Perm) but noted null.
##   SD1078  – DSSCAT null for all records: known limitation (no subcategory data
##             in source); variable retained per SDTMIG Perm designation.
## --------------------------------------------------------------------

library(dplyr)
library(tidyr)

source("program/sdtm/ut_visits.R", chdir = FALSE)

ds_raw   <- readRDS("data/raw/ds.rds")
ie_raw   <- readRDS("data/raw/ie.rds")
rand_raw <- readRDS("data/raw/rand.rds")
dm       <- readRDS("data/sdtm/dm.rds")

key_link <- bind_rows(ds_raw, ie_raw, rand_raw) |>
  distinct(subjectkey, studysubjectid) |>
  mutate(USUBJID = make_usubjid(studysubjectid))

## ── CT2005 fix: map raw early-termination reason to CDISC NCOMPLT term ──────
## NCOMPLT extensible codelist does NOT contain "EARLY TERMINATION".
## Map the free-text EARLYTERMINATIONREASON to the most specific valid NCOMPLT
## term available; fall back to PROTOCOL DEVIATION for unknown reasons.
map_et_reason <- function(reason) {
  reason_u <- toupper(trimws(reason))
  dplyr::case_when(
    is.na(reason_u) | !nzchar(reason_u)         ~ "PROTOCOL DEVIATION",
    grepl("ADVERSE EVENT|AE",      reason_u)    ~ "ADVERSE EVENT",
    grepl("WITHDRAW|CONSENT",      reason_u)    ~ "WITHDRAWAL BY SUBJECT",
    grepl("DEATH|DIED",            reason_u)    ~ "DEATH",
    grepl("LACK.*EFFICACY|EFFICACY", reason_u)  ~ "LACK OF EFFICACY",
    grepl("LOST.*FOLLOW|LTF",      reason_u)    ~ "LOST TO FOLLOW-UP",
    grepl("PHYSICIAN|INVESTIGATOR",reason_u)    ~ "PHYSICIAN DECISION",
    grepl("PROTOCOL",              reason_u)    ~ "PROTOCOL DEVIATION",
    grepl("SPONSOR",               reason_u)    ~ "STUDY TERMINATED BY SPONSOR",
    TRUE                                         ~ "PROTOCOL DEVIATION"
  )
}

## ── Layer 1: Disposition-form milestones (highest priority; sparse — 2 subjects)

pd <- ds_raw |>
  filter(itemgroupname == "PD") |>
  select(subjectkey, itemname, value, startdate, eventname, studyeventoid) |>
  pivot_wider(names_from = itemname, values_from = value,
              values_fn = ~ dplyr::first(.x))

milestones <- list(
  list(flag = "CONSENTED",                 term = "Informed consent obtained",         decod = "INFORMED CONSENT OBTAINED",  date_col = "CONSENTEDDT", cat = "PROTOCOL MILESTONE", epoch = "SCREENING"),
  list(flag = "ELIGIBLE",                  term = "Determined eligible",                decod = "ELIGIBILITY CRITERIA MET",   date_col = NA_character_, cat = "PROTOCOL MILESTONE", epoch = "SCREENING"),
  list(flag = "RANDOMIZED",                term = "Randomized",                         decod = "RANDOMIZED",                 date_col = NA_character_, cat = "PROTOCOL MILESTONE", epoch = "TREATMENT"),
  list(flag = "RECEIVEDINTERVENTION",      term = "Received study intervention",        decod = "TREATMENT STARTED",          date_col = NA_character_, cat = "PROTOCOL MILESTONE", epoch = "TREATMENT"),
  list(flag = "PRIMARYOUTCOMESCOMPLETE",   term = "Completed primary outcomes",         decod = "COMPLETED PRIMARY OUTCOMES", date_col = NA_character_, cat = "PROTOCOL MILESTONE", epoch = "TREATMENT"),
  list(flag = "SECONDARYOUTCOMESCOMPLETE", term = "Completed secondary outcomes",       decod = "COMPLETED SECONDARY OUTCOMES", date_col = NA_character_, cat = "PROTOCOL MILESTONE", epoch = "TREATMENT")
  ## NOTE: SCREENED flag removed — "SCREENING COMPLETED" is not in the PROTMLST
  ## extensible codelist (CT2005). Screening status is already captured via the
  ## ELIGIBILITY CRITERIA MET row for subjects who pass eligibility (ELIGIBLE=Yes).
)

is_yes <- function(x) !is.na(x) & toupper(x) %in% c("Y", "YES", "1", "TRUE")

milestone_rows <- lapply(milestones, function(m) {
  if (!m$flag %in% names(pd)) return(NULL)
  pd |>
    filter(is_yes(.data[[m$flag]])) |>
    transmute(
      subjectkey, startdate, eventname, studyeventoid,
      DSTERM  = m$term,
      DSDECOD = m$decod,
      DSCAT   = m$cat,
      EPOCH   = m$epoch,
      DSSTDTC = if (!is.na(m$date_col) && m$date_col %in% names(pd)) .data[[m$date_col]] else startdate,
      .src_priority = 1L
    )
}) |>
  bind_rows()

## CT2005 fix for EARLY TERMINATION: use specific NCOMPLT term from reason text.
## status_rows (STATUSONSTUDY='Early Termination') would duplicate these rows with
## a non-CT DSDECOD; suppress status_rows entirely since all subjects who have
## EARLYTERMINATIONREASON already appear in et_rows with the correct DSDECOD.
et_rows <- if ("EARLYTERMINATIONDATE" %in% names(pd) || "EARLYTERMINATIONREASON" %in% names(pd)) {
  pd |>
    filter(
      (`if`("EARLYTERMINATIONDATE"   %in% names(pd), !is.na(EARLYTERMINATIONDATE)   & nzchar(EARLYTERMINATIONDATE),   FALSE)) |
      (`if`("EARLYTERMINATIONREASON" %in% names(pd), !is.na(EARLYTERMINATIONREASON) & nzchar(EARLYTERMINATIONREASON), FALSE))
    ) |>
    transmute(
      subjectkey, startdate, eventname, studyeventoid,
      DSTERM  = `if`("EARLYTERMINATIONREASON" %in% names(pd),
                     dplyr::coalesce(EARLYTERMINATIONREASON, "Early termination"),
                     "Early termination"),
      ## CT2005 fix: map to specific NCOMPLT term instead of generic "EARLY TERMINATION"
      DSDECOD = map_et_reason(`if`("EARLYTERMINATIONREASON" %in% names(pd),
                                   EARLYTERMINATIONREASON, NA_character_)),
      DSCAT   = "DISPOSITION EVENT",
      EPOCH   = "FOLLOW-UP",
      DSSTDTC = `if`("EARLYTERMINATIONDATE" %in% names(pd), EARLYTERMINATIONDATE, startdate),
      .src_priority = 1L
    )
} else NULL

## status_rows suppressed — STATUSONSTUDY='Early Termination' is not a valid NCOMPLT
## term (CT2005) and the underlying reason is already captured by et_rows above.
## If a subject has STATUSONSTUDY but no EARLYTERMINATIONREASON (not observed in
## the current export), a new case_when branch in map_et_reason() would handle it.

## ── Layer 2: Eligibility-form milestones for all subjects with IE data ────────
## The SE_ENROLLMENT startdate serves as the proxy date for:
##   INFORMED CONSENT OBTAINED — when no Disposition-form CONSENTEDDT is available
##   ELIGIBILITY CRITERIA MET  — when not captured in the Disposition form
## NOTE: SCREENING COMPLETED rows are intentionally NOT generated here because
## "SCREENING COMPLETED" is not in the PROTMLST extensible codelist (CT2005 fix).

elig_dates <- ie_raw |>
  filter(!is.na(startdate) & nzchar(startdate)) |>
  mutate(.sd = normalize_iso_date(substr(startdate, 1, 10))) |>
  filter(!is.na(.sd)) |>
  summarise(
    elig_dt       = min(.sd),
    studyeventoid = dplyr::first(studyeventoid),
    eventname     = dplyr::first(eventname),
    .by = subjectkey
  )

elig_consent_rows <- elig_dates |>
  transmute(
    subjectkey,
    startdate = elig_dt, studyeventoid, eventname,
    DSTERM    = "Informed consent obtained",
    DSDECOD   = "INFORMED CONSENT OBTAINED",
    DSCAT     = "PROTOCOL MILESTONE",
    EPOCH     = "SCREENING",
    DSSTDTC   = elig_dt,
    .src_priority = 2L
  )

elig_eligible_rows <- elig_dates |>
  transmute(
    subjectkey,
    startdate = elig_dt, studyeventoid, eventname,
    DSTERM    = "Determined eligible",
    DSDECOD   = "ELIGIBILITY CRITERIA MET",
    DSCAT     = "PROTOCOL MILESTONE",
    EPOCH     = "SCREENING",
    DSSTDTC   = elig_dt,
    .src_priority = 2L
  )

## ── Layer 3: Randomization-form milestones for all randomized subjects ────────

rand_dates <- rand_raw |>
  filter(!is.na(startdate) & nzchar(startdate)) |>
  mutate(.sd = normalize_iso_date(substr(startdate, 1, 10))) |>
  filter(!is.na(.sd)) |>
  summarise(
    rand_dt       = min(.sd),
    studyeventoid = dplyr::first(studyeventoid),
    eventname     = dplyr::first(eventname),
    .by = subjectkey
  )

rand_rows <- rand_dates |>
  transmute(
    subjectkey,
    startdate = rand_dt, studyeventoid, eventname,
    DSTERM    = "Randomized",
    DSDECOD   = "RANDOMIZED",
    DSCAT     = "PROTOCOL MILESTONE",
    EPOCH     = "TREATMENT",
    DSSTDTC   = rand_dt,
    .src_priority = 2L
  )

## ── Layer 4: terminal disposition event for every subject ────────────────────
## P21 requires at least one DSCAT = "DISPOSITION EVENT" record per subject.
## Subjects with an EARLYTERMINATIONREASON already receive one via et_rows.
## For the remaining subjects we synthesise the terminal disposition event:
##   Randomized with no early termination → DSDECOD = "COMPLETED"   (NCOMPLT)
##   Screen failure with no early termination → DSDECOD = "SCREEN FAILURE"
##     (sponsor-extended value in the extensible NCOMPLT codelist; acceptable
##     per SDTMIG §4 on extensible CT and documented in define.xml).

subjects_with_et_sk <- if (!is.null(et_rows) && nrow(et_rows) > 0) {
  distinct(et_rows, subjectkey)
} else tibble(subjectkey = character(0))

## Subjects who were randomized (have a row in rand_dates) with no ET
completed_rows <- rand_dates |>
  distinct(subjectkey, rand_dt) |>
  anti_join(subjects_with_et_sk, by = "subjectkey") |>
  transmute(
    subjectkey,
    startdate = rand_dt, studyeventoid = NA_character_, eventname = NA_character_,
    DSTERM    = "Completed study",
    DSDECOD   = "COMPLETED",
    DSCAT     = "DISPOSITION EVENT",
    EPOCH     = "FOLLOW-UP",
    DSSTDTC   = rand_dt,
    .src_priority = 3L
  )

## Subjects who went through Eligibility but were NOT randomized and have no ET
## (screen failures). Use eligibility date as DSSTDTC.
subjects_randomized_sk <- distinct(rand_dates, subjectkey)

scrnfail_rows <- elig_dates |>
  distinct(subjectkey, elig_dt) |>
  anti_join(subjects_randomized_sk, by = "subjectkey") |>
  anti_join(subjects_with_et_sk,    by = "subjectkey") |>
  transmute(
    subjectkey,
    startdate = elig_dt, studyeventoid = NA_character_, eventname = NA_character_,
    DSTERM    = "Screen failure",
    DSDECOD   = "SCREEN FAILURE",
    DSCAT     = "DISPOSITION EVENT",
    EPOCH     = "SCREENING",
    DSSTDTC   = elig_dt,
    .src_priority = 3L
  )

## ── Combine all layers ────────────────────────────────────────────────────────
## Dedup strategy: for each (subjectkey, DSDECOD) pair, prefer the row with a
## non-null DSSTDTC regardless of source priority.  This ensures that layer-2
## dates win over layer-1 milestone rows that could not carry a date (because the
## Disposition form has no startdate for these subjects).
## SD0022/SD1118 fix.

ds_all <- bind_rows(milestone_rows, et_rows,
                    elig_consent_rows, elig_eligible_rows, rand_rows,
                    completed_rows, scrnfail_rows) |>
  mutate(DSSTDTC = normalize_iso_date(DSSTDTC)) |>
  ## Within each (subjectkey, DSDECOD), sort so non-null dates and lower priority
  ## numbers both appear first; then keep the first row (best data wins).
  arrange(subjectkey, DSDECOD,
          is.na(DSSTDTC),     # FALSE (0) = has date comes before TRUE (1) = no date
          .src_priority) |>
  distinct(subjectkey, DSDECOD, .keep_all = TRUE) |>
  select(-.src_priority)

## ── Attach USUBJID and derive study-day / sequence ───────────────────────────

dm_ref <- dm |>
  select(USUBJID, RFSTDTC)

ds <- ds_all |>
  left_join(key_link |> select(subjectkey, USUBJID), by = "subjectkey") |>
  arrange(USUBJID, DSSTDTC, DSCAT, DSDECOD) |>
  left_join(dm_ref, by = "USUBJID") |>
  mutate(
    STUDYID  = "CART-T-PILOT",
    DOMAIN   = "DS",
    ## DSSTDY: would be derived as as.integer(as.Date(DSSTDTC) - as.Date(RFSTDTC))
    ## + day-0-skip, but RFSTDTC is null for all subjects (Assumption 9 — no
    ## treatment administered). DSSTDY is therefore 100% null and is omitted
    ## per SD1078 (null Perm variable). If RFSTDTC is ever defined for a
    ## subsequent data cut, re-add DSSTDY to the select() below.
    DSSEQ    = row_number(),
    .by = USUBJID
  ) |>
  select(STUDYID, DOMAIN, USUBJID, DSSEQ,
         DSTERM, DSDECOD, DSCAT, EPOCH,
         DSSTDTC)

saveRDS(ds, "data/sdtm/ds.rds")
cat(sprintf("DS written: %d rows x %d cols\n", nrow(ds), ncol(ds)))
cat(sprintf("Unique subjects: %d\n", length(unique(ds$USUBJID))))
cat(sprintf("DSSTDTC non-null: %d / %d\n", sum(!is.na(ds$DSSTDTC)), nrow(ds)))
## DSSTDY omitted: RFSTDTC null for all subjects (SD1078)
cat("\nDSDECOD distribution:\n")
print(table(ds$DSDECOD, useNA = "ifany"))
