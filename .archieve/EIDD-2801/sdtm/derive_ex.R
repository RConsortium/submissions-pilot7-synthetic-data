#' derive_ex.R — EX (Exposure) from the study-drug administration forms.

EX_COLS <- c("STUDYID","DOMAIN","USUBJID","EXSEQ","EXTRT","EXOCCUR","EXDOSE",
             "EXDOSU","EXDOSFRM","EXROUTE","EPOCH","VISITNUM","VISIT",
             "EXSTDTC","EXENDTC","EXSTDY")

.DOSU_MAP <- c("milligram" = "mg", "milliliter" = "mL")

derive_ex <- function() {
  ref <- subjects_tbl() |> select(USUBJID, .REF = BASELINE_DATE)

  read_form("study_drug_placebo_administration_oral") |>
    left_join(ref, by = "USUBJID") |>
    mutate(
      .taken  = tolower(`Study Drug taken?`) != "no",
      EXSTDTC = iso_dtc(parse_crf_date(Date), Time),
      EXENDTC = EXSTDTC,
      EXTRT   = DRUG,
      EXOCCUR = ifelse(.taken, "Y", "N"),
      EXDOSE  = real_value(Dose),
      .dosu   = tolower(`Dose units`),
      EXDOSU  = ifelse(.taken,
                       ifelse(.dosu %in% names(.DOSU_MAP), unname(.DOSU_MAP[.dosu]), `Dose units`),
                       ""),
      EXDOSFRM = ifelse(.taken, Formulation, ""),
      EXROUTE  = ifelse(.taken, "ORAL", ""),
      EPOCH    = epoch_of(VISITNUM),
      EXSTDY   = study_day(EXSTDTC, .REF),
      STUDYID  = STUDYID, DOMAIN = "EX",
      .vn      = suppressWarnings(as.integer(VISITNUM))
    ) |>
    arrange(USUBJID, .vn) |>
    add_seq("EXSEQ") |>
    finalize(EX_COLS)
}
