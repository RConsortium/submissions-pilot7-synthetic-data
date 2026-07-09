#' derive_vs.R — VS (Vital Signs) from the supine vital_sign / vital_signs forms.
#' One row per measured parameter (blanks and bare unit tokens dropped).

VS_COLS <- c("STUDYID","DOMAIN","USUBJID","VSSEQ","VSTESTCD","VSTEST","VSPOS",
             "VSORRES","VSORRESU","VSSTRESN","VSSTRESU","VSLOC","EPOCH",
             "VISITNUM","VISIT","VSTPT","VSDTC","VSDY")

.VS_META <- tibble::tribble(
  ~code,   ~VSTESTCD, ~VSTEST,                    ~unit,
  "SYSBP", "SYSBP",   "Systolic Blood Pressure",  "mmHg",
  "DIABP", "DIABP",   "Diastolic Blood Pressure", "mmHg",
  "PULSE", "PULSE",   "Pulse Rate",               "beats/min",
  "RESP",  "RESP",    "Respiratory Rate",         "breaths/min",
  "TEMP",  "TEMP",    "Temperature",              NA_character_
)
.TEMP_UNIT <- c("degree celsius" = "C", "degree fahrenheit" = "F")

derive_vs <- function() {
  ref <- subjects_tbl() |> select(USUBJID, .REF = BASELINE_DATE)
  col <- function(df, nm) if (nm %in% names(df)) df[[nm]] else rep("", nrow(df))

  one <- function(form) {
    df <- read_form(form)
    tibble(
      USUBJID = df$USUBJID, VISITNUM = df$VISITNUM, VISIT = df$VISIT,
      VSTPT = col(df, "Planned Time Point"),
      VSDTC = iso_dtc(parse_crf_date(col(df, "Date of Assessment")),
                      col(df, "Time of Assessment")),
      .tunit = col(df, "Temperature Unit"), .tloc = col(df, "Temperature location"),
      SYSBP = col(df, "Systolic Blood Pressure"),
      DIABP = col(df, "Diastolic Blood Pressure"),
      PULSE = col(df, "Pulse Rate"), RESP = col(df, "Respiratory Rate"),
      TEMP  = col(df, "Temperature")
    )
  }

  bind_rows(one("vital_sign"), one("vital_signs")) |>
    pivot_longer(c(SYSBP, DIABP, PULSE, RESP, TEMP),
                 names_to = "code", values_to = "VSORRES") |>
    mutate(VSORRES = real_value(VSORRES)) |>
    filter(VSORRES != "") |>
    left_join(.VS_META, by = "code") |>
    left_join(ref, by = "USUBJID") |>
    mutate(
      .tu = unname(.TEMP_UNIT[tolower(.tunit)]),
      VSORRESU = ifelse(code == "TEMP", coalesce(.tu, ""), unit),
      VSSTRESN = as_number_chr(VSORRES),
      VSSTRESU = VSORRESU,
      VSLOC    = ifelse(code == "TEMP", .tloc, ""),
      VSPOS    = "SUPINE",
      STUDYID  = STUDYID, DOMAIN = "VS",
      EPOCH    = epoch_of(VISITNUM),
      VSDY     = study_day(VSDTC, .REF),
      .vn      = suppressWarnings(as.integer(VISITNUM))
    ) |>
    arrange(USUBJID, .vn, VSDTC, VSTESTCD) |>
    add_seq("VSSEQ") |>
    finalize(VS_COLS)
}
