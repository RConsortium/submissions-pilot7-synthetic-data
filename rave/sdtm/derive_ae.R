# derive_ae.R — AE (Adverse Events). MedDRA-coded; includes lab-derived AEs
# (leukopenia/neutropenia/anemia from CTCAE grading) and clinical events.

derive_ae <- function() {
  ae <- read_form("AE")

  out <- ae |>
    join_visit("VISIT") |>
    mutate(
      STUDYID = STUDYID,
      DOMAIN  = "AE",
      AESTDY  = AEDY,
    ) |>
    arrange(USUBJID, AESTDTC, AETERM) |>
    add_seq("AESEQ") |>
    transmute(
      STUDYID, DOMAIN, USUBJID, AESEQ, AETERM, AEDECOD, AEBODSYS,
      AESEV, AESER, AEREL, AEACN, AEOUT, AETOXGR, VISITNUM, VISIT,
      AESTDTC, AEENDTC, AESTDY)

  finalize(out, c("STUDYID", "DOMAIN", "USUBJID", "AESEQ", "AETERM",
                  "AEDECOD", "AEBODSYS", "AESEV", "AESER", "AEREL",
                  "AEACN", "AEOUT", "AETOXGR", "VISITNUM", "VISIT",
                  "AESTDTC", "AEENDTC", "AESTDY"))
}
