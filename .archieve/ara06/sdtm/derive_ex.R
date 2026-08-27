# derive_ex.R — EX (Exposure): study drug (ETN/ADA) and background MTX dosing.
# One SDTM record per CRF dosing row; VISIT name/number from the visit lookup.

derive_ex <- function() {
  ex <- read_form("EX")
  ref <- read_form("DM") |> select(USUBJID, RFSTDTC)

  out <- ex |>
    left_join(ref, by = "USUBJID") |>
    join_visit("VISIT") |>
    mutate(
      STUDYID = STUDYID,
      DOMAIN  = "EX",
      EPOCH   = epoch_of(VISIT),
      EXSTDY  = study_day(EXSTDTC, RFSTDTC),
    ) |>
    arrange(USUBJID, EXSTDTC, EXTRT) |>
    add_seq("EXSEQ") |>
    transmute(
      STUDYID, DOMAIN, USUBJID, EXSEQ,
      EXTRT, EXDOSE, EXDOSU, EXDOSFRQ, EXROUTE, EPOCH,
      VISITNUM, VISIT, EXSTDTC, EXENDTC = EXSTDTC, EXSTDY, EXENDY = EXSTDY)

  finalize(out, c("STUDYID", "DOMAIN", "USUBJID", "EXSEQ", "EXTRT",
                  "EXDOSE", "EXDOSU", "EXDOSFRQ", "EXROUTE", "EPOCH",
                  "VISITNUM", "VISIT", "EXSTDTC", "EXENDTC", "EXSTDY", "EXENDY"))
}
