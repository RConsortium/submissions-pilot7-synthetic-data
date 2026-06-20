# adam.R — ADaM derivations (ADSL, ADAE, ADTTE)
# KEYNOTE-564 IPD Causal-DAG Simulator

source("R/dag_state.R")

#' Build ADaM datasets from source and SDTM
#' @param source_dir character, path to source CSVs
#' @param sdtm_dir character, path to SDTM CSVs
#' @param output_dir character, path for ADaM output
#' @return list of ADaM data.tables
build_adam <- function(source_dir = "output/source",
                       sdtm_dir = "output/sdtm",
                       output_dir = "output/adam") {

  dir.create(output_dir, recursive = TRUE, showWarnings = FALSE)

  # Read source data
  dm_src <- fread(file.path(source_dir, "DM.csv"))
  ae_src <- fread(file.path(source_dir, "AE.csv"))
  ex_src <- fread(file.path(source_dir, "EX.csv"))
  ds_src <- fread(file.path(source_dir, "DS.csv"))

  # Need endpoints for ADTTE — read from combined output if available
  # Otherwise derive from source

  # ─── ADSL (Subject-Level Analysis Dataset) ──────────────────────────────
  adsl <- build_adsl(dm_src, ex_src, ds_src)
  fwrite(adsl, file.path(output_dir, "ADSL.csv"))

  # ─── ADAE (Adverse Event Analysis Dataset) ──────────────────────────────
  adae <- build_adae(ae_src, adsl)
  fwrite(adae, file.path(output_dir, "ADAE.csv"))

  # ─── ADTTE (Time-to-Event Analysis Dataset) ─────────────────────────────
  adtte <- build_adtte(adsl)
  fwrite(adtte, file.path(output_dir, "ADTTE.csv"))

  message(sprintf("[adam] Written 3 ADaM datasets to %s", output_dir))
  invisible(list(adsl = adsl, adae = adae, adtte = adtte))
}

#' Build ADSL
build_adsl <- function(dm_src, ex_src, ds_src) {

  # Treatment duration
  treat_summary <- ex_src[, .(
    TRTDUR = max(VISIT_DAY) - min(VISIT_DAY) + 1L,
    NDOSES = sum(EXDOSE > 0),
    TRTEDT_DY = max(VISIT_DAY)
  ), by = SUBJID]

  adsl <- merge(dm_src, treat_summary, by = "SUBJID", all.x = TRUE)
  adsl <- merge(adsl, ds_src[, .(SUBJID, DSDECOD)], by = "SUBJID", all.x = TRUE)

  # Standard ADaM variables
  adsl[, `:=`(
    STUDYID  = "KN564",
    USUBJID  = SUBJID,
    TRT01P   = ARM,
    TRT01A   = ARM,
    TRT01PN  = fifelse(ARM == "PEMBROLIZUMAB", 1L, 2L),
    AGEGR1   = fcase(
      AGE < 50, "<50",
      AGE < 65, "50-<65",
      default = ">=65"
    ),
    AGEGR1N  = fcase(
      AGE < 50, 1L,
      AGE < 65, 2L,
      default = 3L
    ),
    SAFFL    = "Y",  # All randomized patients in safety population
    ITTFL    = "Y",  # All randomized in ITT
    RANDFL   = "Y",
    EOSSTT   = fifelse(DSDECOD == "COMPLETED", "COMPLETED", "DISCONTINUED"),
    DCSREAS  = fifelse(DSDECOD == "COMPLETED", NA_character_, DSDECOD)
  )]

  # Select ADaM columns
  adam_cols <- c("STUDYID", "USUBJID", "SUBJID", "AGE", "AGEGR1", "AGEGR1N",
                "SEX", "RACE", "REGION", "TRT01P", "TRT01A", "TRT01PN",
                "RISK_CATEGORY", "ECOG_BL", "SARCOMATOID", "PDL1_CPS",
                "STRATUM", "SAFFL", "ITTFL", "RANDFL",
                "TRTDUR", "NDOSES", "EOSSTT", "DCSREAS")
  existing_cols <- intersect(adam_cols, names(adsl))
  adsl[, ..existing_cols]
}

#' Build ADAE
build_adae <- function(ae_src, adsl) {
  if (nrow(ae_src) == 0) return(data.table())

  adae <- copy(ae_src)

  # Merge subject-level info
  adae <- merge(adae, adsl[, .(SUBJID = USUBJID, TRT01A = TRT01P, SAFFL)],
                by = "SUBJID", all.x = TRUE)

  adae[, `:=`(
    STUDYID  = "KN564",
    USUBJID  = SUBJID,
    ASTDY    = AESTDT,
    AENDY    = AEENDT,
    ATOXGR   = as.character(AEGR),
    AESEVN   = AEGR,
    AREL     = AEREL,
    TRTEMFL  = "Y",  # All AEs are treatment-emergent in this simulation
    CQ01NAM  = fifelse(AECAT %in% c("IMMUNE_MEDIATED", "THYROID"),
                       "IMMUNE-MEDIATED AES", NA_character_)
  )]

  adae[, .(STUDYID, USUBJID, AETERM, ASTDY, AENDY, ATOXGR, AESEVN,
           AESER, AREL, AEACN, AECAT, AEOUT, TRTEMFL, CQ01NAM, TRT01A)]
}

#' Build ADTTE (one record per parameter per subject)
build_adtte <- function(adsl) {
  # We need the endpoints data — reconstruct from ADSL + available info
  # In practice, this would merge with the endpoints table from outcomes.R
  # For now, create the structure that would be populated

  # Read endpoints if available
  endpoints_path <- "output/source/endpoints.csv"
  if (file.exists(endpoints_path)) {
    endpoints <- fread(endpoints_path)
  } else {
    # Create stub — will be populated when run.R writes endpoints
    message("[adam] Endpoints file not found; ADTTE will be built from endpoints in run.R")
    return(data.table())
  }

  # DFS parameter
  dfs_records <- data.table(
    STUDYID  = "KN564",
    USUBJID  = endpoints$SUBJID,
    PARAMCD  = "DFS",
    PARAM    = "Disease-Free Survival",
    AVAL     = endpoints$DFS_DAY,
    CNSR     = 1L - endpoints$DFS_EVENT,
    EVNTDESC = endpoints$DFS_EVENT_TYPE,
    STARTDT  = 1L
  )

  # OS parameter
  os_records <- data.table(
    STUDYID  = "KN564",
    USUBJID  = endpoints$SUBJID,
    PARAMCD  = "OS",
    PARAM    = "Overall Survival",
    AVAL     = endpoints$OS_DAY,
    CNSR     = 1L - endpoints$OS_EVENT,
    EVNTDESC = fifelse(endpoints$OS_EVENT == 1L, "DEATH", "CENSORED"),
    STARTDT  = 1L
  )

  adtte <- rbindlist(list(dfs_records, os_records))

  # Merge treatment info
  adtte <- merge(adtte,
                 adsl[, .(USUBJID, TRT01P, TRT01PN, RISK_CATEGORY, ECOG_BL)],
                 by = "USUBJID", all.x = TRUE)

  adtte
}
