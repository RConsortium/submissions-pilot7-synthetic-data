#' =============================================================================
#' CDISC Pilot 01 Simulator Configuration
#' Xanomeline Transdermal Therapeutic System in Alzheimer's Disease
#' =============================================================================

# Load targets
source(here::here("targets", "cdiscpilot01_targets.R"))

# Global simulation settings
SIM_CONFIG <- list(
  seed = 20060626,  # Date from source SAS programs
  study_start_date = as.Date("2013-01-01"),
  data_cutoff_date = as.Date("2014-01-15"),
  study_id = "CDISCPILOT01",

  # Sample sizes (from targets)
  n_total = CDISCPILOT01_TARGETS$study$n_total,
  n_placebo = CDISCPILOT01_TARGETS$study$n_placebo,
  n_xan_low = CDISCPILOT01_TARGETS$study$n_xan_low,
  n_xan_high = CDISCPILOT01_TARGETS$study$n_xan_high,

  # Treatment arms
  treatment_arms = c("Placebo", "Xanomeline Low Dose", "Xanomeline High Dose"),
  treatment_codes = c(0, 1, 2),

  # Study design
  treatment_duration_weeks = 24,
  study_duration_weeks = 26,
  n_sites = CDISCPILOT01_TARGETS$study$n_sites,
  site_ids = CDISCPILOT01_TARGETS$study$site_ids,

  # Dosing - Transdermal patches
  # Low dose: 50 cm² patch = 54 mg/day
  # High dose: 75 cm² patch = 81 mg/day (average ~77 due to early discontinuation)
  dose_low_mg = 54,
  dose_high_mg = 81,

  # Visit schedule (weeks)
  # Screening, Baseline, Week 2, 4, 6, 8, 12, 16, 20, 24, 26
  visit_weeks = c(-2, 0, 2, 4, 6, 8, 12, 16, 20, 24, 26),
  visit_names = c("SCREENING", "BASELINE", "WEEK 2", "WEEK 4", "WEEK 6",
                  "WEEK 8", "WEEK 12", "WEEK 16", "WEEK 20", "WEEK 24", "WEEK 26"),

  # Efficacy assessment timepoints (ADAS-Cog, CIBIC+)
  efficacy_weeks = c(0, 4, 8, 12, 24),

  # Demographics targets
  age_mean = 75.1,
  age_sd = 8.25,
  age_min = 51,
  age_max = 89,
  female_pct = 0.56,

  # Race distribution
  race_probs = c(
    "WHITE" = 0.86,
    "BLACK OR AFRICAN AMERICAN" = 0.09,
    "HISPANIC OR LATINO" = 0.05,
    "OTHER" = 0.004
  ),

  # MMSE at baseline (eligibility: 10-23 for mild-moderate AD)
  mmse_mean = 18.1,
  mmse_sd = 4.21,
  mmse_min = 10,
  mmse_max = 24,

  # Disease duration (months since first definite symptoms)
  disease_duration_mean = 43.9,
  disease_duration_sd = 28.40,

  # Education (years)
  education_mean = 12.8,
  education_sd = 3.38,

  # Weight (kg)
  weight_mean = 66.6,
  weight_sd = 14.13,

  # Height (cm)
  height_mean = 163.9,
  height_sd = 10.76,

  # Completion rates by treatment (probability of completing Week 24)
  completion_prob = c(
    "Placebo" = 0.70,
    "Xanomeline Low Dose" = 0.33,
    "Xanomeline High Dose" = 0.36
  ),

  # Discontinuation reasons (among those who discontinue)
  disc_reason_probs = list(
    "Placebo" = c(
      "ADVERSE EVENT" = 0.31,           # 8/26
      "DEATH" = 0.04,                   # 1/26
      "LACK OF EFFICACY" = 0.12,        # 3/26
      "LOST TO FOLLOW-UP" = 0.04,       # 1/26
      "WITHDREW CONSENT" = 0.35,        # 9/26
      "PHYSICIAN DECISION" = 0.04,      # 1/26
      "PROTOCOL CRITERIA NOT MET" = 0.04, # 1/26
      "PROTOCOL VIOLATION" = 0.04,      # 1/26
      "SPONSOR DECISION" = 0.04         # 1/26
    ),
    "Xanomeline Low Dose" = c(
      "ADVERSE EVENT" = 0.79,           # 44/56
      "DEATH" = 0.02,                   # 1/56
      "LACK OF EFFICACY" = 0.00,        # 0/56
      "LOST TO FOLLOW-UP" = 0.00,       # 0/56
      "WITHDREW CONSENT" = 0.14,        # 8/56
      "PHYSICIAN DECISION" = 0.00,      # 0/56
      "PROTOCOL CRITERIA NOT MET" = 0.00, # 0/56
      "PROTOCOL VIOLATION" = 0.02,      # 1/56
      "SPONSOR DECISION" = 0.04         # 2/56
    ),
    "Xanomeline High Dose" = c(
      "ADVERSE EVENT" = 0.72,           # 39/54
      "DEATH" = 0.00,                   # 0/54
      "LACK OF EFFICACY" = 0.02,        # 1/54
      "LOST TO FOLLOW-UP" = 0.00,       # 0/54
      "WITHDREW CONSENT" = 0.15,        # 8/54
      "PHYSICIAN DECISION" = 0.04,      # 2/54
      "PROTOCOL CRITERIA NOT MET" = 0.04, # 2/54
      "PROTOCOL VIOLATION" = 0.02,      # 1/54
      "SPONSOR DECISION" = 0.02         # 1/54
    )
  ),

  # ADAS-Cog parameters
  adas_baseline_mean = list(
    "Placebo" = 24.1,
    "Xanomeline Low Dose" = 24.4,
    "Xanomeline High Dose" = 21.3
  ),
  adas_baseline_sd = list(
    "Placebo" = 12.19,
    "Xanomeline Low Dose" = 12.92,
    "Xanomeline High Dose" = 11.74
  ),
  adas_change_mean = list(
    "Placebo" = 2.5,
    "Xanomeline Low Dose" = 2.0,
    "Xanomeline High Dose" = 1.5
  ),
  adas_change_sd = list(
    "Placebo" = 5.80,
    "Xanomeline Low Dose" = 5.55,
    "Xanomeline High Dose" = 4.26
  ),

  # CIBIC+ parameters (1-7 scale)
  cibic_week24_mean = list(
    "Placebo" = 4.3,
    "Xanomeline Low Dose" = 4.2,
    "Xanomeline High Dose" = 4.3
  ),
  cibic_week24_sd = list(
    "Placebo" = 0.77,
    "Xanomeline Low Dose" = 0.79,
    "Xanomeline High Dose" = 0.81
  )
)

#' Initialize simulation with seed
init_simulation <- function(seed = SIM_CONFIG$seed) {
  set.seed(seed)
  message(sprintf("Simulation initialized with seed: %d", seed))
}
