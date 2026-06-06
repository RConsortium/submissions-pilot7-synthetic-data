## --------------------------------------------------------------------
## ADQS — Questionnaire (SF-12) Analysis Dataset (BDS)
## Spec:   spec/adam/adqs.yaml
## Inputs: data/sdtm/qs.rds, data/adam/adsl.rds
## Output: data/adam/adqs.rds, data/adam/adqs.xpt
## --------------------------------------------------------------------

library(dplyr)
library(tidyr)
library(admiral)

qs   <- readRDS("data/sdtm/qs.rds")   |> admiral::convert_blanks_to_na()
adsl <- readRDS("data/adam/adsl.rds") |> admiral::convert_blanks_to_na()

adsl_vars <- adsl |>
  select(USUBJID, SUBJID, SITEID, AGE, SEX, RACE,
         TRT01P, TRT01A, TRTSDT, EFFFL)

## --------------------------------------------------------------------
## Canonical (PARAMCD, PARAM, PARAMN) lookup — dataset-level, 1-to-1.
##
## Resolves AD0146B / AD0147B: PARAM and PARAMN must be functions of
## PARAMCD across the whole dataset. The previous build derived PARAMN
## per-subject via dense_rank() with `.by = USUBJID`, so the same
## PARAMCD could carry a different PARAMN in different subjects (max 7
## distinct PARAMN per PARAMCD). PARAM was set to QSTEST which is
## already 1-to-1 per QSTESTCD, so AD0146B was effectively a label-
## inheritance artifact — but we now make it explicit via the same
## lookup table for symmetry.
##
## PARAM is a human-readable long form that uniquely encodes both the
## SF-12 instrument and the test code, e.g. "SF-12 Q01 General Health
## (SF1201)" / "SF-12 Bodily Pain Subscale (SF12BP)". This keeps PARAM
## ≤ 200 chars per ADaMIG and ≤ the 200-char field length in the spec.
## PARAMN is the canonical SF-12 item order: items 1..12, then the four
## subscales in PF, RP, BP, GH, VT, SF, RE, MH order (the SF-12 v1
## subscale dictionary order; only BP/GH/VT/SF actually emit rows in
## this pilot — see domains/qs.md for why).
## --------------------------------------------------------------------
param_lookup <- tibble::tribble(
  ~PARAMCD,  ~PARAM,                                          ~PARAMN,
  "SF1201",  "SF-12 Q01 General Health (SF1201)",                  1,
  "SF1202",  "SF-12 Q02 Moderate Activities (SF1202)",             2,
  "SF1203",  "SF-12 Q03 Climb Several Flights (SF1203)",           3,
  "SF1204",  "SF-12 Q04 Accomplished Less - Physical (SF1204)",    4,
  "SF1205",  "SF-12 Q05 Limited in Kind - Physical (SF1205)",      5,
  "SF1206",  "SF-12 Q06 Accomplished Less - Emotional (SF1206)",   6,
  "SF1207",  "SF-12 Q07 Less Careful - Emotional (SF1207)",        7,
  "SF1208",  "SF-12 Q08 Pain Interfered (SF1208)",                 8,
  "SF1209",  "SF-12 Q09 Calm and Peaceful (SF1209)",               9,
  "SF1210",  "SF-12 Q10 Energy (SF1210)",                         10,
  "SF1211",  "SF-12 Q11 Felt Downhearted (SF1211)",               11,
  "SF1212",  "SF-12 Q12 Social Interference (SF1212)",            12,
  "SF12PF",  "SF-12 Physical Functioning Subscale (SF12PF)",      13,
  "SF12RP",  "SF-12 Role Physical Subscale (SF12RP)",             14,
  "SF12BP",  "SF-12 Bodily Pain Subscale (SF12BP)",               15,
  "SF12GH",  "SF-12 General Health Subscale (SF12GH)",            16,
  "SF12VT",  "SF-12 Vitality Subscale (SF12VT)",                  17,
  "SF12SF",  "SF-12 Social Functioning Subscale (SF12SF)",        18,
  "SF12RE",  "SF-12 Role Emotional Subscale (SF12RE)",            19,
  "SF12MH",  "SF-12 Mental Health Subscale (SF12MH)",             20
)

adqs <- qs |>
  admiral::derive_vars_dt(new_vars_prefix = "A", dtc = QSDTC) |>
  left_join(adsl_vars, by = "USUBJID") |>
  admiral::derive_vars_dy(reference_date = TRTSDT,
                          source_vars    = exprs(ADT)) |>
  mutate(
    PARAMCD = QSTESTCD,
    PARCAT1 = QSCAT,
    PARCAT2 = QSSCAT,
    AVAL    = QSSTRESN,
    AVALC   = QSSTRESC,
    ABLFL   = dplyr::if_else(!is.na(QSBLFL) & QSBLFL == "Y", "Y", NA_character_),
    AVISIT  = dplyr::if_else(ABLFL %in% "Y", "Baseline", VISIT),
    AVISITN = dplyr::if_else(ABLFL %in% "Y", 0, VISITNUM)
  ) |>
  ## Attach canonical PARAM / PARAMN by PARAMCD (1-to-1 dataset-wide).
  admiral::derive_vars_merged(
    dataset_add = param_lookup,
    by_vars     = exprs(PARAMCD),
    new_vars    = exprs(PARAM, PARAMN)
  ) |>
  admiral::derive_var_base(
    by_vars    = exprs(USUBJID, PARAMCD),
    source_var = AVAL,
    new_var    = BASE
  ) |>
  admiral::derive_var_chg() |>
  admiral::derive_var_pchg() |>
  arrange(USUBJID, PARAMCD, AVISITN, ADT) |>
  mutate(
    ANL01FL = dplyr::if_else(!is.na(PARCAT2) & PARCAT2 == "SUBSCALE" & !is.na(AVAL),
                             "Y", NA_character_),
    ASEQ    = row_number(),
    .by = USUBJID
  ) |>
  select(STUDYID, USUBJID, SUBJID, SITEID,
         AGE, SEX, RACE, TRT01P, TRT01A,
         ASEQ, PARAMCD, PARAM, PARAMN, PARCAT1, PARCAT2,
         AVAL, AVALC,
         BASE, CHG, PCHG, ABLFL,
         AVISIT, AVISITN, ADT, ADY,
         ANL01FL, EFFFL)

## --------------------------------------------------------------------
## Attach labels and dataset-level label from spec
## (Family A — resolves AD0018, AD0320, AD0503)
##
## metacore/xportr/labelled are not installed in this renv; fall back to
## yaml + base attr(). Labels carry through to XPT via haven::write_xpt
## using the label attribute on each column. See CLAUDE.md for the spec
## YAML contract.
## --------------------------------------------------------------------
spec_yaml <- yaml::read_yaml("spec/adam/adqs.yaml")

# Per-variable label
for (v in names(adqs)) {
  lab <- spec_yaml$variables[[v]]$label
  if (!is.null(lab) && nzchar(lab)) attr(adqs[[v]], "label") <- lab
}

# Dataset-level label
attr(adqs, "label") <- spec_yaml$label

saveRDS(adqs, "data/adam/adqs.rds")
cat(sprintf("ADQS written: %d rows x %d cols\n", nrow(adqs), ncol(adqs)))

## --------------------------------------------------------------------
## Export XPT v5 for P21 validation
## --------------------------------------------------------------------
adqs_xpt <- adqs
# haven::write_xpt does not support integer XPT columns; coerce to double.
int_cols <- names(adqs_xpt)[vapply(adqs_xpt, is.integer, logical(1))]
if (length(int_cols) > 0) {
  for (c in int_cols) {
    lab <- attr(adqs_xpt[[c]], "label")
    adqs_xpt[[c]] <- as.double(adqs_xpt[[c]])
    if (!is.null(lab)) attr(adqs_xpt[[c]], "label") <- lab
  }
}
haven::write_xpt(adqs_xpt, path = "data/adam/adqs.xpt", version = 5, name = "ADQS")
cat("ADQS XPT exported to data/adam/adqs.xpt\n")
