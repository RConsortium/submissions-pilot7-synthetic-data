# ============================================================================
# Program: adqscibc.r
# Purpose: Create ADaM CIBIC+ Analysis Dataset (ADQSCIBC)
# Description: Derives analysis variables for CIBIC+ Dataset.
# Input: SDTM domains (QS), ADaM (ADSL)
# Output: adqscibc.json
# ============================================================================

# ----------------------------------------------------------------------------
# SETUP AND LIBRARY LOADING
# ----------------------------------------------------------------------------

# Load required packages
library(admiral) # ADaM derivations
library(dplyr) # Data manipulation
library(lubridate) # Date handling
library(haven) # Reading/writing SAS datasets
library(stringr) # String manipulation
library(purrr) # Functional programming
library(tibble) # Creating tibbles
library(datasetjson) # Dataset JSON handling
library(metacore) # Metadata handling
library(metatools)

# Import utility functions
source(file.path("code", "utils", "save_dataset_json.r"))

# ----------------------------------------------------------------------------
# LOAD METADATA
# ----------------------------------------------------------------------------
## Load dataset specs -------------
# Very noisy function - remove suppress if you want to see warnings
metacore <- spec_to_metacore(
  file.path(path$adam_reference, "pilot6-specs.xlsx"),
  where_sep_sheet = FALSE,
  quiet = TRUE
)

# Get the specifications for the dataset we are currently building
adcibc_spec <- metacore %>%
  select_dataset("ADCIBC")

# ----------------------------------------------------------------------------
# LOAD DATASETS
# ----------------------------------------------------------------------------
# Define data to load
dat_to_load <- list(
  qs = file.path(path$sdtm, "qs.json"),
  adsl = file.path(path$adam, "adsl.json")
)

# Load datasets using map and convert blanks to NA
purrr::iwalk(dat_to_load, \(file_path, var_name) {
  raw_data <- read_dataset_json(file_path, decimals_as_floats = TRUE)
  assign(var_name, raw_data, envir = .GlobalEnv)
  message(paste("Assigned variable '", var_name, "' to .GlobalEnv"))
})

# ----------------------------------------------------------------------------
# DERIVATIONS
# ----------------------------------------------------------------------------

# filter QS domain for qstestcd = CIBIC
adcibc00 <- qs %>%
  filter(QSTESTCD == "CIBIC") %>%
  select(STUDYID, USUBJID, VISIT, VISITNUM, QSDTC, QSSTRESN, QSSEQ)

## ADSL information ----------------------------------------------
adsl_vars <- exprs(
  STUDYID,
  SITEID,
  SITEGR1,
  USUBJID,
  TRTSDT,
  TRTEDT,
  TRT01P,
  TRT01PN,
  AGE,
  AGEGR1,
  AGEGR1N,
  RACE,
  RACEN,
  SEX,
  ITTFL,
  EFFFL,
  COMP24FL
)

adcibc1 <- adcibc00 %>%
  derive_vars_merged(
    dataset_add = adsl,
    new_vars = adsl_vars,
    by = exprs(STUDYID, USUBJID)
  ) %>%
  rename(TRTP = TRT01P, TRTPN = TRT01PN)

# Derive dates -----------------------------------------------
# derive ADT and ADY
adcibc2 <- adcibc1 %>%
  derive_vars_dt(new_vars_prefix = "A", dtc = QSDTC) %>%
  derive_vars_dy(reference_date = TRTSDT, source_vars = exprs(ADT))

## Derive AVISIT, AVAL, PARAM, AVISITN, PARAMN -------------------
adcibc3 <- adcibc2 %>%
  mutate(
    AVISIT = case_when(
      ADY <= 1 ~ "Baseline",
      ADY >= 2 & ADY <= 84 ~ "Week 8",
      ADY >= 85 & ADY <= 140 ~ "Week 16",
      ADY > 140 ~ "Week 24",
      TRUE ~ NA_character_
    ),
    AVAL = QSSTRESN,
    PARAM = "CIBIC Score"
  ) %>%
  create_var_from_codelist(adcibc_spec, AVISIT, AVISITN) %>%
  create_var_from_codelist(adcibc_spec, PARAM, PARAMN) %>%
  create_var_from_codelist(adcibc_spec, PARAM, PARAMCD)

## Derive AWRANGE, AWTARGET, AWTDIFF, AWLO, AWHI, AWU ----------------
aw_lookup <- tribble(
  ~AVISIT, ~AWRANGE, ~AWTARGET, ~AWLO, ~AWHI,
  "Baseline", "<=1", 1, NA_integer_, 1,
  "Week 8", "2-84", 56, 2, 84,
  "Week 16", "85-140", 112, 85, 140,
  "Week 24", ">140", 168, 141, NA_integer_
)

adcibc4 <- derive_vars_merged(
  adcibc3,
  dataset_add = aw_lookup,
  by_vars = exprs(AVISIT)
) %>%
  mutate(
    AWTDIFF = abs(AWTARGET - ADY),
    AWU = "DAYS"
  )

## Derive ANL01FL ----------------------------------------
adcibc5 <- adcibc4 %>%
  mutate(diff = ADY - AWTARGET) %>%
  restrict_derivation(
    derivation = derive_var_extreme_flag,
    args = params(
      by_vars = exprs(USUBJID, PARAMCD, AVISIT),
      order = exprs(AWTDIFF, diff),
      new_var = ANL01FL,
      mode = "first"
    ),
    filter = !is.na(AVISIT)
  )

## Derive DTYPE=LOCF -----------------------------------------
# A dataset with combinations of PARAMCD, AVISIT which are expected.
cibic_expected_obsv <- tibble::tribble(
  ~PARAMCD, ~AVISITN, ~AVISIT,
  "CIBICVAL", 8, "Week 8",
  "CIBICVAL", 16, "Week 16",
  "CIBICVAL", 24, "Week 24"
)

adcibc_locf <- adcibc5 %>%
  restrict_derivation(
    derivation = derive_locf_records,
    args = params(
      dataset_ref = cibic_expected_obsv,
      by_vars = exprs(
        STUDYID, SITEID, SITEGR1, USUBJID, TRTSDT, TRTEDT,
        TRTP, TRTPN, AGE, AGEGR1, AGEGR1N, RACE, RACEN, SEX,
        ITTFL, EFFFL, COMP24FL, PARAMCD
      ),
      order = exprs(AVISITN, AVISIT),
      keep_vars = exprs(VISIT, VISITNUM, ADY, ADT, PARAM, PARAMN, QSSEQ)
    ),
    filter = !is.na(ANL01FL)
  ) %>%
  # assign ANL01FL for new records
  mutate(ANL01FL = if_else(is.na(DTYPE), ANL01FL, "Y")) %>%
  # re-derive AWRANGE/AWTARGET/AWTDIFF/AWLO/AWHI/AWU
  select(-c("AWRANGE", "AWTARGET", "AWLO", "AWHI")) %>%
  derive_vars_merged(
    dataset_add = aw_lookup,
    by_vars = exprs(AVISIT)
  ) %>%
  mutate(
    AWTDIFF = abs(AWTARGET - ADY),
    AWU = "DAYS"
  ) %>%
  filter(!is.na(ADT))

adqscibc <- adcibc_locf %>%
  mutate_if(is.numeric, as.integer) %>%
  drop_unspec_vars(adcibc_spec) %>%
  check_ct_data(adcibc_spec, na_acceptable = TRUE) %>%
  order_cols(adcibc_spec) %>%
  sort_by_key(adcibc_spec) %>%
  set_variable_labels(adcibc_spec)

# ----------------------------------------------------------------------------
# EXPORT
# ----------------------------------------------------------------------------

save_dataset_json(
  output_dir = path$adam,
  dataset = adqscibc,
  ds_spec = adcibc_spec
)
