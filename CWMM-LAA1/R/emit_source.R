# emit_source.R — CRF projection: convert internal data to source CSVs
# =====================================================================

#' Emit all source data CSVs to output/source/
#' @param baseline data.frame
#' @param longitudinal list from simulate_longitudinal()
#' @param outcomes data.frame from derive_outcomes()
#' @param output_dir Output directory path
emit_source_data <- function(baseline, longitudinal, outcomes, output_dir = "output/source") {
  dir.create(output_dir, recursive = TRUE, showWarnings = FALSE)

  # --- Demographics (DM) ---
  dm <- data.frame(
    SUBJID = baseline$SUBJID,
    ARM = baseline$ARM,
    AGE = baseline$AGE,
    SEX = baseline$SEX,
    RACE = baseline$RACE,
    HEIGHT = baseline$HEIGHT,
    BMI_STRAT = baseline$BMI_STRAT,
    RFSTDTC = as.Date("2024-03-01") + sample(0:180, nrow(baseline), replace = TRUE),
    COUNTRY = sample(c("USA", "UK", "Australia", "Canada"), nrow(baseline), replace = TRUE,
                     prob = c(0.5, 0.2, 0.15, 0.15)),
    stringsAsFactors = FALSE
  )
  write.csv(dm, file.path(output_dir, "dm.csv"), row.names = FALSE)

  # --- Vital Signs / Anthropometrics (VS) ---
  wl <- longitudinal$weight_long
  ml <- longitudinal$metabolic_long
  vs <- data.frame(
    SUBJID = wl$SUBJID,
    VISIT_WEEK = wl$VISIT_WEEK,
    WEIGHT = wl$WEIGHT,
    BMI = wl$BMI,
    SYSBP = ml$SYSBP,
    DIABP = ml$DIABP,
    PULSE = ml$PULSE,
    stringsAsFactors = FALSE
  )
  # Add waist at baseline visits
  vs$WAIST <- NA_real_
  for (i in seq_len(nrow(baseline))) {
    idx_bl <- which(vs$SUBJID == baseline$SUBJID[i] & vs$VISIT_WEEK == 0)
    if (length(idx_bl) == 1) vs$WAIST[idx_bl] <- baseline$WAIST_0[i]
  }
  write.csv(vs, file.path(output_dir, "vs.csv"), row.names = FALSE)

  # --- Lab Chemistry (LB) ---
  lb <- data.frame(
    SUBJID = ml$SUBJID,
    VISIT_WEEK = ml$VISIT_WEEK,
    HBA1C = ml$HBA1C,
    GLUC = ml$GLUC,
    INSULIN = ml$INSULIN,
    HOMA_IR = round(pmax(0, ml$GLUC * ml$INSULIN / 135), 2),
    CHOL = ml$CHOL,
    LDL = ml$LDL,
    HDL = ml$HDL,
    TRIG = ml$TRIG,
    HSCRP = ml$HSCRP,
    stringsAsFactors = FALSE
  )
  write.csv(lb, file.path(output_dir, "lb.csv"), row.names = FALSE)

  # --- Adverse Events (AE) ---
  ae <- longitudinal$ae_long
  if (nrow(ae) > 0) {
    ae_out <- data.frame(
      SUBJID = ae$SUBJID,
      ARM = ae$ARM,
      AETERM = ae$AETERM,
      AEDECOD = ae$AETERM,  # Using term as preferred term
      AEBODSYS = ifelse(ae$AETERM %in% c("nausea", "diarrhoea", "vomiting", "constipation", "decreased_appetite"),
                        "Gastrointestinal disorders",
                        ifelse(ae$AETERM == "fatigue", "General disorders",
                               ifelse(ae$AETERM == "alopecia", "Skin and subcutaneous tissue disorders",
                                      ifelse(ae$AETERM == "headache", "Nervous system disorders", "Other")))),
      AESEV = ae$AESEV,
      AEREL = ae$AEREL,
      AESER = ae$AESER,
      AEOUT = ifelse(ae$AEENDTC_WEEK < 48, "Recovered", "Not Recovered"),
      AESTDTC_WEEK = ae$AESTDTC_WEEK,
      AEENDTC_WEEK = ae$AEENDTC_WEEK,
      stringsAsFactors = FALSE
    )
  } else {
    ae_out <- data.frame(
      SUBJID = character(), ARM = character(), AETERM = character(),
      AEDECOD = character(), AEBODSYS = character(), AESEV = character(),
      AEREL = character(), AESER = character(), AEOUT = character(),
      AESTDTC_WEEK = numeric(), AEENDTC_WEEK = numeric(),
      stringsAsFactors = FALSE
    )
  }
  write.csv(ae_out, file.path(output_dir, "ae.csv"), row.names = FALSE)

  # --- Drug Administration (EX) ---
  ex_records <- list()
  for (i in seq_len(nrow(baseline))) {
    arm_i <- baseline$ARM[i]
    sched <- params$dose_schedule[[arm_i]]  # will use global params
    disc_week <- longitudinal$disposition$TX_DISC_WEEK[i]
    if (is.na(disc_week)) disc_week <- 48

    # Generate dosing records per visit
    for (v in seq_along(VISIT_WEEKS)) {
      wk <- VISIT_WEEKS[v]
      if (wk == 0 || wk > disc_week || wk > 48) next
      dose <- get_effective_dose(arm_i, wk, params)
      ex_records[[length(ex_records) + 1]] <- data.frame(
        SUBJID = baseline$SUBJID[i],
        ARM = arm_i,
        VISIT_WEEK = wk,
        EXDOSE = dose,
        EXDOSU = "mg",
        EXROUTE = "Subcutaneous",
        stringsAsFactors = FALSE
      )
    }
  }
  ex <- do.call(rbind, ex_records)
  write.csv(ex, file.path(output_dir, "ex.csv"), row.names = FALSE)

  # --- Disposition (DS) ---
  ds <- longitudinal$disposition
  ds_out <- data.frame(
    SUBJID = ds$SUBJID,
    ARM = ds$ARM,
    TX_COMPLETED = !ds$TX_DISC,
    TX_DISC = ds$TX_DISC,
    TX_DISC_WEEK = ds$TX_DISC_WEEK,
    TX_DISC_REASON = ds$TX_DISC_REASON,
    STUDY_DISC = ds$STUDY_DISC,
    STUDY_DISC_WEEK = ds$STUDY_DISC_WEEK,
    stringsAsFactors = FALSE
  )
  write.csv(ds_out, file.path(output_dir, "ds.csv"), row.names = FALSE)

  # --- Outcomes / Efficacy (EF) ---
  ef <- outcomes[, c("SUBJID", "ARM", "WEIGHT_0", "WEIGHT_48", "PCT_CHANGE_48",
                     "ABS_CHANGE_48", "BMI_48", "RESP_5PCT", "RESP_10PCT",
                     "RESP_15PCT", "RESP_20PCT")]
  write.csv(ef, file.path(output_dir, "ef.csv"), row.names = FALSE)

  message("Source data emitted to: ", output_dir)
  invisible(list(dm = dm, vs = vs, lb = lb, ae = ae_out, ex = ex, ds = ds_out, ef = ef))
}
