# derive_vs.R — VS (Vital Signs) from the baseline WEIGHT captured on the DM CRF
# (used for mg/kg dosing). One VS record per subject at BASELINE.

derive_vs <- function() {
  dm <- read_form("DM") |> select(USUBJID, WEIGHT, RFSTDTC)

  out <- dm |>
    filter(WEIGHT != "") |>
    transmute(
      STUDYID  = STUDYID,
      DOMAIN   = "VS",
      USUBJID,
      VSTESTCD = "WEIGHT",
      VSTEST   = "Weight",
      VSORRES  = WEIGHT,
      VSORRESU = "kg",
      VSSTRESC = WEIGHT,
      VSSTRESN = WEIGHT,
      VSSTRESU = "kg",
      VSBLFL   = "Y",
      EPOCH    = "TREATMENT",
      VISITNUM = "2",
      VISIT    = "BASELINE",
      VSDTC    = RFSTDTC,
      VSDY     = "1",
    ) |>
    arrange(USUBJID) |>
    add_seq("VSSEQ")

  finalize(out, c(
    "STUDYID", "DOMAIN", "USUBJID", "VSSEQ", "VSTESTCD", "VSTEST",
    "VSORRES", "VSORRESU", "VSSTRESC", "VSSTRESN", "VSSTRESU",
    "VSBLFL", "EPOCH", "VISITNUM", "VISIT", "VSDTC", "VSDY"))
}
