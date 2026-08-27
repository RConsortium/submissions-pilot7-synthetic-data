#!/usr/bin/env Rscript
# run_all.R [task ...] — run the TLF programs against this environment's GENERATED
# ADaM and write each output (tables/listings as .rds + .txt, figures as .png) to
# tlf-derived/<task>/.
#
# Each tlf/<task>/ folder holds (mirroring the cdiscpilot1 tlf catalog):
#   task.json     metadata: inputs (which ADaM), output_type, expected_variables
#   data_setup.R  preprocessing (reads generated ADaM via read_adam())
#   solve.R       builds the result objects (result1..N, or a plot)
#
# Run from the tlf/ stage dir:  cd tlf && Rscript run_all.R [task ...]

suppressPackageStartupMessages({
  library(jsonlite)
})

.args0 <- commandArgs(trailingOnly = FALSE)
.fa <- sub("^--file=", "", .args0[grep("^--file=", .args0)])
TLF_DIR <- if (length(.fa)) dirname(normalizePath(.fa)) else normalizePath(".")
source(file.path(TLF_DIR, "tlf_data.R"))

if (!nzchar(Sys.getenv("TLF_ADAM_DIR")))
  Sys.setenv(TLF_ADAM_DIR = normalizePath(
    file.path(TLF_DIR, "..", "adam", "adam-derived", "_xpt"), mustWork = FALSE))

OUT_BASE <- Sys.getenv("TLF_OUT_DIR", unset = file.path(TLF_DIR, "tlf-derived"))
dir.create(OUT_BASE, recursive = TRUE, showWarnings = FALSE)

want <- commandArgs(trailingOnly = TRUE)
task_dirs <- list.dirs(TLF_DIR, recursive = FALSE)
task_dirs <- task_dirs[file.exists(file.path(task_dirs, "task.json"))]
tasks <- basename(task_dirs)
if (length(want)) tasks <- intersect(tasks, want)
if (!length(tasks)) stop("no TLF tasks matched")

render_one <- function(obj, name, dir) {
  if (inherits(obj, c("gg", "ggplot"))) {
    ggplot2::ggsave(file.path(dir, paste0(name, ".png")), obj,
                    width = 10, height = 6.5, dpi = 130, bg = "white")
  } else {
    saveRDS(obj, file.path(dir, paste0(name, ".rds")))
    txt <- tryCatch(
      paste(formatters::export_as_txt(obj, paginate = FALSE), collapse = "\n"),
      error = function(e) paste(utils::capture.output(print(obj)), collapse = "\n"))
    writeLines(txt, file.path(dir, paste0(name, ".txt")))
  }
  TRUE
}

run_task <- function(task) {
  tdir <- file.path(TLF_DIR, task)
  meta <- fromJSON(file.path(tdir, "task.json"))
  cads <- unique(sub("\\.rds$", "", names(meta$inputs)))
  missing <- cads[!vapply(cads, adam_available, logical(1))]
  outdir <- file.path(OUT_BASE, task)
  if (length(missing))
    return(data.frame(task = task, status = "BLOCKED", n_out = 0L,
                      detail = paste("no generated ADaM for", paste(missing, collapse = ",")),
                      stringsAsFactors = FALSE))

  unlink(outdir, recursive = TRUE); dir.create(outdir, recursive = TRUE)
  tryCatch({
    env <- new.env(parent = globalenv())
    old <- setwd(outdir); on.exit(setwd(old), add = TRUE)
    sys.source(file.path(tdir, "data_setup.R"), envir = env)
    sys.source(file.path(tdir, "solve.R"), envir = env)
    vars <- meta$expected_variables
    if (is.null(vars) || !length(vars))
      vars <- ls(env)[vapply(ls(env), function(v)
        inherits(get(v, env), c("gg", "ggplot", "VTableTree", "listing_df", "rtable")),
        logical(1))]
    n <- 0L
    for (v in vars) if (exists(v, env, inherits = FALSE)) {
      ok <- tryCatch(render_one(get(v, env), v, outdir), error = function(e) FALSE)
      if (ok) n <- n + 1L
    }
    data.frame(task = task, status = if (n > 0) "OK" else "NO_OUTPUT",
               n_out = n, detail = "", stringsAsFactors = FALSE)
  }, error = function(e)
    data.frame(task = task, status = "ERROR", n_out = 0L,
               detail = substr(conditionMessage(e), 1, 200), stringsAsFactors = FALSE))
}

summ <- do.call(rbind, lapply(tasks, function(t) {
  r <- run_task(t)
  cat(sprintf("%-24s %-9s %d  %s\n", r$task, r$status, r$n_out, r$detail))
  r
}))

cat("\n==== summary ====\n"); print(table(summ$status))
write.csv(summ, file.path(OUT_BASE, "_status.csv"), row.names = FALSE)
cat(sprintf("\n%d task(s); %d OK\n", nrow(summ), sum(summ$status == "OK")))
if (any(summ$status == "ERROR")) quit(status = 1)
