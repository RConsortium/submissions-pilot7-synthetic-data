# Name: ADVS — Vital Signs Analysis Dataset
# Input: adsl, vs   (CATH: SYSBP/DIABP/PULSE/TEMP/WEIGHT/HEIGHT/BMI)
library(admiral)
library(dplyr)
library(stringr)

source("00_setup.R")
vs   <- convert_blanks_to_na(read_sdtm("vs"))
adsl <- read_adam("adsl")

adsl_vars <- exprs(TRTSDT, TRTEDT, TRT01A, TRT01P)

param_lookup <- vs %>%
  distinct(VSTESTCD, VSTEST) %>%
  arrange(VSTESTCD) %>%
  transmute(VSTESTCD, PARAMCD = VSTESTCD, PARAM = VSTEST, PARAMN = row_number())

advs <- vs %>%
  derive_vars_merged(dataset_add = adsl, new_vars = adsl_vars,
                     by_vars = exprs(STUDYID, USUBJID)) %>%
  derive_vars_dt(new_vars_prefix = "A", dtc = VSDTC) %>%
  derive_vars_dy(reference_date = TRTSDT, source_vars = exprs(ADT)) %>%
  derive_vars_merged_lookup(dataset_add = param_lookup,
                            new_vars = exprs(PARAMCD, PARAM, PARAMN),
                            by_vars = exprs(VSTESTCD)) %>%
  mutate(AVAL = VSSTRESN, AVISIT = VISIT, AVISITN = VISITNUM,
         ABLFL = VSBLFL, TRTP = TRT01P, TRTA = TRT01A) %>%
  derive_var_base(by_vars = exprs(STUDYID, USUBJID, PARAMCD),
                  source_var = AVAL, new_var = BASE) %>%
  restrict_derivation(derivation = derive_var_chg, filter = !is.na(BASE)) %>%
  restrict_derivation(derivation = derive_var_pchg, filter = !is.na(BASE) & BASE != 0) %>%
  derive_var_obs_number(new_var = ASEQ, by_vars = exprs(STUDYID, USUBJID),
                        order = exprs(PARAMCD, ADT, VISITNUM, VSSEQ), check_type = "error") %>%
  derive_vars_merged(dataset_add = select(adsl, !!!negate_vars(adsl_vars)),
                     by_vars = exprs(STUDYID, USUBJID))

save_adam(advs, "advs")
