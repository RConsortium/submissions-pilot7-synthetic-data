#' =============================================================================
#' CDISC Pilot 01 Simulator - Cognitive Efficacy Assessments (QS)
#' ADAS-Cog and CIBIC+ for Alzheimer's Disease
#' =============================================================================

#' Generate disposition status first (to know who completes Week 24)
#' This is a helper that runs before the full disposition
#' @param dm DM data frame
#' @param config Simulation configuration
#' @return Data frame with completion status
generate_completion_status <- function(dm, config = SIM_CONFIG) {

  n <- nrow(dm)
  completed <- logical(n)
  disc_week <- numeric(n)
  disc_reason <- character(n)

  for (i in 1:n) {
    arm <- dm$.arm[i]
    completion_prob <- config$completion_prob[[arm]]

    if (runif(1) < completion_prob) {
      completed[i] <- TRUE
      disc_week[i] <- NA  # Completed - no discontinuation
      disc_reason[i] <- "COMPLETED"
    } else {
      completed[i] <- FALSE
      # Determine when they discontinued (weighted toward earlier for active arms)
      if (arm == "Placebo") {
        disc_week[i] <- sample(1:24, 1, prob = rep(1, 24))
      } else {
        # Active arms: higher probability of early discontinuation due to AEs
        early_weights <- c(rep(3, 4), rep(2, 4), rep(1.5, 4), rep(1, 12))
        disc_week[i] <- sample(1:24, 1, prob = early_weights)
      }

      # Assign discontinuation reason based on config probabilities
      reason_probs <- config$disc_reason_probs[[arm]]
      disc_reason[i] <- sample(names(reason_probs), 1, prob = reason_probs)
    }
  }

  data.frame(
    USUBJID = dm$USUBJID,
    completed_wk24 = completed,
    disc_week = disc_week,
    disc_reason = disc_reason,
    stringsAsFactors = FALSE
  )
}

#' Simulate QS domain (Questionnaires) - ADAS-Cog and CIBIC+
#' @param dm DM data frame with internal columns
#' @param disposition Disposition data (completion status)
#' @param config Simulation configuration
#' @return List with qs data frame and efficacy summary
sim_efficacy <- function(dm, disposition, config = SIM_CONFIG) {

  n <- nrow(dm)

  # Determine completion status from disposition
  completed <- disposition$completed_wk24

  # Initialize data frames
  adas_data <- data.frame(
    USUBJID = character(),
    VISITNUM = numeric(),
    VISIT = character(),
    QSTESTCD = character(),
    QSTEST = character(),
    QSORRES = character(),
    QSSTRESC = character(),
    QSSTRESN = numeric(),
    QSDTC = character(),
    QSBLFL = character(),
    stringsAsFactors = FALSE
  )

  cibic_data <- data.frame(
    USUBJID = character(),
    VISITNUM = numeric(),
    VISIT = character(),
    QSTESTCD = character(),
    QSTEST = character(),
    QSORRES = character(),
    QSSTRESC = character(),
    QSSTRESN = numeric(),
    QSDTC = character(),
    QSBLFL = character(),
    stringsAsFactors = FALSE
  )

  # For each subject
  for (i in 1:n) {
    subj <- dm[i, ]
    arm <- subj$.arm
    subj_completed <- completed[i]
    disc_week <- disposition$disc_week[i]

    # Baseline ADAS-Cog (everyone has this)
    baseline_mean <- config$adas_baseline_mean[[arm]]
    baseline_sd <- config$adas_baseline_sd[[arm]]
    adas_baseline <- max(3, min(70, round(rnorm(1, baseline_mean, baseline_sd))))

    # Get treatment start date for this subject
    rfstdtc <- subj$.rfstdtc

    # Add baseline ADAS-Cog
    adas_data <- rbind(adas_data, data.frame(
      USUBJID = subj$USUBJID,
      VISITNUM = 1,
      VISIT = "BASELINE",
      QSTESTCD = "ACTOT",
      QSTEST = "ADAS-Cog (11) Total Score",
      QSORRES = as.character(adas_baseline),
      QSSTRESC = as.character(adas_baseline),
      QSSTRESN = adas_baseline,
      QSDTC = format(rfstdtc, "%Y-%m-%d"),
      QSBLFL = "Y",
      stringsAsFactors = FALSE
    ))

    # Intermediate visits (if subject stayed on study): Week 4, 8, 12
    intermediate_visits <- c(4, 8, 12)
    visit_nums <- c(3, 4, 5)
    visit_names <- c("WEEK 4", "WEEK 8", "WEEK 12")

    last_adas <- adas_baseline
    for (v in seq_along(intermediate_visits)) {
      if (is.na(disc_week) || disc_week > intermediate_visits[v]) {
        # Subject was still on study at this visit
        change_rate <- config$adas_change_mean[[arm]] / 24  # change per week
        change_sd <- config$adas_change_sd[[arm]] / sqrt(24)

        expected_change <- intermediate_visits[v] * change_rate
        visit_change <- rnorm(1, expected_change, change_sd * sqrt(intermediate_visits[v]))
        adas_visit <- max(3, min(70, round(adas_baseline + visit_change)))
        last_adas <- adas_visit

        adas_data <- rbind(adas_data, data.frame(
          USUBJID = subj$USUBJID,
          VISITNUM = visit_nums[v],
          VISIT = visit_names[v],
          QSTESTCD = "ACTOT",
          QSTEST = "ADAS-Cog (11) Total Score",
          QSORRES = as.character(adas_visit),
          QSSTRESC = as.character(adas_visit),
          QSSTRESN = adas_visit,
          QSDTC = format(rfstdtc + intermediate_visits[v] * 7, "%Y-%m-%d"),
          QSBLFL = "",
          stringsAsFactors = FALSE
        ))
      }
    }

    # Week 24 ADAS-Cog (LOCF)
    change_mean <- config$adas_change_mean[[arm]]
    change_sd <- config$adas_change_sd[[arm]]

    if (subj_completed) {
      # Completed - actual Week 24 assessment
      adas_change <- rnorm(1, change_mean, change_sd)
      adas_week24 <- max(3, min(70, round(adas_baseline + adas_change)))

      adas_data <- rbind(adas_data, data.frame(
        USUBJID = subj$USUBJID,
        VISITNUM = 7,
        VISIT = "WEEK 24",
        QSTESTCD = "ACTOT",
        QSTEST = "ADAS-Cog (11) Total Score",
        QSORRES = as.character(adas_week24),
        QSSTRESC = as.character(adas_week24),
        QSSTRESN = adas_week24,
        QSDTC = format(rfstdtc + 24 * 7, "%Y-%m-%d"),
        QSBLFL = "",
        stringsAsFactors = FALSE
      ))
    } else {
      # Early termination - use LOCF (last observation)
      adas_week24 <- last_adas
    }

    # CIBIC+ at Week 24 (1-7 scale)
    cibic_mean <- config$cibic_week24_mean[[arm]]
    cibic_sd <- config$cibic_week24_sd[[arm]]

    if (subj_completed) {
      cibic_score <- round(pmax(1, pmin(7, rnorm(1, cibic_mean, cibic_sd))))
    } else {
      # For early terminators, impute slightly worse CIBIC+ (conservative)
      cibic_score <- round(pmax(1, pmin(7, rnorm(1, cibic_mean + 0.3, cibic_sd))))
    }

    # Map to response categories
    cibic_cat <- switch(as.character(cibic_score),
      "1" = "MARKED IMPROVEMENT",
      "2" = "MODERATE IMPROVEMENT",
      "3" = "MINIMAL IMPROVEMENT",
      "4" = "NO CHANGE",
      "5" = "MINIMAL WORSENING",
      "6" = "MODERATE WORSENING",
      "7" = "MARKED WORSENING"
    )

    cibic_data <- rbind(cibic_data, data.frame(
      USUBJID = subj$USUBJID,
      VISITNUM = 7,
      VISIT = "WEEK 24",
      QSTESTCD = "CIBIC",
      QSTEST = "CIBIC+ Global Assessment",
      QSORRES = cibic_cat,
      QSSTRESC = as.character(cibic_score),
      QSSTRESN = cibic_score,
      QSDTC = format(rfstdtc + 24 * 7, "%Y-%m-%d"),
      QSBLFL = "",
      stringsAsFactors = FALSE
    ))
  }

  # Combine ADAS-Cog and CIBIC+ into QS domain
  qs <- rbind(adas_data, cibic_data)
  qs$STUDYID <- config$study_id
  qs$DOMAIN <- "QS"
  qs$QSCAT <- ifelse(qs$QSTESTCD == "ACTOT", "ADAS-COG", "CIBIC+")

  # Add sequence numbers
  qs <- qs[order(qs$USUBJID, qs$QSCAT, qs$VISITNUM), ]
  qs$QSSEQ <- ave(seq_len(nrow(qs)), qs$USUBJID, FUN = seq_along)

  # Create efficacy summary for analysis
  adas_baseline_all <- qs[qs$QSTESTCD == "ACTOT" & qs$VISIT == "BASELINE", ]

  # Get last ADAS-Cog for each subject (Week 24 actual or LOCF)
  adas_last <- aggregate(QSSTRESN ~ USUBJID,
                         data = qs[qs$QSTESTCD == "ACTOT" & qs$VISIT != "BASELINE", ],
                         FUN = function(x) tail(x, 1))
  names(adas_last)[2] <- "ADAS_WEEK24"

  efficacy_summary <- merge(
    adas_baseline_all[, c("USUBJID", "QSSTRESN")],
    adas_last,
    by = "USUBJID"
  )
  names(efficacy_summary)[2] <- "ADAS_BASELINE"
  efficacy_summary$ADAS_CHANGE <- efficacy_summary$ADAS_WEEK24 - efficacy_summary$ADAS_BASELINE

  cibic_all <- qs[qs$QSTESTCD == "CIBIC", c("USUBJID", "QSSTRESN")]
  names(cibic_all)[2] <- "CIBIC_WEEK24"

  efficacy_summary <- merge(efficacy_summary, cibic_all, by = "USUBJID")

  # Add treatment arm
  efficacy_summary <- merge(efficacy_summary, dm[, c("USUBJID", "ARM")], by = "USUBJID")

  # Reorder QS columns
  qs <- qs[, c("STUDYID", "DOMAIN", "USUBJID", "QSSEQ", "QSTESTCD", "QSTEST",
               "QSCAT", "VISITNUM", "VISIT", "QSDTC", "QSBLFL", "QSORRES", "QSSTRESC", "QSSTRESN")]

  list(
    qs = qs,
    efficacy_summary = efficacy_summary
  )
}
