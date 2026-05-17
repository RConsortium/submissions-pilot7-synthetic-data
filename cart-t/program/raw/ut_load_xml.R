## ODM (Operational Data Model) XML loader for OpenClinica data.
##
## R translation of:
##   https://github.com/elong0527/demo-cdisc-yaml/blob/main/src/odm/load.py
##
## Provides:
##   remove_namespaces(xml_content) - strip xmlns declarations and prefixes
##   get_struct_columns(df)         - list-columns that hold per-row attribute records
##   odm_xml_to_df_dict(file_path)  - one row per ItemData; six list-columns
##                                    (study, subject, event, form, item_group, item),
##                                    each holding a named list of attributes
##   odm_xml_to_df(file_path)       - flattened tibble; duplicated attribute names
##                                    receive a "<level>_" prefix, all names lowercased

if (!requireNamespace("xml2",   quietly = TRUE)) stop("Package 'xml2' is required.")
if (!requireNamespace("tibble", quietly = TRUE)) stop("Package 'tibble' is required.")
if (!requireNamespace("tidyr",  quietly = TRUE)) stop("Package 'tidyr' is required.")
if (!requireNamespace("dplyr",  quietly = TRUE)) stop("Package 'dplyr' is required.")


#' Names of list-columns whose elements are named lists (struct-like).
get_struct_columns <- function(df) {
  is_struct <- vapply(
    df,
    function(x) is.list(x) && !is.data.frame(x),
    logical(1)
  )
  names(df)[is_struct]
}


#' Strip XML namespace declarations and prefixes so XPath stays simple.
remove_namespaces <- function(xml_content) {
  xml_content <- gsub('\\s*xmlns[^=]*="[^"]*"',  "", xml_content, perl = TRUE)
  xml_content <- gsub("\\s*xmlns[^=]*='[^']*'",  "", xml_content, perl = TRUE)
  xml_content <- gsub("<([^/>\\s]+:)([^>\\s/]+)",   "<\\2",   xml_content, perl = TRUE)
  xml_content <- gsub("</([^>\\s]+:)([^>\\s]+)",    "</\\2",  xml_content, perl = TRUE)
  xml_content <- gsub("(\\s)([^=\\s]+:)([^=\\s]+)=", "\\1\\3=", xml_content, perl = TRUE)
  xml_content
}


#' Load ODM XML into a tibble with one row per ItemData and six list-columns.
odm_xml_to_df_dict <- function(file_path) {
  file_path <- path.expand(file_path)
  if (!file.exists(file_path)) {
    stop(sprintf("ODM XML file not found: %s", file_path))
  }

  xml_content <- readChar(file_path, file.info(file_path)$size, useBytes = TRUE)
  Encoding(xml_content) <- "UTF-8"
  clean_content <- remove_namespaces(xml_content)
  doc <- xml2::read_xml(clean_content)

  attrs_as_list <- function(node) as.list(xml2::xml_attrs(node))

  ## Walk the ODM hierarchy top-down, mirroring the Python original:
  ##   ClinicalData > SubjectData > StudyEventData >
  ##   FormData    > ItemGroupData > ItemData
  ## Collect one mini-tibble per ItemGroupData, then bind at the end.
  chunks <- list()

  for (clinical_data in xml2::xml_find_all(doc, "./ClinicalData")) {
    study <- attrs_as_list(clinical_data)
    for (subject_data in xml2::xml_find_all(clinical_data, "./SubjectData")) {
      subject <- attrs_as_list(subject_data)
      for (study_event_data in xml2::xml_find_all(subject_data, "./StudyEventData")) {
        event <- attrs_as_list(study_event_data)
        for (form_data in xml2::xml_find_all(study_event_data, "./FormData")) {
          form <- attrs_as_list(form_data)
          for (item_group_data in xml2::xml_find_all(form_data, "./ItemGroupData")) {
            item_group <- attrs_as_list(item_group_data)

            item_nodes <- xml2::xml_find_all(item_group_data, "./ItemData")
            k <- length(item_nodes)
            if (k == 0L) next

            item_records <- lapply(xml2::xml_attrs(item_nodes), as.list)

            chunks[[length(chunks) + 1L]] <- tibble::tibble(
              study      = rep(list(study),      k),
              subject    = rep(list(subject),    k),
              event      = rep(list(event),      k),
              form       = rep(list(form),       k),
              item_group = rep(list(item_group), k),
              item       = item_records
            )
          }
        }
      }
    }
  }

  if (length(chunks) == 0L) {
    return(tibble::tibble(
      study      = list(),
      subject    = list(),
      event      = list(),
      form       = list(),
      item_group = list(),
      item       = list()
    ))
  }

  df <- dplyr::bind_rows(chunks)

  ## Find attribute names that appear in more than one struct column.
  per_col_fields <- lapply(df, function(col) {
    unique(unlist(lapply(col, names), use.names = FALSE))
  })
  all_field_names <- unlist(per_col_fields, use.names = FALSE)
  duplicated_fields <- unique(all_field_names[duplicated(all_field_names)])

  ## Rename: prefix duplicates with the column name; lowercase everything.
  for (col_name in names(df)) {
    df[[col_name]] <- lapply(df[[col_name]], function(rec) {
      if (length(rec) == 0L) return(rec)
      nm <- names(rec)
      new_nm <- ifelse(
        nm %in% duplicated_fields,
        tolower(paste0(col_name, "_", nm)),
        tolower(nm)
      )
      stats::setNames(rec, new_nm)
    })
  }

  df
}


#' Load ODM XML into a flattened tibble, one row per ItemData.
odm_xml_to_df <- function(file_path) {
  df_dict <- odm_xml_to_df_dict(file_path)
  struct_cols <- get_struct_columns(df_dict)

  result <- df_dict
  for (col_name in struct_cols) {
    result <- tidyr::unnest_wider(result, dplyr::all_of(col_name), names_sep = NULL)
  }
  result
}
