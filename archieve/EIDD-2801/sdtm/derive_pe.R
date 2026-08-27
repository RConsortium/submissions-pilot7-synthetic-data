#' derive_pe.R — PE (Physical Examination) from the full and symptom-directed
#' physical-exam forms. One row per body system examined; a not-done exam yields
#' a single PEALL row with PESTAT = "NOT DONE".

PE_COLS <- c("STUDYID","DOMAIN","USUBJID","PESEQ","PETESTCD","PETEST","PEORRES",
             "PESTAT","PEREASND","EPOCH","VISITNUM","VISIT","PEDTC","PEDY")

.PE_SYS <- c("general appearance" = "GENAPP", "heent" = "HEENT",
             "lymphatic" = "LYMPH", "cardiovascular" = "CARDIO",
             "respiratory" = "RESP", "gastrointestinal" = "GI",
             "musculoskeletal" = "MUSSKEL", "neurological" = "NEURO",
             "dermatological" = "DERM", "other" = "OTHER")

.pe_code <- function(sysname) {
  key <- tolower(trimws(sysname))
  mapped <- unname(.PE_SYS[key])
  slug <- substr(gsub("[^A-Z0-9]", "", toupper(sysname)), 1, 8)
  ifelse(!is.na(mapped), mapped, ifelse(slug == "", "PEALL", slug))
}

derive_pe <- function() {
  ref <- subjects_tbl() |> select(USUBJID, .REF = BASELINE_DATE)
  col <- function(df, nm) if (nm %in% names(df)) df[[nm]] else rep("", nrow(df))

  one <- function(form) {
    df <- read_form(form)
    perf <- col(df, "Was Physical Examination performed?")
    perf <- ifelse(perf != "", perf, col(df, "Was the examination performed?"))
    perf <- ifelse(perf != "", perf, col(df, "Was assessment performed?"))
    tibble(
      USUBJID = df$USUBJID, VISITNUM = df$VISITNUM, VISIT = df$VISIT,
      .perf = perf, .reason = col(df, "If No, Reason"),
      .date = col(df, "Date of examination"), .time = col(df, "Time of examination"),
      .result = col(df, "Examination Result"), .sys = col(df, "Body System Examined")
    )
  }

  raw <- bind_rows(one("physical_examination"),
                   one("symptom_directed_physical_exam")) |>
    left_join(ref, by = "USUBJID") |>
    mutate(PEDTC = iso_dtc(parse_crf_date(.date), .time),
           PEDY  = study_day(PEDTC, .REF))

  notdone <- raw |>
    filter(tolower(.perf) == "no") |>
    mutate(PETESTCD = "PEALL", PETEST = "Physical Examination",
           PEORRES = "", PESTAT = "NOT DONE", PEREASND = .reason)

  done <- raw |>
    filter(tolower(.perf) != "no") |>
    separate_rows(.sys, sep = "\\|") |>
    mutate(.sys = trimws(.sys)) |>
    mutate(
      PETESTCD = ifelse(.sys == "", "PEALL", .pe_code(.sys)),
      PETEST   = ifelse(.sys == "", "Physical Examination", .sys),
      PEORRES  = .result, PESTAT = "", PEREASND = ""
    )

  bind_rows(notdone, done) |>
    mutate(STUDYID = STUDYID, DOMAIN = "PE", EPOCH = epoch_of(VISITNUM),
           .vn = suppressWarnings(as.integer(VISITNUM))) |>
    arrange(USUBJID, .vn, PEDTC) |>
    add_seq("PESEQ") |>
    finalize(PE_COLS)
}
