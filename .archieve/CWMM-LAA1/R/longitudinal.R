# longitudinal.R — Layer Lₜ: Weight trajectory, AEs, discontinuation
# ===================================================================

source("R/dag_state.R")

#' Emax dose-response: maps dose to maximum % weight loss
#' @param dose Numeric dose in mg
#' @param emax Maximum possible effect (negative %)
#' @param ed50 Dose producing 50% of Emax
#' @return Expected max % weight loss for this dose
emax_response <- function(dose, emax, ed50) {
  if (dose <= 0) return(0)
  emax * dose / (ed50 + dose)
}

#' Simulate longitudinal data for all patients
#' @param baseline data.frame from generate_baseline()
#' @param params Parameter list
#' @return list with weight_long, ae_long, disposition
simulate_longitudinal <- function(baseline, params) {

  n <- nrow(baseline)
  wtp <- params$weight_trajectory
  ae_model <- params$ae_model
  disc_params <- params$discontinuation
  mc <- params$metabolic_coupling

  # Pre-allocate output structures
  weight_long <- data.frame(
    SUBJID = rep(baseline$SUBJID, each = N_VISITS),
    ARM = rep(baseline$ARM, each = N_VISITS),
    VISIT_WEEK = rep(VISIT_WEEKS, n),
    WEIGHT = NA_real_,
    PCT_CHANGE = NA_real_,
    BMI = NA_real_,
    ON_TREATMENT = TRUE,
    stringsAsFactors = FALSE
  )

  ae_records <- list()
  disposition <- data.frame(
    SUBJID = baseline$SUBJID,
    ARM = baseline$ARM,
    TX_DISC = FALSE,
    TX_DISC_WEEK = NA_real_,
    TX_DISC_REASON = NA_character_,
    STUDY_DISC = FALSE,
    STUDY_DISC_WEEK = NA_real_,
    COMPLETED = TRUE,
    stringsAsFactors = FALSE
  )

  # Metabolic markers storage
  metabolic_long <- data.frame(
    SUBJID = rep(baseline$SUBJID, each = N_VISITS),
    VISIT_WEEK = rep(VISIT_WEEKS, n),
    HBA1C = NA_real_,
    GLUC = NA_real_,
    INSULIN = NA_real_,
    CHOL = NA_real_,
    LDL = NA_real_,
    HDL = NA_real_,
    TRIG = NA_real_,
    HSCRP = NA_real_,
    SYSBP = NA_real_,
    DIABP = NA_real_,
    PULSE = NA_real_,
    stringsAsFactors = FALSE
  )

  # Emax parameters
  emax_val <- wtp$emax
  ed50_val <- wtp$ed50

  for (i in seq_len(n)) {
    arm_i <- baseline$ARM[i]
    wt0 <- baseline$WEIGHT_0[i]
    height_i <- baseline$HEIGHT[i]
    f_met <- baseline$F_METABOLIC[i]
    f_gi <- baseline$F_GI[i]
    f_fat <- baseline$F_FATIGUE[i]
    f_drop <- baseline$F_DROPOUT[i]

    on_tx <- TRUE
    tx_disc_week <- Inf
    study_disc_week <- Inf
    patient_aes <- list()
    last_valid_pct <- 0

    row_offset <- (i - 1) * N_VISITS

    # --- Pre-determine discontinuation timing ---
    # Use per-arm rate + frailty to determine if/when patient discontinues
    base_tx_disc_rate <- disc_params$target_tx_disc[[arm_i]]
    # Modulate by frailty
    disc_prob <- pmin(0.95, pmax(0.01, base_tx_disc_rate + disc_params$gamma_frailty * f_drop * 0.1))

    will_disc_tx <- runif(1) < disc_prob
    if (will_disc_tx) {
      # Determine timing: uniform distribution over treatment period, weighted earlier
      disc_timing <- rbeta(1, 1.5, 2.5)  # Skewed toward early discontinuation
      tx_disc_week <- ceiling(disc_timing * 48)
      # Snap to nearest visit
      tx_disc_week <- VISIT_WEEKS[which.min(abs(VISIT_WEEKS - tx_disc_week))]
      if (tx_disc_week == 0) tx_disc_week <- VISIT_WEEKS[2]

      disposition$TX_DISC[i] <- TRUE
      disposition$TX_DISC_WEEK[i] <- tx_disc_week
      disposition$COMPLETED[i] <- FALSE

      # Determine reason (AE vs other)
      ae_frac <- disc_params$ae_disc_fraction[[arm_i]]
      if (runif(1) < ae_frac) {
        disposition$TX_DISC_REASON[i] <- "Adverse Event"
      } else {
        disposition$TX_DISC_REASON[i] <- sample(
          c("Withdrawal by Subject", "Lost to Follow-up", "Other"),
          1, prob = c(0.5, 0.3, 0.2))
      }

      # Study discontinuation
      study_disc_rate <- disc_params$target_study_disc[[arm_i]]
      # Conditional on tx disc, probability of also leaving study
      p_study_given_tx <- study_disc_rate / base_tx_disc_rate
      p_study_given_tx <- pmin(1.0, p_study_given_tx)
      if (runif(1) < p_study_given_tx) {
        study_disc_week <- tx_disc_week
        disposition$STUDY_DISC[i] <- TRUE
        disposition$STUDY_DISC_WEEK[i] <- study_disc_week
      }
    }

    # --- Pre-determine AEs (patient-level) ---
    # For each AE type, determine if patient experiences it and when
    ae_types <- names(ae_model$target_rates)
    for (ae_name in ae_types) {
      ae_info <- ae_model$target_rates[[ae_name]]
      base_rate <- ae_info[[arm_i]]
      if (is.null(base_rate)) base_rate <- 0

      # Modulate by frailty
      if (ae_info$frailty_type == "f_GI") {
        frailty_mod <- ae_model$gamma_GI * f_gi * 0.15
      } else if (ae_info$frailty_type == "f_fatigue") {
        frailty_mod <- ae_model$gamma_fatigue * f_fat * 0.15
      } else {
        frailty_mod <- 0
      }
      adj_rate <- pmin(0.98, pmax(0.001, base_rate + frailty_mod))

      if (runif(1) < adj_rate) {
        # Patient will experience this AE — determine timing
        # AEs more likely early in treatment (especially GI)
        if (ae_info$frailty_type == "f_GI") {
          ae_week <- ceiling(rbeta(1, 1.2, 3) * min(48, tx_disc_week))
        } else {
          ae_week <- ceiling(runif(1) * min(48, tx_disc_week))
        }
        ae_week <- max(1, ae_week)

        # Duration
        duration <- sample(1:12, 1, prob = c(3, 3, 2, 2, 1, 1, 1, 1, 1, 1, 1, 1))
        end_week <- min(ae_week + duration, 48)

        # Severity
        sev_roll <- runif(1)
        severity <- if (sev_roll < 0.55) "Mild" else if (sev_roll < 0.88) "Moderate" else "Severe"

        patient_aes[[length(patient_aes) + 1]] <- data.frame(
          SUBJID = baseline$SUBJID[i],
          ARM = arm_i,
          AETERM = ae_name,
          AESTDTC_WEEK = ae_week,
          AEENDTC_WEEK = end_week,
          AESEV = severity,
          AEREL = ifelse(base_rate > 0.05, "Related", "Not Related"),
          AESER = ifelse(severity == "Severe" & runif(1) < 0.08, "Yes", "No"),
          stringsAsFactors = FALSE
        )

        # Some patients may experience a second episode
        if (runif(1) < base_rate * 0.3 && end_week < 44) {
          ae_week2 <- end_week + sample(2:8, 1)
          if (ae_week2 <= min(48, tx_disc_week)) {
            end_week2 <- min(ae_week2 + sample(1:6, 1), 48)
            sev2 <- if (runif(1) < 0.7) "Mild" else "Moderate"
            patient_aes[[length(patient_aes) + 1]] <- data.frame(
              SUBJID = baseline$SUBJID[i],
              ARM = arm_i,
              AETERM = ae_name,
              AESTDTC_WEEK = ae_week2,
              AEENDTC_WEEK = end_week2,
              AESEV = sev2,
              AEREL = ifelse(base_rate > 0.05, "Related", "Not Related"),
              AESER = "No",
              stringsAsFactors = FALSE
            )
          }
        }
      }
    }

    # --- Longitudinal weight and metabolic trajectory ---
    for (v in seq_len(N_VISITS)) {
      week <- VISIT_WEEKS[v]
      idx <- row_offset + v

      # Check treatment status
      if (will_disc_tx && week > tx_disc_week) {
        on_tx <- FALSE
      }

      # Effective dose
      if (on_tx && week <= 48) {
        eff_dose <- get_effective_dose(arm_i, week, params)
      } else {
        eff_dose <- 0
      }

      # Dose schedule info
      sched <- params$dose_schedule[[arm_i]]

      # --- Weight trajectory (Emax model) ---
      if (week == 0) {
        wt_pct <- 0
      } else if (on_tx && week <= 48) {
        # For escalation arms, compute blended response
        if (!is.null(sched$escalation_week) && !is.na(sched$escalation_week) && week >= sched$escalation_week) {
          max_loss_p1 <- emax_response(sched$phase1, emax_val, ed50_val)
          max_loss_p2 <- emax_response(sched$phase2, emax_val, ed50_val)
          t_esc <- sched$escalation_week / 48
          wt_at_esc <- max_loss_p1 * (1 - exp(-wtp$k_approach * t_esc))
          t_post <- (week - sched$escalation_week) / (48 - sched$escalation_week)
          wt_pct <- wt_at_esc + (max_loss_p2 - wt_at_esc) * (1 - exp(-wtp$k_approach * t_post))
        } else {
          max_loss <- emax_response(eff_dose, emax_val, ed50_val)
          wt_pct <- max_loss * (1 - exp(-wtp$k_approach * week / 48))
        }
        # Individual metabolic responsiveness
        wt_pct <- wt_pct + f_met * wtp$sigma_resp * (1 - exp(-wtp$k_approach * week / 48))
        # Placebo drift
        wt_pct <- wt_pct + wtp$placebo_drift * (week / 48)
        # Visit noise
        wt_pct <- wt_pct + rnorm(1, 0, wtp$sigma_noise_visit)
        last_valid_pct <- wt_pct
      } else if (!on_tx && week <= 48) {
        # Post-discontinuation: partial regain
        weeks_since_disc <- week - tx_disc_week
        regain <- last_valid_pct * wtp$regain_fraction * (1 - exp(-wtp$k_regain * weeks_since_disc))
        wt_pct <- last_valid_pct - regain + rnorm(1, 0, wtp$sigma_noise_visit)
      } else {
        # Week 58 follow-up
        weeks_off <- week - 48
        regain <- last_valid_pct * wtp$regain_fraction * (1 - exp(-wtp$k_regain * weeks_off))
        wt_pct <- last_valid_pct - regain + rnorm(1, 0, wtp$sigma_noise_visit)
      }

      current_wt <- wt0 * (1 + wt_pct / 100)
      weight_long$WEIGHT[idx] <- round(current_wt, 1)
      weight_long$PCT_CHANGE[idx] <- round(wt_pct, 2)
      weight_long$BMI[idx] <- round(current_wt / (height_i / 100)^2, 1)
      weight_long$ON_TREATMENT[idx] <- on_tx

      # --- Metabolic markers ---
      metabolic_long$HBA1C[idx] <- round(baseline$HBA1C_0[i] + mc$rho_hba1c * wt_pct +
                                           rnorm(1, 0, mc$noise_sd_fraction * (abs(mc$rho_hba1c * wt_pct) + 0.3)), 1)
      metabolic_long$GLUC[idx] <- round(pmax(3.0, baseline$GLUC_0[i] + mc$rho_glucose * wt_pct +
                                               rnorm(1, 0, 0.2)), 2)
      ins_change <- baseline$INSULIN_0[i] * (1 + mc$rho_insulin_pct * wt_pct / 100)
      metabolic_long$INSULIN[idx] <- round(pmax(10, ins_change + rnorm(1, 0, 5)), 1)
      metabolic_long$CHOL[idx] <- round(baseline$CHOL_0[i] + mc$rho_ldl * wt_pct + rnorm(1, 0, 0.2), 2)
      metabolic_long$LDL[idx] <- round(pmax(0.8, baseline$LDL_0[i] + mc$rho_ldl * wt_pct + rnorm(1, 0, 0.2)), 2)
      metabolic_long$HDL[idx] <- round(pmax(0.4, baseline$HDL_0[i] + mc$rho_hdl * wt_pct + rnorm(1, 0, 0.05)), 2)
      trig_change <- baseline$TRIG_0[i] * (1 + mc$rho_trig_pct * wt_pct / 100)
      metabolic_long$TRIG[idx] <- round(pmax(0.3, trig_change + rnorm(1, 0, 0.1)), 2)
      crp_change <- baseline$HSCRP_0[i] * (1 + mc$rho_hscrp_pct * wt_pct / 100)
      metabolic_long$HSCRP[idx] <- round(pmax(0.1, crp_change + rnorm(1, 0, 0.3)), 2)
      metabolic_long$SYSBP[idx] <- round(baseline$SYSBP_0[i] + mc$rho_sysbp * wt_pct + rnorm(1, 0, 4), 0)
      metabolic_long$DIABP[idx] <- round(baseline$DIABP_0[i] + mc$rho_diabp * wt_pct + rnorm(1, 0, 3), 0)
      metabolic_long$PULSE[idx] <- round(baseline$PULSE_0[i] + rnorm(1, 0, 3), 0)

      # If study discontinued, mark subsequent visits as missing
      if (!is.na(study_disc_week) && is.finite(study_disc_week) && week > study_disc_week) {
        weight_long$WEIGHT[idx] <- NA
        weight_long$PCT_CHANGE[idx] <- NA
        weight_long$BMI[idx] <- NA
        metabolic_long$HBA1C[idx] <- NA
        metabolic_long$GLUC[idx] <- NA
        metabolic_long$INSULIN[idx] <- NA
        metabolic_long$CHOL[idx] <- NA
        metabolic_long$LDL[idx] <- NA
        metabolic_long$HDL[idx] <- NA
        metabolic_long$TRIG[idx] <- NA
        metabolic_long$HSCRP[idx] <- NA
        metabolic_long$SYSBP[idx] <- NA
        metabolic_long$DIABP[idx] <- NA
        metabolic_long$PULSE[idx] <- NA
      }
    }

    # Collect AE records
    if (length(patient_aes) > 0) {
      ae_records[[i]] <- do.call(rbind, patient_aes)
    }
  }

  # Combine AE records
  ae_long <- if (length(ae_records) > 0) do.call(rbind, ae_records[!sapply(ae_records, is.null)]) else
    data.frame(SUBJID = character(), ARM = character(), AETERM = character(),
               AESTDTC_WEEK = numeric(), AEENDTC_WEEK = numeric(),
               AESEV = character(), AEREL = character(), AESER = character(),
               stringsAsFactors = FALSE)

  list(
    weight_long = weight_long,
    metabolic_long = metabolic_long,
    ae_long = ae_long,
    disposition = disposition
  )
}
