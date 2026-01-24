#' =============================================================================
#' CDISC Pilot 01 Simulator - Main Entry Point
#' =============================================================================
#' Generates SDTM datasets for Xanomeline Alzheimer's Disease Study
#' =============================================================================

#' Run full simulation
#' @param seed Random seed
#' @param output_dir Output directory for SDTM
#' @return List of SDTM datasets
run_simulator <- function(seed = 20060626, output_dir = NULL) {

  message("=== CDISC PILOT 01 SIMULATOR ===")
  message("Xanomeline Transdermal Therapeutic System in Alzheimer's Disease")
  message(sprintf("Seed: %d", seed))
  set.seed(seed)

  # Source dependencies
  source(here::here("simulator", "sim_config.R"))
  source(here::here("simulator", "sim_demographics.R"))
  source(here::here("simulator", "sim_efficacy.R"))
  source(here::here("simulator", "sim_exposure.R"))
  source(here::here("simulator", "sim_safety.R"))
  source(here::here("simulator", "sim_visits.R"))
  source(here::here("simulator", "sim_disposition.R"))
  source(here::here("simulator", "sim_labs.R"))
  source(here::here("simulator", "sim_vitals.R"))

  # Generate SDTM domains
  message("\n[1/8] Generating Demographics (DM, SC)...")
  dm <- sim_dm()
  sc <- sim_sc(dm)
  message(sprintf("  DM: %d subjects", nrow(dm)))
  message(sprintf("     - Placebo: %d", sum(dm$.arm == "Placebo")))
  message(sprintf("     - Xanomeline Low Dose: %d", sum(dm$.arm == "Xanomeline Low Dose")))
  message(sprintf("     - Xanomeline High Dose: %d", sum(dm$.arm == "Xanomeline High Dose")))
  message(sprintf("  SC: %d records", nrow(sc)))

  message("\n[2/8] Generating Disposition status...")
  # Generate completion status first (needed for efficacy and exposure)
  disposition <- generate_completion_status(dm)
  n_completed <- sum(disposition$completed_wk24)
  message(sprintf("  Completed Week 24: %d (%.1f%%)", n_completed, 100 * n_completed / nrow(dm)))
  by_arm <- tapply(disposition$completed_wk24, dm$.arm, function(x) sprintf("%d (%.0f%%)", sum(x), 100*mean(x)))
  message(sprintf("     - Placebo: %s", by_arm["Placebo"]))
  message(sprintf("     - Xanomeline Low: %s", by_arm["Xanomeline Low Dose"]))
  message(sprintf("     - Xanomeline High: %s", by_arm["Xanomeline High Dose"]))

  message("\n[3/8] Generating Cognitive Efficacy Assessments (QS)...")
  efficacy_result <- sim_efficacy(dm, disposition)
  qs <- efficacy_result$qs
  efficacy_summary <- efficacy_result$efficacy_summary
  message(sprintf("  QS: %d records", nrow(qs)))
  message(sprintf("     - ADAS-Cog assessments: %d", sum(qs$QSTESTCD == "ACTOT")))
  message(sprintf("     - CIBIC+ assessments: %d", sum(qs$QSTESTCD == "CIBIC")))

  message("\n[4/8] Generating Exposure (EX)...")
  ex <- sim_ex(dm, disposition)
  message(sprintf("  EX: %d records", nrow(ex)))

  message("\n[5/8] Generating Safety (AE)...")
  ae <- sim_ae(dm, disposition)
  message(sprintf("  AE: %d records", nrow(ae)))
  message(sprintf("  Subjects with AE: %d (%.1f%%)",
                  length(unique(ae$USUBJID)),
                  100 * length(unique(ae$USUBJID)) / nrow(dm)))

  message("\n[6/8] Generating Subject Visits (SV)...")
  sv <- sim_sv(dm, disposition)
  message(sprintf("  SV: %d records", nrow(sv)))

  message("\n[7/8] Generating Disposition records (DS)...")
  ds <- sim_ds(dm, disposition)
  message(sprintf("  DS: %d records", nrow(ds)))

  message("\n[8/8] Generating Laboratory (LB) and Vital Signs (VS)...")
  lb <- sim_lb(dm, disposition)
  vs <- sim_vs(dm, disposition)
  message(sprintf("  LB: %d records (%d parameters)", nrow(lb), length(unique(lb$LBTESTCD))))
  message(sprintf("  VS: %d records (%d parameters)", nrow(vs), length(unique(vs$VSTESTCD))))

  message("\n[FINAL] Assembling datasets...")

  # Remove internal columns from DM
  dm_clean <- dm[, !grepl("^\\.", names(dm))]

  sdtm <- list(
    dm = dm_clean,
    sc = sc,
    sv = sv,
    ex = ex,
    ds = ds,
    ae = ae,
    qs = qs,
    lb = lb,
    vs = vs
  )

  # Save if output directory specified
  if (!is.null(output_dir)) {
    dir.create(output_dir, recursive = TRUE, showWarnings = FALSE)

    # Save SDTM domains in CSV and JSON
    for (domain in names(sdtm)) {
      # CSV
      csv_path <- file.path(output_dir, paste0(domain, ".csv"))
      write.csv(sdtm[[domain]], csv_path, row.names = FALSE)
      message(sprintf("  Saved: %s", csv_path))

      # JSON
      json_path <- file.path(output_dir, paste0(domain, ".json"))
      jsonlite::write_json(sdtm[[domain]], json_path, pretty = TRUE)
    }

    # Save efficacy summary
    csv_path <- file.path(output_dir, "efficacy_summary.csv")
    write.csv(efficacy_summary, csv_path, row.names = FALSE)

    json_path <- file.path(output_dir, "efficacy_summary.json")
    jsonlite::write_json(efficacy_summary, json_path, pretty = TRUE)
    message(sprintf("  Saved: efficacy_summary (.csv, .json)"))

    # Save disposition summary
    csv_path <- file.path(output_dir, "disposition_summary.csv")
    write.csv(disposition, csv_path, row.names = FALSE)

    json_path <- file.path(output_dir, "disposition_summary.json")
    jsonlite::write_json(disposition, json_path, pretty = TRUE)
    message(sprintf("  Saved: disposition_summary (.csv, .json)"))

    # Save DM with internal columns for mapper
    csv_path <- file.path(output_dir, "dm_internal.csv")
    write.csv(dm, csv_path, row.names = FALSE)

    json_path <- file.path(output_dir, "dm_internal.json")
    jsonlite::write_json(dm, json_path, pretty = TRUE)
  }

  message("\n=== SIMULATION COMPLETE ===")

  list(
    sdtm = sdtm,
    efficacy_summary = efficacy_summary,
    disposition = disposition,
    dm_internal = dm
  )
}

# Run if executed directly
if (sys.nframe() == 0 || !interactive()) {
  if (!requireNamespace("here", quietly = TRUE)) {
    install.packages("here", repos = "https://cloud.r-project.org")
  }
  library(here)

  result <- run_simulator(
    seed = 20060626,
    output_dir = here::here("data", "sdtm")
  )
}
