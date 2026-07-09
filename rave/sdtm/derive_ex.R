# derive_ex.R — EX (Exposure). Combines the randomized study drug (rituximab /
# cyclophosphamide / azathioprine and their double-dummy placebos, from the EX
# CRF) with the protocol-specified prednisone taper (from the GC glucocorticoid
# log). One SDTM record per dosing event.

derive_ex <- function() {
  ref <- ref_dates()

  study <- read_form("EX") |>
    transmute(USUBJID, VISIT_CD = VISIT, EXTRT, EXDOSE, EXDOSU, EXDOSFRQ = "",
              EXROUTE, EXSTDTC)

  pred <- read_form("GC") |>
    filter(PREDDOSE != "" & suppressWarnings(as.numeric(PREDDOSE)) > 0) |>
    transmute(USUBJID, VISIT_CD = VISIT, EXTRT = "PREDNISONE", EXDOSE = PREDDOSE,
              EXDOSU = "mg", EXDOSFRQ = "QD", EXROUTE = "ORAL", EXSTDTC = GCDTC)

  out <- bind_rows(study, pred) |>
    left_join(ref, by = "USUBJID") |>
    join_visit("VISIT_CD") |>
    mutate(
      STUDYID = STUDYID,
      DOMAIN  = "EX",
      EPOCH   = epoch_of(VISIT),
      EXSTDY  = study_day(EXSTDTC, RFSTDTC),
    ) |>
    arrange(USUBJID, EXSTDTC, EXTRT) |>
    add_seq("EXSEQ") |>
    transmute(STUDYID, DOMAIN, USUBJID, EXSEQ, EXTRT, EXDOSE, EXDOSU, EXDOSFRQ,
              EXROUTE, EPOCH, VISITNUM, VISIT, EXSTDTC, EXENDTC = EXSTDTC, EXSTDY,
              EXENDY = EXSTDY)

  finalize(out, c("STUDYID", "DOMAIN", "USUBJID", "EXSEQ", "EXTRT", "EXDOSE",
                  "EXDOSU", "EXDOSFRQ", "EXROUTE", "EPOCH", "VISITNUM", "VISIT",
                  "EXSTDTC", "EXENDTC", "EXSTDY", "EXENDY"))
}
