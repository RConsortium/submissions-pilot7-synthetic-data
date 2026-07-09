#' derive_sv.R — SV (Subject Visits) from the date_of_visit forms.

SV_COLS <- c("STUDYID","DOMAIN","USUBJID","SVSEQ","VISITNUM","VISIT","EPOCH",
             "SVSTDTC","SVSTDY")

derive_sv <- function() {
  ref <- subjects_tbl() |> select(USUBJID, .REF = BASELINE_DATE)

  read_form("date_of_visit") |>
    mutate(.vdt = parse_crf_date(`Visit Date`)) |>
    filter(!is.na(.vdt)) |>
    left_join(ref, by = "USUBJID") |>
    mutate(
      STUDYID = STUDYID, DOMAIN = "SV",
      SVSTDTC = format(.vdt, "%Y-%m-%d"),
      SVSTDY  = study_day(SVSTDTC, .REF),
      EPOCH   = epoch_of(VISITNUM),
      .vn     = suppressWarnings(as.integer(VISITNUM))
    ) |>
    arrange(USUBJID, .vn) |>
    add_seq("SVSEQ") |>
    finalize(SV_COLS)
}
