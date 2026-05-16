## --------------------------------------------------------------------
## LB — Laboratory Test Results
## Spec:   spec/sdtm/lb.yaml
## Inputs: data/raw/lb_bl.rds (baseline), data/raw/lb.rds (follow-up)
## Output: data/sdtm/lb.rds
## --------------------------------------------------------------------

library(dplyr)
library(tidyr)

source("program/sdtm/ut_visits.R", chdir = FALSE)

bl  <- readRDS("data/raw/lb_bl.rds")
fup <- readRDS("data/raw/lb.rds")

key_link <- bind_rows(bl, fup) |>
  distinct(subjectkey, studysubjectid) |>
  mutate(USUBJID = make_usubjid(studysubjectid))

test_map <- tibble::tribble(
  ~itemgroupname, ~itemname,  ~LBTESTCD,  ~LBTEST,                         ~LBCAT,       ~LBORRESU,
  "CHEMPANEL",    "AMYLASE",  "AMYLASE",  "Amylase",                       "CHEMISTRY",  "U/L",
  "CHEMPANEL",    "BUN",      "BUN",      "Blood Urea Nitrogen",           "CHEMISTRY",  "mg/dL",
  "CHEMPANEL",    "CHLORIDE", "CL",       "Chloride",                      "CHEMISTRY",  "mmol/L",
  "CHEMPANEL",    "HOMOC",    "HCYS",     "Homocysteine",                  "CHEMISTRY",  "umol/L",
  "NEPH",         "CREAT",    "CREAT",    "Creatinine",                    "CHEMISTRY",  "mg/dL",
  "NEPH",         "CREATR",   "CREATSI",  "Creatinine (SI)",               "CHEMISTRY",  "umol/L",
  "NEPH",         "EGFR",     "EGFR",     "Estimated GFR",                 "CHEMISTRY",  "mL/min/1.73m2",
  "labs",         "CHOLES",   "CHOL",     "Cholesterol",                   "CHEMISTRY",  "mg/dL",
  "labs",         "TRIG",     "TRIG",     "Triglycerides",                 "CHEMISTRY",  "mg/dL",
  "labs",         "HEMA",     "HCT",      "Hematocrit",                    "HEMATOLOGY", "%",
  "labs",         "HEMO",     "HGB",      "Hemoglobin",                    "HEMATOLOGY", "g/dL",
  "labs",         "RBC",      "RBC",      "Erythrocytes (RBC)",            "HEMATOLOGY", "10^6/uL",
  "labs",         "WBC",      "WBC",      "Leukocytes (WBC)",              "HEMATOLOGY", "10^3/uL"
)

select_lab <- function(df, draw_date_item = NULL) {
  df |>
    filter(itemname %in% test_map$itemname) |>
    select(subjectkey, eventname, studyeventoid, startdate,
           itemgroupname, itemname, value, itemgrouprepeatkey)
}

lb_bl_long <- bl |>
  filter(itemname %in% test_map$itemname) |>
  select(subjectkey, eventname, studyeventoid, startdate,
         itemgroupname, itemname, value) |>
  mutate(LBBLFL = "Y")

lb_fup_long <- fup |>
  filter(itemname %in% test_map$itemname) |>
  select(subjectkey, eventname, studyeventoid, startdate,
         itemgroupname, itemname, value) |>
  mutate(LBBLFL = NA_character_)

# Per-form collection date
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

lb_all <- bind_rows(lb_bl_long, lb_fup_long) |>
  left_join(bl_dates,  by = c("subjectkey", "studyeventoid")) |>
  left_join(fup_dates, by = c("subjectkey", "studyeventoid")) |>
  left_join(test_map,  by = c("itemgroupname", "itemname")) |>
  left_join(key_link |> select(subjectkey, USUBJID), by = "subjectkey") |>
  filter(!is.na(value) & nzchar(value)) |>
  mutate(
    STUDYID  = "CART-T-PILOT",
    DOMAIN   = "LB",
    LBORRES  = as.character(value),
    LBSTRESN = suppressWarnings(as.numeric(LBORRES)),
    LBSTRESC = ifelse(!is.na(LBSTRESN), as.character(LBSTRESN), LBORRES),
    LBSTRESU = LBORRESU,
    LBNRIND  = NA_character_,
    VISITNUM = derive_visitnum(studyeventoid),
    VISIT    = eventname,
    LBDTC    = normalize_iso_date(dplyr::coalesce(BLDATE, FUPDATE, startdate)),
    LBDY     = NA_integer_
  ) |>
  arrange(USUBJID, LBDTC, LBTESTCD) |>
  mutate(LBSEQ = row_number(), .by = USUBJID) |>
  select(STUDYID, DOMAIN, USUBJID, LBSEQ,
         LBTESTCD, LBTEST, LBCAT, LBORRES, LBORRESU,
         LBSTRESC, LBSTRESN, LBSTRESU, LBNRIND, LBBLFL,
         VISITNUM, VISIT, LBDTC, LBDY)

saveRDS(lb_all, "data/sdtm/lb.rds")
cat(sprintf("LB written: %d rows x %d cols\n", nrow(lb_all), ncol(lb_all)))
