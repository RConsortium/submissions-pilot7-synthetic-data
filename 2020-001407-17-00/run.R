#!/usr/bin/env Rscript
#' =============================================================================
#' EIDD-2801-1001-UK Simulation Pipeline  (submission 2020-001407-17-00)
#' =============================================================================
#' CRF-JSON-driven simulator: parsed eCRF templates -> filled patient cases
#' -> SDTM domain tables.
#'
#' Usage:
#'   Rscript run.R                      # 100 patients, seed 0
#'   Rscript run.R --n 250 --seed 42
#' =============================================================================

if (!requireNamespace("here", quietly = TRUE))
  install.packages("here", repos = "https://cloud.r-project.org")
if (!requireNamespace("jsonlite", quietly = TRUE))
  install.packages("jsonlite", repos = "https://cloud.r-project.org")

library(here)

args <- commandArgs(trailingOnly = TRUE)
arg_val <- function(flag, default) {
  i <- which(args == flag)
  if (length(i) && i + 1 <= length(args)) return(args[i + 1])
  default
}
n    <- as.integer(arg_val("--n", "100"))
seed <- as.integer(arg_val("--seed", "0"))

start <- Sys.time()
cat(strrep("=", 70), "\n", sep = "")
cat("  EIDD-2801-1001-UK SIMULATION PIPELINE\n")
cat(sprintf("  n = %d | seed = %d | %s\n", n, seed,
            format(start, "%Y-%m-%d %H:%M:%S")))
cat(strrep("=", 70), "\n\n", sep = "")

source(here::here("simulator", "run_simulator.R"), local = TRUE)
result <- run_simulator(
  n = n, seed = seed,
  sdtm_dir = here::here("data", "sdtm"),
  cases_dir = here::here("data", "cases")
)

cat("\n", strrep("=", 70), "\n", sep = "")
cat(sprintf("  PIPELINE COMPLETE  (%.1f s)\n",
            as.numeric(difftime(Sys.time(), start, units = "secs"))))
cat(strrep("=", 70), "\n", sep = "")
