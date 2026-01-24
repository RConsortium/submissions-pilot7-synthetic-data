#' =============================================================================
#' KEYNOTE-868 Mapper - ADTTE (Time-to-Event Analysis Dataset)
#' =============================================================================

#' Create ADTTE from efficacy data
#' @param efficacy List with pfs, os data frames
#' @param adsl ADSL data frame
#' @return ADTTE data frame
map_adtte <- function(efficacy, adsl) {

  message("  Mapping ADTTE...")

  # Combine PFS and OS
  pfs <- efficacy$pfs
  os <- efficacy$os

  tte <- rbind(pfs, os)

  # Merge with ADSL
  adsl_vars <- c("USUBJID", "TRT01P", "TRT01PN", "AGE", "AGEGR1", "SEX",
                 "MMRSTAT", "ECOGBL", "TRTSDT", "SAFFL", "ITTFL", "EFFFL")

  adsl_subset <- adsl[, intersect(adsl_vars, names(adsl))]

adtte <- merge(tte, adsl_subset, by = "USUBJID", all.x = TRUE)

  # Derive additional variables
  adtte$TRTP <- adtte$TRT01P
  adtte$TRTPN <- adtte$TRT01PN
  adtte$STARTDT <- adtte$TRTSDT
  adtte$ADT <- adtte$TRTSDT + round(adtte$AVAL * 30.44)  # Convert months to days
  adtte$ADY <- as.integer(adtte$ADT - adtte$TRTSDT) + 1L

  # Analysis flags
  adtte$ANL01FL <- "Y"

  # Reorder columns
  col_order <- c("STUDYID", "USUBJID", "TRTP", "TRTPN",
                 "PARAMCD", "PARAM", "AVAL", "CNSR", "EVNTDESC",
                 "STARTDT", "ADT", "ADY",
                 "AGE", "AGEGR1", "SEX", "MMRSTAT", "ECOGBL",
                 "SAFFL", "ITTFL", "EFFFL", "ANL01FL")

  adtte$STUDYID <- "KN868"
  adtte <- adtte[, intersect(col_order, names(adtte))]

  message(sprintf("    ADTTE: %d records", nrow(adtte)))
  message(sprintf("    PFS events: %d", sum(adtte$PARAMCD == "PFS" & adtte$CNSR == 0)))
  message(sprintf("    OS events: %d", sum(adtte$PARAMCD == "OS" & adtte$CNSR == 0)))

  adtte
}
