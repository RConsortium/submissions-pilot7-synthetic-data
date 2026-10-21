# Rscript --vanilla submission-pilot3/program/adam/r/setup.R
script <- sub("^--file=", "", grep("^--file=", commandArgs(), value = TRUE)[1])
source(file.path(dirname(normalizePath(script)), "common.R"))
dir.create(".r-library", showWarnings = FALSE)
.libPaths(c(file.path(study, ".r-library"), .libPaths()))
for (package in c("arrow", "jsonlite", "yaml")) {
  if (!requireNamespace(package, quietly = TRUE)) {
    install.packages(package, lib = ".r-library",
                     repos = "https://cloud.r-project.org")
  }
}
installed_version <- function() tryCatch(
  as.character(packageVersion("yamaa", lib.loc = .libPaths())),
  error = function(e) NA_character_
)
if (is.na(installed_version()) || installed_version() != "0.5.0") {
  archive <- tempfile(fileext = ".tar.gz")
  download.file(paste0("https://github.com/elong0527/yamaa/releases/download/",
                       "yamaa-v0.5.0/yamaa_0.5.0.tar.gz"), archive, mode = "wb")
  install.packages(archive, lib = ".r-library", repos = NULL, type = "source")
}
stopifnot(installed_version() == "0.5.0")
print(sessionInfo())
