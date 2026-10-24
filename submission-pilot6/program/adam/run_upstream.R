# Bootstrap an upstream program in a fresh R process. No references are loaded.
args <- commandArgs(trailingOnly = TRUE)
renv::load(project = Sys.getenv("PILOT6_RENV_PROJECT"), quiet = TRUE)
source(".Rprofile")
library(metatools)
library(xportr)
source(file.path(path$utils, "save_dataset_json.r"))
source(file.path("code", "adam", args[[1]]), chdir = FALSE)
