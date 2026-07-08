# common.R — shared helpers for the per-domain CRF -> SDTM derivation programs (CATH).
#
# Each derive_<domain>.R defines a function derive_<domain>() that reads the raw
# EDC CRF forms under EDC_DIR/forms (+ lookups) and RETURNS the reconstructed SDTM
# domain as a data frame. run_all.R sources these and writes one CSV per domain.
#
# CATH has NO canonical SDTM truth (forward-simulated from a causal DAG), so there
# is no round-trip oracle; conformance is checked downstream by validate_sdtm.py
# (CDISC CORE rules engine).

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

STUDYID <- "CATH"

# ---- readers ---------------------------------------------------------------
read_csv_chr <- function(p) {
  read_csv(p, col_types = cols(.default = col_character()),
           na = character(), show_col_types = FALSE) |>
    mutate(across(everything(), \(x) replace_na(x, "")))
}
read_form <- function(name) read_csv_chr(file.path(FORMS, paste0("CATH_CRF_", name, ".csv")))
read_look <- function(name) read_csv_chr(file.path(LOOK, name))
visit_tab <- function() read_look("visit_schedule.csv")

# Per-subject reference start date (RFSTDTC = baseline) for study-day / date calc.
ref_dates <- function() read_form("DM") |> select(USUBJID, RFSTDTC)

# ---- helpers ---------------------------------------------------------------
subjid_of <- function(usubjid) sub(".*-", "", usubjid)

add_days <- function(dtc, n) {
  d <- suppressWarnings(as.Date(dtc))
  n <- suppressWarnings(as.integer(n))
  ifelse(is.na(d) | is.na(n), "", format(d + n))
}

# SDTM study day relative to a reference date: day of ref = 1, day before = -1.
study_day <- function(dtc, ref) {
  diff <- suppressWarnings(as.integer(as.Date(dtc) - as.Date(ref)))
  ifelse(is.na(diff), "", as.character(ifelse(diff >= 0, diff + 1L, diff)))
}

# Single-treatment-period EPOCH from the standardized VISIT name.
epoch_of <- function(visit) ifelse(visit %in% c("SCREENING", ""), "SCREENING", "TREATMENT")

# Resolve VISIT name / VISITNUM / day OFFSET (days from RFSTDTC) for a frame
# carrying a CRF visit-code column. Adds VISIT, VISITNUM, .OFFSET columns.
join_visit <- function(df, code_col = "VISIT") {
  vt <- visit_tab() |> transmute(.code = VISITCD, .VISIT = VISIT,
                                 .VISITNUM = VISITNUM, .OFFSET = OFFSET)
  df |>
    left_join(vt, by = setNames(".code", code_col)) |>
    mutate(VISIT = .VISIT, VISITNUM = .VISITNUM, .OFFSET = .OFFSET) |>
    select(-.VISIT, -.VISITNUM)
}

# --SEQ: 1..n within USUBJID, in current row order (arrange beforehand).
add_seq <- function(df, seqvar) {
  df |> group_by(USUBJID) |> mutate("{seqvar}" := as.character(row_number())) |> ungroup()
}

# Final tidy: every column to character, NA/"NA" -> "", select column order.
finalize <- function(df, cols) {
  df |>
    mutate(across(everything(), \(x) ifelse(is.na(x) | x == "NA", "", as.character(x)))) |>
    select(all_of(cols))
}
