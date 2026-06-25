## --------------------------------------------------------------------
## ADSL — Subject-Level Analysis Dataset
## Spec:   spec/adam/adsl.yaml
## Inputs: data/sdtm/dm.rds, data/sdtm/ds.rds, data/sdtm/ae.rds, data/sdtm/qs.rds
## Output: data/adam/adsl.rds
## --------------------------------------------------------------------

library(dplyr)
library(tidyr)
library(admiral)

source("program/sdtm/ut_visits.R", chdir = FALSE)

dm   <- readRDS("data/sdtm/dm.rds")   |> admiral::convert_blanks_to_na()
ds   <- readRDS("data/sdtm/ds.rds")   |> admiral::convert_blanks_to_na()
ae   <- readRDS("data/sdtm/ae.rds")   |> admiral::convert_blanks_to_na()
qs   <- readRDS("data/sdtm/qs.rds")   |> admiral::convert_blanks_to_na()
rand <- readRDS("data/raw/rand.rds")

## Phenotype stratum from the Randomize CRF PROFILE item.
phenotype <- rand |>
  filter(itemname == "PROFILE") |>
  distinct(subjectkey, studysubjectid, PROFILE = value) |>
  mutate(USUBJID = make_usubjid(studysubjectid)) |>
  transmute(USUBJID,
            STRAT1  = phenotype_code(PROFILE),
            STRAT1L = phenotype_label(PROFILE))

## TRTxxPN/AN map keyed by ARMCD. Screen failures have ARMCD = null (per
## SDTMIG Assumption 4), so TRT01PN is NA for screen failures; TRT01AN is
## NA for all subjects because ACTARMCD is null throughout (no treatment).
arm_n_map <- c(TREATMENT = 1L)

randdt_per_subj <- ds |>
  filter(DSDECOD == "RANDOMIZED") |>
  group_by(USUBJID) |>
  summarise(RANDDT = suppressWarnings(min(as.Date(DSSTDTC), na.rm = TRUE)),
            .groups = "drop") |>
  mutate(RANDDT = dplyr::if_else(is.finite(RANDDT), RANDDT, as.Date(NA)))

final_disp <- ds |>
  group_by(USUBJID) |>
  arrange(USUBJID, dplyr::desc(DSSTDTC), dplyr::desc(DSSEQ)) |>
  slice_head(n = 1) |>
  ungroup() |>
  select(USUBJID,
         DCDECOD  = DSDECOD,
         DCREASCD = DSTERM)

has_postbl_qs <- qs |>
  filter(!is.na(QSSTRESN)) |>
  distinct(USUBJID) |>
  mutate(has_qs = TRUE)

has_ae <- ae |>
  distinct(USUBJID) |>
  mutate(has_ae = TRUE)

adsl <- dm |>
  ## Date conversions (admiral expects R dates, not ISO 8601 char).
  mutate(
    TRTSDT = suppressWarnings(as.Date(dplyr::coalesce(RFXSTDTC, RFSTDTC))),
    TRTEDT = suppressWarnings(as.Date(dplyr::coalesce(RFXENDTC, RFENDTC))),
    EOSDT  = suppressWarnings(as.Date(RFENDTC))
  ) |>
  admiral::derive_var_trtdurd(
    start_date = TRTSDT,
    end_date   = TRTEDT
  ) |>
  left_join(randdt_per_subj, by = "USUBJID") |>
  left_join(final_disp,      by = "USUBJID") |>
  left_join(has_ae,          by = "USUBJID") |>
  left_join(has_postbl_qs,   by = "USUBJID") |>
  left_join(phenotype,       by = "USUBJID") |>
  mutate(
    AGEGR1   = dplyr::case_when(
      is.na(AGE)  ~ NA_character_,
      AGE <  65   ~ "<65",
      AGE >= 65   ~ ">=65"
    ),
    AGEGR1N  = dplyr::case_when(
      AGEGR1 == "<65"  ~ 1L,
      AGEGR1 == ">=65" ~ 2L,
      TRUE             ~ NA_integer_
    ),

    TRT01P   = ARM,
    TRT01A   = ACTARM,
    TRT01PN  = unname(arm_n_map[ARMCD]),
    TRT01AN  = unname(arm_n_map[ACTARMCD]),

    EOSSTT   = dplyr::case_when(
      is.na(DCDECOD)                                    ~ "ONGOING",
      DCDECOD == "EARLY TERMINATION"                    ~ "DISCONTINUED",
      grepl("COMPLETED", toupper(DCDECOD), fixed = FALSE) ~ "COMPLETED",
      TRUE                                              ~ "ONGOING"
    ),

    ## ADaMIG: population flags are Y/N, never NA. Resolves P21 AD0019.
    RANDFL   = ifelse(!is.na(RANDDT),                  "Y", "N"),
    SAFFL    = ifelse(!is.na(TRTSDT) | !is.na(has_ae), "Y", "N"),
    ITTFL    = ifelse(!is.na(RANDFL) & RANDFL == "Y",  "Y", "N"),
    EFFFL    = ifelse(!is.na(has_qs) &
                        !is.na(RANDFL) & RANDFL == "Y", "Y", "N"),
    COMPLFL  = ifelse(!is.na(EOSSTT) & EOSSTT == "COMPLETED", "Y", "N")
  ) |>
  select(STUDYID, USUBJID, SUBJID, SITEID,
         AGE, AGEU, AGEGR1, AGEGR1N,
         SEX, RACE, ETHNIC, COUNTRY,
         STRAT1, STRAT1L,
         ARMCD, ARM, ACTARMCD, ACTARM,
         TRT01P, TRT01PN, TRT01A, TRT01AN,
         TRTSDT, TRTEDT, TRTDURD,
         RANDDT, EOSDT, EOSSTT, DCDECOD, DCREASCD,
         RANDFL, SAFFL, ITTFL, EFFFL, COMPLFL)

## --------------------------------------------------------------------
## Attach labels and dataset-level label from spec
## (Family A — resolves AD0018, AD0320, AD0503)
##
## metacore/xportr/labelled are not installed in this renv; fall back to
## yaml + base attr(). Labels carry through to XPT via haven::write_xpt
## using the label attribute on each column. See CLAUDE.md for the spec
## YAML contract.
## --------------------------------------------------------------------
spec_yaml <- yaml::read_yaml("spec/adam/adsl.yaml")

# Per-variable label
for (v in names(adsl)) {
  lab <- spec_yaml$variables[[v]]$label
  if (!is.null(lab) && nzchar(lab)) attr(adsl[[v]], "label") <- lab
}

# Dataset-level label
attr(adsl, "label") <- spec_yaml$label

saveRDS(adsl, "data/adam/adsl.rds")
cat(sprintf("ADSL written: %d rows x %d cols\n", nrow(adsl), ncol(adsl)))

## --------------------------------------------------------------------
## Export XPT v5 for P21 validation
## --------------------------------------------------------------------
adsl_xpt <- adsl
# haven::write_xpt does not support integer XPT columns; coerce to double.
int_cols <- names(adsl_xpt)[vapply(adsl_xpt, is.integer, logical(1))]
if (length(int_cols) > 0) {
  for (c in int_cols) {
    lab <- attr(adsl_xpt[[c]], "label")
    adsl_xpt[[c]] <- as.double(adsl_xpt[[c]])
    if (!is.null(lab)) attr(adsl_xpt[[c]], "label") <- lab
  }
}
haven::write_xpt(adsl_xpt, path = "data/adam/adsl.xpt", version = 5, name = "ADSL")
cat("ADSL XPT exported to data/adam/adsl.xpt\n")
