#!/usr/bin/env Rscript
#' =============================================================================
#' KEYNOTE-868 Simulation Pipeline
#' =============================================================================
#'
#' 4-Layer Architecture:
#'   1. TARGETS  - Published data and accuracy metadata
#'   2. SIMULATOR - Generate SDTM from targets
#'   3. MAPPER   - Derive ADaM from SDTM
#'   4. SCORER   - Compare simulated vs targets
#'
#' Usage:
#'   Rscript run.R           # Run full pipeline
#'   Rscript run.R --seed 123  # Run with custom seed
#'
#' =============================================================================

# -----------------------------------------------------------------------------
# Setup
# -----------------------------------------------------------------------------

# Install required packages if needed
if (!requireNamespace("here", quietly = TRUE)) {
  install.packages("here", repos = "https://cloud.r-project.org")
}

if (!requireNamespace("survival", quietly = TRUE)) {
  install.packages("survival", repos = "https://cloud.r-project.org")
}

if (!requireNamespace("jsonlite", quietly = TRUE)) {
  install.packages("jsonlite", repos = "https://cloud.r-project.org")
}

library(here)
library(survival)
library(jsonlite)

# Parse command line arguments
args <- commandArgs(trailingOnly = TRUE)
seed <- 20260120

if ("--seed" %in% args) {
  seed_idx <- which(args == "--seed") + 1
  if (seed_idx <= length(args)) {
    seed <- as.integer(args[seed_idx])
  }
}

# -----------------------------------------------------------------------------
# Main Pipeline
# -----------------------------------------------------------------------------

run_pipeline <- function(seed = 20260120) {

  start_time <- Sys.time()

  cat("\n")
  cat(paste(rep("=", 70), collapse = ""), "\n")
  cat("  KEYNOTE-868 SIMULATION PIPELINE\n")
  cat(paste(rep("=", 70), collapse = ""), "\n")
  cat(sprintf("  Seed: %d\n", seed))
  cat(sprintf("  Time: %s\n", format(start_time, "%Y-%m-%d %H:%M:%S")))
  cat(paste(rep("=", 70), collapse = ""), "\n\n")

  # Create output directories
  dir.create(here("data", "sdtm"), recursive = TRUE, showWarnings = FALSE)
  dir.create(here("data", "adam"), recursive = TRUE, showWarnings = FALSE)
  dir.create(here("output"), recursive = TRUE, showWarnings = FALSE)

  # -------------------------------------------------------------------------
  # Layer 1: TARGETS (loaded by other layers)
  # -------------------------------------------------------------------------
  cat("[LAYER 1] TARGETS\n")
  cat("  Target values and metadata defined in targets/\n")
  cat("  Accuracy tiers: CRITICAL (±5%), HIGH (±10%), MODERATE (±20%), LOW (±30%)\n\n")

  # -------------------------------------------------------------------------
  # Layer 2: SIMULATOR
  # -------------------------------------------------------------------------
  cat("[LAYER 2] SIMULATOR\n")
  source(here("simulator", "run_simulator.R"), local = TRUE)
  sim_result <- run_simulator(seed = seed, output_dir = here("data", "sdtm"))
  cat("\n")

  # -------------------------------------------------------------------------
  # Layer 3: MAPPER
  # -------------------------------------------------------------------------
  cat("[LAYER 3] MAPPER\n")
  source(here("mapper", "run_mapper.R"), local = TRUE)
  adam_result <- run_mapper(
    sdtm_dir = here("data", "sdtm"),
    output_dir = here("data", "adam")
  )
  cat("\n")

  # -------------------------------------------------------------------------
  # Layer 4: SCORER
  # -------------------------------------------------------------------------
  cat("[LAYER 4] SCORER\n")
  source(here("scorer", "run_scorer.R"), local = TRUE)
  score_result <- run_scorer(
    adam_dir = here("data", "adam"),
    output_dir = here("output")
  )

  # -------------------------------------------------------------------------
  # Summary
  # -------------------------------------------------------------------------
  end_time <- Sys.time()
  duration <- difftime(end_time, start_time, units = "secs")

  cat("\n")
  cat(paste(rep("=", 70), collapse = ""), "\n")
  cat("  PIPELINE COMPLETE\n")
  cat(paste(rep("=", 70), collapse = ""), "\n")
  cat(sprintf("  Duration: %.1f seconds\n", as.numeric(duration)))
  cat(sprintf("  Metrics scored: %d\n", score_result$total_metrics))
  cat(sprintf("  Metrics passed: %d (%.1f%%)\n",
              score_result$total_passed,
              score_result$total_passed / score_result$total_metrics * 100))
  cat("\n")
  cat("  Output locations:\n")
  cat(sprintf("    SDTM: %s\n", here("data", "sdtm")))
  cat(sprintf("    ADaM: %s\n", here("data", "adam")))
  cat(sprintf("    Scores: %s\n", here("output")))
  cat(paste(rep("=", 70), collapse = ""), "\n\n")

  invisible(list(
    sim = sim_result,
    adam = adam_result,
    score = score_result
  ))
}

# Run the pipeline
result <- run_pipeline(seed = seed)
