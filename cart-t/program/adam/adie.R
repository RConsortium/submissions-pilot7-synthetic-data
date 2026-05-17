## --------------------------------------------------------------------
## ADIE — Inclusion/Exclusion Not Met Analysis Dataset (OCCDS)
## Spec:   spec/adam/adie.yaml
## Inputs: data/sdtm/ie.rds, data/adam/adsl.rds
## Output: data/adam/adie.rds
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
    AVISIT     = VISIT,
    SCRNFAILFL = dplyr::if_else(is.na(RANDFL), "Y", NA_character_)
  ) |>
  arrange(USUBJID, IESEQ) |>
  select(STUDYID, USUBJID, SUBJID, SITEID,
         AGE, SEX, RACE, STRAT1, TRT01P,
         IESEQ, IETESTCD, IETEST, IECAT, IESCAT, IEORRES,
         ADT, ADY, AVISIT,
         SCRNFAILFL)

saveRDS(adie, "data/adam/adie.rds")
cat(sprintf("ADIE written: %d rows x %d cols\n", nrow(adie), ncol(adie)))
