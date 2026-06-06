## --------------------------------------------------------------------
## ADCM — Concomitant Medications Analysis Dataset (OCCDS)
## Spec:   spec/adam/adcm.yaml
## Inputs: data/sdtm/cm.rds, data/adam/adsl.rds
## Output: data/adam/adcm.rds, data/adam/adcm.xpt
## --------------------------------------------------------------------

library(dplyr)
library(tidyr)
library(admiral)

cm   <- readRDS("data/sdtm/cm.rds")   |> admiral::convert_blanks_to_na()
adsl <- readRDS("data/adam/adsl.rds") |> admiral::convert_blanks_to_na()

## ADSL columns to merge onto every CM record. RACE/SAFFL inherit the
## fixes made upstream (DM -> ADSL for RACE; ADSL Y/N for SAFFL).
adsl_vars <- adsl |>
  select(USUBJID, SUBJID, SITEID,
         AGE, SEX, RACE,
         TRT01P, TRT01A,
         TRTSDT, TRTEDT,
         SAFFL)

adcm <- cm |>
  admiral::derive_vars_dt(new_vars_prefix = "AST", dtc = CMSTDTC) |>
  admiral::derive_vars_dt(new_vars_prefix = "AEN", dtc = CMENDTC) |>
  left_join(adsl_vars, by = "USUBJID") |>
  admiral::derive_vars_dy(reference_date = TRTSDT,
                          source_vars    = exprs(ASTDT, AENDT)) |>
  mutate(
    ## Ongoing flag — derived from SDTM CMENRTPT (the CM build wires
    ## CMENRTPT = "ONGOING" when ONGOING = "Yes" on the raw CRF; the old
    ## CMENRF variable was retired in the SD1076 cleanup).
    ONGOFL  = dplyr::if_else(!is.na(CMENRTPT) & CMENRTPT == "ONGOING",
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
    ),
    ## Analysis-record flag 01: safety subjects only. SAFFL is Y/N
    ## (never NA) after the ADSL Y/N fix.
    ANL01FL = dplyr::if_else(!is.na(SAFFL) & SAFFL == "Y",
                             "Y", NA_character_)
  ) |>
  arrange(USUBJID, CMSEQ) |>
  select(STUDYID, USUBJID, SUBJID, SITEID,
         AGE, SEX, RACE, TRT01P, TRT01A,
         TRTSDT, TRTEDT,
         CMSEQ,
         CMTRT, CMDECOD, CMINDC,
         CMDOSE, CMDOSU, CMROUTE,
         ASTDT, AENDT, ASTDY, AENDY,
         ONGOFL, PREFL, ONTRTFL, SAFFL, ANL01FL)

## --------------------------------------------------------------------
## Attach labels and dataset-level label from spec
## (Family A — resolves AD0018, AD0320, AD0503)
##
## metacore/xportr/labelled are not installed in this renv; fall back to
## yaml + base attr(). Labels carry through to XPT via haven::write_xpt
## using the label attribute on each column. See CLAUDE.md for the spec
## YAML contract.
## --------------------------------------------------------------------
spec_yaml <- yaml::read_yaml("spec/adam/adcm.yaml")

# Per-variable label
for (v in names(adcm)) {
  lab <- spec_yaml$variables[[v]]$label
  if (!is.null(lab) && nzchar(lab)) attr(adcm[[v]], "label") <- lab
}

# Dataset-level label
attr(adcm, "label") <- spec_yaml$label

saveRDS(adcm, "data/adam/adcm.rds")
cat(sprintf("ADCM written: %d rows x %d cols\n", nrow(adcm), ncol(adcm)))

## --------------------------------------------------------------------
## Export XPT v5 for P21 validation
## --------------------------------------------------------------------
adcm_xpt <- adcm
# haven::write_xpt does not support integer XPT columns; coerce to double.
int_cols <- names(adcm_xpt)[vapply(adcm_xpt, is.integer, logical(1))]
if (length(int_cols) > 0) {
  for (c in int_cols) {
    lab <- attr(adcm_xpt[[c]], "label")
    adcm_xpt[[c]] <- as.double(adcm_xpt[[c]])
    if (!is.null(lab)) attr(adcm_xpt[[c]], "label") <- lab
  }
}
haven::write_xpt(adcm_xpt, path = "data/adam/adcm.xpt", version = 5, name = "ADCM")
cat("ADCM XPT exported to data/adam/adcm.xpt\n")
