# Output script for RST01 — assumes data_setup.R has been sourced first.
#
# Table: RST01  Birmingham Vasculitis Activity Score (BVAS/WG) by Visit
# Descriptive statistics (n, Mean (SD), Median, Min-Max) of the disease-activity
# score by analysis visit, split by treatment (Control vs Rituximab). Value-only
# (RS has no pre-treatment baseline record — see data_setup.R).

lyt <- basic_table(
  title = "Table RST01: Birmingham Vasculitis Activity Score (BVAS/WG) by Visit",
  subtitles = c("Intent-To-Treat Population — Disease Activity",
                "Study RAVE (Rituximab vs Cyclophosphamide, ANCA-Associated Vasculitis)"),
  main_footer = "n = number of subjects with a non-missing score at the visit.",
  show_colcounts = TRUE
) %>%
  split_cols_by("TRT01A") %>%
  split_rows_by("AVISIT", label_pos = "topleft", split_label = "Analysis Visit",
                split_fun = drop_split_levels) %>%
  analyze_vars(
    vars = "AVAL",
    .stats = c("n", "mean_sd", "median", "range"),
    .labels = c(n = "n", mean_sd = "Mean (SD)", median = "Median", range = "Min - Max"),
    .formats = c(n = "xx", mean_sd = "xx.x (xx.xx)", median = "xx.x", range = "xx.x - xx.x")
  )

result <- build_table(lyt = lyt, df = adrs_f, alt_counts_df = adsl)
result

result1 <- result
