## --------------------------------------------------------------------
## ADLB — Laboratory Test Results Analysis Dataset (BDS)
## Spec:   spec/adam/adlb.yaml
## Inputs: data/sdtm/lb.rds, data/adam/adsl.rds
## Output: data/adam/adlb.rds, data/adam/adlb.xpt
## --------------------------------------------------------------------

library(dplyr)
library(tidyr)
library(admiral)

lb   <- readRDS("data/sdtm/lb.rds")   |> admiral::convert_blanks_to_na()
adsl <- readRDS("data/adam/adsl.rds") |> admiral::convert_blanks_to_na()

adsl_vars <- adsl |>
  select(USUBJID, SUBJID, SITEID, AGE, SEX, RACE,
         TRT01P, TRT01A, TRTSDT, SAFFL)

adlb <- lb |>
  admiral::derive_vars_dt(new_vars_prefix = "A", dtc = LBDTC) |>
  left_join(adsl_vars, by = "USUBJID") |>
  admiral::derive_vars_dy(reference_date = TRTSDT,
                          source_vars    = exprs(ADT)) |>
  mutate(
    PARAMCD = LBTESTCD,
    PARAM   = trimws(paste0(LBTEST,
                            ifelse(!is.na(LBSTRESU) & nzchar(LBSTRESU),
                                   paste0(" (", LBSTRESU, ")"), ""))),
    PARCAT1 = LBCAT,
    AVAL    = LBSTRESN,
    AVALC   = LBSTRESC,
    AVALU   = LBSTRESU,
    AVISIT  = dplyr::if_else(!is.na(LBBLFL) & LBBLFL == "Y", "Baseline", VISIT),
    AVISITN = dplyr::if_else(!is.na(LBBLFL) & LBBLFL == "Y", 0, VISITNUM)
  ) |>
  group_by(USUBJID, PARAMCD) |>
  arrange(USUBJID, PARAMCD, AVISITN, ADT) |>
  mutate(PARAMN = NA_integer_) |>
  ungroup() |>
  ## ABLFL: prefer LBBLFL records; fall back to latest pre-TRTSDT record.
  admiral::derive_var_extreme_flag(
    by_vars = exprs(USUBJID, PARAMCD),
    order   = exprs(dplyr::desc(LBBLFL %in% "Y"), ADT, LBSEQ),
    new_var = ABLFL,
    mode    = "first"
  ) |>
  admiral::derive_var_base(
    by_vars  = exprs(USUBJID, PARAMCD),
    source_var = AVAL,
    new_var  = BASE
  ) |>
  admiral::derive_var_chg() |>
  admiral::derive_var_pchg() |>
  mutate(
    ANRLO  = NA_real_,
    ANRHI  = NA_real_,
    ANRIND = NA_character_,
    ANL01FL = "Y"
  ) |>
  ## PARAMN: dense-rank by PARAMCD (lexical).
  group_by(PARAMCD) |>
  mutate(PARAMN = NULL) |>
  ungroup() |>
  arrange(USUBJID, PARAMCD, AVISITN, ADT) |>
  mutate(PARAMN = dplyr::dense_rank(PARAMCD)) |>
  mutate(ASEQ = row_number(), .by = USUBJID) |>
  select(STUDYID, USUBJID, SUBJID, SITEID,
         AGE, SEX, RACE, TRT01P, TRT01A,
         ASEQ, PARAMCD, PARAM, PARAMN, PARCAT1,
         AVAL, AVALC, AVALU,
         BASE, CHG, PCHG, ABLFL,
         AVISIT, AVISITN, ADT, ADY,
         ANRLO, ANRHI, ANRIND,
         ANL01FL, SAFFL)

## --------------------------------------------------------------------
## Attach labels and dataset-level label from spec
## (Family A — resolves AD0018, AD0320, AD0503)
##
## metacore/xportr/labelled are not installed in this renv; fall back to
## yaml + base attr(). Labels carry through to XPT via haven::write_xpt
## using the label attribute on each column. See CLAUDE.md for the spec
## YAML contract.
## --------------------------------------------------------------------
spec_yaml <- yaml::read_yaml("spec/adam/adlb.yaml")

# Per-variable label
for (v in names(adlb)) {
  lab <- spec_yaml$variables[[v]]$label
  if (!is.null(lab) && nzchar(lab)) attr(adlb[[v]], "label") <- lab
}

# Dataset-level label
attr(adlb, "label") <- spec_yaml$label

saveRDS(adlb, "data/adam/adlb.rds")
cat(sprintf("ADLB written: %d rows x %d cols\n", nrow(adlb), ncol(adlb)))

## --------------------------------------------------------------------
## Export XPT v5 for P21 validation
## --------------------------------------------------------------------
adlb_xpt <- adlb
# haven::write_xpt does not support integer XPT columns; coerce to double.
int_cols <- names(adlb_xpt)[vapply(adlb_xpt, is.integer, logical(1))]
if (length(int_cols) > 0) {
  for (c in int_cols) {
    lab <- attr(adlb_xpt[[c]], "label")
    adlb_xpt[[c]] <- as.double(adlb_xpt[[c]])
    if (!is.null(lab)) attr(adlb_xpt[[c]], "label") <- lab
  }
}
haven::write_xpt(adlb_xpt, path = "data/adam/adlb.xpt", version = 5, name = "ADLB")
cat("ADLB XPT exported to data/adam/adlb.xpt\n")
