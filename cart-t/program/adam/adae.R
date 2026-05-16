## --------------------------------------------------------------------
## ADAE — Adverse Events Analysis Dataset (OCCDS)
## Spec:   spec/adam/adae.yaml
## Inputs: data/sdtm/ae.rds, data/adam/adsl.rds
## Output: data/adam/adae.rds
## --------------------------------------------------------------------

library(dplyr)
library(tidyr)
library(admiral)

ae   <- readRDS("data/sdtm/ae.rds")   |> admiral::convert_blanks_to_na()
adsl <- readRDS("data/adam/adsl.rds") |> admiral::convert_blanks_to_na()

adsl_vars <- adsl |>
  select(USUBJID, SUBJID, SITEID, AGE, AGEGR1, SEX, RACE,
         TRT01P, TRT01A, TRTSDT, TRTEDT, SAFFL)

adae <- ae |>
  admiral::derive_vars_dt(new_vars_prefix = "AST", dtc = AESTDTC) |>
  admiral::derive_vars_dt(new_vars_prefix = "AEN", dtc = AEENDTC) |>
  left_join(adsl_vars, by = "USUBJID") |>
  admiral::derive_vars_dy(reference_date = TRTSDT,
                          source_vars    = exprs(ASTDT, AENDT)) |>
  mutate(
    AESEVN  = dplyr::recode(AESEV,
                            MILD = 1L, MODERATE = 2L, SEVERE = 3L,
                            .default = NA_integer_),
    TRTEMFL = dplyr::case_when(
      is.na(ASTDT) | is.na(TRTSDT)              ~ NA_character_,
      ASTDT >= TRTSDT &
        (is.na(TRTEDT) | ASTDT <= TRTEDT + 30L) ~ "Y",
      TRUE                                      ~ NA_character_
    ),
    ADURN   = dplyr::if_else(!is.na(ASTDT) & !is.na(AENDT),
                             as.integer(AENDT - ASTDT) + 1L,
                             NA_integer_),
    ADURU   = dplyr::if_else(!is.na(ADURN), "DAYS", NA_character_),
    ANL01FL = dplyr::if_else(!is.na(SAFFL) & SAFFL == "Y" &
                             !is.na(TRTEMFL) & TRTEMFL == "Y",
                             "Y", NA_character_)
  )

## First-occurrence flags (admiral helper handles ties via the ordering vars).
adae <- adae |>
  admiral::derive_var_extreme_flag(
    by_vars  = exprs(USUBJID),
    order    = exprs(ASTDT, AESEQ),
    new_var  = AOCCFL,
    mode     = "first"
  ) |>
  admiral::derive_var_extreme_flag(
    by_vars  = exprs(USUBJID, AEDECOD),
    order    = exprs(ASTDT, AESEQ),
    new_var  = AOCCPFL,
    mode     = "first"
  ) |>
  admiral::derive_var_extreme_flag(
    by_vars  = exprs(USUBJID, AEBODSYS),
    order    = exprs(ASTDT, AESEQ),
    new_var  = AOCCSFL,
    mode     = "first"
  ) |>
  arrange(USUBJID, AESEQ) |>
  select(STUDYID, USUBJID, SUBJID, SITEID,
         AGE, AGEGR1, SEX, RACE,
         TRT01P, TRT01A, TRTEMFL,
         AESEQ, AESPID,
         AETERM, AEDECOD, AEBODSYS,
         AESEV, AESEVN, AESER, AEREL, AEOUT,
         ASTDT, AENDT, ASTDY, AENDY,
         ADURN, ADURU,
         AOCCFL, AOCCPFL, AOCCSFL,
         SAFFL, ANL01FL)

saveRDS(adae, "data/adam/adae.rds")
cat(sprintf("ADAE written: %d rows x %d cols\n", nrow(adae), ncol(adae)))
