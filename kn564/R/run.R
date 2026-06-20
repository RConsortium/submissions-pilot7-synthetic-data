# run.R — Orchestrator for KEYNOTE-564 IPD simulation
# KEYNOTE-564 IPD Causal-DAG Simulator
#
# Usage:
#   source("R/run.R")
#   results <- run_simulation()
#   results <- run_simulation(calibrate = TRUE)

# ─── Load All Modules ─────────────────────────────────────────────────────────

source("R/dag_state.R")
source("R/baseline.R")
source("R/longitudinal.R")
source("R/recurrence.R")
source("R/post_recurrence.R")
source("R/outcomes.R")
source("R/emit_source.R")
source("R/sdtm.R")
source("R/adam.R")

#' Run the full KEYNOTE-564 IPD simulation pipeline
#' @param params_path character, path to parameters file
#' @param calibrate logical, whether to run calibration loop first
#' @param seed integer, random seed (NULL uses params seed)
#' @param n integer, number of patients (NULL uses params N)
#' @param output_dir character, base output directory
#' @param verbose logical, print progress messages
#' @return list with all simulation results
run_simulation <- function(params_path = "params/initial_params.json",
                           calibrate = FALSE,
                           seed = NULL,
                           n = NULL,
                           output_dir = "output",
                           verbose = TRUE) {

  start_time <- Sys.time()

  # Load parameters
  params <- load_params(params_path)
  if (!is.null(seed)) params$seed <- seed
  if (!is.null(n)) params$N <- n

  if (verbose) {
    message("══════════════════════════════════════════════════════════════")
    message("  KEYNOTE-564 IPD Causal-DAG Simulator")
    message(sprintf("  N = %d | Seed = %d | Calibrate = %s",
                    params$N, params$seed, calibrate))
    message("══════════════════════════════════════════════════════════════")
  }

  # ─── Optional Calibration ────────────────────────────────────────────────
  if (calibrate) {
    source("R/calibrate.R")
    cal_result <- run_calibration(max_iter = 8L, params = params, verbose = verbose)
    params <- cal_result$calibrated_params
    params_path <- "params/calibrated_params.json"
  }

  # ─── Step 1: Baseline Generation ────────────────────────────────────────
  if (verbose) message("\n[1/7] Generating baseline characteristics...")
  set.seed(params$seed)
  bl <- generate_baseline(n = params$N, params = params, seed = params$seed)

  # ─── Step 2: Longitudinal Simulation ────────────────────────────────────
  if (verbose) message("[2/7] Simulating longitudinal trajectories...")
  longitudinal <- simulate_longitudinal(bl, params)

  # ─── Step 3: Recurrence Model ───────────────────────────────────────────
  if (verbose) message("[3/7] Simulating recurrence...")
  recurrence_dt <- simulate_recurrence(bl, longitudinal$ex_long, params)

  # ─── Step 4: Post-Recurrence / Death ────────────────────────────────────
  if (verbose) message("[4/7] Simulating post-recurrence and death...")
  death_dt <- simulate_post_recurrence(bl, recurrence_dt, params)

  # ─── Step 5: Endpoint Derivation ────────────────────────────────────────
  if (verbose) message("[5/7] Deriving endpoints...")
  endpoints <- derive_endpoints(bl, recurrence_dt, death_dt)

  # Save endpoints for ADaM
  dir.create(file.path(output_dir, "source"), recursive = TRUE, showWarnings = FALSE)
  fwrite(endpoints, file.path(output_dir, "source", "endpoints.csv"))

  # ─── Step 6: Source Emission ────────────────────────────────────────────
  if (verbose) message("[6/7] Emitting source CSVs...")
  source_data <- emit_source_csvs(bl, longitudinal, recurrence_dt, death_dt, endpoints,
                                   output_dir = file.path(output_dir, "source"))

  # ─── Step 7: SDTM + ADaM ───────────────────────────────────────────────
  if (verbose) message("[7/7] Building SDTM and ADaM datasets...")
  sdtm_domains <- build_sdtm(source_dir = file.path(output_dir, "source"),
                              output_dir = file.path(output_dir, "sdtm"))
  adam_datasets <- build_adam(source_dir = file.path(output_dir, "source"),
                              sdtm_dir = file.path(output_dir, "sdtm"),
                              output_dir = file.path(output_dir, "adam"))

  # ─── Summary Report ─────────────────────────────────────────────────────
  elapsed <- as.numeric(difftime(Sys.time(), start_time, units = "secs"))
  summary_stats <- endpoint_summary(endpoints)

  if (verbose) {
    message("\n══════════════════════════════════════════════════════════════")
    message("  Simulation Complete")
    message(sprintf("  Elapsed: %.1f seconds", elapsed))
    message("══════════════════════════════════════════════════════════════")
    message("\n  DFS Summary:")
    message(sprintf("    Events: pembro=%d, placebo=%d",
                    summary_stats$dfs_events_pembro, summary_stats$dfs_events_placebo))
    message(sprintf("    KM 48mo: pembro=%.3f, placebo=%.3f",
                    summary_stats$dfs_km_48mo_pembro, summary_stats$dfs_km_48mo_placebo))
    message("\n  OS Summary:")
    message(sprintf("    Events: pembro=%d, placebo=%d",
                    summary_stats$os_events_pembro, summary_stats$os_events_placebo))
    message(sprintf("    KM 48mo: pembro=%.3f, placebo=%.3f",
                    summary_stats$os_km_48mo_pembro, summary_stats$os_km_48mo_placebo))

    # Compute HRs
    tryCatch({
      dfs_hr <- compute_hr(endpoints, "DFS_DAY", "DFS_EVENT")
      os_hr <- compute_hr(endpoints, "OS_DAY", "OS_EVENT")
      message(sprintf("\n    DFS HR: %.3f (%.3f-%.3f)",
                      dfs_hr$hr, dfs_hr$hr_lower, dfs_hr$hr_upper))
      message(sprintf("    OS HR:  %.3f (%.3f-%.3f)",
                      os_hr$hr, os_hr$hr_lower, os_hr$hr_upper))
    }, error = function(e) {
      message("  (HR computation requires 'survival' package)")
    })
  }

  # ─── Generate Analysis Outputs ──────────────────────────────────────────
  generate_analysis_report(endpoints, longitudinal, bl, summary_stats,
                           output_dir = file.path(output_dir, "analysis"))

  # Return all results
  invisible(list(
    params = params,
    bl = bl,
    longitudinal = longitudinal,
    recurrence_dt = recurrence_dt,
    death_dt = death_dt,
    endpoints = endpoints,
    source_data = source_data,
    sdtm = sdtm_domains,
    adam = adam_datasets,
    summary = summary_stats
  ))
}

#' Generate analysis report outputs
generate_analysis_report <- function(endpoints, longitudinal, bl, summary_stats,
                                      output_dir = "output/analysis") {

  dir.create(output_dir, recursive = TRUE, showWarnings = FALSE)

  # ─── Calibration Comparison Table ────────────────────────────────────────
  targets <- load_targets()

  comparison <- data.table(
    Metric = c("DFS HR", "DFS KM 48mo (Pembro)", "DFS KM 48mo (Placebo)",
               "OS KM 48mo (Pembro)", "OS KM 48mo (Placebo)",
               "DFS events (Pembro)", "DFS events (Placebo)",
               "OS events (Pembro)", "OS events (Placebo)"),
    Target = c(targets$dfs$hr,
               targets$dfs$km_48mo_pembrolizumab, targets$dfs$km_48mo_placebo,
               targets$os$km_48mo_pembrolizumab, targets$os$km_48mo_placebo,
               targets$dfs$events_pembrolizumab, targets$dfs$events_placebo,
               targets$os$events_pembrolizumab, targets$os$events_placebo),
    Simulated = c(NA_real_,
                  summary_stats$dfs_km_48mo_pembro, summary_stats$dfs_km_48mo_placebo,
                  summary_stats$os_km_48mo_pembro, summary_stats$os_km_48mo_placebo,
                  summary_stats$dfs_events_pembro, summary_stats$dfs_events_placebo,
                  summary_stats$os_events_pembro, summary_stats$os_events_placebo)
  )

  # Add HR if survival package available
  tryCatch({
    dfs_hr <- compute_hr(endpoints, "DFS_DAY", "DFS_EVENT")
    os_hr <- compute_hr(endpoints, "OS_DAY", "OS_EVENT")
    comparison[Metric == "DFS HR", Simulated := dfs_hr$hr]
    comparison <- rbind(comparison, data.table(
      Metric = "OS HR", Target = targets$os$hr, Simulated = os_hr$hr
    ))
  }, error = function(e) NULL)

  comparison[, Deviation := Simulated - Target]
  comparison[, Pct_Deviation := round(100 * Deviation / Target, 2)]

  fwrite(comparison, file.path(output_dir, "calibration_comparison.csv"))

  # ─── AE Summary Table ───────────────────────────────────────────────────
  ae_long <- longitudinal$ae_long
  if (nrow(ae_long) > 0) {
    ae_with_arm <- merge(ae_long, bl[, .(SUBJID, ARM)], by = "SUBJID")
    n_pembro <- sum(bl$ARM == "PEMBROLIZUMAB")
    n_placebo <- sum(bl$ARM == "PLACEBO")

    ae_summary <- ae_with_arm[, .(
      N_patients = uniqueN(SUBJID),
      N_events = .N
    ), by = .(ARM, AETERM)]

    ae_summary[ARM == "PEMBROLIZUMAB", Pct := round(100 * N_patients / n_pembro, 1)]
    ae_summary[ARM == "PLACEBO", Pct := round(100 * N_patients / n_placebo, 1)]

    fwrite(ae_summary, file.path(output_dir, "ae_summary.csv"))
  }

  # ─── KM Data for Plotting ───────────────────────────────────────────────
  km_data <- endpoints[, .(SUBJID, ARM, DFS_DAY, DFS_EVENT, OS_DAY, OS_EVENT)]
  fwrite(km_data, file.path(output_dir, "km_data.csv"))

  message(sprintf("[analysis] Report files written to %s", output_dir))
}

# ─── Convenience: Run if sourced directly ──────────────────────────────────────

if (sys.nframe() == 0) {
  # Running as main script
  results <- run_simulation(calibrate = FALSE, verbose = TRUE)
}
