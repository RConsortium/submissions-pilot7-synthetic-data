# derive_vs.R — VS (Vital Signs) from the baseline WEIGHT captured on the DM CRF.
# ARA06 collects weight once at baseline (used for dosing); modelled as one VS
# record per subject (VSTESTCD = WEIGHT) at the BASELINE visit.

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
      VISITNUM = "2",
      VISIT    = "BASELINE",
      EPOCH    = "TREATMENT",
      VSDTC    = RFSTDTC,
      VSDY     = "1",
      VSBLFL   = "Y",
    ) |>
    arrange(USUBJID) |>
    add_seq("VSSEQ")

  finalize(out, c(
    "STUDYID", "DOMAIN", "USUBJID", "VSSEQ", "VSTESTCD", "VSTEST",
    "VSORRES", "VSORRESU", "VSSTRESC", "VSSTRESN", "VSSTRESU",
    "VSBLFL", "EPOCH", "VISITNUM", "VISIT", "VSDTC", "VSDY"))
}
