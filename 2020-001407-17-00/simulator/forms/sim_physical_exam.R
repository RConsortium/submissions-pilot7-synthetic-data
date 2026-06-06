#' =============================================================================
#' Domain: PE (Physical Examination) — one row per body system examined
#' =============================================================================

PE_COLUMNS <- c("STUDYID", "DOMAIN", "USUBJID", "PESEQ", "PETESTCD", "PETEST",
                "PEORRES", "PESTAT", "PEREASND", "VISITNUM", "VISIT", "PEDTC",
                "PEDY")

.PE_SYS <- c(
  "general appearance" = "GENAPP", "heent" = "HEENT", "lymphatic" = "LYMPH",
  "cardiovascular" = "CARDIO", "respiratory" = "RESP", "gastrointestinal" = "GI",
  "musculoskeletal" = "MUSSKEL", "neurological" = "NEURO",
  "dermatological" = "DERM", "other" = "OTHER")

build_pe <- function(patient, cases) {
  usubjid <- usubjid_of(patient)
  ref <- patient$baseline_date
  rows <- list(); seq <- 0L
  add_row <- function(testcd, test, e, d, dtc, orres = "", stat = "", reasnd = "") {
    seq <<- seq + 1L
    rows[[seq]] <<- list(
      STUDYID = SIM_CONFIG$study_id, DOMAIN = "PE", USUBJID = usubjid,
      PESEQ = seq, PETESTCD = testcd, PETEST = test, PEORRES = orres,
      PESTAT = stat, PEREASND = reasnd, VISITNUM = e$vnum, VISIT = e$vlabel,
      PEDTC = dtc, PEDY = study_day(d, ref))
  }

  for (e in iter_domain_records(cases, function(f) grepl("physical_exam", f))) {
    rec <- e$rec
    performed <- tolower(rec_get(rec, "Was Physical Examination performed?",
                                 "Was the examination performed?") %||% "yes")
    d <- parse_date(rec_get(rec, "Date of examination"))
    dtc <- iso_dtc(d, rec_get(rec, "Time of examination"))
    if (performed == "no") {
      add_row("PEALL", "Physical Examination", e, d, dtc, stat = "NOT DONE",
              reasnd = rec_get(rec, "If No, Reason") %||% "")
      next
    }
    result <- rec_get(rec, "Examination Result") %||% ""
    systems <- rec[["Body System Examined"]]
    systems <- if (is.null(systems)) character(0) else as.character(systems)
    if (length(systems) == 0) {
      add_row("PEALL", "Physical Examination", e, d, dtc, orres = result)
      next
    }
    for (sysname in systems) {
      code <- .PE_SYS[tolower(trimws(sysname))]
      if (is.na(code)) code <- substr(gsub("[^A-Z0-9]", "", toupper(sysname)), 1, 8)
      add_row(unname(code), sysname, e, d, dtc, orres = result)
    }
  }
  rows
}
