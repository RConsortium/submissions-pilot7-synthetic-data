#' =============================================================================
#' CDISC Pilot 01 Mapper - ADQS (Questionnaire Analysis Dataset)
#' Cognitive Efficacy Analysis (ADAS-Cog, CIBIC+)
#' =============================================================================

#' Create ADQS from QS domain
#' @param qs QS data frame
#' @param adsl ADSL data frame
#' @param efficacy_summary Efficacy summary from simulator (optional, for LOCF)
#' @return ADQS data frame
map_adqs <- function(qs, adsl, efficacy_summary = NULL) {

  message("  Mapping ADQS...")

  if (nrow(qs) == 0) {
    message("    No QS records to map")
    return(data.frame())
  }

  # Merge with ADSL
  adsl_vars <- c("USUBJID", "TRT01P", "TRT01PN", "TRTSDT",
                 "AGE", "AGEGR1", "SEX", "MMSETOT", "MMSEGRP",
                 "COMPLFL", "SAFFL", "ITTFL", "EFFFL")

  adsl_subset <- adsl[, intersect(adsl_vars, names(adsl))]

  adqs <- merge(qs, adsl_subset, by = "USUBJID", all.x = TRUE)

  # Derive treatment variables
  adqs$TRTP <- adqs$TRT01P
  adqs$TRTPN <- adqs$TRT01PN

  # Derive PARAMCD and PARAM
  # ADAS-Cog 11 total score
  adqs$PARAMCD <- ifelse(adqs$QSTESTCD == "ACTOT", "ACTOT11",
                          ifelse(adqs$QSTESTCD == "CIBIC", "CIBIC", adqs$QSTESTCD))
  adqs$PARAM <- ifelse(adqs$QSTESTCD == "ACTOT", "ADAS-Cog (11) Total Score",
                        ifelse(adqs$QSTESTCD == "CIBIC", "CIBIC+ Global Impression of Change",
                               adqs$QSTEST))

  # Derive AVAL
  adqs$AVAL <- adqs$QSSTRESN

  # Derive analysis visit variables
  adqs$AVISIT <- adqs$VISIT
  adqs$AVISITN <- adqs$VISITNUM

  # Derive analysis date
  adqs$ADT <- as.Date(adqs$QSDTC)
  if ("TRTSDT" %in% names(adqs)) {
    adqs$ADY <- as.integer(adqs$ADT - as.Date(adqs$TRTSDT)) + 1
    adqs$ADY[adqs$ADT < as.Date(adqs$TRTSDT)] <-
      as.integer(adqs$ADT[adqs$ADT < as.Date(adqs$TRTSDT)] - as.Date(adqs$TRTSDT[adqs$ADT < as.Date(adqs$TRTSDT)]))
  }

  # Derive baseline flag
  adqs$ABLFL <- ifelse(adqs$QSBLFL == "Y", "Y", "")

  # Get baseline values for change from baseline
  baseline <- adqs[adqs$ABLFL == "Y", c("USUBJID", "PARAMCD", "AVAL")]
  names(baseline)[3] <- "BASE"

  adqs <- merge(adqs, baseline, by = c("USUBJID", "PARAMCD"), all.x = TRUE)

  # Calculate change from baseline (for ADAS-Cog, positive change = worsening)
  adqs$CHG <- ifelse(!is.na(adqs$AVAL) & !is.na(adqs$BASE),
                     adqs$AVAL - adqs$BASE, NA)

  # CIBIC doesn't have change from baseline (it IS the change measure)
  # Set CHG to NA for CIBIC
  adqs$CHG[adqs$PARAMCD == "CIBIC"] <- NA

  # Analysis population flags
  adqs$ANL01FL <- "Y"

  # ITT LOCF analysis flag
  # Mark the last observation for LOCF analysis
  adqs <- adqs[order(adqs$USUBJID, adqs$PARAMCD, adqs$AVISITN), ]

  # Identify last observation per subject per parameter
  adqs$ANL02FL <- ""
  for (param in unique(adqs$PARAMCD)) {
    param_idx <- adqs$PARAMCD == param
    last_obs <- !duplicated(paste(adqs$USUBJID[param_idx], adqs$PARAMCD[param_idx]),
                             fromLast = TRUE)
    adqs$ANL02FL[param_idx][last_obs] <- "Y"
  }

  # Week 24 completer analysis flag
  adqs$ANL03FL <- ifelse(adqs$AVISIT == "WEEK 24" & !is.na(adqs$AVAL), "Y", "")

  # Create LOCF imputation for Week 24
  # Add endpoint visit for LOCF analysis
  adqs$DTYPE <- ""

  # For subjects without Week 24, create LOCF records
  w24_subjects <- unique(adqs$USUBJID[adqs$AVISIT == "WEEK 24" & !is.na(adqs$AVAL)])
  all_subjects <- unique(adqs$USUBJID)
  need_locf <- setdiff(all_subjects, w24_subjects)

  if (length(need_locf) > 0) {
    locf_records <- list()
    for (subj in need_locf) {
      for (param in c("ACTOT11")) {  # Only ADAS-Cog needs LOCF
        subj_data <- adqs[adqs$USUBJID == subj & adqs$PARAMCD == param & !is.na(adqs$AVAL), ]
        if (nrow(subj_data) > 0) {
          last_obs <- subj_data[nrow(subj_data), ]
          locf_rec <- last_obs
          locf_rec$AVISIT <- "WEEK 24"
          locf_rec$AVISITN <- 9  # Week 24 visit number
          locf_rec$DTYPE <- "LOCF"
          locf_rec$ANL01FL <- "Y"
          locf_rec$ANL02FL <- "Y"  # LOCF endpoint
          locf_rec$ANL03FL <- ""   # Not actual Week 24
          locf_records[[length(locf_records) + 1]] <- locf_rec
        }
      }
    }
    if (length(locf_records) > 0) {
      adqs <- rbind(adqs, do.call(rbind, locf_records))
    }
  }

  # For CIBIC, create endpoint record
  # CIBIC is only measured at Week 24, so those who dropped out won't have it
  # We can impute as "No Change" (4) or leave as missing

  # Add STUDYID
  adqs$STUDYID <- "CDISCPILOT01"

  # Categorize ADAS-Cog change (clinical interpretation)
  adqs$ACAT1 <- NA_character_
  adas_idx <- adqs$PARAMCD == "ACTOT11" & !is.na(adqs$CHG)
  adqs$ACAT1[adas_idx & adqs$CHG <= -4] <- "Marked Improvement"
  adqs$ACAT1[adas_idx & adqs$CHG > -4 & adqs$CHG < 0] <- "Improvement"
  adqs$ACAT1[adas_idx & adqs$CHG == 0] <- "No Change"
  adqs$ACAT1[adas_idx & adqs$CHG > 0 & adqs$CHG < 4] <- "Worsening"
  adqs$ACAT1[adas_idx & adqs$CHG >= 4] <- "Marked Worsening"

  # Categorize CIBIC
  cibic_idx <- adqs$PARAMCD == "CIBIC" & !is.na(adqs$AVAL)
  adqs$ACAT1[cibic_idx & adqs$AVAL <= 3] <- "Improved"
  adqs$ACAT1[cibic_idx & adqs$AVAL == 4] <- "No Change"
  adqs$ACAT1[cibic_idx & adqs$AVAL >= 5] <- "Worsened"

  # Select and order columns
  col_order <- c("STUDYID", "USUBJID", "TRTP", "TRTPN",
                 "PARAMCD", "PARAM", "AVAL", "BASE", "CHG", "ACAT1",
                 "ADT", "ADY", "AVISIT", "AVISITN",
                 "ABLFL", "DTYPE", "ANL01FL", "ANL02FL", "ANL03FL",
                 "AGE", "AGEGR1", "SEX", "MMSETOT", "MMSEGRP",
                 "COMPLFL", "SAFFL", "ITTFL", "EFFFL")

  adqs <- adqs[, intersect(col_order, names(adqs))]

  # Sort
  adqs <- adqs[order(adqs$USUBJID, adqs$PARAMCD, adqs$AVISITN), ]

  message(sprintf("    ADQS: %d records", nrow(adqs)))
  message(sprintf("    ADAS-Cog assessments: %d", sum(adqs$PARAMCD == "ACTOT11")))
  message(sprintf("    CIBIC+ assessments: %d", sum(adqs$PARAMCD == "CIBIC")))
  message(sprintf("    LOCF records: %d", sum(adqs$DTYPE == "LOCF", na.rm = TRUE)))

  adqs
}
