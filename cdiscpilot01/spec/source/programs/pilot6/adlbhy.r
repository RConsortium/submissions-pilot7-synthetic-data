#************************************************************************
# Purpose:     Generate ADLBHY dataset
# Input:       LB (from datasetjson)
# Output:      adlbhy.json
#************************************************************************

# Note to Reviewer
# To rerun the code below, please refer ADRG appendix.
# After required package are installed, the path variable needs to be defined
# in the .Rprofile file

# Libraries ---------------------------------------------------------------

library(dplyr)
library(tidyr)
library(admiral)
library(metacore)
library(metatools)
library(stringr)
library(purrr)
library(datasetjson)

# Load Data ---------------------------------------------------------------

dat_to_load <- list(
  adlbc = file.path(path$adam, "adlbc.json")
)

datasets <- map(
  dat_to_load,
  ~ convert_blanks_to_na(read_dataset_json(.x, decimals_as_floats = TRUE))
)

list2env(datasets, envir = .GlobalEnv)

# Metadata ----------------------------------------------------------------
## Very noisy function - remove suppress if you want to see warnings
adlbhy_spec <- suppressWarnings(
  spec_to_metacore(
    file.path(path$adam_reference, "pilot6-specs.xlsx"),
    where_sep_sheet = FALSE,
    quiet = TRUE
  )
) %>%
  select_dataset("ADLBHY")

# Select Parameters from LB -----------------------------------------------
allowed_avisit <- c("Baseline", "Week 2", "Week 4", "Week 6", "Week 8", "Week 12", "Week 16", "Week 20", "Week 24")

adlbhy_pre <- adlbc %>%
  filter(
    PARAMCD %in% c("ALT", "AST", "BILI"),
    AVISIT %in% allowed_avisit
  ) %>%
  mutate(
    PARAMN = case_when(
      PARAMCD == "ALT" ~ 1,
      PARAMCD == "AST" ~ 2,
      PARAMCD == "BILI" ~ 3
    ),
    CRIT1 = case_when(
      PARAMCD %in% c("ALT", "AST", "BILI") ~ "R2A1HI > 1.5",
      TRUE ~ NA_character_
    ),
    CRIT1FL = case_when(
      PARAMCD %in% c("ALT", "AST", "BILI") & R2A1HI > 1.5 ~ "Y",
      !is.na(R2A1HI) ~ "N",
      TRUE ~ NA_character_
    ),
    CRIT1FN = case_when(
      PARAMCD %in% c("ALT", "AST", "BILI") & R2A1HI > 1.5 ~ 1,
      !is.na(R2A1HI) ~ 0,
      TRUE ~ NA_real_
    )
  )

# Hys Law -----------------------------------------------------------------
# BILIHY: Bilirubin > 1.5 times ULN
bilihy <- adlbhy_pre %>%
  filter(PARAMCD == "BILI") %>%
  mutate(
    PARAMCD = "BILIHY",
    PARAM = "Bilirubin 1.5 x ULN",
    PARAMN = 4,
    AVAL = if_else(R2A1HI > 1.5, 1, 0),
    PARAMTYP = "DERIVED",
    PARCAT1 = "HYLAW"
  )

# TRANSHY: ALT or AST > 1.5*ULN
transhy <- adlbhy_pre %>%
  filter(PARAMCD %in% c("ALT", "AST")) %>%
  mutate(has_elevated = if_else(R2A1HI > 1.5, 1, 0)) %>%
  arrange(STUDYID, USUBJID, VISIT, VISITNUM, ADT, desc(has_elevated)) %>%
  distinct(STUDYID, USUBJID, VISIT, VISITNUM, ADT, .keep_all = TRUE) %>%
  mutate(
    PARAMCD = "TRANSHY",
    PARAM = "Transaminase 1.5 x ULN",
    PARAMN = 5,
    AVAL = has_elevated,
    PARAMTYP = "DERIVED",
    PARCAT1 = "HYLAW"
  ) %>%
  select(-has_elevated)

# HYLAW: Both conditions met  (0/1 for all visits)
hylaw_visits <- adlbhy_pre %>%
  filter(PARAMCD %in% c("ALT", "AST", "BILI")) %>%
  group_by(STUDYID, USUBJID, VISIT, VISITNUM, ADT) %>%
  summarise(
    across(
      c(
        SUBJID, TRTP, TRTPN, TRTA, TRTAN, TRTSDT, TRTEDT,
        AGE, AGEGR1, AGEGR1N, RACE, RACEN, SEX,
        COMP24FL, DSRAEFL, SAFFL, AVISIT, AVISITN, ADY, ABLFL
      ),
      first
    ),
    has_bili = any(PARAMCD == "BILI" & R2A1HI > 1.5, na.rm = TRUE),
    has_trans = any(PARAMCD %in% c("ALT", "AST") & R2A1HI > 1.5, na.rm = TRUE),
    .groups = "drop"
  ) %>%
  mutate(
    PARAMCD = "HYLAW",
    PARAM = "Total Bili 1.5 x ULN and Transaminase 1.5 x ULN",
    PARAMN = 6,
    AVAL = if_else(has_bili & has_trans, 1, 0),
    PARCAT1 = "HYLAW",
    PARAMTYP = "DERIVED",
    CRIT1 = "R2A1HI > 1.5",
    CRIT1FL = if_else(has_bili & has_trans, "Y", "N"),
    CRIT1FN = if_else(has_bili & has_trans, 1, 0)
  ) %>%
  select(-has_bili, -has_trans)

# Derive baseline and shift for all derived parameters
derived_params <- bind_rows(bilihy, transhy, hylaw_visits) %>%
  group_by(USUBJID, PARAMCD) %>%
  mutate(
    BASE = if_else(ABLFL == "Y", AVAL, NA_real_),
    BASE = max(BASE, na.rm = TRUE)
  ) %>%
  ungroup() %>%
  mutate(
    BASE = if_else(is.infinite(BASE), NA_real_, BASE),
    # SHIFT1 derivation per define.xml specification:
    # - "High to Normal" if BASE=1 and AVAL=0
    # - "Normal to Normal" if BASE=0 and AVAL=0
    # - "Normal to High" if BASE=0 and AVAL=1
    # - Not specified (left blank) if BASE=1 and AVAL=1 (no "High to High" category exists)
    SHIFT1 = case_when(
      is.na(BASE) ~ NA_character_,
      BASE == 1 & AVAL == 0 ~ "High to Normal",
      BASE == 0 & AVAL == 0 ~ "Normal to Normal",
      BASE == 0 & AVAL == 1 ~ "Normal to High",
      BASE == 1 & AVAL == 1 ~ NA_character_ # Not specified in define.xml
    ),
    SHIFT1N = case_when(
      SHIFT1 == "High to Normal" ~ 0,
      SHIFT1 == "Normal to Normal" ~ 1,
      SHIFT1 == "Normal to High" ~ 2
    ),
    VISIT = NA_character_,
    VISITNUM = NA_real_,
    ADT = as.Date(NA),
    ADY = NA_real_,
    A1LO = NA_real_,
    A1HI = NA_real_,
    R2A1LO = NA_real_,
    R2A1HI = NA_real_,
    BR2A1LO = NA_real_,
    BR2A1HI = NA_real_,
    CRIT1 = NA_character_,
    CRIT1FL = NA_character_,
    CRIT1FN = NA_real_
  )

# Combine all
adlbhy <- bind_rows(adlbhy_pre, derived_params) %>%
  arrange(STUDYID, USUBJID, PARAMN, ADT) %>%
  convert_na_to_blanks()

# Output ------------------------------------------------------------------

adlbhy <- adlbhy %>%
  drop_unspec_vars(adlbhy_spec) %>%
  check_ct_data(adlbhy_spec, na_acceptable = TRUE) %>%
  order_cols(adlbhy_spec) %>%
  sort_by_key(adlbhy_spec) %>%
  set_variable_labels(adlbhy_spec) %>%
  save_dataset_json(
    output_dir = path$adam,
    dataset = adlbhy,
    ds_spec = adlbhy_spec
  )

# END ------------------------------------------------------------------
