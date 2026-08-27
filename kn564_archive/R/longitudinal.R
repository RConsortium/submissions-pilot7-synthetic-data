# longitudinal.R — Per-cycle simulation: thyroid, AEs, dose status, ECOG
# KEYNOTE-564 IPD Causal-DAG Simulator

source("R/dag_state.R")

#' Simulate longitudinal trajectories for all patients
#' @param bl data.table, baseline characteristics (from generate_baseline)
#' @param params list, simulation parameters
#' @return list with components: ae_long (AE events), lb_long (labs), ex_long (exposure)
simulate_longitudinal <- function(bl, params = load_params()) {

  n <- nrow(bl)
  max_cycles <- KN564_CONSTANTS$MAX_CYCLES

  # Pre-allocate result lists
  ae_records <- vector("list", n)
  lb_records <- vector("list", n)
  ex_records <- vector("list", n)

  for (i in seq_len(n)) {
    pat <- bl[i]
    result <- simulate_patient_longitudinal(pat, params, max_cycles)
    ae_records[[i]] <- result$ae
    lb_records[[i]] <- result$lb
    ex_records[[i]] <- result$ex
  }

  ae_long <- rbindlist(ae_records, fill = TRUE)
  lb_long <- rbindlist(lb_records, fill = TRUE)
  ex_long <- rbindlist(ex_records, fill = TRUE)

  message(sprintf("[longitudinal] Simulated %d patients: %d AE events, %d lab records, %d doses",
                  n, nrow(ae_long), nrow(lb_long), nrow(ex_long)))

  list(ae_long = ae_long, lb_long = lb_long, ex_long = ex_long)
}

#' Simulate longitudinal trajectory for a single patient
#' @param pat single-row data.table with baseline characteristics
#' @param params list, simulation parameters
#' @param max_cycles integer
#' @return list with ae, lb, ex data.tables
simulate_patient_longitudinal <- function(pat, params, max_cycles) {

  subjid <- pat$SUBJID
  arm <- pat$ARM
  is_pembro <- (arm == "PEMBROLIZUMAB")

  # Initialize state
  thyroid_state <- "EUTHYROID"
  dose_status <- "GIVEN"  # GIVEN, HELD, DISCONTINUED
  cumulative_doses <- 0L
  cumulative_holds <- 0L
  cumulative_ae_count <- 0L
  on_treatment <- TRUE

  # Collect records
  ae_list <- list()
  lb_list <- list()
  ex_list <- list()

  for (cycle in seq_len(max_cycles)) {
    visit_day <- cycle_to_day(cycle)

    # ─── Thyroid State Machine ─────────────────────────────────────────────
    thyroid_result <- update_thyroid_state(
      thyroid_state, is_pembro, on_treatment,
      pat$F_THYROID, params$thyroid, cycle
    )
    thyroid_state <- thyroid_result$new_state
    thyroid_ae <- thyroid_result$ae_event  # "HYPERTHYROIDISM", "HYPOTHYROIDISM", or NULL

    # ─── Labs (TSH, FT4) ──────────────────────────────────────────────────
    labs <- generate_thyroid_labs(thyroid_state, visit_day, subjid)
    lb_list[[length(lb_list) + 1]] <- labs

    # ─── Immune-Mediated AEs ──────────────────────────────────────────────
    immune_aes <- generate_immune_aes(
      is_pembro, on_treatment, pat, params$ae_per_cycle, visit_day, subjid
    )

    # ─── General AEs ──────────────────────────────────────────────────────
    general_aes <- generate_general_aes(
      is_pembro, on_treatment, pat, params$ae_per_cycle, visit_day, subjid
    )

    # Add SUBJID and AESTDT to thyroid AE if present
    if (!is.null(thyroid_ae)) {
      thyroid_ae[, `:=`(SUBJID = subjid, AESTDT = visit_day + sample(0:7, 1))]
    }

    # Combine all AEs this cycle (including thyroid)
    cycle_aes <- rbindlist(c(
      if (!is.null(thyroid_ae)) list(thyroid_ae),
      if (nrow(immune_aes) > 0) list(immune_aes),
      if (nrow(general_aes) > 0) list(general_aes)
    ), fill = TRUE)

    if (nrow(cycle_aes) > 0) {
      ae_list[[length(ae_list) + 1]] <- cycle_aes
    }

    # Track cumulative AE burden
    cumulative_ae_count <- cumulative_ae_count + nrow(cycle_aes)

    # ─── Dose Modification Logic ──────────────────────────────────────────
    # Cycle 1: always give first dose (patients receive at least one dose)
    if (cycle == 1L) {
      dose_status <- "GIVEN"
    } else {
      dose_result <- apply_dose_modification(
        dose_status, cycle_aes, params$dose_modification,
        cumulative_holds, pat$F_DROPOUT, on_treatment,
        cumulative_ae_count = cumulative_ae_count,
        is_pembro = is_pembro
      )
      dose_status <- dose_result$dose_status
    }
    on_treatment <- (dose_status != "DISCONTINUED")

    # ─── Exposure Record ──────────────────────────────────────────────────
    dose_given <- (dose_status == "GIVEN" && on_treatment)
    if (dose_given) cumulative_doses <- cumulative_doses + 1L
    if (dose_status == "HELD") cumulative_holds <- cumulative_holds + 1L

    ex_list[[length(ex_list) + 1]] <- data.table(
      SUBJID = subjid,
      CYCLE = cycle,
      VISIT_DAY = visit_day,
      EXDOSE = ifelse(dose_given, KN564_CONSTANTS$DOSE_MG, 0),
      DOSE_STATUS = dose_status,
      CUMULATIVE_DOSES = cumulative_doses,
      ON_TREATMENT = on_treatment
    )

    # If discontinued, no more cycles
    if (!on_treatment) break
  }

  list(
    ae = rbindlist(ae_list, fill = TRUE),
    lb = rbindlist(lb_list, fill = TRUE),
    ex = rbindlist(ex_list, fill = TRUE)
  )
}

# ─── Thyroid State Machine ───────────────────────────────────────────────────

#' Update thyroid state for one cycle
#' @return list with new_state and ae_event (data.table or NULL)
update_thyroid_state <- function(current_state, is_pembro, on_treatment,
                                 f_thyroid, thyroid_params, cycle) {

  ae_event <- NULL
  new_state <- current_state

  if (current_state == "EUTHYROID") {
    # Transition to hyperthyroid
    base_prob <- if (is_pembro && on_treatment) {
      thyroid_params$prob_hyperthyroid_per_cycle_pembro
    } else {
      thyroid_params$prob_hyperthyroid_per_cycle_placebo
    }
    adj_prob <- apply_frailty(base_prob, f_thyroid, thyroid_params$beta_frailty_thyroid)

    if (runif(1) < adj_prob) {
      new_state <- "HYPERTHYROID"
      # In blinded trial, thyroid events attributed as related regardless of arm
      ae_event <- data.table(
        AETERM = "HYPERTHYROIDISM",
        AEGR = sample(1:2, 1, prob = c(0.7, 0.3)),
        AECAT = "THYROID",
        AEREL = if (is_pembro) "RELATED" else "POSSIBLY RELATED"
      )
    } else {
      # Direct to hypothyroid (spontaneous)
      spont_prob <- if (is_pembro && on_treatment) {
        thyroid_params$prob_spontaneous_hypo_per_cycle_pembro
      } else {
        thyroid_params$prob_spontaneous_hypo_per_cycle_placebo
      }
      adj_spont <- apply_frailty(spont_prob, f_thyroid, thyroid_params$beta_frailty_thyroid)
      if (runif(1) < adj_spont) {
        new_state <- "HYPOTHYROID"
        ae_event <- data.table(
          AETERM = "HYPOTHYROIDISM",
          AEGR = sample(1:2, 1, prob = c(0.8, 0.2)),
          AECAT = "THYROID",
          AEREL = if (is_pembro) "RELATED" else "POSSIBLY RELATED"
        )
      }
    }

  } else if (current_state == "HYPERTHYROID") {
    # Transition to hypothyroid
    if (runif(1) < thyroid_params$prob_hypo_transition_per_cycle) {
      new_state <- "HYPOTHYROID"
      ae_event <- data.table(
        AETERM = "HYPOTHYROIDISM",
        AEGR = sample(1:2, 1, prob = c(0.8, 0.2)),
        AECAT = "THYROID",
        AEREL = if (is_pembro) "RELATED" else "POSSIBLY RELATED"
      )
    }
  }
  # HYPOTHYROID is absorbing — no transition

  list(new_state = new_state, ae_event = ae_event)
}

# ─── Lab Generation ──────────────────────────────────────────────────────────

#' Generate thyroid lab values based on current state
generate_thyroid_labs <- function(thyroid_state, visit_day, subjid) {

  tsh <- switch(thyroid_state,
    "EUTHYROID"    = exp(rnorm(1, log(2.0), 0.3)),
    "HYPERTHYROID" = exp(rnorm(1, log(0.1), 0.5)),
    "HYPOTHYROID"  = exp(rnorm(1, log(15.0), 0.4))
  )

  ft4 <- switch(thyroid_state,
    "EUTHYROID"    = rnorm(1, 1.2, 0.2),
    "HYPERTHYROID" = rnorm(1, 2.5, 0.5),
    "HYPOTHYROID"  = rnorm(1, 0.5, 0.15)
  )
  ft4 <- max(ft4, 0.1)

  tsh_ind <- ifelse(tsh < KN564_CONSTANTS$TSH_NORMAL_LOW, "LOW",
             ifelse(tsh > KN564_CONSTANTS$TSH_NORMAL_HIGH, "HIGH", "NORMAL"))
  ft4_ind <- ifelse(ft4 < KN564_CONSTANTS$FT4_NORMAL_LOW, "LOW",
             ifelse(ft4 > KN564_CONSTANTS$FT4_NORMAL_HIGH, "HIGH", "NORMAL"))

  data.table(
    SUBJID = rep(subjid, 2),
    VISIT_DAY = rep(visit_day, 2),
    LBTEST = c("TSH", "FT4"),
    LBORRES = c(round(tsh, 2), round(ft4, 2)),
    LBORRESU = c("mIU/L", "ng/dL"),
    LBNRIND = c(tsh_ind, ft4_ind)
  )
}

# ─── Immune-Mediated AEs ────────────────────────────────────────────────────

#' Generate immune-mediated AEs for one cycle
generate_immune_aes <- function(is_pembro, on_treatment, pat, ae_params, visit_day, subjid) {

 # Strong shared immune frailty component drives cross-AE-type correlation
  # F_THYROID is repurposed as the dominant immune susceptibility factor
  shared_immune <- 0.6 * pat$F_THYROID + 0.2 * pat$F_SKIN + 0.2 * pat$F_GI

  # PRURITUS/RASH classified as SKIN (not immune-mediated per publication definition)
  # DIARRHEA classified as IMMUNE_MEDIATED (represents potential immune colitis)
  immune_ae_types <- list(
    list(name = "PRURITUS",  frailty = 0.15 * pat$F_SKIN + 0.85 * shared_immune, param_key = "pruritus", cat = "SKIN"),
    list(name = "RASH",      frailty = 0.15 * pat$F_SKIN + 0.85 * shared_immune, param_key = "rash", cat = "SKIN"),
    list(name = "DIARRHEA",  frailty = 0.15 * pat$F_GI + 0.85 * shared_immune,   param_key = "diarrhea", cat = "IMMUNE_MEDIATED")
  )

  records <- list()
  for (ae in immune_ae_types) {
    p <- ae_params[[ae$param_key]]
    if (is.null(p)) next

    base_prob <- if (is_pembro && on_treatment) p$base_prob_pembro else p$base_prob_placebo
    if (!on_treatment) base_prob <- base_prob * 0.1  # Minimal off-treatment

    adj_prob <- apply_frailty(base_prob, ae$frailty, p$beta_frailty)

    if (runif(1) < adj_prob) {
      grade <- if (runif(1) < p$prob_gr3) sample(3:4, 1, prob = c(0.85, 0.15)) else sample(1:2, 1)
      # Immune-mediated AEs: high relatedness in pembro (drug mechanism),
      # moderate in placebo (investigators uncertain in blinded trial)
      imm_rel <- if (is_pembro) {
        sample(c("RELATED", "POSSIBLY RELATED"), 1, prob = c(0.75, 0.25))
      } else {
        sample(c("POSSIBLY RELATED", "NOT RELATED"), 1, prob = c(0.70, 0.30))
      }
      records[[length(records) + 1]] <- data.table(
        SUBJID = subjid,
        AETERM = ae$name,
        AESTDT = visit_day + sample(0:14, 1),  # Onset within cycle
        AEGR = grade,
        AECAT = ae$cat,
        AEREL = imm_rel
      )
    }
  }

  if (length(records) > 0) rbindlist(records, fill = TRUE) else data.table()
}

# ─── General AEs ─────────────────────────────────────────────────────────────

#' Generate general (non-immune) AEs for one cycle
generate_general_aes <- function(is_pembro, on_treatment, pat, ae_params, visit_day, subjid) {

  general_ae_types <- list(
    list(name = "FATIGUE",   frailty = pat$F_SYSTEMIC, param_key = "fatigue"),
    list(name = "ARTHRALGIA", frailty = pat$F_SYSTEMIC, param_key = "arthralgia"),
    list(name = "NAUSEA",    frailty = pat$F_GI,       param_key = "nausea")
  )

  records <- list()
  for (ae in general_ae_types) {
    p <- ae_params[[ae$param_key]]
    if (is.null(p)) next

    base_prob <- if (is_pembro) p$base_prob_pembro else p$base_prob_placebo
    # General AEs have some background rate even off treatment
    if (!on_treatment) base_prob <- base_prob * 0.3

    adj_prob <- apply_frailty(base_prob, ae$frailty, p$beta_frailty)

    if (runif(1) < adj_prob) {
      grade <- if (runif(1) < p$prob_gr3) 3L else sample(1:2, 1)
      # In a blinded trial, investigators assess causality independently.
      # General AEs (fatigue, arthralgia, nausea) have higher "unrelated"
      # fraction than immune-mediated AEs since they have non-drug causes.
      rel_prob <- if (is_pembro) 0.82 else 0.55
      rel_assign <- if (runif(1) < rel_prob) {
        sample(c("RELATED", "POSSIBLY RELATED"), 1, prob = c(0.3, 0.7))
      } else {
        "NOT RELATED"
      }
      records[[length(records) + 1]] <- data.table(
        SUBJID = subjid,
        AETERM = ae$name,
        AESTDT = visit_day + sample(0:14, 1),
        AEGR = grade,
        AECAT = "GENERAL",
        AEREL = rel_assign
      )
    }
  }

  if (length(records) > 0) rbindlist(records, fill = TRUE) else data.table()
}

# ─── Dose Modification ───────────────────────────────────────────────────────

#' Apply dose modification rules based on AEs this cycle
#' @param current_status character, current dose status
#' @param cycle_aes data.table, AEs this cycle
#' @param dose_params list, dose modification parameters
#' @param cumulative_holds integer, total holds so far
#' @param f_dropout numeric, dropout frailty
#' @param on_treatment logical
#' @param cumulative_ae_count integer, total AEs accumulated so far
#' @param is_pembro logical, whether patient is on pembrolizumab
#' @return list with dose_status
apply_dose_modification <- function(current_status, cycle_aes, dose_params,
                                     cumulative_holds, f_dropout, on_treatment,
                                     cumulative_ae_count = 0L, is_pembro = TRUE) {

  if (current_status == "DISCONTINUED" || !on_treatment) {
    return(list(dose_status = "DISCONTINUED"))
  }

  new_status <- "GIVEN"
  n_aes_this_cycle <- nrow(cycle_aes)

  if (n_aes_this_cycle > 0) {
    max_grade <- max(cycle_aes$AEGR, na.rm = TRUE)
    has_immune <- any(cycle_aes$AECAT %in% c("IMMUNE_MEDIATED", "THYROID"), na.rm = TRUE)

    # Grade 4: high probability of discontinuation
    if (max_grade >= 4L) {
      if (runif(1) < dose_params$discontinue_prob_gr4) {
        new_status <- "DISCONTINUED"
      } else {
        new_status <- "HELD"
      }
    }
    # Grade 3 immune-mediated
    else if (max_grade >= 3L && has_immune) {
      r <- runif(1)
      if (r < dose_params$discontinue_prob_gr3_immune) {
        new_status <- "DISCONTINUED"
      } else if (r < dose_params$discontinue_prob_gr3_immune + dose_params$hold_prob_gr3_immune) {
        new_status <- "HELD"
      }
    }
    # Grade 3 general
    else if (max_grade >= 3L) {
      r <- runif(1)
      if (r < dose_params$discontinue_prob_gr3_general) {
        new_status <- "DISCONTINUED"
      } else if (r < dose_params$discontinue_prob_gr3_general + dose_params$hold_prob_gr3_general) {
        new_status <- "HELD"
      }
    }
  }

  # Cumulative holds threshold
  if (new_status == "HELD" && cumulative_holds >= dose_params$max_holds_before_discontinue) {
    new_status <- "DISCONTINUED"
  }

  # AE-driven voluntary discontinuation (conditional on having AEs)
  # This is the main driver of arm-differential discontinuation:
  # Pembro patients get more AEs → higher cumulative burden → more discontinuation
  if (new_status == "GIVEN" && n_aes_this_cycle >= 1) {
    # Probability increases with cumulative AE burden and is arm-specific
    # Pembro: attributed to drug → higher disc probability per AE
    # Placebo: attributed to disease/other → lower disc probability
    ae_disc_rate <- if (is_pembro) 0.062 else 0.003
    # Escalate with cumulative burden
    burden_factor <- 1.0 + 0.10 * pmin(cumulative_ae_count, 8)
    disc_prob <- ae_disc_rate * n_aes_this_cycle * burden_factor *
                 (1 + 0.4 * pmax(f_dropout, 0))
    if (runif(1) < pmin(disc_prob, 0.35)) {
      new_status <- "DISCONTINUED"
    }
  }

  list(dose_status = new_status)
}
