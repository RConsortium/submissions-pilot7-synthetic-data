# post_recurrence.R — Subsequent therapy + post-recurrence survival + background mortality
# KEYNOTE-564 IPD Causal-DAG Simulator

source("R/dag_state.R")

#' Simulate post-recurrence events and death for all patients
#' @param bl data.table, baseline characteristics
#' @param recurrence_dt data.table, recurrence outcomes
#' @param params list, simulation parameters
#' @return data.table with death information per patient
simulate_post_recurrence <- function(bl, recurrence_dt, params = load_params()) {

  n <- nrow(bl)
  pr_params <- params$post_recurrence_survival
  bg_params <- params$background_mortality

  # Merge baseline with recurrence
  combined <- merge(bl[, .(SUBJID, ARM, AGE, ECOG_BL, RISK_CATEGORY)],
                    recurrence_dt, by = "SUBJID", all.x = TRUE)

  # Compute death day for each patient
  death_dt <- combined[, {
    death_day <- simulate_patient_death(
      has_recurrence = !is.na(OBSERVED_RECURRENCE_DAY),
      recurrence_day = OBSERVED_RECURRENCE_DAY,
      recurrence_type = RECURRENCE_TYPE,
      arm = ARM,
      age = AGE,
      ecog_bl = ECOG_BL,
      pr_params = pr_params,
      bg_params = bg_params
    )
    list(
      DEATH_DAY = death_day$death_day,
      DEATH_CAUSE = death_day$cause,
      SUBSEQUENT_THERAPY = death_day$subsequent_therapy
    )
  }, by = SUBJID]

  message(sprintf("[post_recurrence] Deaths: %d (post-recurrence: %d, background: %d)",
                  sum(!is.na(death_dt$DEATH_DAY) & death_dt$DEATH_DAY <= KN564_CONSTANTS$ADMIN_CENSOR_DAY),
                  sum(death_dt$DEATH_CAUSE == "POST_RECURRENCE" & !is.na(death_dt$DEATH_DAY) &
                      death_dt$DEATH_DAY <= KN564_CONSTANTS$ADMIN_CENSOR_DAY, na.rm = TRUE),
                  sum(death_dt$DEATH_CAUSE == "BACKGROUND" & !is.na(death_dt$DEATH_DAY) &
                      death_dt$DEATH_DAY <= KN564_CONSTANTS$ADMIN_CENSOR_DAY, na.rm = TRUE)))

  death_dt
}

#' Simulate death for a single patient
#' @return list with death_day, cause, subsequent_therapy
simulate_patient_death <- function(has_recurrence, recurrence_day, recurrence_type,
                                    arm, age, ecog_bl, pr_params, bg_params) {

  death_day_post_rec <- Inf
  death_day_background <- Inf
  subsequent_therapy <- NA_character_
  is_pembro <- (arm == "PEMBROLIZUMAB")

  # ─── Background Mortality (all patients) ─────────────────────────────────
  # Exponential hazard model for non-cancer death
  annual_rate <- bg_params$annual_rate_base +
    bg_params$beta_age_per_decade * (age - 60) / 10 +
    bg_params$beta_ecog1 * ecog_bl
  annual_rate <- max(annual_rate, 0.001)

  # Convert to daily rate and draw exponential
  daily_rate <- -log(1 - annual_rate) / 365
  u_bg <- runif(1)
  death_day_background <- -log(u_bg) / daily_rate

  # ─── Post-Recurrence Survival ────────────────────────────────────────────
  if (has_recurrence && !is.na(recurrence_day)) {
    # Assign subsequent therapy
    p_subsequent <- pr_params$subsequent_therapy_prob
    if (runif(1) < p_subsequent) {
      # Patients previously on pembro less likely to receive IO rechallenge
      p_io <- ifelse(is_pembro, 0.50, 0.80)
      subsequent_therapy <- ifelse(runif(1) < p_io, "IO_BASED", "TKI_BASED")
    } else {
      subsequent_therapy <- "BSC"  # Best supportive care
    }

    # Weibull AFT for post-recurrence survival
    log_scale <- log(pr_params$weibull_scale_base)

    # Distant recurrence is worse
    if (!is.na(recurrence_type) && recurrence_type == "DISTANT") {
      log_scale <- log_scale - pr_params$beta_distant
    }

    # Prior pembro exposure may improve post-recurrence outcomes
    if (is_pembro) {
      log_scale <- log_scale - pr_params$beta_prior_pembro  # beta is negative, so subtracting negative = increase
    }

    # Later recurrence associated with better prognosis
    time_to_rec_years <- recurrence_day / 365
    log_scale <- log_scale - pr_params$beta_time_to_recurrence_per_year * time_to_rec_years

    # Subsequent IO therapy benefit
    if (!is.na(subsequent_therapy) && subsequent_therapy == "IO_BASED") {
      log_scale <- log_scale + 0.20  # Modest benefit
    }

    shape <- pr_params$weibull_shape
    scale <- exp(log_scale)

    u_pr <- runif(1)
    post_rec_time <- weibull_quantile(u_pr, shape, scale)
    death_day_post_rec <- recurrence_day + post_rec_time
  }

  # ─── Determine Actual Death Day ──────────────────────────────────────────
  actual_death_day <- min(death_day_post_rec, death_day_background)

  if (actual_death_day > 10 * 365) {
    # Effectively no death observed (very long survival)
    return(list(death_day = NA_real_, cause = NA_character_,
                subsequent_therapy = subsequent_therapy))
  }

  cause <- ifelse(death_day_post_rec <= death_day_background,
                  "POST_RECURRENCE", "BACKGROUND")

  list(
    death_day = actual_death_day,
    cause = cause,
    subsequent_therapy = subsequent_therapy
  )
}
