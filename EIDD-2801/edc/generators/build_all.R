#!/usr/bin/env Rscript
#' =============================================================================
#' EIDD-2801-1001-UK — EDC generator (build_all)
#' =============================================================================
#' Fills every CRF form for N simulated subjects and writes the RAW EDC extract:
#'
#'   edc/forms/<form_category>.csv   one row per filled CRF record
#'                                   (columns = collected CRF field names)
#'   edc/forms/subjects.csv          subject registration / demographics source
#'   edc/lookups/visit_schedule.csv  VISITCD -> VISIT / VISITNUM / VISITDY
#'
#' This is the collection layer. The SDTM domains are reconstructed from these
#' raw forms downstream by sdtm/derive_*.R — mirroring the cdiscpilot1
#' environment (edc/ -> sdtm/ -> adam/).
#'
#' Run:
#'   Rscript edc/generators/build_all.R                 # 100 subjects, seed 0
#'   Rscript edc/generators/build_all.R --n 250 --seed 42
#' =============================================================================

suppressPackageStartupMessages({
  library(jsonlite)
})

# ---- locate this script so paths work regardless of cwd ---------------------
.args_all <- commandArgs(trailingOnly = FALSE)
.fa <- sub("^--file=", "", .args_all[grep("^--file=", .args_all)])
GEN_DIR <- if (length(.fa)) dirname(normalizePath(.fa)) else normalizePath(".")
EDC_DIR <- normalizePath(file.path(GEN_DIR, ".."))       # environments/EIDD-2801/edc
CRF_DIR <- file.path(EDC_DIR, "crf_json")
FORMS_DIR <- file.path(EDC_DIR, "forms")
LOOK_DIR  <- file.path(EDC_DIR, "lookups")
dir.create(FORMS_DIR, showWarnings = FALSE, recursive = TRUE)
dir.create(LOOK_DIR,  showWarnings = FALSE, recursive = TRUE)

source(file.path(GEN_DIR, "sim_config.R"))
source(file.path(GEN_DIR, "sim_core.R"))

# ---- CLI ---------------------------------------------------------------------
.cli <- commandArgs(trailingOnly = TRUE)
arg_val <- function(flag, default) {
  i <- match(flag, .cli)
  if (!is.na(i) && i < length(.cli)) return(.cli[i + 1L])
  default
}
N    <- as.integer(arg_val("--n", "100"))
SEED <- as.integer(arg_val("--seed", "0"))

# ---- helpers -----------------------------------------------------------------
# Encode a (possibly multi-select) CRF value as a single cell; join vectors with "|".
cell <- function(v) {
  if (is.null(v) || length(v) == 0) return("")
  paste(as.character(v), collapse = "|")
}

# Bind a list of named-list rows into a data frame over the UNION of field names
# (missing fields -> ""), preserving first-seen column order.
rows_union_df <- function(rows, lead_cols) {
  fields <- character(0)
  for (r in rows) fields <- union(fields, names(r))
  cols <- c(lead_cols, setdiff(fields, lead_cols))
  mat <- lapply(cols, function(col)
    vapply(rows, function(r) if (is.null(r[[col]])) "" else r[[col]], character(1)))
  stats::setNames(as.data.frame(mat, stringsAsFactors = FALSE), cols)
}

# ---- load CRF templates (skip forms with no recognized visit prefix) ---------
paths <- sort(list.files(CRF_DIR, pattern = "\\.json$", full.names = TRUE))
templates <- list(); skipped <- 0L
for (p in paths) {
  stem <- tools::file_path_sans_ext(basename(p))
  vi <- split_visit_form(stem)
  if (is.na(vi$visit) || is.null(VISIT_INFO[[vi$visit]])) { skipped <- skipped + 1L; next }
  templates[[stem]] <- load_template(p)
}
message(sprintf("=== EIDD-2801 EDC GENERATOR ===  n=%d seed=%d", N, SEED))
message(sprintf("Loaded %d CRF templates (%d skipped)", length(templates), skipped))

set.seed(SEED)
study_formulation <- rnd_choice(SIM_CONFIG$formulation_options)
study_dose_mg     <- rnd_choice(SIM_CONFIG$dose_mg_options)
setup_form_tp_choice(paths)
message(sprintf("Study constants: formulation=%s, dose=%d mg",
                study_formulation, study_dose_mg))

# ---- per-subject: fill all forms, accumulate raw rows per form category ------
by_form  <- list()   # form category -> list of raw rows
subjects <- list()

for (i in seq_len(N)) {
  pid <- sprintf("P%03d", i)
  patient <- make_patient(pid, study_formulation, study_dose_mg)
  usubjid <- usubjid_of(patient)
  cases <- simulate_patient(patient, templates)

  # subject registration / demographics source row
  subjects[[i]] <- list(
    USUBJID = usubjid, SUBJID = sub("^[A-Za-z]+", "", pid),
    SITEID = SIM_CONFIG$site_id, COUNTRY = SIM_CONFIG$country,
    SEX = if (patient$sex == "Male") "M" else "F",
    AGE = as.character(patient$age), AGEU = "YEARS",
    RACE = patient$race, ETHNIC = patient$ethnic,
    WEIGHT = as.character(patient$weight_kg), HEIGHT = as.character(patient$height_cm),
    FORMULATION = patient$formulation, DOSE_MG = as.character(patient$dose_mg),
    ELIGIBLE = if (isTRUE(patient$eligible)) "Y" else "N",
    BASELINE_DATE = format(patient$baseline_date, "%Y-%m-%d"),
    DOSE_DTC = iso_dtc(as.Date(patient$dose_datetime),
                       format(patient$dose_datetime, "%H:%M")))

  # raw CRF records, one row per filled form instance
  stems <- names(cases)
  stems <- stems[order(vapply(stems, chrono_key, numeric(1)))]
  for (stem in stems) {
    vi <- split_visit_form(stem)
    meta <- visit_meta(vi$visit)
    recn <- 0L
    for (rec in cases[[stem]]) {
      recn <- recn + 1L
      row <- list(USUBJID = usubjid, VISITCD = vi$visit,
                  VISITNUM = as.character(meta$num), VISIT = meta$label,
                  RECN = as.character(recn))
      for (fld in names(rec)) row[[fld]] <- cell(rec[[fld]])
      by_form[[vi$form]] <- c(by_form[[vi$form]], list(row))
    }
  }
}

# ---- write raw form CSVs -----------------------------------------------------
lead <- c("USUBJID", "VISITCD", "VISITNUM", "VISIT", "RECN")
for (form in sort(names(by_form))) {
  df <- rows_union_df(by_form[[form]], lead)
  utils::write.csv(df, file.path(FORMS_DIR, paste0(form, ".csv")),
                   row.names = FALSE, na = "")
}
subj_df <- rows_union_df(subjects,
  c("USUBJID","SUBJID","SITEID","COUNTRY","SEX","AGE","AGEU","RACE","ETHNIC",
    "WEIGHT","HEIGHT","FORMULATION","DOSE_MG","ELIGIBLE","BASELINE_DATE","DOSE_DTC"))
utils::write.csv(subj_df, file.path(FORMS_DIR, "subjects.csv"),
                 row.names = FALSE, na = "")

# ---- visit schedule lookup ---------------------------------------------------
vs_rows <- lapply(names(VISIT_INFO), function(cd) {
  m <- VISIT_INFO[[cd]]
  data.frame(VISITCD = cd, VISIT = m$label, VISITNUM = m$num,
             VISITDY = if (m$offset >= 0) m$offset + 1L else m$offset,
             OFFSET = m$offset, stringsAsFactors = FALSE)
})
utils::write.csv(do.call(rbind, vs_rows),
                 file.path(LOOK_DIR, "visit_schedule.csv"), row.names = FALSE)

message(sprintf("\nWrote %d form CSVs + subjects.csv to %s",
                length(by_form), FORMS_DIR))
for (form in sort(names(by_form)))
  message(sprintf("  %-34s %5d rows", form, length(by_form[[form]])))
message(sprintf("subjects.csv: %d rows", length(subjects)))
message(sprintf("lookups/visit_schedule.csv: %d visits", length(VISIT_INFO)))
