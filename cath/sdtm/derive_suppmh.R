# derive_suppmh.R — SUPPMH: atopy history qualifier of the MH diagnosis record.

derive_suppmh <- function() {
  mh  <- derive_mh() |> select(USUBJID, MHSEQ)
  raw <- read_form("MH") |> select(USUBJID, ATOPY)

  out <- mh |>
    left_join(raw, by = "USUBJID") |>
    filter(ATOPY != "") |>
    mutate(
      STUDYID  = STUDYID,
      RDOMAIN  = "MH",
      IDVAR    = "MHSEQ",
      IDVARVAL = MHSEQ,
      QNAM     = "ATOPY",
      QLABEL   = "Atopy History",
      QVAL     = ATOPY,
      QORIG    = "CRF",
      QEVAL    = "",
    ) |>
    arrange(USUBJID)

  finalize(out, c("STUDYID", "RDOMAIN", "USUBJID", "IDVAR", "IDVARVAL",
                  "QNAM", "QLABEL", "QVAL", "QORIG", "QEVAL"))
}
