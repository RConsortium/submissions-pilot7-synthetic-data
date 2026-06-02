#' =============================================================================
#' EIDD-2801-1001-UK Simulator - Main Entry Point
#' =============================================================================
#' Single combined driver:
#'   1. sample N patient profiles
#'   2. fill every CRF form per patient via the generic engine (sim_core.R)
#'      -> ground-truth cases written to data/cases/<P###>/
#'   3. dispatch to each per-domain module (forms/sim_*.R) to map filled cases
#'      -> SDTM domain tables written to data/sdtm/ (CSV + JSON)
#' =============================================================================

#' Registry of SDTM domains: name -> list(columns, builder).
#' Add a new form category by dropping a forms/sim_*.R file and one line here.
sdtm_domain_registry <- function() {
  list(
    dm = list(columns = DM_COLUMNS, build = build_dm),
    sv = list(columns = SV_COLUMNS, build = build_sv),
    ie = list(columns = IE_COLUMNS, build = build_ie),
    ex = list(columns = EX_COLUMNS, build = build_ex),
    vs = list(columns = VS_COLUMNS, build = build_vs),
    eg = list(columns = EG_COLUMNS, build = build_eg),
    lb = list(columns = LB_COLUMNS, build = build_lb),
    pc = list(columns = PC_COLUMNS, build = build_pc),
    pe = list(columns = PE_COLUMNS, build = build_pe),
    ml = list(columns = ML_COLUMNS, build = build_ml)
  )
}

#' Run the full simulation.
#' @param n         number of patient cases
#' @param seed      RNG seed (reproducible within R)
#' @param crf_dir   directory of CRF template JSONs
#' @param sdtm_dir  output dir for SDTM tables (NULL = don't write)
#' @param cases_dir output dir for filled-case ground truth (NULL = don't write)
run_simulator <- function(n = 100, seed = 0,
                          crf_dir = here::here("simulator", "crf_json"),
                          sdtm_dir = here::here("data", "sdtm"),
                          cases_dir = here::here("data", "cases")) {

  sim_dir <- here::here("simulator")
  # Source into the global env so constants (e.g. DM_COLUMNS) and builders are
  # visible to the registry and to one another.
  source(file.path(sim_dir, "sim_config.R"))
  source(file.path(sim_dir, "sim_core.R"))
  for (f in list.files(file.path(sim_dir, "forms"), pattern = "\\.R$", full.names = TRUE))
    source(f)

  message("=== EIDD-2801-1001-UK SIMULATOR ===")
  message(sprintf("Study %s | molnupiravir (%s) | n=%d | seed=%d",
                  SIM_CONFIG$study_id, SIM_CONFIG$drug_trt, n, seed))
  set.seed(seed)

  # ---- load CRF templates (skip those with no recognized visit prefix) ----
  paths <- sort(list.files(crf_dir, pattern = "\\.json$", full.names = TRUE))
  templates <- list(); skipped <- 0L
  for (p in paths) {
    stem <- tools::file_path_sans_ext(basename(p))
    vi <- split_visit_form(stem)
    if (is.na(vi$visit) || is.null(VISIT_INFO[[vi$visit]])) { skipped <- skipped + 1L; next }
    templates[[stem]] <- load_template(p)
  }
  message(sprintf("Loaded %d CRF templates (%d skipped)", length(templates), skipped))

  # ---- study-wide constants + planned-time-point choices ----
  study_formulation <- rnd_choice(SIM_CONFIG$formulation_options)
  study_dose_mg <- rnd_choice(SIM_CONFIG$dose_mg_options)
  setup_form_tp_choice(paths)
  message(sprintf("Study constants: formulation=%s, dose=%d mg",
                  study_formulation, study_dose_mg))

  registry <- sdtm_domain_registry()
  domain_rows <- stats::setNames(vector("list", length(registry)), names(registry))

  if (!is.null(cases_dir)) {
    unlink(cases_dir, recursive = TRUE)
    dir.create(cases_dir, recursive = TRUE, showWarnings = FALSE)
  }

  # ---- per-patient: fill cases, then map every domain ----
  for (i in seq_len(n)) {
    pid <- sprintf("P%03d", i)
    patient <- make_patient(pid, study_formulation, study_dose_mg)
    cases <- simulate_patient(patient, templates)
    if (!is.null(cases_dir)) write_patient_cases(cases, patient, cases_dir)
    for (dom in names(registry)) {
      rows <- registry[[dom]]$build(patient, cases)
      if (length(rows)) domain_rows[[dom]] <- c(domain_rows[[dom]], rows)
    }
  }

  # ---- assemble + save ----
  sdtm <- list()
  for (dom in names(registry)) {
    sdtm[[dom]] <- rows_to_df(domain_rows[[dom]], registry[[dom]]$columns)
  }

  if (!is.null(sdtm_dir)) {
    dir.create(sdtm_dir, recursive = TRUE, showWarnings = FALSE)
    for (dom in names(sdtm)) {
      if (nrow(sdtm[[dom]]) == 0) next
      write_domain(sdtm[[dom]], sdtm_dir, dom)
    }
  }

  message("\n=== SIMULATION COMPLETE ===")
  for (dom in names(sdtm))
    message(sprintf("  %-3s %6d rows", toupper(dom), nrow(sdtm[[dom]])))
  if (!is.null(sdtm_dir)) message(sprintf("\nSDTM:  %s", sdtm_dir))
  if (!is.null(cases_dir)) message(sprintf("Cases: %s", cases_dir))

  invisible(list(sdtm = sdtm, n = n, seed = seed))
}

# Auto-run only when this file is the script passed to Rscript (not when
# sourced by run.R, which sources it then calls run_simulator() itself).
.invoked <- grep("--file=", commandArgs(FALSE), value = TRUE)
if (length(.invoked) && grepl("run_simulator\\.R$", .invoked)) {
  if (!requireNamespace("here", quietly = TRUE))
    install.packages("here", repos = "https://cloud.r-project.org")
  library(here)
  run_simulator()
}
