#' =============================================================================
#' CDISC Pilot 01 Mapper - ADAE (Adverse Events Analysis Dataset)
#' Xanomeline TTS in Alzheimer's Disease
#' =============================================================================

#' Create ADAE from AE domain
#' @param ae AE domain
#' @param adsl ADSL data frame
#' @return ADAE data frame
map_adae <- function(ae, adsl) {

  message("  Mapping ADAE...")

  if (nrow(ae) == 0) {
    message("    No AE records to map")
    return(data.frame())
  }

  # Merge with ADSL
  adsl_vars <- c("USUBJID", "TRT01P", "TRT01PN", "AGE", "SEX", "AGEGR1",
                 "MMSETOT", "TRTSDT", "TRTEDT", "SAFFL")

  adsl_subset <- adsl[, intersect(adsl_vars, names(adsl))]

  adae <- merge(ae, adsl_subset, by = "USUBJID", all.x = TRUE)

  # Derive treatment variables
  adae$TRTP <- adae$TRT01P
  adae$TRTPN <- adae$TRT01PN

  # Dates
  adae$ASTDT <- as.Date(adae$AESTDTC)
  adae$AENDT <- as.Date(adae$AEENDTC)
  adae$ASTDY <- adae$AESTDY
  adae$AENDY <- adae$AEENDY

  # Duration
  adae$ADURN <- ifelse(!is.na(adae$AENDY), adae$AENDY - adae$AESTDY + 1L, NA_integer_)
  adae$ADURU <- "DAY"

  # Toxicity grade numeric
  adae$ATOXGRN <- as.integer(adae$AETOXGR)

  # Treatment-emergent flag
  adae$TRTEMFL <- ifelse(adae$ASTDY >= 1, "Y", "N")

  # Occurrence flags (first occurrence per subject per PT)
  adae <- adae[order(adae$USUBJID, adae$AEDECOD, adae$ASTDY), ]
  adae$AOCCFL <- ave(seq_len(nrow(adae)),
                     paste(adae$USUBJID, adae$AEDECOD),
                     FUN = function(x) ifelse(seq_along(x) == 1, "Y", ""))
  adae$AOCCFL[adae$AOCCFL == ""] <- NA_character_

  # First occurrence per SOC
  adae$AOCC01FL <- ave(seq_len(nrow(adae)),
                       paste(adae$USUBJID, adae$AEBODSYS),
                       FUN = function(x) ifelse(seq_along(x) == 1, "Y", ""))
  adae$AOCC01FL[adae$AOCC01FL == ""] <- NA_character_

  # Serious flag occurrence
  adae$AOCCPFL <- NA_character_
  adae$AOCCPFL[adae$AESER == "Y" & !duplicated(paste(adae$USUBJID, adae$AEDECOD, adae$AESER))] <- "Y"

  # Custom query for application site AEs (key tolerability endpoint)
  adae$CQ01NAM <- ifelse(adae$AECAT == "APPLICATION SITE", "APPLICATION SITE REACTION", NA_character_)

  # Custom query for dermatological AEs
  adae$CQ02NAM <- ifelse(adae$AEBODSYS == "Skin and subcutaneous tissue disorders",
                          "DERMATOLOGICAL AE", NA_character_)

  # Relatedness
  adae$RELGR1 <- ifelse(adae$AEREL %in% c("RELATED", "POSSIBLY RELATED"), "Y", "N")

  # Relatedness numeric
  adae$RELGR1N <- ifelse(adae$RELGR1 == "Y", 1L, 0L)

  # Add STUDYID
  adae$STUDYID <- "CDISCPILOT01"

  # Reorder columns
  col_order <- c("STUDYID", "USUBJID", "AESEQ", "TRTP", "TRTPN",
                 "AETERM", "AEDECOD", "AEBODSYS", "AECAT",
                 "AESEV", "AETOXGR", "ATOXGRN", "AESER", "AEREL", "RELGR1", "RELGR1N",
                 "ASTDT", "AENDT", "ASTDY", "AENDY", "ADURN", "ADURU",
                 "TRTEMFL", "AOCCFL", "AOCC01FL", "AOCCPFL", "CQ01NAM", "CQ02NAM",
                 "AGE", "AGEGR1", "SEX", "MMSETOT", "SAFFL")

  adae <- adae[, intersect(col_order, names(adae))]

  message(sprintf("    ADAE: %d records", nrow(adae)))
  message(sprintf("    Subjects with AE: %d", length(unique(adae$USUBJID))))
  message(sprintf("    Application site AEs: %d", sum(!is.na(adae$CQ01NAM))))
  message(sprintf("    Serious AEs: %d", sum(adae$AESER == "Y", na.rm = TRUE)))

  adae
}
