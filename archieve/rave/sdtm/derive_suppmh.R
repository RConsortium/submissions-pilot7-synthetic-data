# derive_suppmh.R — SUPPMH: ANCA-associated-vasculitis disease qualifiers of the
# MH diagnosis record — ANCA antibody type (PR3/MPO) and status, new vs relapsing
# diagnosis, and renal involvement.

derive_suppmh <- function() {
  mh  <- derive_mh() |> select(USUBJID, MHSEQ)
  raw <- read_form("DC") |> select(USUBJID, ANCATYPE, ANCASTAT, NEWDX, RENAL)
  labels <- c(ANCATYPE = "ANCA Antibody Type",
              ANCASTAT = "ANCA Status",
              NEWDX    = "New vs Relapsing Diagnosis",
              RENAL    = "Renal Involvement")

  out <- mh |>
    left_join(raw, by = "USUBJID") |>
    pivot_longer(c(ANCATYPE, ANCASTAT, NEWDX, RENAL),
                 names_to = "QNAM", values_to = "QVAL") |>
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
