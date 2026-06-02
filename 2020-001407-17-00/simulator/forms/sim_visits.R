#' =============================================================================
#' Domain: SV (Subject Visits) — from date_of_visit forms
#' =============================================================================

SV_COLUMNS <- c("STUDYID", "DOMAIN", "USUBJID", "SVSEQ", "VISITNUM", "VISIT",
                "SVSTDTC", "SVDY")

build_sv <- function(patient, cases) {
  usubjid <- usubjid_of(patient)
  ref <- patient$baseline_date
  rows <- list(); seq <- 0L
  for (e in iter_domain_records(cases, function(f) f == "date_of_visit")) {
    d <- parse_date(rec_get(e$rec, "Visit Date"))
    if (is.null(d)) next
    seq <- seq + 1L
    rows[[seq]] <- list(
      STUDYID = SIM_CONFIG$study_id, DOMAIN = "SV", USUBJID = usubjid,
      SVSEQ = seq, VISITNUM = e$vnum, VISIT = e$vlabel,
      SVSTDTC = format(d, "%Y-%m-%d"), SVDY = study_day(d, ref))
  }
  rows
}
