#' derive_pc.R — PC (PK / biospecimen collection log) from the blood / urine /
#' PBMC sampling forms. The CRF captures collection only (date/time/timepoint/
#' specimen), no assayed concentration, so PCORRES is left blank — each row
#' documents one collection.

PC_COLS <- c("STUDYID","DOMAIN","USUBJID","PCSEQ","PCTESTCD","PCTEST","PCSPEC",
             "PCORRES","PCORRESU","EPOCH","VISITNUM","VISIT","PCTPT","PCDTC","PCDY")

.PC_SPEC <- c(pk_blood_sample = "BLOOD", pk_urine_sample = "URINE",
              pbmc_collection = "PBMC")

derive_pc <- function() {
  ref <- subjects_tbl() |> select(USUBJID, .REF = BASELINE_DATE)
  col <- function(df, nm) if (nm %in% names(df)) df[[nm]] else rep("", nrow(df))

  one <- function(form) {
    df <- read_form(form)
    tibble(
      USUBJID  = df$USUBJID, VISITNUM = df$VISITNUM, VISIT = df$VISIT,
      PCSPEC   = .PC_SPEC[[form]],
      PCTPT    = col(df, "Planned Time Point"),
      .coll    = col(df, "Was the sample collected?"),
      .date    = ifelse(col(df, "Date of Sample Collection") != "",
                        col(df, "Date of Sample Collection"),
                        col(df, "Start Date of Collection")),
      .time    = ifelse(col(df, "Time of Sample Collection") != "",
                        col(df, "Time of Sample Collection"),
                        col(df, "Start Time of Collection"))
    )
  }

  bind_rows(lapply(names(.PC_SPEC), one)) |>
    filter(tolower(.coll) != "no") |>
    left_join(ref, by = "USUBJID") |>
    mutate(
      STUDYID = STUDYID, DOMAIN = "PC",
      PCTESTCD = "EIDD2801", PCTEST = DRUG,
      PCORRES = "", PCORRESU = "",
      PCDTC = iso_dtc(parse_crf_date(.date), .time),
      PCDY  = study_day(PCDTC, .REF),
      EPOCH = epoch_of(VISITNUM),
      .vn   = suppressWarnings(as.integer(VISITNUM))
    ) |>
    filter(PCDTC != "") |>
    arrange(USUBJID, .vn, PCDTC, PCSPEC) |>
    add_seq("PCSEQ") |>
    finalize(PC_COLS)
}
