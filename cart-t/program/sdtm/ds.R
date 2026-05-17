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

pd <- ds_raw |>
  filter(itemgroupname == "PD") |>
  select(subjectkey, itemname, value, startdate, eventname, studyeventoid) |>
  pivot_wider(names_from = itemname, values_from = value,
              values_fn = ~ dplyr::first(.x))

milestones <- list(
  list(flag = "CONSENTED",                 term = "Informed consent obtained",         decod = "INFORMED CONSENT OBTAINED", date_col = "CONSENTEDDT",            cat = "PROTOCOL MILESTONE", epoch = "SCREENING"),
  list(flag = "SCREENED",                  term = "Screening completed",                decod = "SCREENING COMPLETED",       date_col = NA_character_,            cat = "PROTOCOL MILESTONE", epoch = "SCREENING"),
  list(flag = "ELIGIBLE",                  term = "Determined eligible",                decod = "ELIGIBILITY CRITERIA MET",  date_col = NA_character_,            cat = "PROTOCOL MILESTONE", epoch = "SCREENING"),
  list(flag = "RANDOMIZED",                term = "Randomized",                         decod = "RANDOMIZED",                date_col = NA_character_,            cat = "PROTOCOL MILESTONE", epoch = "TREATMENT"),
  list(flag = "RECEIVEDINTERVENTION",      term = "Received study intervention",        decod = "TREATMENT STARTED",         date_col = NA_character_,            cat = "PROTOCOL MILESTONE", epoch = "TREATMENT"),
  list(flag = "PRIMARYOUTCOMESCOMPLETE",   term = "Completed primary outcomes",         decod = "COMPLETED PRIMARY OUTCOMES",date_col = NA_character_,            cat = "PROTOCOL MILESTONE", epoch = "TREATMENT"),
  list(flag = "SECONDARYOUTCOMESCOMPLETE", term = "Completed secondary outcomes",       decod = "COMPLETED SECONDARY OUTCOMES", date_col = NA_character_,         cat = "PROTOCOL MILESTONE", epoch = "TREATMENT")
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
      DSSTDTC = if (!is.na(m$date_col) && m$date_col %in% names(pd)) .data[[m$date_col]] else startdate
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
      DSSTDTC = `if`("EARLYTERMINATIONDATE" %in% names(pd), EARLYTERMINATIONDATE, startdate)
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
      DSSTDTC = startdate
    )
} else NULL

ds <- bind_rows(milestone_rows, et_rows, status_rows) |>
  left_join(key_link |> select(subjectkey, USUBJID), by = "subjectkey") |>
  mutate(DSSTDTC = normalize_iso_date(DSSTDTC)) |>
  arrange(USUBJID, DSSTDTC, DSCAT, DSDECOD) |>
  mutate(
    STUDYID = "CART-T-PILOT",
    DOMAIN  = "DS",
    DSSCAT  = NA_character_,
    DSSTDY  = NA_integer_,
    DSSEQ   = row_number(),
    VISITNUM = derive_visitnum(studyeventoid),
    VISIT    = eventname,
    .by = USUBJID
  ) |>
  select(STUDYID, DOMAIN, USUBJID, DSSEQ,
         DSTERM, DSDECOD, DSCAT, DSSCAT, EPOCH,
         DSSTDTC, DSSTDY, VISITNUM, VISIT)

saveRDS(ds, "data/sdtm/ds.rds")
cat(sprintf("DS written: %d rows x %d cols\n", nrow(ds), ncol(ds)))
