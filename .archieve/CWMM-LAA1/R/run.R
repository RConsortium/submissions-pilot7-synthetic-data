# run.R — Main orchestrator for CWMM-LAA1 IPD simulation
# ==========================================================

# Set working directory to project root
if (basename(getwd()) != "CWMM-LAA1") {
  # Try to find project root
  if (file.exists("R/dag_state.R")) {
    # already in root
  } else if (file.exists("../R/dag_state.R")) {
    setwd("..")
  }
}

# Source all modules
source("R/dag_state.R")
source("R/baseline.R")
source("R/longitudinal.R")
source("R/outcomes.R")
source("R/emit_source.R")
source("R/calibrate.R")

# ============================================================
# MAIN SIMULATION
# ============================================================

run_simulation <- function(param_file = "params/initial_params.json",
                           target_file = "data-raw/targets.json",
                           seed = 20250620,
                           n_calibration_iter = 10,
                           emit_csv = TRUE,
                           verbose = TRUE) {

  if (verbose) message("=== CWMM-LAA1 IPD Simulator ===")
  if (verbose) message("Loading parameters...")

  params <<- load_params(param_file)  # Make available globally for emit_source
  targets <- load_targets(target_file)

  # --- Calibration loop ---
  best_result <- NULL
  best_eff_rmse <- Inf
  current_params <- params

  for (iter in seq_len(n_calibration_iter)) {
    if (verbose) message(sprintf("\n--- Calibration iteration %d/%d ---", iter, n_calibration_iter))

    # Step 1: Generate baseline
    set.seed(seed + iter - 1)
    if (verbose) message("  Generating baseline covariates...")
    baseline <- generate_baseline(current_params, seed = seed + iter - 1)

    # Step 2: Simulate longitudinal
    if (verbose) message("  Simulating longitudinal trajectories...")
    longitudinal <- simulate_longitudinal(baseline, current_params)

    # Step 3: Derive outcomes
    if (verbose) message("  Deriving endpoints...")
    outcomes <- derive_outcomes(baseline, longitudinal$weight_long, longitudinal$disposition)

    # Step 4: Compute summaries
    efficacy_summary <- compute_efficacy_summary(outcomes)
    ae_summary <- compute_ae_summary(longitudinal$ae_long, baseline)
    disc_summary <- compute_disc_summary(longitudinal$disposition)

    # Step 5: Calibration check
    cal_result <- run_calibration_check(efficacy_summary, ae_summary, disc_summary, targets)

    if (verbose) {
      message("  Efficacy comparison:")
      for (r in seq_len(nrow(cal_result$efficacy))) {
        message(sprintf("    %s: sim=%.1f, target=%.1f, diff=%.1f %s",
                        cal_result$efficacy$ARM[r],
                        cal_result$efficacy$SIM_MEAN[r],
                        cal_result$efficacy$TARGET_MEAN[r],
                        cal_result$efficacy$DIFF[r],
                        ifelse(cal_result$efficacy$WITHIN_TOL[r], "[OK]", "[!]")))
      }
    }

    # Compute RMSE for efficacy
    eff_rmse <- sqrt(mean(cal_result$efficacy$DIFF^2))
    if (verbose) message(sprintf("  Efficacy RMSE: %.2f", eff_rmse))

    if (eff_rmse < best_eff_rmse) {
      best_eff_rmse <- eff_rmse
      best_result <- list(
        baseline = baseline,
        longitudinal = longitudinal,
        outcomes = outcomes,
        efficacy_summary = efficacy_summary,
        ae_summary = ae_summary,
        disc_summary = disc_summary,
        cal_result = cal_result,
        params = current_params,
        iter = iter
      )
    }

    # --- Parameter adjustment (simple gradient-free tuning) ---
    if (iter < n_calibration_iter && eff_rmse > 1.0) {
      if (verbose) message("  Adjusting parameters...")
      current_params <- adjust_params(current_params, cal_result, targets)
    }
  }

  if (verbose) {
    message(sprintf("\n=== Best result from iteration %d (RMSE=%.2f) ===",
                    best_result$iter, best_eff_rmse))
  }

  # Use best result
  params <<- best_result$params

  # --- Emit outputs ---
  if (emit_csv) {
    if (verbose) message("\nEmitting source CSVs...")
    emit_source_data(best_result$baseline, best_result$longitudinal,
                     best_result$outcomes, output_dir = "output/source")
  }

  # Generate calibration report
  if (verbose) message("Generating calibration report...")
  generate_calibration_report(best_result$cal_result)

  # Save calibrated params
  if (verbose) message("Saving calibrated parameters...")
  writeLines(toJSON(best_result$params, pretty = TRUE, auto_unbox = TRUE),
             "params/calibrated_params.json")

  if (verbose) {
    message("\n=== Simulation complete ===")
    message("Outputs:")
    message("  - output/source/*.csv")
    message("  - output/analysis/calibration_report.md")
    message("  - params/calibrated_params.json")
  }

  invisible(best_result)
}

#' Simple parameter adjustment based on calibration mismatches
adjust_params <- function(params, cal_result, targets) {
  # Adjust Emax/ED50 for weight trajectory based on errors
  eff <- cal_result$efficacy
  # Exclude placebo from dose-response adjustment
  active_arms <- eff[eff$ARM != "Placebo", ]

  if (nrow(active_arms) > 0) {
    mean_diff <- mean(active_arms$DIFF)
    # If simulated is less negative than target (DIFF > 0), increase |emax|
    if (abs(mean_diff) > 0.5) {
      params$weight_trajectory$emax <- params$weight_trajectory$emax - mean_diff * 0.08
    }
    # Check if low-dose arms are disproportionately off (ED50 adjustment)
    low_dose <- active_arms[active_arms$ARM %in% c("1mg", "3mg"), ]
    high_dose <- active_arms[active_arms$ARM %in% c("9mg"), ]
    if (nrow(low_dose) > 0 && nrow(high_dose) > 0) {
      low_err <- mean(low_dose$DIFF)
      high_err <- mean(high_dose$DIFF)
      # If low-dose is relatively more off (positive diff = not enough loss)
      if (low_err - high_err > 1.5) {
        params$weight_trajectory$ed50 <- params$weight_trajectory$ed50 * 0.9
      } else if (high_err - low_err > 1.5) {
        params$weight_trajectory$ed50 <- params$weight_trajectory$ed50 * 1.1
      }
    }
  }

  # Adjust placebo drift
  placebo_row <- eff[eff$ARM == "Placebo", ]
  if (nrow(placebo_row) == 1) {
    pbo_diff <- placebo_row$DIFF
    if (abs(pbo_diff) > 0.5) {
      params$weight_trajectory$placebo_drift <- params$weight_trajectory$placebo_drift - pbo_diff * 0.3
    }
  }

  # Adjust AE hazards based on mean direction
  ae_comp <- cal_result$ae_rates
  for (ae_name in unique(ae_comp$AETERM)) {
    ae_subset <- ae_comp[ae_comp$AETERM == ae_name, ]
    mean_ae_diff <- mean(ae_subset$DIFF)
    if (abs(mean_ae_diff) > 3) {
      # Adjust alpha (intercept) for this AE
      direction <- -sign(mean_ae_diff) * 0.15
      params$ae_hazards[[ae_name]]$alpha <- params$ae_hazards[[ae_name]]$alpha + direction
    }
  }

  # Adjust discontinuation
  disc_comp <- cal_result$discontinuation
  tx_disc <- disc_comp[disc_comp$METRIC == "tx_disc", ]
  for (r in seq_len(nrow(tx_disc))) {
    arm <- tx_disc$ARM[r]
    diff_val <- tx_disc$DIFF[r]
    if (abs(diff_val) > 5) {
      adj <- -sign(diff_val) * 0.1
      params$discontinuation$arm_effects[[arm]] <- params$discontinuation$arm_effects[[arm]] + adj
    }
  }

  params
}

# --- Run if executed directly ---
if (sys.nframe() == 0 || !interactive()) {
  result <- run_simulation()
}
