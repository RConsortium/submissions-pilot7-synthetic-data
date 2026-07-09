# derive_mh.R — MH (Medical History): the ANCA-associated vasculitis primary
# diagnosis (GPA / MPA), from the DC disease-characteristics CRF. ANCA serology
# and other disease qualifiers go to SUPPMH.

derive_mh <- function() {
  dc <- read_form("DC")

  out <- dc |>
    mutate(
      STUDYID = STUDYID,
      DOMAIN  = "MH",
      MHDECOD = recode(DIAGTYPE,
                       "GPA" = "Granulomatosis with polyangiitis",
                       "MPA" = "Microscopic polyangiitis",
                       .default = DIAGTYPE),
      MHTERM  = MHDECOD,
      MHCAT   = "PRIMARY DIAGNOSIS",
      MHPRESP = "Y",
      MHOCCUR = "Y",
    ) |>
    arrange(USUBJID) |>
    add_seq("MHSEQ")

  finalize(out, c("STUDYID", "DOMAIN", "USUBJID", "MHSEQ", "MHTERM",
                  "MHDECOD", "MHCAT", "MHPRESP", "MHOCCUR"))
}
