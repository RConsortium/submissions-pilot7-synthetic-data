# derive_ex.R — EX (Exposure): vitamin D3 4000 IU / placebo PO QD over the
# 21-day dosing period. One CRF row (and one SDTM record) per subject. Compliance
# percentage -> SUPPEX.

derive_ex <- function() {
  ex <- read_form("EX")
  ref <- ref_dates()

  out <- ex |>
    left_join(ref, by = "USUBJID") |>
    mutate(
      STUDYID  = STUDYID,
      DOMAIN   = "EX",
      EXDOSE   = ifelse(grepl("PLACEBO", EXTRT, ignore.case = TRUE), "0", EXDOSE),
      EXDOSFRQ = "QD",
      EPOCH    = "TREATMENT",
      EXSTDY   = study_day(EXSTDTC, RFSTDTC),
      EXENDY   = study_day(EXENDTC, RFSTDTC),
    ) |>
    arrange(USUBJID) |>
    add_seq("EXSEQ")

  finalize(out, c("STUDYID", "DOMAIN", "USUBJID", "EXSEQ", "EXTRT",
                  "EXDOSE", "EXDOSU", "EXDOSFRQ", "EXROUTE", "EPOCH",
                  "EXSTDTC", "EXENDTC", "EXSTDY", "EXENDY"))
}
