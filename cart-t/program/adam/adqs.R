## --------------------------------------------------------------------
## ADQS — Questionnaire (SF-12) Analysis Dataset (BDS)
## Spec:   spec/adam/adqs.yaml
## Inputs: data/sdtm/qs.rds, data/adam/adsl.rds
## Output: data/adam/adqs.rds
## --------------------------------------------------------------------

library(dplyr)
library(tidyr)
library(admiral)

qs   <- readRDS("data/sdtm/qs.rds")   |> admiral::convert_blanks_to_na()
adsl <- readRDS("data/adam/adsl.rds") |> admiral::convert_blanks_to_na()

adsl_vars <- adsl |>
  select(USUBJID, SUBJID, SITEID, AGE, SEX, RACE,
         TRT01P, TRT01A, TRTSDT, EFFFL)

adqs <- qs |>
  admiral::derive_vars_dt(new_vars_prefix = "A", dtc = QSDTC) |>
  left_join(adsl_vars, by = "USUBJID") |>
  admiral::derive_vars_dy(reference_date = TRTSDT,
                          source_vars    = exprs(ADT)) |>
  mutate(
    PARAMCD = QSTESTCD,
    PARAM   = QSTEST,
    PARCAT1 = QSCAT,
    PARCAT2 = QSSCAT,
    AVAL    = QSSTRESN,
    AVALC   = QSSTRESC,
    ABLFL   = dplyr::if_else(!is.na(QSBLFL) & QSBLFL == "Y", "Y", NA_character_),
    AVISIT  = dplyr::if_else(ABLFL %in% "Y", "Baseline", VISIT),
    AVISITN = dplyr::if_else(ABLFL %in% "Y", 0, VISITNUM)
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
    PARAMN  = dplyr::dense_rank(PARAMCD),
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

saveRDS(adqs, "data/adam/adqs.rds")
cat(sprintf("ADQS written: %d rows x %d cols\n", nrow(adqs), ncol(adqs)))
