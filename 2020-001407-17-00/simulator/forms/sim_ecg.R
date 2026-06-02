#' =============================================================================
#' Domain: EG (ECG Test Results) — from 12-lead / continuous ECG forms
#' =============================================================================
#' Interval fields recorded only as the unit token "ms" are suppressed
#' (real_value), so typically Heart Rate + Interpretation produce rows.
#' =============================================================================

EG_COLUMNS <- c("STUDYID", "DOMAIN", "USUBJID", "EGSEQ", "EGTESTCD", "EGTEST",
                "EGPOS", "EGORRES", "EGORRESU", "EGSTRESN", "EGSTRESU",
                "VISITNUM", "VISIT", "EGDTC", "EGDY")

.EG_MAP <- list(
  "heart rate"    = list("EGHR", "Heart Rate", "beats/min"),
  "pr interval"   = list("PR", "PR Interval", "ms"),
  "qrs duration"  = list("QRSDUR", "QRS Duration", "ms"),
  "qt interval"   = list("QT", "QT Interval", "ms"),
  "cf"            = list("QTCF", "QTcF Interval", "ms"),
  "rr interval"   = list("RR", "RR Interval", "ms")
)

build_eg <- function(patient, cases) {
  usubjid <- usubjid_of(patient)
  ref <- patient$baseline_date
  rows <- list(); seq <- 0L
  for (e in iter_domain_records(cases, function(f) grepl("ecg", f))) {
    rec <- e$rec
    if (tolower(rec_get(rec, "Was the ECG performed?") %||% "yes") == "no") next
    d <- parse_date(rec_get(rec, "Date of Assessment"))
    dtc <- iso_dtc(d, rec_get(rec, "Time of Assessment"))
    pos <- toupper(rec_get(rec, "Subject Position") %||% "")
    add_row <- function(testcd, test, orres, unit = "") {
      num <- as_number(orres)
      seq <<- seq + 1L
      rows[[seq]] <<- list(
        STUDYID = SIM_CONFIG$study_id, DOMAIN = "EG", USUBJID = usubjid,
        EGSEQ = seq, EGTESTCD = testcd, EGTEST = test, EGPOS = pos,
        EGORRES = orres, EGORRESU = unit, EGSTRESN = num %||% "",
        EGSTRESU = if (!is.null(num)) unit else "",
        VISITNUM = e$vnum, VISIT = e$vlabel, EGDTC = dtc,
        EGDY = study_day(d, ref))
    }
    for (fn in names(.EG_MAP)) {
      m <- .EG_MAP[[fn]]
      val <- real_value(rec_get(rec, fn))
      if (!is.null(val)) add_row(m[[1]], m[[2]], val, m[[3]])
    }
    interp <- real_value(rec_get(rec, "ECG Interpretation"))
    if (!is.null(interp)) add_row("INTP", "Interpretation", interp)
  }
  rows
}
