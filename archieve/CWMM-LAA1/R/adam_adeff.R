# adam_adeff.R — Derive ADEFF (Efficacy Analysis Dataset)
library(dplyr)

adsl <- read.csv("output/adam/adsl.csv", stringsAsFactors = FALSE)
ef <- read.csv("output/source/ef.csv", stringsAsFactors = FALSE)

adsl_vars <- adsl |>
  select(STUDYID, USUBJID, SUBJID,
         TRT01P, TRT01PN, TRT01A, TRT01AN,
         TRTSDT, TRTEDT, SAFFL, ITTFL)

adeff <- ef |>
  left_join(adsl_vars, by = "SUBJID") |>
  mutate(
    PARAMCD = "PCHGBW",
    PARAM = "Percent Change in Body Weight from Baseline (%)",
    PARAMN = 1L,
    AVALU = "%",
    AVAL = PCT_CHANGE_48,
    AVISIT = "Week 48",
    AVISITN = 48L,
    BASE = WEIGHT_0,
    CHG = ABS_CHANGE_48,
    PCHG = PCT_CHANGE_48,
    ANL01FL = if_else(!is.na(AVAL), "Y", NA_character_),
    CRIT1 = ">=5% Weight Loss",
    CRIT1FL = if_else(AVAL <= -5, "Y", NA_character_),
    CRIT2 = ">=10% Weight Loss",
    CRIT2FL = if_else(AVAL <= -10, "Y", NA_character_),
    CRIT3 = ">=15% Weight Loss",
    CRIT3FL = if_else(AVAL <= -15, "Y", NA_character_),
    CRIT4 = ">=20% Weight Loss",
    CRIT4FL = if_else(AVAL <= -20, "Y", NA_character_)
  ) |>
  select(
    STUDYID, USUBJID, SUBJID,
    TRT01P, TRT01PN, TRT01A, TRT01AN, ARM,
    TRTSDT, TRTEDT, SAFFL, ITTFL,
    PARAMCD, PARAM, PARAMN, AVALU,
    AVISIT, AVISITN, AVAL, BASE, CHG, PCHG,
    ANL01FL, CRIT1, CRIT1FL, CRIT2, CRIT2FL, CRIT3, CRIT3FL, CRIT4, CRIT4FL
  )

write.csv(adeff, "output/adam/adeff.csv", row.names = FALSE)
cat("ADEFF written:", nrow(adeff), "records\n")
