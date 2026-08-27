#!/usr/bin/env Rscript
#' =============================================================================
#' RAVE end-to-end pipeline  (Rituximab vs Cyclophosphamide, ANCA vasculitis,
#' NCT00104299)
#' =============================================================================
#' Runs the three-stage environment, mirroring cdiscpilot1 (edc -> sdtm -> adam),
#' plus a TLF reporting stage:
#'
#'   1. edc/generators (build_all)  causal-DAG simulator -> raw EDC CRF CSVs
#'   2. sdtm/run_all.R              raw forms -> SDTM domains (CSV)
#'      sdtm/export_conformant.py   SDTM CSV -> typed XPT + Define-XML
#'   3. adam/run_all.R              SDTM XPT -> ADaM datasets (rds + csv)
#'      adam/export_xpt.R           ADaM -> labelled XPT
#'   4. tlf/run_all.R               ADaM -> tables / listings / figures
#'
#' The EDC generator (Python) reproduces the committed CRFs with its default
#' config (N=197, seed=123); change n_patients/seed via a GenConfig in
#' edc/generators/config.py.
#'
#' Usage:
#'   Rscript run.R                  # through ADaM
#'   Rscript run.R --stage sdtm     # only through the SDTM stage
#'   Rscript run.R --stage tlf      # also render the TLF outputs
#' =============================================================================

ROOT <- tryCatch(dirname(normalizePath(sub("^--file=", "",
          grep("^--file=", commandArgs(FALSE), value = TRUE)[1]))),
          error = function(e) normalizePath("."))
args <- commandArgs(trailingOnly = TRUE)
arg_val <- function(flag, default) {
  i <- which(args == flag); if (length(i) && i < length(args)) args[i + 1] else default
}
stage <- arg_val("--stage", "adam")            # edc | sdtm | adam | tlf (cumulative)
.order <- c(edc = 1L, sdtm = 2L, adam = 3L, tlf = 4L)
thru <- function(s) .order[[stage]] >= .order[[s]]
PYTHON <- Sys.getenv("PYTHON", unset = "python3")

run <- function(label, dir, cmd) {
  cat(sprintf("\n>>> %s\n", label))
  status <- system(sprintf("cd %s && %s", shQuote(dir), cmd))
  if (status != 0) stop(sprintf("stage failed (%s): exit %d", label, status))
}

start <- Sys.time()
cat(strrep("=", 70), "\n  RAVE PIPELINE  (stage=", stage, ")\n",
    strrep("=", 70), "\n", sep = "")

# 1. EDC (Python causal-DAG simulator -> edc/forms/)
run("EDC generator", file.path(ROOT, "edc"),
    sprintf("%s -m generators.build_all", PYTHON))

# 2. SDTM
if (thru("sdtm")) {
  run("SDTM derivations", file.path(ROOT, "sdtm"), "Rscript run_all.R")
  run("SDTM export (XPT + Define-XML)", file.path(ROOT, "sdtm"),
      sprintf("%s export_conformant.py", PYTHON))
}

# 3. ADaM
if (thru("adam")) {
  run("ADaM derivations", file.path(ROOT, "adam"), "Rscript run_all.R")
  run("ADaM export (XPT)", file.path(ROOT, "adam"), "Rscript export_xpt.R")
}

# 4. TLF
if (thru("tlf")) {
  run("TLF (tables / listings / figures)", file.path(ROOT, "tlf"), "Rscript run_all.R")
}

cat("\n", strrep("=", 70), "\n",
    sprintf("  PIPELINE COMPLETE  (%.1f s)\n",
            as.numeric(difftime(Sys.time(), start, units = "secs"))),
    strrep("=", 70), "\n", sep = "")
