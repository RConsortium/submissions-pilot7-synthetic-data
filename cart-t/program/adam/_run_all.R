## Build every ADaM dataset in dependency order, with per-program logrx logs.
## Run from project root: Rscript program/adam/_run_all.R
##
## ADSL must come first (other datasets join treatment vars from it).

library(logrx)

order   <- c("adsl", "adae", "adcm", "adlb", "adqs",
             "admh", "adds", "adie", "adce")
log_dir <- file.path("logs", "adam")
dir.create(log_dir, recursive = TRUE, showWarnings = FALSE)

for (ds in order) {
  src <- file.path("program", "adam", paste0(ds, ".R"))
  if (!file.exists(src)) {
    cat("SKIP (not yet implemented):", src, "\n")
    next
  }
  cat("\n>>>", src, "\n")
  logrx::axecute(
    file          = src,
    log_name      = paste0(ds, ".log"),
    log_path      = log_dir,
    include_rds   = FALSE,
    quit_on_error = FALSE,
    show_repo_url = FALSE
  )
}
cat("\nAll ADaM datasets built. Logs in", log_dir, "\n")
