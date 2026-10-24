# ============================================================================
# Program: compare_data.r
# Purpose: Compare two files passed as arguments
# Description: Compares two files and prints the differences between them.
# Input: Two file paths
# Output: Differences between the files
# ============================================================================

# ----------------------------------------------------------------------------
# SETUP AND LIBRARY LOADING
# ----------------------------------------------------------------------------

# Load required packages
library(diffdf) # Data frame comparison
library(datasetjson) # Reading Dataset-JSON

# ----------------------------------------------------------------------------
# CHECKS
# ----------------------------------------------------------------------------

args <- commandArgs(trailingOnly = TRUE)
if (length(args) != 2) {
  cat("Usage: Rscript compare_data.r <file1> <file2>\n")
  quit(status = 1)
}

# ----------------------------------------------------------------------------
# LOAD DATASETS
# ----------------------------------------------------------------------------

base <- read_dataset_json(args[1])
compare <- read_dataset_json(args[2])

# ----------------------------------------------------------------------------
# COMPARE DATASETS
# ----------------------------------------------------------------------------

# Compare the datasets and print differences
if (identical(base, compare)) {
  cat("The datasets are identical.\n")
} else {
  cat("The datasets differ.\n")
  # You can add more detailed comparison logic here, such as comparing specific columns or rows
  diff <- diffdf(base, compare)
  print(diff)
}
