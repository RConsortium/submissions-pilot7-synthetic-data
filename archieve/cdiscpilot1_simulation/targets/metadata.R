#' =============================================================================
#' CDISC Pilot 01 Target Metadata
#' Xanomeline TTS in Alzheimer's Disease
#' =============================================================================
#' Defines target outputs and their accuracy requirements for scoring
#'
#' Accuracy Tiers:
#'   - CRITICAL: Must match closely (±5%) - demographics, primary efficacy
#'   - HIGH:     Should match well (±10%) - key secondary endpoints, disposition
#'   - MODERATE: Reasonable match (±20%) - safety, specific AEs
#'   - LOW:      Directional match (±30%) - rare events, subgroups
#' =============================================================================

# Define tier constants
TIER_CRITICAL <- "CRITICAL"
TIER_HIGH <- "HIGH"
TIER_MODERATE <- "MODERATE"
TIER_LOW <- "LOW"

#' Target categories with accuracy requirements
TARGET_METADATA <- list(

  # ---------------------------------------------------------------------------
  # DEMOGRAPHICS - CRITICAL accuracy expected
  # ---------------------------------------------------------------------------
  demographics = list(
    tier = "CRITICAL",
    tolerance = 0.05,
    description = "Baseline demographics must closely match published Table 14-2.01",
    targets = c(
      "age_mean", "age_sd", "age_lt65_pct", "age_65_80_pct", "age_gt80_pct",
      "male_pct", "female_pct",
      "caucasian_pct", "african_pct",
      "mmse_mean", "mmse_sd"
    )
  ),

  # ---------------------------------------------------------------------------
  # PRIMARY EFFICACY - CRITICAL accuracy expected
  # ---------------------------------------------------------------------------
  primary_efficacy = list(
    tier = "CRITICAL",
    tolerance = 0.05,
    description = "Primary endpoint (ADAS-Cog) must match published results",
    targets = c(
      "adas_baseline_placebo_mean", "adas_baseline_xan_low_mean", "adas_baseline_xan_high_mean",
      "adas_week24_placebo_mean", "adas_week24_xan_low_mean", "adas_week24_xan_high_mean",
      "adas_change_placebo_mean", "adas_change_xan_low_mean", "adas_change_xan_high_mean"
    )
  ),

  # ---------------------------------------------------------------------------
  # SECONDARY EFFICACY - HIGH accuracy expected
  # ---------------------------------------------------------------------------
  secondary_efficacy = list(
    tier = "HIGH",
    tolerance = 0.10,
    description = "Secondary endpoints (CIBIC+) should match reasonably well",
    targets = c(
      "cibic_week24_placebo_mean", "cibic_week24_xan_low_mean", "cibic_week24_xan_high_mean"
    )
  ),

  # ---------------------------------------------------------------------------
  # DISPOSITION - CRITICAL accuracy expected
  # ---------------------------------------------------------------------------
  disposition = list(
    tier = "CRITICAL",
    tolerance = 0.05,
    description = "Study completion/discontinuation rates",
    targets = c(
      "completed_wk24_placebo_pct", "completed_wk24_xan_low_pct", "completed_wk24_xan_high_pct",
      "disc_ae_placebo_pct", "disc_ae_xan_low_pct", "disc_ae_xan_high_pct"
    )
  ),

  # ---------------------------------------------------------------------------
  # SAFETY OVERALL - MODERATE accuracy expected
  # ---------------------------------------------------------------------------
  safety_overall = list(
    tier = "MODERATE",
    tolerance = 0.20,
    description = "Overall safety rates should be in reasonable range",
    targets = c(
      "any_ae_placebo_pct", "any_ae_xan_low_pct", "any_ae_xan_high_pct"
    )
  ),

  # ---------------------------------------------------------------------------
  # APPLICATION SITE AEs - CRITICAL for transdermal study
  # ---------------------------------------------------------------------------
  safety_app_site = list(
    tier = "CRITICAL",
    tolerance = 0.10,
    description = "Application site reactions are key tolerability endpoints",
    targets = c(
      "app_site_pruritus_placebo_pct", "app_site_pruritus_xan_low_pct", "app_site_pruritus_xan_high_pct",
      "app_site_erythema_placebo_pct", "app_site_erythema_xan_low_pct", "app_site_erythema_xan_high_pct"
    )
  ),

  # ---------------------------------------------------------------------------
  # SKIN AEs - HIGH accuracy expected
  # ---------------------------------------------------------------------------
  safety_skin = list(
    tier = "HIGH",
    tolerance = 0.15,
    description = "Dermatological adverse events",
    targets = c(
      "pruritus_placebo_pct", "pruritus_xan_low_pct", "pruritus_xan_high_pct",
      "erythema_placebo_pct", "erythema_xan_low_pct", "erythema_xan_high_pct",
      "rash_placebo_pct", "rash_xan_low_pct", "rash_xan_high_pct"
    )
  ),

  # ---------------------------------------------------------------------------
  # NEUROLOGICAL/CARDIAC AEs - MODERATE accuracy expected
  # ---------------------------------------------------------------------------
  safety_other = list(
    tier = "MODERATE",
    tolerance = 0.20,
    description = "Other adverse events",
    targets = c(
      "dizziness_placebo_pct", "dizziness_xan_low_pct", "dizziness_xan_high_pct",
      "nausea_placebo_pct", "nausea_xan_low_pct", "nausea_xan_high_pct",
      "syncope_placebo_pct", "syncope_xan_low_pct", "syncope_xan_high_pct",
      "sinus_bradycardia_placebo_pct", "sinus_bradycardia_xan_low_pct", "sinus_bradycardia_xan_high_pct"
    )
  ),

  # ---------------------------------------------------------------------------
  # EXPOSURE - HIGH accuracy expected
  # ---------------------------------------------------------------------------
  exposure = list(
    tier = "HIGH",
    tolerance = 0.10,
    description = "Treatment exposure should match protocol",
    targets = c(
      "avg_daily_dose_xan_low", "avg_daily_dose_xan_high",
      "cumulative_dose_xan_low_mean", "cumulative_dose_xan_high_mean"
    )
  )
)

#' Get tolerance for a specific target
#' @param target_name Name of the target metric
#' @return Numeric tolerance value
get_target_tolerance <- function(target_name) {
  for (category in names(TARGET_METADATA)) {
    if (target_name %in% TARGET_METADATA[[category]]$targets) {
      return(TARGET_METADATA[[category]]$tolerance)
    }
  }
  return(0.20)  # Default moderate tolerance
}

#' Get tier for a specific target
#' @param target_name Name of the target metric
#' @return Character tier name
get_target_tier <- function(target_name) {
  for (category in names(TARGET_METADATA)) {
    if (target_name %in% TARGET_METADATA[[category]]$targets) {
      return(TARGET_METADATA[[category]]$tier)
    }
  }
  return("MODERATE")
}

#' Get all targets by tier
#' @param tier Tier name (CRITICAL, HIGH, MODERATE, LOW)
#' @return Character vector of target names
get_targets_by_tier <- function(tier) {
  targets <- c()
  for (category in names(TARGET_METADATA)) {
    if (TARGET_METADATA[[category]]$tier == tier) {
      targets <- c(targets, TARGET_METADATA[[category]]$targets)
    }
  }
  targets
}

#' Get flat list of all targets with their values
#' @return Named list of target values
get_flat_targets <- function() {
  source(here::here("targets", "cdiscpilot01_targets.R"))

  targets <- list()

  # Demographics
  targets$age_mean <- DEMOGRAPHIC_TARGETS$age_mean$value
  targets$age_sd <- DEMOGRAPHIC_TARGETS$age_mean$sd
  targets$age_lt65_pct <- DEMOGRAPHIC_TARGETS$age_lt65_pct$value / 100
  targets$age_65_80_pct <- DEMOGRAPHIC_TARGETS$age_65_80_pct$value / 100
  targets$age_gt80_pct <- DEMOGRAPHIC_TARGETS$age_gt80_pct$value / 100
  targets$male_pct <- DEMOGRAPHIC_TARGETS$male_pct$value / 100
  targets$female_pct <- DEMOGRAPHIC_TARGETS$female_pct$value / 100
  targets$caucasian_pct <- DEMOGRAPHIC_TARGETS$caucasian_pct$value / 100
  targets$african_pct <- DEMOGRAPHIC_TARGETS$african_pct$value / 100
  targets$mmse_mean <- DEMOGRAPHIC_TARGETS$mmse_mean$value
  targets$mmse_sd <- DEMOGRAPHIC_TARGETS$mmse_mean$sd

  # Efficacy - ADAS-Cog
  targets$adas_baseline_placebo_mean <- EFFICACY_TARGETS$adas_baseline$placebo_mean
  targets$adas_baseline_xan_low_mean <- EFFICACY_TARGETS$adas_baseline$xan_low_mean
  targets$adas_baseline_xan_high_mean <- EFFICACY_TARGETS$adas_baseline$xan_high_mean
  targets$adas_week24_placebo_mean <- EFFICACY_TARGETS$adas_week24$placebo_mean
  targets$adas_week24_xan_low_mean <- EFFICACY_TARGETS$adas_week24$xan_low_mean
  targets$adas_week24_xan_high_mean <- EFFICACY_TARGETS$adas_week24$xan_high_mean
  targets$adas_change_placebo_mean <- EFFICACY_TARGETS$adas_change$placebo_mean
  targets$adas_change_xan_low_mean <- EFFICACY_TARGETS$adas_change$xan_low_mean
  targets$adas_change_xan_high_mean <- EFFICACY_TARGETS$adas_change$xan_high_mean

  # Efficacy - CIBIC+
  targets$cibic_week24_placebo_mean <- EFFICACY_TARGETS$cibic_week24$placebo_mean
  targets$cibic_week24_xan_low_mean <- EFFICACY_TARGETS$cibic_week24$xan_low_mean
  targets$cibic_week24_xan_high_mean <- EFFICACY_TARGETS$cibic_week24$xan_high_mean

  # Disposition
  targets$completed_wk24_placebo_pct <- DISPOSITION_TARGETS$completed_wk24_pct$placebo / 100
  targets$completed_wk24_xan_low_pct <- DISPOSITION_TARGETS$completed_wk24_pct$xan_low / 100
  targets$completed_wk24_xan_high_pct <- DISPOSITION_TARGETS$completed_wk24_pct$xan_high / 100
  targets$disc_ae_placebo_pct <- DISPOSITION_TARGETS$disc_ae_pct$placebo / 100
  targets$disc_ae_xan_low_pct <- DISPOSITION_TARGETS$disc_ae_pct$xan_low / 100
  targets$disc_ae_xan_high_pct <- DISPOSITION_TARGETS$disc_ae_pct$xan_high / 100

  # Safety - Overall
  targets$any_ae_placebo_pct <- SAFETY_TARGETS$any_ae_pct$placebo / 100
  targets$any_ae_xan_low_pct <- SAFETY_TARGETS$any_ae_pct$xan_low / 100
  targets$any_ae_xan_high_pct <- SAFETY_TARGETS$any_ae_pct$xan_high / 100

  # Safety - Application site
  targets$app_site_pruritus_placebo_pct <- SAFETY_TARGETS$app_site_pruritus_pct$placebo / 100
  targets$app_site_pruritus_xan_low_pct <- SAFETY_TARGETS$app_site_pruritus_pct$xan_low / 100
  targets$app_site_pruritus_xan_high_pct <- SAFETY_TARGETS$app_site_pruritus_pct$xan_high / 100
  targets$app_site_erythema_placebo_pct <- SAFETY_TARGETS$app_site_erythema_pct$placebo / 100
  targets$app_site_erythema_xan_low_pct <- SAFETY_TARGETS$app_site_erythema_pct$xan_low / 100
  targets$app_site_erythema_xan_high_pct <- SAFETY_TARGETS$app_site_erythema_pct$xan_high / 100

  # Safety - Skin
  targets$pruritus_placebo_pct <- SAFETY_TARGETS$pruritus_pct$placebo / 100
  targets$pruritus_xan_low_pct <- SAFETY_TARGETS$pruritus_pct$xan_low / 100
  targets$pruritus_xan_high_pct <- SAFETY_TARGETS$pruritus_pct$xan_high / 100
  targets$erythema_placebo_pct <- SAFETY_TARGETS$erythema_pct$placebo / 100
  targets$erythema_xan_low_pct <- SAFETY_TARGETS$erythema_pct$xan_low / 100
  targets$erythema_xan_high_pct <- SAFETY_TARGETS$erythema_pct$xan_high / 100
  targets$rash_placebo_pct <- SAFETY_TARGETS$rash_pct$placebo / 100
  targets$rash_xan_low_pct <- SAFETY_TARGETS$rash_pct$xan_low / 100
  targets$rash_xan_high_pct <- SAFETY_TARGETS$rash_pct$xan_high / 100

  # Safety - Other
  targets$dizziness_placebo_pct <- SAFETY_TARGETS$dizziness_pct$placebo / 100
  targets$dizziness_xan_low_pct <- SAFETY_TARGETS$dizziness_pct$xan_low / 100
  targets$dizziness_xan_high_pct <- SAFETY_TARGETS$dizziness_pct$xan_high / 100
  targets$nausea_placebo_pct <- SAFETY_TARGETS$nausea_pct$placebo / 100
  targets$nausea_xan_low_pct <- SAFETY_TARGETS$nausea_pct$xan_low / 100
  targets$nausea_xan_high_pct <- SAFETY_TARGETS$nausea_pct$xan_high / 100
  targets$syncope_placebo_pct <- SAFETY_TARGETS$syncope_pct$placebo / 100
  targets$syncope_xan_low_pct <- SAFETY_TARGETS$syncope_pct$xan_low / 100
  targets$syncope_xan_high_pct <- SAFETY_TARGETS$syncope_pct$xan_high / 100
  targets$sinus_bradycardia_placebo_pct <- SAFETY_TARGETS$sinus_bradycardia_pct$placebo / 100
  targets$sinus_bradycardia_xan_low_pct <- SAFETY_TARGETS$sinus_bradycardia_pct$xan_low / 100
  targets$sinus_bradycardia_xan_high_pct <- SAFETY_TARGETS$sinus_bradycardia_pct$xan_high / 100

  # Exposure
  targets$avg_daily_dose_xan_low <- EXPOSURE_TARGETS$avg_daily_dose_xan_low$value
  targets$avg_daily_dose_xan_high <- EXPOSURE_TARGETS$avg_daily_dose_xan_high$value
  targets$cumulative_dose_xan_low_mean <- EXPOSURE_TARGETS$cumulative_dose_xan_low$mean
  targets$cumulative_dose_xan_high_mean <- EXPOSURE_TARGETS$cumulative_dose_xan_high$mean

  targets
}
