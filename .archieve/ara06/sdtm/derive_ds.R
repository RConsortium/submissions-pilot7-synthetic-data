# derive_ds.R — DS (Disposition). One disposition event per subject; the study
# day (DSSTDY) is converted to a date relative to RFSTDTC (DM).

derive_ds <- function() {
  ds <- read_form("DS")
  ref <- read_form("DM") |> select(USUBJID, RFSTDTC)

  out <- ds |>
    left_join(ref, by = "USUBJID") |>
    mutate(
      STUDYID = STUDYID,
      DOMAIN  = "DS",
      DSCAT   = "DISPOSITION EVENT",
      EPOCH   = "TREATMENT",
      DSSTDTC = add_days(RFSTDTC, as.integer(DSSTDY) - 1L),
    ) |>
    arrange(USUBJID) |>
    add_seq("DSSEQ") |>
    transmute(STUDYID, DOMAIN, USUBJID, DSSEQ, DSCAT, DSDECOD, DSTERM,
              EPOCH, DSSTDTC, DSSTDY)

  finalize(out, c("STUDYID", "DOMAIN", "USUBJID", "DSSEQ", "DSCAT",
                  "DSDECOD", "DSTERM", "EPOCH", "DSSTDTC", "DSSTDY"))
}
