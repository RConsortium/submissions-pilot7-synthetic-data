# adam_bds.R — Derive ADVS and ADLB (BDS Analysis Datasets)
# Following admiral/CDISC ADaM conventions
# ===========================================================================

library(dplyr)

# --- Step 1: Load source data ---
vs <- read.csv("output/source/vs.csv", stringsAsFactors = FALSE)
lb <- read.csv("output/source/lb.csv", stringsAsFactors = FALSE)
adsl <- read.csv("output/adam/adsl.csv", stringsAsFactors = FALSE)
ef <- read.csv("output/source/ef.csv", stringsAsFactors = FALSE)

# ===========================================================================
# ADVS — Vital Signs (Body Weight, BMI, BP, Pulse)
# ===========================================================================

cat("=== Deriving ADVS ===\n")

# --- Step 2: Merge ADSL backbone ---
adsl_vars <- adsl |>
  select(STUDYID, USUBJID, SUBJID,
         TRT01P, TRT01PN, TRT01A, TRT01AN, ARM,
         TRTSDT, TRTEDT, SAFFL, ITTFL)

# Pivot VS to long format with PARAMCD
advs_long <- vs |>
  tidyr::pivot_longer(
    cols = c(WEIGHT, BMI, SYSBP, DIABP, PULSE),
    names_to = "PARAMCD",
    values_to = "AVAL"
  ) |>
  filter(!is.na(AVAL))

# --- Step 3: Parameter assignment ---
# REVIEW: PARAMCD mapping from ADaM spec
param_lookup <- data.frame(
  PARAMCD = c("WEIGHT", "BMI", "SYSBP", "DIABP", "PULSE"),
  PARAM = c("Body Weight (kg)", "Body Mass Index (kg/m2)",
            "Systolic Blood Pressure (mmHg)", "Diastolic Blood Pressure (mmHg)",
            "Pulse Rate (bpm)"),
  PARAMN = c(1L, 2L, 3L, 4L, 5L),
  AVALU = c("kg", "kg/m2", "mmHg", "mmHg", "bpm"),
  stringsAsFactors = FALSE
)

advs_long <- advs_long |>
  left_join(param_lookup, by = "PARAMCD")

# --- Step 4: Merge ADSL ---
advs <- advs_long |>
  left_join(adsl_vars, by = "SUBJID") |>
  mutate(TRTSDT = as.Date(TRTSDT), TRTEDT = as.Date(TRTEDT))

# --- Step 5: Date and visit variables ---
advs <- advs |>
  mutate(
    ADT = TRTSDT + as.integer(VISIT_WEEK) * 7L,
    ADY = as.integer(ADT - TRTSDT) + 1L,
    # REVIEW: Visit map from protocol schedule
    AVISIT = case_when(
      VISIT_WEEK == 0 ~ "Baseline",
      VISIT_WEEK == 58 ~ "Follow-up (Week 58)",
      TRUE ~ paste0("Week ", VISIT_WEEK)
    ),
    AVISITN = VISIT_WEEK
  )

# --- Step 6: Baseline flag (ABLFL) ---
# REVIEW: Baseline = last non-missing record on or before TRTSDT (Week 0)
advs <- advs |>
  mutate(
    ABLFL = if_else(VISIT_WEEK == 0 & !is.na(AVAL), "Y", NA_character_)
  )

# --- Step 7: BASE value ---
baseline_vals <- advs |>
  filter(ABLFL == "Y") |>
  select(SUBJID, PARAMCD, BASE = AVAL)

advs <- advs |>
  left_join(baseline_vals, by = c("SUBJID", "PARAMCD"))

# --- Step 8: CHG and PCHG ---
advs <- advs |>
  mutate(
    CHG = if_else(!is.na(BASE) & VISIT_WEEK > 0, AVAL - BASE, NA_real_),
    PCHG = if_else(!is.na(BASE) & BASE != 0 & VISIT_WEEK > 0,
                   (AVAL - BASE) / BASE * 100, NA_real_)
  )

# --- Step 9: Analysis flags ---
# REVIEW: ANL01FL — records for primary analysis (on-treatment, non-baseline)
advs <- advs |>
  mutate(
    ANL01FL = if_else(VISIT_WEEK > 0 & VISIT_WEEK <= 48 & !is.na(AVAL),
                      "Y", NA_character_),
    DTYPE = NA_character_,
    BASETYPE = "LAST"
  )

# --- Step 10: Select and write ADVS ---
advs <- advs |>
  select(
    STUDYID, USUBJID, SUBJID,
    TRT01P, TRT01PN, TRT01A, TRT01AN, ARM,
    TRTSDT, TRTEDT, SAFFL, ITTFL,
    PARAMCD, PARAM, PARAMN, AVALU,
    AVISIT, AVISITN, ADT, ADY,
    AVAL, BASE, CHG, PCHG,
    ABLFL, ANL01FL, DTYPE, BASETYPE
  )

write.csv(advs, "output/adam/advs.csv", row.names = FALSE)
cat("ADVS written:", nrow(advs), "records\n")


# ===========================================================================
# ADLB — Laboratory Values
# ===========================================================================

cat("\n=== Deriving ADLB ===\n")

# Pivot LB to long format
adlb_long <- lb |>
  tidyr::pivot_longer(
    cols = c(HBA1C, GLUC, INSULIN, CHOL, LDL, HDL, TRIG, HSCRP),
    names_to = "PARAMCD",
    values_to = "AVAL"
  ) |>
  filter(!is.na(AVAL))

# --- Parameter assignment ---
# REVIEW: PARAMCD mapping per ADaM spec
param_lookup_lb <- data.frame(
  PARAMCD = c("HBA1C", "GLUC", "INSULIN", "CHOL", "LDL", "HDL", "TRIG", "HSCRP"),
  PARAM = c("Glycated Haemoglobin (mmol/mol)", "Fasting Glucose (mmol/L)",
            "Fasting Insulin (mIU/L)", "Total Cholesterol (mmol/L)",
            "LDL Cholesterol (mmol/L)", "HDL Cholesterol (mmol/L)",
            "Triglycerides (mmol/L)", "High-sensitivity CRP (mg/L)"),
  PARAMN = 1:8,
  AVALU = c("mmol/mol", "mmol/L", "mIU/L", "mmol/L", "mmol/L", "mmol/L", "mmol/L", "mg/L"),
  stringsAsFactors = FALSE
)

adlb_long <- adlb_long |>
  left_join(param_lookup_lb, by = "PARAMCD")

# Merge ADSL
adlb <- adlb_long |>
  left_join(adsl_vars, by = "SUBJID") |>
  mutate(TRTSDT = as.Date(TRTSDT), TRTEDT = as.Date(TRTEDT))

# Date and visit
adlb <- adlb |>
  mutate(
    ADT = TRTSDT + as.integer(VISIT_WEEK) * 7L,
    ADY = as.integer(ADT - TRTSDT) + 1L,
    AVISIT = case_when(
      VISIT_WEEK == 0 ~ "Baseline",
      VISIT_WEEK == 58 ~ "Follow-up (Week 58)",
      TRUE ~ paste0("Week ", VISIT_WEEK)
    ),
    AVISITN = VISIT_WEEK
  )

# Baseline flag
adlb <- adlb |>
  mutate(ABLFL = if_else(VISIT_WEEK == 0 & !is.na(AVAL), "Y", NA_character_))

# BASE
baseline_lb <- adlb |>
  filter(ABLFL == "Y") |>
  select(SUBJID, PARAMCD, BASE = AVAL)

adlb <- adlb |>
  left_join(baseline_lb, by = c("SUBJID", "PARAMCD"))

# CHG and PCHG
adlb <- adlb |>
  mutate(
    CHG = if_else(!is.na(BASE) & VISIT_WEEK > 0, AVAL - BASE, NA_real_),
    PCHG = if_else(!is.na(BASE) & BASE != 0 & VISIT_WEEK > 0,
                   (AVAL - BASE) / BASE * 100, NA_real_)
  )

# Analysis flags
adlb <- adlb |>
  mutate(
    ANL01FL = if_else(VISIT_WEEK > 0 & VISIT_WEEK <= 48 & !is.na(AVAL),
                      "Y", NA_character_),
    DTYPE = NA_character_,
    BASETYPE = "LAST"
  )

# Select and write
adlb <- adlb |>
  select(
    STUDYID, USUBJID, SUBJID,
    TRT01P, TRT01PN, TRT01A, TRT01AN, ARM,
    TRTSDT, TRTEDT, SAFFL, ITTFL,
    PARAMCD, PARAM, PARAMN, AVALU,
    AVISIT, AVISITN, ADT, ADY,
    AVAL, BASE, CHG, PCHG,
    ABLFL, ANL01FL, DTYPE, BASETYPE
  )

write.csv(adlb, "output/adam/adlb.csv", row.names = FALSE)
cat("ADLB written:", nrow(adlb), "records\n")


cat("\n=== ADVS and ADLB generated (run adam_adeff.R separately for ADEFF) ===\n")
