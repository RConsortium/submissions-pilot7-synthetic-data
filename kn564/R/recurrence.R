# recurrence.R — Weibull AFT recurrence model + imaging detection
# KEYNOTE-564 IPD Causal-DAG Simulator

source("R/dag_state.R")

#' Simulate recurrence for all patients
#' @param bl data.table, baseline characteristics
#' @param ex_long data.table, exposure records (to determine treatment duration)
#' @param params list, simulation parameters
#' @return data.table with recurrence information per patient
simulate_recurrence <- function(bl, ex_long, params = load_params()) {

  n <- nrow(bl)
  rec_params <- params$recurrence
  img_params <- params$imaging

  # Pre-compute treatment duration per patient
  treat_duration <- compute_treatment_duration(ex_long)
  bl_merged <- merge(bl, treat_duration, by = "SUBJID", all.x = TRUE)
  bl_merged[is.na(LAST_DOSE_DAY), LAST_DOSE_DAY := 0L]

  # Draw latent recurrence times
  recurrence_dt <- bl_merged[, {
    lat_rec <- draw_latent_recurrence(
      risk_category = RISK_CATEGORY,
      pdl1_cps = PDL1_CPS,
      sarcomatoid = SARCOMATOID,
      age = AGE,
      ecog_bl = ECOG_BL,
      f_recurrence = F_RECURRENCE,
      arm = ARM,
      last_dose_day = LAST_DOSE_DAY,
      rec_params = rec_params
    )
    list(
      LATENT_RECURRENCE_DAY = lat_rec$latent_day,
      RECURRENCE_TYPE = lat_rec$recurrence_type
    )
  }, by = SUBJID]

  # Map latent recurrence to observed (imaging detection)
  imaging_days <- IMAGING_SCHEDULE
  recurrence_dt[, OBSERVED_RECURRENCE_DAY := sapply(LATENT_RECURRENCE_DAY, function(d) {
    if (is.na(d) || d > KN564_CONSTANTS$ADMIN_CENSOR_DAY) return(NA_real_)
    # Apply detection sensitivity
    obs_day <- next_imaging_day(d, imaging_days)
    if (is.na(obs_day)) return(NA_real_)
    # Small probability of missed detection at first scan
    if (runif(1) > img_params$detection_sensitivity) {
      # Detected at next scan instead
      obs_day2 <- next_imaging_day(obs_day + 1, imaging_days)
      if (!is.na(obs_day2)) obs_day <- obs_day2
    }
    obs_day
  })]

  # Censor recurrences beyond admin censor
  recurrence_dt[OBSERVED_RECURRENCE_DAY > KN564_CONSTANTS$ADMIN_CENSOR_DAY,
                `:=`(OBSERVED_RECURRENCE_DAY = NA_real_, RECURRENCE_TYPE = NA_character_)]

  message(sprintf("[recurrence] Recurrence events: %d (of %d patients)",
                  sum(!is.na(recurrence_dt$OBSERVED_RECURRENCE_DAY)), n))

  recurrence_dt
}

#' Draw latent recurrence time for a single patient
#' @return list with latent_day and recurrence_type
draw_latent_recurrence <- function(risk_category, pdl1_cps, sarcomatoid,
                                    age, ecog_bl, f_recurrence, arm,
                                    last_dose_day, rec_params) {

  # Base scale by risk category
  base_scale <- switch(risk_category,
    "M0_INT_HIGH" = rec_params$weibull_scale_M0_int_high,
    "M0_HIGH"     = rec_params$weibull_scale_M0_high,
    "M1_NED"      = rec_params$weibull_scale_M1_NED
  )

  # Log-linear predictor for AFT scale
  log_scale <- log(base_scale) +
    rec_params$beta_pdl1_pos * as.numeric(pdl1_cps == ">=1") +
    rec_params$beta_sarcomatoid * sarcomatoid +
    rec_params$beta_age_per_decade * (age - 60) / 10 +
    rec_params$beta_ecog1 * ecog_bl +
    rec_params$beta_frailty * f_recurrence

  # Treatment effect (pembro arm only)
  if (arm == "PEMBROLIZUMAB") {
    # During treatment: full effect
    # After treatment: waning effect
    # We model this as a time-averaged shift to the AFT scale
    treatment_days <- min(last_dose_day, KN564_CONSTANTS$TREATMENT_DAYS)
    waning_halflife <- rec_params$waning_halflife_days

    # Effective treatment benefit = weighted average of on-treatment and post-treatment
    # Approximate by applying blended effect to scale
    on_tx_effect <- rec_params$treatment_effect_on_treatment
    post_tx_effect <- rec_params$treatment_effect_post_treatment

    # Weight by treatment duration relative to total observation
    tx_weight <- treatment_days / KN564_CONSTANTS$ADMIN_CENSOR_DAY
    post_weight <- 1 - tx_weight

    blended_effect <- -(tx_weight * abs(on_tx_effect) + post_weight * abs(post_tx_effect))
    log_scale <- log_scale - blended_effect  # Negative effect = longer time = less scale reduction
  }

  shape <- rec_params$weibull_shape
  scale <- exp(log_scale)

  # Draw from Weibull

  u <- runif(1)
  latent_day <- weibull_quantile(u, shape, scale)

  # Determine recurrence type (local vs distant)
  recurrence_type <- NA_character_
  if (latent_day <= KN564_CONSTANTS$ADMIN_CENSOR_DAY) {
    p_distant <- switch(risk_category,
      "M1_NED"      = 0.60,
      "M0_HIGH"     = 0.45,
      "M0_INT_HIGH" = 0.35
    )
    # Earlier recurrence more likely distant
    if (latent_day < 365) p_distant <- p_distant + 0.10
    recurrence_type <- ifelse(runif(1) < p_distant, "DISTANT", "LOCAL")
  }

  list(latent_day = latent_day, recurrence_type = recurrence_type)
}

#' Compute treatment duration for each patient from exposure records
#' @param ex_long data.table with SUBJID, VISIT_DAY, DOSE_STATUS
#' @return data.table with SUBJID, LAST_DOSE_DAY, TOTAL_DOSES
compute_treatment_duration <- function(ex_long) {
  ex_long[DOSE_STATUS == "GIVEN", .(
    LAST_DOSE_DAY = max(VISIT_DAY),
    TOTAL_DOSES = .N
  ), by = SUBJID]
}
