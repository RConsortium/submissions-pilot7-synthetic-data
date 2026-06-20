# calibrate.R — Calibration loop: compare simulated vs target statistics
# ======================================================================

source("R/dag_state.R")

#' Load calibration targets
load_targets <- function(target_file = "data-raw/targets.json") {
  fromJSON(target_file, simplifyVector = TRUE, simplifyDataFrame = FALSE)
}

#' Compare simulated efficacy to targets
#' @param efficacy_summary data.frame from compute_efficacy_summary()
#' @param targets List from load_targets()
#' @return data.frame with comparison
compare_efficacy <- function(efficacy_summary, targets) {
  target_arms <- targets$primary_efficacy$arms

  comparison <- data.frame(
    ARM = character(),
    SIM_MEAN = numeric(),
    TARGET_MEAN = numeric(),
    DIFF = numeric(),
    WITHIN_TOL = logical(),
    stringsAsFactors = FALSE
  )

  for (arm in names(target_arms)) {
    sim_row <- efficacy_summary[efficacy_summary$ARM == arm, ]
    if (nrow(sim_row) == 0) next
    tgt <- target_arms[[arm]]
    diff_val <- sim_row$MEAN_PCT_CHANGE - tgt$mean
    comparison <- rbind(comparison, data.frame(
      ARM = arm,
      SIM_MEAN = sim_row$MEAN_PCT_CHANGE,
      TARGET_MEAN = tgt$mean,
      DIFF = round(diff_val, 2),
      WITHIN_TOL = abs(diff_val) <= targets$tolerances$weight_change_mean_tol,
      stringsAsFactors = FALSE
    ))
  }

  comparison
}

#' Compare simulated AE rates to targets
#' @param ae_summary data.frame from compute_ae_summary()
#' @param targets List from load_targets()
#' @return data.frame with comparison
compare_ae_rates <- function(ae_summary, targets) {
  target_aes <- targets$safety_ae_rates$aes
  tol <- targets$tolerances$ae_rate_tol_pct_pts

  comparison <- data.frame(
    ARM = character(),
    AETERM = character(),
    SIM_PCT = numeric(),
    TARGET_PCT = numeric(),
    DIFF = numeric(),
    WITHIN_TOL = logical(),
    stringsAsFactors = FALSE
  )

  for (ae_name in names(target_aes)) {
    target_ae <- target_aes[[ae_name]]
    for (arm in names(target_ae)) {
      sim_row <- ae_summary[ae_summary$ARM == arm & ae_summary$AETERM == ae_name, ]
      if (nrow(sim_row) == 0) next
      diff_val <- sim_row$PCT - target_ae[[arm]]
      comparison <- rbind(comparison, data.frame(
        ARM = arm,
        AETERM = ae_name,
        SIM_PCT = sim_row$PCT,
        TARGET_PCT = target_ae[[arm]],
        DIFF = round(diff_val, 1),
        WITHIN_TOL = abs(diff_val) <= tol,
        stringsAsFactors = FALSE
      ))
    }
  }

  comparison
}

#' Compare simulated discontinuation to targets
#' @param disc_summary data.frame from compute_disc_summary()
#' @param targets List from load_targets()
#' @return data.frame with comparison
compare_discontinuation <- function(disc_summary, targets) {
  target_disc <- targets$discontinuation$arms
  tol <- targets$tolerances$disc_rate_tol_pct_pts

  comparison <- data.frame(
    ARM = character(),
    METRIC = character(),
    SIM_PCT = numeric(),
    TARGET_PCT = numeric(),
    DIFF = numeric(),
    WITHIN_TOL = logical(),
    stringsAsFactors = FALSE
  )

  for (arm in names(target_disc)) {
    tgt <- target_disc[[arm]]
    sim_row <- disc_summary[disc_summary$ARM == arm, ]
    if (nrow(sim_row) == 0) next

    # Treatment discontinuation
    diff_tx <- sim_row$TX_DISC_PCT - tgt$tx_disc * 100
    comparison <- rbind(comparison, data.frame(
      ARM = arm, METRIC = "tx_disc",
      SIM_PCT = sim_row$TX_DISC_PCT,
      TARGET_PCT = tgt$tx_disc * 100,
      DIFF = round(diff_tx, 1),
      WITHIN_TOL = abs(diff_tx) <= tol,
      stringsAsFactors = FALSE
    ))

    # Study discontinuation
    diff_study <- sim_row$STUDY_DISC_PCT - tgt$study_disc * 100
    comparison <- rbind(comparison, data.frame(
      ARM = arm, METRIC = "study_disc",
      SIM_PCT = sim_row$STUDY_DISC_PCT,
      TARGET_PCT = tgt$study_disc * 100,
      DIFF = round(diff_study, 1),
      WITHIN_TOL = abs(diff_study) <= tol,
      stringsAsFactors = FALSE
    ))
  }

  comparison
}

#' Run full calibration check and report
#' @param efficacy_summary, ae_summary, disc_summary from outcome functions
#' @param targets from load_targets()
#' @return list with all comparisons and overall pass/fail
run_calibration_check <- function(efficacy_summary, ae_summary, disc_summary, targets) {
  eff_comp <- compare_efficacy(efficacy_summary, targets)
  ae_comp <- compare_ae_rates(ae_summary, targets)
  disc_comp <- compare_discontinuation(disc_summary, targets)

  # Overall pass: all efficacy within tolerance
  eff_pass <- all(eff_comp$WITHIN_TOL)
  ae_pass_pct <- mean(ae_comp$WITHIN_TOL) * 100
  disc_pass_pct <- mean(disc_comp$WITHIN_TOL) * 100

  list(
    efficacy = eff_comp,
    ae_rates = ae_comp,
    discontinuation = disc_comp,
    summary = data.frame(
      CHECK = c("Efficacy (all arms)", "AE rates (% within tol)", "Discontinuation (% within tol)"),
      RESULT = c(ifelse(eff_pass, "PASS", "FAIL"),
                 paste0(round(ae_pass_pct, 0), "%"),
                 paste0(round(disc_pass_pct, 0), "%")),
      stringsAsFactors = FALSE
    )
  )
}

#' Generate calibration report markdown
#' @param cal_result from run_calibration_check()
#' @param output_file path to write report
generate_calibration_report <- function(cal_result, output_file = "output/analysis/calibration_report.md") {
  dir.create(dirname(output_file), recursive = TRUE, showWarnings = FALSE)

  lines <- c(
    "# Calibration Report — CWMM-LAA1 IPD Simulator",
    "",
    paste0("Generated: ", Sys.time()),
    "",
    "## Summary",
    "",
    "| Check | Result |",
    "|-------|--------|",
    paste0("| ", cal_result$summary$CHECK, " | ", cal_result$summary$RESULT, " |"),
    "",
    "## Efficacy: % Weight Change at Week 48",
    "",
    "| Arm | Simulated | Target | Diff | Pass |",
    "|-----|-----------|--------|------|------|",
    paste0("| ", cal_result$efficacy$ARM, " | ",
           cal_result$efficacy$SIM_MEAN, " | ",
           cal_result$efficacy$TARGET_MEAN, " | ",
           cal_result$efficacy$DIFF, " | ",
           ifelse(cal_result$efficacy$WITHIN_TOL, "YES", "NO"), " |"),
    "",
    "## AE Rates (% patients)",
    "",
    "| Arm | AE | Simulated | Target | Diff | Pass |",
    "|-----|----|-----------| -------|------|------|",
    paste0("| ", cal_result$ae_rates$ARM, " | ",
           cal_result$ae_rates$AETERM, " | ",
           cal_result$ae_rates$SIM_PCT, " | ",
           cal_result$ae_rates$TARGET_PCT, " | ",
           cal_result$ae_rates$DIFF, " | ",
           ifelse(cal_result$ae_rates$WITHIN_TOL, "YES", "NO"), " |"),
    "",
    "## Discontinuation",
    "",
    "| Arm | Metric | Simulated | Target | Diff | Pass |",
    "|-----|--------|-----------|--------|------|------|",
    paste0("| ", cal_result$discontinuation$ARM, " | ",
           cal_result$discontinuation$METRIC, " | ",
           cal_result$discontinuation$SIM_PCT, " | ",
           cal_result$discontinuation$TARGET_PCT, " | ",
           cal_result$discontinuation$DIFF, " | ",
           ifelse(cal_result$discontinuation$WITHIN_TOL, "YES", "NO"), " |")
  )

  writeLines(lines, output_file)
  message("Calibration report written to: ", output_file)
}
