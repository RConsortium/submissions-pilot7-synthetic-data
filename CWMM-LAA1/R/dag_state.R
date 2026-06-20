# dag_state.R — Visit grid, constants, helpers for CWMM-LAA1 simulator
# =========================================================================

library(jsonlite)

# --- Load parameters ---
load_params <- function(param_file = "params/initial_params.json") {
  fromJSON(param_file, simplifyVector = TRUE, simplifyDataFrame = FALSE)
}

# --- Constants ---
VISIT_WEEKS <- c(0, 1, 2, 4, 8, 12, 16, 20, 24, 28, 32, 36, 40, 44, 48, 58)
N_VISITS <- length(VISIT_WEEKS)

ARM_LABELS <- c("Placebo", "1mg", "3mg", "6mg", "9mg", "6to9mg", "3to9mg")
ARM_RATIOS <- c(2, 1, 1, 1, 2, 1, 2)
ARM_N <- c(Placebo = 53, `1mg` = 28, `3mg` = 24, `6mg` = 28,
           `9mg` = 54, `6to9mg` = 24, `3to9mg` = 52)

# --- Helpers ---

#' Truncated normal draw
rtruncnorm <- function(n, mean, sd, lower = -Inf, upper = Inf) {
  out <- numeric(n)
  for (i in seq_len(n)) {
    repeat {
      x <- rnorm(1, mean, sd)
      if (x >= lower && x <= upper) { out[i] <- x; break }
    }
  }
  out
}

#' Inverse logit
inv_logit <- function(x) 1 / (1 + exp(-x))

#' Get effective dose at a given week for an arm
get_effective_dose <- function(arm, week, params) {
  sched <- params$dose_schedule[[arm]]
  if (is.null(sched$escalation_week) || is.na(sched$escalation_week)) {
    return(sched$phase1)
  }
  if (week < sched$escalation_week) sched$phase1 else sched$phase2
}

#' Compute visit intervals (in weeks) for hazard calculations
visit_intervals <- function() {
  diff(VISIT_WEEKS)
}

#' Initialize empty patient state
init_patient_state <- function(id, arm) {
  list(
    id = id,
    arm = arm,
    alive = TRUE,
    on_treatment = TRUE,
    tx_disc_week = NA_real_,
    study_disc_week = NA_real_,
    weight = numeric(N_VISITS),
    wt_pct_change = numeric(N_VISITS),
    aes = list(),
    cum_ae_count = 0

  )
}

#' Create a date sequence for visits given a reference start date
visit_dates <- function(start_date = as.Date("2024-03-01")) {
  start_date + VISIT_WEEKS * 7
}
