#' derive_ml.R — ML (Meals) from the meal_detail forms.

ML_COLS <- c("STUDYID","DOMAIN","USUBJID","MLSEQ","MLTRT","MLPRESP","MLOCCUR",
             "EPOCH","VISITNUM","VISIT","MLSTDTC","MLENDTC","MLSTDY")

derive_ml <- function() {
  ref <- subjects_tbl() |> select(USUBJID, .REF = BASELINE_DATE)

  read_form("meal_detail") |>
    left_join(ref, by = "USUBJID") |>
    mutate(
      .sd = parse_crf_date(`Start Date`),
      .ed = parse_crf_date(`End Date`),
      .completed = tolower(`Did the subject complete the meal?`),
      STUDYID = STUDYID, DOMAIN = "ML",
      MLTRT   = `Meal Type`, MLPRESP = "Y",
      MLOCCUR = case_when(.completed == "yes" ~ "Y", .completed == "no" ~ "N", TRUE ~ ""),
      MLSTDTC = iso_dtc(.sd, `Start Time`),
      MLENDTC = iso_dtc(.ed, `End Time`),
      MLSTDY  = study_day(MLSTDTC, .REF),
      EPOCH   = epoch_of(VISITNUM),
      .vn     = suppressWarnings(as.integer(VISITNUM))
    ) |>
    arrange(USUBJID, .vn) |>
    add_seq("MLSEQ") |>
    finalize(ML_COLS)
}
