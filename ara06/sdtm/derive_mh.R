# derive_mh.R — MH (Medical History): the RA primary-diagnosis record.
# Disease-specific qualifiers (RA duration, RF/anti-CCP status) move to SUPPMH.

derive_mh <- function() {
  mh <- read_form("MH")

  out <- mh |>
    transmute(
      STUDYID = STUDYID,
      DOMAIN  = "MH",
      USUBJID,
      MHTERM  = MHTERM,
      MHDECOD = "Rheumatoid arthritis",
      MHCAT   = "PRIMARY DIAGNOSIS",
      MHPRESP = "Y",
      MHOCCUR = "Y",
    ) |>
    arrange(USUBJID) |>
    add_seq("MHSEQ")

  finalize(out, c("STUDYID", "DOMAIN", "USUBJID", "MHSEQ", "MHTERM",
                  "MHDECOD", "MHCAT", "MHPRESP", "MHOCCUR"))
}
