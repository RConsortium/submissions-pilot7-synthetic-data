# Output script for AET02 — assumes data_setup.R has been sourced first.
#
# Table: AET02  Adverse Events by System Organ Class and Preferred Term
# Counts of subjects with >=1 treatment-emergent AE (and event counts), by
# treatment, summarized at the SOC level and counted at the Preferred Term level.

# ---- variant1 ----
lbls <- c(unique = "Total number of patients with at least one adverse event",
          nonunique = "Total number of adverse events")

lyt <- basic_table(
  title = "Table AET02: Adverse Events by System Organ Class and Preferred Term",
  subtitles = c("Safety Population — Treatment-Emergent Adverse Events",
                "Study ARA06 (Anti-TNF Agents in Rheumatoid Arthritis)"),
  main_footer = "Treatment-emergent = onset on or after first dose. n = number of subjects.",
  show_colcounts = TRUE
) %>%
  split_cols_by("TRT01A") %>%
  add_overall_col("All Patients") %>%
  analyze_num_patients(
    vars = "USUBJID", .stats = c("unique", "nonunique"), .labels = lbls
  ) %>%
  split_rows_by(
    "AEBODSYS", child_labels = "visible", nested = FALSE,
    split_fun = drop_split_levels, label_pos = "topleft",
    split_label = "MedDRA System Organ Class"
  ) %>%
  summarize_num_patients(
    var = "USUBJID", .stats = c("unique", "nonunique"), .labels = lbls
  ) %>%
  count_occurrences(vars = "AEDECOD", .indent_mods = -1L)

result <- build_table(lyt = lyt, df = adae, alt_counts_df = adsl) %>%
  sort_at_path(path = c("AEBODSYS", "*", "AEDECOD"),
               scorefun = score_occurrences)
result

result1 <- result
