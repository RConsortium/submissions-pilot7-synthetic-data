#' =============================================================================
#' CDISC Pilot 01 Scorer - Calculate Metrics from Simulated Data
#' Xanomeline TTS in Alzheimer's Disease
#' =============================================================================

#' Calculate all metrics from ADaM datasets
#' @param adam List of ADaM datasets
#' @return Named list of calculated metrics
calculate_metrics <- function(adam) {

  metrics <- list()
  adsl <- adam$adsl
  adqs <- adam$adqs
  adae <- adam$adae

  n_total <- nrow(adsl)
  n_placebo <- sum(adsl$TRT01PN == 0)
  n_xan_low <- sum(adsl$TRT01PN == 1)
  n_xan_high <- sum(adsl$TRT01PN == 2)

  message(sprintf("    N total: %d, Placebo: %d, Xan Low: %d, Xan High: %d",
                  n_total, n_placebo, n_xan_low, n_xan_high))

  # ===========================================================================
  # DEMOGRAPHICS
  # ===========================================================================
  message("  Calculating demographics metrics...")

  metrics$age_mean <- mean(adsl$AGE)
  metrics$age_sd <- sd(adsl$AGE)
  metrics$age_lt65_pct <- mean(adsl$AGE < 65)
  metrics$age_65_80_pct <- mean(adsl$AGE >= 65 & adsl$AGE <= 80)
  metrics$age_gt80_pct <- mean(adsl$AGE > 80)

  metrics$male_pct <- mean(adsl$SEX == "M")
  metrics$female_pct <- mean(adsl$SEX == "F")

  metrics$caucasian_pct <- mean(adsl$RACE == "WHITE")
  metrics$african_pct <- mean(adsl$RACE == "BLACK OR AFRICAN AMERICAN")

  # MMSE
  if ("MMSETOT" %in% names(adsl)) {
    metrics$mmse_mean <- mean(adsl$MMSETOT, na.rm = TRUE)
    metrics$mmse_sd <- sd(adsl$MMSETOT, na.rm = TRUE)
  }

  # ===========================================================================
  # DISPOSITION
  # ===========================================================================
  message("  Calculating disposition metrics...")

  if ("COMPLFL" %in% names(adsl)) {
    metrics$completed_wk24_placebo_pct <- mean(adsl$COMPLFL[adsl$TRT01PN == 0] == "Y", na.rm = TRUE)
    metrics$completed_wk24_xan_low_pct <- mean(adsl$COMPLFL[adsl$TRT01PN == 1] == "Y", na.rm = TRUE)
    metrics$completed_wk24_xan_high_pct <- mean(adsl$COMPLFL[adsl$TRT01PN == 2] == "Y", na.rm = TRUE)
  }

  if ("DCTREAS" %in% names(adsl)) {
    # Discontinuation due to AE
    disc_ae_calc <- function(arm_n) {
      subj <- adsl[adsl$TRT01PN == arm_n, ]
      mean(subj$DCTREAS == "ADVERSE EVENT", na.rm = TRUE)
    }
    metrics$disc_ae_placebo_pct <- disc_ae_calc(0)
    metrics$disc_ae_xan_low_pct <- disc_ae_calc(1)
    metrics$disc_ae_xan_high_pct <- disc_ae_calc(2)
  }

  # ===========================================================================
  # PRIMARY EFFICACY - ADAS-Cog
  # ===========================================================================
  message("  Calculating efficacy metrics...")

  if (!is.null(adqs) && nrow(adqs) > 0) {
    # ADAS-Cog (11) Total Score
    adas <- adqs[adqs$PARAMCD == "ACTOT11", ]

    if (nrow(adas) > 0) {
      # Baseline ADAS-Cog
      adas_baseline <- adas[adas$ABLFL == "Y", ]
      if (nrow(adas_baseline) > 0) {
        metrics$adas_baseline_placebo_mean <- mean(adas_baseline$AVAL[adas_baseline$TRTPN == 0], na.rm = TRUE)
        metrics$adas_baseline_xan_low_mean <- mean(adas_baseline$AVAL[adas_baseline$TRTPN == 1], na.rm = TRUE)
        metrics$adas_baseline_xan_high_mean <- mean(adas_baseline$AVAL[adas_baseline$TRTPN == 2], na.rm = TRUE)
      }

      # Week 24 ADAS-Cog (using LOCF endpoint - ANL02FL)
      adas_endpoint <- adas[adas$ANL02FL == "Y", ]
      if (nrow(adas_endpoint) > 0) {
        metrics$adas_week24_placebo_mean <- mean(adas_endpoint$AVAL[adas_endpoint$TRTPN == 0], na.rm = TRUE)
        metrics$adas_week24_xan_low_mean <- mean(adas_endpoint$AVAL[adas_endpoint$TRTPN == 1], na.rm = TRUE)
        metrics$adas_week24_xan_high_mean <- mean(adas_endpoint$AVAL[adas_endpoint$TRTPN == 2], na.rm = TRUE)

        # Change from baseline
        metrics$adas_change_placebo_mean <- mean(adas_endpoint$CHG[adas_endpoint$TRTPN == 0], na.rm = TRUE)
        metrics$adas_change_xan_low_mean <- mean(adas_endpoint$CHG[adas_endpoint$TRTPN == 1], na.rm = TRUE)
        metrics$adas_change_xan_high_mean <- mean(adas_endpoint$CHG[adas_endpoint$TRTPN == 2], na.rm = TRUE)

        message(sprintf("    ADAS-Cog Change from Baseline: Placebo=%.2f, Xan Low=%.2f, Xan High=%.2f",
                        metrics$adas_change_placebo_mean,
                        metrics$adas_change_xan_low_mean,
                        metrics$adas_change_xan_high_mean))
      }
    }

    # CIBIC+
    cibic <- adqs[adqs$PARAMCD == "CIBIC", ]
    if (nrow(cibic) > 0) {
      metrics$cibic_week24_placebo_mean <- mean(cibic$AVAL[cibic$TRTPN == 0], na.rm = TRUE)
      metrics$cibic_week24_xan_low_mean <- mean(cibic$AVAL[cibic$TRTPN == 1], na.rm = TRUE)
      metrics$cibic_week24_xan_high_mean <- mean(cibic$AVAL[cibic$TRTPN == 2], na.rm = TRUE)

      message(sprintf("    CIBIC+ Week 24: Placebo=%.2f, Xan Low=%.2f, Xan High=%.2f",
                      metrics$cibic_week24_placebo_mean,
                      metrics$cibic_week24_xan_low_mean,
                      metrics$cibic_week24_xan_high_mean))
    }
  }

  # ===========================================================================
  # SAFETY
  # ===========================================================================
  message("  Calculating safety metrics...")

  if (!is.null(adae) && nrow(adae) > 0) {
    ae_placebo <- adae[adae$TRTPN == 0, ]
    ae_xan_low <- adae[adae$TRTPN == 1, ]
    ae_xan_high <- adae[adae$TRTPN == 2, ]

    # Any AE
    metrics$any_ae_placebo_pct <- length(unique(ae_placebo$USUBJID)) / n_placebo
    metrics$any_ae_xan_low_pct <- length(unique(ae_xan_low$USUBJID)) / n_xan_low
    metrics$any_ae_xan_high_pct <- length(unique(ae_xan_high$USUBJID)) / n_xan_high

    # Helper function to calculate AE rate by arm
    ae_rate <- function(ae_data, term_pattern, n_arm) {
      length(unique(ae_data$USUBJID[grepl(term_pattern, ae_data$AEDECOD, ignore.case = TRUE)])) / n_arm
    }

    # Application Site Reactions
    metrics$app_site_pruritus_placebo_pct <- ae_rate(ae_placebo, "Application site pruritus", n_placebo)
    metrics$app_site_pruritus_xan_low_pct <- ae_rate(ae_xan_low, "Application site pruritus", n_xan_low)
    metrics$app_site_pruritus_xan_high_pct <- ae_rate(ae_xan_high, "Application site pruritus", n_xan_high)

    metrics$app_site_erythema_placebo_pct <- ae_rate(ae_placebo, "Application site erythema", n_placebo)
    metrics$app_site_erythema_xan_low_pct <- ae_rate(ae_xan_low, "Application site erythema", n_xan_low)
    metrics$app_site_erythema_xan_high_pct <- ae_rate(ae_xan_high, "Application site erythema", n_xan_high)

    # Skin AEs (not application site)
    metrics$pruritus_placebo_pct <- ae_rate(ae_placebo, "^Pruritus$", n_placebo)
    metrics$pruritus_xan_low_pct <- ae_rate(ae_xan_low, "^Pruritus$", n_xan_low)
    metrics$pruritus_xan_high_pct <- ae_rate(ae_xan_high, "^Pruritus$", n_xan_high)

    metrics$erythema_placebo_pct <- ae_rate(ae_placebo, "^Erythema$", n_placebo)
    metrics$erythema_xan_low_pct <- ae_rate(ae_xan_low, "^Erythema$", n_xan_low)
    metrics$erythema_xan_high_pct <- ae_rate(ae_xan_high, "^Erythema$", n_xan_high)

    metrics$rash_placebo_pct <- ae_rate(ae_placebo, "^Rash$", n_placebo)
    metrics$rash_xan_low_pct <- ae_rate(ae_xan_low, "^Rash$", n_xan_low)
    metrics$rash_xan_high_pct <- ae_rate(ae_xan_high, "^Rash$", n_xan_high)

    # Neurological
    metrics$dizziness_placebo_pct <- ae_rate(ae_placebo, "Dizziness", n_placebo)
    metrics$dizziness_xan_low_pct <- ae_rate(ae_xan_low, "Dizziness", n_xan_low)
    metrics$dizziness_xan_high_pct <- ae_rate(ae_xan_high, "Dizziness", n_xan_high)

    metrics$syncope_placebo_pct <- ae_rate(ae_placebo, "Syncope", n_placebo)
    metrics$syncope_xan_low_pct <- ae_rate(ae_xan_low, "Syncope", n_xan_low)
    metrics$syncope_xan_high_pct <- ae_rate(ae_xan_high, "Syncope", n_xan_high)

    # GI
    metrics$nausea_placebo_pct <- ae_rate(ae_placebo, "Nausea", n_placebo)
    metrics$nausea_xan_low_pct <- ae_rate(ae_xan_low, "Nausea", n_xan_low)
    metrics$nausea_xan_high_pct <- ae_rate(ae_xan_high, "Nausea", n_xan_high)

    # Cardiac
    metrics$sinus_bradycardia_placebo_pct <- ae_rate(ae_placebo, "Sinus bradycardia", n_placebo)
    metrics$sinus_bradycardia_xan_low_pct <- ae_rate(ae_xan_low, "Sinus bradycardia", n_xan_low)
    metrics$sinus_bradycardia_xan_high_pct <- ae_rate(ae_xan_high, "Sinus bradycardia", n_xan_high)

    message(sprintf("    Any AE: Placebo=%.1f%%, Xan Low=%.1f%%, Xan High=%.1f%%",
                    metrics$any_ae_placebo_pct * 100,
                    metrics$any_ae_xan_low_pct * 100,
                    metrics$any_ae_xan_high_pct * 100))
  }

  # ===========================================================================
  # EXPOSURE
  # ===========================================================================
  message("  Calculating exposure metrics...")

  if ("CUMDOSE" %in% names(adsl)) {
    # Cumulative dose (mg)
    metrics$cumulative_dose_xan_low_mean <- mean(adsl$CUMDOSE[adsl$TRT01PN == 1], na.rm = TRUE)
    metrics$cumulative_dose_xan_high_mean <- mean(adsl$CUMDOSE[adsl$TRT01PN == 2], na.rm = TRUE)
  }

  # Average daily dose (from treatment arm, assuming full compliance)
  # For Xanomeline Low: 54 mg/day
  # For Xanomeline High: ~72 mg/day average (due to early dropouts)
  if ("TRTDURD" %in% names(adsl) && "CUMDOSE" %in% names(adsl)) {
    xan_low <- adsl[adsl$TRT01PN == 1 & adsl$TRTDURD > 0, ]
    xan_high <- adsl[adsl$TRT01PN == 2 & adsl$TRTDURD > 0, ]

    if (nrow(xan_low) > 0) {
      metrics$avg_daily_dose_xan_low <- mean(xan_low$CUMDOSE / xan_low$TRTDURD, na.rm = TRUE)
    }
    if (nrow(xan_high) > 0) {
      metrics$avg_daily_dose_xan_high <- mean(xan_high$CUMDOSE / xan_high$TRTDURD, na.rm = TRUE)
    }
  }

  metrics
}
