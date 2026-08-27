# Name: ADVS — Vital Signs Analysis Dataset
# Input: adsl, vs
library(admiral)
library(dplyr)
library(lubridate)
library(stringr)

source("00_setup.R")
vs   <- convert_blanks_to_na(read_sdtm("vs"))
adsl <- read_adam("adsl")

param_lookup <- tibble::tribble(
  ~VSTESTCD, ~PARAMCD, ~PARAM,                             ~PARAMN,
  "SYSBP",   "SYSBP",  "Systolic Blood Pressure (mmHg)",   1,
  "DIABP",   "DIABP",  "Diastolic Blood Pressure (mmHg)",  2,
  "PULSE",   "PULSE",  "Pulse Rate (beats/min)",           3,
  "RESP",    "RESP",   "Respiratory Rate (breaths/min)",   4,
  "TEMP",    "TEMP",   "Temperature (C)",                  5
)

adsl_vars <- exprs(TRTSDT, TRTEDT, TRT01A, TRT01P)

advs <- vs %>%
  derive_vars_merged(dataset_add = adsl, new_vars = adsl_vars,
                     by_vars = exprs(STUDYID, USUBJID)) %>%
  derive_vars_dt(new_vars_prefix = "A", dtc = VSDTC) %>%
  derive_vars_dy(reference_date = TRTSDT, source_vars = exprs(ADT)) %>%
  derive_vars_merged_lookup(dataset_add = param_lookup,
                            new_vars = exprs(PARAMCD, PARAM, PARAMN),
                            by_vars = exprs(VSTESTCD)) %>%
  mutate(
    AVAL    = VSSTRESN,
    ATPT    = VSTPT,
    AVISIT  = VISIT,
    AVISITN = VISITNUM,
    TRTP    = TRT01P,
    TRTA    = TRT01A
  ) %>%
  # baseline = last non-missing on/before first dose
  restrict_derivation(
    derivation = derive_var_extreme_flag,
    args = params(by_vars = exprs(STUDYID, USUBJID, PARAMCD),
                  order = exprs(ADT, VISITNUM, VSSEQ),
                  new_var = ABLFL, mode = "last"),
    filter = !is.na(AVAL) & !is.na(TRTSDT) & ADT <= TRTSDT
  ) %>%
  derive_var_base(by_vars = exprs(STUDYID, USUBJID, PARAMCD),
                  source_var = AVAL, new_var = BASE) %>%
  restrict_derivation(derivation = derive_var_chg, filter = !is.na(BASE)) %>%
  restrict_derivation(derivation = derive_var_pchg, filter = !is.na(BASE) & BASE != 0) %>%
  derive_var_obs_number(new_var = ASEQ, by_vars = exprs(STUDYID, USUBJID),
                        order = exprs(PARAMCD, ADT, VISITNUM), check_type = "error") %>%
  derive_vars_merged(dataset_add = select(adsl, !!!negate_vars(adsl_vars)),
                     by_vars = exprs(STUDYID, USUBJID))

save_adam(advs, "advs")
