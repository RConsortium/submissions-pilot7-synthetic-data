# derive_rp.R — RP (Reproductive System Findings): serum/urine pregnancy test
# for women of childbearing potential. The CRF carries no date, so RPDTC is
# reconstructed from the visit offset.

derive_rp <- function() {
  ref <- ref_dates()

  out <- read_form("PG") |>
    filter(PGRES != "") |>
    left_join(ref, by = "USUBJID") |>
    join_visit("VISIT") |>
    mutate(
      STUDYID  = STUDYID,
      DOMAIN   = "RP",
      RPTESTCD = "PREGIND",
      RPTEST   = "Pregnancy Test Indicator",
      RPCAT    = "PREGNANCY",
      RPORRES  = PGRES,
      RPSTRESC = PGRES,
      RPDTC    = add_days(RFSTDTC, .OFFSET),
      RPDY     = study_day(add_days(RFSTDTC, .OFFSET), RFSTDTC),
      EPOCH    = epoch_of(VISIT),
    ) |>
    arrange(USUBJID, as.integer(VISITNUM)) |>
    add_seq("RPSEQ")

  finalize(out, c(
    "STUDYID", "DOMAIN", "USUBJID", "RPSEQ", "RPTESTCD", "RPTEST", "RPCAT",
    "RPORRES", "RPSTRESC", "EPOCH", "VISITNUM", "VISIT", "RPDTC", "RPDY"))
}
