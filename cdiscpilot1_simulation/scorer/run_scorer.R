#' =============================================================================
#' CDISC Pilot 01 Scorer - Main Entry Point
#' Xanomeline TTS in Alzheimer's Disease
#' =============================================================================
#' Compares simulated metrics against targets with accuracy tiers
#' =============================================================================

#' Score a single metric
#' @param simulated Simulated value
#' @param target Target value
#' @param tolerance Acceptable tolerance
#' @return List with pass/fail and details
score_metric <- function(simulated, target, tolerance) {

  # Handle NA targets
  if (is.na(target)) {
    return(list(
      simulated = simulated,
      target = NA,
      tolerance = tolerance,
      deviation = NA,
      pass = TRUE,  # NA targets are acceptable
      status = "NA_TARGET"
    ))
  }

  # Handle NA simulated
  if (is.na(simulated)) {
    return(list(
      simulated = NA,
      target = target,
      tolerance = tolerance,
      deviation = NA,
      pass = FALSE,
      status = "NA_SIMULATED"
    ))
  }

  # Calculate deviation
  if (target == 0) {
    deviation <- abs(simulated)
  } else {
    deviation <- abs(simulated - target) / abs(target)
  }

  pass <- deviation <= tolerance

  list(
    simulated = round(simulated, 4),
    target = round(target, 4),
    tolerance = tolerance,
    deviation = round(deviation, 4),
    pass = pass,
    status = if(pass) "PASS" else "FAIL"
  )
}

#' Run full scoring
#' @param adam_dir Directory containing ADaM datasets
#' @param output_dir Output directory for score report
#' @return Scoring results
run_scorer <- function(adam_dir = NULL, output_dir = NULL) {

  message("=== CDISC PILOT 01 SCORER ===")
  message("Xanomeline Transdermal Therapeutic System in Alzheimer's Disease")

  # Source dependencies
  source(here::here("targets", "metadata.R"))
  source(here::here("targets", "cdiscpilot01_targets.R"))
  source(here::here("scorer", "calculate_metrics.R"))
  source(here::here("scorer", "validate_data.R"))

  # Load ADaM data
  if (is.null(adam_dir)) {
    adam_dir <- here::here("data", "adam")
  }

  message(sprintf("\nLoading ADaM from: %s", adam_dir))

  # Read from CSV format
  adam <- list(
    adsl = read.csv(file.path(adam_dir, "adsl.csv"), stringsAsFactors = FALSE),
    adqs = read.csv(file.path(adam_dir, "adqs.csv"), stringsAsFactors = FALSE),
    adae = read.csv(file.path(adam_dir, "adae.csv"), stringsAsFactors = FALSE)
  )

  # Also read ADLB and ADVS if available
  if (file.exists(file.path(adam_dir, "adlb.csv"))) {
    adam$adlb <- read.csv(file.path(adam_dir, "adlb.csv"), stringsAsFactors = FALSE)
  }
  if (file.exists(file.path(adam_dir, "advs.csv"))) {
    adam$advs <- read.csv(file.path(adam_dir, "advs.csv"), stringsAsFactors = FALSE)
  }

  message(sprintf("  ADSL: %d subjects", nrow(adam$adsl)))
  message(sprintf("  ADQS: %d records", nrow(adam$adqs)))
  message(sprintf("  ADAE: %d records", nrow(adam$adae)))

  # Run data validation checks
  message("\nValidating data consistency...")
  validation <- validate_data(adam)
  print_validation_results(validation)

  # Calculate metrics from simulated data
  message("\nCalculating metrics from simulated data...")
  simulated <- calculate_metrics(adam)

  # Get target values
  targets <- get_flat_targets()

  # Score each metric
  message("\nScoring metrics by tier...")

  results <- list()
  summary_by_tier <- list(
    CRITICAL = list(total = 0, passed = 0),
    HIGH = list(total = 0, passed = 0),
    MODERATE = list(total = 0, passed = 0),
    LOW = list(total = 0, passed = 0)
  )

  for (metric_name in names(simulated)) {
    if (metric_name %in% names(targets)) {
      tier <- get_target_tier(metric_name)
      tolerance <- get_target_tolerance(metric_name)

      score <- score_metric(
        simulated[[metric_name]],
        targets[[metric_name]],
        tolerance
      )

      score$metric <- metric_name
      score$tier <- tier
      results[[metric_name]] <- score

      # Update summary
      if (tier %in% names(summary_by_tier)) {
        summary_by_tier[[tier]]$total <- summary_by_tier[[tier]]$total + 1
        if (score$pass) {
          summary_by_tier[[tier]]$passed <- summary_by_tier[[tier]]$passed + 1
        }
      }
    }
  }

  # Print results by tier
  message("\n" , paste(rep("=", 70), collapse = ""))
  message("SCORING RESULTS BY TIER")
  message(paste(rep("=", 70), collapse = ""))

  for (tier in c("CRITICAL", "HIGH", "MODERATE", "LOW")) {
    tier_results <- Filter(function(x) x$tier == tier, results)

    if (length(tier_results) > 0) {
      passed <- sum(sapply(tier_results, function(x) x$pass))
      total <- length(tier_results)
      pct <- round(passed / total * 100, 1)

      message(sprintf("\n[%s] %d/%d passed (%.1f%%)", tier, passed, total, pct))
      message(paste(rep("-", 50), collapse = ""))

      for (r in tier_results) {
        status_icon <- if(r$pass) "OK" else "XX"
        if (is.na(r$target)) {
          message(sprintf("  [%s] %s: sim=%.3f, target=NA",
                          status_icon, r$metric, r$simulated))
        } else if (is.na(r$simulated)) {
          message(sprintf("  [%s] %s: sim=NA, target=%.3f",
                          status_icon, r$metric, r$target))
        } else {
          message(sprintf("  [%s] %s: sim=%.3f, target=%.3f, dev=%.1f%%",
                          status_icon, r$metric, r$simulated, r$target, r$deviation * 100))
        }
      }
    }
  }

  # Overall summary
  message("\n" , paste(rep("=", 70), collapse = ""))
  message("OVERALL SUMMARY")
  message(paste(rep("=", 70), collapse = ""))

  total_all <- sum(sapply(summary_by_tier, function(x) x$total))
  passed_all <- sum(sapply(summary_by_tier, function(x) x$passed))

  if (total_all > 0) {
    message(sprintf("\nTotal metrics scored: %d", total_all))
    message(sprintf("Total passed: %d (%.1f%%)", passed_all, passed_all/total_all * 100))

    for (tier in c("CRITICAL", "HIGH", "MODERATE", "LOW")) {
      s <- summary_by_tier[[tier]]
      if (s$total > 0) {
        message(sprintf("  %s: %d/%d (%.1f%%)",
                        tier, s$passed, s$total, s$passed/s$total * 100))
      }
    }
  }

  # Save results if output directory specified
  if (!is.null(output_dir)) {
    dir.create(output_dir, recursive = TRUE, showWarnings = FALSE)

    # Save detailed results
    if (length(results) > 0) {
      results_df <- do.call(rbind, lapply(results, function(x) {
        data.frame(
          metric = x$metric,
          tier = x$tier,
          simulated = x$simulated,
          target = x$target,
          tolerance = x$tolerance,
          deviation = x$deviation,
          pass = x$pass,
          status = x$status,
          stringsAsFactors = FALSE
        )
      }))

      write.csv(results_df, file.path(output_dir, "score_details.csv"), row.names = FALSE)
      jsonlite::write_json(results_df, file.path(output_dir, "score_details.json"), pretty = TRUE)
    }

    # Save summary
    summary_df <- data.frame(
      tier = names(summary_by_tier),
      total = sapply(summary_by_tier, function(x) x$total),
      passed = sapply(summary_by_tier, function(x) x$passed),
      stringsAsFactors = FALSE
    )
    summary_df$pct_passed <- ifelse(summary_df$total > 0,
                                     round(summary_df$passed / summary_df$total * 100, 1),
                                     NA)

    write.csv(summary_df, file.path(output_dir, "score_summary.csv"), row.names = FALSE)
    jsonlite::write_json(summary_df, file.path(output_dir, "score_summary.json"), pretty = TRUE)

    # Save validation results
    if (!is.null(validation$summary$results_df) && nrow(validation$summary$results_df) > 0) {
      write.csv(validation$summary$results_df, file.path(output_dir, "validation_details.csv"), row.names = FALSE)
      jsonlite::write_json(validation$summary$results_df, file.path(output_dir, "validation_details.json"), pretty = TRUE)
    }

    message(sprintf("\nResults saved to: %s", output_dir))
  }

  message("\n=== SCORING COMPLETE ===")

  list(
    results = results,
    summary = summary_by_tier,
    total_passed = passed_all,
    total_metrics = total_all,
    validation = validation
  )
}

# Run if executed directly
if (sys.nframe() == 0 || !interactive()) {
  if (!requireNamespace("here", quietly = TRUE)) {
    install.packages("here", repos = "https://cloud.r-project.org")
  }
  library(here)

  result <- run_scorer(
    adam_dir = here::here("data", "adam"),
    output_dir = here::here("output")
  )
}
