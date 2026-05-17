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

demog      <- pivot_subject_items(dm_raw,   c("PTSEX", "PTRACE", "HISP", "OTHERRACE"))
elig       <- pivot_subject_items(ie_raw,   c("BDAY", "PTAGE", "PTBYEAR"))
randomized <- pivot_subject_items(rand_raw, c("PROFILE"))
disp       <- pivot_subject_items(ds_raw,   c("CONSENTEDDT", "EARLYTERMINATIONDATE"))

dm <- subjects |>
  left_join(demog,      by = "subjectkey") |>
  left_join(elig,       by = "subjectkey") |>
  left_join(randomized, by = "subjectkey") |>
  left_join(disp,       by = "subjectkey") |>
  mutate(
    STUDYID  = "CART-T-PILOT",
    DOMAIN   = "DM",
    SITEID   = "01",
    SUBJID   = studysubjectid,
    USUBJID  = make_usubjid(SUBJID),

    RFICDTC  = normalize_iso_date(CONSENTEDDT),
    RFSTDTC  = RFICDTC,
    RFENDTC  = normalize_iso_date(EARLYTERMINATIONDATE),
    RFXSTDTC = NA_character_,
    RFXENDTC = NA_character_,
    RFPENDTC = normalize_iso_date(EARLYTERMINATIONDATE),

    BRTHDTC  = normalize_iso_date(dplyr::coalesce(
      BDAY,
      ifelse(!is.na(PTBYEAR) & nzchar(PTBYEAR), paste0(PTBYEAR, "-01-01"), NA_character_)
    )),
    AGE      = suppressWarnings(as.integer(PTAGE)),
    AGEU     = "YEARS",

    SEX      = dplyr::recode(toupper(PTSEX), M = "M", F = "F",
                             .default = "U", .missing = "U"),
    RACE     = toupper(PTRACE),
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
