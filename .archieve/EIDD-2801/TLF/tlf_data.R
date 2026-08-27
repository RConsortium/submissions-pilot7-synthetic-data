# tlf_data.R — load THIS environment's GENERATED ADaM for the TLF programs.
#
# The TLF programs read the ADaM our pipeline produces as SAS Transport (.xpt)
# under adam/adam-derived/_xpt/. Each task's data_setup.R calls
# `read_adam("adsl")` (etc.); the legacy `cad<name>` ids from the upstream
# TLG catalog resolve to our stems via CAD_TO_ADAM.
#
# ADaM datasets we generate: adsl advs adeg adlb. Tasks needing analysis data we
# do NOT derive (AE/CM/MH, PK params, disposition) are reported BLOCKED, not faked.

suppressPackageStartupMessages({
  library(haven)
})

# Legacy benchmark dataset id (cad<name>) -> our generated ADaM stem.
CAD_TO_ADAM <- c(cadsl = "adsl", cadvs = "advs", cadeg = "adeg", cadlb = "adlb")

# Directory holding the generated ADaM .xpt. Defaults to the env's own
# adam-derived/_xpt; override with TLF_ADAM_DIR (set by run_all for a run).
tlf_adam_dir <- function() {
  d <- Sys.getenv("TLF_ADAM_DIR", unset = "")
  if (!nzchar(d) && exists("TLF_DIR"))
    d <- file.path(TLF_DIR, "..", "adam", "adam-derived", "_xpt")
  if (!nzchar(d)) d <- file.path("..", "adam", "adam-derived", "_xpt")
  normalizePath(d, mustWork = FALSE)
}

.adam_stem <- function(name)
  if (name %in% names(CAD_TO_ADAM)) unname(CAD_TO_ADAM[[name]]) else tolower(name)

# Read one generated ADaM dataset from its .xpt, by ADaM name ("adsl") or legacy
# cad name ("cadsl"). haven::read_xpt restores Char/Num types + labels.
read_adam <- function(name, adam_dir = tlf_adam_dir()) {
  p <- file.path(adam_dir, paste0(.adam_stem(name), ".xpt"))
  if (!file.exists(p)) stop("generated ADaM XPT not found: ", p)
  haven::read_xpt(p)
}

adam_available <- function(name)
  file.exists(file.path(tlf_adam_dir(), paste0(.adam_stem(name), ".xpt")))
