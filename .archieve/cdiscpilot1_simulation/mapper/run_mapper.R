#' =============================================================================
#' CDISC Pilot 01 Mapper - Main Entry Point
#' Xanomeline TTS in Alzheimer's Disease
#' =============================================================================
#' Derives ADaM datasets from SDTM
#' =============================================================================

#' Run full mapping
#' @param sdtm_dir Directory containing SDTM datasets
#' @param output_dir Output directory for ADaM
#' @return List of ADaM datasets
run_mapper <- function(sdtm_dir = NULL, output_dir = NULL) {

  message("=== CDISC PILOT 01 MAPPER ===")
  message("Xanomeline Transdermal Therapeutic System in Alzheimer's Disease")

  # Source dependencies
  source(here::here("mapper", "map_adsl.R"))
  source(here::here("mapper", "map_adqs.R"))
  source(here::here("mapper", "map_adae.R"))
  source(here::here("mapper", "map_adlb.R"))
  source(here::here("mapper", "map_advs.R"))

  # Load SDTM data
  if (is.null(sdtm_dir)) {
    sdtm_dir <- here::here("data", "sdtm")
  }

  message(sprintf("\nLoading SDTM from: %s", sdtm_dir))

  # Read from CSV format
  dm <- read.csv(file.path(sdtm_dir, "dm_internal.csv"), stringsAsFactors = FALSE)
  sc <- read.csv(file.path(sdtm_dir, "sc.csv"), stringsAsFactors = FALSE)
  ex <- read.csv(file.path(sdtm_dir, "ex.csv"), stringsAsFactors = FALSE)
  ds <- read.csv(file.path(sdtm_dir, "ds.csv"), stringsAsFactors = FALSE)
  ae <- read.csv(file.path(sdtm_dir, "ae.csv"), stringsAsFactors = FALSE)
  qs <- read.csv(file.path(sdtm_dir, "qs.csv"), stringsAsFactors = FALSE)
  lb <- read.csv(file.path(sdtm_dir, "lb.csv"), stringsAsFactors = FALSE)
  vs <- read.csv(file.path(sdtm_dir, "vs.csv"), stringsAsFactors = FALSE)

  # Load efficacy summary (for LOCF reference)
  efficacy_summary <- NULL
  eff_path <- file.path(sdtm_dir, "efficacy_summary.csv")
  if (file.exists(eff_path)) {
    efficacy_summary <- read.csv(eff_path, stringsAsFactors = FALSE)
  }

  # Convert date columns back to Date type
  date_cols <- c("RFSTDTC", "RFENDTC", ".randdt", ".rfstdtc")
  for (col in date_cols) {
    if (col %in% names(dm)) {
      dm[[col]] <- as.Date(dm[[col]])
    }
  }

  ex_date_cols <- c("EXSTDTC", "EXENDTC")
  for (col in ex_date_cols) {
    if (col %in% names(ex)) {
      ex[[col]] <- as.Date(ex[[col]])
    }
  }

  ae_date_cols <- c("AESTDTC", "AEENDTC")
  for (col in ae_date_cols) {
    if (col %in% names(ae)) {
      ae[[col]] <- as.Date(ae[[col]])
    }
  }

  qs_date_cols <- c("QSDTC")
  for (col in qs_date_cols) {
    if (col %in% names(qs)) {
      qs[[col]] <- as.Date(qs[[col]])
    }
  }

  lb_date_cols <- c("LBDTC")
  for (col in lb_date_cols) {
    if (col %in% names(lb)) {
      lb[[col]] <- as.Date(lb[[col]])
    }
  }

  vs_date_cols <- c("VSDTC")
  for (col in vs_date_cols) {
    if (col %in% names(vs)) {
      vs[[col]] <- as.Date(vs[[col]])
    }
  }

  message(sprintf("  DM: %d subjects", nrow(dm)))
  message(sprintf("  SC: %d records", nrow(sc)))
  message(sprintf("  EX: %d records", nrow(ex)))
  message(sprintf("  DS: %d records", nrow(ds)))
  message(sprintf("  AE: %d records", nrow(ae)))
  message(sprintf("  QS: %d records", nrow(qs)))
  message(sprintf("  LB: %d records", nrow(lb)))
  message(sprintf("  VS: %d records", nrow(vs)))

  # Create ADaM datasets
  message("\nMapping ADaM datasets...")

  # ADSL - Subject Level Analysis Dataset
  adsl <- map_adsl(dm, sc, ex, ds)

  # ADQS - Questionnaire (Cognitive Efficacy) Analysis Dataset
  adqs <- map_adqs(qs, adsl, efficacy_summary)

  # ADAE - Adverse Events Analysis Dataset
  adae <- map_adae(ae, adsl)

  # ADLB - Laboratory Analysis Dataset
  adlb <- map_adlb(lb, adsl)

  # ADVS - Vital Signs Analysis Dataset
  advs <- map_advs(vs, adsl)

  adam <- list(
    adsl = adsl,
    adqs = adqs,
    adae = adae,
    adlb = adlb,
    advs = advs
  )

  # Save if output directory specified
  if (!is.null(output_dir)) {
    dir.create(output_dir, recursive = TRUE, showWarnings = FALSE)

    for (ds_name in names(adam)) {
      # CSV
      csv_path <- file.path(output_dir, paste0(ds_name, ".csv"))
      write.csv(adam[[ds_name]], csv_path, row.names = FALSE)
      message(sprintf("  Saved: %s", csv_path))

      # JSON
      json_path <- file.path(output_dir, paste0(ds_name, ".json"))
      jsonlite::write_json(adam[[ds_name]], json_path, pretty = TRUE)
    }
  }

  message("\n=== MAPPING COMPLETE ===")

  adam
}

# Run if executed directly
if (sys.nframe() == 0 || !interactive()) {
  if (!requireNamespace("here", quietly = TRUE)) {
    install.packages("here", repos = "https://cloud.r-project.org")
  }
  library(here)

  result <- run_mapper(
    sdtm_dir = here::here("data", "sdtm"),
    output_dir = here::here("data", "adam")
  )
}
