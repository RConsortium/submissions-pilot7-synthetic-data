# Rscript --vanilla submission-pilot3/program/adam/r/compare.R
script <- sub("^--file=", "", grep("^--file=", commandArgs(), value = TRUE)[1])
source(file.path(dirname(normalizePath(script)), "common.R"))
source("program/adam/r/compare-lib.R")
dir.create("log", recursive = TRUE, showWarnings = FALSE)
started <- proc.time()[["elapsed"]]
require_order <- "--require-row-order" %in% commandArgs(trailingOnly = TRUE)
results <- list()
for (stage in c("raw", "exported")) for (name in datasets) {
  reference <- arrow::read_parquet(file.path("data/adam", paste0(name, ".parquet")),
                                  as_data_frame = FALSE)
  path <- file.path("data/adam", paste0(name, if (stage == "raw")
                    "-yamaa-raw.parquet" else "-yamaa.parquet"))
  ref <- as.data.frame(reference)
  if (!file.exists(path)) {
    results[[paste(stage, name)]] <- list(stage = stage, dataset = name,
      status = "blocked", reference_cells = nrow(ref) * ncol(ref), exact = 0,
      uncompared = nrow(ref) * ncol(ref), ok = FALSE)
    next
  }
  output <- arrow::read_parquet(path, as_data_frame = FALSE)
  result <- compare_frames(as.data.frame(output), ref, keys[[name]])
  labels <- setNames(lapply(output$schema$fields,
                            function(f) f$metadata[["yamaa:label"]]), names(output))
  result$persisted_label_issues <- sum(vapply(reference$schema$fields, function(f) {
    !identical(labels[[f$name]], f$metadata[["yamaa:label"]])
  }, logical(1)))
  result$stage <- stage
  result$dataset <- name
  result$status <- "compared"
  result$ok <- data_matches(result, allow_blank = stage == "raw",
                            require_order = require_order) &&
    (stage == "raw" || result$persisted_label_issues == 0)
  results[[paste(stage, name)]] <- result
  cat(sprintf("%s %s: %d/%d exact; tolerance=%d blank/null=%d; order=%s labels=%d\n",
              stage, toupper(name), result$exact, result$reference_cells,
              result$tolerance_only, result$blank_null_only,
              result$row_order, result$persisted_label_issues))
}
jsonlite::write_json(list(datasets = results, numeric_absolute_tolerance = 1e-10,
                         require_row_order = require_order,
                         seconds = proc.time()[["elapsed"]] - started),
                    "log/yamaa-comparison.json", auto_unbox = TRUE, pretty = TRUE)
exported <- results[vapply(results, function(x) x$stage == "exported", logical(1))]
if (!all(vapply(exported, function(x) x$ok, logical(1)))) {
  stop("Exported comparison failed; see log/yamaa-comparison.json")
}
cat("All five exported datasets match by record identity and variable labels.\n")
