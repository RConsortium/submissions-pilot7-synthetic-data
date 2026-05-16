## --------------------------------------------------------------------
## ADDS — Disposition Analysis Dataset (OCCDS)
## Spec:   spec/adam/adds.yaml
## Inputs: data/sdtm/ds.rds, data/adam/adsl.rds
## Output: data/adam/adds.rds
## --------------------------------------------------------------------

library(dplyr)
library(tidyr)
library(admiral)

ds   <- readRDS("data/sdtm/ds.rds")   |> admiral::convert_blanks_to_na()
adsl <- readRDS("data/adam/adsl.rds") |> admiral::convert_blanks_to_na()

adsl_vars <- adsl |>
  select(USUBJID, SUBJID, SITEID, AGE, SEX, RACE, STRAT1,
         TRT01P, TRT01A, TRTSDT, SAFFL, ITTFL)

adds <- ds |>
  admiral::derive_vars_dt(new_vars_prefix = "AST", dtc = DSSTDTC) |>
  left_join(adsl_vars, by = "USUBJID") |>
  admiral::derive_vars_dy(reference_date = TRTSDT,
                          source_vars    = exprs(ASTDT)) |>
  admiral::derive_var_extreme_flag(
    by_vars = exprs(USUBJID),
    order   = exprs(ASTDT, DSSEQ),
    new_var = FINALFL,
    mode    = "last"
  ) |>
  arrange(USUBJID, DSSEQ) |>
  select(STUDYID, USUBJID, SUBJID, SITEID,
         AGE, SEX, RACE, STRAT1,
         TRT01P, TRT01A,
         DSSEQ, DSTERM, DSDECOD, DSCAT, EPOCH,
         ASTDT, ASTDY,
         FINALFL, SAFFL, ITTFL)

saveRDS(adds, "data/adam/adds.rds")
cat(sprintf("ADDS written: %d rows x %d cols\n", nrow(adds), ncol(adds)))
