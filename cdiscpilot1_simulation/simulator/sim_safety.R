#' =============================================================================
#' CDISC Pilot 01 Simulator - Safety (AE)
#' Xanomeline Transdermal System - Adverse Events
#' =============================================================================

#' Define AE terms with rates by treatment group
#' Rates from Table 14-5.01
AE_TERMS <- data.frame(
  aedecod = c(
    # Application Site Reactions (General Disorders SOC)
    "Application site pruritus",
    "Application site erythema",
    "Application site irritation",
    "Application site dermatitis",
    "Application site vesicles",
    # Skin and Subcutaneous Tissue Disorders
    "Pruritus",
    "Erythema",
    "Rash",
    "Hyperhidrosis",
    "Skin irritation",
    # Nervous System Disorders
    "Dizziness",
    "Headache",
    "Syncope",
    "Somnolence",
    # Gastrointestinal Disorders
    "Nausea",
    "Vomiting",
    "Diarrhoea",
    # Cardiac Disorders
    "Sinus bradycardia",
    "Myocardial infarction",
    # Psychiatric Disorders
    "Insomnia",
    "Confusional state",
    "Agitation",
    "Anxiety",
    # Respiratory
    "Cough",
    "Nasal congestion",
    # Infections
    "Nasopharyngitis",
    "Upper respiratory tract infection",
    # General
    "Fatigue"
  ),
  aebodsys = c(
    rep("General disorders and administration site conditions", 5),
    rep("Skin and subcutaneous tissue disorders", 5),
    rep("Nervous system disorders", 4),
    rep("Gastrointestinal disorders", 3),
    rep("Cardiac disorders", 2),
    rep("Psychiatric disorders", 4),
    rep("Respiratory, thoracic and mediastinal disorders", 2),
    rep("Infections and infestations", 2),
    "General disorders and administration site conditions"
  ),
  # Rates from Table 14-5.01 (Placebo, Xan Low, Xan High)
  rate_placebo = c(
    0.070, 0.035, 0.035, 0.058, 0.012,  # App site
    0.093, 0.093, 0.058, 0.023, 0.035,  # Skin
    0.023, 0.035, 0.000, 0.023,          # Nervous
    0.035, 0.035, 0.105,                 # GI
    0.023, 0.047,                        # Cardiac
    0.023, 0.023, 0.023, 0.000,          # Psych
    0.012, 0.035,                        # Resp
    0.023, 0.070,                        # Infection
    0.012                                # Fatigue
  ),
  rate_xan_low = c(
    0.262, 0.143, 0.107, 0.107, 0.048,  # App site
    0.250, 0.167, 0.155, 0.048, 0.071,  # Skin
    0.095, 0.036, 0.048, 0.036,          # Nervous
    0.036, 0.036, 0.048,                 # GI
    0.083, 0.024,                        # Cardiac
    0.000, 0.036, 0.024, 0.036,          # Psych
    0.060, 0.012,                        # Resp
    0.048, 0.012,                        # Infection
    0.060                                # Fatigue
  ),
  rate_xan_high = c(
    0.262, 0.179, 0.107, 0.083, 0.071,  # App site
    0.310, 0.167, 0.107, 0.095, 0.060,  # Skin
    0.131, 0.060, 0.036, 0.012,          # Nervous
    0.071, 0.083, 0.048,                 # GI
    0.095, 0.048,                        # Cardiac
    0.024, 0.012, 0.012, 0.000,          # Psych
    0.060, 0.036,                        # Resp
    0.071, 0.036,                        # Infection
    0.060                                # Fatigue
  ),
  # Fraction of events that are Grade 3+ (most are Grade 1-2 for this study)
  gr3_fraction = c(
    0.05, 0.02, 0.02, 0.02, 0.02,       # App site (mostly mild)
    0.05, 0.02, 0.05, 0.02, 0.02,       # Skin
    0.10, 0.05, 0.30, 0.05,              # Nervous (syncope can be serious)
    0.05, 0.10, 0.10,                    # GI
    0.30, 0.50,                          # Cardiac (can be serious)
    0.05, 0.10, 0.10, 0.05,              # Psych
    0.02, 0.02,                          # Resp
    0.05, 0.10,                          # Infection
    0.05                                 # Fatigue
  ),
  is_app_site = c(
    rep(TRUE, 5),
    rep(FALSE, 23)
  ),
  stringsAsFactors = FALSE
)

#' Generate AE domain
#' @param dm DM data frame
#' @param disposition Disposition data
#' @param config Simulation configuration
#' @return AE data frame
sim_ae <- function(dm, disposition, config = SIM_CONFIG) {

  ae_records <- list()

  for (i in 1:nrow(dm)) {
    subj <- dm[i, ]
    arm <- subj$.arm

    # Get rates for this arm
    if (arm == "Placebo") {
      rates <- AE_TERMS$rate_placebo
    } else if (arm == "Xanomeline Low Dose") {
      rates <- AE_TERMS$rate_xan_low
    } else {
      rates <- AE_TERMS$rate_xan_high
    }

    # Get exposure duration to scale AE probability
    disc_week <- disposition$disc_week[i]
    completed <- disposition$completed_wk24[i]
    if (completed) {
      exposure_fraction <- 1.0
    } else if (!is.na(disc_week)) {
      exposure_fraction <- disc_week / 24
    } else {
      exposure_fraction <- 0.1
    }

    # Adjust rates based on exposure duration (longer exposure = more AEs)
    adjusted_rates <- 1 - (1 - rates)^exposure_fraction

    # Sample which AEs this subject experiences
    has_ae <- rbinom(nrow(AE_TERMS), 1, adjusted_rates)

    for (j in which(has_ae == 1)) {
      ae_term <- AE_TERMS[j, ]

      # Determine grade (most are mild for transdermal)
      is_gr3plus <- rbinom(1, 1, ae_term$gr3_fraction)
      if (is_gr3plus) {
        grade <- sample(3:4, 1, prob = c(0.85, 0.15))
      } else {
        grade <- sample(1:2, 1, prob = c(0.45, 0.55))
      }

      # Onset day (application site AEs tend to be early)
      if (ae_term$is_app_site) {
        onset_day <- round(rweibull(1, shape = 2, scale = 14))  # Early onset
      } else {
        onset_day <- round(rweibull(1, shape = 1.5, scale = 42))  # Distributed
      }
      onset_day <- max(1, min(onset_day, exposure_fraction * 24 * 7))

      # Duration (days)
      if (ae_term$is_app_site) {
        duration <- round(rweibull(1, shape = 1.5, scale = 14))  # Shorter
      } else {
        duration <- round(rweibull(1, shape = 1.5, scale = 21))
      }

      # Serious?
      serious <- grade >= 3 | rbinom(1, 1, 0.02)

      # Relationship (application site reactions highly related)
      if (ae_term$is_app_site) {
        relation <- sample(c("RELATED", "POSSIBLY RELATED"), 1, prob = c(0.85, 0.15))
      } else {
        relation <- sample(c("RELATED", "POSSIBLY RELATED", "NOT RELATED"),
                          1, prob = c(0.30, 0.35, 0.35))
      }

      ae_records[[length(ae_records) + 1]] <- data.frame(
        USUBJID = subj$USUBJID,
        AETERM = ae_term$aedecod,
        AEDECOD = ae_term$aedecod,
        AEBODSYS = ae_term$aebodsys,
        AESEV = c("MILD", "MODERATE", "SEVERE", "LIFE-THREATENING")[grade],
        AETOXGR = as.character(grade),
        AESER = ifelse(serious, "Y", "N"),
        AEREL = relation,
        AESTDTC = format(subj$.rfstdtc + onset_day, "%Y-%m-%d"),
        AEENDTC = format(subj$.rfstdtc + onset_day + duration, "%Y-%m-%d"),
        AESTDY = as.integer(onset_day),
        AEENDY = as.integer(onset_day + duration),
        AECAT = ifelse(ae_term$is_app_site, "APPLICATION SITE", "GENERAL"),
        stringsAsFactors = FALSE
      )
    }
  }

  if (length(ae_records) == 0) {
    # Return empty data frame with correct structure
    return(data.frame(
      STUDYID = character(),
      DOMAIN = character(),
      USUBJID = character(),
      AESEQ = integer(),
      AETERM = character(),
      AEDECOD = character(),
      AEBODSYS = character(),
      AECAT = character(),
      AESEV = character(),
      AETOXGR = character(),
      AESER = character(),
      AEREL = character(),
      AESTDTC = character(),
      AEENDTC = character(),
      AESTDY = integer(),
      AEENDY = integer(),
      stringsAsFactors = FALSE
    ))
  }

  ae <- do.call(rbind, ae_records)
  ae$STUDYID <- config$study_id
  ae$DOMAIN <- "AE"
  ae$AESEQ <- ave(seq_len(nrow(ae)), ae$USUBJID, FUN = seq_along)

  ae[, c("STUDYID", "DOMAIN", "USUBJID", "AESEQ", "AETERM", "AEDECOD", "AEBODSYS",
         "AECAT", "AESEV", "AETOXGR", "AESER", "AEREL",
         "AESTDTC", "AEENDTC", "AESTDY", "AEENDY")]
}
