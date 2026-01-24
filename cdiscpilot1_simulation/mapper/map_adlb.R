#' =============================================================================
#' CDISC Pilot 01 Mapper - ADLB (Laboratory Analysis Dataset)
#' Xanomeline TTS in Alzheimer's Disease
#' =============================================================================

#' Create ADLB from LB domain
#' @param lb LB data frame
#' @param adsl ADSL data frame
#' @return ADLB data frame
map_adlb <- function(lb, adsl) {

  message("  Mapping ADLB...")

  # Merge with ADSL
  adsl_vars <- c("USUBJID", "TRT01P", "TRT01PN", "TRTSDT", "TRTEDT",
                 "AGE", "SEX", "SAFFL")

  adsl_subset <- adsl[, intersect(adsl_vars, names(adsl))]

  adlb <- merge(lb, adsl_subset, by = "USUBJID", all.x = TRUE)

  # Derive treatment variables
  adlb$TRTP <- adlb$TRT01P
  adlb$TRTPN <- adlb$TRT01PN

  # Derive PARAMCD and PARAM
  adlb$PARAMCD <- adlb$LBTESTCD
  adlb$PARAM <- paste(adlb$LBTEST, "(", adlb$LBSTRESU, ")")

  # Derive AVAL
  adlb$AVAL <- adlb$LBSTRESN

  # Derive analysis date
  adlb$ADT <- as.Date(adlb$LBDTC)
  if ("TRTSDT" %in% names(adlb)) {
    adlb$ADY <- as.integer(adlb$ADT - as.Date(adlb$TRTSDT)) + 1
    adlb$ADY[adlb$ADT < as.Date(adlb$TRTSDT)] <-
      as.integer(adlb$ADT[adlb$ADT < as.Date(adlb$TRTSDT)] - as.Date(adlb$TRTSDT[adlb$ADT < as.Date(adlb$TRTSDT)]))
  }

  # Derive analysis visit
  adlb$AVISIT <- adlb$VISIT
  adlb$AVISITN <- adlb$VISITNUM

  # Derive baseline flag
  adlb$ABLFL <- ifelse(adlb$LBBLFL == "Y", "Y", "")

  # Get baseline values for change from baseline
  baseline <- adlb[adlb$ABLFL == "Y", c("USUBJID", "PARAMCD", "AVAL")]
  names(baseline)[3] <- "BASE"

  adlb <- merge(adlb, baseline, by = c("USUBJID", "PARAMCD"), all.x = TRUE)

  # Calculate change from baseline
  adlb$CHG <- ifelse(!is.na(adlb$AVAL) & !is.na(adlb$BASE),
                     adlb$AVAL - adlb$BASE, NA)
  adlb$PCHG <- ifelse(!is.na(adlb$BASE) & adlb$BASE != 0,
                      (adlb$CHG / adlb$BASE) * 100, NA)

  # Derive analysis ranges
  adlb$A1LO <- adlb$LBSTNRLO
  adlb$A1HI <- adlb$LBSTNRHI

  # Derive ANRIND (analysis reference range indicator)
  adlb$ANRIND <- adlb$LBNRIND

  # Shift from baseline (baseline to post-baseline)
  adlb$BNRIND <- NA_character_
  bl_nrind <- adlb[adlb$ABLFL == "Y", c("USUBJID", "PARAMCD", "LBNRIND")]
  names(bl_nrind)[3] <- "BNRIND"
  adlb <- merge(adlb[, setdiff(names(adlb), "BNRIND")], bl_nrind,
                by = c("USUBJID", "PARAMCD"), all.x = TRUE)

  # Shift analysis
  adlb$SHIFT1 <- paste(adlb$BNRIND, "->", adlb$ANRIND)
  adlb$SHIFT1[is.na(adlb$BNRIND) | is.na(adlb$ANRIND)] <- NA

  # Analysis flags
  adlb$ANL01FL <- "Y"

  # Add STUDYID
  adlb$STUDYID <- "CDISCPILOT01"

  # Select and order columns
  col_order <- c("STUDYID", "USUBJID", "TRTP", "TRTPN",
                 "PARAMCD", "PARAM", "AVAL", "BASE", "CHG", "PCHG",
                 "A1LO", "A1HI", "ANRIND", "BNRIND", "SHIFT1",
                 "ADT", "ADY", "AVISIT", "AVISITN",
                 "ABLFL", "ANL01FL", "SAFFL")

  adlb <- adlb[, intersect(col_order, names(adlb))]

  message(sprintf("    ADLB: %d records", nrow(adlb)))
  message(sprintf("    Parameters: %d", length(unique(adlb$PARAMCD))))
  message(sprintf("    Subjects: %d", length(unique(adlb$USUBJID))))

  adlb
}
