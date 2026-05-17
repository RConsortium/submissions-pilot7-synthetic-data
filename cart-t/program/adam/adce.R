## --------------------------------------------------------------------
## ADCE — Clinical Events Analysis Dataset (OCCDS)
## Spec:   spec/adam/adce.yaml
## Inputs: data/sdtm/ce.rds, data/adam/adsl.rds
## Output: data/adam/adce.rds
## --------------------------------------------------------------------

library(dplyr)
library(tidyr)
library(admiral)

ce   <- readRDS("data/sdtm/ce.rds")   |> admiral::convert_blanks_to_na()
adsl <- readRDS("data/adam/adsl.rds") |> admiral::convert_blanks_to_na()

adsl_vars <- adsl |>
  select(USUBJID, SUBJID, SITEID, AGE, SEX, RACE, STRAT1,
         TRT01P, TRT01A, TRTSDT, SAFFL)

adce <- ce |>
  admiral::derive_vars_dt(new_vars_prefix = "AST", dtc = CESTDTC) |>
  left_join(adsl_vars, by = "USUBJID") |>
  admiral::derive_vars_dy(reference_date = TRTSDT,
                          source_vars    = exprs(ASTDT)) |>
  admiral::derive_var_extreme_flag(
    by_vars = exprs(USUBJID),
    order   = exprs(ASTDT, CESEQ),
    new_var = AOCCFL,
    mode    = "first"
  ) |>
  mutate(
    ANL01FL = dplyr::if_else(!is.na(SAFFL) & SAFFL == "Y", "Y", NA_character_)
  ) |>
  arrange(USUBJID, CESEQ) |>
  select(STUDYID, USUBJID, SUBJID, SITEID,
         AGE, SEX, RACE, STRAT1,
         TRT01P, TRT01A,
         CESEQ, CETERM, CEDECOD, CECAT, CESER, CEPRESP, CEOCCUR,
         ASTDT, ASTDY,
         AOCCFL, SAFFL, ANL01FL)

saveRDS(adce, "data/adam/adce.rds")
cat(sprintf("ADCE written: %d rows x %d cols\n", nrow(adce), ncol(adce)))
