#' =============================================================================
#' Domain: VS (Vital Signs) — from vital_sign / vital_signs forms
#' =============================================================================

VS_COLUMNS <- c("STUDYID", "DOMAIN", "USUBJID", "VSSEQ", "VSTESTCD", "VSTEST",
                "VSPOS", "VSORRES", "VSORRESU", "VSSTRESN", "VSSTRESU", "VSLOC",
                "VISITNUM", "VISIT", "VSTPT", "VSDTC", "VSDY")

# field name (lower) -> list(TESTCD, TEST, default unit)
.VS_MAP <- list(
  "systolic blood pressure"  = list("SYSBP", "Systolic Blood Pressure", "mmHg"),
  "diastolic blood pressure" = list("DIABP", "Diastolic Blood Pressure", "mmHg"),
  "pulse rate"               = list("PULSE", "Pulse Rate", "beats/min"),
  "respiratory rate"         = list("RESP", "Respiratory Rate", "breaths/min"),
  "temperature"              = list("TEMP", "Temperature", NA_character_)
)
.TEMP_UNIT <- c("degree celsius" = "C", "degree fahrenheit" = "F")

build_vs <- function(patient, cases) {
  usubjid <- usubjid_of(patient)
  ref <- patient$baseline_date
  rows <- list(); seq <- 0L
  for (e in iter_domain_records(cases, function(f) grepl("vital_sign", f))) {
    rec <- e$rec
    d <- parse_date(rec_get(rec, "Date of Assessment"))
    dtc <- iso_dtc(d, rec_get(rec, "Time of Assessment"))
    loc <- rec_get(rec, "Temperature location") %||% ""
    tunit_raw <- tolower(rec_get(rec, "Temperature Unit") %||% "")
    tunit <- if (tunit_raw %in% names(.TEMP_UNIT)) .TEMP_UNIT[[tunit_raw]] else ""
    for (fn in names(.VS_MAP)) {
      m <- .VS_MAP[[fn]]
      val <- real_value(rec_get(rec, fn))
      if (is.null(val)) next
      u <- if (m[[1]] == "TEMP") tunit else m[[3]]
      num <- as_number(val)
      seq <- seq + 1L
      rows[[seq]] <- list(
        STUDYID = SIM_CONFIG$study_id, DOMAIN = "VS", USUBJID = usubjid,
        VSSEQ = seq, VSTESTCD = m[[1]], VSTEST = m[[2]], VSPOS = "SUPINE",
        VSORRES = val, VSORRESU = u %||% "",
        VSSTRESN = num %||% "", VSSTRESU = u %||% "",
        VSLOC = if (m[[1]] == "TEMP") loc else "",
        VISITNUM = e$vnum, VISIT = e$vlabel, VSTPT = "", VSDTC = dtc,
        VSDY = study_day(d, ref))
    }
  }
  rows
}
