## --------------------------------------------------------------------
## ADCM — Concomitant Medications Analysis Dataset (OCCDS)
## Spec:   spec/adam/adcm.yaml
## Inputs: data/sdtm/cm.rds, data/adam/adsl.rds
## Output: data/adam/adcm.rds
## --------------------------------------------------------------------

library(dplyr)
library(tidyr)
library(admiral)

cm   <- readRDS("data/sdtm/cm.rds")   |> admiral::convert_blanks_to_na()
adsl <- readRDS("data/adam/adsl.rds") |> admiral::convert_blanks_to_na()

adsl_vars <- adsl |>
  select(USUBJID, SUBJID, SITEID, AGE, SEX, RACE,
         TRT01P, TRT01A, TRTSDT, TRTEDT, SAFFL)

adcm <- cm |>
  admiral::derive_vars_dt(new_vars_prefix = "AST", dtc = CMSTDTC) |>
  admiral::derive_vars_dt(new_vars_prefix = "AEN", dtc = CMENDTC) |>
  left_join(adsl_vars, by = "USUBJID") |>
  admiral::derive_vars_dy(reference_date = TRTSDT,
                          source_vars    = exprs(ASTDT, AENDT)) |>
  mutate(
    ONGOFL  = dplyr::if_else(!is.na(CMENRF) & CMENRF == "ONGOING",
                             "Y", NA_character_),
    PREFL   = dplyr::case_when(
      is.na(ASTDT) | is.na(TRTSDT) ~ NA_character_,
      ASTDT < TRTSDT               ~ "Y",
      TRUE                         ~ NA_character_
    ),
    ONTRTFL = dplyr::case_when(
      is.na(ASTDT) | is.na(TRTSDT)                                  ~ NA_character_,
      ASTDT >= TRTSDT & (is.na(TRTEDT) | ASTDT <= TRTEDT)            ~ "Y",
      TRUE                                                           ~ NA_character_
    )
  ) |>
  arrange(USUBJID, CMSEQ) |>
  select(STUDYID, USUBJID, SUBJID, SITEID,
         AGE, SEX, RACE, TRT01P, TRT01A,
         CMSEQ,
         CMTRT, CMDECOD, CMRXCUI, CMINDC,
         CMDOSE, CMDOSU, CMROUTE,
         ASTDT, AENDT, ASTDY, AENDY,
         ONGOFL, PREFL, ONTRTFL, SAFFL)

saveRDS(adcm, "data/adam/adcm.rds")
cat(sprintf("ADCM written: %d rows x %d cols\n", nrow(adcm), ncol(adcm)))
