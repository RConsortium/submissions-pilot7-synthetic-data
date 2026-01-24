#' =============================================================================
#' CDISC Pilot 01 Scorer - Data Validation
#' Xanomeline TTS in Alzheimer's Disease
#' =============================================================================
#' Validates ADaM data for consistency and logical correctness
#' =============================================================================

#' Validate ADaM data
#' @param adam List of ADaM datasets
#' @return List with validation results
validate_data <- function(adam) {

  checks <- list()

  adsl <- adam$adsl
  adqs <- adam$adqs
  adae <- adam$adae

  # ===========================================================================
  # DEMOGRAPHIC CHECKS
  # ===========================================================================

  # Check 1: Sample size matches expected
  checks$sample_size <- list(
    name = "Sample size",
    category = "LOGICAL",
    expected = 254,
    actual = nrow(adsl),
    passed = nrow(adsl) >= 250 && nrow(adsl) <= 260,
    message = sprintf("Expected ~254 subjects, got %d", nrow(adsl))
  )

  # Check 2: Treatment arm balance
  arm_counts <- table(adsl$TRT01PN)
  checks$arm_balance <- list(
    name = "Treatment arm balance",
    category = "LOGICAL",
    expected = "~84-86 per arm",
    actual = paste(arm_counts, collapse = "/"),
    passed = all(arm_counts >= 80 & arm_counts <= 90),
    message = sprintf("Arm sizes: Placebo=%d, Xan Low=%d, Xan High=%d",
                      arm_counts["0"], arm_counts["1"], arm_counts["2"])
  )

  # Check 3: Age range
  checks$age_range <- list(
    name = "Age range",
    category = "RANGE",
    expected = "50-90 years (elderly Alzheimer's)",
    actual = sprintf("%.0f-%.0f", min(adsl$AGE), max(adsl$AGE)),
    passed = min(adsl$AGE) >= 50 && max(adsl$AGE) <= 95,
    message = sprintf("Age range: %.0f to %.0f years", min(adsl$AGE), max(adsl$AGE))
  )

  # Check 4: Sex distribution
  male_pct <- mean(adsl$SEX == "M") * 100
  checks$sex_distribution <- list(
    name = "Sex distribution",
    category = "RANGE",
    expected = "~44% male, ~56% female",
    actual = sprintf("%.0f%% male", male_pct),
    passed = male_pct >= 35 && male_pct <= 55,
    message = sprintf("Male: %.1f%%", male_pct)
  )

  # Check 5: MMSE range (eligibility criteria)
  if ("MMSETOT" %in% names(adsl)) {
    mmse_range <- range(adsl$MMSETOT, na.rm = TRUE)
    checks$mmse_range <- list(
      name = "MMSE range",
      category = "RANGE",
      expected = "10-24 (mild-moderate AD)",
      actual = sprintf("%.0f-%.0f", mmse_range[1], mmse_range[2]),
      passed = mmse_range[1] >= 10 && mmse_range[2] <= 24,
      message = sprintf("MMSE range: %.0f to %.0f", mmse_range[1], mmse_range[2])
    )
  }

  # ===========================================================================
  # DISPOSITION CHECKS
  # ===========================================================================

  if ("COMPLFL" %in% names(adsl)) {
    completion_rate <- mean(adsl$COMPLFL == "Y", na.rm = TRUE) * 100
    checks$completion_rate <- list(
      name = "Overall completion rate",
      category = "RANGE",
      expected = "~46% (high dropout in active arms)",
      actual = sprintf("%.1f%%", completion_rate),
      passed = completion_rate >= 35 && completion_rate <= 55,
      message = sprintf("Overall completion rate: %.1f%%", completion_rate)
    )

    # Completion by arm - Placebo should have higher completion
    comp_placebo <- mean(adsl$COMPLFL[adsl$TRT01PN == 0] == "Y", na.rm = TRUE) * 100
    comp_xan_low <- mean(adsl$COMPLFL[adsl$TRT01PN == 1] == "Y", na.rm = TRUE) * 100
    comp_xan_high <- mean(adsl$COMPLFL[adsl$TRT01PN == 2] == "Y", na.rm = TRUE) * 100

    checks$completion_pattern <- list(
      name = "Completion pattern (Placebo > Active)",
      category = "CLINICAL",
      expected = "Placebo ~70%, Active ~35%",
      actual = sprintf("P=%.0f%%, XL=%.0f%%, XH=%.0f%%",
                       comp_placebo, comp_xan_low, comp_xan_high),
      passed = comp_placebo > comp_xan_low && comp_placebo > comp_xan_high,
      message = "Placebo should have higher completion than active arms"
    )
  }

  # ===========================================================================
  # EFFICACY CHECKS (ADQS)
  # ===========================================================================

  if (!is.null(adqs) && nrow(adqs) > 0) {
    # Check ADAS-Cog records
    adas <- adqs[adqs$PARAMCD == "ACTOT11", ]
    if (nrow(adas) > 0) {
      checks$adas_records <- list(
        name = "ADAS-Cog records present",
        category = "LOGICAL",
        expected = "Multiple timepoints per subject",
        actual = sprintf("%d records", nrow(adas)),
        passed = nrow(adas) > nrow(adsl),
        message = sprintf("ADAS-Cog records: %d", nrow(adas))
      )

      # Baseline ADAS-Cog range
      adas_bl <- adas[adas$ABLFL == "Y", ]
      if (nrow(adas_bl) > 0) {
        adas_range <- range(adas_bl$AVAL, na.rm = TRUE)
        checks$adas_baseline_range <- list(
          name = "ADAS-Cog baseline range",
          category = "RANGE",
          expected = "~10-50 (typical for mild-moderate AD)",
          actual = sprintf("%.0f-%.0f", adas_range[1], adas_range[2]),
          passed = adas_range[1] >= 0 && adas_range[2] <= 70,
          message = sprintf("ADAS-Cog baseline: %.0f to %.0f", adas_range[1], adas_range[2])
        )
      }

      # ADAS-Cog change should be positive (worsening over time)
      adas_change <- adas[!is.na(adas$CHG), ]
      if (nrow(adas_change) > 0) {
        mean_change <- mean(adas_change$CHG, na.rm = TRUE)
        checks$adas_change_direction <- list(
          name = "ADAS-Cog change direction",
          category = "CLINICAL",
          expected = "Positive (worsening over time)",
          actual = sprintf("Mean change = %.2f", mean_change),
          passed = mean_change > 0,
          message = "ADAS-Cog should worsen over time in placebo/early terminator"
        )
      }
    }

    # Check CIBIC+ records
    cibic <- adqs[adqs$PARAMCD == "CIBIC", ]
    if (nrow(cibic) > 0) {
      cibic_range <- range(cibic$AVAL, na.rm = TRUE)
      checks$cibic_range <- list(
        name = "CIBIC+ range",
        category = "RANGE",
        expected = "1-7 scale",
        actual = sprintf("%.0f-%.0f", cibic_range[1], cibic_range[2]),
        passed = cibic_range[1] >= 1 && cibic_range[2] <= 7,
        message = sprintf("CIBIC+ range: %.0f to %.0f", cibic_range[1], cibic_range[2])
      )
    }
  }

  # ===========================================================================
  # SAFETY CHECKS (ADAE)
  # ===========================================================================

  if (!is.null(adae) && nrow(adae) > 0) {
    # AE rate should be higher in active arms
    ae_rate_placebo <- length(unique(adae$USUBJID[adae$TRTPN == 0])) /
      sum(adsl$TRT01PN == 0) * 100
    ae_rate_xan_low <- length(unique(adae$USUBJID[adae$TRTPN == 1])) /
      sum(adsl$TRT01PN == 1) * 100
    ae_rate_xan_high <- length(unique(adae$USUBJID[adae$TRTPN == 2])) /
      sum(adsl$TRT01PN == 2) * 100

    checks$ae_rate_pattern <- list(
      name = "AE rate pattern (Active > Placebo)",
      category = "CLINICAL",
      expected = "Active arms should have higher AE rates",
      actual = sprintf("P=%.0f%%, XL=%.0f%%, XH=%.0f%%",
                       ae_rate_placebo, ae_rate_xan_low, ae_rate_xan_high),
      passed = ae_rate_xan_low > ae_rate_placebo && ae_rate_xan_high > ae_rate_placebo,
      message = "Active arms should have higher AE rates due to application site reactions"
    )

    # Application site AEs should be more common in active arms
    app_site_ae <- adae[grepl("Application site", adae$AEDECOD, ignore.case = TRUE), ]
    if (nrow(app_site_ae) > 0) {
      app_site_placebo <- length(unique(app_site_ae$USUBJID[app_site_ae$TRTPN == 0]))
      app_site_active <- length(unique(app_site_ae$USUBJID[app_site_ae$TRTPN %in% c(1, 2)]))

      checks$app_site_pattern <- list(
        name = "Application site AEs (Active >> Placebo)",
        category = "CLINICAL",
        expected = "Much higher in active arms",
        actual = sprintf("Placebo: %d, Active: %d", app_site_placebo, app_site_active),
        passed = app_site_active > app_site_placebo * 2,
        message = "Application site AEs are key tolerability signal for transdermal"
      )
    }
  }

  # ===========================================================================
  # CROSS-DATASET CHECKS
  # ===========================================================================

  # All ADQS subjects should be in ADSL
  if (!is.null(adqs) && nrow(adqs) > 0) {
    adqs_subjects <- unique(adqs$USUBJID)
    adsl_subjects <- unique(adsl$USUBJID)
    missing_in_adsl <- setdiff(adqs_subjects, adsl_subjects)

    checks$adqs_subjects_in_adsl <- list(
      name = "ADQS subjects in ADSL",
      category = "CROSS_DATASET",
      expected = "All ADQS subjects in ADSL",
      actual = sprintf("%d subjects in ADQS, %d missing in ADSL",
                       length(adqs_subjects), length(missing_in_adsl)),
      passed = length(missing_in_adsl) == 0,
      message = if (length(missing_in_adsl) == 0) "All OK" else
        paste("Missing:", paste(head(missing_in_adsl, 5), collapse = ", "))
    )
  }

  # All ADAE subjects should be in ADSL
  if (!is.null(adae) && nrow(adae) > 0) {
    adae_subjects <- unique(adae$USUBJID)
    missing_in_adsl <- setdiff(adae_subjects, adsl_subjects)

    checks$adae_subjects_in_adsl <- list(
      name = "ADAE subjects in ADSL",
      category = "CROSS_DATASET",
      expected = "All ADAE subjects in ADSL",
      actual = sprintf("%d subjects with AEs, %d missing in ADSL",
                       length(adae_subjects), length(missing_in_adsl)),
      passed = length(missing_in_adsl) == 0,
      message = if (length(missing_in_adsl) == 0) "All OK" else
        paste("Missing:", paste(head(missing_in_adsl, 5), collapse = ", "))
    )
  }

  # ===========================================================================
  # SUMMARY
  # ===========================================================================

  total_checks <- length(checks)
  passed_checks <- sum(sapply(checks, function(x) isTRUE(x$passed)))
  skipped <- sum(sapply(checks, function(x) is.na(x$passed)))

  # Create results data frame
  results_df <- do.call(rbind, lapply(names(checks), function(check_name) {
    check <- checks[[check_name]]
    data.frame(
      check = check_name,
      name = check$name,
      category = check$category,
      expected = as.character(check$expected),
      actual = as.character(check$actual),
      passed = check$passed,
      message = check$message,
      stringsAsFactors = FALSE
    )
  }))

  list(
    checks = checks,
    summary = list(
      total_checks = total_checks,
      passed = passed_checks,
      failed = total_checks - passed_checks - skipped,
      skipped = skipped,
      pass_rate = round(passed_checks / (total_checks - skipped) * 100, 1),
      results_df = results_df
    )
  )
}

#' Print validation results
#' @param validation Validation results from validate_data()
print_validation_results <- function(validation) {

  message(sprintf("\n  Validation: %d/%d checks passed (%.1f%%)",
                  validation$summary$passed,
                  validation$summary$total_checks - validation$summary$skipped,
                  validation$summary$pass_rate))

  # Group by category
  categories <- unique(sapply(validation$checks, function(x) x$category))

  for (cat in categories) {
    cat_checks <- Filter(function(x) x$category == cat, validation$checks)
    cat_passed <- sum(sapply(cat_checks, function(x) isTRUE(x$passed)))
    cat_total <- length(cat_checks)

    message(sprintf("    %s: %d/%d", cat, cat_passed, cat_total))

    # Show failed checks
    for (check in cat_checks) {
      if (!isTRUE(check$passed)) {
        message(sprintf("      [FAIL] %s: %s", check$name, check$message))
      }
    }
  }
}
