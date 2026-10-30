#************************************************************************
# Purpose:     Generate ADLBH dataset
# Input:       LB, SUPPLB (from datasetjson), and ADSL datasets
# Output:      adlbh.json
#************************************************************************

# Note to Reviewer
# To rerun the code below, please refer ADRG appendix.
# After required package are installed, the path variable needs to be defined
# in the .Rprofile file

# Setup -----------------
## Load libraries -------
library(dplyr)
library(tidyr)
library(admiral)
library(metacore)
library(metatools)
library(stringr)
library(purrr)
library(datasetjson)

source(file.path(path$utils, "save_dataset_json.r"))

## Load datasets ------------
dat_to_load <- list(
  lb = file.path(path$sdtm, "lb.json"),
  supplb = file.path(path$sdtm, "supplb.json"),
  adsl = file.path(path$adam, "adsl.json")
)

purrr::iwalk(dat_to_load, \(file_path, var_name) {
  raw_data <- read_dataset_json(file_path)
  assign(var_name, raw_data, envir = .GlobalEnv)
  message(paste("Assigned variable '", var_name, "' to .GlobalEnv"))
})

## Load dataset specs -----------
metacore <- spec_to_metacore(
  file.path(path$adam_reference, "pilot6-specs.xlsx"),
  where_sep_sheet = FALSE,
  quiet = TRUE
)

### Get the specifications for the dataset we are currently building
adlbh_spec <- metacore %>%
  select_dataset("ADLBH")

# Create adlbh dataset -----------------
adlb00 <- lb %>%
  combine_supp(supplb) %>%
  filter(LBCAT == "HEMATOLOGY") %>%
  mutate(
    LBSTNRLO = as.numeric(LBSTNRLO),
    LBSTNRHI = as.numeric(LBSTNRHI),
    LBSTRESN = as.numeric(LBSTRESN),
  )

## ADSL information ----------------------------------------------
adsl_vars <- exprs(
  STUDYID,
  SUBJID,
  USUBJID,
  TRT01PN,
  TRT01P,
  TRT01AN,
  TRT01A,
  TRTSDT,
  TRTEDT,
  AGE,
  AGEGR1,
  AGEGR1N,
  RACE,
  RACEN,
  SEX,
  COMP24FL,
  DSRAEFL,
  SAFFL
)

adlb01 <- adlb00 %>%
  derive_vars_merged(
    dataset_add = adsl,
    new_vars = adsl_vars,
    by = exprs(STUDYID, USUBJID)
  )

## Dates -------------------------------------------
adlb02 <- adlb01 %>%
  derive_vars_dt(
    new_vars_prefix = "A",
    dtc = LBDTC,
    highest_imputation = "n"
  ) %>%
  derive_vars_dy(reference_date = TRTSDT, source_vars = exprs(ADT))

## AVAL(C) ------------------------------------------------
# No imputations are done for values below LL or above UL
adlb03 <- adlb02 %>%
  mutate(
    AVAL = as.numeric(LBSTRESN),
    AVALC = ifelse(!is.na(AVAL), LBSTRESC, NA)
  )

## Parameter --------------------------------------------
adlb04 <- adlb03 %>%
  mutate(
    PARAM = paste0(LBTEST, " (", LBSTRESU, ")"),
    PARAMCD = LBTESTCD,
    PARCAT1 = "HEM"
  ) %>%
  create_var_from_codelist(
    metacore = adlbh_spec,
    input_var = PARAM,
    out_var = PARAMN
  )

## Baseline ----------------------------------
adlb05 <- adlb04 %>%
  mutate(ABLFL = LBBLFL) %>%
  derive_var_base(
    by_vars = exprs(STUDYID, USUBJID, PARAMCD),
    source_var = AVAL,
    new_var = BASE
  ) %>%
  derive_var_chg() %>%
  mutate(CHG = ifelse(VISITNUM == 1, NA, CHG))


## Visits ------------------------------
eot <- adlb05 %>%
  filter(ENDPOINT == "Y" | VISITNUM == 12) %>%
  mutate(
    AVISIT = "End of Treatment",
    AVISITN = 99,
    AENTMTFL = "Y"
  )

adlb06 <- adlb05 %>%
  # nolint start
  filter(
    grepl("WEEK", VISIT, fixed = TRUE) |
      grepl("UNSCHEDULED", VISIT, fixed = TRUE) |
      grepl("SCREENING", VISIT, fixed = TRUE)
  ) %>%
  # nolint end
  mutate(
    AVISIT = case_when(
      ABLFL == "Y" ~ "Baseline",
      grepl("UNSCHEDULED", VISIT) == TRUE ~ "",
      TRUE ~ str_to_sentence(VISIT)
    ),
    AVISITN = case_when(
      AVISIT == "Baseline" ~ 0,
      TRUE ~ as.numeric(gsub("[^0-9]", "", AVISIT))
    ),
    AENTMTFL = ""
  ) %>%
  rbind(eot) %>%
  mutate(
    AVISITN = ifelse(AVISITN == -1, "", AVISITN)
  )

# get EOT for those that did not make it to week 24
eot2 <- adlb06 %>%
  arrange(STUDYID, USUBJID, PARAMCD, desc(AVISITN)) %>%
  group_by(STUDYID, USUBJID, PARAMCD) %>%
  filter(VISITNUM != 13) %>%
  slice(1) %>%
  filter(!is.na(AVISITN), AVISITN != 0, AVISITN != 99) %>%
  mutate(
    AVISITN = 99,
    AVISIT = "End of Treatment",
    AENTMTFL = "Y"
  )

adlb07 <- adlb06 %>%
  filter(VISITNUM <= 12 & AVISITN > 0 & AVISITN != 99 & !grepl("UN", VISIT)) %>%
  group_by(USUBJID, PARAMCD) %>%
  mutate(AENTMTFL_1 = ifelse(max(AVISITN, na.rm = TRUE) == AVISITN, "Y", "")) %>%
  select(USUBJID, PARAMCD, AENTMTFL_1, LBSEQ) %>%
  full_join(adlb06, by = c("USUBJID", "PARAMCD", "LBSEQ"), multiple = "all") %>%
  mutate(AENTMTFL = ifelse(AENTMTFL == "Y", AENTMTFL, AENTMTFL_1)) %>%
  select(-AENTMTFL_1) %>%
  rbind(eot2) %>%
  ungroup()

## Limits -----------------------------------
adlb08 <- adlb07 %>%
  mutate(
    ANRLO = LBSTNRLO,
    ANRHI = LBSTNRHI,
    A1LO = LBSTNRLO,
    A1HI = LBSTNRHI,
    R2A1LO = AVAL / A1LO,
    R2A1HI = AVAL / A1HI,
    BR2A1LO = BASE / A1LO,
    BR2A1HI = BASE / A1HI,
    ONE = abs((LBSTRESN - (1.5 * LBSTNRHI))),
    TWO = abs(((.5 * LBSTNRLO) - LBSTRESN)),
    ALBTRVAL = ifelse(ONE > TWO, ONE, TWO),
    ANRIND = ifelse(AVAL < (0.5 * LBSTNRLO), "L", ifelse(AVAL > (1.5 * LBSTNRHI), "H", "N")),
    ANRIND = ifelse(is.na(AVAL), "N", ANRIND)
  ) %>%
  derive_var_base(
    by_vars = exprs(STUDYID, USUBJID, PARAMCD),
    source_var = ANRIND,
    new_var = BNRIND
  ) %>% # Low and High values are repeating
  group_by(STUDYID, USUBJID, PARAMCD) %>%
  ungroup() %>%
  select(-ONE, -TWO)

## Derive ANL01FL -----------
adlb09 <- adlb08 %>%
  filter((VISITNUM >= 4 & VISITNUM <= 12) & !grepl("UN", VISIT)) %>%
  group_by(USUBJID, PARAMCD) %>%
  mutate(
    maxALBTRVAL = ifelse(!is.na(ALBTRVAL), max(ALBTRVAL, na.rm = TRUE), ALBTRVAL),
    ANL01FL = ifelse(maxALBTRVAL == ALBTRVAL, "Y", "")
  ) %>%
  arrange(desc(ANL01FL)) %>%
  select(USUBJID, PARAMCD, LBSEQ, ANL01FL) %>%
  slice(1) %>%
  full_join(adlb08, by = c("USUBJID", "PARAMCD", "LBSEQ"), multiple = "all")

adlbh10 <- adlb09 %>%
  mutate(
    TRTP = TRT01P,
    TRTPN = TRT01PN,
    TRTA = TRT01A,
    TRTAN = TRT01AN
  )

adlbh <- adlbh10 %>%
  drop_unspec_vars(adlbh_spec) %>%
  order_cols(adlbh_spec) %>%
  set_variable_labels(adlbh_spec)

# Saving the dataset as datasetjson format --------------
save_dataset_json(path$adam, adlbh, adlbh_spec)
