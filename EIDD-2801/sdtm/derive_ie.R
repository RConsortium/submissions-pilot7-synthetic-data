#' derive_ie.R — IE (Inclusion/Exclusion Criteria Not Met).
#' Only criteria explicitly flagged as not met are recorded (eligible subjects
#' produce no IE rows), matching SDTMIG IE semantics.

IE_COLS <- c("STUDYID","DOMAIN","USUBJID","IESEQ","IETESTCD","IETEST","IECAT",
             "IEORRES","VISITNUM","VISIT","IEDTC")

derive_ie <- function() {
  raw <- read_form("inclusion_exclusion_criteria") |>
    filter(tolower(`Did the subject meet all eligibility criteria?`) == "no",
           `Inclusion/Exclusion Criterion` != "")

  if (nrow(raw) == 0) {
    return(finalize(raw[FALSE, , drop = FALSE], IE_COLS))
  }

  raw |>
    separate_rows(`Inclusion/Exclusion Criterion`, sep = "\\|") |>
    mutate(.crit = trimws(`Inclusion/Exclusion Criterion`)) |>
    filter(.crit != "") |>
    mutate(
      STUDYID  = STUDYID, DOMAIN = "IE",
      IETESTCD = toupper(.crit), IETEST = toupper(.crit),
      IECAT    = ifelse(startsWith(toupper(.crit), "EXCL"), "EXCLUSION", "INCLUSION"),
      IEORRES  = "NOT MET", IEDTC = ""
    ) |>
    arrange(USUBJID) |>
    add_seq("IESEQ") |>
    finalize(IE_COLS)
}
