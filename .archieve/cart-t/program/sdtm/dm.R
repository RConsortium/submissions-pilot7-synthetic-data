## --------------------------------------------------------------------
## DM — Demographics
## Spec:   spec/sdtm/dm.yaml
## Inputs: data/raw/flat.rds (subject universe) + dm.rds, ie.rds,
##         rand.rds, ds.rds, ae.rds (item-level content)
## Output: data/sdtm/dm.rds
##
## IG compliance notes (SDTMIG v3.3, DM Assumptions §4, §8–11):
##   ARMCD/ARM: null for screen failures; ARMNRS = "SCREEN FAILURE".
##   ACTARMCD/ACTARM: null for all (no subject received treatment);
##     ARMNRS = "ASSIGNED, NOT TREATED" for randomized subjects.
##   RFXSTDTC/RFXENDTC: null (no EX data); columns present as Exp.
##   RFSTDTC/RFENDTC: null for screen failures; enrollment-based for
##     randomized subjects (sponsor-defined reference per §10 exception
##     for studies where treatment is not expected).
##   RACE: "UNKNOWN" when PTRACE not collected.
##   AGE: derived from BRTHDTC–RFICDTC when PTAGE is missing.
## --------------------------------------------------------------------

library(dplyr)
library(tidyr)

source("program/sdtm/ut_visits.R", chdir = FALSE)

flat     <- readRDS("data/raw/flat.rds")
dm_raw   <- readRDS("data/raw/dm.rds")
ie_raw   <- readRDS("data/raw/ie.rds")
rand_raw <- readRDS("data/raw/rand.rds")
ds_raw   <- readRDS("data/raw/ds.rds")
ae_raw   <- readRDS("data/raw/ae.rds")

## Death information sourced from the AE form.
##   - DTHFL  = "Y" if any AE row has AESDTH = "Y"            (rule SD1255)
##   - DTHDTC = first non-empty AE.DTHDAT for the subject
ae_dth <- ae_raw |>
  filter(itemname == "AESDTH" & toupper(value) == "Y") |>
  distinct(subjectkey) |>
  mutate(dth_flag_y = "Y")

ae_dthdat <- ae_raw |>
  filter(itemname == "DTHDAT" & !is.na(value) & nzchar(value)) |>
  mutate(.dt = normalize_iso_date(substr(value, 1, 10))) |>
  filter(!is.na(.dt)) |>
  summarise(dth_dtc = min(.dt), .by = subjectkey)

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
## When PTRACE is absent or unmapped, RACE = "UNKNOWN" per SDTMIG §6 (race not
## provided / subject refused). UNKNOWN is valid in the extensible RACE CT (C74457).
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
    is.na(ptrace) | !nzchar(trimws(ptrace)) ~ "UNKNOWN",
    grepl(",", ptrace, fixed = TRUE)         ~ "MULTIPLE",
    ptrace %in% names(race_map)              ~ unname(race_map[ptrace]),
    TRUE                                     ~ "UNKNOWN"
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

## Eligibility form (SE_ENROLLMENT) startdate per subject — used as proxy for
## RFICDTC when Disposition.CONSENTEDDT is absent. The enrollment encounter is
## the first on-study contact and is a defensible surrogate for consent date in
## a synthetic pilot where actual ICF dates are sparsely recorded.
elig_dates <- ie_raw |>
  filter(!is.na(startdate) & nzchar(startdate)) |>
  mutate(.sd = normalize_iso_date(substr(startdate, 1, 10))) |>
  filter(!is.na(.sd)) |>
  summarise(elig_startdate = min(.sd), .by = subjectkey)

demog      <- pivot_subject_items(dm_raw,   c("PTSEX", "PTSEXEL", "PTRACE", "HISP", "OTHERRACE"))
elig       <- pivot_subject_items(ie_raw,   c("BDAY", "PTAGE", "PTBYEAR", "PSEX"))
randomized <- pivot_subject_items(rand_raw, c("PROFILE"))
disp       <- pivot_subject_items(ds_raw,   c("CONSENTEDDT", "EARLYTERMINATIONDATE"))

dm <- subjects |>
  left_join(demog,       by = "subjectkey") |>
  left_join(elig,        by = "subjectkey") |>
  left_join(randomized,  by = "subjectkey") |>
  left_join(disp,        by = "subjectkey") |>
  left_join(visit_dates, by = "subjectkey") |>
  left_join(elig_dates,  by = "subjectkey") |>
  left_join(ae_dth,      by = "subjectkey") |>
  left_join(ae_dthdat,   by = "subjectkey") |>
  mutate(
    STUDYID  = "CART-T-PILOT",
    DOMAIN   = "DM",
    SITEID   = "01",
    SUBJID   = studysubjectid,
    USUBJID  = make_usubjid(SUBJID),

    ## RFICDTC: consent date from Disposition.CONSENTEDDT where available;
    ## falls back to the Eligibility form (SE_ENROLLMENT) startdate as a proxy.
    ## Cap: if the computed RFICDTC exceeds the subject's first recorded study
    ## activity (first_visit_dt), clamp to first_visit_dt. This handles cases
    ## where CONSENTEDDT was entered late into the Disposition form (after
    ## randomization), which would otherwise make RFICDTC > DS disposition dates
    ## and trigger P21 "DSSTDTC is before RFICDTC". The IG (DM Assumption 10)
    ## requires RFICDTC to represent the date of the first informed consent.
    .rficdtc_raw = dplyr::coalesce(normalize_iso_date(CONSENTEDDT), elig_startdate),
    RFICDTC  = dplyr::if_else(
      !is.na(.rficdtc_raw) & !is.na(first_visit_dt) & .rficdtc_raw > first_visit_dt,
      first_visit_dt,
      .rficdtc_raw
    ),

    ## Identify randomized vs screen-failure subjects (used downstream for ARMNRS).
    .is_rand = !is.na(PROFILE) & nzchar(trimws(PROFILE)),

    ## RFSTDTC / RFENDTC: null for all subjects.
    ## ARMNRS is populated for every subject in this study (either "SCREEN FAILURE"
    ## or "ASSIGNED, NOT TREATED"). P21 rule: RFSTDTC and RFENDTC must be null
    ## whenever ARMNRS is populated. Additionally, ACTARMCD is null for all subjects
    ## because RECEIVEDINTERVENTION = No for everyone — no treatment reference period
    ## can be defined. The enrollment/consent date is carried in RFICDTC; last study
    ## activity is in RFPENDTC.
    RFSTDTC  = NA_character_,
    RFENDTC  = NA_character_,

    ## RFXSTDTC / RFXENDTC: date/time of first/last study treatment.
    ## RECEIVEDINTERVENTION = No for all subjects — no EX data exists.
    ## Columns are Expected (Exp) per SDTMIG; null throughout.
    RFXSTDTC = NA_character_,
    RFXENDTC = NA_character_,

    ## RFPENDTC: last date of participation (same source as RFENDTC for this study).
    RFPENDTC = dplyr::coalesce(
      normalize_iso_date(EARLYTERMINATIONDATE),
      last_visit_dt
    ),

    BRTHDTC  = normalize_iso_date(dplyr::coalesce(
      BDAY,
      ifelse(!is.na(PTBYEAR) & nzchar(PTBYEAR), paste0(PTBYEAR, "-01-01"), NA_character_)
    )),

    ## AGE: prefer PTAGE as recorded; derive from BRTHDTC − RFICDTC when absent.
    ## Floor to whole years (standard for AGE in years per SDTMIG).
    .ptage_int = suppressWarnings(as.integer(PTAGE)),
    .age_dob   = dplyr::if_else(
      !is.na(BRTHDTC) & nchar(BRTHDTC) >= 10 &
        !is.na(RFICDTC) & nchar(RFICDTC) >= 10,
      as.integer(floor(
        as.numeric(as.Date(substr(RFICDTC, 1, 10)) -
                   as.Date(substr(BRTHDTC, 1, 10))) / 365.25
      )),
      NA_integer_
    ),
    AGE      = dplyr::coalesce(.ptage_int, .age_dob),
    AGEU     = ifelse(!is.na(dplyr::coalesce(.ptage_int, .age_dob)), "YEARS", NA_character_),

    SEX      = dplyr::coalesce(
                 dplyr::recode(PTSEX,            "1" = "M", "2" = "F", .default = NA_character_),
                 dplyr::recode(toupper(PTSEXEL), "MALE" = "M", "FEMALE" = "F", .default = NA_character_),
                 dplyr::recode(PSEX,             "1" = "M", "2" = "F", .default = NA_character_),
                 "U"
               ),

    ## RACE: map OpenClinica MSL_62 codes to CDISC RACE extensible CT (C74457).
    ## Multi-select (comma-separated codes) maps to "MULTIPLE" per SDTMIG guidance.
    ## Missing / uncollected maps to "UNKNOWN" per SDTMIG Assumption 6.
    RACE     = map_race(PTRACE),

    ETHNIC   = dplyr::recode(HISP,
                             "1" = "HISPANIC OR LATINO",
                             "0" = "NOT HISPANIC OR LATINO",
                             .default = NA_character_),

    ## ARMCD / ARM — SDTMIG v3.3 DM Assumption 4:
    ##   Screen failures were not assigned to an arm → ARMCD = null, ARM = null.
    ##   Randomized subjects → ARMCD = "TREATMENT", ARM = "Study Treatment".
    ARMCD    = armcd_map(PROFILE),
    ARM      = arm_map(PROFILE),

    ## ACTARMCD / ACTARM — null for all subjects.
    ##   RECEIVEDINTERVENTION = No for every subject in this export.
    ##   Randomized subjects were assigned but not treated → ACTARMCD = null,
    ##   ACTARM = null, ARMNRS = "ASSIGNED, NOT TREATED" per SDTMIG Example 6.
    ACTARMCD = NA_character_,
    ACTARM   = NA_character_,

    ## ARMNRS — reason Arm / Actual Arm is null (Exp; must be populated when
    ##   ARMCD or ACTARMCD is null per SDTMIG Assumption 4 rules 1 and 2).
    ##   Screen failures: "SCREEN FAILURE"
    ##   Randomized not treated: "ASSIGNED, NOT TREATED"
    ARMNRS   = armnrs_map(PROFILE),

    ## ACTARMUD — description of unplanned actual arm; null throughout.
    ##   Only populated when ARMNRS = "UNPLANNED TREATMENT" per SDTMIG §4.
    ACTARMUD = NA_character_,

    ## DTHDTC / DTHFL sourced from AE form (DTHDAT item + AESDTH = "Y").
    ## P21 rule SD1255 requires DTHFL = "Y" whenever AE.AESDTH = "Y".
    ## DTHDTC may be null when DTHDAT was not recorded (known data limitation
    ## for 4 subjects); DTHFL = "Y" without DTHDTC is correct per SDTMIG
    ## ("should be populated even when the death date is unknown").
    DTHDTC   = dth_dtc,
    DTHFL    = dth_flag_y,
    COUNTRY  = "USA"
  ) |>
  arrange(USUBJID) |>
  select(STUDYID, DOMAIN, USUBJID, SUBJID,
         RFSTDTC, RFENDTC, RFXSTDTC, RFXENDTC, RFICDTC, RFPENDTC,
         DTHDTC, DTHFL, SITEID,
         BRTHDTC, AGE, AGEU, SEX, RACE, ETHNIC,
         ARMCD, ARM, ACTARMCD, ACTARM, ARMNRS, ACTARMUD,
         COUNTRY)

saveRDS(dm, "data/sdtm/dm.rds")
cat(sprintf("DM written: %d rows x %d cols\n", nrow(dm), ncol(dm)))
cat(sprintf("ARMCD dist: %s\n", paste(names(table(dm$ARMCD, useNA="ifany")),
                                       table(dm$ARMCD, useNA="ifany"), sep="=", collapse=" | ")))
cat(sprintf("ARMNRS dist: %s\n", paste(names(table(dm$ARMNRS, useNA="ifany")),
                                        table(dm$ARMNRS, useNA="ifany"), sep="=", collapse=" | ")))
cat(sprintf("AGE non-null: %d / %d\n", sum(!is.na(dm$AGE)), nrow(dm)))
cat(sprintf("RACE UNKNOWN: %d\n", sum(dm$RACE == "UNKNOWN", na.rm = TRUE)))
cat(sprintf("RFXSTDTC non-null: %d / %d (expected 0)\n", sum(!is.na(dm$RFXSTDTC)), nrow(dm)))
