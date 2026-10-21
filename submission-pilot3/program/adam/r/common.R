# Shared paths and explicit export conventions for the Pilot 3 workflow.
script <- sub("^--file=", "", grep("^--file=", commandArgs(), value = TRUE)[1])
study <- normalizePath(file.path(dirname(normalizePath(script)), "../../.."))
setwd(study)
.libPaths(c(file.path(study, ".r-library"), .libPaths()))
datasets <- c("adsl", "adae", "adadas", "adtte", "adlbc")
keys <- list(
  adsl = c("STUDYID", "USUBJID"),
  adae = c("STUDYID", "USUBJID", "AESEQ"),
  adadas = c("STUDYID", "USUBJID", "PARAMCD", "AVISIT", "ADT"),
  adtte = c("STUDYID", "USUBJID"),
  adlbc = c("STUDYID", "USUBJID", "PARAMCD", "AVISIT", "LBSEQ")
)

read_spec <- function(name) yaml::read_yaml(
  file.path("spec/yamaa", paste0(name, ".yaml")),
  handlers = list(
    "bool#yes" = function(x) if (x == "true") TRUE else x,
    "bool#no" = function(x) if (x == "false") FALSE else x
  )
)

write_log <- function(x, path) {
  jsonlite::write_json(x, paste0(path, ".json"), dataframe = "rows",
                       auto_unbox = TRUE, pretty = TRUE)
  for (nm in names(x)) if (is.list(x[[nm]])) {
    x[[nm]] <- vapply(x[[nm]], jsonlite::toJSON, character(1),
                      auto_unbox = TRUE)
  }
  write.csv(x, paste0(path, ".csv"), row.names = FALSE)
}

publish <- function() {
  # No reference data or reference labels are read. The raw engine artifacts
  # remain available; this explicit export applies the study's XPT-derived
  # blank-character convention and the labels declared in each specification.
  for (name in datasets) {
    raw <- arrow::read_parquet(
      file.path("data/adam", paste0(name, "-yamaa-raw.parquet")),
      as_data_frame = FALSE
    )
    spec <- read_spec(name)
    labels <- setNames(lapply(spec$columns, function(x) x$label),
                       vapply(spec$columns, function(x) x$name, character(1)))
    values <- as.data.frame(raw)
    for (nm in names(values)) if (is.character(values[[nm]])) {
      values[[nm]][is.na(values[[nm]])] <- ""
    }
    fields <- lapply(raw$schema$fields, function(f) {
      arrow::field(f$name, f$type, nullable = f$nullable,
                   metadata = list("yamaa:label" = labels[[f$name]]))
    })
    output <- arrow::Table$create(values, schema = do.call(arrow::schema, fields))
    arrow::write_parquet(output,
                        file.path("data/adam", paste0(name, "-yamaa.parquet")))
  }
}
