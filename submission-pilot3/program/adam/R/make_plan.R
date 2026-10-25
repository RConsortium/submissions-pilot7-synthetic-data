#!/usr/bin/env Rscript
# Regenerate the ADADAS LOCF planning relation using the rules in make_plan.py.

build <- function(qs_path, ex_path) {
  qs <- arrow::read_parquet(qs_path)
  ex <- arrow::read_parquet(ex_path)
  iso_date <- function(value) {
    date <- as.Date(value, format = "%Y-%m-%d")
    if (any(!is.na(value) & (is.na(date) | format(date, "%Y-%m-%d") != value))) {
      stop("Expected complete ISO dates (YYYY-MM-DD).", call. = FALSE)
    }
    date
  }

  # ISO dates sort chronologically; retain the earliest exposure per subject.
  ex <- ex[order(ex$EXSTDTC, na.last = TRUE, method = "radix"), ]
  trtsdt <- ex[!duplicated(ex$USUBJID), c("USUBJID", "EXSTDTC")]
  subjects <- sort(trtsdt$USUBJID, method = "radix")

  actot <- qs[which(qs$QSTESTCD == "ACTOT"), c("USUBJID", "QSDTC")]
  start <- iso_date(trtsdt$EXSTDTC)
  ady <- as.integer(iso_date(actot$QSDTC) -
    start[match(actot$USUBJID, trtsdt$USUBJID)]) + 1L
  actot$AVISIT <- ifelse(!is.na(ady) & ady <= 1, "Baseline",
    ifelse(!is.na(ady) & ady <= 84, "Week 8",
      ifelse(!is.na(ady) & ady <= 140, "Week 16", "Week 24")))

  expected <- data.frame(
    USUBJID = rep(subjects, each = 3L),
    PARAMCD = rep("ACTOT", length(subjects) * 3L),
    AVISIT = rep(c("Week 8", "Week 16", "Week 24"), length(subjects)),
    AVISITN = rep(c(8L, 16L, 24L), length(subjects))
  )
  collected <- unique(actot[c("USUBJID", "AVISIT")])
  collected$COLLECTED <- rep(TRUE, nrow(collected))
  plan <- merge(expected, collected, by = c("USUBJID", "AVISIT"),
    all.x = TRUE, sort = FALSE)
  plan <- plan[is.na(plan$COLLECTED), names(expected)]
  plan <- plan[order(plan$USUBJID, plan$AVISITN, method = "radix"), ]

  paste0("USUBJID,PARAMCD,AVISIT,AVISITN\n", paste0(sprintf("%s,%s,%s,%d\n",
    plan$USUBJID, plan$PARAMCD, plan$AVISIT, plan$AVISITN), collapse = ""))
}

main <- function() {
  args <- commandArgs(trailingOnly = TRUE)
  usage <- "Usage: Rscript make_plan.R [--qs PATH] [--ex PATH] [--out PATH]\n"
  if (any(args %in% c("--help", "-h"))) {
    cat(usage)
    return(invisible(NULL))
  }
  script <- sub("^--file=", "", grep("^--file=",
    commandArgs(trailingOnly = FALSE), value = TRUE))
  study <- normalizePath(file.path(dirname(script), "../../.."), mustWork = TRUE)
  paths <- list(
    qs = file.path(study, "data/sdtm/qs.parquet"),
    ex = file.path(study, "data/sdtm/ex.parquet"),
    out = file.path(study, "data/mapping/plan.csv")
  )
  if (length(args) %% 2L != 0L) stop(usage, call. = FALSE)
  for (i in seq_len(length(args) / 2L)) {
    option <- args[2L * i - 1L]
    if (!option %in% paste0("--", names(paths))) stop(usage, call. = FALSE)
    paths[[substring(option, 3L)]] <- args[2L * i]
  }
  writeBin(charToRaw(enc2utf8(build(paths$qs, paths$ex))), paths$out)
}

if (sys.nframe() == 0L) main()
