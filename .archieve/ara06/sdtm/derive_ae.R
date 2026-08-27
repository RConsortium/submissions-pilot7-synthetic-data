# derive_ae.R — AE (Adverse Events). The CRF already carries MedDRA PT/SOC
# (AEDECOD/AEBODSYS), severity, CTCAE grade, relationship, action and outcome.

derive_ae <- function() {
  ae <- read_form("AE")

  out <- ae |>
    mutate(
      STUDYID = STUDYID,
      DOMAIN  = "AE",
      AESTDY  = AEDY,
    ) |>
    arrange(USUBJID, AESTDTC, AETERM) |>
    add_seq("AESEQ") |>
    transmute(
      STUDYID, DOMAIN, USUBJID, AESEQ,
      AETERM, AEDECOD, AEBODSYS,
      AESEV, AESER, AEREL, AEACN, AEOUT, AETOXGR,
      VISITNUM, VISIT = VISITLBL,
      AESTDTC, AEENDTC, AESTDY)

  finalize(out, c("STUDYID", "DOMAIN", "USUBJID", "AESEQ", "AETERM",
                  "AEDECOD", "AEBODSYS", "AESEV", "AESER", "AEREL",
                  "AEACN", "AEOUT", "AETOXGR", "VISITNUM", "VISIT",
                  "AESTDTC", "AEENDTC", "AESTDY"))
}
