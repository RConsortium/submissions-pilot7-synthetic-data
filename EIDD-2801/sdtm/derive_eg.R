#' derive_eg.R — EG (ECG Test Results) from the 12-lead ECG forms.
#' Interval fields captured only as the unit token "ms" carry no value and are
#' dropped; in practice Heart Rate (numeric) + Interpretation (text) remain.

EG_COLS <- c("STUDYID","DOMAIN","USUBJID","EGSEQ","EGTESTCD","EGTEST","EGPOS",
             "EGORRES","EGORRESU","EGSTRESN","EGSTRESU","EGSTRESC","EPOCH",
             "VISITNUM","VISIT","EGDTC","EGDY")

.EG_META <- tibble::tribble(
  ~col,             ~EGTESTCD, ~EGTEST,          ~unit,
  "Heart Rate",     "EGHR",    "Heart Rate",     "beats/min",
  "PR Interval",    "PRAG",    "PR Interval",    "ms",
  "QRS Duration",   "QRSDUR",  "QRS Duration",   "ms",
  "QT Interval",    "QT",      "QT Interval",    "ms",
  "cF",             "QTCF",    "QTcF Interval",  "ms",
  "RR Interval",    "RRAG",    "RR Interval",    "ms"
)

derive_eg <- function() {
  ref <- subjects_tbl() |> select(USUBJID, .REF = BASELINE_DATE)
  df  <- read_form("12_lead_ecg")

  base <- df |>
    filter(tolower(`Was the ECG performed?`) != "no") |>
    mutate(EGDTC = iso_dtc(parse_crf_date(`Date of Assessment`), `Time of Assessment`),
           EGPOS = toupper(`Subject Position`))

  # quantitative parameters
  quant <- base |>
    select(USUBJID, VISITNUM, VISIT, EGDTC, EGPOS,
           any_of(.EG_META$col)) |>
    pivot_longer(any_of(.EG_META$col), names_to = "col", values_to = "EGORRES") |>
    mutate(EGORRES = real_value(EGORRES)) |>
    filter(EGORRES != "") |>
    left_join(.EG_META, by = "col") |>
    mutate(EGORRESU = unit,
           EGSTRESN = as_number_chr(EGORRES),
           EGSTRESU = ifelse(EGSTRESN != "", unit, ""),
           EGSTRESC = EGORRES)

  # qualitative interpretation
  interp <- base |>
    mutate(EGORRES = real_value(`ECG Interpretation`)) |>
    filter(EGORRES != "") |>
    transmute(USUBJID, VISITNUM, VISIT, EGDTC, EGPOS,
              EGTESTCD = "INTP", EGTEST = "Interpretation",
              EGORRES, EGORRESU = "", EGSTRESN = "", EGSTRESU = "", EGSTRESC = EGORRES)

  bind_rows(quant, interp) |>
    left_join(ref, by = "USUBJID") |>
    mutate(STUDYID = STUDYID, DOMAIN = "EG", EPOCH = epoch_of(VISITNUM),
           EGDY = study_day(EGDTC, .REF),
           .vn = suppressWarnings(as.integer(VISITNUM))) |>
    arrange(USUBJID, .vn, EGDTC, EGTESTCD) |>
    add_seq("EGSEQ") |>
    finalize(EG_COLS)
}
