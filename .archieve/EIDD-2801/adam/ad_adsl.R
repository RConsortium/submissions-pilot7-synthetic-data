# Name: ADSL — Subject-Level Analysis Dataset
# Input: dm, ex
#
# EIDD-2801 is a single-dose Phase 1 study with no DS/AE domains, so ADSL carries
# treatment (from EX) + population flags + demographic groupings only.
library(admiral)
library(dplyr)
library(lubridate)
library(stringr)

source("00_setup.R")
dm <- convert_blanks_to_na(read_sdtm("dm"))
ex <- convert_blanks_to_na(read_sdtm("ex"))

# ---- user functions --------------------------------------------------------
format_agegr1 <- function(x) case_when(
  x < 18 ~ "<18", between(x, 18, 64) ~ "18-64", x > 64 ~ ">64", TRUE ~ "Missing")
format_racegr1 <- function(x) case_when(
  x == "WHITE" ~ "White", !is.na(x) ~ "Non-white", TRUE ~ "Missing")
format_region1 <- function(x) case_when(
  x %in% c("GBR", "IRL", "FRA", "DEU") ~ "Europe",
  x %in% c("USA", "CAN") ~ "North America",
  !is.na(x) ~ "Rest of World", TRUE ~ "Missing")

# ---- derivations -----------------------------------------------------------
# impute exposure start/end times (start=first, end=last); date not imputed
ex_ext <- ex %>%
  derive_vars_dtm(dtc = EXSTDTC, new_vars_prefix = "EXST") %>%
  derive_vars_dtm(dtc = EXENDTC, new_vars_prefix = "EXEN", time_imputation = "last")

adsl <- dm %>%
  mutate(TRT01P = ARM, TRT01A = ACTARM) %>%
  # first treatment datetime
  derive_vars_merged(
    dataset_add = ex_ext,
    filter_add = EXDOSE > 0 & !is.na(EXSTDTM),
    new_vars = exprs(TRTSDTM = EXSTDTM, TRTSTMF = EXSTTMF),
    order = exprs(EXSTDTM, EXSEQ), mode = "first",
    by_vars = exprs(STUDYID, USUBJID)
  ) %>%
  # last treatment datetime
  derive_vars_merged(
    dataset_add = ex_ext,
    filter_add = EXDOSE > 0 & !is.na(EXENDTM),
    new_vars = exprs(TRTEDTM = EXENDTM, TRTETMF = EXENTMF),
    order = exprs(EXENDTM, EXSEQ), mode = "last",
    by_vars = exprs(STUDYID, USUBJID)
  ) %>%
  derive_vars_dtm_to_dt(source_vars = exprs(TRTSDTM, TRTEDTM)) %>%
  derive_var_trtdurd() %>%
  # safety population = received study drug
  derive_var_merged_exist_flag(
    dataset_add = ex, by_vars = exprs(STUDYID, USUBJID),
    new_var = SAFFL, false_value = "N", missing_value = "N",
    condition = EXDOSE > 0
  ) %>%
  mutate(
    ITTFL   = SAFFL,
    AGEGR1  = format_agegr1(AGE),
    RACEGR1 = format_racegr1(RACE),
    REGION1 = format_region1(COUNTRY),
    DOMAIN  = NULL
  )

save_adam(adsl, "adsl")
