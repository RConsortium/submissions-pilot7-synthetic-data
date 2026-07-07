#' derive_dm.R — DM (Demographics), one row per subject.
#' Source: subjects registration table + study-drug dosing form (reference dates,
#' planned arm = dose level + formulation) + date_of_visit (reference end date).

DM_COLS <- c("STUDYID","DOMAIN","USUBJID","SUBJID","RFSTDTC","RFENDTC",
             "RFXSTDTC","RFXENDTC","SITEID","AGE","AGEU","SEX","RACE","ETHNIC",
             "ARMCD","ARM","ACTARMCD","ACTARM","COUNTRY")

derive_dm <- function() {
  subj <- subjects_tbl()

  dose <- read_form("study_drug_placebo_administration_oral") |>
    transmute(USUBJID,
              RFSTDTC = iso_dtc(parse_crf_date(Date), Time),
              .dose   = real_value(Dose))

  rfend <- read_form("date_of_visit") |>
    mutate(.vdt = parse_crf_date(`Visit Date`)) |>
    group_by(USUBJID) |>
    summarise(RFENDTC = {
      m <- suppressWarnings(max(.vdt, na.rm = TRUE))
      if (is.infinite(m)) "" else format(m, "%Y-%m-%d")
    }, .groups = "drop")

  out <- subj |>
    left_join(dose, by = "USUBJID") |>
    left_join(rfend, by = "USUBJID") |>
    mutate(
      STUDYID  = STUDYID, DOMAIN = "DM",
      RFSTDTC  = coalesce(RFSTDTC, ""),
      RFXSTDTC = RFSTDTC, RFXENDTC = RFSTDTC,
      .dose_n  = suppressWarnings(as.numeric(.dose)),
      ARMCD    = ifelse(!is.na(.dose_n), paste0(round(.dose_n), "MG"), "SCRNFAIL"),
      ARM      = ifelse(!is.na(.dose_n),
                        trimws(sprintf("%s %d mg %s", DRUG, round(.dose_n), FORMULATION)),
                        "Screen Failure"),
      ACTARMCD = ARMCD, ACTARM = ARM
    )

  finalize(out, DM_COLS) |> arrange(USUBJID)
}
