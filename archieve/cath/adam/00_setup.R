# Local-data setup for the admiral ADaM derivations (CATH — vitamin D3 vs placebo).
# Sourced at the top of every ad_*.R. Defines SDTM_DIR / ADAM_DIR paths plus
# read_sdtm() / read_adam() / save_adam() so the programs run against THIS
# environment's generated SDTM (../sdtm/sdtm-derived/xpt/). Mirrors cdiscpilot1.
#
# Run from adam/. Override via env vars: ADAM_SDTM_DIR (XPT source), ADAM_OUT_DIR.

SDTM_DIR <- Sys.getenv("ADAM_SDTM_DIR", unset = "")
if (!nzchar(SDTM_DIR)) SDTM_DIR <- file.path("..", "sdtm", "sdtm-derived", "xpt")
SDTM_DIR <- normalizePath(SDTM_DIR, mustWork = FALSE)
ADAM_DIR <- Sys.getenv("ADAM_OUT_DIR", unset = "adam-derived")
dir.create(ADAM_DIR, recursive = TRUE, showWarnings = FALSE)
ADAM_DIR <- normalizePath(ADAM_DIR)

.coerce_for_admiral <- function(df) {
  for (nm in names(df)) {
    col <- df[[nm]]
    if (inherits(col, c("POSIXct", "POSIXt"))) {
      df[[nm]] <- format(col, "%Y-%m-%dT%H:%M:%S")
    } else if (inherits(col, "Date")) {
      df[[nm]] <- format(col, "%Y-%m-%d")
    } else if (is.logical(col) && all(is.na(col))) {
      df[[nm]] <- as.character(col)
    }
  }
  df
}

read_sdtm <- function(name) {
  path <- file.path(SDTM_DIR, paste0(tolower(name), ".xpt"))
  if (!file.exists(path)) stop("SDTM file not found: ", path)
  .coerce_for_admiral(tibble::as_tibble(haven::read_xpt(path)))
}

read_adam <- function(name) {
  rds <- file.path(ADAM_DIR, paste0(tolower(name), ".rds"))
  if (!file.exists(rds)) stop("ADaM not found: ", rds, " (build it first)")
  readRDS(rds)
}

# ---- labelling -------------------------------------------------------------
.adam_dataset_labels <- c(
  ADSL = "Subject-Level Analysis Dataset",
  ADAE = "Adverse Events Analysis Dataset",
  ADVS = "Vital Signs Analysis Dataset",
  ADLB = "Laboratory Analysis Dataset",
  ADRS = "Disease Response Analysis Dataset"
)

.adam_suffix_label <- function(v) {
  u <- toupper(v)
  if (grepl("EDTM$", u)) return("End Datetime")
  if (grepl("SDTM$", u)) return("Start Datetime")
  if (grepl("TMF$",  u)) return("Time Imputation Flag")
  if (grepl("DTF$",  u)) return("Date Imputation Flag")
  if (grepl("SDT$",  u)) return("Start Date")
  if (grepl("EDT$",  u)) return("End Date")
  if (grepl("ADY$",  u)) return("Relative Day")
  if (grepl("DTM$",  u)) return("Datetime")
  if (grepl("DT$",   u)) return("Date")
  if (grepl("TM$",   u)) return("Time")
  NA_character_
}

.adam_var_labels <- c(
  STUDYID = "Study Identifier", USUBJID = "Unique Subject Identifier",
  SUBJID = "Subject Identifier for the Study", SITEID = "Study Site Identifier",
  AGE = "Age", AGEU = "Age Units", SEX = "Sex", RACE = "Race", ETHNIC = "Ethnicity",
  COUNTRY = "Country", ARM = "Description of Planned Arm",
  ACTARM = "Description of Actual Arm", ARMCD = "Planned Arm Code",
  ACTARMCD = "Actual Arm Code",
  TRTP = "Planned Treatment", TRTA = "Actual Treatment",
  TRT01P = "Planned Treatment for Period 01", TRT01A = "Actual Treatment for Period 01",
  TRTSDT = "Date of First Exposure to Treatment",
  TRTEDT = "Date of Last Exposure to Treatment",
  TRTDURD = "Total Treatment Duration (Days)",
  EOSSTT = "End of Study Status", EOSDT = "End of Study Date",
  DCSREAS = "Reason for Discontinuation from Study",
  SAFFL = "Safety Population Flag", ITTFL = "Intent-To-Treat Population Flag",
  AGEGR1 = "Pooled Age Group 1", RACEGR1 = "Pooled Race Group 1",
  REGION1 = "Geographic Region 1",
  PARAM = "Parameter", PARAMCD = "Parameter Code", PARAMN = "Parameter (N)",
  PARCAT1 = "Parameter Category 1",
  AVAL = "Analysis Value", AVALC = "Analysis Value (C)",
  BASE = "Baseline Value", CHG = "Change from Baseline",
  PCHG = "Percent Change from Baseline",
  ABLFL = "Baseline Record Flag", ANL01FL = "Analysis Record Flag 01",
  AVISIT = "Analysis Visit", AVISITN = "Analysis Visit (N)",
  VISIT = "Visit Name", VISITNUM = "Visit Number",
  ASEQ = "Analysis Sequence Number", DTYPE = "Derivation Type",
  ONTRTFL = "On Treatment Record Flag", TRTEMFL = "Treatment Emergent Analysis Flag",
  ASTDT = "Analysis Start Date", ASTDY = "Analysis Start Relative Day",
  ASEV = "Analysis Severity/Intensity", ASEVN = "Analysis Severity/Intensity (N)",
  AESER = "Serious Event", AEREL = "Causality", AEDECOD = "Dictionary-Derived Term",
  AEBODSYS = "Body System or Organ Class"
)

apply_adam_labels <- function(df, name) {
  ds <- toupper(name)
  for (nm in names(df)) {
    suffix_lab <- .adam_suffix_label(nm)
    lab <- if (!is.na(suffix_lab)) suffix_lab
    else if (toupper(nm) %in% names(.adam_var_labels)) unname(.adam_var_labels[[toupper(nm)]])
    else attr(df[[nm]], "label")
    if (!is.null(lab) && !is.na(lab)) attr(df[[nm]], "label") <- lab
  }
  if (ds %in% names(.adam_dataset_labels))
    attr(df, "label") <- unname(.adam_dataset_labels[[ds]])
  df
}

save_adam <- function(df, name) {
  .sdtm_only <- names(df)[names(df) %in% c("EPOCH", "DOMAIN")]
  if (length(.sdtm_only)) df <- df[, setdiff(names(df), .sdtm_only), drop = FALSE]
  df <- apply_adam_labels(df, name)
  base <- file.path(ADAM_DIR, tolower(name))
  saveRDS(df, paste0(base, ".rds"))
  readr::write_csv(df, paste0(base, ".csv"), na = "")
  message("[admiral] wrote ", base, ".{rds,csv}  (", nrow(df), " rows x ", ncol(df), " cols)")
  invisible(df)
}
