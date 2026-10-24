# ============================================================================
# Program: save_dataset_json.r
# Purpose: Save a dataset in Dataset-JSON format
# Description: Saves a dataset in Dataset-JSON format using
#              the provided metadata specification.
# Input: None
# Output: JSON file saved to the specified output directory
# ============================================================================

library(dplyr)
library(datasetjson) # Dataset JSON handling
library(metacore) # Metadata handling

#' Save a dataset in Dataset-JSON format
#'
#' This function saves a dataset in Dataset-JSON format using the provided metadata specification.
#' @param output_dir Character string specifying the output directory where the JSON file will be saved.
#' @param dataset Data frame containing the dataset to be saved.
#' @param ds_spec Metacore object with the dataset specification (use select_dataset on the metacore spec).
#' @param study (Optional) List containing study metadata such as name and originator. If not specified,
#' the global study list will be used.
#' @return None. The function writes a JSON file to the specified output directory.
#' @examples
#' \dontrun{
#' # Assuming `advs_spec` is a metacore object for the ADVS dataset
#' save_dataset_json("data/adam", advs_data, advs_spec)
#' }
save_dataset_json <- function(output_dir, dataset, ds_spec, study = NULL) {
  # Check parameters
  if (!is.character(output_dir)) {
    stop("Parameter 'output_dir' must be a character string.")
  }
  if (!is.data.frame(dataset)) {
    stop("Parameter 'dataset' must be a data frame.")
  }
  if (is.null(ds_spec$ds_vars) || is.null(ds_spec$var_spec) || is.null(ds_spec$ds_spec)) {
    stop("Parameter 'ds_spec' must be a metacore dataset specification.")
  }

  # Get study from the global environment if not provided
  if (is.null(study)) {
    study <- get("study", envir = .GlobalEnv)
  } else {
    study <- list(
      name = "",
      originator = "",
      metadata_version = "",
      metadata_ref = ""
    )
  }

  ds_dataset <- ds_spec$ds_spec[["dataset"]]
  ds_name <- as.character(ds_dataset)[1]

  # Select variables as per spec
  dataset_final <- dataset %>%
    dplyr::select(
      ds_spec$ds_vars$variable
    )

  oid_cols <- ds_spec$ds_vars %>%
    select(.data$dataset, .data$variable, .data$key_seq) %>%
    left_join(ds_spec$var_spec, by = c("variable")) %>%
    rename(name = .data$variable, dataType = .data$type, keySequence = .data$key_seq, displayFormat = .data$format) %>%
    mutate(itemOID = paste0("IT.", .data$dataset, ".", .data$name)) %>%
    select(
      .data$itemOID, .data$name, .data$label, .data$dataType,
      .data$length, .data$keySequence, .data$displayFormat
    ) %>%
    mutate(
      dataType =
        case_when(
          displayFormat == "DATE9." ~ "date",
          displayFormat == "DATETIME20." ~ "datetime",
          substr(name, nchar(name) - 3 + 1, nchar(name)) == "DTC" & length == "8" ~ "date",
          substr(name, nchar(name) - 3 + 1, nchar(name)) == "DTC" & length == "20" ~ "datetime",
          dataType == "text" ~ "string",
          .default = as.character(.data$dataType)
        ),
      targetDataType =
        case_when(
          displayFormat == "DATE9." ~ "integer",
          displayFormat == "DATETIME20." ~ "integer",
          .default = NA
        ),
      length = case_when(
        dataType == "string" ~ length,
        .default = NA
      )
    ) %>%
    data.frame()

  dataset_json(
    dataset_final,
    last_modified = strftime(as.POSIXlt(Sys.time(), "UTC"), "%Y-%m-%dT%H:%M"),
    originator = study$originator,
    sys = paste0("R on ", R.Version()$os, " ", unname(Sys.info())[[2]]),
    sys_version = R.Version()$version.string,
    version = "1.1.0",
    study = study$name,
    metadata_version = study$metadata_version,
    metadata_ref = study$metadata_ref,
    item_oid = paste0("IG.", toupper(ds_name)),
    name = toupper(ds_name),
    dataset_label = ds_spec$ds_spec[["label"]],
    file_oid = file.path(path$adam, ds_name),
    columns = oid_cols
  ) %>%
    write_dataset_json(file = file.path(output_dir, paste0(tolower(ds_name), ".json")))
}
