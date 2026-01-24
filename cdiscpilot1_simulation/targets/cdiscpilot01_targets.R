#' =============================================================================
#' CDISC Pilot 01 Targets - Xanomeline Alzheimer's Disease Study
#' =============================================================================
#' Target values extracted from Tables 14-1.01 through 14-5.02
#' =============================================================================

# Source accuracy tier definitions
source(here::here("targets", "metadata.R"))

#' =============================================================================
#' STUDY DESIGN TARGETS
#' =============================================================================

STUDY_TARGETS <- list(
  # Total enrollment
  n_total = 254,
  n_placebo = 86,
  n_xan_low = 84,
  n_xan_high = 84,

  # Study duration
  treatment_duration_weeks = 24,
  study_duration_weeks = 26,

  # Sites (from Table 14-1.03)
  n_sites = 17,
  site_ids = c(701, 703, 704, 705, 708, 709, 710, 713, 716, 718,
               702, 706, 707, 711, 714, 715, 717)
)

#' =============================================================================
#' POPULATION TARGETS (Table 14-1.01)
#' =============================================================================

POPULATION_TARGETS <- list(
  # ITT Population
  itt_total = list(value = 254, pct = 100, tier = TIER_CRITICAL),
  itt_placebo = list(value = 86, pct = 100, tier = TIER_CRITICAL),
  itt_xan_low = list(value = 84, pct = 100, tier = TIER_CRITICAL),
  itt_xan_high = list(value = 84, pct = 100, tier = TIER_CRITICAL),

  # Safety Population
  safety_total = list(value = 254, pct = 100, tier = TIER_CRITICAL),

  # Efficacy Population
  efficacy_total = list(value = 234, pct = 92, tier = TIER_HIGH),
  efficacy_placebo = list(value = 79, pct = 92, tier = TIER_HIGH),
  efficacy_xan_low = list(value = 81, pct = 96, tier = TIER_HIGH),
  efficacy_xan_high = list(value = 74, pct = 88, tier = TIER_HIGH),

  # Completers - Week 24
  complete_wk24_total = list(value = 118, pct = 46, tier = TIER_CRITICAL),
  complete_wk24_placebo = list(value = 60, pct = 70, tier = TIER_CRITICAL),
  complete_wk24_xan_low = list(value = 28, pct = 33, tier = TIER_CRITICAL),
  complete_wk24_xan_high = list(value = 30, pct = 36, tier = TIER_CRITICAL),

  # Completers - Study
  complete_study_total = list(value = 110, pct = 43, tier = TIER_HIGH),
  complete_study_placebo = list(value = 58, pct = 67, tier = TIER_HIGH),
  complete_study_xan_low = list(value = 25, pct = 30, tier = TIER_HIGH),
  complete_study_xan_high = list(value = 27, pct = 32, tier = TIER_HIGH)
)

#' =============================================================================
#' DEMOGRAPHIC TARGETS (Table 14-2.01)
#' =============================================================================

DEMOGRAPHIC_TARGETS <- list(
  # Age
  age_mean = list(value = 75.1, sd = 8.25, tier = TIER_CRITICAL),
  age_min = list(value = 51, tier = TIER_MODERATE),
  age_max = list(value = 89, tier = TIER_MODERATE),
  age_lt65_pct = list(value = 13, tier = TIER_HIGH),
  age_65_80_pct = list(value = 57, tier = TIER_HIGH),
  age_gt80_pct = list(value = 30, tier = TIER_HIGH),

  # By treatment
  age_placebo = list(mean = 75.2, sd = 8.59, tier = TIER_CRITICAL),
  age_xan_low = list(mean = 75.7, sd = 8.29, tier = TIER_CRITICAL),
  age_xan_high = list(mean = 74.4, sd = 7.89, tier = TIER_CRITICAL),

  # Sex
  male_pct = list(value = 44, tier = TIER_CRITICAL),
  female_pct = list(value = 56, tier = TIER_CRITICAL),

  # Race
  caucasian_pct = list(value = 86, tier = TIER_CRITICAL),
  african_pct = list(value = 9, tier = TIER_HIGH),
  hispanic_pct = list(value = 5, tier = TIER_HIGH),
  other_pct = list(value = 0.4, tier = TIER_LOW),

  # MMSE (Mini-Mental State Examination)
  mmse_mean = list(value = 18.1, sd = 4.21, tier = TIER_CRITICAL),
  mmse_min = list(value = 10, tier = TIER_MODERATE),
  mmse_max = list(value = 24, tier = TIER_MODERATE),

  # Duration of disease (months)
  disease_duration_mean = list(value = 43.9, sd = 28.40, tier = TIER_HIGH),
  disease_duration_lt12mo_pct = list(value = 5, tier = TIER_MODERATE),
  disease_duration_ge12mo_pct = list(value = 95, tier = TIER_MODERATE),

  # Years of education
  education_mean = list(value = 12.8, sd = 3.38, tier = TIER_MODERATE),

  # Baseline weight (kg)
  weight_mean = list(value = 66.6, sd = 14.13, tier = TIER_HIGH),
  weight_placebo = list(mean = 62.8, sd = 12.77, tier = TIER_HIGH),
  weight_xan_low = list(mean = 67.3, sd = 14.12, tier = TIER_HIGH),
  weight_xan_high = list(mean = 70.0, sd = 14.65, tier = TIER_HIGH),

  # Baseline height (cm)
  height_mean = list(value = 163.9, sd = 10.76, tier = TIER_HIGH),

  # Baseline BMI
  bmi_mean = list(value = 24.7, sd = 4.09, tier = TIER_HIGH),
  bmi_lt25_pct = list(value = 59, tier = TIER_MODERATE),
  bmi_25_30_pct = list(value = 30, tier = TIER_MODERATE),
  bmi_ge30_pct = list(value = 11, tier = TIER_MODERATE)
)

#' =============================================================================
#' DISPOSITION TARGETS (Table 14-1.02)
#' =============================================================================

DISPOSITION_TARGETS <- list(
  # Completion Status
  completed_wk24_pct = list(
    total = 46,
    placebo = 70,
    xan_low = 33,
    xan_high = 36,
    tier = TIER_CRITICAL
  ),

  early_termination_pct = list(
    total = 54,
    placebo = 30,
    xan_low = 67,
    xan_high = 64,
    tier = TIER_CRITICAL
  ),

  # Reasons for Early Termination
  disc_ae_pct = list(
    total = 36,
    placebo = 9,
    xan_low = 52,
    xan_high = 46,
    tier = TIER_CRITICAL
  ),

  disc_death_pct = list(
    total = 1,
    placebo = 1,
    xan_low = 1,
    xan_high = 0,
    tier = TIER_LOW
  ),

  disc_lack_efficacy_pct = list(
    total = 2,
    placebo = 3,
    xan_low = 0,
    xan_high = 1,
    tier = TIER_MODERATE
  ),

  disc_lost_followup_pct = list(
    total = 0.4,
    placebo = 1,
    xan_low = 0,
    xan_high = 0,
    tier = TIER_LOW
  ),

  disc_withdrew_pct = list(
    total = 10,
    placebo = 10,
    xan_low = 10,
    xan_high = 10,
    tier = TIER_HIGH
  ),

  disc_physician_pct = list(
    total = 1,
    placebo = 1,
    xan_low = 0,
    xan_high = 2,
    tier = TIER_LOW
  ),

  disc_protocol_pct = list(
    total = 1,
    placebo = 1,
    xan_low = 0,
    xan_high = 2,
    tier = TIER_LOW
  ),

  disc_violation_pct = list(
    total = 1,
    placebo = 1,
    xan_low = 1,
    xan_high = 1,
    tier = TIER_LOW
  ),

  disc_sponsor_pct = list(
    total = 2,
    placebo = 1,
    xan_low = 2,
    xan_high = 1,
    tier = TIER_LOW
  )
)

#' =============================================================================
#' EFFICACY TARGETS (Tables 14-3.01, 14-3.02)
#' =============================================================================

EFFICACY_TARGETS <- list(
  # ADAS-Cog (11) - Primary Endpoint
  # Higher scores = worse cognition, positive change = worsening

  # Baseline ADAS-Cog
  adas_baseline = list(
    total_mean = 23.3,
    total_sd = 12.35,
    placebo_mean = 24.1,
    placebo_sd = 12.19,
    xan_low_mean = 24.4,
    xan_low_sd = 12.92,
    xan_high_mean = 21.3,
    xan_high_sd = 11.74,
    tier = TIER_CRITICAL
  ),

  # Week 24 ADAS-Cog
  adas_week24 = list(
    placebo_mean = 26.7,
    placebo_sd = 13.79,
    xan_low_mean = 26.4,
    xan_low_sd = 13.18,
    xan_high_mean = 22.8,
    xan_high_sd = 12.48,
    tier = TIER_CRITICAL
  ),

  # Change from Baseline ADAS-Cog
  adas_change = list(
    placebo_mean = 2.5,
    placebo_sd = 5.80,
    xan_low_mean = 2.0,
    xan_low_sd = 5.55,
    xan_high_mean = 1.5,
    xan_high_sd = 4.26,
    tier = TIER_CRITICAL
  ),

  # Treatment difference (LS Means)
  adas_diff_low_vs_placebo = list(value = -0.5, se = 0.82, tier = TIER_HIGH),
  adas_diff_high_vs_placebo = list(value = -1.0, se = 0.84, tier = TIER_HIGH),

  # ADAS-Cog p-values
  adas_pvalue_dose_response = list(value = 0.245, tier = TIER_MODERATE),

  # CIBIC+ (Clinician's Interview-Based Impression of Change plus caregiver input)
  # Score 1-7: 1=marked improvement, 4=no change, 7=marked worsening

  cibic_week24 = list(
    placebo_mean = 4.3,
    placebo_sd = 0.77,
    xan_low_mean = 4.2,
    xan_low_sd = 0.79,
    xan_high_mean = 4.3,
    xan_high_sd = 0.81,
    tier = TIER_HIGH
  ),

  # CIBIC+ treatment difference
  cibic_diff_low_vs_placebo = list(value = -0.1, se = 0.13, tier = TIER_MODERATE),
  cibic_diff_high_vs_placebo = list(value = 0.0, se = 0.13, tier = TIER_MODERATE),

  # CIBIC+ p-values
  cibic_pvalue_dose_response = list(value = 0.960, tier = TIER_LOW)
)

#' =============================================================================
#' EXPOSURE TARGETS (Table 14-4.01)
#' =============================================================================

EXPOSURE_TARGETS <- list(
  # Average daily dose (mg) - Safety Population
  avg_daily_dose_xan_low = list(value = 54.0, tier = TIER_CRITICAL),
  avg_daily_dose_xan_high = list(value = 71.6, sd = 8.11, tier = TIER_CRITICAL),

  # Cumulative dose at end of study (mg) - Safety Population
  cumulative_dose_xan_low = list(mean = 5347.3, sd = 3680.35, tier = TIER_HIGH),
  cumulative_dose_xan_high = list(mean = 7551.0, sd = 5531.04, tier = TIER_HIGH),

  # Cumulative dose - Completers only
  cumulative_dose_xan_low_completers = list(mean = 9918.6, sd = 603.84, tier = TIER_MODERATE),
  cumulative_dose_xan_high_completers = list(mean = 14089.5, sd = 481.01, tier = TIER_MODERATE)
)

#' =============================================================================
#' SAFETY TARGETS (Table 14-5.01)
#' =============================================================================

SAFETY_TARGETS <- list(
  # Any TEAE
  any_ae_pct = list(
    total = 85.8,
    placebo = 75.6,
    xan_low = 91.7,
    xan_high = 90.5,
    tier = TIER_CRITICAL
  ),

  # General Disorders and Administration Site Conditions
  general_disorders_pct = list(
    placebo = 24.4,
    xan_low = 56.0,
    xan_high = 47.6,
    tier = TIER_HIGH
  ),

  # Application Site Reactions (key differentiating AE for transdermal)
  app_site_pruritus_pct = list(
    placebo = 7.0,
    xan_low = 26.2,
    xan_high = 26.2,
    tier = TIER_CRITICAL
  ),

  app_site_erythema_pct = list(
    placebo = 3.5,
    xan_low = 14.3,
    xan_high = 17.9,
    tier = TIER_HIGH
  ),

  app_site_irritation_pct = list(
    placebo = 3.5,
    xan_low = 10.7,
    xan_high = 10.7,
    tier = TIER_HIGH
  ),

  app_site_dermatitis_pct = list(
    placebo = 5.8,
    xan_low = 10.7,
    xan_high = 8.3,
    tier = TIER_MODERATE
  ),

  # Skin and Subcutaneous Tissue Disorders
  skin_disorders_pct = list(
    placebo = 23.3,
    xan_low = 46.4,
    xan_high = 47.6,
    tier = TIER_CRITICAL
  ),

  pruritus_pct = list(
    placebo = 9.3,
    xan_low = 25.0,
    xan_high = 31.0,
    tier = TIER_HIGH
  ),

  erythema_pct = list(
    placebo = 9.3,
    xan_low = 16.7,
    xan_high = 16.7,
    tier = TIER_HIGH
  ),

  rash_pct = list(
    placebo = 5.8,
    xan_low = 15.5,
    xan_high = 10.7,
    tier = TIER_HIGH
  ),

  # Nervous System Disorders
  nervous_system_pct = list(
    placebo = 9.3,
    xan_low = 23.8,
    xan_high = 29.8,
    tier = TIER_HIGH
  ),

  dizziness_pct = list(
    placebo = 2.3,
    xan_low = 9.5,
    xan_high = 13.1,
    tier = TIER_HIGH
  ),

  headache_pct = list(
    placebo = 3.5,
    xan_low = 3.6,
    xan_high = 6.0,
    tier = TIER_MODERATE
  ),

  syncope_pct = list(
    placebo = 0,
    xan_low = 4.8,
    xan_high = 3.6,
    tier = TIER_MODERATE
  ),

  # Gastrointestinal Disorders
  gi_disorders_pct = list(
    placebo = 19.8,
    xan_low = 16.7,
    xan_high = 23.8,
    tier = TIER_MODERATE
  ),

  nausea_pct = list(
    placebo = 3.5,
    xan_low = 3.6,
    xan_high = 7.1,
    tier = TIER_MODERATE
  ),

  vomiting_pct = list(
    placebo = 3.5,
    xan_low = 3.6,
    xan_high = 8.3,
    tier = TIER_MODERATE
  ),

  diarrhea_pct = list(
    placebo = 10.5,
    xan_low = 4.8,
    xan_high = 4.8,
    tier = TIER_MODERATE
  ),

  # Cardiac Disorders
  cardiac_disorders_pct = list(
    placebo = 14.0,
    xan_low = 15.5,
    xan_high = 17.9,
    tier = TIER_MODERATE
  ),

  sinus_bradycardia_pct = list(
    placebo = 2.3,
    xan_low = 8.3,
    xan_high = 9.5,
    tier = TIER_LOW
  ),

  # Psychiatric Disorders
  psychiatric_disorders_pct = list(
    placebo = 11.6,
    xan_low = 11.9,
    xan_high = 9.5,
    tier = TIER_MODERATE
  ),

  # Infections
  infections_pct = list(
    placebo = 18.6,
    xan_low = 10.7,
    xan_high = 15.5,
    tier = TIER_MODERATE
  ),

  # Fatigue
  fatigue_pct = list(
    placebo = 1.2,
    xan_low = 6.0,
    xan_high = 6.0,
    tier = TIER_MODERATE
  )
)

#' =============================================================================
#' COMBINED TARGETS LIST
#' =============================================================================

CDISCPILOT01_TARGETS <- list(
  study = STUDY_TARGETS,
  population = POPULATION_TARGETS,
  demographics = DEMOGRAPHIC_TARGETS,
  disposition = DISPOSITION_TARGETS,
  efficacy = EFFICACY_TARGETS,
  exposure = EXPOSURE_TARGETS,
  safety = SAFETY_TARGETS
)
