#' =============================================================================
#' Domain: ML (Meal Data) — from meal_detail forms
#' =============================================================================

ML_COLUMNS <- c("STUDYID", "DOMAIN", "USUBJID", "MLSEQ", "MLTRT", "MLPRESP",
                "MLOCCUR", "VISITNUM", "VISIT", "MLSTDTC", "MLENDTC", "MLDY")

build_ml <- function(patient, cases) {
  usubjid <- usubjid_of(patient)
  ref <- patient$baseline_date
  rows <- list(); seq <- 0L
  for (e in iter_domain_records(cases, function(f) f == "meal_detail")) {
    rec <- e$rec
    sd <- parse_date(rec_get(rec, "Start Date"))
    ed <- parse_date(rec_get(rec, "End Date"))
    completed <- tolower(rec_get(rec, "Did the subject complete the meal?") %||% "")
    seq <- seq + 1L
    rows[[seq]] <- list(
      STUDYID = SIM_CONFIG$study_id, DOMAIN = "ML", USUBJID = usubjid,
      MLSEQ = seq, MLTRT = rec_get(rec, "Meal Type") %||% "", MLPRESP = "Y",
      MLOCCUR = if (completed == "yes") "Y" else if (completed == "no") "N" else "",
      VISITNUM = e$vnum, VISIT = e$vlabel,
      MLSTDTC = iso_dtc(sd, rec_get(rec, "Start Time")),
      MLENDTC = iso_dtc(ed, rec_get(rec, "End Time")), MLDY = study_day(sd, ref))
  }
  rows
}
