# derive_dm.R — DM (Demographics) from the CATH DM CRF.
# Diagnostic group + Fitzpatrick type -> SUPPDM; height/weight/BMI -> VS.

derive_dm <- function() {
  dm <- read_form("DM")
  ds <- read_form("DS") |> select(USUBJID, DSSTDY)
  ex <- read_form("EX") |> select(USUBJID, RFXSTDTC = EXSTDTC, RFXENDTC = EXENDTC)

  out <- dm |>
    left_join(ds, by = "USUBJID") |>
    left_join(ex, by = "USUBJID") |>
    mutate(
      STUDYID  = STUDYID,
      DOMAIN   = "DM",
      SUBJID   = subjid_of(USUBJID),
      RFENDTC  = add_days(RFSTDTC, as.integer(DSSTDY) - 1L),
      ACTARMCD = ARMCD,
      ACTARM   = ARM,
      AGEU     = "YEARS",
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
