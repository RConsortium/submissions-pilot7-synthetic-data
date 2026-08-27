# derive_mh.R — MH (Medical History): the baseline diagnosis record (healthy
# control / atopic dermatitis / psoriasis). Atopy history -> SUPPMH.

derive_mh <- function() {
  mh <- read_form("MH")

  out <- mh |>
    transmute(
      STUDYID = STUDYID,
      DOMAIN  = "MH",
      USUBJID,
      MHTERM  = MHTERM,
      MHDECOD = MHDECOD,
      MHCAT   = MHCAT,
      MHPRESP = "Y",
      MHOCCUR = "Y",
    ) |>
    arrange(USUBJID) |>
    add_seq("MHSEQ")

  finalize(out, c("STUDYID", "DOMAIN", "USUBJID", "MHSEQ", "MHTERM",
                  "MHDECOD", "MHCAT", "MHPRESP", "MHOCCUR"))
}
