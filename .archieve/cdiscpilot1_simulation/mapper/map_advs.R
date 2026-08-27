#' =============================================================================
#' CDISC Pilot 01 Mapper - ADVS (Vital Signs Analysis Dataset)
#' Xanomeline TTS in Alzheimer's Disease
#' =============================================================================

#' Create ADVS from VS domain
#' @param vs VS data frame
#' @param adsl ADSL data frame
#' @return ADVS data frame
map_advs <- function(vs, adsl) {

  message("  Mapping ADVS...")

  # Merge with ADSL
  adsl_vars <- c("USUBJID", "TRT01P", "TRT01PN", "TRTSDT", "TRTEDT",
                 "AGE", "SEX", "SAFFL")

  adsl_subset <- adsl[, intersect(adsl_vars, names(adsl))]

  advs <- merge(vs, adsl_subset, by = "USUBJID", all.x = TRUE)

  # Derive treatment variables
  advs$TRTP <- advs$TRT01P
  advs$TRTPN <- advs$TRT01PN

  # Derive PARAMCD and PARAM
  advs$PARAMCD <- advs$VSTESTCD
  advs$PARAM <- paste(advs$VSTEST, "(", advs$VSSTRESU, ")")

  # Derive AVAL
  advs$AVAL <- advs$VSSTRESN

  # Derive analysis date
  advs$ADT <- as.Date(advs$VSDTC)
  if ("TRTSDT" %in% names(advs)) {
    advs$ADY <- as.integer(advs$ADT - as.Date(advs$TRTSDT)) + 1
    advs$ADY[advs$ADT < as.Date(advs$TRTSDT)] <-
      as.integer(advs$ADT[advs$ADT < as.Date(advs$TRTSDT)] - as.Date(advs$TRTSDT[advs$ADT < as.Date(advs$TRTSDT)]))
  }

  # Derive analysis visit
  advs$AVISIT <- advs$VISIT
  advs$AVISITN <- advs$VISITNUM

  # Derive baseline flag
  advs$ABLFL <- ifelse(advs$VSBLFL == "Y", "Y", "")

  # Get baseline values for change from baseline
  baseline <- advs[advs$ABLFL == "Y", c("USUBJID", "PARAMCD", "AVAL")]
  names(baseline)[3] <- "BASE"

  advs <- merge(advs, baseline, by = c("USUBJID", "PARAMCD"), all.x = TRUE)

  # Calculate change from baseline
  advs$CHG <- ifelse(!is.na(advs$AVAL) & !is.na(advs$BASE),
                     advs$AVAL - advs$BASE, NA)
  advs$PCHG <- ifelse(!is.na(advs$BASE) & advs$BASE != 0,
                      (advs$CHG / advs$BASE) * 100, NA)

  # Clinically significant flags for vital signs
  # Pulse rate
  advs$AVALCAT1 <- NA_character_
  pulse_idx <- advs$PARAMCD == "PULSE"
  advs$AVALCAT1[pulse_idx & advs$AVAL < 50] <- "Bradycardia (<50)"
  advs$AVALCAT1[pulse_idx & advs$AVAL >= 50 & advs$AVAL <= 100] <- "Normal (50-100)"
  advs$AVALCAT1[pulse_idx & advs$AVAL > 100] <- "Tachycardia (>100)"

  # Systolic BP
  sbp_idx <- advs$PARAMCD == "SYSBP"
  advs$AVALCAT1[sbp_idx & advs$AVAL < 90] <- "Hypotension (<90)"
  advs$AVALCAT1[sbp_idx & advs$AVAL >= 90 & advs$AVAL <= 140] <- "Normal (90-140)"
  advs$AVALCAT1[sbp_idx & advs$AVAL > 140] <- "Hypertension (>140)"

  # Derive BMI if height and weight available (one BMI per subject per visit)
  ht <- advs[advs$PARAMCD == "HEIGHT", c("USUBJID", "AVISITN", "AVAL")]
  names(ht)[3] <- "HEIGHT_CM"
  wt <- advs[advs$PARAMCD == "WEIGHT", c("USUBJID", "AVISITN", "AVAL")]
  names(wt)[3] <- "WEIGHT_KG"

  bmi_data <- merge(ht, wt, by = c("USUBJID", "AVISITN"))
  if (nrow(bmi_data) > 0) {
    bmi_data$BMI <- bmi_data$WEIGHT_KG / (bmi_data$HEIGHT_CM / 100)^2

    # Create BMI records
    bmi_records <- data.frame(
      STUDYID = "CDISCPILOT01",
      USUBJID = bmi_data$USUBJID,
      PARAMCD = "BMI",
      PARAM = "Body Mass Index (kg/m2)",
      AVAL = round(bmi_data$BMI, 1),
      AVISITN = bmi_data$AVISITN,
      stringsAsFactors = FALSE
    )

    # Get additional variables from first record of each subject-visit
    for (i in 1:nrow(bmi_records)) {
      subj_visit <- advs[advs$USUBJID == bmi_records$USUBJID[i] &
                           advs$AVISITN == bmi_records$AVISITN[i], ][1, ]
      bmi_records$TRTP[i] <- subj_visit$TRTP
      bmi_records$TRTPN[i] <- subj_visit$TRTPN
      bmi_records$ADT[i] <- as.character(subj_visit$ADT)
      bmi_records$ADY[i] <- subj_visit$ADY
      bmi_records$AVISIT[i] <- subj_visit$AVISIT
      bmi_records$SAFFL[i] <- subj_visit$SAFFL
    }

    bmi_records$ADT <- as.Date(bmi_records$ADT)
    bmi_records$ABLFL <- ifelse(bmi_records$AVISITN == 1, "Y", "")

    # Get BMI baseline
    bmi_baseline <- bmi_records[bmi_records$ABLFL == "Y", c("USUBJID", "AVAL")]
    names(bmi_baseline)[2] <- "BASE"
    bmi_records <- merge(bmi_records, bmi_baseline, by = "USUBJID", all.x = TRUE)
    bmi_records$CHG <- bmi_records$AVAL - bmi_records$BASE
    bmi_records$PCHG <- (bmi_records$CHG / bmi_records$BASE) * 100

    bmi_records$ANL01FL <- "Y"

    # Add to main dataset
    common_cols <- intersect(names(advs), names(bmi_records))
    advs <- rbind(advs[, common_cols], bmi_records[, common_cols])
  }

  # Analysis flags
  advs$ANL01FL <- "Y"

  # Add STUDYID
  advs$STUDYID <- "CDISCPILOT01"

  # Select and order columns
  col_order <- c("STUDYID", "USUBJID", "TRTP", "TRTPN",
                 "PARAMCD", "PARAM", "AVAL", "BASE", "CHG", "PCHG", "AVALCAT1",
                 "ADT", "ADY", "AVISIT", "AVISITN",
                 "ABLFL", "ANL01FL", "SAFFL")

  advs <- advs[, intersect(col_order, names(advs))]

  message(sprintf("    ADVS: %d records", nrow(advs)))
  message(sprintf("    Parameters: %d", length(unique(advs$PARAMCD))))
  message(sprintf("    Subjects: %d", length(unique(advs$USUBJID))))

  advs
}
