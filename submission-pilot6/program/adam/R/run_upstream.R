# Bootstrap an upstream program in a fresh R process. No references are loaded.
args <- commandArgs(trailingOnly = TRUE)
renv::load(project = Sys.getenv("PILOT6_RENV_PROJECT"), quiet = TRUE)
source(".Rprofile")
library(metatools)
library(xportr)
source(file.path(path$utils, "save_dataset_json.r"))
# Upstream used datasetjson 0.3.0. Its reader returned decimal columns as text
# unless decimals_as_floats = TRUE, and adlbh.r relies on that default. The
# native reader always returns numbers, so rebuild the 0.3.0 text: upstream's
# SDTM files hold format(x, digits = 16), padded NA included. `[]<-` keeps labels.
read_dataset_json <- function(file, decimals_as_floats = FALSE) {
  x <- datasetjson::read_dataset_json(file)
  if (!isTRUE(decimals_as_floats)) {
    for (column in attr(x, "columns")) {
      if (identical(column$dataType, "decimal")) {
        x[[column$name]][] <- format(x[[column$name]], digits = 16)
      }
    }
  }
  x
}
# The references were written by datasetjson 0.3.0, whose yyjsonr writer stored
# Inf as null; the native 0.4 writer rejects it (NaN is already null). Write Inf
# as null again, e.g. ADLBH ratios to a zero lower limit. Finite values are unchanged.
write_dataset_json <- function(x, ...) {
  for (name in names(x)) {
    if (is.double(x[[name]])) x[[name]][is.infinite(x[[name]])] <- NA_real_
  }
  datasetjson::write_dataset_json(x, ...)
}
source(file.path("code", "adam", args[[1]]), chdir = FALSE)
