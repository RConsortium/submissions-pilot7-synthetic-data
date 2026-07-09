# Name: ADLB — Laboratory Analysis Dataset
# Input: adsl, lb
#
# CATH LB spans CHEMISTRY / IMMUNOLOGY / GENE EXPRESSION and the study's primary
# biomarker, ANTIMICROBIAL PEPTIDE (cathelicidin) — all carried through PARCAT1.
library(admiral)
library(dplyr)
library(stringr)

source("00_setup.R")
lb   <- convert_blanks_to_na(read_sdtm("lb"))
adsl <- read_adam("adsl")

adsl_vars <- exprs(TRTSDT, TRTEDT, TRT01A, TRT01P)

param_lookup <- lb %>%
  distinct(LBTESTCD, LBTEST, LBCAT) %>%
  arrange(LBCAT, LBTESTCD) %>%
  transmute(LBTESTCD, PARAMCD = LBTESTCD, PARAM = LBTEST, PARAMN = row_number())

adlb <- lb %>%
  derive_vars_merged(dataset_add = adsl, new_vars = adsl_vars,
                     by_vars = exprs(STUDYID, USUBJID)) %>%
  derive_vars_dt(new_vars_prefix = "A", dtc = LBDTC) %>%
  derive_vars_dy(reference_date = TRTSDT, source_vars = exprs(ADT)) %>%
  derive_vars_merged_lookup(dataset_add = param_lookup,
                            new_vars = exprs(PARAMCD, PARAM, PARAMN),
                            by_vars = exprs(LBTESTCD)) %>%
  mutate(PARCAT1 = LBCAT, AVAL = LBSTRESN,
         AVALC = if_else(is.na(LBSTRESN), LBSTRESC, NA_character_),
         AVISIT = VISIT, AVISITN = VISITNUM, ABLFL = LBBLFL,
         TRTP = TRT01P, TRTA = TRT01A) %>%
  derive_var_base(by_vars = exprs(STUDYID, USUBJID, PARAMCD),
                  source_var = AVAL, new_var = BASE) %>%
  restrict_derivation(derivation = derive_var_chg, filter = !is.na(BASE)) %>%
  restrict_derivation(derivation = derive_var_pchg, filter = !is.na(BASE) & BASE != 0) %>%
  derive_var_obs_number(new_var = ASEQ, by_vars = exprs(STUDYID, USUBJID),
                        order = exprs(PARAMCD, ADT, VISITNUM, LBSEQ), check_type = "error") %>%
  derive_vars_merged(dataset_add = select(adsl, !!!negate_vars(adsl_vars)),
                     by_vars = exprs(STUDYID, USUBJID))

save_adam(adlb, "adlb")
