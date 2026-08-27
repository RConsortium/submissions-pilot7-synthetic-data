# dag_state.R — Constants, visit grid, imaging schedule, helpers
# KEYNOTE-564 IPD Causal-DAG Simulator

library(data.table)
library(jsonlite)

# ─── Constants ─────────────────────────────────────────────────────────────────

KN564_CONSTANTS <- list(

  TRIAL_NAME       = "KEYNOTE-564",
  NCT_ID           = "NCT03142334",
  N_TOTAL          = 994L,
  N_PEMBRO         = 496L,

  N_PLACEBO        = 498L,
  CYCLE_LENGTH     = 21L,        # days per cycle

  MAX_CYCLES       = 17L,        # ~1 year of treatment
  TREATMENT_DAYS   = 17L * 21L,  # 357 days
  ADMIN_CENSOR_DAY = 1740L,      # ~57.2 months from randomization
  DOSE_MG          = 200L,
  ARMS             = c("PEMBROLIZUMAB", "PLACEBO"),


  # Stratification factor levels
  RISK_CATEGORIES  = c("M0_INT_HIGH", "M0_HIGH", "M1_NED"),
  ECOG_LEVELS      = c(0L, 1L),
  REGIONS          = c("US", "OTHER"),

  # Lab reference ranges
  TSH_NORMAL_LOW   = 0.4,
  TSH_NORMAL_HIGH  = 4.0,
  FT4_NORMAL_LOW   = 0.8,

  FT4_NORMAL_HIGH  = 1.8,

  # Thyroid states
  THYROID_STATES   = c("EUTHYROID", "HYPERTHYROID", "HYPOTHYROID")
)

# ─── Visit Grid ────────────────────────────────────────────────────────────────

#' Generate the treatment visit schedule (dosing visits)
#' @param max_cycles integer, maximum number of cycles (default 17)
#' @return data.table with columns: cycle, visit_day, visit_type
generate_dosing_visits <- function(max_cycles = KN564_CONSTANTS$MAX_CYCLES) {
  data.table(
    cycle     = seq_len(max_cycles),
    visit_day = (seq_len(max_cycles) - 1L) * KN564_CONSTANTS$CYCLE_LENGTH + 1L,
    visit_type = "DOSING"
  )
}

#' Generate the imaging/surveillance schedule
#' @param max_day integer, maximum study day to schedule through
#' @return numeric vector of imaging visit days
generate_imaging_schedule <- function(max_day = KN564_CONSTANTS$ADMIN_CENSOR_DAY) {
  imaging_days <- integer(0)
  current_day <- 1L


  # Year 1: every 12 weeks (84 days)
  year1_end <- 365L
  while (current_day <= min(year1_end, max_day)) {
    current_day <- current_day + 84L
    if (current_day <= max_day) {
      imaging_days <- c(imaging_days, current_day)
    }
  }

  # Years 2-4: every 16 weeks (112 days)
  year4_end <- 4L * 365L
  while (current_day <= min(year4_end, max_day)) {
    current_day <- current_day + 112L
    if (current_day <= max_day) {
      imaging_days <- c(imaging_days, current_day)
    }
  }

  # Year 5+: every 24 weeks (168 days)
  while (current_day <= max_day) {
    current_day <- current_day + 168L
    if (current_day <= max_day) {
      imaging_days <- c(imaging_days, current_day)
    }
  }

  sort(unique(imaging_days))
}

# ─── Helper Functions ──────────────────────────────────────────────────────────

#' Load parameters from JSON file
#' @param path character, path to params JSON
#' @return list of parameters
load_params <- function(path = "params/initial_params.json") {
  fromJSON(path, simplifyVector = TRUE, simplifyDataFrame = FALSE)
}

#' Load calibration targets
#' @param path character, path to targets JSON
#' @return list of targets
load_targets <- function(path = "data-raw/targets.json") {

  fromJSON(path, simplifyVector = TRUE, simplifyDataFrame = FALSE)
}

#' Expit (inverse logit) function
#' @param x numeric
#' @return numeric in (0,1)
expit <- function(x) {
  1 / (1 + exp(-x))
}

#' Logit function
#' @param p numeric in (0,1)
#' @return numeric
logit <- function(p) {
  log(p / (1 - p))
}

#' Weibull quantile function (parameterized as shape/scale)
#' @param u numeric in (0,1), uniform draw
#' @param shape numeric > 0
#' @param scale numeric > 0
#' @return numeric, time from Weibull distribution
weibull_quantile <- function(u, shape, scale) {
  scale * (-log(1 - u))^(1 / shape)
}

#' Weibull survival function
#' @param t numeric >= 0
#' @param shape numeric > 0
#' @param scale numeric > 0
#' @return numeric in (0,1)
weibull_surv <- function(t, shape, scale) {
  exp(-(t / scale)^shape)
}

#' Apply frailty to per-cycle probability
#' @param base_prob numeric, baseline per-cycle probability
#' @param frailty numeric, individual frailty (Normal(0,1))
#' @param beta_frailty numeric, frailty coefficient
#' @return numeric, adjusted probability
apply_frailty <- function(base_prob, frailty, beta_frailty) {
  log_odds <- logit(pmin(pmax(base_prob, 1e-6), 1 - 1e-6))
  expit(log_odds + beta_frailty * frailty)
}

#' Find the next imaging day after a given event day
#' @param event_day numeric, the day the latent event occurs
#' @param imaging_days numeric vector, scheduled imaging days
#' @return numeric, the imaging day when event is detected (or NA if beyond schedule)
next_imaging_day <- function(event_day, imaging_days) {
  candidates <- imaging_days[imaging_days >= event_day]
  if (length(candidates) == 0) return(NA_real_)
  min(candidates)
}

#' Map study day to cycle number
#' @param day integer, study day
#' @return integer, cycle number (1-indexed)
day_to_cycle <- function(day) {
  pmax(1L, ceiling(day / KN564_CONSTANTS$CYCLE_LENGTH))
}

#' Map cycle number to study day (start of cycle)
#' @param cycle integer, cycle number
#' @return integer, first day of that cycle
cycle_to_day <- function(cycle) {
  (cycle - 1L) * KN564_CONSTANTS$CYCLE_LENGTH + 1L
}

#' Set seed reproducibly for a patient
#' @param base_seed integer, master seed
#' @param patient_id integer, patient identifier
#' @return invisible NULL (sets .Random.seed as side effect)
set_patient_seed <- function(base_seed, patient_id) {
  set.seed(base_seed + patient_id)
  invisible(NULL)
}

# ─── Imaging Schedule (pre-computed for efficiency) ────────────────────────────

IMAGING_SCHEDULE <- generate_imaging_schedule()
DOSING_VISITS    <- generate_dosing_visits()

message("[dag_state] KEYNOTE-564 simulator constants and helpers loaded.")
