# Rscript --vanilla submission-pilot3/program/adam/r/run.R
script <- sub("^--file=", "", grep("^--file=", commandArgs(), value = TRUE)[1])
source(file.path(dirname(normalizePath(script)), "common.R"))
stopifnot(as.character(packageVersion("yamaa")) == "0.5.0")
dir.create("log", recursive = TRUE, showWarnings = FALSE)
writeLines(capture.output(sessionInfo()), "log/yamaa-session-info.txt")
# A failed attempt must not leave previous exported files looking current.
unlink(file.path("data/adam", paste0(datasets, "-yamaa.parquet")))
started <- proc.time()[["elapsed"]]
run <- yamaa::yamaa_project("project.yaml")$run("adam")
write_log(run$issues, "log/yamaa-issues")
write_log(run$report, "log/yamaa-report")
if (nrow(run$issues)) stop("Project run has issues; see log/yamaa-issues.json")
tryCatch(run$save(), error = function(e) {
  if (!is.null(e$issues)) write_log(e$issues, "log/yamaa-issues")
  stop(e)
})
engine_seconds <- proc.time()[["elapsed"]] - started
publish()
jsonlite::write_json(list(engine_and_save_seconds = engine_seconds,
                         total_seconds = proc.time()[["elapsed"]] - started),
                    "log/yamaa-timing.json", auto_unbox = TRUE, pretty = TRUE)
cat("Built and exported", length(run$names), "datasets with zero issues.\n")
