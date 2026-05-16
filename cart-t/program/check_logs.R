## --------------------------------------------------------------------
## check_logs.R — scan every logrx log file under logs/ and summarise
##                errors, warnings, output, and run time.
##
## Run from project root:  Rscript program/check_logs.R
##
## Console: pass/fail line per log + detail block for any log that has
##          errors or warnings.
## File:    logs/_summary.md (markdown report) overwritten each run.
## --------------------------------------------------------------------

suppressPackageStartupMessages({
  library(dplyr)
  library(stringr)
})

log_root <- "logs"
log_files <- list.files(log_root, pattern = "\\.log$",
                        recursive = TRUE, full.names = TRUE)

if (length(log_files) == 0L) {
  cat("No log files under", log_root, "— nothing to summarise.\n")
  quit(save = "no")
}

## logrx splits the log into sections delimited by 80-char dash lines, with
## the section title centered on a line in between (also `-`-padded). Sections
## relevant here:
##   "Errors and Warnings"         -> contains Errors: and Warnings: blocks
##   "Messages, Output, and Result"-> contains Messages:, Output:, Result:
##   "Program Run Time Information"-> contains start time, end time, etc.
parse_log <- function(path) {
  lines <- readLines(path, warn = FALSE)

  ## Find section header lines: e.g. "- <Title> -" between two long dash rows.
  header_re <- "^-\\s+(.*?)\\s+-\\s*$"
  is_div    <- grepl("^-{60,}$", lines)
  is_hdr    <- grepl(header_re, lines) & !is_div

  hdr_idx   <- which(is_hdr)
  hdr_title <- str_trim(str_match(lines[hdr_idx], header_re)[, 2])
  hdr_end   <- c(hdr_idx[-1] - 1L, length(lines))

  ## Index sections by their title for easy lookup.
  section <- function(name) {
    j <- which(hdr_title == name)
    if (length(j) == 0L) return(character(0))
    body <- lines[(hdr_idx[j] + 1L):hdr_end[j]]
    body <- body[!grepl("^-{60,}$", body)]
    body
  }

  ## Within "Errors and Warnings": Errors: <text>  / Warnings: <text>
  ew <- section("Errors and Warnings")
  i_err  <- which(ew == "Errors:")
  i_warn <- which(ew == "Warnings:")
  errors_txt   <- if (length(i_err)  && length(i_warn) && i_warn > i_err)
                    paste(ew[(i_err + 1L):(i_warn - 1L)], collapse = "\n") else ""
  warnings_txt <- if (length(i_warn))
                    paste(ew[(i_warn + 1L):length(ew)], collapse = "\n") else ""

  ## Within "Messages, Output, and Result"
  mor <- section("Messages, Output, and Result")
  i_msg <- which(mor == "Messages:")
  i_out <- which(mor == "Output:")
  i_res <- which(mor == "Result:")
  messages_txt <- if (length(i_msg) && length(i_out))
                    paste(mor[(i_msg + 1L):(i_out - 1L)], collapse = "\n") else ""
  output_txt   <- if (length(i_out) && length(i_res))
                    paste(mor[(i_out + 1L):(i_res - 1L)], collapse = "\n") else ""

  ## Run time (if logrx wrote it)
  rt  <- section("Program Run Time Information")
  start_time <- str_trim(sub(".*?:", "", grep("^Start time", rt, value = TRUE)[1]))
  end_time   <- str_trim(sub(".*?:", "", grep("^End time",   rt, value = TRUE)[1]))
  run_time   <- str_trim(sub(".*?:", "", grep("^Run time",   rt, value = TRUE)[1]))

  ## "errors" is non-empty content beyond whitespace/tabs.
  has_content <- function(s) nzchar(str_trim(gsub("[[:space:]]", "", s)))

  n_warn <- if (has_content(warnings_txt))
              max(1L, as.integer(str_match(warnings_txt, "(\\d+) warning")[1, 2] %||% NA_integer_), na.rm = TRUE)
            else 0L
  if (is.na(n_warn) || length(n_warn) == 0L) n_warn <- 0L
  status <- dplyr::case_when(
    has_content(errors_txt)   ~ "ERROR",
    n_warn > 0L               ~ "WARN",
    has_content(warnings_txt) ~ "WARN",
    TRUE                      ~ "CLEAN"
  )

  tibble::tibble(
    path        = path,
    area        = basename(dirname(path)),
    program     = sub("\\.log$", "", basename(path)),
    status      = status,
    n_warnings  = n_warn,
    output      = str_trim(output_txt),
    messages    = str_trim(messages_txt),
    errors      = str_trim(errors_txt),
    warnings    = str_trim(warnings_txt),
    start_time  = start_time %||% NA_character_,
    end_time    = end_time %||% NA_character_,
    run_time    = run_time %||% NA_character_
  )
}

## Tiny null-coalesce since base R doesn't ship one until 4.4.
`%||%` <- function(a, b) if (is.null(a) || (length(a) == 1L && is.na(a))) b else a

summary_tbl <- bind_rows(lapply(log_files, parse_log)) |>
  arrange(area, program)

## ---- Console report -----------------------------------------------------
cat("=== logrx scan ===\n")
cat(sprintf("logs scanned: %d   clean: %d   warn: %d   error: %d\n",
            nrow(summary_tbl),
            sum(summary_tbl$status == "CLEAN"),
            sum(summary_tbl$status == "WARN"),
            sum(summary_tbl$status == "ERROR")))
cat("\n")

print(
  summary_tbl |>
    transmute(area, program, status,
              warnings = n_warnings,
              output_snippet = str_trunc(gsub("\\s+", " ", output), 60),
              run_time),
  n = Inf
)

problem_rows <- summary_tbl |> filter(status != "CLEAN")
if (nrow(problem_rows) > 0L) {
  cat("\n--- Detail for non-CLEAN logs ---\n")
  for (i in seq_len(nrow(problem_rows))) {
    r <- problem_rows[i, ]
    cat(sprintf("\n[%s] %s/%s\n", r$status, r$area, r$program))
    if (nzchar(r$errors))   cat("  Errors:\n", paste0("    ", strsplit(r$errors,   "\n")[[1]], collapse = "\n"), "\n", sep = "")
    if (nzchar(r$warnings)) cat("  Warnings (first 12 lines):\n",
                                paste0("    ", head(strsplit(r$warnings, "\n")[[1]], 12), collapse = "\n"), "\n", sep = "")
  }
}

## ---- Markdown report ----------------------------------------------------
md_path <- file.path(log_root, "_summary.md")
md <- c(
  "# Log Summary",
  "",
  sprintf("Generated %s.", format(Sys.time(), "%Y-%m-%d %H:%M:%S")),
  "",
  sprintf("- Logs scanned: %d", nrow(summary_tbl)),
  sprintf("- Clean: %d", sum(summary_tbl$status == "CLEAN")),
  sprintf("- Warn:  %d", sum(summary_tbl$status == "WARN")),
  sprintf("- Error: %d", sum(summary_tbl$status == "ERROR")),
  "",
  "## Table",
  "",
  "| Area | Program | Status | Warnings | Output | Run time |",
  "|---|---|---|---|---|---|",
  sprintf("| %s | %s | %s | %d | %s | %s |",
          summary_tbl$area, summary_tbl$program, summary_tbl$status,
          summary_tbl$n_warnings,
          str_trunc(gsub("\\s+", " ", summary_tbl$output), 70),
          coalesce(summary_tbl$run_time, ""))
)

if (nrow(problem_rows) > 0L) {
  md <- c(md, "", "## Details for non-CLEAN logs")
  for (i in seq_len(nrow(problem_rows))) {
    r <- problem_rows[i, ]
    md <- c(md, "",
            sprintf("### `%s/%s` — %s", r$area, r$program, r$status))
    if (nzchar(r$errors)) {
      md <- c(md, "", "**Errors:**", "", "```", r$errors, "```")
    }
    if (nzchar(r$warnings)) {
      md <- c(md, "", "**Warnings (first 30 lines):**", "", "```",
              head(strsplit(r$warnings, "\n")[[1]], 30), "```")
    }
  }
}

writeLines(md, md_path)
cat(sprintf("\nMarkdown report: %s\n", md_path))
