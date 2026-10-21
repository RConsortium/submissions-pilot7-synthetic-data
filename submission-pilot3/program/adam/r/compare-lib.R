# Independent comparison of every reference cell, with explicit identities.
row_identity <- function(x, columns) {
  # Length-prefixed values avoid delimiter collisions without content hashing.
  tokens <- lapply(x[columns], function(z) {
    text <- if (inherits(z, "Date")) as.character(z) else if (is.numeric(z)) {
      sprintf("%.17g", z)
    } else as.character(z)
    ifelse(is.na(z), "M;", paste0("V", nchar(text, type = "bytes"), ":", text, ";"))
  })
  do.call(paste0, tokens)
}

logical_type <- function(x) {
  if (inherits(x, "Date")) "date" else if (is.numeric(x)) "numeric" else {
    paste(class(x), collapse = "/")
  }
}

compare_frames <- function(output, reference, key, tolerance = 1e-10) {
  total <- nrow(reference) * ncol(reference)
  result <- list(reference_rows = nrow(reference),
                 reference_columns = ncol(reference), reference_cells = total,
                 exact = 0, tolerance_only = 0, blank_null_only = 0,
                 different = 0, uncompared = total,
                 missing_rows = nrow(reference), extra_rows = nrow(output),
                 missing_columns = length(setdiff(names(reference), names(output))),
                 extra_columns = length(setdiff(names(output), names(reference))),
                 duplicate_reference_keys = 0, duplicate_output_keys = 0,
                 column_order = identical(names(output), names(reference)),
                 row_order = FALSE, logical_type_issues = 0)
  if (!all(key %in% names(reference)) || !all(key %in% names(output))) {
    result$key_columns_missing <- TRUE
    return(result)
  }
  kr <- row_identity(reference, key)
  ko <- row_identity(output, key)
  result$duplicate_reference_keys <- sum(duplicated(kr))
  result$duplicate_output_keys <- sum(duplicated(ko))
  result$missing_rows <- sum(!kr %in% ko)
  result$extra_rows <- sum(!ko %in% kr)
  result$row_order <- identical(kr, ko)
  if (result$duplicate_reference_keys || result$duplicate_output_keys) return(result)
  index <- match(kr, ko)
  present <- !is.na(index)
  result$uncompared <- 0
  for (name in names(reference)) {
    if (!name %in% names(output)) {
      result$uncompared <- result$uncompared + nrow(reference)
      next
    }
    a <- output[[name]][index]
    b <- reference[[name]]
    result$logical_type_issues <- result$logical_type_issues +
      !identical(logical_type(a), logical_type(b))
    both_missing <- is.na(a) & is.na(b) & (is.nan(a) == is.nan(b))
    exact <- present & (both_missing | (!is.na(a) & !is.na(b) & a == b))
    exact[is.na(exact)] <- FALSE
    close <- blank <- rep(FALSE, nrow(reference))
    if (is.numeric(a) && is.numeric(b) && !inherits(a, "Date")) {
      delta <- abs(a - b)
      close <- present & !exact & !is.na(delta) & delta <= tolerance
    }
    if (is.character(a) && is.character(b)) {
      blank <- present & !exact & ((is.na(a) & b == "") | (a == "" & is.na(b)))
      blank[is.na(blank)] <- FALSE
    }
    result$exact <- result$exact + sum(exact)
    result$tolerance_only <- result$tolerance_only + sum(close)
    result$blank_null_only <- result$blank_null_only + sum(blank)
    result$different <- result$different + sum(present & !(exact | close | blank))
    result$uncompared <- result$uncompared + sum(!present)
  }
  stopifnot(sum(unlist(result[c("exact", "tolerance_only", "blank_null_only",
                                "different", "uncompared")])) == total)
  result
}

data_matches <- function(result, allow_blank = FALSE, require_order = FALSE) {
  !isTRUE(result$key_columns_missing) &&
    result$different == 0 && result$uncompared == 0 &&
    result$missing_rows == 0 && result$extra_rows == 0 &&
    result$missing_columns == 0 && result$extra_columns == 0 &&
    result$duplicate_reference_keys == 0 && result$duplicate_output_keys == 0 &&
    result$logical_type_issues == 0 && result$column_order &&
    (allow_blank || result$blank_null_only == 0) &&
    (!require_order || result$row_order)
}
