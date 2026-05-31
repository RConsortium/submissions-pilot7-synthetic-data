## --------------------------------------------------------------------
## DM — Demographics
## Spec:   spec/sdtm/dm.yaml
## Inputs: data/raw/flat.rds (subject universe) + dm.rds, ie.rds,
##         rand.rds, ds.rds (item-level content)
## Output: data/sdtm/dm.rds
## --------------------------------------------------------------------

library(dplyr)
library(tidyr)

source("program/sdtm/ut_visits.R", chdir = FALSE)

flat     <- readRDS("data/raw/flat.rds")
dm_raw   <- readRDS("data/raw/dm.rds")
ie_raw   <- readRDS("data/raw/ie.rds")
rand_raw <- readRDS("data/raw/rand.rds")
ds_raw   <- readRDS("data/raw/ds.rds")

## Subject universe = every distinct subject that appears anywhere in
## the OpenClinica export. Guarantees DM is the master subject table.
subjects <- flat |>
  distinct(subjectkey, studysubjectid) |>
  arrange(studysubjectid)

pivot_subject_items <- function(raw, items) {
  raw |>
    filter(itemname %in% items) |>
    select(subjectkey, itemname, value) |>
    pivot_wider(
      names_from  = itemname,
      values_from = value,
      values_fn   = ~ dplyr::first(.x[!is.na(.x) & .x != ""])
    )
}

## Map PTRACE multi-select codes (comma-separated integers) to CDISC RACE CT.
## MSL_62 codelist from OpenClinica XML:
##   1 = American Indian/Alaskan Native
##   2 = Asian
##   3 = Black/African American
##   4 = Native Hawaiian/Pacific Islander
##   5 = White/Caucasian
##   6 = Other (free text captured in OTHERRACE)
## When multiple codes are comma-separated, SDTMIG instructs RACE = "MULTIPLE".
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

## First and last event startdate per subject, used as fallback for
## RFSTDTC / RFENDTC / RFPENDTC when CRF-specific dates are absent.
## startdate can be "yyyy-mm-dd" or "yyyy-mm-ddTHH:MM:SS"; take first 10 chars.
visit_dates <- flat |>
  filter(!is.na(startdate) & nzchar(startdate)) |>
  mutate(startdate_ymd = normalize_iso_date(substr(startdate, 1, 10))) |>
  filter(!is.na(startdate_ymd)) |>
  summarise(
    first_visit_dt = min(startdate_ymd),
    last_visit_dt  = max(startdate_ymd),
    .by = subjectkey
  )

demog      <- pivot_subject_items(dm_raw,   c("PTSEX", "PTRACE", "HISP", "OTHERRACE"))
elig       <- pivot_subject_items(ie_raw,   c("BDAY", "PTAGE", "PTBYEAR"))
randomized <- pivot_subject_items(rand_raw, c("PROFILE"))
disp       <- pivot_subject_items(ds_raw,   c("CONSENTEDDT", "EARLYTERMINATIONDATE"))

dm <- subjects |>
  left_join(demog,       by = "subjectkey") |>
  left_join(elig,        by = "subjectkey") |>
  left_join(randomized,  by = "subjectkey") |>
  left_join(disp,        by = "subjectkey") |>
  left_join(visit_dates, by = "subjectkey") |>
  mutate(
    STUDYID  = "CART-T-PILOT",
    DOMAIN   = "DM",
    SITEID   = "01",
    SUBJID   = studysubjectid,
    USUBJID  = make_usubjid(SUBJID),

    ## RFICDTC: informed consent date from Disposition.CONSENTEDDT.
    ## Sparsely populated in source data (only 1 subject has CONSENTEDDT).
    RFICDTC  = normalize_iso_date(CONSENTEDDT),

    ## RFSTDTC / RFENDTC / RFPENDTC: use CRF dates where available;
    ## fall back to first / last event startdate from the flat export.
    RFSTDTC  = dplyr::coalesce(RFICDTC, first_visit_dt),
    RFENDTC  = dplyr::coalesce(
      normalize_iso_date(EARLYTERMINATIONDATE),
      last_visit_dt
    ),
    RFXSTDTC = NA_character_,
    RFXENDTC = NA_character_,
    RFPENDTC = dplyr::coalesce(
      normalize_iso_date(EARLYTERMINATIONDATE),
      last_visit_dt
    ),

    BRTHDTC  = normalize_iso_date(dplyr::coalesce(
      BDAY,
      ifelse(!is.na(PTBYEAR) & nzchar(PTBYEAR), paste0(PTBYEAR, "-01-01"), NA_character_)
    )),
    AGE      = suppressWarnings(as.integer(PTAGE)),
    AGEU     = "YEARS",

    SEX      = dplyr::recode(toupper(PTSEX), M = "M", F = "F",
                             .default = "U", .missing = "U"),

    ## RACE: map OpenClinica MSL_62 codes to CDISC RACE extensible CT (C74457).
    ## Multi-select (comma-separated codes) maps to "MULTIPLE" per SDTMIG guidance.
    RACE     = map_race(PTRACE),

    ETHNIC   = dplyr::recode(toupper(HISP),
                             Y = "HISPANIC OR LATINO",
                             N = "NOT HISPANIC OR LATINO",
                             .default = NA_character_,
                             .missing  = NA_character_),

    ARMCD    = armcd_map(PROFILE),
    ARM      = arm_map(PROFILE),
    ACTARMCD = ARMCD,
    ACTARM   = ARM,

    DTHDTC   = NA_character_,
    DTHFL    = NA_character_,
    COUNTRY  = "USA"
  ) |>
  arrange(USUBJID) |>
  select(STUDYID, DOMAIN, USUBJID, SUBJID,
         RFSTDTC, RFENDTC, RFXSTDTC, RFXENDTC, RFICDTC, RFPENDTC,
         DTHDTC, DTHFL, SITEID,
         BRTHDTC, AGE, AGEU, SEX, RACE, ETHNIC,
         ARMCD, ARM, ACTARMCD, ACTARM, COUNTRY)

saveRDS(dm, "data/sdtm/dm.rds")
cat(sprintf("DM written: %d rows x %d cols\n", nrow(dm), ncol(dm)))
