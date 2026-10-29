# ============================================================================
# Program: advs.r
# Purpose: Create ADaM Vital Signs Analysis Dataset (ADVS)
# Description: Derives analysis variables for vital signs data including
#              change from baseline, analysis flags, and parameter mappings.
# Input: SDTM domains (VS), ADaM (ADSL)
# Output: advs.json
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
library(metacore) # Metadata handling
library(datasetjson) # Dataset JSON handling

# Import utility functions
source(file.path("code", "utils", "save_dataset_json.r"))

# ----------------------------------------------------------------------------
# LOAD METADATA
# ----------------------------------------------------------------------------

# Load define.xml metadata
metacore <- spec_to_metacore(
  file.path(path$adam_reference, "pilot6-specs.xlsx"),
  where_sep_sheet = FALSE,
  quiet = TRUE
)

# Get the specifications for the dataset we are currently building
advs_spec <- metacore %>%
  select_dataset("ADVS")

# Tibbles with codelists
atpt_codelist <- advs_spec$codelist %>%
  filter(code_id == "ADVS.ATPTN") %>%
  pull(codes) %>%
  pluck(1) %>%
  select(code, decode) %>%
  mutate(
    code = str_trim(code),
    code = as.integer((code))
  ) %>%
  rename(ATPTN = code, ATPT = decode)

avisit_codelist <- advs_spec$codelist %>%
  filter(code_id == "ADVS.AVISITN") %>%
  pull(codes) %>%
  pluck(1) %>%
  select(code, decode) %>%
  mutate(
    code = str_trim(code),
    code = as.integer((code))
  ) %>%
  rename(AVISITN = code, AVISIT = decode)

paramcd_codelist <- advs_spec$codelist %>%
  filter(code_id == "PARAMCD_ADVS") %>%
  pull(codes) %>%
  pluck(1) %>%
  select(code, decode) %>%
  rename(PARAMCD = code, PARAM = decode)

paramn_codelist <- advs_spec$codelist %>%
  filter(code_id == "PARAMN_ADVS") %>%
  pull(codes) %>%
  pluck(1) %>%
  select(code, decode) %>%
  mutate(
    code = str_trim(code),
    code = as.integer((code))
  ) %>%
  rename(PARAMN = code, PARAM = decode)

param_lookup <- paramcd_codelist %>%
  inner_join(paramn_codelist, by = "PARAM") %>%
  select(PARAMCD, PARAM, PARAMN) %>%
  mutate(VSTESTCD = PARAMCD)

# ----------------------------------------------------------------------------
# LOAD DATASETS
# ----------------------------------------------------------------------------

vs <- read_dataset_json(file.path(path$sdtm, "vs.json"), decimals_as_floats = TRUE)

adsl <- read_dataset_json(file.path(path$adam, "adsl.json"), decimals_as_floats = TRUE)

# ----------------------------------------------------------------------------
# DERIVATIONS
# ----------------------------------------------------------------------------

## Merge ADSL variables
# Select ADSL variables to merge
adsl_vars <- exprs(
  SITEID, TRTSDT, TRTEDT, TRT01P, TRT01PN, TRT01A, TRT01AN,
  AGE, AGEGR1, AGEGR1N, RACE, RACEN, SEX, SAFFL
)

advs_adsl <- vs %>%
  derive_vars_merged(
    dataset_add = adsl,
    new_vars = adsl_vars,
    by_vars = exprs(STUDYID, USUBJID)
  ) %>%
  mutate(
    TRTP = TRT01P,
    TRTPN = TRT01PN,
    TRTA = TRT01A,
    TRTAN = TRT01AN
  )

## Derive Analysis Date (ADT) and Relative Day (ADY)
advs_dt <- advs_adsl %>%
  derive_vars_dt(
    new_vars_prefix = "A",
    dtc = VSDTC
  ) %>%
  derive_vars_dy(
    reference_date = TRTSDT,
    source_vars = exprs(ADT)
  )

## Derive Parameters (PARAMCD, PARAM, PARAMN)
advs_param <- advs_dt %>%
  inner_join(param_lookup, by = "VSTESTCD")

## Derive Analysis Value
advs_aval <- advs_param %>%
  mutate(AVAL = VSSTRESN)

## Derive Analysis Timepoints (ATPT, ATPTN)
advs_atpt <- advs_aval %>%
  mutate(ATPT = VSTPT) %>%
  left_join(atpt_codelist, by = "ATPT")

## Derive Analysis Visits (AVISIT, AVISITN)
# Lookup table for visits
advs_avisit <- advs_atpt %>%
  mutate(
    AVISIT = case_when(
      str_detect(VISIT, "SCREENING|UNSCH|AMBUL ECG|RETRIEVAL") ~ NA_character_,
      TRUE ~ str_to_title(VISIT)
    )
  ) %>%
  left_join(avisit_codelist, by = "AVISIT")

# Derive end of treatment visit
advs_eot <- advs_avisit %>%
  derive_extreme_records(
    dataset_add = advs_avisit,
    by_vars = exprs(STUDYID, USUBJID, PARAMCD, ATPT),
    order = exprs(ADT, AVISITN, ATPTN, AVAL),
    mode = "last",
    filter_add = (AVISITN > 2),
    set_values_to = exprs(
      AVISIT = "End of Treatment",
      AVISITN = 99
    )
  )

## Derive Baseline Variables (ABLFL, BASE, BASETYPE, CHG, PCHG)
advs_baseline <- advs_eot %>%
  mutate(
    ABLFL = VSBLFL,
    BASETYPE = VSTPT
  ) %>%
  derive_var_base(
    by_vars = exprs(STUDYID, USUBJID, PARAMCD, BASETYPE),
    source_var = AVAL,
    new_var = BASE,
    filter = ABLFL == "Y"
  ) %>%
  derive_var_chg() %>%
  derive_var_pchg()

## Derive Analysis Flags (ANL01FL)
advs_anl01fl <- advs_baseline %>%
  mutate(
    ANL01FL = case_when(
      !is.na(AVISIT) ~ "Y",
      TRUE ~ NA_character_
    )
  )

# Sort the data
sort_order <- advs_anl01fl %>%
  select(USUBJID, PARAMCD, ATPTN, VISITNUM, AVISIT, VSSEQ) %>%
  colnames()

advs_sorted <- advs_anl01fl %>%
  arrange(across(all_of(sort_order)))

# ----------------------------------------------------------------------------
# EXPORT
# ----------------------------------------------------------------------------

save_dataset_json(
  output_dir = path$adam,
  dataset = advs_sorted,
  ds_spec = advs_spec
)
