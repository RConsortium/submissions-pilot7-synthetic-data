# derive_rs.R — RS (Disease Response and Clin Classification): PASI (Psoriasis
# Area and Severity Index), collected only for the psoriasis stratum.

derive_rs <- function() {
  ref <- ref_dates()

  out <- read_form("DD") |>
    filter(PASI != "") |>
    left_join(ref, by = "USUBJID") |>
    join_visit("VISIT") |>
    mutate(
      STUDYID  = STUDYID,
      DOMAIN   = "RS",
      RSTESTCD = "PASI",
      RSTEST   = "Psoriasis Area and Severity Index",
      RSCAT    = "DISEASE SEVERITY",
      RSORRES  = as.character(round(as.numeric(PASI), 4)),
      RSORRESU = "",
      RSSTRESC = RSORRES,
      RSSTRESN = RSORRES,
      RSDTC    = ifelse(PASIDTC == "", add_days(RFSTDTC, .OFFSET), PASIDTC),
      RSBLFL   = ifelse(VISIT == "BASELINE" & PASI != "", "Y", ""),
      EPOCH    = epoch_of(VISIT),
    ) |>
    mutate(RSDY = study_day(RSDTC, RFSTDTC)) |>
    arrange(USUBJID, as.integer(VISITNUM)) |>
    add_seq("RSSEQ")

  finalize(out, c(
    "STUDYID", "DOMAIN", "USUBJID", "RSSEQ", "RSTESTCD", "RSTEST", "RSCAT",
    "RSORRES", "RSORRESU", "RSSTRESC", "RSSTRESN", "RSBLFL", "EPOCH",
    "VISITNUM", "VISIT", "RSDTC", "RSDY"))
}
