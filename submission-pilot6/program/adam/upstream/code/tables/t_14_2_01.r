#************************************************************************
# Purpose:     Generate Table 14.2.1 - Summary of Demographic and Baseline Characteristics
# Input:       ADSL
# Output:      t14_2_01.pdf
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
library(forcats)
library(purrr)

# Import utility functions
source(file.path("code", "utils", "doc_relative_path.r"))
source(file.path("code", "utils", "table_functions.r"))

# ----------------------------------------------------------------------------
# Load datasets
# ----------------------------------------------------------------------------

# Local helper to replace blank strings with NA
convert_blanks_to_na_local <- function(df) {
  df %>%
    mutate(across(where(is.character), ~ na_if(.x, "")))
}

# Convert all variable names to lowercase for code style consistency
adsl <- read_dataset_json(file.path(path$adam, "adsl.json")) %>%
  convert_blanks_to_na_local() %>%
  rename_with(tolower) %>%
  filter(ittfl == "Y")

# ----------------------------------------------------------------------------
# Prepare data
# ----------------------------------------------------------------------------

adsl_updated <- adsl %>%
  # Factorize categorical variables to keep order in summaries
  # BMI Category does not have a numeric variable in ADSL, so order is defined manually
  mutate(
    trt01p = fct_reorder(factor(trt01p), trt01pn),
    agegr1 = fct_reorder(factor(agegr1), agegr1n),
    racec = fct_reorder(factor(racec), racecn),
    bmiblgr1 = factor(bmiblgr1, levels = c("<25", "25-<30", ">=30"))
  ) %>%
  # Update Sex values, as dataset values are abbreviated
  mutate(
    sex_updated = case_when(
      sex == "M" ~ "Male",
      sex == "F" ~ "Female",
      TRUE ~ sex
    ),
    sex_updated = factor(sex_updated, levels = c("Male", "Female"))
  )

# ----------------------------------------------------------------------------
# Get table summary data
# ----------------------------------------------------------------------------

# The variable list is reused in several places, so keep it as vector
summary_cols <- c(
  "age", "agegr1", "sex_updated", "racec", "mmsetot",
  "durdis", "durdsgr1", "educlvl", "weightbl", "heightbl", "bmibl", "bmiblgr1"
)

# Create summary table for demographic and baseline characteristics
t_14_2_01 <- adsl_updated %>%
  tbl_summary(
    by = trt01p,
    type = all_continuous() ~ "continuous2",
    include = all_of(summary_cols),
    statistic = list(
      all_continuous() ~ c("{N_nonmiss}", "{mean}", "{sd}", "{median}", "{min}", "{max}"),
      all_categorical() ~ "{n} ({p}%)"
    ),
    # Do not show missing values
    missing = "no",
    digits = list(
      all_continuous() ~ c(0, 1, 2, 1, 1, 1),
      all_categorical() ~ list(
        p = format_percent
      )
    ),
    label = list(
      age = "Age (y)",
      agegr1 = "Age Category",
      sex_updated = "Sex",
      racec = "Race (Origin)",
      mmsetot = "MMSE",
      durdis = "Duration of Disease",
      durdsgr1 = "Duration of Disease Category",
      educlvl = "Years of Education",
      weightbl = "Baseline Weight (kg)",
      heightbl = "Baseline Height (cm)",
      bmibl = "Baseline BMI",
      bmiblgr1 = "Baseline BMI Category"
    )
  ) %>%
  # Add Total column, label is assigned later for the stat_0 column
  add_overall(
    last = TRUE
  ) %>%
  # ANOVA for continuous (oneway.test + var.equal = TRUE) variables and chi-square test for categorical variables
  add_p(
    pvalue_fun = label_style_number(digits = 4),
    test = list(
      all_continuous() ~ "oneway.test",
      all_categorical() ~ "chisq.test"
    ),
    test.args = list(
      all_continuous() ~ list(var.equal = TRUE)
    )
  ) %>%
  # Column headers
  modify_header(label = "") %>%
  modify_header(!!!list(
    all_stat_cols() ~ "**{level}**  \n(N={n})",
    stat_0 ~ "**Total**  \n(N={N})",
    p.value ~ "**p-value  \n[1]**"
  )) %>%
  remove_footnote_header(columns = everything()) %>%
  # Various formatting modifications
  modify_table_body(
    ~ .x %>%
      # Add a blank line before each category
      mutate(variable = factor(variable, levels = summary_cols)) %>%
      group_by(variable, .add = TRUE) %>%
      reframe(add_row(pick(everything()), .before = 1)) %>%
      mutate(variable = as.character(variable)) %>%
      # Manually set labels, as "n" default label is different
      mutate(label = case_when(
        (row_type == "level" & label == "N Non-missing") ~ "n",
        TRUE ~ label
      )) %>%
      # Formatting
      mutate(
        across(
          all_stat_cols(),
          ~ case_when(
            # Align values for continuous variables
            (var_type == "continuous2" & row_type == "level" & label == "n") ~ paste0(.x, "\u2007\u2007\u2007"),
            (var_type == "continuous2" & row_type == "level" & label != "SD") ~ paste0(.x, "\u2007"),
            # Remove 0% in categorical rows
            (var_type == "categorical" & row_type == "level" & . == "0 (  0%)")
            ~ "0\u2007\u2007\u2007\u2007\u2007\u2007\u2007",
            TRUE ~ .x
          )
        )
      ) %>%
      # To center the values, add 5 spaces at the end
      mutate(
        across(
          all_stat_cols(),
          ~ case_when(
            # Align values for continuous variables
            row_type == "level" ~ paste0(.x, "\u2007\u2007\u2007\u2007\u2007"),
            TRUE ~ .x
          )
        )
      )
  )

# ----------------------------------------------------------------------------
# Output data
# ----------------------------------------------------------------------------

# Convert gtsummary object to ARD format
t_14_2_01_ard <- gather_ard(t_14_2_01)

# Save ARD as RDS
saveRDS(t_14_2_01_ard, file.path(path$table_ard, "t_14_2_01.rds"))

# Save as PDF
# We have to split table into several tables to avoid mid-page split of categories
t_14_2_01_by_page <-
  t_14_2_01 %>%
  tbl_split_by_rows(variables = c(sex_updated, mmsetot, educlvl, heightbl))

gt_tables_list <- map(t_14_2_01_by_page, ~ {
  .x %>%
    as_gt(auto_align = FALSE) %>%
    tab_style(
      style = cell_text(align = "center", v_align = "bottom"),
      locations = cells_column_labels(columns = everything())
    ) %>%
    cols_align(
      align = "right",
      columns = all_stat_cols()
    ) %>%
    cols_align(
      align = "center",
      columns = p.value
    ) %>%
    cols_align(
      align = "auto",
      columns = label
    ) %>%
    cols_width(
      label ~ "26%",
      all_stat_cols() ~ "16%",
      p.value ~ "10%"
    ) %>%
    tab_header(
      title = "Table 14-2.01",
      subtitle = "Summary of Demographic and Baseline Characteristics"
    )
})

# Add header and footer using docorator
gt_group(.list = gt_tables_list) %>%
  as_docorator(
    display_name = "t_14_2_01",
    display_loc = path$table_output,
    tbl_scale = FALSE,
    header = fancyhead(
      fancyrow(left = "Protocol: CDISCPILOT01", center = NA, right = doc_pagenum()),
      fancyrow(left = "Population: Intent-to-Treat", center = NA, right = NA)
    ),
    footer = fancyfoot(
      fancyrow(
        left = paste0(
          "[1] P-values are results of ANOVA treatment group comparison for continuous",
          " variable and Pearson's chi-square test for"
        )
      ),
      fancyrow(
        "categorical variables."
      ),
      fancyrow(
        left = paste0(
          "NOTE: Duration of disease is computed as months between date of",
          " enrollment and date of onset of the first definite"
        )
      ),
      fancyrow(
        "symptoms of Alzheimer's disease"
      ),
      fancyrow(left = paste0("Source: ", doc_relative_path()), center = NA, right = doc_datetime())
    ),
    save_object = FALSE
  ) %>%
  render_pdf(path$table_output)
