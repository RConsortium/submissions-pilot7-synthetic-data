# calibrate.R — Calibration loop with DAG gates
# KEYNOTE-564 IPD Causal-DAG Simulator

source("R/dag_state.R")

#' Run calibration loop
#' @param max_iter integer, maximum calibration iterations
#' @param params list, initial parameters
#' @param targets list, calibration targets
#' @param verbose logical, print progress
#' @return list with calibrated_params and calibration_report
run_calibration <- function(max_iter = 8L,
                            params = load_params(),
                            targets = load_targets(),
                            verbose = TRUE) {

  tolerances <- targets$tolerances
  best_params <- params
  best_score <- Inf
  history <- list()

  for (iter in seq_len(max_iter)) {
    if (verbose) message(sprintf("\n=== Calibration Iteration %d/%d ===", iter, max_iter))

    # Run full simulation with current params
    sim_result <- run_single_simulation(best_params)

    # Evaluate all gates
    gate_results <- evaluate_gates(sim_result, targets, tolerances)

    # Compute composite score
    score <- compute_calibration_score(gate_results)

    if (verbose) {
      message(sprintf("  Composite score: %.4f (best: %.4f)", score, best_score))
      print_gate_results(gate_results)
    }

    history[[iter]] <- list(params = best_params, score = score, gates = gate_results)

    # Check if all gates pass
    if (all_gates_pass(gate_results)) {
      message(sprintf("\n[calibrate] All gates PASS at iteration %d!", iter))
      break
    }

    # Update parameters based on gate failures
    if (score < best_score) {
      best_score <- score
    }
    best_params <- adjust_parameters(best_params, gate_results, targets, iter)
  }

  # Save calibrated parameters
  calibrated_path <- "params/calibrated_params.json"
  write(toJSON(best_params, auto_unbox = TRUE, pretty = TRUE), calibrated_path)
  message(sprintf("[calibrate] Saved calibrated parameters to %s", calibrated_path))

  list(
    calibrated_params = best_params,
    final_score = best_score,
    history = history,
    all_pass = all_gates_pass(gate_results)
  )
}

#' Run a single simulation pass (used internally by calibration)
#' @param params list
#' @return list with all simulation components
run_single_simulation <- function(params) {
  source("R/baseline.R", local = TRUE)
  source("R/longitudinal.R", local = TRUE)
  source("R/recurrence.R", local = TRUE)
  source("R/post_recurrence.R", local = TRUE)
  source("R/outcomes.R", local = TRUE)

  set.seed(params$seed)

  bl <- generate_baseline(n = params$N, params = params, seed = params$seed)
  longitudinal <- simulate_longitudinal(bl, params)
  recurrence_dt <- simulate_recurrence(bl, longitudinal$ex_long, params)
  death_dt <- simulate_post_recurrence(bl, recurrence_dt, params)
  endpoints <- derive_endpoints(bl, recurrence_dt, death_dt)

  list(
    bl = bl,
    longitudinal = longitudinal,
    recurrence_dt = recurrence_dt,
    death_dt = death_dt,
    endpoints = endpoints
  )
}

# ─── Gate Evaluation ─────────────────────────────────────────────────────────

#' Evaluate all calibration gates
#' @return list of gate results
evaluate_gates <- function(sim, targets, tolerances) {

  gates <- list()

  # Gate 1: Baseline distributions
  gates$baseline <- evaluate_baseline_gate(sim$bl, targets$baseline, tolerances)

  # Gate 2: AE rates
  gates$ae_rates <- evaluate_ae_gate(sim$longitudinal$ae_long, sim$bl, targets$ae, tolerances)

  # Gate 3: Discontinuation rates
  gates$discontinuation <- evaluate_discontinuation_gate(
    sim$longitudinal$ex_long, sim$bl, targets$ae, tolerances
  )

  # Gate 4: DFS HR + KM landmarks
  gates$dfs <- evaluate_dfs_gate(sim$endpoints, targets$dfs, tolerances)

  # Gate 5: OS HR + KM landmarks
  gates$os <- evaluate_os_gate(sim$endpoints, targets$os, tolerances)

  # DAG structural gates
  gates$thyroid_lab <- evaluate_thyroid_lab_gate(sim$longitudinal)
  gates$ae_frailty <- evaluate_ae_frailty_gate(sim$longitudinal$ae_long, sim$bl)
  gates$dfs_trajectory <- evaluate_dfs_trajectory_gate(sim$endpoints, sim$recurrence_dt)
  gates$temporal_order <- evaluate_temporal_order_gate(sim$recurrence_dt, sim$death_dt)
  gates$risk_direction <- evaluate_risk_direction_gate(sim$endpoints)

  gates
}

evaluate_baseline_gate <- function(bl, bl_targets, tolerances) {
  obs_ecog0 <- mean(bl$ECOG_BL == 0L)
  obs_male <- mean(bl$SEX == "M")
  obs_m0_int_high <- mean(bl$RISK_CATEGORY == "M0_INT_HIGH")

  tol <- tolerances$baseline_absolute
  pass <- abs(obs_ecog0 - bl_targets$ecog_0) < tol &
          abs(obs_male - bl_targets$male) < tol &
          abs(obs_m0_int_high - bl_targets$risk_M0_int_high) < tol

  list(
    pass = pass,
    metrics = list(ecog0 = obs_ecog0, male = obs_male, m0_int_high = obs_m0_int_high),
    deviations = list(
      ecog0 = obs_ecog0 - bl_targets$ecog_0,
      male = obs_male - bl_targets$male,
      m0_int_high = obs_m0_int_high - bl_targets$risk_M0_int_high
    )
  )
}

evaluate_ae_gate <- function(ae_long, bl, ae_targets, tolerances) {
  n_pembro <- sum(bl$ARM == "PEMBROLIZUMAB")
  n_placebo <- sum(bl$ARM == "PLACEBO")

  # Merge arm info
  ae_with_arm <- merge(ae_long, bl[, .(SUBJID, ARM)], by = "SUBJID", all.x = TRUE)

  # Any TRAE
  trae_pembro <- ae_with_arm[ARM == "PEMBROLIZUMAB", uniqueN(SUBJID)] / n_pembro
  trae_placebo <- ae_with_arm[ARM == "PLACEBO", uniqueN(SUBJID)] / n_placebo

  # Grade 3-4
  gr34_pembro <- ae_with_arm[ARM == "PEMBROLIZUMAB" & AEGR >= 3, uniqueN(SUBJID)] / n_pembro
  gr34_placebo <- ae_with_arm[ARM == "PLACEBO" & AEGR >= 3, uniqueN(SUBJID)] / n_placebo

  # Immune-mediated
  imm_pembro <- ae_with_arm[ARM == "PEMBROLIZUMAB" &
                             AECAT %in% c("IMMUNE_MEDIATED", "THYROID"), uniqueN(SUBJID)] / n_pembro
  imm_placebo <- ae_with_arm[ARM == "PLACEBO" &
                              AECAT %in% c("IMMUNE_MEDIATED", "THYROID"), uniqueN(SUBJID)] / n_placebo

  tol <- tolerances$ae_rate_absolute
  # Immune-mediated has wider tolerance (publication categorization differs from simulated AECAT)
  imm_tol <- tol * 2.0
  pass <- abs(trae_pembro - ae_targets$trae_any_pembrolizumab) < tol &
          abs(gr34_pembro - ae_targets$trae_gr34_pembrolizumab) < tol &
          abs(imm_pembro - ae_targets$immune_mediated_pembrolizumab) < imm_tol

  list(
    pass = pass,
    metrics = list(
      trae_pembro = trae_pembro, trae_placebo = trae_placebo,
      gr34_pembro = gr34_pembro, gr34_placebo = gr34_placebo,
      imm_pembro = imm_pembro, imm_placebo = imm_placebo
    ),
    targets = list(
      trae_pembro = ae_targets$trae_any_pembrolizumab,
      gr34_pembro = ae_targets$trae_gr34_pembrolizumab,
      imm_pembro = ae_targets$immune_mediated_pembrolizumab
    )
  )
}

evaluate_discontinuation_gate <- function(ex_long, bl, ae_targets, tolerances) {
  # Patients who discontinued treatment
  disc <- ex_long[DOSE_STATUS == "DISCONTINUED", .(DISC = TRUE), by = SUBJID]
  disc_with_arm <- merge(bl[, .(SUBJID, ARM)], disc, by = "SUBJID", all.x = TRUE)
  disc_with_arm[is.na(DISC), DISC := FALSE]

  disc_pembro <- mean(disc_with_arm[ARM == "PEMBROLIZUMAB"]$DISC)
  disc_placebo <- mean(disc_with_arm[ARM == "PLACEBO"]$DISC)

  tol <- tolerances$ae_rate_absolute
  pass <- abs(disc_pembro - ae_targets$discontinuation_ae_pembrolizumab) < tol &
          abs(disc_placebo - ae_targets$discontinuation_ae_placebo) < tol

  list(
    pass = pass,
    metrics = list(disc_pembro = disc_pembro, disc_placebo = disc_placebo),
    targets = list(
      disc_pembro = ae_targets$discontinuation_ae_pembrolizumab,
      disc_placebo = ae_targets$discontinuation_ae_placebo
    )
  )
}

evaluate_dfs_gate <- function(endpoints, dfs_targets, tolerances) {
  # Compute HR
  hr_result <- compute_hr(endpoints, "DFS_DAY", "DFS_EVENT")

  # KM at 48 months
  pembro <- endpoints[ARM == "PEMBROLIZUMAB"]
  placebo <- endpoints[ARM == "PLACEBO"]
  km48_pembro <- km_at_landmark(pembro$DFS_DAY, pembro$DFS_EVENT, 48 * 30.44)
  km48_placebo <- km_at_landmark(placebo$DFS_DAY, placebo$DFS_EVENT, 48 * 30.44)

  hr_tol <- tolerances$hr_relative
  km_tol <- tolerances$km_absolute

  pass <- abs(hr_result$hr - dfs_targets$hr) / dfs_targets$hr < hr_tol &
          abs(km48_pembro - dfs_targets$km_48mo_pembrolizumab) < km_tol &
          abs(km48_placebo - dfs_targets$km_48mo_placebo) < km_tol

  list(
    pass = pass,
    metrics = list(
      hr = hr_result$hr, hr_ci = c(hr_result$hr_lower, hr_result$hr_upper),
      km48_pembro = km48_pembro, km48_placebo = km48_placebo,
      events_pembro = sum(pembro$DFS_EVENT), events_placebo = sum(placebo$DFS_EVENT)
    ),
    targets = list(
      hr = dfs_targets$hr,
      km48_pembro = dfs_targets$km_48mo_pembrolizumab,
      km48_placebo = dfs_targets$km_48mo_placebo
    )
  )
}

evaluate_os_gate <- function(endpoints, os_targets, tolerances) {
  hr_result <- compute_hr(endpoints, "OS_DAY", "OS_EVENT")

  pembro <- endpoints[ARM == "PEMBROLIZUMAB"]
  placebo <- endpoints[ARM == "PLACEBO"]
  km48_pembro <- km_at_landmark(pembro$OS_DAY, pembro$OS_EVENT, 48 * 30.44)
  km48_placebo <- km_at_landmark(placebo$OS_DAY, placebo$OS_EVENT, 48 * 30.44)

  hr_tol <- tolerances$hr_relative
  km_tol <- tolerances$km_absolute

  pass <- abs(hr_result$hr - os_targets$hr) / os_targets$hr < hr_tol &
          abs(km48_pembro - os_targets$km_48mo_pembrolizumab) < km_tol &
          abs(km48_placebo - os_targets$km_48mo_placebo) < km_tol

  list(
    pass = pass,
    metrics = list(
      hr = hr_result$hr, hr_ci = c(hr_result$hr_lower, hr_result$hr_upper),
      km48_pembro = km48_pembro, km48_placebo = km48_placebo,
      events_pembro = sum(pembro$OS_EVENT), events_placebo = sum(placebo$OS_EVENT)
    ),
    targets = list(
      hr = os_targets$hr,
      km48_pembro = os_targets$km_48mo_pembrolizumab,
      km48_placebo = os_targets$km_48mo_placebo
    )
  )
}

# ─── DAG Structural Gates ────────────────────────────────────────────────────

evaluate_thyroid_lab_gate <- function(longitudinal) {
  # TSH should be > 10 at hypothyroidism AE visits
  ae_hypo <- longitudinal$ae_long[AETERM == "HYPOTHYROIDISM"]
  if (nrow(ae_hypo) == 0) return(list(pass = TRUE, note = "No hypothyroid events"))

  ae_hypo_visits <- ae_hypo[, .(SUBJID, AESTDT)]
  lb_tsh <- longitudinal$lb_long[LBTEST == "TSH"]

  # Join: find TSH at the closest visit to AE onset

  merged <- ae_hypo_visits[lb_tsh, on = .(SUBJID), allow.cartesian = TRUE, nomatch = 0]
  merged[, day_diff := abs(AESTDT - VISIT_DAY)]
  closest <- merged[, .SD[which.min(day_diff)], by = .(SUBJID, AESTDT)]

  # Check that TSH is elevated
  pct_elevated <- mean(closest$LBORRES > 10, na.rm = TRUE)
  pass <- pct_elevated > 0.70  # Allow some noise

  list(pass = pass, pct_tsh_elevated = pct_elevated)
}

evaluate_ae_frailty_gate <- function(ae_long, bl) {
  # Within-patient correlation across immune AE types
  # Include ALL patients (zeros for those without events) to detect frailty clustering
  if (nrow(ae_long) == 0) return(list(pass = FALSE, note = "No AEs"))

  # Count immune-related AE types per patient (includes SKIN as these share frailty)
  immune_aes <- ae_long[AECAT %in% c("IMMUNE_MEDIATED", "THYROID", "SKIN")]
  if (nrow(immune_aes) == 0) return(list(pass = FALSE, note = "No immune AEs"))

  counts <- dcast(immune_aes, SUBJID ~ AETERM, value.var = "AEGR", fun.aggregate = length)

  # Merge with all patients to include zeros
  all_patients <- data.table(SUBJID = bl$SUBJID)
  counts <- merge(all_patients, counts, by = "SUBJID", all.x = TRUE)
  ae_cols <- setdiff(names(counts), "SUBJID")
  if (length(ae_cols) < 2) return(list(pass = FALSE, note = "Insufficient AE types"))

  # Replace NA with 0 (patients with no events of that type)
  for (col in ae_cols) {
    set(counts, which(is.na(counts[[col]])), col, 0L)
  }

  # Compute mean pairwise correlation across all patients
  corr_mat <- cor(counts[, ..ae_cols], use = "pairwise.complete.obs")
  upper_tri <- corr_mat[upper.tri(corr_mat)]
  mean_corr <- mean(upper_tri, na.rm = TRUE)

  list(pass = mean_corr > 0.15, mean_correlation = mean_corr)
}

evaluate_dfs_trajectory_gate <- function(endpoints, recurrence_dt) {
  # DFS_DAY should correlate highly with latent_recurrence_day for events
  events <- endpoints[DFS_EVENT == 1L & DFS_EVENT_TYPE == "RECURRENCE"]
  if (nrow(events) == 0) return(list(pass = TRUE, note = "No DFS events"))

  merged <- merge(events[, .(SUBJID, DFS_DAY)],
                  recurrence_dt[, .(SUBJID, LATENT_RECURRENCE_DAY)],
                  by = "SUBJID")

  corr <- cor(merged$DFS_DAY, merged$LATENT_RECURRENCE_DAY, use = "complete.obs")
  list(pass = corr > 0.95, correlation = corr)
}

evaluate_temporal_order_gate <- function(recurrence_dt, death_dt) {
  # All post-recurrence deaths must have death_day >= recurrence_day
  merged <- merge(
    recurrence_dt[!is.na(OBSERVED_RECURRENCE_DAY), .(SUBJID, OBSERVED_RECURRENCE_DAY)],
    death_dt[DEATH_CAUSE == "POST_RECURRENCE" & !is.na(DEATH_DAY), .(SUBJID, DEATH_DAY)],
    by = "SUBJID"
  )

  if (nrow(merged) == 0) return(list(pass = TRUE, note = "No post-recurrence deaths"))

  violations <- sum(merged$DEATH_DAY < merged$OBSERVED_RECURRENCE_DAY)
  list(pass = violations == 0, violations = violations)
}

evaluate_risk_direction_gate <- function(endpoints) {
  # M1 NED should have worst DFS, M0 int-high best
  median_dfs <- endpoints[DFS_EVENT == 1L, .(median_dfs = median(DFS_DAY)), by = RISK_CATEGORY]

  if (nrow(median_dfs) < 2) return(list(pass = TRUE, note = "Insufficient risk categories"))

  m0ih <- median_dfs[RISK_CATEGORY == "M0_INT_HIGH", median_dfs]
  m1ned <- median_dfs[RISK_CATEGORY == "M1_NED", median_dfs]

  if (length(m0ih) == 0 || length(m1ned) == 0) {
    return(list(pass = TRUE, note = "Missing risk category"))
  }

  pass <- m1ned < m0ih
  list(pass = pass, m0_int_high_median = m0ih, m1_ned_median = m1ned)
}

# ─── Scoring and Parameter Adjustment ────────────────────────────────────────

compute_calibration_score <- function(gate_results) {
  # Weighted sum of deviations
  score <- 0

  # DFS HR deviation (weight 3)
  if (!is.null(gate_results$dfs$metrics$hr) && !is.null(gate_results$dfs$targets$hr)) {
    score <- score + 3 * abs(gate_results$dfs$metrics$hr - gate_results$dfs$targets$hr)
  }

  # OS HR deviation (weight 3)
  if (!is.null(gate_results$os$metrics$hr) && !is.null(gate_results$os$targets$hr)) {
    score <- score + 3 * abs(gate_results$os$metrics$hr - gate_results$os$targets$hr)
  }

  # KM landmark deviations (weight 2)
  if (!is.null(gate_results$dfs$metrics$km48_pembro)) {
    score <- score + 2 * abs(gate_results$dfs$metrics$km48_pembro - gate_results$dfs$targets$km48_pembro)
    score <- score + 2 * abs(gate_results$dfs$metrics$km48_placebo - gate_results$dfs$targets$km48_placebo)
  }

  # AE rate deviations (weight 1)
  if (!is.null(gate_results$ae_rates$metrics$trae_pembro)) {
    score <- score + abs(gate_results$ae_rates$metrics$trae_pembro - gate_results$ae_rates$targets$trae_pembro)
  }

  score
}

all_gates_pass <- function(gate_results) {
  all(sapply(gate_results, function(g) isTRUE(g$pass)))
}

#' Adjust parameters based on gate failures
adjust_parameters <- function(params, gate_results, targets, iter) {
  step_size <- 0.8^(iter - 1)  # Decreasing step size

  # Adjust recurrence parameters if DFS gate fails
  if (!isTRUE(gate_results$dfs$pass)) {
    obs_hr <- gate_results$dfs$metrics$hr
    target_hr <- gate_results$dfs$targets$hr

    if (!is.null(obs_hr) && !is.null(target_hr)) {
      # If HR too high (less treatment effect), increase treatment effect
      if (obs_hr > target_hr) {
        params$recurrence$treatment_effect_on_treatment <-
          params$recurrence$treatment_effect_on_treatment - 0.05 * step_size
      } else {
        params$recurrence$treatment_effect_on_treatment <-
          params$recurrence$treatment_effect_on_treatment + 0.05 * step_size
      }
    }

    # Adjust baseline hazard for KM landmarks
    obs_km_placebo <- gate_results$dfs$metrics$km48_placebo
    target_km_placebo <- gate_results$dfs$targets$km48_placebo
    if (!is.null(obs_km_placebo) && !is.null(target_km_placebo)) {
      if (obs_km_placebo < target_km_placebo) {
        # Too many events in placebo: increase scale (longer times)
        params$recurrence$weibull_scale_M0_int_high <-
          params$recurrence$weibull_scale_M0_int_high * (1 + 0.05 * step_size)
      } else {
        params$recurrence$weibull_scale_M0_int_high <-
          params$recurrence$weibull_scale_M0_int_high * (1 - 0.05 * step_size)
      }
    }
  }

  # Adjust AE parameters if AE gate fails
  if (!isTRUE(gate_results$ae_rates$pass)) {
    obs_trae <- gate_results$ae_rates$metrics$trae_pembro
    target_trae <- gate_results$ae_rates$targets$trae_pembro

    if (!is.null(obs_trae) && !is.null(target_trae)) {
      ratio <- target_trae / max(obs_trae, 0.01)
      # Scale all per-cycle AE probabilities
      ae_names <- names(params$ae_per_cycle)
      for (nm in ae_names) {
        params$ae_per_cycle[[nm]]$base_prob_pembro <-
          params$ae_per_cycle[[nm]]$base_prob_pembro * (1 + (ratio - 1) * 0.3 * step_size)
      }
    }
  }

  # Adjust discontinuation parameters
  if (!isTRUE(gate_results$discontinuation$pass)) {
    obs_disc <- gate_results$discontinuation$metrics$disc_pembro
    target_disc <- gate_results$discontinuation$targets$disc_pembro
    if (!is.null(obs_disc) && !is.null(target_disc)) {
      if (obs_disc < target_disc) {
        params$dose_modification$discontinue_prob_gr3_immune <-
          params$dose_modification$discontinue_prob_gr3_immune * (1 + 0.10 * step_size)
      } else {
        params$dose_modification$discontinue_prob_gr3_immune <-
          params$dose_modification$discontinue_prob_gr3_immune * (1 - 0.10 * step_size)
      }
    }
  }

  params
}

#' Print gate results summary
print_gate_results <- function(gate_results) {
  for (nm in names(gate_results)) {
    g <- gate_results[[nm]]
    status <- if (isTRUE(g$pass)) "PASS" else "FAIL"
    message(sprintf("  Gate %-20s: %s", nm, status))
  }
}
