# derive_ae.R — AE (Adverse Events). Sparse in CATH (vitamin D is well tolerated).
# The CRF carries MedDRA PT/SOC, severity, CTCAE grade, relationship and outcome.

derive_ae <- function() {
  ae <- read_form("AE")
  if (nrow(ae) == 0) {
    return(finalize(ae[FALSE, ], c(
      "STUDYID", "DOMAIN", "USUBJID", "AESEQ", "AETERM", "AEDECOD", "AEBODSYS",
      "AESEV", "AESER", "AEREL", "AEACN", "AEOUT", "AETOXGR", "VISITNUM",
      "VISIT", "AESTDTC", "AESTDY")))
  }

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
      AESTDTC, AESTDY)

  finalize(out, c("STUDYID", "DOMAIN", "USUBJID", "AESEQ", "AETERM",
                  "AEDECOD", "AEBODSYS", "AESEV", "AESER", "AEREL",
                  "AEACN", "AEOUT", "AETOXGR", "VISITNUM", "VISIT",
                  "AESTDTC", "AESTDY"))
}
