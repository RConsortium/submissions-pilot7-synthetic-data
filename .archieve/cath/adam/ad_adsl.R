# Name: ADSL — Subject-Level Analysis Dataset
# Input: dm, ex, ds
#
# CATH (vitamin D3 vs placebo, 21-day skin study): treatment from EX,
# disposition from DS, population flags, demographic groupings.
library(admiral)
library(dplyr)
library(lubridate)
library(stringr)

source("00_setup.R")
dm <- convert_blanks_to_na(read_sdtm("dm"))
ex <- convert_blanks_to_na(read_sdtm("ex"))
ds <- convert_blanks_to_na(read_sdtm("ds"))

format_agegr1 <- function(x) case_when(
  x < 40 ~ "<40", between(x, 40, 64) ~ "40-64", x >= 65 ~ ">=65", TRUE ~ "Missing")
format_racegr1 <- function(x) case_when(
  x == "WHITE" ~ "White", !is.na(x) ~ "Non-white", TRUE ~ "Missing")
format_region1 <- function(x) case_when(
  x %in% c("USA", "CAN") ~ "North America",
  x %in% c("GBR", "DEU", "FRA", "ESP", "ITA", "IRL") ~ "Europe",
  !is.na(x) ~ "Rest of World", TRUE ~ "Missing")
format_eosstt <- function(x) case_when(
  x == "COMPLETED" ~ "COMPLETED", !is.na(x) ~ "DISCONTINUED", TRUE ~ "ONGOING")

ex_ext <- ex %>%
  derive_vars_dtm(dtc = EXSTDTC, new_vars_prefix = "EXST") %>%
  derive_vars_dtm(dtc = EXENDTC, new_vars_prefix = "EXEN", time_imputation = "last")

ds_ext <- derive_vars_dt(ds, dtc = DSSTDTC, new_vars_prefix = "DSST")

adsl <- dm %>%
  mutate(TRT01P = ARM, TRT01A = ACTARM) %>%
  derive_vars_merged(
    dataset_add = ex_ext, filter_add = EXDOSE > 0 & !is.na(EXSTDTM),
    new_vars = exprs(TRTSDTM = EXSTDTM, TRTSTMF = EXSTTMF),
    order = exprs(EXSTDTM, EXSEQ), mode = "first",
    by_vars = exprs(STUDYID, USUBJID)
  ) %>%
  derive_vars_merged(
    dataset_add = ex_ext, filter_add = EXDOSE > 0 & !is.na(EXENDTM),
    new_vars = exprs(TRTEDTM = EXENDTM, TRTETMF = EXENTMF),
    order = exprs(EXENDTM, EXSEQ), mode = "last",
    by_vars = exprs(STUDYID, USUBJID)
  ) %>%
  derive_vars_dtm_to_dt(source_vars = exprs(TRTSDTM, TRTEDTM)) %>%
  derive_var_trtdurd() %>%
  derive_vars_merged(
    dataset_add = ds_ext, by_vars = exprs(STUDYID, USUBJID),
    filter_add = DSCAT == "DISPOSITION EVENT",
    new_vars = exprs(EOSDT = DSSTDT, EOSSTT = format_eosstt(DSDECOD),
                     DCSREAS = DSTERM),
    missing_values = exprs(EOSSTT = "ONGOING")
  ) %>%
  derive_var_merged_exist_flag(
    dataset_add = ex, by_vars = exprs(STUDYID, USUBJID),
    new_var = SAFFL, false_value = "N", missing_value = "N",
    condition = EXDOSE > 0
  ) %>%
  mutate(
    DCSREAS = if_else(EOSSTT == "DISCONTINUED", DCSREAS, NA_character_),
    ITTFL   = if_else(!is.na(ARMCD) & ARMCD != "", "Y", "N"),
    AGEGR1  = format_agegr1(AGE),
    RACEGR1 = format_racegr1(RACE),
    REGION1 = format_region1(COUNTRY),
    DOMAIN  = NULL
  )

save_adam(adsl, "adsl")
