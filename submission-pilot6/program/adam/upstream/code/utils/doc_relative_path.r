# ============================================================================
# Program: doc_relative_path.r
# Purpose: Get relative path of the program for output footnote
# Description: This utility function gets a path for the program relative
#              to the git root folder
# Input: None
# Output: character string with a relative path
# ============================================================================

# We are using docorator doc_path function to avoid duplication of code
# as there is no simple way to get the path of the current script in R.
library(docorator)

#' Get the relative path of the current script
#'
#' @param filename Name of the file passed to docorator doc_path function. If NULL, it will use the current script.
#' @param path program path passed to docorator doc_path function. If NULL, it will use the current script path.
#'
#' This function returns the path of the current script relative to the git root folder.
#' @return Character string with the relative path of the current script.
#' @examples
#' \dontrun{
#' # Get the relative path of the current script
#' doc_relative_path()
#' }
doc_relative_path <- function(filename = NULL, path = NULL) {
  # Get the absolute path of the current script
  absolute_path <- doc_path(filename, path)

  # Get the root directory of the git repository
  git_root <- system("git rev-parse --show-toplevel", intern = TRUE)

  # Calculate the relative path
  relative_path <- sub(paste0("^", git_root, "/"), "", absolute_path)

  relative_path
}
