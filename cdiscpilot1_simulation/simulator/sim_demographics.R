#' =============================================================================
#' CDISC Pilot 01 Simulator - Demographics (DM, SC)
#' Xanomeline in Alzheimer's Disease
#' =============================================================================

#' Generate DM domain
#' @param targets Target values from cdiscpilot01_targets.R
#' @param config Simulation configuration
#' @return DM data frame
sim_dm <- function(targets = CDISCPILOT01_TARGETS, config = SIM_CONFIG) {

  n <- config$n_total

  # Generate site assignments based on actual distribution from Table 14-1.03
  site_ids <- config$site_ids
  n_sites <- length(site_ids)

  # Approximate subjects per site (from reference data)
  site_sizes <- c(41, 18, 25, 16, 25, 21, 31, 9, 24, 13,  # Sites 701-718
                  1, 3, 2, 4, 6, 8, 7)                     # Sites 702-717 (pooled 900)
  site_probs <- site_sizes / sum(site_sizes)
  site_assignment <- sample(site_ids, n, replace = TRUE, prob = site_probs)

  # Sort by site for sequential subject numbering
  site_order <- order(site_assignment)
  site_assignment <- site_assignment[site_order]

  # Generate USUBJIDs
  usubjid <- character(n)
  siteid <- character(n)
  subj_in_site <- table(site_assignment)
  subj_counter <- 1

  for (site in names(subj_in_site)) {
    n_site <- subj_in_site[[site]]
    idx <- subj_counter:(subj_counter + n_site - 1)
    siteid[idx] <- site
    usubjid[idx] <- sprintf("01-%.0f-%03d", as.numeric(site), seq_len(n_site))
    subj_counter <- subj_counter + n_site
  }

  # Randomize to treatment arms (1:1:1)
  # n_placebo=86, n_xan_low=84, n_xan_high=84
  arm_assignment <- c(
    rep("Placebo", config$n_placebo),
    rep("Xanomeline Low Dose", config$n_xan_low),
    rep("Xanomeline High Dose", config$n_xan_high)
  )
  arm <- sample(arm_assignment)  # Random permutation

  # Age - elderly population
  age <- round(pmax(config$age_min, pmin(config$age_max,
    rnorm(n, config$age_mean, config$age_sd))))

  # Sex (44% male, 56% female)
  sex <- sample(c("M", "F"), n, replace = TRUE,
                prob = c(1 - config$female_pct, config$female_pct))

  # Race
  race_names <- names(config$race_probs)
  race_probs <- as.numeric(config$race_probs)
  race <- sample(race_names, n, replace = TRUE, prob = race_probs)

  # Randomization date (staggered over enrollment period)
  enrollment_days <- sample(0:365, n, replace = TRUE)
  randdt <- config$study_start_date + enrollment_days

  # Reference start date (first treatment, same day or next day after randomization)
  rfstdtc <- randdt + sample(0:1, n, replace = TRUE)

  # MMSE at baseline (eligibility: 10-24 for mild-moderate AD)
  mmse <- round(pmax(config$mmse_min, pmin(config$mmse_max,
    rnorm(n, config$mmse_mean, config$mmse_sd))))

  # Disease duration (months)
  disease_duration <- pmax(2, rnorm(n, config$disease_duration_mean, config$disease_duration_sd))

  # Education (years)
  education <- pmax(3, pmin(24, round(rnorm(n, config$education_mean, config$education_sd))))

  # Weight - varies by treatment arm slightly (as observed in reference)
  weight <- numeric(n)
  for (i in 1:n) {
    if (arm[i] == "Placebo") {
      weight[i] <- rnorm(1, 62.8, 12.77)
    } else if (arm[i] == "Xanomeline Low Dose") {
      weight[i] <- rnorm(1, 67.3, 14.12)
    } else {
      weight[i] <- rnorm(1, 70.0, 14.65)
    }
  }
  weight <- pmax(34, pmin(108, round(weight, 1)))

  # Height - correlated with sex
  height <- numeric(n)
  height[sex == "M"] <- rnorm(sum(sex == "M"), 170, 7)
  height[sex == "F"] <- rnorm(sum(sex == "F"), 158, 6)
  height <- pmax(136, pmin(196, round(height, 1)))

  # BMI
  bmi <- round(weight / (height/100)^2, 1)

  # Create DM
  dm <- data.frame(
    STUDYID = config$study_id,
    DOMAIN = "DM",
    USUBJID = usubjid,
    SUBJID = sub(".*-", "", usubjid),
    SITEID = siteid,
    RFSTDTC = format(rfstdtc, "%Y-%m-%d"),
    RFXSTDTC = format(rfstdtc, "%Y-%m-%d"),
    AGE = as.integer(age),
    AGEU = "YEARS",
    SEX = sex,
    RACE = race,
    ARMCD = ifelse(arm == "Placebo", "Pbo",
                   ifelse(arm == "Xanomeline Low Dose", "Xan_Lo", "Xan_Hi")),
    ARM = arm,
    ACTARMCD = ifelse(arm == "Placebo", "Pbo",
                      ifelse(arm == "Xanomeline Low Dose", "Xan_Lo", "Xan_Hi")),
    ACTARM = arm,
    COUNTRY = "USA",  # US-based study
    ETHNIC = sample(c("HISPANIC OR LATINO", "NOT HISPANIC OR LATINO"), n, replace = TRUE,
                    prob = c(0.05, 0.95)),
    stringsAsFactors = FALSE
  )

  # Add internal tracking columns
  dm$.arm <- arm
  dm$.armn <- ifelse(arm == "Placebo", 0, ifelse(arm == "Xanomeline Low Dose", 1, 2))
  dm$.mmse <- mmse
  dm$.disease_duration <- disease_duration
  dm$.education <- education
  dm$.weight <- weight
  dm$.height <- height
  dm$.bmi <- bmi
  dm$.randdt <- randdt
  dm$.rfstdtc <- rfstdtc

  dm
}

#' Generate SC domain (Subject Characteristics)
#' @param dm DM data frame with internal columns
#' @param config Simulation configuration
#' @return SC data frame
sim_sc <- function(dm, config = SIM_CONFIG) {

  n <- nrow(dm)
  records <- list()

  # MMSE - Mini-Mental State Examination
  records$mmse <- data.frame(
    USUBJID = dm$USUBJID,
    SCTESTCD = "MMSCORE",
    SCTEST = "Mini-Mental State Examination Total Score",
    SCORRES = as.character(dm$.mmse),
    SCSTRESC = as.character(dm$.mmse),
    SCSTRESN = dm$.mmse,
    stringsAsFactors = FALSE
  )

  # Disease Duration (months)
  records$disdur <- data.frame(
    USUBJID = dm$USUBJID,
    SCTESTCD = "DISDUR",
    SCTEST = "Duration of Disease",
    SCORRES = sprintf("%.1f", dm$.disease_duration),
    SCSTRESC = sprintf("%.1f", dm$.disease_duration),
    SCSTRESN = round(dm$.disease_duration, 1),
    stringsAsFactors = FALSE
  )

  # Years of Education
  records$educyrs <- data.frame(
    USUBJID = dm$USUBJID,
    SCTESTCD = "EDUCYR",
    SCTEST = "Years of Education",
    SCORRES = as.character(dm$.education),
    SCSTRESC = as.character(dm$.education),
    SCSTRESN = dm$.education,
    stringsAsFactors = FALSE
  )

  # Baseline Weight
  records$weight <- data.frame(
    USUBJID = dm$USUBJID,
    SCTESTCD = "WEIGHT",
    SCTEST = "Baseline Weight",
    SCORRES = sprintf("%.1f", dm$.weight),
    SCSTRESC = sprintf("%.1f", dm$.weight),
    SCSTRESN = dm$.weight,
    stringsAsFactors = FALSE
  )

  # Baseline Height
  records$height <- data.frame(
    USUBJID = dm$USUBJID,
    SCTESTCD = "HEIGHT",
    SCTEST = "Baseline Height",
    SCORRES = sprintf("%.1f", dm$.height),
    SCSTRESC = sprintf("%.1f", dm$.height),
    SCSTRESN = dm$.height,
    stringsAsFactors = FALSE
  )

  # BMI
  records$bmi <- data.frame(
    USUBJID = dm$USUBJID,
    SCTESTCD = "BMI",
    SCTEST = "Body Mass Index",
    SCORRES = sprintf("%.1f", dm$.bmi),
    SCSTRESC = sprintf("%.1f", dm$.bmi),
    SCSTRESN = dm$.bmi,
    stringsAsFactors = FALSE
  )

  # Combine
  sc <- do.call(rbind, records)
  sc$STUDYID <- config$study_id
  sc$DOMAIN <- "SC"
  sc$SCSEQ <- ave(seq_len(nrow(sc)), sc$USUBJID, FUN = seq_along)

  sc[, c("STUDYID", "DOMAIN", "USUBJID", "SCSEQ", "SCTESTCD", "SCTEST",
         "SCORRES", "SCSTRESC", "SCSTRESN")]
}
