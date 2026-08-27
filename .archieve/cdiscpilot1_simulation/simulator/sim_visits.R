#' =============================================================================
#' CDISC Pilot 01 Simulator - Subject Visits (SV)
#' Xanomeline TTS in Alzheimer's Disease
#' =============================================================================

#' Simulate Subject Visits domain
#' @param dm DM data frame with internal columns
#' @param disposition Disposition data with completion status
#' @param config Simulation configuration
#' @return SV data frame
sim_sv <- function(dm, disposition, config = SIM_CONFIG) {

  n <- nrow(dm)

  # Define visit schedule for CDISC Pilot 01 Alzheimer's study
  # Treatment visits at baseline, weeks 2, 4, 8, 12, 16, 20, 24
  # Follow-up at week 26
  visit_schedule <- data.frame(
    VISITNUM = c(1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 100),
    VISIT = c("SCREENING", "BASELINE", "WEEK 2", "WEEK 4", "WEEK 8",
              "WEEK 12", "WEEK 16", "WEEK 20", "WEEK 24", "END OF TREATMENT",
              "WEEK 26", "UNSCHEDULED"),
    VISITDY = c(-14, 1, 15, 29, 57, 85, 113, 141, 169, NA, 183, NA),
    WEEK = c(NA, 0, 2, 4, 8, 12, 16, 20, 24, NA, 26, NA),
    stringsAsFactors = FALSE
  )

  sv_list <- list()

  for (i in 1:n) {
    subj <- dm[i, ]
    completed <- disposition$completed_wk24[i]
    disc_week <- disposition$disc_week[i]

    # Determine last treatment visit based on disposition
    if (completed) {
      last_treatment_week <- 24
    } else if (!is.na(disc_week)) {
      last_treatment_week <- disc_week
    } else {
      last_treatment_week <- 0  # At least baseline
    }

    # Select visits up to discontinuation
    # Always include screening and baseline
    subj_visits <- visit_schedule[visit_schedule$VISITNUM %in% c(1, 2), ]

    # Add treatment visits based on when they discontinued
    treatment_visits <- visit_schedule[!is.na(visit_schedule$WEEK) &
                                         visit_schedule$WEEK > 0 &
                                         visit_schedule$WEEK <= last_treatment_week, ]
    if (nrow(treatment_visits) > 0) {
      subj_visits <- rbind(subj_visits, treatment_visits)
    }

    # Add End of Treatment visit
    eot <- visit_schedule[visit_schedule$VISIT == "END OF TREATMENT", ]
    if (completed) {
      eot$VISITDY <- 169  # Day 169 (Week 24)
    } else {
      eot$VISITDY <- max(subj_visits$VISITDY, na.rm = TRUE) + sample(1:7, 1)
    }
    subj_visits <- rbind(subj_visits, eot)

    # Add Week 26 follow-up if completed treatment or close to completion
    if (completed || last_treatment_week >= 20) {
      fu <- visit_schedule[visit_schedule$VISIT == "WEEK 26", ]
      subj_visits <- rbind(subj_visits, fu)
    }

    # Calculate actual dates with some variability (+/- 3 days window)
    subj_visits$SVSTDTC <- as.character(format(
      subj$.randdt + subj_visits$VISITDY + sample(-3:3, nrow(subj_visits), replace = TRUE),
      "%Y-%m-%d"
    ))

    # Fix screening date (before randomization)
    subj_visits$SVSTDTC[subj_visits$VISIT == "SCREENING"] <-
      format(subj$.randdt - sample(7:21, 1), "%Y-%m-%d")

    # Add subject identifiers
    subj_visits$STUDYID <- config$study_id
    subj_visits$DOMAIN <- "SV"
    subj_visits$USUBJID <- subj$USUBJID

    # Add sequence number
    subj_visits$SVSEQ <- seq_len(nrow(subj_visits))

    # Add end date (same as start for most visits)
    subj_visits$SVENDTC <- subj_visits$SVSTDTC

    sv_list[[i]] <- subj_visits
  }

  sv <- do.call(rbind, sv_list)

  # Reorder and select columns
  sv <- sv[, c("STUDYID", "DOMAIN", "USUBJID", "SVSEQ", "VISITNUM", "VISIT",
               "VISITDY", "SVSTDTC", "SVENDTC")]

  sv
}
