## --------------------------------------------------------------------
## ADDS — Disposition Analysis Dataset (OCCDS)
## Spec:   spec/adam/adds.yaml
## Inputs: data/sdtm/ds.rds, data/adam/adsl.rds
## Output: data/adam/adds.rds, data/adam/adds.xpt
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

## --------------------------------------------------------------------
## Attach labels and dataset-level label from spec
## (Family A — resolves AD0018, AD0320, AD0503)
##
## metacore/xportr/labelled are not installed in this renv; fall back to
## yaml + base attr(). Labels carry through to XPT via haven::write_xpt
## using the label attribute on each column. See CLAUDE.md for the spec
## YAML contract.
## --------------------------------------------------------------------
spec_yaml <- yaml::read_yaml("spec/adam/adds.yaml")

# Per-variable label
for (v in names(adds)) {
  lab <- spec_yaml$variables[[v]]$label
  if (!is.null(lab) && nzchar(lab)) attr(adds[[v]], "label") <- lab
}

# Dataset-level label
attr(adds, "label") <- spec_yaml$label

saveRDS(adds, "data/adam/adds.rds")
cat(sprintf("ADDS written: %d rows x %d cols\n", nrow(adds), ncol(adds)))

## --------------------------------------------------------------------
## Export XPT v5 for P21 validation
## --------------------------------------------------------------------
adds_xpt <- adds
# haven::write_xpt does not support integer XPT columns; coerce to double.
int_cols <- names(adds_xpt)[vapply(adds_xpt, is.integer, logical(1))]
if (length(int_cols) > 0) {
  for (c in int_cols) {
    lab <- attr(adds_xpt[[c]], "label")
    adds_xpt[[c]] <- as.double(adds_xpt[[c]])
    if (!is.null(lab)) attr(adds_xpt[[c]], "label") <- lab
  }
}
haven::write_xpt(adds_xpt, path = "data/adam/adds.xpt", version = 5, name = "ADDS")
cat("ADDS XPT exported to data/adam/adds.xpt\n")
