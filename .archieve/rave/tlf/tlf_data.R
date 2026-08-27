# tlf_data.R — load THIS environment's GENERATED ADaM for the TLF programs.
#
# Reads the ADaM our pipeline produces as SAS Transport (.xpt) under
# adam/adam-derived/_xpt/. Each task's data_setup.R calls read_adam("adsl") (etc.);
# legacy cad<name> ids resolve via CAD_TO_ADAM.
#
# ADaM datasets we generate: adsl adae advs adlb adrs.

suppressPackageStartupMessages({
  library(haven)
})

CAD_TO_ADAM <- c(cadsl = "adsl", cadae = "adae", cadvs = "advs",
                 cadlb = "adlb", cadrs = "adrs")

tlf_adam_dir <- function() {
  d <- Sys.getenv("TLF_ADAM_DIR", unset = "")
  if (!nzchar(d) && exists("TLF_DIR"))
    d <- file.path(TLF_DIR, "..", "adam", "adam-derived", "_xpt")
  if (!nzchar(d)) d <- file.path("..", "adam", "adam-derived", "_xpt")
  normalizePath(d, mustWork = FALSE)
}

.adam_stem <- function(name)
  if (name %in% names(CAD_TO_ADAM)) unname(CAD_TO_ADAM[[name]]) else tolower(name)

read_adam <- function(name, adam_dir = tlf_adam_dir()) {
  p <- file.path(adam_dir, paste0(.adam_stem(name), ".xpt"))
  if (!file.exists(p)) stop("generated ADaM XPT not found: ", p)
  haven::read_xpt(p)
}

adam_available <- function(name)
  file.exists(file.path(tlf_adam_dir(), paste0(.adam_stem(name), ".xpt")))
