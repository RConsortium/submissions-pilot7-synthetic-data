#' =============================================================================
#' Domain: DM (Demographics) — one row per subject
#' =============================================================================
#' Source CRF has no demographics form; subject attributes come from the
#' sampled patient profile (sex, age, race, ethnicity, eligibility) and from
#' the dosing record (reference dates, arm = dose level + formulation).
#' =============================================================================

DM_COLUMNS <- c("STUDYID", "DOMAIN", "USUBJID", "SUBJID", "SITEID", "RFSTDTC",
                "RFENDTC", "RFXSTDTC", "RFXENDTC", "AGE", "AGEU", "SEX", "RACE",
                "ETHNIC", "ARMCD", "ARM", "ACTARMCD", "ACTARM", "COUNTRY")

build_dm <- function(patient, cases) {
  usubjid <- usubjid_of(patient)
  subjid <- sub("^[A-Za-z]+", "", patient$pid)

  # Reference start = dosing datetime (from study-drug form); end = last visit.
  rfstdtc <- ""; drug_taken <- TRUE; dose <- NULL
  for (e in iter_domain_records(cases, function(f) grepl("study_drug", f))) {
    rec <- e$rec
    drug_taken <- tolower(rec_get(rec, "Study Drug taken?") %||% "yes") != "no"
    d <- parse_date(rec_get(rec, "Date"))
    if (!is.null(d)) rfstdtc <- iso_dtc(d, rec_get(rec, "Time"))
    dose <- real_value(rec_get(rec, "Dose"))
  }
  last_visit <- NULL
  for (e in iter_domain_records(cases, function(f) f == "date_of_visit")) {
    d <- parse_date(rec_get(e$rec, "Visit Date"))
    if (!is.null(d) && (is.null(last_visit) || d > last_visit)) last_visit <- d
  }

  dose_n <- as_number(dose)
  if (!is.null(dose_n)) {
    armcd <- paste0(round(dose_n), "MG")
    arm <- trimws(sprintf("%s %d mg %s", SIM_CONFIG$drug_trt, round(dose_n),
                          patient$formulation))
  } else {
    armcd <- "SCRNFAIL"; arm <- "Screen Failure"
  }
  sex <- if (patient$sex == "Male") "M" else "F"

  list(list(
    STUDYID = SIM_CONFIG$study_id, DOMAIN = "DM", USUBJID = usubjid,
    SUBJID = subjid, SITEID = SIM_CONFIG$site_id, RFSTDTC = rfstdtc,
    RFENDTC = if (is.null(last_visit)) "" else format(last_visit, "%Y-%m-%d"),
    RFXSTDTC = rfstdtc, RFXENDTC = rfstdtc,
    AGE = patient$age, AGEU = "YEARS", SEX = sex, RACE = patient$race,
    ETHNIC = patient$ethnic, ARMCD = armcd, ARM = arm, ACTARMCD = armcd,
    ACTARM = arm, COUNTRY = SIM_CONFIG$country))
}
