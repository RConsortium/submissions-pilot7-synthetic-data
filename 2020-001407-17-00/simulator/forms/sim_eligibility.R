#' =============================================================================
#' Domain: IE (Inclusion/Exclusion Criteria Not Met)
#' =============================================================================
#' Only criteria explicitly flagged as not met are recorded (eligible subjects
#' produce no IE rows), matching SDTMIG IE semantics.
#' =============================================================================

IE_COLUMNS <- c("STUDYID", "DOMAIN", "USUBJID", "IESEQ", "IETESTCD", "IETEST",
                "IECAT", "IEORRES", "VISITNUM", "VISIT", "IEDTC")

build_ie <- function(patient, cases) {
  usubjid <- usubjid_of(patient)
  rows <- list(); seq <- 0L
  for (e in iter_domain_records(cases, function(f) f == "inclusion_exclusion_criteria")) {
    rec <- e$rec
    if (tolower(rec_get(rec, "Did the subject meet all eligibility criteria?") %||% "") != "no")
      next
    crits <- rec[["Inclusion/Exclusion Criterion"]]
    if (is.null(crits)) next
    items <- if (length(crits) > 1) crits else trimws(strsplit(as.character(crits), ",")[[1]])
    for (crit in items) {
      if (is_blank(crit)) next
      cat <- if (startsWith(toupper(crit), "EXCL")) "EXCLUSION" else "INCLUSION"
      seq <- seq + 1L
      rows[[seq]] <- list(
        STUDYID = SIM_CONFIG$study_id, DOMAIN = "IE", USUBJID = usubjid,
        IESEQ = seq, IETESTCD = toupper(crit), IETEST = toupper(crit),
        IECAT = cat, IEORRES = "NOT MET", VISITNUM = e$vnum, VISIT = e$vlabel,
        IEDTC = "")
    }
  }
  rows
}
