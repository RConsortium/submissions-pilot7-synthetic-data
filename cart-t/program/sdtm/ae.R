## --------------------------------------------------------------------
## AE — Adverse Events
## Spec:   spec/sdtm/ae.yaml
## Inputs: data/raw/ae.rds, data/sdtm/dm.rds
## Output: data/sdtm/ae.rds
## --------------------------------------------------------------------

library(dplyr)
library(tidyr)

source("program/sdtm/ut_visits.R", chdir = FALSE)

raw <- readRDS("data/raw/ae.rds")

key_link <- raw |>
  distinct(subjectkey, studysubjectid) |>
  mutate(USUBJID = make_usubjid(studysubjectid))

ae_items <- c("AETERM", "AESEV", "AESER", "AEACN", "AEREL", "AEOUT",
              "AESCONG", "AESDISAB", "AESDTH", "AESHOSP", "AESLIFE",
              "AESIMIE", "AESINTV", "AESPID", "AESTDAT", "AEENDDAT",
              "AEONGO", "AE_MEDREL",
              "CONMED1", "CONMED3", "MED1", "MED2", "MED3")

wide <- raw |>
  filter(itemgroupname == "AE", itemname %in% ae_items) |>
  select(subjectkey, itemgrouprepeatkey,
         eventname, studyeventoid, startdate,
         itemname, value) |>
  pivot_wider(names_from = itemname, values_from = value,
              values_fn = ~ dplyr::first(.x))

acn_map <- c(
  `DOSE NOT CHANGED` = "DOSE NOT CHANGED",
  `DOSE REDUCED`     = "DOSE REDUCED",
  `DRUG WITHDRAWN`   = "DRUG WITHDRAWN",
  `NOT APPLICABLE`   = "NOT APPLICABLE",
  UNKNOWN            = "UNKNOWN"
)
out_map <- c(
  RECOVERED            = "RECOVERED/RESOLVED",
  RESOLVED             = "RECOVERED/RESOLVED",
  RECOVERING           = "RECOVERING/RESOLVING",
  `NOT RECOVERED`      = "NOT RECOVERED/NOT RESOLVED",
  FATAL                = "FATAL",
  UNKNOWN              = "UNKNOWN"
)

ae <- wide |>
  filter(!is.na(AETERM) & nzchar(AETERM)) |>
  left_join(key_link |> select(subjectkey, USUBJID), by = "subjectkey") |>
  mutate(
    STUDYID  = "CART-T-PILOT",
    DOMAIN   = "AE",
    AETERM   = AETERM,
    AEMODIFY = NA_character_,
    AEDECOD  = NA_character_,
    AEBODSYS = NA_character_,
    AESEV    = toupper(AESEV),
    AESER    = toupper(AESER),
    AEACN    = unname(acn_map[toupper(AEACN)]),
    AEREL    = toupper(AEREL),
    AERELNST = AE_MEDREL,
    AEOUT    = unname(out_map[toupper(AEOUT)]),
    AESCONG  = toupper(AESCONG),
    AESDISAB = toupper(AESDISAB),
    AESDTH   = toupper(AESDTH),
    AESHOSP  = toupper(AESHOSP),
    AESLIFE  = toupper(AESLIFE),
    AESMIE   = toupper(AESIMIE),
    AESINTV  = toupper(AESINTV),
    AECONTRT = ifelse(
      if_any(any_of(c("CONMED1","CONMED3","MED1","MED2","MED3")),
             ~ !is.na(.x) & nzchar(.x)),
      "Y", "N"),
    AESPID   = AESPID,
    AESTDTC  = normalize_iso_date(AESTDAT),
    AEENDTC  = normalize_iso_date(
                 ifelse(!is.na(AEONGO) & toupper(AEONGO) == "Y", NA_character_, AEENDDAT)),
    AEENRF   = ifelse(!is.na(AEONGO) & toupper(AEONGO) == "Y", "ONGOING", NA_character_),
    AESTDY   = NA_integer_,
    AEENDY   = NA_integer_,
    VISITNUM = derive_visitnum(studyeventoid),
    VISIT    = eventname
  ) |>
  arrange(USUBJID, AESTDTC, AETERM) |>
  mutate(AESEQ = row_number(), .by = USUBJID) |>
  select(STUDYID, DOMAIN, USUBJID, AESEQ, AESPID,
         AETERM, AEMODIFY, AEDECOD, AEBODSYS,
         AESEV, AESER, AEACN, AEREL, AERELNST, AEOUT,
         AESCONG, AESDISAB, AESDTH, AESHOSP, AESLIFE, AESMIE, AESINTV,
         AECONTRT, AESTDTC, AEENDTC, AEENRF, AESTDY, AEENDY,
         VISITNUM, VISIT)

saveRDS(ae, "data/sdtm/ae.rds")
cat(sprintf("AE written: %d rows x %d cols\n", nrow(ae), ncol(ae)))
