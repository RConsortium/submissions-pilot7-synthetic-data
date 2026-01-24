#' =============================================================================
#' CDISC Pilot 01 Simulator - Disposition (DS)
#' =============================================================================

#' Simulate Disposition domain
#' @param dm DM data frame with internal columns
#' @param disposition Completion status from generate_completion_status()
#' @param config Simulation configuration
#' @return DS data frame
sim_ds <- function(dm, disposition, config = SIM_CONFIG) {

  n <- nrow(dm)
  ds_list <- list()

  for (i in 1:n) {
    subj <- dm[i, ]
    completed <- disposition$completed_wk24[i]
    disc_week <- disposition$disc_week[i]
    disc_reason <- disposition$disc_reason[i]

    subj_ds <- list()
    record_num <- 1

    # 1. Informed Consent
    subj_ds[[record_num]] <- data.frame(
      STUDYID = config$study_id,
      DOMAIN = "DS",
      USUBJID = subj$USUBJID,
      DSSEQ = record_num,
      DSTERM = "INFORMED CONSENT OBTAINED",
      DSDECOD = "INFORMED CONSENT OBTAINED",
      DSCAT = "PROTOCOL MILESTONE",
      DSSCAT = "",
      DSSTDTC = format(subj$.randdt - sample(7:21, 1), "%Y-%m-%d"),
      DSDY = NA_integer_,
      stringsAsFactors = FALSE
    )
    record_num <- record_num + 1

    # 2. Randomization
    subj_ds[[record_num]] <- data.frame(
      STUDYID = config$study_id,
      DOMAIN = "DS",
      USUBJID = subj$USUBJID,
      DSSEQ = record_num,
      DSTERM = "RANDOMIZED",
      DSDECOD = "RANDOMIZED",
      DSCAT = "PROTOCOL MILESTONE",
      DSSCAT = "",
      DSSTDTC = format(subj$.randdt, "%Y-%m-%d"),
      DSDY = 1L,
      stringsAsFactors = FALSE
    )
    record_num <- record_num + 1

    # 3. Treatment disposition
    if (completed) {
      # Completed Week 24 treatment
      trt_disc_reason <- "COMPLETED"
      trt_disc_term <- "COMPLETED TREATMENT"
      trt_end_date <- subj$.randdt + (24 * 7)  # Week 24
    } else {
      # Early termination
      trt_disc_reason <- disc_reason
      trt_disc_term <- disc_reason
      trt_end_date <- subj$.randdt + (disc_week * 7)
    }

    subj_ds[[record_num]] <- data.frame(
      STUDYID = config$study_id,
      DOMAIN = "DS",
      USUBJID = subj$USUBJID,
      DSSEQ = record_num,
      DSTERM = trt_disc_term,
      DSDECOD = trt_disc_reason,
      DSCAT = "DISPOSITION EVENT",
      DSSCAT = "TREATMENT",
      DSSTDTC = format(trt_end_date, "%Y-%m-%d"),
      DSDY = as.integer(trt_end_date - subj$.randdt) + 1L,
      stringsAsFactors = FALSE
    )
    record_num <- record_num + 1

    # 4. Study disposition (Week 26 or early)
    if (completed) {
      # Completed study (including follow-up)
      # ~90% of Week 24 completers also complete study (Week 26)
      if (runif(1) < 0.90) {
        study_disc_reason <- "COMPLETED"
        study_disc_term <- "COMPLETED STUDY"
        study_end_date <- subj$.randdt + (26 * 7)  # Week 26
      } else {
        # Few completers withdraw during follow-up
        study_disc_probs <- c(
          "LOST TO FOLLOW-UP" = 0.30,
          "WITHDREW CONSENT" = 0.50,
          "OTHER" = 0.20
        )
        study_disc_reason <- sample(names(study_disc_probs), 1, prob = study_disc_probs)
        study_disc_term <- study_disc_reason
        study_end_date <- subj$.randdt + (24 * 7) + sample(1:14, 1)  # Shortly after Week 24
      }
    } else {
      # Early terminator from treatment
      if (disc_reason == "DEATH") {
        study_disc_reason <- "DEATH"
        study_disc_term <- "DEATH"
        study_end_date <- trt_end_date
      } else {
        study_disc_reason <- disc_reason
        study_disc_term <- disc_reason
        study_end_date <- trt_end_date + sample(0:14, 1)  # Same day or shortly after
      }
    }

    subj_ds[[record_num]] <- data.frame(
      STUDYID = config$study_id,
      DOMAIN = "DS",
      USUBJID = subj$USUBJID,
      DSSEQ = record_num,
      DSTERM = study_disc_term,
      DSDECOD = study_disc_reason,
      DSCAT = "DISPOSITION EVENT",
      DSSCAT = "STUDY",
      DSSTDTC = format(study_end_date, "%Y-%m-%d"),
      DSDY = as.integer(study_end_date - subj$.randdt) + 1L,
      stringsAsFactors = FALSE
    )

    ds_list[[i]] <- do.call(rbind, subj_ds)
  }

  ds <- do.call(rbind, ds_list)
  ds
}
