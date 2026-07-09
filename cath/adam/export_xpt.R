#!/usr/bin/env Rscript
# export_xpt.R — convert the derived ADaM tables (adam-derived/<name>.rds)
# into SAS Transport (.xpt v5) under adam-derived/_xpt/, carrying the variable
# and dataset labels that run_all.R/save_adam() already attached.
#
# This is the ADaM analogue of ../sdtm/export_conformant.py: run_all.R does the
# analysis-variable derivations (writing .rds + .csv); this step renders them to
# the labelled XPT that the CDISC ADaM rules engine consumes. The validator can
# also read the .csv directly, but XPT preserves the dataset/variable labels that
# the label-conformance rules (e.g. ADSL must be "Subject-Level Analysis Dataset")
# check, so XPT is the canonical validation input.
#
# Run from this directory:
#   cd environments/cdiscpilot1/adam
#   Rscript export_xpt.R

suppressPackageStartupMessages({
  library(haven)
})

# Defaults to the env's own adam-derived/, overridable via ADAM_OUT_DIR so a
# freshly generated run elsewhere can be exported (see generate_adam).
ADAM_DIR <- Sys.getenv("ADAM_OUT_DIR", unset = "adam-derived")
ADAM_DIR <- normalizePath(ADAM_DIR, mustWork = TRUE)
OUT <- file.path(ADAM_DIR, "_xpt")
dir.create(OUT, recursive = TRUE, showWarnings = FALSE)

rds_files <- sort(list.files(ADAM_DIR, pattern = "\\.rds$", full.names = TRUE))
if (!length(rds_files)) {
  stop("No ADaM .rds files in ", ADAM_DIR, " — run `Rscript run_all.R` first.")
}

# ADaM stores analysis dates/times as *numeric* SAS values (--DT = days from
# 1970-01-01, --DTM = seconds, --TM = seconds since midnight). admiral's
# derive_vars_dt/dtm()/time helpers produce R Date / POSIXct / hms (difftime)
# columns, and haven would write those with SAS date/time *formats* — which read
# back as date/time objects, not numbers, tripping the "*DT*/*DTM*/*TM* must be
# numeric" ADaM rules. Coerce them to plain numeric first, matching how the
# canonical ADaM XPT is stored. Labels are dropped by as.numeric, so re-attach
# them. Character --DTC and --TMF imputation flags are untouched.
numericize_dates <- function(df) {
  for (nm in names(df)) {
    col <- df[[nm]]
    if (inherits(col, "Date") || inherits(col, "POSIXct") ||
        inherits(col, "POSIXt") || inherits(col, "difftime")) {
      lab <- attr(col, "label")
      df[[nm]] <- as.numeric(col)
      if (!is.null(lab)) attr(df[[nm]], "label") <- lab
    }
  }
  df
}

# XPT v5 caps variable labels at 40 bytes; truncate (with a warning) rather than
# error so the export never blocks validation.
trunc_labels <- function(df) {
  for (nm in names(df)) {
    lab <- attr(df[[nm]], "label")
    if (!is.null(lab) && !is.na(lab) && nchar(lab) > 40L) {
      warning("Truncating label for ", nm, ": ", lab, call. = FALSE)
      attr(df[[nm]], "label") <- substr(lab, 1L, 40L)
    }
  }
  df
}

for (f in rds_files) {
  name <- tools::file_path_sans_ext(basename(f))   # e.g. "adsl"
  df <- trunc_labels(numericize_dates(readRDS(f)))
  out_path <- file.path(OUT, paste0(name, ".xpt"))
  # name = transport member name (<= 8 chars, upper-cased by haven).
  write_xpt(df, out_path, version = 5, name = toupper(name))
  message(sprintf("[xpt] %-8s -> %s  (%d rows x %d cols)",
                  toupper(name), out_path, nrow(df), ncol(df)))
}
