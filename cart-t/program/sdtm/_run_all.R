## Build every SDTM domain in dependency order, with per-program logrx logs.
## Run from project root: Rscript program/sdtm/_run_all.R
##
## Each program writes data/sdtm/<dom>.rds and logs/sdtm/<dom>.log.

library(logrx)

order   <- c("dm", "mh", "ie", "ae", "cm", "ds", "lb", "qs", "ce")
log_dir <- file.path("logs", "sdtm")
dir.create(log_dir, recursive = TRUE, showWarnings = FALSE)

for (dom in order) {
  src <- file.path("program", "sdtm", paste0(dom, ".R"))
  cat("\n>>>", src, "\n")
  logrx::axecute(
    file          = src,
    log_name      = paste0(dom, ".log"),
    log_path      = log_dir,
    include_rds   = FALSE,
    quit_on_error = FALSE,
    show_repo_url = FALSE
  )
}
cat("\nAll SDTM domains built. Logs in", log_dir, "\n")
