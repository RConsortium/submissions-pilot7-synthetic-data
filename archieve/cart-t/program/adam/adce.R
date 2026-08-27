## --------------------------------------------------------------------
## ADCE — Clinical Events Analysis Dataset (OCCDS)
## Spec:   spec/adam/adce.yaml
## Inputs: data/sdtm/ce.rds, data/adam/adsl.rds
## Output: data/adam/adce.rds, data/adam/adce.xpt
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
         CESEQ, CETERM, CECAT,
         ASTDT, ASTDY,
         AOCCFL, SAFFL, ANL01FL)

## --------------------------------------------------------------------
## Attach labels and dataset-level label from spec
## (Family A — resolves AD0018, AD0320, AD0503)
##
## metacore/xportr/labelled are not installed in this renv; fall back to
## yaml + base attr(). Labels carry through to XPT via haven::write_xpt
## using the label attribute on each column. See CLAUDE.md for the spec
## YAML contract.
## --------------------------------------------------------------------
spec_yaml <- yaml::read_yaml("spec/adam/adce.yaml")

# Per-variable label
for (v in names(adce)) {
  lab <- spec_yaml$variables[[v]]$label
  if (!is.null(lab) && nzchar(lab)) attr(adce[[v]], "label") <- lab
}

# Dataset-level label
attr(adce, "label") <- spec_yaml$label

saveRDS(adce, "data/adam/adce.rds")
cat(sprintf("ADCE written: %d rows x %d cols\n", nrow(adce), ncol(adce)))

## --------------------------------------------------------------------
## Export XPT v5 for P21 validation
## --------------------------------------------------------------------
adce_xpt <- adce
# haven::write_xpt does not support integer XPT columns; coerce to double.
int_cols <- names(adce_xpt)[vapply(adce_xpt, is.integer, logical(1))]
if (length(int_cols) > 0) {
  for (c in int_cols) {
    lab <- attr(adce_xpt[[c]], "label")
    adce_xpt[[c]] <- as.double(adce_xpt[[c]])
    if (!is.null(lab)) attr(adce_xpt[[c]], "label") <- lab
  }
}
haven::write_xpt(adce_xpt, path = "data/adam/adce.xpt", version = 5, name = "ADCE")
cat("ADCE XPT exported to data/adam/adce.xpt\n")
