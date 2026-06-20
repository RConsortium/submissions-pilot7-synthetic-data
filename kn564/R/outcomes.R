# outcomes.R — Deterministic DFS/OS derivation from trajectories
# KEYNOTE-564 IPD Causal-DAG Simulator

source("R/dag_state.R")

#' Derive DFS and OS endpoints from recurrence and death data
#' @param bl data.table, baseline characteristics
#' @param recurrence_dt data.table, recurrence outcomes
#' @param death_dt data.table, death outcomes
#' @return data.table with endpoint variables per patient
derive_endpoints <- function(bl, recurrence_dt, death_dt) {

  # Merge all components
  endpoints <- merge(
    bl[, .(SUBJID, ARM, RISK_CATEGORY)],
    recurrence_dt[, .(SUBJID, LATENT_RECURRENCE_DAY, OBSERVED_RECURRENCE_DAY, RECURRENCE_TYPE)],
    by = "SUBJID", all.x = TRUE
  )
  endpoints <- merge(
    endpoints,
    death_dt[, .(SUBJID, DEATH_DAY, DEATH_CAUSE, SUBSEQUENT_THERAPY)],
    by = "SUBJID", all.x = TRUE
  )

  # Staggered enrollment: patients enrolled over ~900 days (Jun 2017 - Dec 2019)
  # Data cutoff is fixed → variable follow-up per patient
  # Enrollment day drawn from Uniform(0, 900) relative to first patient
  set.seed(564099)  # Deterministic enrollment pattern
  n_pts <- nrow(endpoints)
  enrollment_day <- sort(round(runif(n_pts, 0, 900)))  # Sorted by enrollment
  # Randomize assignment of enrollment days to patients
  enrollment_day <- sample(enrollment_day)
  # Max follow-up = admin_censor_day (from first patient enrolled)
  # Each patient's actual censor = max_study_duration - enrollment_offset
  max_study_day <- KN564_CONSTANTS$ADMIN_CENSOR_DAY + 450  # ~72 months from first patient
  endpoints[, ENROLLMENT_DAY := enrollment_day]
  endpoints[, ADMIN_CENSOR := pmax(max_study_day - ENROLLMENT_DAY, 365L)]

  # ─── DFS Derivation ─────────────────────────────────────────────────────
  # DFS event = first of: recurrence (observed), death, or patient-specific admin censor
  endpoints[, `:=`(
    DFS_DAY = pmin(
      fifelse(is.na(OBSERVED_RECURRENCE_DAY), Inf, OBSERVED_RECURRENCE_DAY),
      fifelse(is.na(DEATH_DAY), Inf, DEATH_DAY),
      ADMIN_CENSOR,
      na.rm = TRUE
    ),
    DFS_EVENT = as.integer(
      (!is.na(OBSERVED_RECURRENCE_DAY) & OBSERVED_RECURRENCE_DAY <= ADMIN_CENSOR) |
      (!is.na(DEATH_DAY) & DEATH_DAY <= ADMIN_CENSOR &
       (is.na(OBSERVED_RECURRENCE_DAY) | DEATH_DAY <= OBSERVED_RECURRENCE_DAY))
    )
  )]

  # DFS event type
  endpoints[, DFS_EVENT_TYPE := fcase(
    DFS_EVENT == 0L, "CENSORED",
    !is.na(OBSERVED_RECURRENCE_DAY) & OBSERVED_RECURRENCE_DAY <= ADMIN_CENSOR &
      (is.na(DEATH_DAY) | OBSERVED_RECURRENCE_DAY <= DEATH_DAY), "RECURRENCE",
    !is.na(DEATH_DAY) & DEATH_DAY <= ADMIN_CENSOR, "DEATH",
    default = "CENSORED"
  )]

  # ─── OS Derivation ──────────────────────────────────────────────────────
  endpoints[, `:=`(
    OS_DAY = pmin(
      fifelse(is.na(DEATH_DAY), Inf, DEATH_DAY),
      ADMIN_CENSOR
    ),
    OS_EVENT = as.integer(!is.na(DEATH_DAY) & DEATH_DAY <= ADMIN_CENSOR)
  )]

  # Ensure no infinite values remain
  endpoints[is.infinite(DFS_DAY), DFS_DAY := ADMIN_CENSOR]
  endpoints[is.infinite(OS_DAY), OS_DAY := ADMIN_CENSOR]

  # ─── Landmark KM Probabilities ──────────────────────────────────────────
  # (computed externally in calibrate.R, but provide convenience function)

  message(sprintf("[outcomes] DFS events: pembro=%d, placebo=%d | OS events: pembro=%d, placebo=%d",
                  sum(endpoints[ARM == "PEMBROLIZUMAB"]$DFS_EVENT),
                  sum(endpoints[ARM == "PLACEBO"]$DFS_EVENT),
                  sum(endpoints[ARM == "PEMBROLIZUMAB"]$OS_EVENT),
                  sum(endpoints[ARM == "PLACEBO"]$OS_EVENT)))

  endpoints
}

#' Compute Kaplan-Meier survival probability at a landmark time
#' @param time numeric vector, event/censor times
#' @param event integer vector, event indicators (1=event, 0=censor)
#' @param landmark numeric, time point for KM estimate
#' @return numeric, KM survival probability at landmark
km_at_landmark <- function(time, event, landmark) {
  if (length(time) == 0) return(NA_real_)

  # Simple KM computation without survival package dependency
  dt <- data.table(time = time, event = event)
  dt <- dt[order(time)]

  n_risk <- nrow(dt)
  surv_prob <- 1.0

  event_times <- dt[event == 1, unique(time)]
  event_times <- sort(event_times[event_times <= landmark])

  for (t in event_times) {
    # Number at risk just before time t
    n_risk <- sum(dt$time >= t)
    # Number of events at time t
    n_events <- sum(dt$time == t & dt$event == 1)
    # KM step
    surv_prob <- surv_prob * (1 - n_events / n_risk)
  }

  surv_prob
}

#' Compute Cox PH hazard ratio (simple two-arm comparison)
#' @param endpoints data.table with ARM, time_col, event_col
#' @param time_col character, name of time column
#' @param event_col character, name of event column
#' @return list with hr, hr_lower, hr_upper, p_value
compute_hr <- function(endpoints, time_col = "DFS_DAY", event_col = "DFS_EVENT") {

  # Requires survival package
  if (!requireNamespace("survival", quietly = TRUE)) {
    stop("Package 'survival' is required for HR computation")
  }

  form <- as.formula(paste0("survival::Surv(", time_col, ", ", event_col,
                            ") ~ ARM_NUM"))
  endpoints_copy <- copy(endpoints)
  endpoints_copy[, ARM_NUM := as.integer(ARM == "PEMBROLIZUMAB")]

  fit <- survival::coxph(form, data = endpoints_copy)
  s <- summary(fit)

  list(
    hr = exp(s$coefficients[1, "coef"]),
    hr_lower = s$conf.int[1, "lower .95"],
    hr_upper = s$conf.int[1, "upper .95"],
    p_value = s$coefficients[1, "Pr(>|z|)"]
  )
}

#' Summary statistics for endpoints
#' @param endpoints data.table from derive_endpoints
#' @return list with summary statistics
endpoint_summary <- function(endpoints) {

  dfs_pembro <- endpoints[ARM == "PEMBROLIZUMAB"]
  dfs_placebo <- endpoints[ARM == "PLACEBO"]

  list(
    dfs_events_pembro = sum(dfs_pembro$DFS_EVENT),
    dfs_events_placebo = sum(dfs_placebo$DFS_EVENT),
    os_events_pembro = sum(dfs_pembro$OS_EVENT),
    os_events_placebo = sum(dfs_placebo$OS_EVENT),
    dfs_km_48mo_pembro = km_at_landmark(dfs_pembro$DFS_DAY, dfs_pembro$DFS_EVENT, 48 * 30.44),
    dfs_km_48mo_placebo = km_at_landmark(dfs_placebo$DFS_DAY, dfs_placebo$DFS_EVENT, 48 * 30.44),
    os_km_48mo_pembro = km_at_landmark(dfs_pembro$OS_DAY, dfs_pembro$OS_EVENT, 48 * 30.44),
    os_km_48mo_placebo = km_at_landmark(dfs_placebo$OS_DAY, dfs_placebo$OS_EVENT, 48 * 30.44)
  )
}
