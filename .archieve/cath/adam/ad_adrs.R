# Name: ADRS — Disease Response Analysis Dataset (efficacy)
# Input: adsl, rs   (CATH: PASI — Psoriasis Area and Severity Index)
library(admiral)
library(dplyr)
library(stringr)

source("00_setup.R")
rs   <- convert_blanks_to_na(read_sdtm("rs"))
adsl <- read_adam("adsl")

adsl_vars <- exprs(TRTSDT, TRTEDT, TRT01A, TRT01P)

param_lookup <- rs %>%
  distinct(RSTESTCD, RSTEST, RSCAT) %>%
  arrange(RSTESTCD) %>%
  transmute(RSTESTCD, PARAMCD = RSTESTCD, PARAM = RSTEST, PARAMN = row_number())

adrs <- rs %>%
  derive_vars_merged(dataset_add = adsl, new_vars = adsl_vars,
                     by_vars = exprs(STUDYID, USUBJID)) %>%
  derive_vars_dt(new_vars_prefix = "A", dtc = RSDTC) %>%
  derive_vars_dy(reference_date = TRTSDT, source_vars = exprs(ADT)) %>%
  derive_vars_merged_lookup(dataset_add = param_lookup,
                            new_vars = exprs(PARAMCD, PARAM, PARAMN),
                            by_vars = exprs(RSTESTCD)) %>%
  mutate(PARCAT1 = RSCAT, AVAL = RSSTRESN,
         AVALC = if_else(is.na(RSSTRESN), RSSTRESC, NA_character_),
         AVISIT = VISIT, AVISITN = VISITNUM, ABLFL = RSBLFL,
         TRTP = TRT01P, TRTA = TRT01A) %>%
  derive_var_base(by_vars = exprs(STUDYID, USUBJID, PARAMCD),
                  source_var = AVAL, new_var = BASE) %>%
  restrict_derivation(derivation = derive_var_chg, filter = !is.na(BASE)) %>%
  restrict_derivation(derivation = derive_var_pchg, filter = !is.na(BASE) & BASE != 0) %>%
  derive_var_obs_number(new_var = ASEQ, by_vars = exprs(STUDYID, USUBJID),
                        order = exprs(PARAMCD, ADT, VISITNUM), check_type = "error") %>%
  derive_vars_merged(dataset_add = select(adsl, !!!negate_vars(adsl_vars)),
                     by_vars = exprs(STUDYID, USUBJID))

save_adam(adrs, "adrs")
