## --------------------------------------------------------------------
## MH — Medical History
## Spec:   spec/sdtm/mh.yaml
## Inputs: data/raw/dm.rds (group1, group2 item groups), data/sdtm/dm.rds (USUBJID)
## Output: data/sdtm/mh.rds
## --------------------------------------------------------------------

library(dplyr)
library(tidyr)

source("program/sdtm/ut_visits.R", chdir = FALSE)

raw <- readRDS("data/raw/dm.rds")

key_link <- raw |>
  distinct(subjectkey, studysubjectid) |>
  mutate(USUBJID = make_usubjid(studysubjectid))

mh_group1 <- raw |>
  filter(itemgroupname == "group1",
         itemname %in% c("DIAG", "BODY", "DATE", "ONG", "STOP")) |>
  select(subjectkey, itemgrouprepeatkey, eventname, studyeventoid,
         startdate, itemname, value) |>
  pivot_wider(names_from = itemname, values_from = value,
              values_fn = ~ dplyr::first(.x)) |>
  filter(!is.na(DIAG) & nzchar(DIAG)) |>
  transmute(
    subjectkey,
    eventname, studyeventoid, startdate,
    MHCAT   = "GENERAL MEDICAL HISTORY",
    MHTERM  = DIAG,
    MHSCAT  = BODY,
    MHSTDTC = normalize_iso_date(DATE),
    MHENDTC = normalize_iso_date(STOP),
    MHENRF  = ifelse(!is.na(ONG) & toupper(ONG) == "Y", "ONGOING", NA_character_),
    MHSPID  = NA_character_
  )

mh_group2 <- raw |>
  filter(itemgroupname == "group2",
         itemname %in% c("CANCER1", "CANCER2", "CANCERORG", "DIAGNOSED")) |>
  select(subjectkey, itemgrouprepeatkey, eventname, studyeventoid,
         startdate, itemname, value) |>
  pivot_wider(names_from = itemname, values_from = value,
              values_fn = ~ dplyr::first(.x))

mh_group2_long <- bind_rows(
  mh_group2 |>
    filter(!is.na(CANCER1) & nzchar(CANCER1)) |>
    transmute(subjectkey, eventname, studyeventoid, startdate,
              MHCAT = "CANCER HISTORY", MHTERM = CANCER1,
              MHSCAT = NA_character_, MHSTDTC = normalize_iso_date(DIAGNOSED),
              MHENDTC = NA_character_, MHENRF = NA_character_,
              MHSPID = CANCERORG),
  mh_group2 |>
    filter(!is.na(CANCER2) & nzchar(CANCER2)) |>
    transmute(subjectkey, eventname, studyeventoid, startdate,
              MHCAT = "CANCER HISTORY", MHTERM = CANCER2,
              MHSCAT = NA_character_, MHSTDTC = normalize_iso_date(DIAGNOSED),
              MHENDTC = NA_character_, MHENRF = NA_character_,
              MHSPID = CANCERORG)
)

mh <- bind_rows(mh_group1, mh_group2_long) |>
  left_join(key_link |> select(subjectkey, USUBJID), by = "subjectkey") |>
  arrange(USUBJID, MHSTDTC, MHCAT, MHTERM) |>
  mutate(
    STUDYID  = "CART-T-PILOT",
    DOMAIN   = "MH",
    MHSEQ    = row_number(),
    MHDECOD  = NA_character_,
    MHBODSYS = NA_character_,
    MHPRESP  = NA_character_,
    MHOCCUR  = NA_character_,
    MHSTAT   = NA_character_,
    MHSTDY   = NA_integer_,
    VISITNUM = derive_visitnum(studyeventoid),
    VISIT    = eventname,
    .by = USUBJID
  ) |>
  select(STUDYID, DOMAIN, USUBJID, MHSEQ, MHSPID, MHTERM, MHDECOD, MHBODSYS,
         MHCAT, MHSCAT, MHPRESP, MHOCCUR, MHSTAT, MHENRF,
         MHSTDTC, MHENDTC, MHSTDY, VISITNUM, VISIT)

saveRDS(mh, "data/sdtm/mh.rds")
cat(sprintf("MH written: %d rows x %d cols\n", nrow(mh), ncol(mh)))
