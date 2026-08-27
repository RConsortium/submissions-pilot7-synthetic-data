#' common.R — shared helpers for the per-domain CRF -> SDTM derivation programs
#' (EIDD-2801-1001-UK, study 2020-001407-17-00).
#'
#' Each derive_<domain>.R defines derive_<domain>() that reads the raw EDC forms
#' under EDC_DIR/forms (+ lookups) and RETURNS the reconstructed SDTM domain as a
#' data frame (one row per SDTM record). run_all.R sources these and writes the
#' results to OUT (sdtm/sdtm-derived/).
#'
#' Like the ara06 / cath / rave environments (and unlike cdiscpilot1), EIDD-2801
#' is forward-simulated and has NO canonical SDTM truth, so there is no round-trip
#' oracle here — conformance is checked downstream against the CDISC CORE rules
#' engine (validate_sdtm.py).

suppressPackageStartupMessages({
  library(dplyr)
  library(tidyr)
  library(readr)
  library(stringr)
})

if (!exists("EDC_DIR")) EDC_DIR <- normalizePath(file.path("..", "edc"))
FORMS <- file.path(EDC_DIR, "forms")
LOOK  <- file.path(EDC_DIR, "lookups")
if (!exists("OUT")) OUT <- file.path("sdtm-derived")
dir.create(OUT, showWarnings = FALSE, recursive = TRUE)

STUDYID <- "2020-001407-17-00"
DRUG    <- "EIDD-2801"

# unit-only tokens the CRF may echo where a measured value is expected; such a
# cell carries no observation and is dropped (mirrors the generator's suppression).
UNIT_TOKENS <- c("ms", "mmhg", "beats/min", "breaths/min", "kg", "cm", "%",
                 "mg/dl", "mmol/l", "g/dl", "g/l", "ml", "milligram",
                 "milliliter", "degree celsius", "degree fahrenheit")

# ---- readers ---------------------------------------------------------------
read_csv_chr <- function(p) {
  read_csv(p, col_types = cols(.default = col_character()),
           na = character(), show_col_types = FALSE) |>
    mutate(across(everything(), \(x) replace_na(x, "")))
}
read_form <- function(name) read_csv_chr(file.path(FORMS, paste0(name, ".csv")))
read_look <- function(name) read_csv_chr(file.path(LOOK, name))

# Subject registration table (demographics source) + per-subject reference date.
subjects_tbl <- function() read_form("subjects")
# named vector USUBJID -> baseline (Day 1 / dosing) date, the study-day reference.
ref_dates <- function() {
  s <- subjects_tbl()
  setNames(s$BASELINE_DATE, s$USUBJID)
}

# ---- value helpers (ported from the simulator's SDTM helpers) ---------------
`%||%` <- function(a, b) if (is.null(a) || length(a) == 0) b else a

is_blank <- function(v) is.null(v) || length(v) == 0 ||
  (is.character(v) && all(trimws(v) == ""))

is_unit_token <- function(v)
  is.character(v) && length(v) == 1 && tolower(trimws(v)) %in% UNIT_TOKENS

# real (reportable) value: drop blanks and bare unit tokens.
real_value <- function(v) ifelse(is_blank(v) | tolower(trimws(v)) %in% UNIT_TOKENS,
                                 "", as.character(v))

as_number_chr <- function(v) {
  n <- suppressWarnings(as.numeric(v))
  ifelse(is.na(n), "", as.character(n))
}

# "15/Oct/2025" -> Date ("" -> NA)
parse_crf_date <- function(s) {
  s <- trimws(s)
  suppressWarnings(as.Date(ifelse(s == "", NA, s), format = "%d/%b/%Y"))
}

# Date + "HH:MM" -> ISO-8601 --DTC (date-only if time missing/malformed).
iso_dtc <- function(d, time_str = "") {
  base <- ifelse(is.na(d), "", format(d, "%Y-%m-%d"))
  t <- trimws(time_str %||% "")
  ok <- base != "" & str_detect(t, "^[0-9]{1,2}:[0-9]{2}$")
  hhmm <- ifelse(ok, sprintf("%02d:%s",
                             suppressWarnings(as.integer(str_extract(t, "^[0-9]{1,2}"))),
                             str_extract(t, "[0-9]{2}$")), "")
  ifelse(ok, paste0(base, "T", hhmm), base)
}

# SDTM study day: ref day = 1, day before = -1 (no day 0). "" on missing input.
study_day <- function(dtc, ref_iso) {
  d   <- suppressWarnings(as.Date(substr(dtc, 1, 10)))
  ref <- suppressWarnings(as.Date(ref_iso))
  diff <- as.integer(d - ref)
  ifelse(is.na(diff), "", as.character(ifelse(diff >= 0, diff + 1L, diff)))
}

# Single-dose SAD epoch from the visit number.
epoch_of <- function(visitnum) {
  n <- suppressWarnings(as.integer(visitnum))
  case_when(n == 1 ~ "SCREENING", n >= 7 ~ "FOLLOW-UP",
            !is.na(n) ~ "TREATMENT", TRUE ~ "")
}

# --SEQ: 1..n within USUBJID in current row order. Pass data already arranged.
add_seq <- function(df, seqvar) {
  df |> group_by(USUBJID) |> mutate("{seqvar}" := as.character(row_number())) |> ungroup()
}

# Final tidy: every column -> character, NA/"NA" -> "", select in order.
finalize <- function(df, cols) {
  for (c in cols) if (!c %in% names(df)) df[[c]] <- ""
  df |>
    mutate(across(everything(), \(x) { x <- as.character(x); ifelse(is.na(x) | x == "NA", "", x) })) |>
    select(all_of(cols))
}
