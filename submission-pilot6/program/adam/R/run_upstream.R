# Bootstrap an upstream program in a fresh R process. No references are loaded.
args <- commandArgs(trailingOnly = TRUE)
renv::load(project = Sys.getenv("PILOT6_RENV_PROJECT"), quiet = TRUE)
source(".Rprofile")
library(metatools)
library(xportr)
source(file.path(path$utils, "save_dataset_json.r"))
# The native reader already returns decimal/float columns as numeric. Keep the
# legacy argument used by the unchanged upstream programs without losing precision.
read_dataset_json <- function(file, decimals_as_floats = TRUE) {
  if (!isTRUE(decimals_as_floats)) {
    stop("This workflow reads staged numeric columns as floating-point values.")
  }
  datasetjson::read_dataset_json(file)
}
source(file.path("code", "adam", args[[1]]), chdir = FALSE)
