# outcomes.R — Layer Y: Derived endpoints from trajectories
# =========================================================

#' Derive primary and secondary endpoints from longitudinal data
#' Uses the "efficacy estimand" (hypothetical strategy): for patients who
#' discontinue, extrapolate their on-treatment trajectory to week 48 using
#' the individual's exponential approach model. This matches the MMRM-based
#' estimand reported in the publication.
#' @param baseline data.frame from generate_baseline()
#' @param weight_long data.frame from simulate_longitudinal()
#' @param disposition data.frame from simulate_longitudinal()
#' @return data.frame with one row per patient, all derived endpoints
derive_outcomes <- function(baseline, weight_long, disposition) {

  n <- nrow(baseline)

  outcomes <- data.frame(
    SUBJID = baseline$SUBJID,
    ARM = baseline$ARM,
    WEIGHT_0 = baseline$WEIGHT_0,
    WEIGHT_48 = NA_real_,
    PCT_CHANGE_48 = NA_real_,
    ABS_CHANGE_48 = NA_real_,
    BMI_48 = NA_real_,
    RESP_5PCT = NA,
    RESP_10PCT = NA,
    RESP_15PCT = NA,
    RESP_20PCT = NA,
    COMPLETED_TX = !disposition$TX_DISC,
    TX_DISC_WEEK = disposition$TX_DISC_WEEK,
    STUDY_DISC = disposition$STUDY_DISC,
    stringsAsFactors = FALSE
  )

  for (i in seq_len(n)) {
    subj <- baseline$SUBJID[i]
    subj_data <- weight_long[weight_long$SUBJID == subj, ]

    if (disposition$TX_DISC[i]) {
      # Efficacy estimand: use last ON-TREATMENT observation and extrapolate
      # Find last on-treatment measurement
      on_tx_rows <- which(subj_data$ON_TREATMENT == TRUE & !is.na(subj_data$PCT_CHANGE))
      if (length(on_tx_rows) > 0) {
        last_on_tx <- on_tx_rows[length(on_tx_rows)]
        last_week <- subj_data$VISIT_WEEK[last_on_tx]
        last_pct <- subj_data$PCT_CHANGE[last_on_tx]

        # Extrapolate: if the patient was still approaching nadir,
        # scale by ratio of (1-exp(-k*48/48))/(1-exp(-k*last_week/48))
        # This gives the projected value at week 48 if treatment continued
        k <- 3.0  # approach rate
        if (last_week > 0 && last_week < 48) {
          approach_at_last <- 1 - exp(-k * last_week / 48)
          approach_at_48 <- 1 - exp(-k)  # ~0.95
          if (approach_at_last > 0.1) {
            projected_pct <- last_pct * (approach_at_48 / approach_at_last)
          } else {
            projected_pct <- last_pct
          }
        } else {
          projected_pct <- last_pct
        }

        outcomes$PCT_CHANGE_48[i] <- projected_pct
        outcomes$WEIGHT_48[i] <- baseline$WEIGHT_0[i] * (1 + projected_pct / 100)
        outcomes$ABS_CHANGE_48[i] <- outcomes$WEIGHT_48[i] - baseline$WEIGHT_0[i]
        outcomes$BMI_48[i] <- outcomes$WEIGHT_48[i] / (baseline$HEIGHT[i] / 100)^2
      }
    } else {
      # Completed treatment: use week 48 value
      w48_row <- which(subj_data$VISIT_WEEK == 48)
      if (length(w48_row) == 1 && !is.na(subj_data$WEIGHT[w48_row])) {
        outcomes$WEIGHT_48[i] <- subj_data$WEIGHT[w48_row]
        outcomes$PCT_CHANGE_48[i] <- subj_data$PCT_CHANGE[w48_row]
        outcomes$ABS_CHANGE_48[i] <- subj_data$WEIGHT[w48_row] - baseline$WEIGHT_0[i]
        outcomes$BMI_48[i] <- subj_data$BMI[w48_row]
      } else {
        # Study discontinued but didn't tx_disc: use last available
        avail <- which(!is.na(subj_data$WEIGHT))
        if (length(avail) > 0) {
          last_row <- avail[length(avail)]
          outcomes$WEIGHT_48[i] <- subj_data$WEIGHT[last_row]
          outcomes$PCT_CHANGE_48[i] <- subj_data$PCT_CHANGE[last_row]
          outcomes$ABS_CHANGE_48[i] <- subj_data$WEIGHT[last_row] - baseline$WEIGHT_0[i]
          outcomes$BMI_48[i] <- subj_data$BMI[last_row]
        }
      }
    }

    # Responder categories
    if (!is.na(outcomes$PCT_CHANGE_48[i])) {
      outcomes$RESP_5PCT[i] <- outcomes$PCT_CHANGE_48[i] <= -5
      outcomes$RESP_10PCT[i] <- outcomes$PCT_CHANGE_48[i] <= -10
      outcomes$RESP_15PCT[i] <- outcomes$PCT_CHANGE_48[i] <= -15
      outcomes$RESP_20PCT[i] <- outcomes$PCT_CHANGE_48[i] <= -20
    }
  }

  outcomes
}

#' Compute efficacy estimand (treatment policy: all randomized, MMRM-like)
#' This uses all available data including post-discontinuation measurements
#' to approximate the efficacy estimand from the publication
#' @param outcomes data.frame from derive_outcomes()
#' @return data.frame with per-arm summary
compute_efficacy_summary <- function(outcomes) {
  arms <- unique(outcomes$ARM)
  summary_df <- data.frame(
    ARM = character(),
    N = integer(),
    MEAN_PCT_CHANGE = numeric(),
    SD_PCT_CHANGE = numeric(),
    SE = numeric(),
    CI_LOWER = numeric(),
    CI_UPPER = numeric(),
    stringsAsFactors = FALSE
  )

  for (arm in ARM_LABELS) {
    arm_data <- outcomes[outcomes$ARM == arm, ]
    pct_vals <- arm_data$PCT_CHANGE_48[!is.na(arm_data$PCT_CHANGE_48)]
    n_eff <- length(pct_vals)
    if (n_eff > 0) {
      m <- mean(pct_vals)
      s <- sd(pct_vals)
      se <- s / sqrt(n_eff)
      summary_df <- rbind(summary_df, data.frame(
        ARM = arm,
        N = n_eff,
        MEAN_PCT_CHANGE = round(m, 2),
        SD_PCT_CHANGE = round(s, 2),
        SE = round(se, 2),
        CI_LOWER = round(m - 1.96 * se, 2),
        CI_UPPER = round(m + 1.96 * se, 2),
        stringsAsFactors = FALSE
      ))
    }
  }

  summary_df
}

#' Compute AE incidence summary
#' @param ae_long data.frame from simulate_longitudinal()
#' @param baseline data.frame for denominator
#' @return data.frame with AE rates per arm
compute_ae_summary <- function(ae_long, baseline) {
  ae_types <- c("nausea", "fatigue", "diarrhoea", "constipation",
                "decreased_appetite", "vomiting", "alopecia", "headache")

  result <- expand.grid(ARM = ARM_LABELS, AETERM = ae_types, stringsAsFactors = FALSE)
  result$N_PATIENTS <- NA_integer_
  result$N_WITH_AE <- NA_integer_
  result$PCT <- NA_real_


  for (arm in ARM_LABELS) {
    n_arm <- sum(baseline$ARM == arm)
    for (ae in ae_types) {
      idx <- which(result$ARM == arm & result$AETERM == ae)
      subjs_with_ae <- unique(ae_long$SUBJID[ae_long$ARM == arm & ae_long$AETERM == ae])
      result$N_PATIENTS[idx] <- n_arm
      result$N_WITH_AE[idx] <- length(subjs_with_ae)
      result$PCT[idx] <- round(length(subjs_with_ae) / n_arm * 100, 1)
    }
  }

  result
}

#' Compute discontinuation summary
#' @param disposition data.frame from simulate_longitudinal()
#' @return data.frame with disc rates per arm
compute_disc_summary <- function(disposition) {
  result <- data.frame(ARM = ARM_LABELS, stringsAsFactors = FALSE)
  result$N <- NA_integer_
  result$TX_DISC_N <- NA_integer_
  result$TX_DISC_PCT <- NA_real_
  result$AE_DISC_N <- NA_integer_
  result$AE_DISC_PCT <- NA_real_
  result$STUDY_DISC_N <- NA_integer_
  result$STUDY_DISC_PCT <- NA_real_

  for (j in seq_along(ARM_LABELS)) {
    arm <- ARM_LABELS[j]
    arm_disp <- disposition[disposition$ARM == arm, ]
    n_arm <- nrow(arm_disp)
    result$N[j] <- n_arm
    result$TX_DISC_N[j] <- sum(arm_disp$TX_DISC)
    result$TX_DISC_PCT[j] <- round(sum(arm_disp$TX_DISC) / n_arm * 100, 1)
    result$AE_DISC_N[j] <- sum(arm_disp$TX_DISC_REASON == "Adverse Event", na.rm = TRUE)
    result$AE_DISC_PCT[j] <- round(sum(arm_disp$TX_DISC_REASON == "Adverse Event", na.rm = TRUE) / n_arm * 100, 1)
    result$STUDY_DISC_N[j] <- sum(arm_disp$STUDY_DISC)
    result$STUDY_DISC_PCT[j] <- round(sum(arm_disp$STUDY_DISC) / n_arm * 100, 1)
  }

  result
}
