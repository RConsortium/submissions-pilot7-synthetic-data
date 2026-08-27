## --------------------------------------------------------------------
## QS — Questionnaires (RAND SF-12)
## Spec:   spec/sdtm/qs.yaml
## Inputs: data/raw/qs_sf12.rds, data/sdtm/dm.rds
## Output: data/sdtm/qs.rds
##
## P21 fixes applied (issue #21):
##   SD0017 (439) – Invalid value for QSTEST: align QSTESTCD/QSTEST to CDISC
##                  SF-12 v1 canonical pairs (QSCAT="SF12", QSTEST ≤ 40 chars,
##                  no "SF-12 Qnn -" prefix). Items: SF1201..SF1212.
##                  Subscales: SF12PF/RP/BP/GH/VT/SF/RE/MH (note MH not ME).
##   CT2002 (1)   – QSCAT: "SF-12" → "SF12" (CDISC controlled value, no dash).
##   CT2002 (1)   – QSORRESU = "SCORE" → NA. SF-12 subscale scores are unitless.
##   CT2002 (1)   – QSSTRESU = "SCORE" → NA. Same.
##   SD1077 (1)   – Regulatory Expected variable EPOCH not found: derive from
##                  QSDTC vs DM.RFSTDTC/RFENDTC, same pattern as CE/DS.
##
## Out of scope (deferred follow-up): recomputing the 8 SF-12 subscale scores
## from items Q1..Q12 per the published SF-12v1/v2 algorithm. QSSTRESN /
## QSSTRESC are still copied directly from the raw "c" item-group values.
## --------------------------------------------------------------------

library(dplyr)
library(tidyr)

source("program/sdtm/ut_visits.R", chdir = FALSE)

raw <- readRDS("data/raw/qs_sf12.rds")
dm  <- readRDS("data/sdtm/dm.rds")

key_link <- raw |>
  distinct(subjectkey, studysubjectid) |>
  mutate(USUBJID = make_usubjid(studysubjectid))

## ── CDISC SF-12 v1 canonical QSTESTCD / QSTEST mappings ─────────────────────
## QSCAT = "SF12" (no dash). QSTEST values are the official CDISC short
## labels — all ≤ 40 chars, no "SF-12 Qnn -" prefix.
## Subscale codes follow CDISC convention (Mental Health = SF12MH, NOT SF12ME).

raw_items <- tibble::tribble(
  ~itemname, ~QSTESTCD, ~QSTEST,                              ~QSSCAT,
  "Q1",      "SF1201",  "General Health",                     "ITEM",
  "Q2",      "SF1202",  "Moderate Activities",                "ITEM",
  "Q3",      "SF1203",  "Climb Several Flights",              "ITEM",
  "Q4",      "SF1204",  "Accomplished Less - Physical",       "ITEM",
  "Q5",      "SF1205",  "Limited in Kind - Physical",         "ITEM",
  "Q6",      "SF1206",  "Accomplished Less - Emotional",      "ITEM",
  "Q7",      "SF1207",  "Less Careful - Emotional",           "ITEM",
  "Q8",      "SF1208",  "Pain Interfered",                    "ITEM",
  "Q9",      "SF1209",  "Calm and Peaceful",                  "ITEM",
  "Q10",     "SF1210",  "Energy",                             "ITEM",
  "Q11",     "SF1211",  "Felt Downhearted",                   "ITEM",
  "Q12",     "SF1212",  "Social Interference",                "ITEM"
)

subscale_items <- tibble::tribble(
  ~itemname, ~QSTESTCD, ~QSTEST,                            ~QSSCAT,
  "PF",      "SF12PF",  "Physical Functioning Score",       "SUBSCALE",
  "RP",      "SF12RP",  "Role Physical Score",              "SUBSCALE",
  "BP",      "SF12BP",  "Bodily Pain Score",                "SUBSCALE",
  "GH",      "SF12GH",  "General Health Score",             "SUBSCALE",
  "VT",      "SF12VT",  "Vitality Score",                   "SUBSCALE",
  "SF",      "SF12SF",  "Social Functioning Score",         "SUBSCALE",
  "RE",      "SF12RE",  "Role Emotional Score",             "SUBSCALE",
  "ME",      "SF12MH",  "Mental Health Score",              "SUBSCALE"
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
    ## CT2002 fix: QSCAT must be the CDISC controlled value "SF12" (no dash).
    QSCAT    = "SF12",
    QSORRES  = as.character(value),
    ## CT2002 fix: SF-12 subscale scores are unitless (0-100 raw or norm-based).
    ## Leave QSORRESU/QSSTRESU NA — "SCORE" is not in the CDISC Unit codelist.
    QSORRESU = NA_character_,
    QSSTRESN = suppressWarnings(as.numeric(QSORRES)),
    QSSTRESC = ifelse(!is.na(QSSTRESN), as.character(QSSTRESN), QSORRES),
    QSSTRESU = NA_character_,
    VISITNUM = derive_visitnum(studyeventoid),
    VISIT    = eventname,
    ## startdate is mixed ISO-date and ISO-datetime; truncate to date portion
    ## before normalizing (matches ds.R / ie.R / lb.R pattern).
    QSDTC    = normalize_iso_date(substr(startdate, 1, 10)),
    QSDY     = NA_integer_
  ) |>
  arrange(USUBJID, VISITNUM, QSSCAT, QSTESTCD) |>
  ## QSBLFL: flag the earliest SF-12 administration per (USUBJID, QSTESTCD).
  ## In this pilot the SF-12 form is administered once, so every record qualifies.
  group_by(USUBJID, QSTESTCD) |>
  mutate(QSBLFL = ifelse(QSDTC == min(QSDTC, na.rm = TRUE), "Y", NA_character_)) |>
  ungroup()

## ── SD1077 fix: derive EPOCH from DM reference dates (CE/DS pattern) ────────

qs <- qs |>
  left_join(dm |> select(USUBJID, RFSTDTC, RFENDTC), by = "USUBJID") |>
  mutate(
    EPOCH = dplyr::case_when(
      is.na(QSDTC) | is.na(RFSTDTC)            ~ NA_character_,
      QSDTC < RFSTDTC                          ~ "SCREENING",
      !is.na(RFENDTC) & QSDTC > RFENDTC        ~ "FOLLOW-UP",
      TRUE                                     ~ "TREATMENT"
    ),
    ## QSDY derivation: study day relative to DM.RFSTDTC; skip day 0.
    QSDY = dplyr::if_else(
      !is.na(QSDTC) & !is.na(RFSTDTC),
      as.integer(as.Date(QSDTC) - as.Date(RFSTDTC)) +
        ifelse(QSDTC >= RFSTDTC, 1L, 0L),
      NA_integer_
    )
  ) |>
  mutate(QSSEQ = row_number(), .by = USUBJID) |>
  select(STUDYID, DOMAIN, USUBJID, QSSEQ,
         QSTESTCD, QSTEST, QSCAT, QSSCAT,
         QSORRES, QSORRESU, QSSTRESC, QSSTRESN, QSSTRESU,
         QSBLFL, EPOCH, VISITNUM, VISIT, QSDTC, QSDY)

saveRDS(qs, "data/sdtm/qs.rds")

cat(sprintf("QS written: %d rows x %d cols\n", nrow(qs), ncol(qs)))
cat(sprintf("Unique subjects: %d\n", length(unique(qs$USUBJID))))
cat(sprintf("QSDTC non-null: %d / %d\n", sum(!is.na(qs$QSDTC) & nzchar(qs$QSDTC)), nrow(qs)))
cat(sprintf("EPOCH non-null: %d / %d\n", sum(!is.na(qs$EPOCH)), nrow(qs)))
cat(sprintf("QSDY  non-null: %d / %d\n", sum(!is.na(qs$QSDY)),  nrow(qs)))
cat(sprintf("Max QSTEST length: %d (limit 40)\n", max(nchar(qs$QSTEST), na.rm = TRUE)))
cat("\nQSCAT distribution:\n"); print(table(qs$QSCAT, useNA = "ifany"))
cat("\nQSSCAT distribution:\n"); print(table(qs$QSSCAT, useNA = "ifany"))
cat("\nEPOCH distribution:\n"); print(table(qs$EPOCH, useNA = "ifany"))
cat("\nQSTESTCD distribution:\n"); print(table(qs$QSTESTCD, useNA = "ifany"))
