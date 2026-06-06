#' =============================================================================
#' Domain: EX (Exposure) — from study-drug administration forms
#' =============================================================================

EX_COLUMNS <- c("STUDYID", "DOMAIN", "USUBJID", "EXSEQ", "EXTRT", "EXOCCUR",
                "EXDOSE", "EXDOSU", "EXDOSFRM", "EXROUTE", "VISITNUM", "VISIT",
                "EXSTDTC", "EXENDTC", "EXSTDY")

.DOSU_MAP <- c("milligram" = "mg", "milliliter" = "mL")

build_ex <- function(patient, cases) {
  usubjid <- usubjid_of(patient)
  ref <- patient$baseline_date
  rows <- list(); seq <- 0L
  for (e in iter_domain_records(cases, function(f) grepl("study_drug", f))) {
    rec <- e$rec
    taken <- tolower(rec_get(rec, "Study Drug taken?") %||% "yes") != "no"
    d <- parse_date(rec_get(rec, "Date"))
    dtc <- iso_dtc(d, rec_get(rec, "Time"))
    dose <- real_value(rec_get(rec, "Dose"))
    dosu_raw <- tolower(rec_get(rec, "Dose units") %||% "")
    dosu <- if (dosu_raw %in% names(.DOSU_MAP)) .DOSU_MAP[[dosu_raw]] else (rec_get(rec, "Dose units") %||% "")
    seq <- seq + 1L
    rows[[seq]] <- list(
      STUDYID = SIM_CONFIG$study_id, DOMAIN = "EX", USUBJID = usubjid,
      EXSEQ = seq, EXTRT = SIM_CONFIG$drug_trt,
      EXOCCUR = if (taken) "Y" else "N",
      EXDOSE = dose %||% "", EXDOSU = if (taken) dosu else "",
      EXDOSFRM = if (taken) (rec_get(rec, "Formulation") %||% "") else "",
      EXROUTE = if (taken) "ORAL" else "",
      VISITNUM = e$vnum, VISIT = e$vlabel, EXSTDTC = dtc, EXENDTC = dtc,
      EXSTDY = study_day(d, ref))
  }
  rows
}
