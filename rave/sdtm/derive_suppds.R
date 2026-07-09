# derive_suppds.R — SUPPDS: treatment-crossover qualifiers of the disposition
# record (whether the subject crossed over to the other arm, and the study day).

derive_suppds <- function() {
  ds  <- derive_ds() |> select(USUBJID, DSSEQ)
  raw <- read_form("DS") |> select(USUBJID, CROSSOVER, CROSSDY)
  labels <- c(CROSSOVR = "Treatment Crossover",
              CROSSDY  = "Crossover Study Day")

  out <- ds |>
    left_join(raw, by = "USUBJID") |>
    rename(CROSSOVR = CROSSOVER) |>
    pivot_longer(c(CROSSOVR, CROSSDY), names_to = "QNAM", values_to = "QVAL") |>
    filter(QVAL != "") |>
    mutate(
      STUDYID  = STUDYID,
      RDOMAIN  = "DS",
      IDVAR    = "DSSEQ",
      IDVARVAL = DSSEQ,
      QLABEL   = unname(labels[QNAM]),
      QORIG    = "CRF",
      QEVAL    = "",
    ) |>
    arrange(USUBJID, QNAM)

  finalize(out, c("STUDYID", "RDOMAIN", "USUBJID", "IDVAR", "IDVARVAL",
                  "QNAM", "QLABEL", "QVAL", "QORIG", "QEVAL"))
}
