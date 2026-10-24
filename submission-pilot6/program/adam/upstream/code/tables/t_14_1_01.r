#************************************************************************
# Purpose:     Generate Table 14.1.1 - Summary of Populations
# Input:       ADSL
# Output:      t14_1_1.pdf
#************************************************************************

# Note to Reviewer
# To rerun the code below, please refer ADRG appendix.
# After required package are installed, the path variable needs to be defined
# in the .Rprofile file

# Load required packages
library(dplyr)
library(datasetjson)
library(cards)
library(gtsummary)
library(gt)
library(docorator)
library(stringr)

# Import utility functions
source(file.path("code", "utils", "doc_relative_path.r"))

# ----------------------------------------------------------------------------
# Load datasets
# ----------------------------------------------------------------------------

# Local helper to replace blank strings with NA
convert_blanks_to_na_local <- function(df) {
  df %>%
    mutate(across(where(is.character), ~ na_if(.x, "")))
}

adsl <- read_dataset_json(file.path(path$adam, "adsl.json")) %>%
  convert_blanks_to_na_local() %>%
  rename_with(tolower)

# ----------------------------------------------------------------------------
# Prepare data
# ----------------------------------------------------------------------------

# Define treatment groups
trt_levels <- c(
  "Placebo",
  "Xanomeline Low Dose",
  "Xanomeline High Dose",
  "Total"
)

# Define population labels
population_def <- tribble(
  ~population_id, ~population_label,
  "ittfl", "Intent-To-Treat (ITT)",
  "saffl", "Safety",
  "efffl", "Efficacy",
  "comp24fl", "Completer Week 24",
  "complfl", "Complete Study"
)

# Add total treatment group
adsl_total <- bind_rows(
  adsl,
  adsl %>% mutate(trt01p = "Total")
) %>%
  mutate(trt01p = factor(as.character(trt01p), levels = trt_levels))

# ----------------------------------------------------------------------------
# Get table summary data
# ----------------------------------------------------------------------------

# Create summary table using gtsummary
t_14_1_01 <- adsl_total %>%
  tbl_summary(
    by = trt01p,
    statistic = list(all_dichotomous() ~ "{n} ({p}%)"),
    include = all_of(population_def$population_id),
    value = list(all_of(population_def$population_id) ~ "Y"),
    digits = list(
      all_dichotomous() ~ list(
        p = label_style_percent(digits = 0, width = 3, justify = "right")
      )
    ),
    label = as.list(population_def$population_label) %>% setNames(population_def$population_id)
  ) %>%
  modify_header(label = "") %>%
  modify_header(all_stat_cols() ~ "**{level}**  \n(N={n})") %>%
  remove_footnote_header(columns = all_stat_cols())

# Additional alignments

# ----------------------------------------------------------------------------
# Output data
# ----------------------------------------------------------------------------

# Convert gtsummary object to ARD format
t_14_1_01_ard <- gather_ard(t_14_1_01)

# Save ARD as RDS
saveRDS(t_14_1_01_ard, file.path(path$table_ard, "t_14_1_01.rds"))

# Save as PDF
gt_table <-
  t_14_1_01 %>%
  as_gt() %>%
  cols_align(align = "center", columns = -label) %>%
  tab_style(
    style = cell_text(align = "center"),
    locations = cells_column_labels(columns = everything())
  ) %>%
  tab_header(
    title = "Table 14-1.01",
    subtitle = "Summary of Populations"
  )

# Add header and footer using docorator
gt_table %>%
  as_docorator(
    display_name = "t_14_1_01",
    display_loc = path$table_output,
    header = fancyhead(
      fancyrow(left = "Protocol: CDISCPILOT01", center = NA, right = doc_pagenum()),
      fancyrow(left = "Population: All Subjects", center = NA, right = NA)
    ),
    footer = fancyfoot(
      fancyrow(
        left = paste0(
          "NOTE: N in column headers represents number of subjects entered in study ",
          "(i.e., signed informed consent). ",
          "The ITT ",
          "population includes all subjects randomized. ",
          "The Safety population includes all randomized subjects known to have taken at",
          "least one dose of randomized study drug.",
          "The Efficacy population includes all subjects in the safety ",
          "population who also have",
          "at least one post-baseline ADAS-Cog and CIBIC+ assessment."
        )
      ),
      fancyrow(left = paste0("Source: ", doc_relative_path()), center = NA, right = doc_datetime())
    ),
    save_object = FALSE
  ) %>%
  render_pdf(path$table_output)
