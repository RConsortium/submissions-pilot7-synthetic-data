# derive_dm.R — DM (Demographics) from the RAVE DM CRF. Ethnicity is not
# collected in RAVE, so ETHNIC is left blank. RFXST/EN come from active study
# drug exposure (rituximab / cyclophosphamide / azathioprine, excluding placebos).

derive_dm <- function() {
  dm <- read_form("DM")
  ds <- read_form("DS") |> select(USUBJID, DSSTDY, DSDECOD)
  # First/last exposure spans every protocol treatment that lands in the derived
  # EX dataset: active randomized drug (EX form, excl. placebos) + prednisone (GC).
  ex_dates <- bind_rows(
    read_form("EX") |>
      filter(!grepl("PLACEBO", EXTRT, ignore.case = TRUE)) |>
      transmute(USUBJID, DTC = EXSTDTC),
    read_form("GC") |>
      filter(PREDDOSE != "" & suppressWarnings(as.numeric(PREDDOSE)) > 0) |>
      transmute(USUBJID, DTC = GCDTC)
  ) |>
    filter(DTC != "") |>
    group_by(USUBJID) |>
    summarise(RFXSTDTC = min(DTC), RFXENDTC = max(DTC), .groups = "drop")

  out <- dm |>
    left_join(ds, by = "USUBJID") |>
    left_join(ex_dates, by = "USUBJID") |>
    mutate(
      STUDYID  = STUDYID,
      DOMAIN   = "DM",
      SUBJID   = subjid_of(USUBJID),
      RFENDTC  = add_days(RFSTDTC, as.integer(DSSTDY) - 1L),
      RFXSTDTC = ifelse(is.na(RFXSTDTC), "", RFXSTDTC),
      RFXENDTC = ifelse(is.na(RFXENDTC), "", RFXENDTC),
      DTHFL    = ifelse(DSDECOD == "DEATH", "Y", ""),
      DTHDTC   = ifelse(DSDECOD == "DEATH",
                        add_days(RFSTDTC, as.integer(DSSTDY) - 1L), ""),
      ACTARMCD = ARMCD,
      ACTARM   = ARM,
      AGEU     = "YEARS",
      ETHNIC   = "",
    ) |>
    arrange(USUBJID)

  finalize(out, c(
    "STUDYID", "DOMAIN", "USUBJID", "SUBJID", "RFSTDTC", "RFENDTC",
    "RFXSTDTC", "RFXENDTC", "DTHDTC", "DTHFL", "SITEID", "ARMCD", "ARM",
    "ACTARMCD", "ACTARM", "AGE", "AGEU", "SEX", "RACE", "ETHNIC", "COUNTRY"))
}
