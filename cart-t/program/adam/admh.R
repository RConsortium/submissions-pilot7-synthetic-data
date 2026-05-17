## --------------------------------------------------------------------
## ADMH — Medical History Analysis Dataset (OCCDS)
## Spec:   spec/adam/admh.yaml
## Inputs: data/sdtm/mh.rds, data/adam/adsl.rds
## Output: data/adam/admh.rds
## --------------------------------------------------------------------

library(dplyr)
library(tidyr)
library(admiral)

mh   <- readRDS("data/sdtm/mh.rds")   |> admiral::convert_blanks_to_na()
adsl <- readRDS("data/adam/adsl.rds") |> admiral::convert_blanks_to_na()

adsl_vars <- adsl |>
  select(USUBJID, SUBJID, SITEID, AGE, AGEGR1, SEX, RACE,
         TRT01P, TRT01A, TRTSDT, SAFFL, ITTFL)

admh <- mh |>
  admiral::derive_vars_dt(new_vars_prefix = "AST", dtc = MHSTDTC) |>
  admiral::derive_vars_dt(new_vars_prefix = "AEN", dtc = MHENDTC) |>
  left_join(adsl_vars, by = "USUBJID") |>
  admiral::derive_vars_dy(reference_date = TRTSDT,
                          source_vars    = exprs(ASTDT, AENDT)) |>
  mutate(
    ONGOFL  = dplyr::if_else(!is.na(MHENRF) & MHENRF == "ONGOING",
                             "Y", NA_character_),
    PREHISFL = dplyr::case_when(
      !is.na(MHENRF) & MHENRF == "ONGOING"                       ~ "Y",
      !is.na(ASTDT) & !is.na(TRTSDT) & ASTDT <= TRTSDT           ~ "Y",
      !is.na(ASTDT) & is.na(TRTSDT)                              ~ "Y",
      TRUE                                                       ~ NA_character_
    )
  ) |>
  arrange(USUBJID, MHSEQ) |>
  select(STUDYID, USUBJID, SUBJID, SITEID,
         AGE, AGEGR1, SEX, RACE,
         TRT01P, TRT01A,
         MHSEQ, MHTERM, MHDECOD, MHBODSYS, MHCAT, MHSCAT, MHENRF,
         ASTDT, AENDT, ASTDY, AENDY,
         PREHISFL, ONGOFL, SAFFL, ITTFL)

saveRDS(admh, "data/adam/admh.rds")
cat(sprintf("ADMH written: %d rows x %d cols\n", nrow(admh), ncol(admh)))
