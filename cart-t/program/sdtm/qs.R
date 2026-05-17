## --------------------------------------------------------------------
## QS — Questionnaires (RAND SF-12)
## Spec:   spec/sdtm/qs.yaml
## Inputs: data/raw/qs_sf12.rds
## Output: data/sdtm/qs.rds
## --------------------------------------------------------------------

library(dplyr)
library(tidyr)

source("program/sdtm/ut_visits.R", chdir = FALSE)

raw <- readRDS("data/raw/qs_sf12.rds")

key_link <- raw |>
  distinct(subjectkey, studysubjectid) |>
  mutate(USUBJID = make_usubjid(studysubjectid))

raw_items <- tibble::tribble(
  ~itemname, ~QSTESTCD,  ~QSTEST,                                        ~QSSCAT,
  "Q1",      "SF12Q01",  "SF-12 Q01 - General Health",                   "ITEM",
  "Q2",      "SF12Q02",  "SF-12 Q02 - Moderate Activities Limit",        "ITEM",
  "Q3",      "SF12Q03",  "SF-12 Q03 - Climbing Stairs Limit",            "ITEM",
  "Q4",      "SF12Q04",  "SF-12 Q04 - Accomplished Less - Physical",     "ITEM",
  "Q5",      "SF12Q05",  "SF-12 Q05 - Limited Kind of Work - Physical",  "ITEM",
  "Q6",      "SF12Q06",  "SF-12 Q06 - Accomplished Less - Emotional",    "ITEM",
  "Q7",      "SF12Q07",  "SF-12 Q07 - Less Carefully - Emotional",       "ITEM",
  "Q8",      "SF12Q08",  "SF-12 Q08 - Pain Interfered with Work",        "ITEM",
  "Q9",      "SF12Q09",  "SF-12 Q09 - Felt Calm and Peaceful",           "ITEM",
  "Q10",     "SF12Q10",  "SF-12 Q10 - Had a Lot of Energy",              "ITEM",
  "Q11",     "SF12Q11",  "SF-12 Q11 - Felt Downhearted and Blue",        "ITEM",
  "Q12",     "SF12Q12",  "SF-12 Q12 - Social Activities Limit",          "ITEM"
)

subscale_items <- tibble::tribble(
  ~itemname, ~QSTESTCD,  ~QSTEST,                            ~QSSCAT,
  "PF",      "SF12PF",   "SF-12 Physical Functioning",       "SUBSCALE",
  "RP",      "SF12RP",   "SF-12 Role Physical",              "SUBSCALE",
  "BP",      "SF12BP",   "SF-12 Bodily Pain",                "SUBSCALE",
  "GH",      "SF12GH",   "SF-12 General Health",             "SUBSCALE",
  "VT",      "SF12VT",   "SF-12 Vitality",                   "SUBSCALE",
  "SF",      "SF12SF",   "SF-12 Social Functioning",         "SUBSCALE",
  "RE",      "SF12RE",   "SF-12 Role Emotional",             "SUBSCALE",
  "ME",      "SF12ME",   "SF-12 Mental Health",              "SUBSCALE"
)

test_map <- bind_rows(raw_items, subscale_items)

qs <- raw |>
  filter(itemname %in% test_map$itemname) |>
  select(subjectkey, eventname, studyeventoid, startdate,
         itemgroupname, itemname, value) |>
  left_join(test_map, by = "itemname") |>
  left_join(key_link |> select(subjectkey, USUBJID), by = "subjectkey") |>
  filter(!is.na(value) & nzchar(value)) |>
  mutate(
    STUDYID  = "CART-T-PILOT",
    DOMAIN   = "QS",
    QSCAT    = "SF-12",
    QSORRES  = as.character(value),
    QSORRESU = ifelse(QSSCAT == "SUBSCALE", "SCORE", NA_character_),
    QSSTRESN = suppressWarnings(as.numeric(QSORRES)),
    QSSTRESC = ifelse(!is.na(QSSTRESN), as.character(QSSTRESN), QSORRES),
    QSSTRESU = QSORRESU,
    VISITNUM = derive_visitnum(studyeventoid),
    VISIT    = eventname,
    QSDTC    = startdate,
    QSDY     = NA_integer_
  ) |>
  arrange(USUBJID, VISITNUM, QSSCAT, QSTESTCD) |>
  ## QSBLFL: flag the earliest SF-12 administration per (USUBJID, QSTESTCD).
  ## In this pilot the SF-12 form is administered once, so every record qualifies.
  group_by(USUBJID, QSTESTCD) |>
  mutate(QSBLFL = ifelse(QSDTC == min(QSDTC, na.rm = TRUE), "Y", NA_character_)) |>
  ungroup() |>
  mutate(QSSEQ = row_number(), .by = USUBJID) |>
  select(STUDYID, DOMAIN, USUBJID, QSSEQ,
         QSTESTCD, QSTEST, QSCAT, QSSCAT,
         QSORRES, QSORRESU, QSSTRESC, QSSTRESN, QSSTRESU,
         QSBLFL, VISITNUM, VISIT, QSDTC, QSDY)

saveRDS(qs, "data/sdtm/qs.rds")
cat(sprintf("QS written: %d rows x %d cols\n", nrow(qs), ncol(qs)))
