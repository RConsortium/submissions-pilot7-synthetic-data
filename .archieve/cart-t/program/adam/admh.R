## --------------------------------------------------------------------
## ADMH — Medical History Analysis Dataset (OCCDS)
## Spec:   spec/adam/admh.yaml
## Inputs: data/sdtm/mh.rds, data/adam/adsl.rds
## Output: data/adam/admh.rds, data/adam/admh.xpt
## --------------------------------------------------------------------

library(dplyr)
library(tidyr)
library(admiral)

mh   <- readRDS("data/sdtm/mh.rds")   |> admiral::convert_blanks_to_na()
adsl <- readRDS("data/adam/adsl.rds") |> admiral::convert_blanks_to_na()

## ADSL columns to merge onto every MH record. RACE / SAFFL / ITTFL
## inherit upstream fixes (DM -> ADSL for RACE; ADSL Y/N for flags).
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
    ## Ongoing flag — derived from SDTM MHENRTPT (the MH build wires
    ## MHENRTPT = "ONGOING" when raw ONG = "1"). The old MHENRF column
    ## is still emitted by SDTM MH, but using MHENRTPT keeps the
    ## convention aligned with ADCM (CMENRTPT) and is robust if MHENRF
    ## is later dropped.
    ONGOFL  = dplyr::if_else(!is.na(MHENRTPT) & MHENRTPT == "ONGOING",
                             "Y", NA_character_),
    PREHISFL = dplyr::case_when(
      !is.na(MHENRTPT) & MHENRTPT == "ONGOING"                   ~ "Y",
      !is.na(ASTDT) & !is.na(TRTSDT) & ASTDT <= TRTSDT           ~ "Y",
      !is.na(ASTDT) & is.na(TRTSDT)                              ~ "Y",
      TRUE                                                       ~ NA_character_
    )
  ) |>
  arrange(USUBJID, MHSEQ) |>
  select(STUDYID, USUBJID, SUBJID, SITEID,
         AGE, AGEGR1, SEX, RACE,
         TRT01P, TRT01A,
         MHSEQ, MHTERM, MHDECOD, MHBODSYS, MHCAT, MHSCAT, MHENRTPT,
         ASTDT, AENDT, ASTDY, AENDY,
         PREHISFL, ONGOFL, SAFFL, ITTFL)

## --------------------------------------------------------------------
## Attach labels and dataset-level label from spec
## (Family A — resolves AD0018, AD0320, AD0503)
##
## metacore/xportr/labelled are not installed in this renv; fall back to
## yaml + base attr(). Labels carry through to XPT via haven::write_xpt
## using the label attribute on each column. See CLAUDE.md for the spec
## YAML contract.
## --------------------------------------------------------------------
spec_yaml <- yaml::read_yaml("spec/adam/admh.yaml")

# Per-variable label
for (v in names(admh)) {
  lab <- spec_yaml$variables[[v]]$label
  if (!is.null(lab) && nzchar(lab)) attr(admh[[v]], "label") <- lab
}

# Dataset-level label
attr(admh, "label") <- spec_yaml$label

saveRDS(admh, "data/adam/admh.rds")
cat(sprintf("ADMH written: %d rows x %d cols\n", nrow(admh), ncol(admh)))

## --------------------------------------------------------------------
## Export XPT v5 for P21 validation
## --------------------------------------------------------------------
admh_xpt <- admh
# haven::write_xpt does not support integer XPT columns; coerce to double.
int_cols <- names(admh_xpt)[vapply(admh_xpt, is.integer, logical(1))]
if (length(int_cols) > 0) {
  for (c in int_cols) {
    lab <- attr(admh_xpt[[c]], "label")
    admh_xpt[[c]] <- as.double(admh_xpt[[c]])
    if (!is.null(lab)) attr(admh_xpt[[c]], "label") <- lab
  }
}
haven::write_xpt(admh_xpt, path = "data/adam/admh.xpt", version = 5, name = "ADMH")
cat("ADMH XPT exported to data/adam/admh.xpt\n")
