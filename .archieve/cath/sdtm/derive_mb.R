# derive_mb.R — MB (Microbiology Findings): skin-surface bacterial load
# (log10 CFU) by compartment. The CRF carries no collection date, so MBDTC is
# reconstructed from the visit offset.

derive_mb <- function() {
  ref <- ref_dates()

  out <- read_form("MB") |>
    filter(CFU_LOG10 != "") |>
    left_join(ref, by = "USUBJID") |>
    join_visit("VISIT") |>
    mutate(
      STUDYID  = STUDYID,
      DOMAIN   = "MB",
      MBTESTCD = "CFU",
      MBTEST   = "Bacterial Colony Count",
      MBCAT    = "MICROBIOLOGY",
      MBORRES  = CFU_LOG10,
      MBORRESU = "log10 CFU",
      MBSTRESC = CFU_LOG10,
      MBSTRESN = CFU_LOG10,
      MBSTRESU = "log10 CFU",
      MBSPEC   = "SKIN SWAB",
      MBLOC    = COMPART,
      MBDTC    = add_days(RFSTDTC, .OFFSET),
      MBDY     = study_day(add_days(RFSTDTC, .OFFSET), RFSTDTC),
      EPOCH    = epoch_of(VISIT),
    ) |>
    arrange(USUBJID, MBLOC, as.integer(VISITNUM)) |>
    add_seq("MBSEQ")

  finalize(out, c(
    "STUDYID", "DOMAIN", "USUBJID", "MBSEQ", "MBTESTCD", "MBTEST", "MBCAT",
    "MBORRES", "MBORRESU", "MBSTRESC", "MBSTRESN", "MBSTRESU", "MBSPEC", "MBLOC",
    "EPOCH", "VISITNUM", "VISIT", "MBDTC", "MBDY"))
}
