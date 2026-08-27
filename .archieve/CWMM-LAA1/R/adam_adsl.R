# adam_adsl.R — Derive ADSL (Subject-Level Analysis Dataset)
# Following admiral/CDISC ADaM conventions
# ===========================================================================

library(dplyr)

# --- Step 1: Load source SDTM-like domains ---
dm <- read.csv("output/source/dm.csv", stringsAsFactors = FALSE)
ex <- read.csv("output/source/ex.csv", stringsAsFactors = FALSE)
ds <- read.csv("output/source/ds.csv", stringsAsFactors = FALSE)
vs <- read.csv("output/source/vs.csv", stringsAsFactors = FALSE)
lb <- read.csv("output/source/lb.csv", stringsAsFactors = FALSE)

# Confirm one record per SUBJID in DM
stopifnot(nrow(dm) == n_distinct(dm$SUBJID))

# --- Step 2: Subject spine ---
adsl <- dm |>
  mutate(
    STUDYID = "CWMM-LAA1",
    USUBJID = paste0("CWMM-LAA1-", SUBJID),
    SUBJID = SUBJID,
    SITEID = sprintf("SITE-%02d", as.integer(factor(COUNTRY)))
  )

# --- Step 3: Treatment variables (TRT01P, TRT01PN, TRT01A, TRT01AN) ---
# REVIEW: Confirm ARMCD values and numeric codes against randomisation schedule
arm_lookup <- data.frame(
 ARM = c("Placebo", "1mg", "3mg", "6mg", "9mg", "6to9mg", "3to9mg"),
  TRT01P = c("Placebo", "Eloralintide 1 mg", "Eloralintide 3 mg",
             "Eloralintide 6 mg", "Eloralintide 9 mg",
             "Eloralintide 6-9 mg", "Eloralintide 3-9 mg"),
  TRT01PN = c(1L, 2L, 3L, 4L, 5L, 6L, 7L),
  stringsAsFactors = FALSE
)

adsl <- adsl |>
  left_join(arm_lookup, by = "ARM") |>
  mutate(
    TRT01A = TRT01P,
    TRT01AN = TRT01PN,
    ARMCD = ARM
  )

# --- Step 4: Treatment dates (TRTSDT, TRTEDT) ---
adsl <- adsl |>
  mutate(
    TRTSDT = as.Date(RFSTDTC),
    RFSTDTC_chr = as.character(RFSTDTC)
  )

# Derive TRTEDT from EX (last dosing date per subject)
ex_last <- ex |>
  group_by(SUBJID) |>
  summarise(
    TRTEDT_WEEK = max(VISIT_WEEK, na.rm = TRUE),
    .groups = "drop"
  )

adsl <- adsl |>
  left_join(ex_last, by = "SUBJID") |>
  mutate(
    TRTEDT = TRTSDT + TRTEDT_WEEK * 7,
    TRTDURD = as.integer(TRTEDT - TRTSDT) + 1L
  )

# --- Step 5: Disposition (EOSSTT, DCSREAS) ---
adsl <- adsl |>
  left_join(
    ds |> select(SUBJID, TX_DISC, TX_DISC_WEEK, TX_DISC_REASON, STUDY_DISC, STUDY_DISC_WEEK),
    by = "SUBJID"
  ) |>
  mutate(
    # REVIEW: EOSSTT categorisation — "COMPLETED" or "DISCONTINUED"
    EOSSTT = if_else(STUDY_DISC, "DISCONTINUED", "COMPLETED"),
    DCSREAS = if_else(STUDY_DISC, coalesce(TX_DISC_REASON, "OTHER"), NA_character_),
    EOSDT = if_else(STUDY_DISC, TRTSDT + as.integer(STUDY_DISC_WEEK) * 7L,
                    TRTSDT + 48L * 7L)
  )

# --- Step 6: Baseline demographics ---
# Height from DM
adsl <- adsl |>
  rename(HEIGHTBL = HEIGHT)

# Baseline weight from VS at Week 0
bl_vs <- vs |>
  filter(VISIT_WEEK == 0) |>
  select(SUBJID, WEIGHTBL = WEIGHT, BMIBL = BMI)

adsl <- adsl |>
  left_join(bl_vs, by = "SUBJID")

# Baseline labs
bl_lb <- lb |>
  filter(VISIT_WEEK == 0) |>
  select(SUBJID, HBA1CBL = HBA1C, GLUCBL = GLUC, INSULBL = INSULIN,
         CHOLBL = CHOL, LDLBL = LDL, HDLBL = HDL, TRIGBL = TRIG, HSCRPBL = HSCRP)

adsl <- adsl |>
  left_join(bl_lb, by = "SUBJID")

# Baseline vitals
bl_vitals <- vs |>
  filter(VISIT_WEEK == 0) |>
  select(SUBJID, SYSBPBL = SYSBP, DIABPBL = DIABP, PULSEBL = PULSE)

adsl <- adsl |>
  left_join(bl_vitals, by = "SUBJID")

# --- Step 7: Age grouping ---
# REVIEW: Age cut-points per ADaM spec
adsl <- adsl |>
  mutate(
    AGEGR1 = case_when(
      AGE < 40 ~ "<40",
      AGE >= 40 & AGE < 65 ~ "40-64",
      AGE >= 65 ~ ">=65"
    ),
    AGEGR1N = case_when(
      AGEGR1 == "<40" ~ 1L,
      AGEGR1 == "40-64" ~ 2L,
      AGEGR1 == ">=65" ~ 3L
    )
  )

# --- Step 8: Population flags ---
# REVIEW: SAFFL = received at least one dose. Flag is "Y" or NA, never "N"
subj_with_dose <- unique(ex$SUBJID)

adsl <- adsl |>
  mutate(
    SAFFL = if_else(SUBJID %in% subj_with_dose, "Y", NA_character_),
    ITTFL = "Y",  # All randomised subjects
    # REVIEW: Per-protocol flag — no major protocol deviations
    PPROTFL = if_else(!TX_DISC | TX_DISC_WEEK >= 36, "Y", NA_character_)
  )

# --- Step 9: BMI category ---
adsl <- adsl |>
  mutate(
    BMICAT = case_when(
      BMIBL < 30 ~ "<30",
      BMIBL >= 30 & BMIBL < 35 ~ "30 to <35",
      BMIBL >= 35 & BMIBL < 40 ~ "35 to <40",
      BMIBL >= 40 ~ ">=40"
    )
  )

# --- Step 10: Select and order final variables ---
adsl <- adsl |>
  select(
    STUDYID, USUBJID, SUBJID, SITEID,
    ARM, ARMCD, TRT01P, TRT01PN, TRT01A, TRT01AN,
    AGE, AGEGR1, AGEGR1N, SEX, RACE, COUNTRY,
    HEIGHTBL, WEIGHTBL, BMIBL, BMICAT, BMI_STRAT,
    SYSBPBL, DIABPBL, PULSEBL,
    HBA1CBL, GLUCBL, INSULBL, CHOLBL, LDLBL, HDLBL, TRIGBL, HSCRPBL,
    TRTSDT, TRTEDT, TRTDURD,
    EOSSTT, DCSREAS, EOSDT,
    SAFFL, ITTFL, PPROTFL
  )

# --- Final assertion ---
stopifnot(nrow(adsl) == n_distinct(adsl$USUBJID))

# --- Write output ---
write.csv(adsl, "output/adam/adsl.csv", row.names = FALSE)
cat("ADSL written:", nrow(adsl), "subjects\n")
