# derive_suppex.R — SUPPEX: pill-count treatment compliance (%) qualifier of EX.

derive_suppex <- function() {
  ex  <- derive_ex() |> select(USUBJID, EXSEQ)
  raw <- read_form("EX") |> select(USUBJID, COMPLIANCE_PCT)

  out <- ex |>
    left_join(raw, by = "USUBJID") |>
    filter(COMPLIANCE_PCT != "") |>
    mutate(
      STUDYID  = STUDYID,
      RDOMAIN  = "EX",
      IDVAR    = "EXSEQ",
      IDVARVAL = EXSEQ,
      QNAM     = "CMPLPCT",
      QLABEL   = "Treatment Compliance (%)",
      QVAL     = COMPLIANCE_PCT,
      QORIG    = "DERIVED",
      QEVAL    = "",
    ) |>
    arrange(USUBJID)

  finalize(out, c("STUDYID", "RDOMAIN", "USUBJID", "IDVAR", "IDVARVAL",
                  "QNAM", "QLABEL", "QVAL", "QORIG", "QEVAL"))
}
