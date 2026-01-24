#' =============================================================================
#' CDISC Pilot 01 Simulator - Exposure (EX)
#' Xanomeline Transdermal Therapeutic System
#' =============================================================================

#' Generate EX domain
#' @param dm DM data frame
#' @param disposition Disposition data with completion status
#' @param config Simulation configuration
#' @return EX data frame
sim_ex <- function(dm, disposition, config = SIM_CONFIG) {

  ex_records <- list()

  for (i in 1:nrow(dm)) {
    subj <- dm[i, ]
    arm <- subj$.arm

    # Get treatment duration from disposition
    completed <- disposition$completed_wk24[i]
    disc_week <- disposition$disc_week[i]

    if (completed) {
      # Completed Week 24 treatment
      treatment_weeks <- 24
    } else if (!is.na(disc_week)) {
      treatment_weeks <- disc_week
    } else {
      treatment_weeks <- 1  # Minimal exposure
    }

    # Treatment days
    treatment_days <- treatment_weeks * 7

    # Determine dose based on treatment arm
    if (arm == "Placebo") {
      daily_dose <- 0
      extrt <- "PLACEBO"
    } else if (arm == "Xanomeline Low Dose") {
      daily_dose <- config$dose_low_mg  # 54 mg
      extrt <- "XANOMELINE"
    } else {
      daily_dose <- config$dose_high_mg  # 81 mg
      extrt <- "XANOMELINE"
    }

    # Create exposure record (one record per treatment period)
    # In transdermal studies, typically one record covers the treatment period
    start_date <- subj$.rfstdtc
    end_date <- start_date + treatment_days - 1

    # Calculate cumulative dose
    cumulative_dose <- daily_dose * treatment_days

    # Add some variability in compliance (95-100% for those who stay on study)
    compliance <- runif(1, 0.95, 1.0)
    actual_cumulative_dose <- round(cumulative_dose * compliance, 1)
    avg_daily_dose <- if (treatment_days > 0) round(actual_cumulative_dose / treatment_days, 1) else 0

    ex_records[[length(ex_records) + 1]] <- data.frame(
      USUBJID = subj$USUBJID,
      EXTRT = extrt,
      EXDOSE = avg_daily_dose,
      EXDOSU = "mg",
      EXDOSFRQ = "QD",  # Once daily (apply patch daily)
      EXDOSFRM = "PATCH",
      EXROUTE = "TRANSDERMAL",
      EXSTDTC = format(start_date, "%Y-%m-%d"),
      EXENDTC = format(end_date, "%Y-%m-%d"),
      EXSTDY = 1,
      EXENDY = as.integer(treatment_days),
      EXDUR = treatment_days,
      EXCUMDOS = actual_cumulative_dose,
      stringsAsFactors = FALSE
    )
  }

  ex <- do.call(rbind, ex_records)
  ex$STUDYID <- config$study_id
  ex$DOMAIN <- "EX"
  ex$EXSEQ <- 1  # One record per subject for transdermal

  ex[, c("STUDYID", "DOMAIN", "USUBJID", "EXSEQ", "EXTRT", "EXDOSE", "EXDOSU",
         "EXDOSFRQ", "EXDOSFRM", "EXROUTE", "EXSTDTC", "EXENDTC", "EXSTDY",
         "EXENDY", "EXDUR", "EXCUMDOS")]
}
