#' =============================================================================
#' CDISC Pilot 01 Simulator - Laboratory (LB)
#' Xanomeline TTS in Alzheimer's Disease
#' =============================================================================

#' Laboratory test parameters for elderly Alzheimer's population
#' Reference ranges adjusted for elderly (65+ years)
LB_PARAMS <- list(
  # Hematology
  HGB = list(name = "Hemoglobin", unit = "g/dL", cat = "HEMATOLOGY",
             mean_m = 14.0, mean_f = 12.5, sd = 1.2,
             low_m = 13.0, high_m = 17.0, low_f = 12.0, high_f = 15.5),
  WBC = list(name = "White Blood Cells", unit = "10^9/L", cat = "HEMATOLOGY",
             mean = 6.5, sd = 1.8, low = 4.0, high = 11.0),
  RBC = list(name = "Red Blood Cells", unit = "10^12/L", cat = "HEMATOLOGY",
             mean_m = 4.7, mean_f = 4.2, sd = 0.4,
             low_m = 4.5, high_m = 5.5, low_f = 4.0, high_f = 5.0),
  PLT = list(name = "Platelets", unit = "10^9/L", cat = "HEMATOLOGY",
             mean = 240, sd = 50, low = 150, high = 400),
  HCT = list(name = "Hematocrit", unit = "%", cat = "HEMATOLOGY",
             mean_m = 42, mean_f = 38, sd = 3,
             low_m = 38, high_m = 50, low_f = 36, high_f = 44),

  # Chemistry - Liver Function
  ALT = list(name = "Alanine Aminotransferase", unit = "U/L", cat = "CHEMISTRY",
             mean = 22, sd = 10, low = 7, high = 56),
  AST = list(name = "Aspartate Aminotransferase", unit = "U/L", cat = "CHEMISTRY",
             mean = 24, sd = 8, low = 10, high = 40),
  ALP = list(name = "Alkaline Phosphatase", unit = "U/L", cat = "CHEMISTRY",
             mean = 70, sd = 20, low = 44, high = 147),
  BILI = list(name = "Bilirubin", unit = "mg/dL", cat = "CHEMISTRY",
              mean = 0.6, sd = 0.25, low = 0.1, high = 1.2),
  ALB = list(name = "Albumin", unit = "g/dL", cat = "CHEMISTRY",
             mean = 3.9, sd = 0.3, low = 3.5, high = 5.0),

  # Chemistry - Renal Function
  CREAT = list(name = "Creatinine", unit = "mg/dL", cat = "CHEMISTRY",
               mean = 1.0, sd = 0.25, low = 0.7, high = 1.3),
  BUN = list(name = "Blood Urea Nitrogen", unit = "mg/dL", cat = "CHEMISTRY",
             mean = 18, sd = 5, low = 8, high = 23),

  # Electrolytes
  SODIUM = list(name = "Sodium", unit = "mmol/L", cat = "CHEMISTRY",
                mean = 140, sd = 2.5, low = 136, high = 145),
  POTASSIUM = list(name = "Potassium", unit = "mmol/L", cat = "CHEMISTRY",
                   mean = 4.3, sd = 0.35, low = 3.5, high = 5.0),
  CHLORIDE = list(name = "Chloride", unit = "mmol/L", cat = "CHEMISTRY",
                  mean = 102, sd = 2, low = 98, high = 106),

  # Glucose
  GLUC = list(name = "Glucose", unit = "mg/dL", cat = "CHEMISTRY",
              mean = 100, sd = 15, low = 70, high = 110)
)

#' Simulate Laboratory domain
#' @param dm DM data frame with internal columns
#' @param disposition Disposition data with completion status
#' @param config Simulation configuration
#' @return LB data frame
sim_lb <- function(dm, disposition, config = SIM_CONFIG) {

  n <- nrow(dm)

  # Define visit timepoints for labs (study days)
  # Labs collected at Screening, Baseline, Week 8, Week 16, Week 24
  lab_visits <- data.frame(
    visit_day = c(-7, 1, 57, 113, 169),
    visit_name = c("SCREENING", "BASELINE", "WEEK 8", "WEEK 16", "WEEK 24"),
    visit_num = c(1, 2, 5, 7, 9),
    week = c(NA, 0, 8, 16, 24),
    stringsAsFactors = FALSE
  )

  lb_list <- list()

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
    subj_lab_visits <- lab_visits[is.na(lab_visits$week) | lab_visits$week <= last_week, ]

    if (nrow(subj_lab_visits) == 0) next

    # Determine sex for sex-specific reference ranges
    is_male <- subj$SEX == "M"

    subj_lb <- list()
    seq_num <- 1

    # Generate stable baseline values for this subject
    subj_baseline <- list()
    for (test_code in names(LB_PARAMS)) {
      params <- LB_PARAMS[[test_code]]

      # Use sex-specific mean if available
      if (!is.null(params$mean_m) && !is.null(params$mean_f)) {
        mean_val <- if (is_male) params$mean_m else params$mean_f
      } else {
        mean_val <- params$mean
      }

      subj_baseline[[test_code]] <- rnorm(1, mean_val, params$sd)
    }

    for (v in 1:nrow(subj_lab_visits)) {
      visit <- subj_lab_visits[v, ]

      for (test_code in names(LB_PARAMS)) {
        params <- LB_PARAMS[[test_code]]

        # Get reference ranges (sex-specific if available)
        if (!is.null(params$low_m) && !is.null(params$low_f)) {
          low_ref <- if (is_male) params$low_m else params$low_f
          high_ref <- if (is_male) params$high_m else params$high_f
        } else {
          low_ref <- params$low
          high_ref <- params$high
        }

        # Generate value
        if (visit$visit_name == "SCREENING") {
          # Baseline value
          value <- subj_baseline[[test_code]]
        } else {
          # Small random variation from baseline (elderly population, stable)
          # Xanomeline doesn't have major lab effects
          value <- subj_baseline[[test_code]] + rnorm(1, 0, params$sd * 0.15)
        }

        # Ensure positive values
        value <- max(0.01, value)

        # Determine if abnormal
        if (value < low_ref) {
          lbnrind <- "LOW"
        } else if (value > high_ref) {
          lbnrind <- "HIGH"
        } else {
          lbnrind <- "NORMAL"
        }

        subj_lb[[seq_num]] <- data.frame(
          STUDYID = config$study_id,
          DOMAIN = "LB",
          USUBJID = subj$USUBJID,
          LBSEQ = seq_num,
          LBTESTCD = test_code,
          LBTEST = params$name,
          LBCAT = params$cat,
          LBORRES = round(value, 2),
          LBORRESU = params$unit,
          LBSTRESN = round(value, 2),
          LBSTRESU = params$unit,
          LBSTNRLO = low_ref,
          LBSTNRHI = high_ref,
          LBNRIND = lbnrind,
          LBBLFL = if (visit$visit_name == "SCREENING") "Y" else "",
          VISITNUM = visit$visit_num,
          VISIT = visit$visit_name,
          VISITDY = visit$visit_day,
          LBDTC = format(subj$.randdt + visit$visit_day + sample(-1:1, 1), "%Y-%m-%d"),
          LBDY = visit$visit_day,
          stringsAsFactors = FALSE
        )
        seq_num <- seq_num + 1
      }
    }

    if (length(subj_lb) > 0) {
      lb_list[[i]] <- do.call(rbind, subj_lb)
    }
  }

  lb <- do.call(rbind, lb_list)

  lb
}
