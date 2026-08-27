## --------------------------------------------------------------------
## LB — Laboratory Test Results
## Spec:   spec/sdtm/lb.yaml
## Inputs: data/raw/lb_bl.rds  (baseline labs and imaging)
##         data/raw/lb.rds     (follow-up "Lab Results")
##         data/sdtm/dm.rds    (for RFSTDTC -> LBDY)
## Output: data/sdtm/lb.rds
## --------------------------------------------------------------------

library(dplyr)
library(tidyr)

source("program/sdtm/ut_visits.R", chdir = FALSE)

bl  <- readRDS("data/raw/lb_bl.rds")
fup <- readRDS("data/raw/lb.rds")
dm  <- readRDS("data/sdtm/dm.rds")

key_link <- bind_rows(bl, fup) |>
  distinct(subjectkey, studysubjectid) |>
  mutate(USUBJID = make_usubjid(studysubjectid))

## CDISC-CT-aligned test_map.
## LBTESTCD must be in 'Laboratory Test Code' (C65047).
## LBTEST   must be in 'Laboratory Test Name' (C67154) AND must pair
## with the matching LBTESTCD (same NCI concept).
## LBORRESU must be in 'Unit' (C71620) — canonical Submission Value.
test_map <- tibble::tribble(
  ~itemgroupname, ~itemname,  ~LBTESTCD,  ~LBTEST,                         ~LBCAT,        ~LBORRESU,
  "CHEMPANEL",    "AMYLASE",  "AMYLASE",  "Amylase",                       "CHEMISTRY",   "U/L",
  "CHEMPANEL",    "BUN",      "UREAN",    "Urea Nitrogen",                 "CHEMISTRY",   "mg/dL",
  "CHEMPANEL",    "CHLORIDE", "CL",       "Chloride",                      "CHEMISTRY",   "mmol/L",
  "CHEMPANEL",    "HOMOC",    "HOMOCY",   "Homocysteine",                  "CHEMISTRY",   "umol/L",
  "NEPH",         "CREAT",    "CREAT",    "Creatinine",                    "CHEMISTRY",   "mg/dL",
  ## NEPH.CREATR and CHEMPANEL.HOMOCRANGE are CRF help-text items that
  ## carry the literal string "(Normal range, ...)" — not lab results.
  ## They are intentionally NOT in test_map and are filtered out below.
  "NEPH",         "EGFR",     "GFR",      "Glomerular Filtration Rate",    "CHEMISTRY",   "mL/min/1.73 m2",
  "labs",         "CHOLES",   "CHOL",     "Cholesterol",                   "CHEMISTRY",   "mg/dL",
  "labs",         "TRIG",     "TRIG",     "Triglycerides",                 "CHEMISTRY",   "mg/dL",
  "labs",         "HEMA",     "HCT",      "Hematocrit",                    "HEMATOLOGY",  "%",
  "labs",         "HEMO",     "HGB",      "Hemoglobin",                    "HEMATOLOGY",  "g/dL",
  "labs",         "RBC",      "RBC",      "Erythrocytes",                  "HEMATOLOGY",  "10^12/L",
  "labs",         "WBC",      "WBC",      "Leukocytes",                    "HEMATOLOGY",  "10^9/L"
)

## ----------------------------------------------------------------
## Build long-form per-result tables
## ----------------------------------------------------------------

lb_bl_long <- bl |>
  filter(itemname %in% test_map$itemname,
         !is.na(value), nzchar(value)) |>
  select(subjectkey, eventname, studyeventoid, startdate,
         itemgroupname, itemname, itemgrouprepeatkey, value) |>
  mutate(LBBLFL = "Y", .src = "BL")

lb_fup_long <- fup |>
  filter(itemname %in% test_map$itemname,
         !is.na(value), nzchar(value)) |>
  select(subjectkey, eventname, studyeventoid, startdate,
         itemgroupname, itemname, itemgrouprepeatkey, value) |>
  mutate(LBBLFL = NA_character_, .src = "FUP")

## ----------------------------------------------------------------
## Per-event collection dates (item-level when present)
## ----------------------------------------------------------------

bl_dates <- bl |>
  filter(itemname %in% c("date_of_blood_draw", "DRAWDATE", "SCANDATE")) |>
  group_by(subjectkey, studyeventoid) |>
  summarise(BLDATE = dplyr::first(value[!is.na(value) & nzchar(value)]),
            .groups = "drop")

fup_dates <- fup |>
  filter(itemname %in% c("LABDATE")) |>
  group_by(subjectkey, studyeventoid) |>
  summarise(FUPDATE = dplyr::first(value[!is.na(value) & nzchar(value)]),
            .groups = "drop")

## ----------------------------------------------------------------
## Combine + dedup
##
## SD1117 root cause: raw 'Lab Results' form re-emits the same
## (subjectkey, studyeventoid, itemgrouprepeatkey, itemname) up to
## six times — some with the same value, some with a corrected value
## (e.g. CNH-001 HEMA values 666 and 44 in the same event).
##
## Dedup rule: arrange by USUBJID, LBTESTCD, VISITNUM, LBDTC; within
## each group keep the LAST row, which (for ties on key) is the latest
## entry in the export — interpreted as the most recent data entry /
## correction.
## ----------------------------------------------------------------

dm_ref <- dm |> select(USUBJID, RFSTDTC)

lb_all <- bind_rows(lb_bl_long, lb_fup_long) |>
  left_join(bl_dates,  by = c("subjectkey", "studyeventoid")) |>
  left_join(fup_dates, by = c("subjectkey", "studyeventoid")) |>
  left_join(test_map,  by = c("itemgroupname", "itemname")) |>
  left_join(key_link |> select(subjectkey, USUBJID), by = "subjectkey") |>
  left_join(dm_ref, by = "USUBJID") |>
  mutate(
    STUDYID   = "CART-T-PILOT",
    DOMAIN    = "LB",
    LBORRES   = as.character(value),
    LBSTRESN  = suppressWarnings(as.numeric(LBORRES)),
    LBSTRESC  = ifelse(!is.na(LBSTRESN), as.character(LBSTRESN), LBORRES),
    LBSTRESU  = LBORRESU,
    LBORNRLO  = NA_character_,   # reference ranges not captured in raw
    LBORNRHI  = NA_character_,
    LBSTNRLO  = NA_character_,
    LBSTNRHI  = NA_character_,
    LBNRIND   = NA_character_,
    LBLOBXFL  = NA_character_,   # no exposure data → cannot derive
    VISITNUM  = derive_visitnum(studyeventoid),
    VISIT     = eventname,
    LBDTC_raw = dplyr::coalesce(BLDATE, FUPDATE, startdate),
    LBDTC     = normalize_iso_date(LBDTC_raw)
  ) |>
  # Stable sort BEFORE dedup so "last wins" is deterministic.
  arrange(USUBJID, LBTESTCD, VISITNUM, LBDTC, itemgrouprepeatkey) |>
  # Dedup: one record per (USUBJID, LBTESTCD, VISITNUM, LBDTC) — the
  # natural keys for LB plus VISITNUM to keep baseline distinct from
  # follow-up when dates collide. Keep the last (most recent entry).
  group_by(USUBJID, LBTESTCD, VISITNUM, LBDTC) |>
  slice_tail(n = 1) |>
  ungroup() |>
  # Derive LBDY now that LBDTC is final and ISO. Only full yyyy-mm-dd
  # strings can become a study day; year-only LBDTC ("2026") yields NA.
  mutate(
    .lbdtc_iso = ifelse(grepl("^[0-9]{4}-[0-9]{2}-[0-9]{2}$", LBDTC),
                       LBDTC, NA_character_),
    .rfstd_iso = ifelse(grepl("^[0-9]{4}-[0-9]{2}-[0-9]{2}$", RFSTDTC),
                       RFSTDTC, NA_character_),
    .lbdtc_d  = suppressWarnings(as.Date(.lbdtc_iso)),
    .rfstd_d  = suppressWarnings(as.Date(.rfstd_iso)),
    LBDY = dplyr::if_else(
      !is.na(.lbdtc_d) & !is.na(.rfstd_d),
      as.integer(.lbdtc_d - .rfstd_d) +
        as.integer(ifelse(.lbdtc_d >= .rfstd_d, 1L, 0L)),
      NA_integer_
    )
  ) |>
  arrange(USUBJID, LBDTC, LBTESTCD) |>
  mutate(LBSEQ = row_number(), .by = USUBJID) |>
  select(STUDYID, DOMAIN, USUBJID, LBSEQ,
         LBTESTCD, LBTEST, LBCAT,
         LBORRES, LBORRESU, LBORNRLO, LBORNRHI,
         LBSTRESC, LBSTRESN, LBSTRESU, LBSTNRLO, LBSTNRHI,
         LBNRIND, LBBLFL, LBLOBXFL,
         VISITNUM, VISIT, LBDTC, LBDY)

saveRDS(lb_all, "data/sdtm/lb.rds")

n_dup <- nrow(lb_all) -
  nrow(distinct(lb_all, USUBJID, LBTESTCD, VISITNUM, LBDTC))

cat(sprintf("LB written: %d rows x %d cols\n", nrow(lb_all), ncol(lb_all)))
cat(sprintf("Unique subjects: %d\n", length(unique(lb_all$USUBJID))))
cat(sprintf("Residual dups on (USUBJID, LBTESTCD, VISITNUM, LBDTC): %d\n", n_dup))
cat(sprintf("LBDTC non-null: %d / %d\n",
            sum(!is.na(lb_all$LBDTC)), nrow(lb_all)))
cat(sprintf("LBDY  non-null: %d / %d\n",
            sum(!is.na(lb_all$LBDY)), nrow(lb_all)))
cat(sprintf("LBTESTCDs: %s\n",
            paste(sort(unique(lb_all$LBTESTCD)), collapse=", ")))
cat(sprintf("LBORRESUs: %s\n",
            paste(sort(unique(lb_all$LBORRESU)), collapse=", ")))
