# Name: ADEG — ECG Analysis Dataset
# Input: adsl, eg
library(admiral)
library(dplyr)
library(lubridate)
library(stringr)

source("00_setup.R")
eg   <- convert_blanks_to_na(read_sdtm("eg"))
adsl <- read_adam("adsl")

param_lookup <- tibble::tribble(
  ~EGTESTCD, ~PARAMCD, ~PARAM,                    ~PARAMN,
  "EGHR",    "EGHR",   "Heart Rate (beats/min)",  1,
  "INTP",    "INTP",   "ECG Interpretation",      2
)

adsl_vars <- exprs(TRTSDT, TRTEDT, TRT01A, TRT01P)

adeg <- eg %>%
  derive_vars_merged(dataset_add = adsl, new_vars = adsl_vars,
                     by_vars = exprs(STUDYID, USUBJID)) %>%
  derive_vars_dt(new_vars_prefix = "A", dtc = EGDTC) %>%
  derive_vars_dy(reference_date = TRTSDT, source_vars = exprs(ADT)) %>%
  derive_vars_merged_lookup(dataset_add = param_lookup,
                            new_vars = exprs(PARAMCD, PARAM, PARAMN),
                            by_vars = exprs(EGTESTCD)) %>%
  mutate(
    AVAL    = EGSTRESN,                                   # numeric (EGHR); NA for INTP
    AVALC   = if_else(is.na(EGSTRESN), EGORRES, NA_character_),
    ATPT    = "",
    AVISIT  = VISIT,
    AVISITN = VISITNUM,
    TRTP    = TRT01P,
    TRTA    = TRT01A
  ) %>%
  # baseline for the numeric parameter
  restrict_derivation(
    derivation = derive_var_extreme_flag,
    args = params(by_vars = exprs(STUDYID, USUBJID, PARAMCD),
                  order = exprs(ADT, VISITNUM, EGSEQ),
                  new_var = ABLFL, mode = "last"),
    filter = !is.na(AVAL) & !is.na(TRTSDT) & ADT <= TRTSDT
  ) %>%
  derive_var_base(by_vars = exprs(STUDYID, USUBJID, PARAMCD),
                  source_var = AVAL, new_var = BASE) %>%
  restrict_derivation(derivation = derive_var_chg, filter = !is.na(BASE)) %>%
  derive_var_obs_number(new_var = ASEQ, by_vars = exprs(STUDYID, USUBJID),
                        order = exprs(PARAMCD, ADT, VISITNUM), check_type = "error") %>%
  derive_vars_merged(dataset_add = select(adsl, !!!negate_vars(adsl_vars)),
                     by_vars = exprs(STUDYID, USUBJID))

save_adam(adeg, "adeg")
