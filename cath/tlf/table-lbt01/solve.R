# Output script for LBT01 — assumes data_setup.R has been sourced first.
#
# Table: LBT01  Antimicrobial Peptide (Cathelicidin) — Value and Change from
# Baseline by Visit (CATH primary efficacy endpoint), Vitamin D3 vs Placebo.
# Descriptive statistics (n, Mean (SD), Median, Min-Max) of the analysis value
# and change from baseline, by parameter and analysis visit, split by treatment.

afun <- function(x, .var, .spl_context, ...) {
  n_fun <- sum(!is.na(x))
  if (n_fun == 0) {
    mean_sd <- c(NA, NA); med <- NA; mnmx <- c(NA, NA)
  } else {
    mean_sd <- c(mean(x, na.rm = TRUE), sd(x, na.rm = TRUE))
    med <- median(x, na.rm = TRUE); mnmx <- c(min(x), max(x))
  }
  is_chg <- .var == "CHG"
  visit_now <- .spl_context$value[which(.spl_context$split == "AVISIT")]
  if (length(visit_now) && visit_now == BL_VISIT && is_chg)
    n_fun <- mean_sd <- med <- mnmx <- NULL

  in_rows(
    "n" = n_fun,
    "Mean (SD)" = mean_sd,
    "Median" = med,
    "Min - Max" = mnmx,
    .formats = list("n" = "xx", "Mean (SD)" = "xx.xx (xx.xxx)",
                    "Median" = "xx.xx", "Min - Max" = "xx.xx - xx.xx"),
    .format_na_strs = list("n" = "NE", "Mean (SD)" = "NE (NE)",
                           "Median" = "NE", "Min - Max" = "NE - NE")
  )
}

lyt <- basic_table(
  title = "Table LBT01: Antimicrobial Peptide (Cathelicidin) — Value and Change from Baseline by Visit",
  subtitles = c("Intent-To-Treat Population — Primary Efficacy Endpoint",
                "Study CATH (Vitamin D3 vs Placebo)"),
  main_footer = "n = number of subjects with a non-missing value. NE = not estimable.",
  show_colcounts = TRUE
) %>%
  split_cols_by("TRT01A") %>%
  split_rows_by("PARAM", label_pos = "topleft", split_label = "Parameter",
                split_fun = drop_split_levels) %>%
  split_rows_by("AVISIT", label_pos = "topleft", split_label = "Analysis Visit",
                split_fun = drop_split_levels) %>%
  split_cols_by_multivar(
    vars = c("AVAL", "CHG"),
    varlabels = c("Value at Visit", "Change from Baseline")
  ) %>%
  analyze_colvars(afun = afun)

result <- build_table(lyt = lyt, df = adlb_f, alt_counts_df = adsl)
result

result1 <- result
