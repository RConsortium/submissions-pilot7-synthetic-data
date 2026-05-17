## --------------------------------------------------------------------
## CM — Concomitant Medications
## Spec:   spec/sdtm/cm.yaml
## Inputs: data/raw/cm.rds (ConMed)
## Output: data/sdtm/cm.rds
## --------------------------------------------------------------------

library(dplyr)
library(tidyr)

source("program/sdtm/ut_visits.R", chdir = FALSE)

raw <- readRDS("data/raw/cm.rds")

key_link <- raw |>
  distinct(subjectkey, studysubjectid) |>
  mutate(USUBJID = make_usubjid(studysubjectid))

cm_items <- c("CMTRTL", "CMTRTLX", "MEDNAME",
              "CMDOSE", "CMDOSU", "CMDOSUTXT",
              "CMDOSFRM", "CMDOSFRMTEXT", "CMDOSFRQ", "CMROUTE",
              "CMINDC", "CMSTDAT", "CMENDAT", "ONGOING",
              "RXCUI", "RXAUI", "RXSTR", "RXTTY", "RXTYPE")

wide <- raw |>
  filter(itemgroupname == "group1", itemname %in% cm_items) |>
  select(subjectkey, itemgrouprepeatkey,
         eventname, studyeventoid, startdate,
         itemname, value) |>
  pivot_wider(names_from = itemname, values_from = value,
              values_fn = ~ dplyr::first(.x))

cm <- wide |>
  filter(!is.na(CMTRTL) & nzchar(CMTRTL)) |>
  left_join(key_link |> select(subjectkey, USUBJID), by = "subjectkey") |>
  mutate(
    STUDYID  = "CART-T-PILOT",
    DOMAIN   = "CM",
    CMTRT    = CMTRTL,
    CMMODIFY = CMTRTLX,
    CMDECOD  = MEDNAME,
    CMRXCUI  = RXCUI,
    CMCLAS   = RXTTY,
    CMDOSE   = suppressWarnings(as.numeric(CMDOSE)),
    CMDOSU   = dplyr::coalesce(CMDOSU, CMDOSUTXT),
    CMDOSFRM = dplyr::coalesce(CMDOSFRM, CMDOSFRMTEXT),
    CMDOSFRQ = CMDOSFRQ,
    CMROUTE  = CMROUTE,
    CMINDC   = CMINDC,
    CMSTDTC  = normalize_iso_date(CMSTDAT),
    CMENDTC  = normalize_iso_date(
                 ifelse(!is.na(ONGOING) & toupper(ONGOING) == "Y", NA_character_, CMENDAT)),
    CMENRF   = ifelse(!is.na(ONGOING) & toupper(ONGOING) == "Y", "ONGOING", NA_character_),
    CMSTDY   = NA_integer_,
    CMENDY   = NA_integer_,
    VISITNUM = derive_visitnum(studyeventoid),
    VISIT    = eventname
  ) |>
  arrange(USUBJID, CMSTDTC, CMTRT) |>
  mutate(CMSEQ = row_number(), .by = USUBJID) |>
  select(STUDYID, DOMAIN, USUBJID, CMSEQ,
         CMTRT, CMMODIFY, CMDECOD, CMRXCUI, CMCLAS,
         CMDOSE, CMDOSU, CMDOSFRM, CMDOSFRQ, CMROUTE,
         CMINDC, CMSTDTC, CMENDTC, CMENRF, CMSTDY, CMENDY,
         VISITNUM, VISIT)

saveRDS(cm, "data/sdtm/cm.rds")
cat(sprintf("CM written: %d rows x %d cols\n", nrow(cm), ncol(cm)))
