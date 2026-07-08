# Name: ADAE — Adverse Events Analysis Dataset (OCCDS)
# Input: adsl, ae   (CATH AE captures onset only — no AEENDTC)
library(admiral)
library(dplyr)
library(lubridate)
library(stringr)

source("00_setup.R")
ae   <- convert_blanks_to_na(read_sdtm("ae"))
adsl <- read_adam("adsl")

adsl_vars <- exprs(TRTSDT, TRTEDT, TRT01A, TRT01P, SAFFL)
sev_levels <- c("MILD", "MODERATE", "SEVERE", "LIFE-THREATENING")

adae <- ae %>%
  derive_vars_merged(dataset_add = adsl, new_vars = adsl_vars,
                     by_vars = exprs(STUDYID, USUBJID)) %>%
  derive_vars_dt(new_vars_prefix = "AST", dtc = AESTDTC) %>%
  derive_vars_dy(reference_date = TRTSDT, source_vars = exprs(ASTDT)) %>%
  mutate(
    TRTEMFL = if_else(!is.na(ASTDT) & !is.na(TRTSDT) & ASTDT >= TRTSDT, "Y", NA_character_),
    ASEV    = AESEV,
    ASEVN   = match(AESEV, sev_levels),
    AREL    = AEREL,
    TRTA    = TRT01A,
    TRTP    = TRT01P
  ) %>%
  restrict_derivation(
    derivation = derive_var_extreme_flag,
    args = params(by_vars = exprs(USUBJID), order = exprs(ASTDT, AESEQ),
                  new_var = AOCCFL, mode = "first"),
    filter = TRTEMFL == "Y"
  ) %>%
  restrict_derivation(
    derivation = derive_var_extreme_flag,
    args = params(by_vars = exprs(USUBJID, AEBODSYS), order = exprs(ASTDT, AESEQ),
                  new_var = AOCCSFL, mode = "first"),
    filter = TRTEMFL == "Y"
  ) %>%
  restrict_derivation(
    derivation = derive_var_extreme_flag,
    args = params(by_vars = exprs(USUBJID, AEBODSYS, AEDECOD), order = exprs(ASTDT, AESEQ),
                  new_var = AOCCPFL, mode = "first"),
    filter = TRTEMFL == "Y"
  )

save_adam(adae, "adae")
