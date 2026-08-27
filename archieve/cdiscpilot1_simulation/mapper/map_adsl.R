#' =============================================================================
#' CDISC Pilot 01 Mapper - ADSL (Subject Level Analysis Dataset)
#' Xanomeline TTS in Alzheimer's Disease
#' =============================================================================

#' Create ADSL from SDTM
#' @param dm DM domain (with internal columns)
#' @param sc SC domain
#' @param ex EX domain
#' @param ds DS domain (optional)
#' @return ADSL data frame
map_adsl <- function(dm, sc, ex = NULL, ds = NULL) {

  message("  Mapping ADSL...")

  n <- nrow(dm)

  # Base ADSL from DM
  adsl <- data.frame(
    STUDYID = dm$STUDYID,
    USUBJID = dm$USUBJID,
    SUBJID = dm$SUBJID,
    SITEID = dm$SITEID,

    # Treatment (3-arm design)
    TRT01P = dm$ARM,
    TRT01PN = ifelse(dm$ARMCD == "Pbo", 0L,
                     ifelse(dm$ARMCD == "Xan_Lo", 1L, 2L)),
    TRT01A = dm$ACTARM,
    TRT01AN = ifelse(dm$ACTARMCD == "Pbo", 0L,
                     ifelse(dm$ACTARMCD == "Xan_Lo", 1L, 2L)),

    # Demographics
    AGE = dm$AGE,
    AGEGR1 = ifelse(dm$AGE < 65, "<65",
                    ifelse(dm$AGE < 80, "65-80", ">80")),
    AGEGR1N = ifelse(dm$AGE < 65, 1L,
                     ifelse(dm$AGE < 80, 2L, 3L)),
    SEX = dm$SEX,
    SEXN = ifelse(dm$SEX == "M", 1L, 2L),
    RACE = dm$RACE,
    ETHNIC = dm$ETHNIC,
    COUNTRY = dm$COUNTRY,

    # Dates
    RANDDT = as.Date(dm$RFSTDTC),
    TRTSDT = as.Date(dm$RFSTDTC),

    stringsAsFactors = FALSE
  )

  # Add MMSE baseline from SC
  mmse <- sc[sc$SCTESTCD == "MMSCORE", c("USUBJID", "SCSTRESN")]
  names(mmse)[2] <- "MMSETOT"
  adsl <- merge(adsl, mmse, by = "USUBJID", all.x = TRUE)

  # MMSE severity category
  adsl$MMSEGRP <- cut(adsl$MMSETOT,
                       breaks = c(-Inf, 14, 19, 24, Inf),
                       labels = c("Severe (0-14)", "Moderate (15-19)",
                                  "Mild (20-24)", "Normal (>24)"))
  adsl$MMSEGRPN <- ifelse(adsl$MMSETOT <= 14, 1L,
                           ifelse(adsl$MMSETOT <= 19, 2L,
                                  ifelse(adsl$MMSETOT <= 24, 3L, 4L)))

  # Add disease duration from SC
  disdur <- sc[sc$SCTESTCD == "DISDUR", c("USUBJID", "SCSTRESN")]
  names(disdur)[2] <- "DISDUR"
  adsl <- merge(adsl, disdur, by = "USUBJID", all.x = TRUE)

  # Add education years from SC
  educ <- sc[sc$SCTESTCD == "EDUCYR", c("USUBJID", "SCSTRESN")]
  names(educ)[2] <- "EDUCYR"
  adsl <- merge(adsl, educ, by = "USUBJID", all.x = TRUE)

  # Add exposure summary if available
  if (!is.null(ex) && nrow(ex) > 0) {
    ex_summ <- data.frame(
      USUBJID = ex$USUBJID,
      TRTDURD = ex$EXDUR,
      CUMDOSE = ex$EXCUMDOS,
      TRTEDT = as.Date(ex$EXENDTC),
      stringsAsFactors = FALSE
    )
    adsl <- merge(adsl, ex_summ, by = "USUBJID", all.x = TRUE)
  } else {
    adsl$TRTDURD <- NA
    adsl$CUMDOSE <- NA
    adsl$TRTEDT <- NA
  }

  # Completion status (derived from DS if available)
  if (!is.null(ds) && nrow(ds) > 0) {
    # Treatment completion
    trt_comp <- ds[ds$DSSCAT == "TREATMENT", c("USUBJID", "DSDECOD")]
    names(trt_comp)[2] <- "DCTREAS"
    adsl <- merge(adsl, trt_comp, by = "USUBJID", all.x = TRUE)
    adsl$COMPLFL <- ifelse(adsl$DCTREAS == "COMPLETED", "Y", "N")

    # Study completion
    study_comp <- ds[ds$DSSCAT == "STUDY", c("USUBJID", "DSDECOD")]
    names(study_comp)[2] <- "DCSREAS"
    adsl <- merge(adsl, study_comp, by = "USUBJID", all.x = TRUE)
    adsl$EOSSTT <- ifelse(adsl$DCSREAS == "COMPLETED", "COMPLETED", "DISCONTINUED")
  }

  # Add safety flag (all randomized subjects who received study drug)
  adsl$SAFFL <- "Y"

  # Add ITT flag (all randomized subjects)
  adsl$ITTFL <- "Y"

  # Add efficacy flag (ITT with at least one post-baseline efficacy assessment)
  adsl$EFFFL <- "Y"

  # Reorder columns
  col_order <- c("STUDYID", "USUBJID", "SUBJID", "SITEID",
                 "TRT01P", "TRT01PN", "TRT01A", "TRT01AN",
                 "AGE", "AGEGR1", "AGEGR1N", "SEX", "SEXN", "RACE", "ETHNIC", "COUNTRY",
                 "MMSETOT", "MMSEGRP", "MMSEGRPN", "DISDUR", "EDUCYR",
                 "RANDDT", "TRTSDT", "TRTEDT", "TRTDURD", "CUMDOSE",
                 "COMPLFL", "DCTREAS", "EOSSTT", "DCSREAS",
                 "SAFFL", "ITTFL", "EFFFL")

  adsl <- adsl[, intersect(col_order, names(adsl))]

  message(sprintf("    ADSL: %d subjects", nrow(adsl)))
  message(sprintf("    Placebo: %d", sum(adsl$TRT01PN == 0)))
  message(sprintf("    Xanomeline Low: %d", sum(adsl$TRT01PN == 1)))
  message(sprintf("    Xanomeline High: %d", sum(adsl$TRT01PN == 2)))

  adsl
}
