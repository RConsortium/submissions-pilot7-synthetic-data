# derive_suppmh.R — SUPPMH: RA-specific qualifiers of the MH primary-diagnosis
# record (RA duration in years; RF/anti-CCP seropositivity). Linked via MHSEQ.

derive_suppmh <- function() {
  mh  <- derive_mh() |> select(USUBJID, MHSEQ)
  raw <- read_form("MH") |> select(USUBJID, RADURYR, RFCCPPOS)
  labels <- c(RADURYR  = "RA Duration (years)",
              RFCCPPOS = "RF/anti-CCP Seropositive")

  out <- mh |>
    left_join(raw, by = "USUBJID") |>
    pivot_longer(c(RADURYR, RFCCPPOS), names_to = "QNAM", values_to = "QVAL") |>
    filter(QVAL != "") |>
    mutate(
      STUDYID  = STUDYID,
      RDOMAIN  = "MH",
      IDVAR    = "MHSEQ",
      IDVARVAL = MHSEQ,
      QLABEL   = unname(labels[QNAM]),
      QORIG    = "CRF",
      QEVAL    = "",
    ) |>
    arrange(USUBJID, QNAM)

  finalize(out, c("STUDYID", "RDOMAIN", "USUBJID", "IDVAR", "IDVARVAL",
                  "QNAM", "QLABEL", "QVAL", "QORIG", "QEVAL"))
}
