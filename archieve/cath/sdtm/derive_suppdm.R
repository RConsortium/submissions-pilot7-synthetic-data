# derive_suppdm.R — SUPPDM: baseline subject characteristics that are not
# standard DM variables — diagnostic stratum (DXGROUP) and Fitzpatrick skin type.

derive_suppdm <- function() {
  # QNAM is limited to 8 chars, so FITZPATRICK is carried as FITZSKIN.
  raw <- read_form("DM") |>
    select(USUBJID, DXGROUP, FITZSKIN = FITZPATRICK)
  labels <- c(DXGROUP  = "Diagnostic Group",
              FITZSKIN = "Fitzpatrick Skin Type")

  out <- raw |>
    pivot_longer(c(DXGROUP, FITZSKIN), names_to = "QNAM", values_to = "QVAL") |>
    filter(QVAL != "") |>
    mutate(
      STUDYID  = STUDYID,
      RDOMAIN  = "DM",
      IDVAR    = "",
      IDVARVAL = "",
      QLABEL   = unname(labels[QNAM]),
      QORIG    = "CRF",
      QEVAL    = "",
    ) |>
    arrange(USUBJID, QNAM)

  finalize(out, c("STUDYID", "RDOMAIN", "USUBJID", "IDVAR", "IDVARVAL",
                  "QNAM", "QLABEL", "QVAL", "QORIG", "QEVAL"))
}
