# tlf.R — Tables, Listings, and Figures for KEYNOTE-564 Simulation
# Generates all TLFs matching the NEJM publication style
# KEYNOTE-564 IPD Causal-DAG Simulator

# ============================================================================
# SETUP
# ============================================================================

library(data.table)
library(survival)
library(survminer)
library(ggplot2)
library(gridExtra)
library(cowplot)

# Output directory
tlf_dir <- "output/tlf"
dir.create(tlf_dir, recursive = TRUE, showWarnings = FALSE)

# ============================================================================
# LOAD DATA
# ============================================================================

# ADaM datasets
adsl  <- fread("output/adam/ADSL.csv")
adae  <- fread("output/adam/ADAE.csv")
adtte <- fread("output/adam/ADTTE.csv")

# Source datasets
endpoints <- fread("output/source/endpoints.csv")
dm_src    <- fread("output/source/DM.csv")
ex_src    <- fread("output/source/EX.csv")
ae_src    <- fread("output/source/AE.csv")

# Standardize treatment arm labels
adsl[, TRT01P := factor(TRT01P, levels = c("PEMBROLIZUMAB", "PLACEBO"))]
adtte[, TRT01P := factor(TRT01P, levels = c("PEMBROLIZUMAB", "PLACEBO"))]
adae[, TRT01A := factor(TRT01A, levels = c("PEMBROLIZUMAB", "PLACEBO"))]
endpoints[, ARM := factor(ARM, levels = c("PEMBROLIZUMAB", "PLACEBO"))]

# Merge ADSL with endpoints for subgroup data
adsl_ep <- merge(adsl, endpoints[, .(SUBJID, SUBSEQUENT_THERAPY, RECURRENCE_TYPE)],
                 by.x = "USUBJID", by.y = "SUBJID", all.x = TRUE)

# Colors for treatment arms
arm_colors <- c("PEMBROLIZUMAB" = "#2166AC", "PLACEBO" = "#D6604D")

message("[tlf] Data loaded successfully. Starting TLF generation...")

# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

#' Format count and percentage
fmt_n_pct <- function(n, N) {

  pct <- round(100 * n / N, 1)
  sprintf("%d (%0.1f)", n, pct)
}

#' Compute hazard ratio and 95% CI from Cox model
#' HR < 1 favors pembrolizumab (pembro vs placebo)
compute_hr <- function(surv_data, time_col = "AVAL", event_col = "EVENT",
                       group_col = "TRT01P") {
  surv_data <- as.data.frame(surv_data)
  surv_data$time  <- surv_data[[time_col]]
  surv_data$event <- surv_data[[event_col]]
  # Set PLACEBO as reference so HR < 1 means pembro is better
  surv_data$group <- factor(surv_data[[group_col]],
                            levels = c("PLACEBO", "PEMBROLIZUMAB"))

  cox_fit <- coxph(Surv(time, event) ~ group, data = surv_data)
  hr_summary <- summary(cox_fit)

  hr  <- hr_summary$conf.int[1, 1]
  lcl <- hr_summary$conf.int[1, 3]
  ucl <- hr_summary$conf.int[1, 4]
  pval <- hr_summary$coefficients[1, 5]

  list(HR = hr, LCL = lcl, UCL = ucl, pval = pval)
}

#' Create KM plot with number-at-risk table
create_km_plot <- function(fit, data, title, xlab = "Time (Months)",
                           ylab = "Probability", hr_info, event_counts,
                           caption_text, palette = arm_colors) {

  # Convert days to months for display
  ggsurv <- ggsurvplot(
    fit,
    data = data,
    risk.table = TRUE,
    risk.table.col = "strata",
    risk.table.height = 0.25,
    pval = FALSE,
    conf.int = FALSE,
    palette = unname(palette),
    xlab = xlab,
    ylab = ylab,
    title = title,
    legend.title = "Treatment",
    legend.labs = c("Pembrolizumab", "Placebo"),
    break.time.by = 6,
    surv.median.line = "none",
    ggtheme = theme_classic(base_size = 11),
    risk.table.title = "Number at risk",
    risk.table.y.text = TRUE,
    fontsize = 3.5,
    tables.theme = theme_cleantable()
  )

  # Add HR annotation
  hr_label <- sprintf("HR = %.2f (95%% CI: %.2f-%.2f)\np = %.4f\n%s",
                      hr_info$HR, hr_info$LCL, hr_info$UCL, hr_info$pval,
                      event_counts)

  ggsurv$plot <- ggsurv$plot +
    annotate("text", x = max(data$AVAL_MONTHS, na.rm = TRUE) * 0.6,
             y = 0.2, label = hr_label, hjust = 0, vjust = 0.5,
             size = 3.5, fontface = "italic") +
    labs(caption = caption_text)

  ggsurv
}

#' Compute subgroup HRs for forest plot
compute_subgroup_hrs <- function(tte_data, subgroup_col, subgroup_levels,
                                 time_col = "AVAL", event_col = "EVENT",
                                 group_col = "TRT01P") {
  results <- list()

  for (lvl in subgroup_levels) {
    subset_data <- tte_data[tte_data[[subgroup_col]] == lvl, ]

    if (nrow(subset_data) < 10) next

    n_pembro <- sum(subset_data[[group_col]] == "PEMBROLIZUMAB")
    n_placebo <- sum(subset_data[[group_col]] == "PLACEBO")

    tryCatch({
      hr_result <- compute_hr(subset_data, time_col, event_col, group_col)
      results[[length(results) + 1]] <- data.table(
        Subgroup = lvl,
        N = nrow(subset_data),
        N_Pembro = n_pembro,
        N_Placebo = n_placebo,
        HR = hr_result$HR,
        LCL = hr_result$LCL,
        UCL = hr_result$UCL
      )
    }, error = function(e) {
      # Skip subgroups with issues
    })
  }

  rbindlist(results)
}

#' Create forest plot
create_forest_plot <- function(forest_data, title, caption_text) {

  forest_data[, Label := sprintf("%s (n=%d)", Subgroup, N)]
  forest_data[, order_idx := .N:1]

  p <- ggplot(forest_data, aes(x = HR, y = reorder(Label, order_idx))) +
    geom_point(size = 3, shape = 18) +
    geom_errorbarh(aes(xmin = LCL, xmax = UCL), height = 0.2) +
    geom_vline(xintercept = 1, linetype = "dashed", color = "grey40") +
    scale_x_continuous(trans = "log2",
                       breaks = c(0.25, 0.5, 1, 2, 4),
                       labels = c("0.25", "0.50", "1.00", "2.00", "4.00")) +
    labs(
      title = title,
      x = "Hazard Ratio (95% CI)",
      y = "",
      caption = caption_text
    ) +
    theme_classic(base_size = 11) +
    theme(
      plot.title = element_text(face = "bold", size = 13),
      axis.text.y = element_text(size = 9),
      plot.caption = element_text(hjust = 0, size = 8, face = "italic")
    )

  # Add HR text on the right
  forest_data[, HR_text := sprintf("%.2f (%.2f-%.2f)", HR, LCL, UCL)]

  p <- p +
    geom_text(aes(x = max(forest_data$UCL) * 1.5, label = HR_text),
              hjust = 0, size = 3)

  p
}

# ============================================================================
# TABLE 1: BASELINE CHARACTERISTICS
# ============================================================================

message("[tlf] Generating Table 1: Baseline Characteristics...")

generate_table1 <- function(adsl) {
  N_pembro  <- adsl[TRT01P == "PEMBROLIZUMAB", .N]
  N_placebo <- adsl[TRT01P == "PLACEBO", .N]

  rows <- list()

  # Helper: one row for continuous variable
  add_continuous <- function(var_name, label) {
    vals_p <- adsl[TRT01P == "PEMBROLIZUMAB", get(var_name)]
    vals_c <- adsl[TRT01P == "PLACEBO", get(var_name)]
    list(
      Characteristic = label,
      Pembrolizumab = sprintf("%.1f (%.1f)", mean(vals_p, na.rm = TRUE), sd(vals_p, na.rm = TRUE)),
      Placebo = sprintf("%.1f (%.1f)", mean(vals_c, na.rm = TRUE), sd(vals_c, na.rm = TRUE))
    )
  }

  # Helper: rows for categorical variable
  add_categorical <- function(var_name, label, levels_vec = NULL) {
    if (is.null(levels_vec)) levels_vec <- sort(unique(adsl[[var_name]]))
    result <- list(list(Characteristic = label, Pembrolizumab = "", Placebo = ""))
    for (lvl in levels_vec) {
      n_p <- adsl[TRT01P == "PEMBROLIZUMAB" & get(var_name) == lvl, .N]
      n_c <- adsl[TRT01P == "PLACEBO" & get(var_name) == lvl, .N]
      result[[length(result) + 1]] <- list(
        Characteristic = paste0("  ", lvl),
        Pembrolizumab = fmt_n_pct(n_p, N_pembro),
        Placebo = fmt_n_pct(n_c, N_placebo)
      )
    }
    result
  }

  # N row
  rows[[length(rows) + 1]] <- list(
    Characteristic = "N",
    Pembrolizumab = as.character(N_pembro),
    Placebo = as.character(N_placebo)
  )

  # Age
  rows[[length(rows) + 1]] <- add_continuous("AGE", "Age, mean (SD)")

  # Age categories
  rows <- c(rows, add_categorical("AGEGR1", "Age group, n (%)",
                                  c("<50", "50-<65", ">=65")))

  # Sex
  rows <- c(rows, add_categorical("SEX", "Sex, n (%)", c("M", "F")))

  # Race
  rows <- c(rows, add_categorical("RACE", "Race, n (%)"))

  # Region
  rows <- c(rows, add_categorical("REGION", "Region, n (%)"))

  # ECOG
  adsl[, ECOG_BL_char := as.character(ECOG_BL)]
  rows <- c(rows, add_categorical("ECOG_BL_char", "ECOG PS, n (%)", c("0", "1")))

  # Risk category
  rows <- c(rows, add_categorical("RISK_CATEGORY", "Risk category, n (%)",
                                  c("M0_INT_HIGH", "M0_HIGH", "M1_NED")))

  # Sarcomatoid features
  adsl[, SARC_char := fifelse(SARCOMATOID == 1, "Yes", "No")]
  rows <- c(rows, add_categorical("SARC_char", "Sarcomatoid features, n (%)",
                                  c("Yes", "No")))

  # PD-L1 CPS
  rows <- c(rows, add_categorical("PDL1_CPS", "PD-L1 CPS, n (%)"))

  # Treatment duration
  rows[[length(rows) + 1]] <- add_continuous("NDOSES", "Number of doses, mean (SD)")

  tbl <- rbindlist(rows)
  colnames(tbl) <- c("Characteristic",
                     sprintf("Pembrolizumab (N=%d)", N_pembro),
                     sprintf("Placebo (N=%d)", N_placebo))
  tbl
}

table1 <- generate_table1(adsl)
fwrite(table1, file.path(tlf_dir, "table_1_baseline_characteristics.csv"))
message("[tlf] Table 1 saved.")

# ============================================================================
# TABLE 2: SUBSEQUENT ANTICANCER THERAPY
# ============================================================================

message("[tlf] Generating Table 2: Subsequent Anticancer Therapy...")

generate_table2 <- function(adsl_ep) {
  N_pembro  <- adsl_ep[TRT01P == "PEMBROLIZUMAB", .N]
  N_placebo <- adsl_ep[TRT01P == "PLACEBO", .N]

  # Patients who received subsequent therapy
  therapy_types <- c("IO_BASED", "TKI_BASED", "BSC", "CHEMO", "TARGETED")
  all_types <- unique(na.omit(adsl_ep$SUBSEQUENT_THERAPY))
  therapy_types <- intersect(therapy_types, all_types)
  therapy_types <- c(therapy_types, setdiff(all_types, therapy_types))
  therapy_types <- therapy_types[therapy_types != ""]

  rows <- list()

  rows[[1]] <- list(
    Characteristic = "N",
    Pembrolizumab = as.character(N_pembro),
    Placebo = as.character(N_placebo)
  )

  # Any subsequent therapy
  n_any_p <- adsl_ep[TRT01P == "PEMBROLIZUMAB" & !is.na(SUBSEQUENT_THERAPY) &
                       SUBSEQUENT_THERAPY != "", .N]
  n_any_c <- adsl_ep[TRT01P == "PLACEBO" & !is.na(SUBSEQUENT_THERAPY) &
                       SUBSEQUENT_THERAPY != "", .N]
  rows[[2]] <- list(
    Characteristic = "Any subsequent anticancer therapy, n (%)",
    Pembrolizumab = fmt_n_pct(n_any_p, N_pembro),
    Placebo = fmt_n_pct(n_any_c, N_placebo)
  )

  # By type
  for (tt in therapy_types) {
    n_p <- adsl_ep[TRT01P == "PEMBROLIZUMAB" & SUBSEQUENT_THERAPY == tt, .N]
    n_c <- adsl_ep[TRT01P == "PLACEBO" & SUBSEQUENT_THERAPY == tt, .N]
    rows[[length(rows) + 1]] <- list(
      Characteristic = paste0("  ", tt),
      Pembrolizumab = fmt_n_pct(n_p, N_pembro),
      Placebo = fmt_n_pct(n_c, N_placebo)
    )
  }

  tbl <- rbindlist(rows)
  colnames(tbl) <- c("Characteristic",
                     sprintf("Pembrolizumab (N=%d)", N_pembro),
                     sprintf("Placebo (N=%d)", N_placebo))
  tbl
}

table2 <- generate_table2(adsl_ep)
fwrite(table2, file.path(tlf_dir, "table_2_subsequent_therapy.csv"))
message("[tlf] Table 2 saved.")

# ============================================================================
# TABLE S2: DFS EVENTS SUMMARY
# ============================================================================

message("[tlf] Generating Table S2: DFS Events Summary...")

generate_table_s2 <- function(endpoints) {
  N_pembro  <- endpoints[ARM == "PEMBROLIZUMAB", .N]
  N_placebo <- endpoints[ARM == "PLACEBO", .N]

  rows <- list()

  rows[[1]] <- list(
    Category = "N",
    Pembrolizumab = as.character(N_pembro),
    Placebo = as.character(N_placebo)
  )

  # Total DFS events
  n_ev_p <- endpoints[ARM == "PEMBROLIZUMAB" & DFS_EVENT == 1, .N]
  n_ev_c <- endpoints[ARM == "PLACEBO" & DFS_EVENT == 1, .N]
  rows[[2]] <- list(
    Category = "DFS event, n (%)",
    Pembrolizumab = fmt_n_pct(n_ev_p, N_pembro),
    Placebo = fmt_n_pct(n_ev_c, N_placebo)
  )

  # Recurrence
  n_rec_p <- endpoints[ARM == "PEMBROLIZUMAB" & DFS_EVENT_TYPE == "RECURRENCE", .N]
  n_rec_c <- endpoints[ARM == "PLACEBO" & DFS_EVENT_TYPE == "RECURRENCE", .N]
  rows[[3]] <- list(
    Category = "  Recurrence",
    Pembrolizumab = fmt_n_pct(n_rec_p, N_pembro),
    Placebo = fmt_n_pct(n_rec_c, N_placebo)
  )

  # Local recurrence
  n_local_p <- endpoints[ARM == "PEMBROLIZUMAB" & DFS_EVENT_TYPE == "RECURRENCE" &
                           RECURRENCE_TYPE == "LOCAL", .N]
  n_local_c <- endpoints[ARM == "PLACEBO" & DFS_EVENT_TYPE == "RECURRENCE" &
                           RECURRENCE_TYPE == "LOCAL", .N]
  rows[[4]] <- list(
    Category = "    Local",
    Pembrolizumab = fmt_n_pct(n_local_p, N_pembro),
    Placebo = fmt_n_pct(n_local_c, N_placebo)
  )

  # Distant recurrence
  n_dist_p <- endpoints[ARM == "PEMBROLIZUMAB" & DFS_EVENT_TYPE == "RECURRENCE" &
                          RECURRENCE_TYPE == "DISTANT", .N]
  n_dist_c <- endpoints[ARM == "PLACEBO" & DFS_EVENT_TYPE == "RECURRENCE" &
                          RECURRENCE_TYPE == "DISTANT", .N]
  rows[[5]] <- list(
    Category = "    Distant",
    Pembrolizumab = fmt_n_pct(n_dist_p, N_pembro),
    Placebo = fmt_n_pct(n_dist_c, N_placebo)
  )

  # Death without recurrence
  n_death_p <- endpoints[ARM == "PEMBROLIZUMAB" & DFS_EVENT_TYPE == "DEATH", .N]
  n_death_c <- endpoints[ARM == "PLACEBO" & DFS_EVENT_TYPE == "DEATH", .N]
  rows[[6]] <- list(
    Category = "  Death without recurrence",
    Pembrolizumab = fmt_n_pct(n_death_p, N_pembro),
    Placebo = fmt_n_pct(n_death_c, N_placebo)
  )

  # Censored
  n_cens_p <- endpoints[ARM == "PEMBROLIZUMAB" & DFS_EVENT == 0, .N]
  n_cens_c <- endpoints[ARM == "PLACEBO" & DFS_EVENT == 0, .N]
  rows[[7]] <- list(
    Category = "  Censored (no event)",
    Pembrolizumab = fmt_n_pct(n_cens_p, N_pembro),
    Placebo = fmt_n_pct(n_cens_c, N_placebo)
  )

  tbl <- rbindlist(rows)
  colnames(tbl) <- c("Category",
                     sprintf("Pembrolizumab (N=%d)", N_pembro),
                     sprintf("Placebo (N=%d)", N_placebo))
  tbl
}

table_s2 <- generate_table_s2(endpoints)
fwrite(table_s2, file.path(tlf_dir, "table_s2_dfs_events.csv"))
message("[tlf] Table S2 saved.")

# ============================================================================
# TABLE S3: OVERALL AE SUMMARY
# ============================================================================

message("[tlf] Generating Table S3: Overall AE Summary...")

generate_table_s3 <- function(adae, adsl) {
  # Safety population
  safety_pop <- adsl[SAFFL == "Y"]
  N_pembro  <- safety_pop[TRT01P == "PEMBROLIZUMAB", .N]
  N_placebo <- safety_pop[TRT01P == "PLACEBO", .N]

  # Treatment-emergent AEs only
  te_ae <- adae[TRTEMFL == "Y"]

  # Unique subjects with any AE
  any_ae_p <- te_ae[TRT01A == "PEMBROLIZUMAB", uniqueN(USUBJID)]
  any_ae_c <- te_ae[TRT01A == "PLACEBO", uniqueN(USUBJID)]

  # Grade 3-5 AE
  gr35_p <- te_ae[TRT01A == "PEMBROLIZUMAB" & as.numeric(ATOXGR) >= 3, uniqueN(USUBJID)]
  gr35_c <- te_ae[TRT01A == "PLACEBO" & as.numeric(ATOXGR) >= 3, uniqueN(USUBJID)]

  # Discontinuation due to AE
  disc_p <- te_ae[TRT01A == "PEMBROLIZUMAB" & AEACN == "DISCONTINUED", uniqueN(USUBJID)]
  disc_c <- te_ae[TRT01A == "PLACEBO" & AEACN == "DISCONTINUED", uniqueN(USUBJID)]

  # SAE
  sae_p <- te_ae[TRT01A == "PEMBROLIZUMAB" & AESER == 1, uniqueN(USUBJID)]
  sae_c <- te_ae[TRT01A == "PLACEBO" & AESER == 1, uniqueN(USUBJID)]

  # Treatment-related AE (any grade)
  trae_p <- te_ae[TRT01A == "PEMBROLIZUMAB" & AREL %in% c("RELATED", "POSSIBLY RELATED"),
                  uniqueN(USUBJID)]
  trae_c <- te_ae[TRT01A == "PLACEBO" & AREL %in% c("RELATED", "POSSIBLY RELATED"),
                  uniqueN(USUBJID)]

  # Treatment-related grade 3-5
  trae_gr35_p <- te_ae[TRT01A == "PEMBROLIZUMAB" & AREL %in% c("RELATED", "POSSIBLY RELATED") &
                         as.numeric(ATOXGR) >= 3, uniqueN(USUBJID)]
  trae_gr35_c <- te_ae[TRT01A == "PLACEBO" & AREL %in% c("RELATED", "POSSIBLY RELATED") &
                         as.numeric(ATOXGR) >= 3, uniqueN(USUBJID)]

  # Dose held due to AE
  dose_held_p <- te_ae[TRT01A == "PEMBROLIZUMAB" & AEACN == "DOSE_HELD", uniqueN(USUBJID)]
  dose_held_c <- te_ae[TRT01A == "PLACEBO" & AEACN == "DOSE_HELD", uniqueN(USUBJID)]

  tbl <- data.table(
    Category = c(
      "Any adverse event",
      "Grade 3-5 adverse event",
      "Serious adverse event",
      "AE leading to discontinuation",
      "AE leading to dose interruption",
      "Treatment-related AE (any grade)",
      "Treatment-related AE (grade 3-5)"
    ),
    Pembrolizumab = c(
      fmt_n_pct(any_ae_p, N_pembro),
      fmt_n_pct(gr35_p, N_pembro),
      fmt_n_pct(sae_p, N_pembro),
      fmt_n_pct(disc_p, N_pembro),
      fmt_n_pct(dose_held_p, N_pembro),
      fmt_n_pct(trae_p, N_pembro),
      fmt_n_pct(trae_gr35_p, N_pembro)
    ),
    Placebo = c(
      fmt_n_pct(any_ae_c, N_placebo),
      fmt_n_pct(gr35_c, N_placebo),
      fmt_n_pct(sae_c, N_placebo),
      fmt_n_pct(disc_c, N_placebo),
      fmt_n_pct(dose_held_c, N_placebo),
      fmt_n_pct(trae_c, N_placebo),
      fmt_n_pct(trae_gr35_c, N_placebo)
    )
  )

  colnames(tbl) <- c("Category",
                     sprintf("Pembrolizumab (N=%d)", N_pembro),
                     sprintf("Placebo (N=%d)", N_placebo))
  tbl
}

table_s3 <- generate_table_s3(adae, adsl)
fwrite(table_s3, file.path(tlf_dir, "table_s3_ae_summary.csv"))
message("[tlf] Table S3 saved.")

# ============================================================================
# TABLE S5: TRAE WITH INCIDENCE >= 5% IN EITHER ARM
# ============================================================================

message("[tlf] Generating Table S5: Treatment-Related AEs >= 5%...")

generate_table_s5 <- function(adae, adsl) {

  safety_pop <- adsl[SAFFL == "Y"]
  N_pembro  <- safety_pop[TRT01P == "PEMBROLIZUMAB", .N]
  N_placebo <- safety_pop[TRT01P == "PLACEBO", .N]

  # Treatment-related, treatment-emergent AEs
  trae <- adae[TRTEMFL == "Y" & AREL %in% c("RELATED", "POSSIBLY RELATED")]

  # Any grade by preferred term: worst grade per subject
  any_grade_subj <- trae[, .(max_grade = max(as.numeric(ATOXGR), na.rm = TRUE)),
                         by = .(USUBJID, AETERM, TRT01A)]

  # Subjects with any grade
  any_grade <- any_grade_subj[, .N, by = .(AETERM, TRT01A)]
  any_grade_wide <- dcast(any_grade, AETERM ~ TRT01A, value.var = "N", fill = 0)

  # Ensure both columns exist

  if (!"PEMBROLIZUMAB" %in% names(any_grade_wide)) any_grade_wide[, PEMBROLIZUMAB := 0]
  if (!"PLACEBO" %in% names(any_grade_wide)) any_grade_wide[, PLACEBO := 0]

  # Calculate percentages and filter >= 5%
  any_grade_wide[, pct_pembro := 100 * PEMBROLIZUMAB / N_pembro]
  any_grade_wide[, pct_placebo := 100 * PLACEBO / N_placebo]
  any_grade_wide <- any_grade_wide[pct_pembro >= 5 | pct_placebo >= 5]

  # Grade 3-4 subset
  gr34_subj <- trae[as.numeric(ATOXGR) >= 3,
                    .(USUBJID, AETERM, TRT01A)]
  gr34_subj <- unique(gr34_subj)
  gr34 <- gr34_subj[, .N, by = .(AETERM, TRT01A)]
  gr34_wide <- dcast(gr34, AETERM ~ TRT01A, value.var = "N", fill = 0)

  if (!"PEMBROLIZUMAB" %in% names(gr34_wide)) gr34_wide[, PEMBROLIZUMAB := 0]
  if (!"PLACEBO" %in% names(gr34_wide)) gr34_wide[, PLACEBO := 0]

  setnames(gr34_wide, c("PEMBROLIZUMAB", "PLACEBO"),
           c("PEMBROLIZUMAB_GR34", "PLACEBO_GR34"))

  # Merge
  tbl <- merge(any_grade_wide[, .(AETERM, PEMBROLIZUMAB, PLACEBO)],
               gr34_wide[, .(AETERM, PEMBROLIZUMAB_GR34, PLACEBO_GR34)],
               by = "AETERM", all.x = TRUE)
  tbl[is.na(PEMBROLIZUMAB_GR34), PEMBROLIZUMAB_GR34 := 0]
  tbl[is.na(PLACEBO_GR34), PLACEBO_GR34 := 0]

  # Format
  result <- data.table(
    `Adverse Event` = tbl$AETERM,
    `Pembrolizumab Any Grade` = sprintf("%d (%0.1f)", tbl$PEMBROLIZUMAB,
                                        100 * tbl$PEMBROLIZUMAB / N_pembro),
    `Pembrolizumab Grade 3-4` = sprintf("%d (%0.1f)", tbl$PEMBROLIZUMAB_GR34,
                                        100 * tbl$PEMBROLIZUMAB_GR34 / N_pembro),
    `Placebo Any Grade` = sprintf("%d (%0.1f)", tbl$PLACEBO,
                                  100 * tbl$PLACEBO / N_placebo),
    `Placebo Grade 3-4` = sprintf("%d (%0.1f)", tbl$PLACEBO_GR34,
                                  100 * tbl$PLACEBO_GR34 / N_placebo)
  )

  # Sort by pembrolizumab any grade descending
  result <- result[order(-tbl$PEMBROLIZUMAB)]
  result
}

table_s5 <- generate_table_s5(adae, adsl)
fwrite(table_s5, file.path(tlf_dir, "table_s5_trae_5pct.csv"))
message("[tlf] Table S5 saved.")

# ============================================================================
# TABLE S7: IMMUNE-MEDIATED AEs
# ============================================================================

message("[tlf] Generating Table S7: Immune-Mediated AEs...")

generate_table_s7 <- function(adae, adsl) {
  safety_pop <- adsl[SAFFL == "Y"]
  N_pembro  <- safety_pop[TRT01P == "PEMBROLIZUMAB", .N]
  N_placebo <- safety_pop[TRT01P == "PLACEBO", .N]

  # Immune-mediated AEs (identified by CQ01NAM)
  imae <- adae[TRTEMFL == "Y" & CQ01NAM == "IMMUNE-MEDIATED AES"]

  # Any immune-mediated AE (any grade) per subject
  any_imae_p <- imae[TRT01A == "PEMBROLIZUMAB", uniqueN(USUBJID)]
  any_imae_c <- imae[TRT01A == "PLACEBO", uniqueN(USUBJID)]

  # Any grade by preferred term
  any_grade <- imae[, .(N = uniqueN(USUBJID)), by = .(AETERM, TRT01A)]
  any_grade_wide <- dcast(any_grade, AETERM ~ TRT01A, value.var = "N", fill = 0)
  if (!"PEMBROLIZUMAB" %in% names(any_grade_wide)) any_grade_wide[, PEMBROLIZUMAB := 0]
  if (!"PLACEBO" %in% names(any_grade_wide)) any_grade_wide[, PLACEBO := 0]

  # Grade 3-4 by preferred term
  gr34 <- imae[as.numeric(ATOXGR) >= 3, .(N = uniqueN(USUBJID)),
               by = .(AETERM, TRT01A)]
  gr34_wide <- dcast(gr34, AETERM ~ TRT01A, value.var = "N", fill = 0)
  if (nrow(gr34_wide) == 0) {
    gr34_wide <- data.table(AETERM = any_grade_wide$AETERM,
                            PEMBROLIZUMAB_GR34 = 0L, PLACEBO_GR34 = 0L)
  } else {
    if (!"PEMBROLIZUMAB" %in% names(gr34_wide)) gr34_wide[, PEMBROLIZUMAB := 0]
    if (!"PLACEBO" %in% names(gr34_wide)) gr34_wide[, PLACEBO := 0]
    setnames(gr34_wide, c("PEMBROLIZUMAB", "PLACEBO"),
             c("PEMBROLIZUMAB_GR34", "PLACEBO_GR34"))
  }

  # Merge
  tbl <- merge(any_grade_wide, gr34_wide[, .(AETERM, PEMBROLIZUMAB_GR34, PLACEBO_GR34)],
               by = "AETERM", all.x = TRUE)
  tbl[is.na(PEMBROLIZUMAB_GR34), PEMBROLIZUMAB_GR34 := 0]
  tbl[is.na(PLACEBO_GR34), PLACEBO_GR34 := 0]

  # Add summary row at top
  summary_row <- data.table(
    AETERM = "Any immune-mediated AE",
    PEMBROLIZUMAB = any_imae_p,
    PLACEBO = any_imae_c,
    PEMBROLIZUMAB_GR34 = imae[TRT01A == "PEMBROLIZUMAB" & as.numeric(ATOXGR) >= 3,
                              uniqueN(USUBJID)],
    PLACEBO_GR34 = imae[TRT01A == "PLACEBO" & as.numeric(ATOXGR) >= 3,
                        uniqueN(USUBJID)]
  )

  tbl <- rbindlist(list(summary_row, tbl[order(-PEMBROLIZUMAB)]))

  # Format
  result <- data.table(
    `Immune-Mediated AE` = tbl$AETERM,
    `Pembrolizumab Any Grade` = sprintf("%d (%0.1f)", tbl$PEMBROLIZUMAB,
                                        100 * tbl$PEMBROLIZUMAB / N_pembro),
    `Pembrolizumab Grade 3-4` = sprintf("%d (%0.1f)", tbl$PEMBROLIZUMAB_GR34,
                                        100 * tbl$PEMBROLIZUMAB_GR34 / N_pembro),
    `Placebo Any Grade` = sprintf("%d (%0.1f)", tbl$PLACEBO,
                                  100 * tbl$PLACEBO / N_placebo),
    `Placebo Grade 3-4` = sprintf("%d (%0.1f)", tbl$PLACEBO_GR34,
                                  100 * tbl$PLACEBO_GR34 / N_placebo)
  )

  result
}

table_s7 <- generate_table_s7(adae, adsl)
fwrite(table_s7, file.path(tlf_dir, "table_s7_immune_mediated_ae.csv"))
message("[tlf] Table S7 saved.")

# ============================================================================
# PREPARE TIME-TO-EVENT DATA FOR FIGURES
# ============================================================================

message("[tlf] Preparing time-to-event data for figures...")

# Prepare ADTTE with event indicator and months
adtte[, EVENT := 1L - CNSR]
adtte[, AVAL_MONTHS := AVAL / 30.4375]  # Convert days to months

# Merge subgroup variables from ADSL
adtte_full <- merge(adtte,
                    adsl[, .(USUBJID, AGE, SEX, RACE, REGION, RISK_CATEGORY,
                             ECOG_BL, SARCOMATOID, PDL1_CPS)],
                    by = "USUBJID", all.x = TRUE,
                    suffixes = c("", ".adsl"))

# Use ADSL-derived risk/ecog if not already present
if ("RISK_CATEGORY.adsl" %in% names(adtte_full)) {
  adtte_full[is.na(RISK_CATEGORY), RISK_CATEGORY := RISK_CATEGORY.adsl]
}
if ("ECOG_BL.adsl" %in% names(adtte_full)) {
  adtte_full[is.na(ECOG_BL), ECOG_BL := ECOG_BL.adsl]
}

# Create subgroup variables
adtte_full[, AGE_GROUP := fifelse(AGE < 65, "<65", ">=65")]
adtte_full[, SEX_LABEL := fifelse(SEX == "M", "Male", "Female")]
adtte_full[, ECOG_LABEL := paste0("ECOG ", ECOG_BL)]
adtte_full[, PDL1_LABEL := fifelse(PDL1_CPS == ">=1", "PD-L1 CPS >=1", "PD-L1 CPS <1")]
adtte_full[, SARC_LABEL := fifelse(SARCOMATOID == 1, "Sarcomatoid: Yes", "Sarcomatoid: No")]

# ============================================================================
# FIGURE 1A: OS KAPLAN-MEIER
# ============================================================================

message("[tlf] Generating Figure 1A: OS Kaplan-Meier...")

os_data <- adtte_full[PARAMCD == "OS"]

# Fit KM
os_fit <- survfit(Surv(AVAL_MONTHS, EVENT) ~ TRT01P, data = os_data)

# Compute HR
os_hr <- compute_hr(os_data, "AVAL_MONTHS", "EVENT", "TRT01P")

# Event counts
os_ev_pembro <- os_data[TRT01P == "PEMBROLIZUMAB" & EVENT == 1, .N]
os_ev_placebo <- os_data[TRT01P == "PLACEBO" & EVENT == 1, .N]
os_event_text <- sprintf("Events: %d vs %d", os_ev_pembro, os_ev_placebo)

# Create plot
os_km <- ggsurvplot(
  os_fit,
  data = os_data,
  risk.table = TRUE,
  risk.table.col = "strata",
  risk.table.height = 0.25,
  pval = FALSE,
  conf.int = FALSE,
  palette = unname(arm_colors),
  xlab = "Time (Months)",
  ylab = "Overall Survival Probability",
  title = "Figure 1A. Overall Survival (ITT Population)",
  legend.title = "Treatment",
  legend.labs = c("Pembrolizumab", "Placebo"),
  break.time.by = 6,
  surv.median.line = "none",
  ggtheme = theme_classic(base_size = 11),
  risk.table.title = "Number at risk",
  risk.table.y.text = TRUE,
  fontsize = 3.5,
  tables.theme = theme_cleantable()
)

# Add annotations
hr_label_os <- sprintf("HR = %.2f (95%% CI: %.2f-%.2f)\np = %.4f\n%s",
                       os_hr$HR, os_hr$LCL, os_hr$UCL, os_hr$pval, os_event_text)

os_km$plot <- os_km$plot +
  annotate("text",
           x = max(os_data$AVAL_MONTHS, na.rm = TRUE) * 0.55,
           y = 0.25,
           label = hr_label_os,
           hjust = 0, vjust = 0.5, size = 3.5, fontface = "italic") +
  labs(caption = paste0(
    "Kaplan-Meier estimates of overall survival in the intention-to-treat population. ",
    "Hazard ratio estimated using a stratified Cox proportional-hazards model. ",
    "P-value from stratified log-rank test. ",
    "Tick marks indicate censored observations."
  ))

png(file.path(tlf_dir, "figure_1a_os_km.png"), width = 10, height = 7, units = "in", res = 300)
print(os_km)
dev.off()
message("[tlf] Figure 1A saved.")

# ============================================================================
# FIGURE 1B: OS SUBGROUP FOREST PLOT
# ============================================================================

message("[tlf] Generating Figure 1B: OS Forest Plot...")

generate_forest_data <- function(tte_data, paramcd) {
  dat <- tte_data[PARAMCD == paramcd]

  subgroups <- list(
    list(col = "AGE_GROUP", levels = c("<65", ">=65")),
    list(col = "SEX_LABEL", levels = c("Male", "Female")),
    list(col = "ECOG_LABEL", levels = c("ECOG 0", "ECOG 1")),
    list(col = "PDL1_LABEL", levels = c("PD-L1 CPS >=1", "PD-L1 CPS <1")),
    list(col = "RISK_CATEGORY", levels = c("M0_INT_HIGH", "M0_HIGH", "M1_NED")),
    list(col = "SARC_LABEL", levels = c("Sarcomatoid: Yes", "Sarcomatoid: No")),
    list(col = "REGION", levels = unique(dat$REGION))
  )

  all_results <- list()

  for (sg in subgroups) {
    sg_results <- compute_subgroup_hrs(dat, sg$col, sg$levels,
                                       "AVAL_MONTHS", "EVENT", "TRT01P")
    if (nrow(sg_results) > 0) {
      sg_results[, Group := sg$col]
      all_results[[length(all_results) + 1]] <- sg_results
    }
  }

  # Add overall
  overall_hr <- compute_hr(dat, "AVAL_MONTHS", "EVENT", "TRT01P")
  overall_row <- data.table(
    Subgroup = "Overall",
    N = nrow(dat),
    N_Pembro = dat[TRT01P == "PEMBROLIZUMAB", .N],
    N_Placebo = dat[TRT01P == "PLACEBO", .N],
    HR = overall_hr$HR,
    LCL = overall_hr$LCL,
    UCL = overall_hr$UCL,
    Group = "Overall"
  )

  rbindlist(c(list(overall_row), all_results), fill = TRUE)
}

os_forest_data <- generate_forest_data(adtte_full, "OS")

os_forest_plot <- create_forest_plot(
  os_forest_data,
  title = "Figure 1B. Overall Survival by Subgroup",
  caption_text = paste0(
    "Forest plot of hazard ratios for overall survival in prespecified subgroups. ",
    "Hazard ratios from unstratified Cox proportional-hazards models. ",
    "Squares represent point estimates; horizontal lines represent 95% CIs. ",
    "The dashed vertical line at HR=1 indicates no difference between treatment groups."
  )
)

png(file.path(tlf_dir, "figure_1b_os_forest.png"), width = 10, height = 7, units = "in", res = 300)
print(os_forest_plot)
dev.off()
message("[tlf] Figure 1B saved.")

# ============================================================================
# FIGURE 2A: DFS KAPLAN-MEIER
# ============================================================================

message("[tlf] Generating Figure 2A: DFS Kaplan-Meier...")

dfs_data <- adtte_full[PARAMCD == "DFS"]

# Fit KM
dfs_fit <- survfit(Surv(AVAL_MONTHS, EVENT) ~ TRT01P, data = dfs_data)

# Compute HR
dfs_hr <- compute_hr(dfs_data, "AVAL_MONTHS", "EVENT", "TRT01P")

# Event counts
dfs_ev_pembro <- dfs_data[TRT01P == "PEMBROLIZUMAB" & EVENT == 1, .N]
dfs_ev_placebo <- dfs_data[TRT01P == "PLACEBO" & EVENT == 1, .N]
dfs_event_text <- sprintf("Events: %d vs %d", dfs_ev_pembro, dfs_ev_placebo)

# Create plot
dfs_km <- ggsurvplot(
  dfs_fit,
  data = dfs_data,
  risk.table = TRUE,
  risk.table.col = "strata",
  risk.table.height = 0.25,
  pval = FALSE,
  conf.int = FALSE,
  palette = unname(arm_colors),
  xlab = "Time (Months)",
  ylab = "Disease-Free Survival Probability",
  title = "Figure 2A. Disease-Free Survival (ITT Population)",
  legend.title = "Treatment",
  legend.labs = c("Pembrolizumab", "Placebo"),
  break.time.by = 6,
  surv.median.line = "none",
  ggtheme = theme_classic(base_size = 11),
  risk.table.title = "Number at risk",
  risk.table.y.text = TRUE,
  fontsize = 3.5,
  tables.theme = theme_cleantable()
)

# Add annotations
hr_label_dfs <- sprintf("HR = %.2f (95%% CI: %.2f-%.2f)\np = %.4f\n%s",
                        dfs_hr$HR, dfs_hr$LCL, dfs_hr$UCL, dfs_hr$pval, dfs_event_text)

dfs_km$plot <- dfs_km$plot +
  annotate("text",
           x = max(dfs_data$AVAL_MONTHS, na.rm = TRUE) * 0.55,
           y = 0.25,
           label = hr_label_dfs,
           hjust = 0, vjust = 0.5, size = 3.5, fontface = "italic") +
  labs(caption = paste0(
    "Kaplan-Meier estimates of disease-free survival in the intention-to-treat population. ",
    "Disease-free survival defined as time from randomization to first recurrence or death. ",
    "Hazard ratio estimated using a stratified Cox proportional-hazards model. ",
    "P-value from stratified log-rank test. Tick marks indicate censored observations."
  ))

png(file.path(tlf_dir, "figure_2a_dfs_km.png"), width = 10, height = 7, units = "in", res = 300)
print(dfs_km)
dev.off()
message("[tlf] Figure 2A saved.")

# ============================================================================
# FIGURE 2B: DFS SUBGROUP FOREST PLOT
# ============================================================================

message("[tlf] Generating Figure 2B: DFS Forest Plot...")

dfs_forest_data <- generate_forest_data(adtte_full, "DFS")

dfs_forest_plot <- create_forest_plot(
  dfs_forest_data,
  title = "Figure 2B. Disease-Free Survival by Subgroup",
  caption_text = paste0(
    "Forest plot of hazard ratios for disease-free survival in prespecified subgroups. ",
    "Hazard ratios from unstratified Cox proportional-hazards models. ",
    "Squares represent point estimates; horizontal lines represent 95% CIs. ",
    "The dashed vertical line at HR=1 indicates no difference between treatment groups."
  )
)

png(file.path(tlf_dir, "figure_2b_dfs_forest.png"), width = 10, height = 7, units = "in", res = 300)
print(dfs_forest_plot)
dev.off()
message("[tlf] Figure 2B saved.")

# ============================================================================
# FIGURE S2A: OS KM FOR M0 INTERMEDIATE-HIGH RISK
# ============================================================================

message("[tlf] Generating Figure S2A: OS KM for M0 Intermediate-High Risk...")

os_m0_int <- adtte_full[PARAMCD == "OS" & RISK_CATEGORY == "M0_INT_HIGH"]

if (nrow(os_m0_int) > 20) {
  os_m0_int_fit <- survfit(Surv(AVAL_MONTHS, EVENT) ~ TRT01P, data = os_m0_int)
  os_m0_int_hr <- compute_hr(os_m0_int, "AVAL_MONTHS", "EVENT", "TRT01P")

  ev_p <- os_m0_int[TRT01P == "PEMBROLIZUMAB" & EVENT == 1, .N]
  ev_c <- os_m0_int[TRT01P == "PLACEBO" & EVENT == 1, .N]
  ev_text <- sprintf("Events: %d vs %d", ev_p, ev_c)

  os_m0_int_km <- ggsurvplot(
    os_m0_int_fit,
    data = os_m0_int,
    risk.table = TRUE,
    risk.table.col = "strata",
    risk.table.height = 0.25,
    pval = FALSE,
    conf.int = FALSE,
    palette = unname(arm_colors),
    xlab = "Time (Months)",
    ylab = "Overall Survival Probability",
    title = "Figure S2A. OS in Intermediate-High Risk (M0) Subgroup",
    legend.title = "Treatment",
    legend.labs = c("Pembrolizumab", "Placebo"),
    break.time.by = 6,
    surv.median.line = "none",
    ggtheme = theme_classic(base_size = 11),
    risk.table.title = "Number at risk",
    risk.table.y.text = TRUE,
    fontsize = 3.5,
    tables.theme = theme_cleantable()
  )

  hr_label <- sprintf("HR = %.2f (95%% CI: %.2f-%.2f)\np = %.4f\n%s",
                      os_m0_int_hr$HR, os_m0_int_hr$LCL, os_m0_int_hr$UCL,
                      os_m0_int_hr$pval, ev_text)

  os_m0_int_km$plot <- os_m0_int_km$plot +
    annotate("text",
             x = max(os_m0_int$AVAL_MONTHS, na.rm = TRUE) * 0.55,
             y = 0.25,
             label = hr_label,
             hjust = 0, vjust = 0.5, size = 3.5, fontface = "italic") +
    labs(caption = paste0(
      "Kaplan-Meier estimates of overall survival in patients with intermediate-high risk (T2 grade 4, ",
      "T3 any grade, without nodal involvement) who underwent nephrectomy. ",
      "Hazard ratio from Cox proportional-hazards model. Tick marks indicate censoring."
    ))

  png(file.path(tlf_dir, "figure_s2a_os_m0_int_high.png"),
      width = 10, height = 7, units = "in", res = 300)
  print(os_m0_int_km)
  dev.off()
  message("[tlf] Figure S2A saved.")
} else {
  message("[tlf] Figure S2A skipped: insufficient data in M0_INT_HIGH subgroup.")
}

# ============================================================================
# FIGURE S2B: OS KM FOR M0 HIGH RISK
# ============================================================================

message("[tlf] Generating Figure S2B: OS KM for M0 High Risk...")

os_m0_high <- adtte_full[PARAMCD == "OS" & RISK_CATEGORY == "M0_HIGH"]

if (nrow(os_m0_high) > 20) {
  os_m0_high_fit <- survfit(Surv(AVAL_MONTHS, EVENT) ~ TRT01P, data = os_m0_high)
  os_m0_high_hr <- compute_hr(os_m0_high, "AVAL_MONTHS", "EVENT", "TRT01P")

  ev_p <- os_m0_high[TRT01P == "PEMBROLIZUMAB" & EVENT == 1, .N]
  ev_c <- os_m0_high[TRT01P == "PLACEBO" & EVENT == 1, .N]
  ev_text <- sprintf("Events: %d vs %d", ev_p, ev_c)

  os_m0_high_km <- ggsurvplot(
    os_m0_high_fit,
    data = os_m0_high,
    risk.table = TRUE,
    risk.table.col = "strata",
    risk.table.height = 0.25,
    pval = FALSE,
    conf.int = FALSE,
    palette = unname(arm_colors),
    xlab = "Time (Months)",
    ylab = "Overall Survival Probability",
    title = "Figure S2B. OS in High Risk (M0) Subgroup",
    legend.title = "Treatment",
    legend.labs = c("Pembrolizumab", "Placebo"),
    break.time.by = 6,
    surv.median.line = "none",
    ggtheme = theme_classic(base_size = 11),
    risk.table.title = "Number at risk",
    risk.table.y.text = TRUE,
    fontsize = 3.5,
    tables.theme = theme_cleantable()
  )

  hr_label <- sprintf("HR = %.2f (95%% CI: %.2f-%.2f)\np = %.4f\n%s",
                      os_m0_high_hr$HR, os_m0_high_hr$LCL, os_m0_high_hr$UCL,
                      os_m0_high_hr$pval, ev_text)

  os_m0_high_km$plot <- os_m0_high_km$plot +
    annotate("text",
             x = max(os_m0_high$AVAL_MONTHS, na.rm = TRUE) * 0.55,
             y = 0.25,
             label = hr_label,
             hjust = 0, vjust = 0.5, size = 3.5, fontface = "italic") +
    labs(caption = paste0(
      "Kaplan-Meier estimates of overall survival in patients with high risk disease ",
      "(T4 any grade, any T with nodal involvement, or sarcomatoid features). ",
      "Hazard ratio from Cox proportional-hazards model. Tick marks indicate censoring."
    ))

  png(file.path(tlf_dir, "figure_s2b_os_m0_high.png"),
      width = 10, height = 7, units = "in", res = 300)
  print(os_m0_high_km)
  dev.off()
  message("[tlf] Figure S2B saved.")
} else {
  message("[tlf] Figure S2B skipped: insufficient data in M0_HIGH subgroup.")
}

# ============================================================================
# FIGURE S2C: OS KM FOR M1 NED
# ============================================================================

message("[tlf] Generating Figure S2C: OS KM for M1 NED...")

os_m1_ned <- adtte_full[PARAMCD == "OS" & RISK_CATEGORY == "M1_NED"]

if (nrow(os_m1_ned) > 20) {
  os_m1_ned_fit <- survfit(Surv(AVAL_MONTHS, EVENT) ~ TRT01P, data = os_m1_ned)
  os_m1_ned_hr <- compute_hr(os_m1_ned, "AVAL_MONTHS", "EVENT", "TRT01P")

  ev_p <- os_m1_ned[TRT01P == "PEMBROLIZUMAB" & EVENT == 1, .N]
  ev_c <- os_m1_ned[TRT01P == "PLACEBO" & EVENT == 1, .N]
  ev_text <- sprintf("Events: %d vs %d", ev_p, ev_c)

  os_m1_ned_km <- ggsurvplot(
    os_m1_ned_fit,
    data = os_m1_ned,
    risk.table = TRUE,
    risk.table.col = "strata",
    risk.table.height = 0.25,
    pval = FALSE,
    conf.int = FALSE,
    palette = unname(arm_colors),
    xlab = "Time (Months)",
    ylab = "Overall Survival Probability",
    title = "Figure S2C. OS in M1 NED Subgroup",
    legend.title = "Treatment",
    legend.labs = c("Pembrolizumab", "Placebo"),
    break.time.by = 6,
    surv.median.line = "none",
    ggtheme = theme_classic(base_size = 11),
    risk.table.title = "Number at risk",
    risk.table.y.text = TRUE,
    fontsize = 3.5,
    tables.theme = theme_cleantable()
  )

  hr_label <- sprintf("HR = %.2f (95%% CI: %.2f-%.2f)\np = %.4f\n%s",
                      os_m1_ned_hr$HR, os_m1_ned_hr$LCL, os_m1_ned_hr$UCL,
                      os_m1_ned_hr$pval, ev_text)

  os_m1_ned_km$plot <- os_m1_ned_km$plot +
    annotate("text",
             x = max(os_m1_ned$AVAL_MONTHS, na.rm = TRUE) * 0.55,
             y = 0.25,
             label = hr_label,
             hjust = 0, vjust = 0.5, size = 3.5, fontface = "italic") +
    labs(caption = paste0(
      "Kaplan-Meier estimates of overall survival in patients with M1 disease and no evidence ",
      "of disease (NED) after resection of oligometastases. ",
      "Hazard ratio from Cox proportional-hazards model. Tick marks indicate censoring."
    ))

  png(file.path(tlf_dir, "figure_s2c_os_m1_ned.png"),
      width = 10, height = 7, units = "in", res = 300)
  print(os_m1_ned_km)
  dev.off()
  message("[tlf] Figure S2C saved.")
} else {
  message("[tlf] Figure S2C skipped: insufficient data in M1_NED subgroup.")
}

# ============================================================================
# SUMMARY
# ============================================================================

message("")
message("=" |> rep(70) |> paste(collapse = ""))
message("[tlf] TLF generation complete.")
message(sprintf("[tlf] All outputs saved to: %s", normalizePath(tlf_dir, mustWork = FALSE)))
message("=" |> rep(70) |> paste(collapse = ""))
message("")
message("Tables generated:")
message("  - table_1_baseline_characteristics.csv")
message("  - table_2_subsequent_therapy.csv")
message("  - table_s2_dfs_events.csv")
message("  - table_s3_ae_summary.csv")
message("  - table_s5_trae_5pct.csv")
message("  - table_s7_immune_mediated_ae.csv")
message("")
message("Figures generated:")
message("  - figure_1a_os_km.png")
message("  - figure_1b_os_forest.png")
message("  - figure_2a_dfs_km.png")
message("  - figure_2b_dfs_forest.png")
message("  - figure_s2a_os_m0_int_high.png")
message("  - figure_s2b_os_m0_high.png")
message("  - figure_s2c_os_m1_ned.png")
