# derive_dm.R — DM (Demographics) from the ARA06 DM CRF.
# RFENDTC = last study contact (RFSTDTC + DSSTDY - 1); RFXSTDTC/RFXENDTC from EX.

derive_dm <- function() {
  dm <- read_form("DM")
  ds <- read_form("DS") |> select(USUBJID, DSSTDY)
  ex <- read_form("EX") |>
    filter(EXTRT %in% c("ETANERCEPT", "ADALIMUMAB")) |>
    group_by(USUBJID) |>
    summarise(RFXSTDTC = min(EXSTDTC), RFXENDTC = max(EXSTDTC), .groups = "drop")

  out <- dm |>
    left_join(ds, by = "USUBJID") |>
    left_join(ex, by = "USUBJID") |>
    mutate(
      STUDYID  = STUDYID,
      DOMAIN   = "DM",
      SUBJID   = subjid_of(USUBJID),
      RFENDTC  = add_days(RFSTDTC, as.integer(DSSTDY) - 1L),
      RFXSTDTC = ifelse(is.na(RFXSTDTC), "", RFXSTDTC),
      RFXENDTC = ifelse(is.na(RFXENDTC), "", RFXENDTC),
      ACTARMCD = ARMCD,
      ACTARM   = ARM,
      AGEU     = "YEARS",
      # CDISC ETHNIC controlled terminology (C66790).
      ETHNIC   = recode(ETHNIC,
                        "NOT HISPANIC" = "NOT HISPANIC OR LATINO",
                        "HISPANIC"     = "HISPANIC OR LATINO",
                        .default = ETHNIC),
    ) |>
    arrange(USUBJID)

  finalize(out, c(
    "STUDYID", "DOMAIN", "USUBJID", "SUBJID", "RFSTDTC", "RFENDTC",
    "RFXSTDTC", "RFXENDTC", "SITEID", "ARMCD", "ARM", "ACTARMCD", "ACTARM",
    "AGE", "AGEU", "SEX", "RACE", "ETHNIC", "COUNTRY"))
}
