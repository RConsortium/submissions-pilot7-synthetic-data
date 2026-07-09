# common.R — shared helpers for the per-domain CRF -> SDTM derivation programs (ARA06).
#
# Each derive_<domain>.R defines a function derive_<domain>() that reads the raw
# EDC CRF forms under EDC_DIR/forms (+ lookups) and RETURNS the reconstructed SDTM
# domain as a data frame (one row per SDTM record). run_all.R sources these and
# writes the results to OUT (sdtm/sdtm-derived/).
#
# Unlike cdiscpilot1, ARA06 has NO canonical SDTM truth (it is forward-simulated
# from a causal DAG), so there is no round-trip oracle here. Conformance is checked
# downstream against the CDISC CORE rules engine (validate_sdtm.py).

suppressPackageStartupMessages({
  library(dplyr)
  library(tidyr)
  library(readr)
  library(stringr)
})

if (!exists("EDC_DIR")) EDC_DIR <- normalizePath(".")
FORMS <- file.path(EDC_DIR, "forms")
LOOK  <- file.path(EDC_DIR, "lookups")
if (!exists("OUT")) OUT <- file.path(EDC_DIR, "..", "sdtm", "sdtm-derived")
dir.create(OUT, showWarnings = FALSE, recursive = TRUE)

STUDYID <- "ARA06"

# ---- readers ---------------------------------------------------------------
# Read CSV as all-character (NA -> "") so structural transforms never coerce.
read_csv_chr <- function(p) {
  read_csv(p, col_types = cols(.default = col_character()),
           na = character(), show_col_types = FALSE) |>
    mutate(across(everything(), \(x) replace_na(x, "")))
}
read_form <- function(name) read_csv_chr(file.path(FORMS, paste0("ARA06_CRF_", name, ".csv")))
read_look <- function(name) read_csv_chr(file.path(LOOK, name))

# Visit lookup: CRF VISIT code (e.g. "V2") -> full VISIT name + VISITNUM + VISITDY.
visit_tab <- function() read_look("visit_schedule.csv")

# ---- helpers ---------------------------------------------------------------
# USUBJID "ARA06-SITE08-0001" -> SUBJID "0001".
subjid_of <- function(usubjid) sub(".*-", "", usubjid)

# ISO date + integer day offset -> ISO date ("" on any missing input).
add_days <- function(dtc, n) {
  d <- suppressWarnings(as.Date(dtc))
  n <- suppressWarnings(as.integer(n))
  ifelse(is.na(d) | is.na(n), "", format(d + n))
}

# SDTM study day relative to a reference date: day of ref = 1, day before = -1
# (there is no day 0). "" on any missing input.
study_day <- function(dtc, ref) {
  diff <- suppressWarnings(as.integer(as.Date(dtc) - as.Date(ref)))
  ifelse(is.na(diff), "", as.character(ifelse(diff >= 0, diff + 1L, diff)))
}

# Single-treatment-period EPOCH from the standardized VISIT name.
epoch_of <- function(visit) ifelse(visit == "SCREENING", "SCREENING", "TREATMENT")

# Add the standard --DTC-from-study-day helper isn't needed: the CRFs already
# carry ISO --DTC and integer --DY columns; we copy them through.

# Resolve full VISIT name (and numeric VISITNUM/VISITDY) for a frame that already
# carries a CRF VISIT code column named `code_col`. Returns the frame with VISIT,
# VISITNUM, VISITDY columns (character).
join_visit <- function(df, code_col = "VISIT") {
  vt <- visit_tab() |> rename(.code = VISITCD, .VISIT = VISIT,
                              .VISITNUM = VISITNUM, .VISITDY = VISITDY)
  out <- df |>
    left_join(vt, by = setNames(".code", code_col)) |>
    mutate(VISIT = .VISIT, VISITNUM = .VISITNUM, VISITDY = .VISITDY) |>
    select(-.VISIT, -.VISITNUM, -.VISITDY)
  out
}

# --SEQ: 1..n within USUBJID, in current row order. Pass the data already arranged.
add_seq <- function(df, seqvar) {
  df |> group_by(USUBJID) |> mutate("{seqvar}" := as.character(row_number())) |> ungroup()
}

# Final tidy: every column to character, NA/"NA" -> "".
finalize <- function(df, cols) {
  df |>
    mutate(across(everything(), \(x) ifelse(is.na(x) | x == "NA", "", as.character(x)))) |>
    select(all_of(cols))
}
