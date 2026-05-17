## --------------------------------------------------------------------
## ADLB — Laboratory Analysis Dataset (BDS)
## Spec:   spec/adam/adlb.yaml
## Inputs: data/sdtm/lb.rds, data/adam/adsl.rds
## Output: data/adam/adlb.rds
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

saveRDS(adlb, "data/adam/adlb.rds")
cat(sprintf("ADLB written: %d rows x %d cols\n", nrow(adlb), ncol(adlb)))
