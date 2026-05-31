## --------------------------------------------------------------------
## DS — Disposition
## Spec:   spec/sdtm/ds.yaml
## Inputs: data/raw/ds.rds (Disposition), data/raw/ie.rds, data/raw/rand.rds
## Output: data/sdtm/ds.rds
## --------------------------------------------------------------------

library(dplyr)
library(tidyr)

source("program/sdtm/ut_visits.R", chdir = FALSE)

ds_raw   <- readRDS("data/raw/ds.rds")
ie_raw   <- readRDS("data/raw/ie.rds")
rand_raw <- readRDS("data/raw/rand.rds")

key_link <- bind_rows(ds_raw, ie_raw, rand_raw) |>
  distinct(subjectkey, studysubjectid) |>
  mutate(USUBJID = make_usubjid(studysubjectid))

## ── Layer 1: Disposition-form milestones (highest priority; sparse — 2 subjects)

pd <- ds_raw |>
  filter(itemgroupname == "PD") |>
  select(subjectkey, itemname, value, startdate, eventname, studyeventoid) |>
  pivot_wider(names_from = itemname, values_from = value,
              values_fn = ~ dplyr::first(.x))

milestones <- list(
  list(flag = "CONSENTED",                 term = "Informed consent obtained",         decod = "INFORMED CONSENT OBTAINED",  date_col = "CONSENTEDDT", cat = "PROTOCOL MILESTONE", epoch = "SCREENING"),
  list(flag = "SCREENED",                  term = "Screening completed",                decod = "SCREENING COMPLETED",        date_col = NA_character_, cat = "PROTOCOL MILESTONE", epoch = "SCREENING"),
  list(flag = "ELIGIBLE",                  term = "Determined eligible",                decod = "ELIGIBILITY CRITERIA MET",   date_col = NA_character_, cat = "PROTOCOL MILESTONE", epoch = "SCREENING"),
  list(flag = "RANDOMIZED",                term = "Randomized",                         decod = "RANDOMIZED",                 date_col = NA_character_, cat = "PROTOCOL MILESTONE", epoch = "TREATMENT"),
  list(flag = "RECEIVEDINTERVENTION",      term = "Received study intervention",        decod = "TREATMENT STARTED",          date_col = NA_character_, cat = "PROTOCOL MILESTONE", epoch = "TREATMENT"),
  list(flag = "PRIMARYOUTCOMESCOMPLETE",   term = "Completed primary outcomes",         decod = "COMPLETED PRIMARY OUTCOMES", date_col = NA_character_, cat = "PROTOCOL MILESTONE", epoch = "TREATMENT"),
  list(flag = "SECONDARYOUTCOMESCOMPLETE", term = "Completed secondary outcomes",       decod = "COMPLETED SECONDARY OUTCOMES", date_col = NA_character_, cat = "PROTOCOL MILESTONE", epoch = "TREATMENT")
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
      DSDECOD = "EARLY TERMINATION",
      DSCAT   = "DISPOSITION EVENT",
      EPOCH   = "FOLLOW-UP",
      DSSTDTC = `if`("EARLYTERMINATIONDATE" %in% names(pd), EARLYTERMINATIONDATE, startdate),
      .src_priority = 1L
    )
} else NULL

status_rows <- if ("STATUSONSTUDY" %in% names(pd)) {
  pd |>
    filter(!is.na(STATUSONSTUDY) & nzchar(STATUSONSTUDY)) |>
    transmute(
      subjectkey, startdate, eventname, studyeventoid,
      DSTERM  = STATUSONSTUDY,
      DSDECOD = toupper(STATUSONSTUDY),
      DSCAT   = "DISPOSITION EVENT",
      EPOCH   = "FOLLOW-UP",
      DSSTDTC = startdate,
      .src_priority = 1L
    )
} else NULL

## ── Layer 2: Eligibility-form milestones for all subjects with IE data
## The SE_ENROLLMENT startdate is the first on-study encounter and serves as
## the proxy date for INFORMED CONSENT OBTAINED and SCREENING COMPLETED when
## no Disposition-form date is available.

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

elig_screen_rows <- elig_dates |>
  transmute(
    subjectkey,
    startdate = elig_dt, studyeventoid, eventname,
    DSTERM    = "Screening completed",
    DSDECOD   = "SCREENING COMPLETED",
    DSCAT     = "PROTOCOL MILESTONE",
    EPOCH     = "SCREENING",
    DSSTDTC   = elig_dt,
    .src_priority = 2L
  )

## ── Layer 3: Randomization-form milestones for all randomized subjects

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

## ── Combine all layers; Disposition-form records win on (subjectkey, DSDECOD)

ds <- bind_rows(milestone_rows, et_rows, status_rows,
                elig_consent_rows, elig_screen_rows, rand_rows) |>
  arrange(subjectkey, DSDECOD, .src_priority) |>
  distinct(subjectkey, DSDECOD, .keep_all = TRUE) |>
  select(-.src_priority) |>
  left_join(key_link |> select(subjectkey, USUBJID), by = "subjectkey") |>
  mutate(DSSTDTC = normalize_iso_date(DSSTDTC)) |>
  arrange(USUBJID, DSSTDTC, DSCAT, DSDECOD) |>
  mutate(
    STUDYID  = "CART-T-PILOT",
    DOMAIN   = "DS",
    DSSCAT   = NA_character_,
    DSSTDY   = NA_integer_,
    DSSEQ    = row_number(),
    VISITNUM = derive_visitnum(studyeventoid),
    VISIT    = eventname,
    .by = USUBJID
  ) |>
  select(STUDYID, DOMAIN, USUBJID, DSSEQ,
         DSTERM, DSDECOD, DSCAT, DSSCAT, EPOCH,
         DSSTDTC, DSSTDY, VISITNUM, VISIT)

saveRDS(ds, "data/sdtm/ds.rds")
cat(sprintf("DS written: %d rows x %d cols\n", nrow(ds), ncol(ds)))
