## --------------------------------------------------------------------
## ADIE — Inclusion/Exclusion Analysis Dataset (OCCDS)
## Spec:   spec/adam/adie.yaml
## Inputs: data/sdtm/ie.rds, data/adam/adsl.rds
## Output: data/adam/adie.rds, data/adam/adie.xpt
## --------------------------------------------------------------------

library(dplyr)
library(tidyr)
library(admiral)

ie   <- readRDS("data/sdtm/ie.rds")   |> admiral::convert_blanks_to_na()
adsl <- readRDS("data/adam/adsl.rds") |> admiral::convert_blanks_to_na()

adsl_vars <- adsl |>
  select(USUBJID, SUBJID, SITEID, AGE, SEX, RACE, STRAT1,
         TRT01P, TRTSDT, RANDFL)

adie <- ie |>
  admiral::derive_vars_dt(new_vars_prefix = "A", dtc = IEDTC) |>
  left_join(adsl_vars, by = "USUBJID") |>
  admiral::derive_vars_dy(reference_date = TRTSDT,
                          source_vars    = exprs(ADT)) |>
  mutate(
    AVISIT  = VISIT,
    # ADSL.RANDFL is "Y"/"N" (Y/N pop flags, never NA, per ADaMIG).
    # SCRNFFL = "Y" when subject was NOT randomized (RANDFL = "N"); else null.
    SCRNFFL = dplyr::if_else(!is.na(RANDFL) & RANDFL == "N", "Y", NA_character_)
  ) |>
  arrange(USUBJID, IESEQ) |>
  select(STUDYID, USUBJID, SUBJID, SITEID,
         AGE, SEX, RACE, STRAT1, TRT01P,
         IESEQ, IETESTCD, IETEST, IECAT, IESCAT, IEORRES,
         ADT, ADY, AVISIT,
         SCRNFFL)

## --------------------------------------------------------------------
## Attach labels and dataset-level label from spec
## (Family A — resolves AD0018, AD0320, AD0503)
##
## metacore/xportr/labelled are not installed in this renv; fall back to
## yaml + base attr(). Labels carry through to XPT via haven::write_xpt
## using the label attribute on each column. See CLAUDE.md for the spec
## YAML contract.
## --------------------------------------------------------------------
spec_yaml <- yaml::read_yaml("spec/adam/adie.yaml")

# Per-variable label
for (v in names(adie)) {
  lab <- spec_yaml$variables[[v]]$label
  if (!is.null(lab) && nzchar(lab)) attr(adie[[v]], "label") <- lab
}

# Dataset-level label
attr(adie, "label") <- spec_yaml$label

saveRDS(adie, "data/adam/adie.rds")
cat(sprintf("ADIE written: %d rows x %d cols\n", nrow(adie), ncol(adie)))

## --------------------------------------------------------------------
## Export XPT v5 for P21 validation
## --------------------------------------------------------------------
adie_xpt <- adie
# haven::write_xpt does not support integer XPT columns; coerce to double.
int_cols <- names(adie_xpt)[vapply(adie_xpt, is.integer, logical(1))]
if (length(int_cols) > 0) {
  for (c in int_cols) {
    lab <- attr(adie_xpt[[c]], "label")
    adie_xpt[[c]] <- as.double(adie_xpt[[c]])
    if (!is.null(lab)) attr(adie_xpt[[c]], "label") <- lab
  }
}
haven::write_xpt(adie_xpt, path = "data/adam/adie.xpt", version = 5, name = "ADIE")
cat("ADIE XPT exported to data/adam/adie.xpt\n")
