## Build raw .rds files from car-t-openclinica.xml with logrx logging.
## Run from project root: Rscript program/raw/_run_all.R
##
## Produces data/raw/flat.rds plus one .rds per CRF form (slug names from
## the form_slug map in load_xml.R). Log: logs/raw/load_xml.log.

library(logrx)

log_dir <- file.path("logs", "raw")
dir.create(log_dir, recursive = TRUE, showWarnings = FALSE)

logrx::axecute(
  file          = file.path("program", "raw", "load_xml.R"),
  log_name      = "load_xml.log",
  log_path      = log_dir,
  include_rds   = FALSE,
  quit_on_error = FALSE,
  show_repo_url = FALSE
)

cat("\nRaw .rds built. Log in", log_dir, "\n")
