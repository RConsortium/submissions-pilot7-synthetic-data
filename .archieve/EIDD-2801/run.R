#!/usr/bin/env Rscript
#' =============================================================================
#' EIDD-2801-1001-UK end-to-end pipeline  (submission 2020-001407-17-00)
#' =============================================================================
#' Runs the three-stage environment, mirroring cdiscpilot1 (edc -> sdtm -> adam):
#'
#'   1. edc/generators/build_all.R  parsed eCRF templates -> raw EDC form CSVs
#'   2. sdtm/run_all.R              raw forms -> SDTM domains (CSV)
#'      sdtm/export_conformant.py   SDTM CSV -> typed XPT + Define-XML
#'   3. adam/run_all.R              SDTM XPT -> ADaM datasets (rds + csv)
#'      adam/export_xpt.R           ADaM -> labelled XPT
#'   4. TLF/run_all.R               ADaM -> tables / listings / figures
#'
#' Usage:
#'   Rscript run.R                      # 100 subjects, seed 0 (through ADaM)
#'   Rscript run.R --n 250 --seed 42
#'   Rscript run.R --stage sdtm         # only through the SDTM stage
#'   Rscript run.R --stage tlf          # through the TLF stage
#' =============================================================================

ROOT   <- tryCatch(dirname(normalizePath(sub("^--file=", "",
            grep("^--file=", commandArgs(FALSE), value = TRUE)[1]))),
            error = function(e) normalizePath("."))
args   <- commandArgs(trailingOnly = TRUE)
arg_val <- function(flag, default) {
  i <- which(args == flag); if (length(i) && i < length(args)) args[i + 1] else default
}
n     <- as.integer(arg_val("--n", "100"))
seed  <- as.integer(arg_val("--seed", "0"))
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
cat(strrep("=", 70), "\n  EIDD-2801-1001-UK PIPELINE\n",
    sprintf("  n=%d seed=%d stage=%s\n", n, seed, stage),
    strrep("=", 70), "\n", sep = "")

# 1. EDC
run("EDC generator", ROOT,
    sprintf("Rscript edc/generators/build_all.R --n %d --seed %d", n, seed))

# 2. SDTM
if (thru("sdtm")) {
  run("SDTM derivations",  file.path(ROOT, "sdtm"), "Rscript run_all.R")
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
  run("TLF (tables / listings / figures)", file.path(ROOT, "TLF"), "Rscript run_all.R")
}

cat("\n", strrep("=", 70), "\n",
    sprintf("  PIPELINE COMPLETE  (%.1f s)\n",
            as.numeric(difftime(Sys.time(), start, units = "secs"))),
    strrep("=", 70), "\n", sep = "")
