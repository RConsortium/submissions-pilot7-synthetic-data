#' =============================================================================
#' CDISC Pilot 01 Simulator - Vital Signs (VS)
#' Xanomeline TTS in Alzheimer's Disease
#' =============================================================================

#' Vital signs parameters for elderly Alzheimer's population
VS_PARAMS <- list(
  WEIGHT = list(name = "Weight", unit = "kg",
                mean = 72, sd = 14, low = 45, high = 120),
  HEIGHT = list(name = "Height", unit = "cm",
                mean = 168, sd = 10, low = 145, high = 195),
  TEMP = list(name = "Temperature", unit = "C",
              mean = 36.6, sd = 0.35, low = 36.0, high = 37.5),
  SYSBP = list(name = "Systolic Blood Pressure", unit = "mmHg",
               mean = 135, sd = 18, low = 90, high = 140),
  DIABP = list(name = "Diastolic Blood Pressure", unit = "mmHg",
               mean = 80, sd = 10, low = 60, high = 90),
  PULSE = list(name = "Pulse Rate", unit = "beats/min",
               mean = 72, sd = 10, low = 60, high = 100),
  RESP = list(name = "Respiratory Rate", unit = "breaths/min",
              mean = 16, sd = 2, low = 12, high = 20)
)

#' Simulate Vital Signs domain
#' @param dm DM data frame with internal columns
#' @param disposition Disposition data with completion status
#' @param config Simulation configuration
#' @return VS data frame
sim_vs <- function(dm, disposition, config = SIM_CONFIG) {

  n <- nrow(dm)

  # Define visit timepoints for vitals (study days)
  # Vitals at each study visit: Screening, Baseline, Weeks 2, 4, 8, 12, 16, 20, 24
  vs_visits <- data.frame(
    visit_day = c(-7, 1, 15, 29, 57, 85, 113, 141, 169),
    visit_name = c("SCREENING", "BASELINE", "WEEK 2", "WEEK 4", "WEEK 8",
                   "WEEK 12", "WEEK 16", "WEEK 20", "WEEK 24"),
    visit_num = c(1, 2, 3, 4, 5, 6, 7, 8, 9),
    week = c(NA, 0, 2, 4, 8, 12, 16, 20, 24),
    stringsAsFactors = FALSE
  )

  vs_list <- list()

  for (i in 1:n) {
    subj <- dm[i, ]
    completed <- disposition$completed_wk24[i]
    disc_week <- disposition$disc_week[i]

    # Determine last visit week
    if (completed) {
      last_week <- 24
    } else if (!is.na(disc_week)) {
      last_week <- disc_week
    } else {
      last_week <- 0
    }

    # Get applicable visits
    subj_vs_visits <- vs_visits[is.na(vs_visits$week) | vs_visits$week <= last_week, ]

    if (nrow(subj_vs_visits) == 0) next

    # Subject-specific baseline values
    subj_baseline <- list()
    for (test_code in names(VS_PARAMS)) {
      params <- VS_PARAMS[[test_code]]
      subj_baseline[[test_code]] <- rnorm(1, params$mean, params$sd)
    }

    # Elderly population characteristics:
    # - Higher baseline BP (adjusted in params)
    # - Weight generally stable (unlike cancer cachexia)
    # - Potential slight BP effects from cholinergic drug (bradycardia, hypotension)

    subj_vs <- list()
    seq_num <- 1

    for (v in 1:nrow(subj_vs_visits)) {
      visit <- subj_vs_visits[v, ]

      for (test_code in names(VS_PARAMS)) {
        params <- VS_PARAMS[[test_code]]

        if (visit$visit_name == "SCREENING") {
          # Baseline value
          value <- subj_baseline[[test_code]]
        } else {
          # On-treatment values
          if (test_code == "HEIGHT") {
            # Height doesn't change
            value <- subj_baseline[[test_code]]
          } else if (test_code == "WEIGHT") {
            # Elderly AD patients - weight relatively stable
            # Small random variation
            value <- subj_baseline[[test_code]] + rnorm(1, 0, 0.5)
          } else if (test_code == "PULSE" && subj$.arm != "Placebo") {
            # Cholinergic effect: potential bradycardia with Xanomeline
            # Small decrease in pulse for active treatment
            week <- visit$week
            if (!is.na(week) && week > 0) {
              bradycardia_effect <- if (subj$.arm == "Xanomeline High Dose") -3 else -2
              value <- subj_baseline[[test_code]] + bradycardia_effect + rnorm(1, 0, params$sd * 0.2)
            } else {
              value <- subj_baseline[[test_code]] + rnorm(1, 0, params$sd * 0.2)
            }
          } else if (test_code == "SYSBP" && subj$.arm != "Placebo") {
            # Potential mild hypotension with Xanomeline
            week <- visit$week
            if (!is.na(week) && week > 0) {
              bp_effect <- if (subj$.arm == "Xanomeline High Dose") -4 else -2
              value <- subj_baseline[[test_code]] + bp_effect + rnorm(1, 0, params$sd * 0.2)
            } else {
              value <- subj_baseline[[test_code]] + rnorm(1, 0, params$sd * 0.2)
            }
          } else {
            # Other vitals - small random variation
            value <- subj_baseline[[test_code]] + rnorm(1, 0, params$sd * 0.15)
          }
        }

        # Ensure reasonable bounds
        value <- max(params$low * 0.8, min(params$high * 1.2, value))

        subj_vs[[seq_num]] <- data.frame(
          STUDYID = config$study_id,
          DOMAIN = "VS",
          USUBJID = subj$USUBJID,
          VSSEQ = seq_num,
          VSTESTCD = test_code,
          VSTEST = params$name,
          VSORRES = round(value, 1),
          VSORRESU = params$unit,
          VSSTRESN = round(value, 1),
          VSSTRESU = params$unit,
          VSBLFL = if (visit$visit_name == "SCREENING") "Y" else "",
          VISITNUM = visit$visit_num,
          VISIT = visit$visit_name,
          VISITDY = visit$visit_day,
          VSDTC = format(subj$.randdt + visit$visit_day + sample(-1:1, 1), "%Y-%m-%d"),
          VSDY = visit$visit_day,
          stringsAsFactors = FALSE
        )
        seq_num <- seq_num + 1
      }
    }

    if (length(subj_vs) > 0) {
      vs_list[[i]] <- do.call(rbind, subj_vs)
    }
  }

  vs <- do.call(rbind, vs_list)

  vs
}
