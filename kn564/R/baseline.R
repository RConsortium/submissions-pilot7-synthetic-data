# baseline.R — L0 generation + stratified randomization
# KEYNOTE-564 IPD Causal-DAG Simulator

source("R/dag_state.R")

#' Generate baseline patient characteristics
#' @param n integer, total number of patients
#' @param params list, simulation parameters
#' @param seed integer, random seed
#' @return data.table with one row per patient, all L0 variables
generate_baseline <- function(n = KN564_CONSTANTS$N_TOTAL,
                              params = load_params(),
                              seed = NULL) {

  if (!is.null(seed)) set.seed(seed)


  # ─── Demographics ──────────────────────────────────────────────────────────

  # Region
  region <- sample(KN564_CONSTANTS$REGIONS,
                   size = n, replace = TRUE,
                   prob = c(0.30, 0.70))

  # Age: Normal(60, 10), truncated [24, 84]
  age <- numeric(n)
  for (i in seq_len(n)) {
    repeat {
      a <- rnorm(1, mean = 60, sd = 10)
      if (a >= 24 && a <= 84) { age[i] <- round(a, 1); break }
    }
  }

  # Sex
  sex <- ifelse(runif(n) < 0.71, "M", "F")

  # Race (conditional on region)
  race <- character(n)
  for (i in seq_len(n)) {
    if (region[i] == "US") {
      race[i] <- sample(c("WHITE", "BLACK", "ASIAN", "OTHER"),
                        size = 1, prob = c(0.75, 0.12, 0.05, 0.08))
    } else {
      race[i] <- sample(c("WHITE", "ASIAN", "BLACK", "OTHER"),
                        size = 1, prob = c(0.50, 0.35, 0.02, 0.13))
    }
  }

  # ─── Disease Characteristics ───────────────────────────────────────────────

  # Risk category
  risk_category <- sample(KN564_CONSTANTS$RISK_CATEGORIES,
                          size = n, replace = TRUE,
                          prob = c(0.86, 0.08, 0.06))

  # Sarcomatoid features (enriched in higher risk)
  sarc_prob <- ifelse(risk_category == "M0_HIGH", 0.13,
               ifelse(risk_category == "M1_NED", 0.20, 0.10))
  sarcomatoid <- as.integer(runif(n) < sarc_prob)

  # PD-L1 CPS (sarcomatoid shifts toward positive)
  pdl1_cps <- character(n)
  for (i in seq_len(n)) {
    p_neg <- 0.24
    p_pos <- 0.75
    p_miss <- 0.01
    if (sarcomatoid[i] == 1L) {
      # Shift 10% from <1 to >=1
      p_neg <- p_neg - 0.10
      p_pos <- p_pos + 0.10
    }
    pdl1_cps[i] <- sample(c("<1", ">=1", "MISSING"),
                          size = 1, prob = c(p_neg, p_pos, p_miss))
  }

  # ECOG (slight age dependence); intercept calibrated so mean ~ 0.15
  ecog_prob <- expit(-1.73 + 0.01 * (age - 60))
  ecog_bl <- as.integer(runif(n) < ecog_prob)

  # ─── Latent Frailties ──────────────────────────────────────────────────────

  f_thyroid    <- rnorm(n, 0, 1)
  f_skin       <- rnorm(n, 0, 1)
  f_GI         <- rnorm(n, 0, 1)
  f_systemic   <- rnorm(n, 0, 1)
  f_recurrence <- rnorm(n, 0, 1)
  f_dropout    <- rnorm(n, 0, 1)

  # ─── Assemble Baseline Table ───────────────────────────────────────────────

  bl <- data.table(
    SUBJID         = sprintf("KN564-%04d", seq_len(n)),
    AGE            = age,
    SEX            = sex,
    RACE           = race,
    REGION         = region,
    RISK_CATEGORY  = risk_category,
    SARCOMATOID    = sarcomatoid,
    PDL1_CPS       = pdl1_cps,
    ECOG_BL        = ecog_bl,
    F_THYROID      = f_thyroid,
    F_SKIN         = f_skin,
    F_GI           = f_GI,
    F_SYSTEMIC     = f_systemic,
    F_RECURRENCE   = f_recurrence,
    F_DROPOUT      = f_dropout
  )

  # ─── Stratified Randomization ──────────────────────────────────────────────

  bl <- stratified_randomize(bl)

  message(sprintf("[baseline] Generated %d patients: %d pembro, %d placebo",
                  nrow(bl), sum(bl$ARM == "PEMBROLIZUMAB"), sum(bl$ARM == "PLACEBO")))

  bl
}

#' Perform stratified block randomization
#' @param bl data.table with RISK_CATEGORY, ECOG_BL, REGION columns
#' @return data.table with ARM column added
stratified_randomize <- function(bl) {

  # Define strata: M-status x ECOG x Region(within M0)
  bl[, STRATUM := fcase(
    RISK_CATEGORY == "M1_NED" & ECOG_BL == 0L, "M1_ECOG0",
    RISK_CATEGORY == "M1_NED" & ECOG_BL == 1L, "M1_ECOG1",
    RISK_CATEGORY != "M1_NED" & ECOG_BL == 0L & REGION == "US", "M0_ECOG0_US",
    RISK_CATEGORY != "M1_NED" & ECOG_BL == 0L & REGION == "OTHER", "M0_ECOG0_OTHER",
    RISK_CATEGORY != "M1_NED" & ECOG_BL == 1L & REGION == "US", "M0_ECOG1_US",
    RISK_CATEGORY != "M1_NED" & ECOG_BL == 1L & REGION == "OTHER", "M0_ECOG1_OTHER"
  )]

  # Block randomize within each stratum (block size 4)
  bl[, ARM := {
    n_stratum <- .N
    # Create permuted blocks of size 4 (2 pembro, 2 placebo each)
    n_blocks <- ceiling(n_stratum / 4)
    assignments <- character(0)
    for (b in seq_len(n_blocks)) {
      block <- sample(rep(c("PEMBROLIZUMAB", "PLACEBO"), 2))
      assignments <- c(assignments, block)
    }
    assignments[seq_len(n_stratum)]
  }, by = STRATUM]

  bl
}
