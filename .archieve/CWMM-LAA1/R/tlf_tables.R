# tlf_tables.R — Generate Tables matching publication shell
# ==========================================================
# Tables: 1 (demographics), 2 (endpoints), 3 (AEs), S1-S6 (appendix)

# Load source data
dm <- read.csv("output/source/dm.csv", stringsAsFactors = FALSE)
vs <- read.csv("output/source/vs.csv", stringsAsFactors = FALSE)
lb <- read.csv("output/source/lb.csv", stringsAsFactors = FALSE)
ae <- read.csv("output/source/ae.csv", stringsAsFactors = FALSE)
ds <- read.csv("output/source/ds.csv", stringsAsFactors = FALSE)
ef <- read.csv("output/source/ef.csv", stringsAsFactors = FALSE)
ex <- read.csv("output/source/ex.csv", stringsAsFactors = FALSE)

arms_order <- c("Placebo", "1mg", "3mg", "6mg", "9mg", "6to9mg", "3to9mg")
arm_labels <- c("Placebo\n(n=53)", "1 mg\n(n=28)", "3 mg\n(n=24)",
                "6 mg\n(n=28)", "9 mg\n(n=54)", "6-9 mg\n(n=24)", "3-9 mg\n(n=52)")

outdir <- "output/tlf"
dir.create(outdir, recursive = TRUE, showWarnings = FALSE)

# ============================================================
# TABLE 1: Demographic and clinical characteristics at baseline
# ============================================================
generate_table1 <- function() {
  # Merge baseline data
  bl_vs <- vs[vs$VISIT_WEEK == 0, ]
  bl_lb <- lb[lb$VISIT_WEEK == 0, ]
  dat <- merge(dm, bl_vs[, c("SUBJID", "WEIGHT", "BMI", "SYSBP", "DIABP", "PULSE")], by = "SUBJID")
  dat <- merge(dat, bl_lb[, c("SUBJID", "HBA1C", "GLUC", "INSULIN", "CHOL", "LDL", "HDL", "TRIG", "HSCRP")], by = "SUBJID")

  # Helper: mean(SD) or n(%)
  mean_sd <- function(x) sprintf("%.1f (%.1f)", mean(x, na.rm = TRUE), sd(x, na.rm = TRUE))
  n_pct <- function(x, val, n) sprintf("%d (%d%%)", sum(x == val, na.rm = TRUE), round(sum(x == val, na.rm = TRUE) / n * 100))

  rows <- list()
  for (arm in arms_order) {
    d <- dat[dat$ARM == arm, ]
    n <- nrow(d)
    rows[[arm]] <- c(
      N = as.character(n),
      Age = mean_sd(d$AGE),
      Female = n_pct(d$SEX, "Female", n),
      Male = n_pct(d$SEX, "Male", n),
      White = n_pct(d$RACE, "White", n),
      Black = n_pct(d$RACE, "Black", n),
      Other = n_pct(d$RACE, "Other", n),
      Bodyweight_kg = mean_sd(d$WEIGHT),
      BMI = mean_sd(d$BMI),
      HbA1c_mmol_mol = mean_sd(d$HBA1C),
      Fasting_glucose = mean_sd(d$GLUC),
      Fasting_insulin = mean_sd(d$INSULIN),
      Pulse = mean_sd(d$PULSE),
      SBP = mean_sd(d$SYSBP),
      DBP = mean_sd(d$DIABP),
      Total_cholesterol = mean_sd(d$CHOL),
      HDL = mean_sd(d$HDL),
      LDL = mean_sd(d$LDL),
      Triglycerides = mean_sd(d$TRIG),
      hsCRP = mean_sd(d$HSCRP)
    )
  }

  # Overall
  d <- dat
  n <- nrow(d)
  rows[["Overall"]] <- c(
    N = as.character(n),
    Age = mean_sd(d$AGE),
    Female = n_pct(d$SEX, "Female", n),
    Male = n_pct(d$SEX, "Male", n),
    White = n_pct(d$RACE, "White", n),
    Black = n_pct(d$RACE, "Black", n),
    Other = n_pct(d$RACE, "Other", n),
    Bodyweight_kg = mean_sd(d$WEIGHT),
    BMI = mean_sd(d$BMI),
    HbA1c_mmol_mol = mean_sd(d$HBA1C),
    Fasting_glucose = mean_sd(d$GLUC),
    Fasting_insulin = mean_sd(d$INSULIN),
    Pulse = mean_sd(d$PULSE),
    SBP = mean_sd(d$SYSBP),
    DBP = mean_sd(d$DIABP),
    Total_cholesterol = mean_sd(d$CHOL),
    HDL = mean_sd(d$HDL),
    LDL = mean_sd(d$LDL),
    Triglycerides = mean_sd(d$TRIG),
    hsCRP = mean_sd(d$HSCRP)
  )

  tbl1 <- do.call(cbind, rows)
  colnames(tbl1) <- c(arms_order, "Overall")
  rownames(tbl1) <- c("N", "Age, years", "Female", "Male", "White",
                       "Black or African American", "Other",
                       "Bodyweight, kg", "BMI, kg/m2",
                       "HbA1c, mmol/mol", "Fasting glucose, mmol/L",
                       "Fasting insulin, mIU/L", "Pulse, bpm",
                       "Systolic BP, mmHg", "Diastolic BP, mmHg",
                       "Total cholesterol, mmol/L", "HDL, mmol/L",
                       "LDL, mmol/L", "Triglycerides, mmol/L", "hsCRP, mg/L")

  write.csv(tbl1, file.path(outdir, "table1_demographics.csv"))
  cat("Table 1 written.\n")
  tbl1
}

# ============================================================
# TABLE 2: Secondary and exploratory endpoints, change from baseline
# ============================================================
generate_table2 <- function() {
  # Merge Week 48 data
  w48_vs <- vs[vs$VISIT_WEEK == 48, ]
  w48_lb <- lb[lb$VISIT_WEEK == 48, ]
  bl_vs <- vs[vs$VISIT_WEEK == 0, ]
  bl_lb <- lb[lb$VISIT_WEEK == 0, ]

  # Compute changes
  dat <- merge(
    bl_vs[, c("SUBJID", "WEIGHT", "BMI", "SYSBP", "DIABP", "PULSE")],
    w48_vs[, c("SUBJID", "WEIGHT", "BMI", "SYSBP", "DIABP", "PULSE")],
    by = "SUBJID", suffixes = c("_BL", "_W48")
  )
  dat_lb <- merge(
    bl_lb[, c("SUBJID", "HBA1C", "GLUC", "INSULIN", "CHOL", "LDL", "HDL", "TRIG", "HSCRP")],
    w48_lb[, c("SUBJID", "HBA1C", "GLUC", "INSULIN", "CHOL", "LDL", "HDL", "TRIG", "HSCRP")],
    by = "SUBJID", suffixes = c("_BL", "_W48")
  )
  dat <- merge(dat, dat_lb, by = "SUBJID")
  dat <- merge(dat, dm[, c("SUBJID", "ARM")], by = "SUBJID")

  # Compute deltas
  dat$d_weight <- dat$WEIGHT_W48 - dat$WEIGHT_BL
  dat$d_bmi <- dat$BMI_W48 - dat$BMI_BL
  dat$d_sbp <- dat$SYSBP_W48 - dat$SYSBP_BL
  dat$d_dbp <- dat$DIABP_W48 - dat$DIABP_BL
  dat$d_pulse <- dat$PULSE_W48 - dat$PULSE_BL
  dat$d_hba1c <- dat$HBA1C_W48 - dat$HBA1C_BL
  dat$d_glucose <- dat$GLUC_W48 - dat$GLUC_BL
  dat$pct_insulin <- (dat$INSULIN_W48 - dat$INSULIN_BL) / dat$INSULIN_BL * 100
  dat$pct_chol <- (dat$CHOL_W48 - dat$CHOL_BL) / dat$CHOL_BL * 100
  dat$pct_ldl <- (dat$LDL_W48 - dat$LDL_BL) / dat$LDL_BL * 100
  dat$pct_hdl <- (dat$HDL_W48 - dat$HDL_BL) / dat$HDL_BL * 100
  dat$pct_trig <- (dat$TRIG_W48 - dat$TRIG_BL) / dat$TRIG_BL * 100
  dat$pct_crp <- (dat$HSCRP_W48 - dat$HSCRP_BL) / dat$HSCRP_BL * 100

  # Format mean (95% CI)
  mean_ci <- function(x) {
    x <- x[!is.na(x)]
    if (length(x) < 3) return("--")
    m <- mean(x); se <- sd(x) / sqrt(length(x))
    sprintf("%.1f (%.1f to %.1f)", m, m - 1.96 * se, m + 1.96 * se)
  }
  mean_se <- function(x) {
    x <- x[!is.na(x)]
    if (length(x) < 3) return("--")
    sprintf("%.1f (%.1f)", mean(x), sd(x) / sqrt(length(x)))
  }

  vars <- c("d_weight", "d_bmi", "d_sbp", "d_dbp", "d_pulse",
            "d_hba1c", "d_glucose", "pct_insulin",
            "pct_chol", "pct_ldl", "pct_hdl", "pct_trig", "pct_crp")
  var_labels <- c("Bodyweight, kg", "BMI, kg/m2",
                  "Systolic BP, mmHg", "Diastolic BP, mmHg", "Pulse, bpm",
                  "HbA1c, mmol/mol", "Fasting glucose, mmol/L",
                  "Fasting insulin, % change",
                  "Total cholesterol, % change", "LDL, % change",
                  "HDL, % change", "Triglycerides, % change", "hsCRP, % change")

  rows <- list()
  for (arm in arms_order) {
    ad <- dat[dat$ARM == arm, ]
    row_vals <- sapply(vars, function(v) mean_ci(ad[[v]]))
    rows[[arm]] <- row_vals
  }

  tbl2 <- do.call(cbind, rows)
  colnames(tbl2) <- arms_order
  rownames(tbl2) <- var_labels

  # Add efficacy endpoint (% weight change from ef.csv)
  eff_row <- sapply(arms_order, function(arm) {
    x <- ef$PCT_CHANGE_48[ef$ARM == arm]
    x <- x[!is.na(x)]
    m <- mean(x); se <- sd(x) / sqrt(length(x))
    sprintf("%.1f (%.1f to %.1f)", m, m - 1.96 * se, m + 1.96 * se)
  })
  tbl2 <- rbind("% change bodyweight (efficacy)" = eff_row, tbl2)

  write.csv(tbl2, file.path(outdir, "table2_endpoints.csv"))
  cat("Table 2 written.\n")
  tbl2
}

# ============================================================
# TABLE 3: Adverse events
# ============================================================
generate_table3 <- function() {
  # Safety set = those who received at least one dose
  safety_set <- dm  # All 263 in our sim received treatment

  n_pct_ae <- function(arm, filter_fn = NULL) {
    arm_subj <- safety_set$SUBJID[safety_set$ARM == arm]
    n_arm <- length(arm_subj)
    if (!is.null(filter_fn)) {
      arm_ae <- ae[ae$ARM == arm & filter_fn(ae), ]
    } else {
      arm_ae <- ae[ae$ARM == arm, ]
    }
    n_with <- length(unique(arm_ae$SUBJID))
    sprintf("%d (%d%%)", n_with, round(n_with / n_arm * 100))
  }

  # Build table rows
  ae_terms <- c("nausea", "fatigue", "diarrhoea", "constipation",
                "decreased_appetite", "vomiting", "alopecia", "headache")
  ae_labels <- c("Nausea", "Fatigue", "Diarrhoea", "Constipation",
                 "Decreased appetite", "Vomiting", "Alopecia", "Headache")

  rows <- list()

  # Any AE
  rows[["Any AE"]] <- sapply(arms_order, function(arm) {
    n_arm <- sum(safety_set$ARM == arm)
    n_with <- length(unique(ae$SUBJID[ae$ARM == arm]))
    sprintf("%d (%d%%)", n_with, round(n_with / n_arm * 100))
  })

  # Serious AEs
  rows[["Serious AE"]] <- sapply(arms_order, function(arm) {
    n_arm <- sum(safety_set$ARM == arm)
    n_with <- length(unique(ae$SUBJID[ae$ARM == arm & ae$AESER == "Yes"]))
    sprintf("%d (%d%%)", n_with, round(n_with / n_arm * 100))
  })

  # AEs leading to discontinuation
  rows[["AE leading to discontinuation"]] <- sapply(arms_order, function(arm) {
    n_arm <- sum(safety_set$ARM == arm)
    n_disc <- sum(ds$ARM == arm & ds$TX_DISC_REASON == "Adverse Event", na.rm = TRUE)
    sprintf("%d (%d%%)", n_disc, round(n_disc / n_arm * 100))
  })

  # Individual AE terms
  for (i in seq_along(ae_terms)) {
    rows[[ae_labels[i]]] <- sapply(arms_order, function(arm) {
      n_arm <- sum(safety_set$ARM == arm)
      n_with <- length(unique(ae$SUBJID[ae$ARM == arm & ae$AETERM == ae_terms[i]]))
      sprintf("%d (%d%%)", n_with, round(n_with / n_arm * 100))
    })
  }

  tbl3 <- do.call(rbind, rows)
  colnames(tbl3) <- arms_order

  # Add pooled eloralintide and overall columns
  all_elora <- arms_order[arms_order != "Placebo"]
  n_pooled <- sum(safety_set$ARM %in% all_elora)
  n_overall <- nrow(safety_set)

  pooled_col <- c(
    sprintf("%d (%d%%)", length(unique(ae$SUBJID[ae$ARM %in% all_elora])), round(length(unique(ae$SUBJID[ae$ARM %in% all_elora])) / n_pooled * 100)),
    sprintf("%d (%d%%)", length(unique(ae$SUBJID[ae$ARM %in% all_elora & ae$AESER == "Yes"])), round(length(unique(ae$SUBJID[ae$ARM %in% all_elora & ae$AESER == "Yes"])) / n_pooled * 100)),
    sprintf("%d (%d%%)", sum(ds$ARM %in% all_elora & ds$TX_DISC_REASON == "Adverse Event", na.rm = TRUE), round(sum(ds$ARM %in% all_elora & ds$TX_DISC_REASON == "Adverse Event", na.rm = TRUE) / n_pooled * 100)),
    sapply(ae_terms, function(t) {
      n_with <- length(unique(ae$SUBJID[ae$ARM %in% all_elora & ae$AETERM == t]))
      sprintf("%d (%d%%)", n_with, round(n_with / n_pooled * 100))
    })
  )

  overall_col <- c(
    sprintf("%d (%d%%)", length(unique(ae$SUBJID)), round(length(unique(ae$SUBJID)) / n_overall * 100)),
    sprintf("%d (%d%%)", length(unique(ae$SUBJID[ae$AESER == "Yes"])), round(length(unique(ae$SUBJID[ae$AESER == "Yes"])) / n_overall * 100)),
    sprintf("%d (%d%%)", sum(ds$TX_DISC_REASON == "Adverse Event", na.rm = TRUE), round(sum(ds$TX_DISC_REASON == "Adverse Event", na.rm = TRUE) / n_overall * 100)),
    sapply(ae_terms, function(t) {
      n_with <- length(unique(ae$SUBJID[ae$AETERM == t]))
      sprintf("%d (%d%%)", n_with, round(n_with / n_overall * 100))
    })
  )

  tbl3 <- cbind(tbl3, "Pooled Elora" = pooled_col, "Overall" = overall_col)
  write.csv(tbl3, file.path(outdir, "table3_adverse_events.csv"))
  cat("Table 3 written.\n")
  tbl3
}

# ============================================================
# TABLE S3: GI and fatigue AEs by maximum severity
# ============================================================
generate_table_s3 <- function() {
  gi_terms <- c("nausea", "diarrhoea", "vomiting", "constipation")
  all_terms <- c(gi_terms, "fatigue")

  sev_levels <- c("Mild", "Moderate", "Severe")

  rows <- list()
  for (term in all_terms) {
    for (arm in arms_order) {
      n_arm <- sum(dm$ARM == arm)
      term_ae <- ae[ae$ARM == arm & ae$AETERM == term, ]
      # Get max severity per patient
      if (nrow(term_ae) > 0) {
        pat_max <- tapply(term_ae$AESEV, term_ae$SUBJID, function(s) {
          sev_num <- ifelse(s == "Severe", 3, ifelse(s == "Moderate", 2, 1))
          sev_levels[max(sev_num)]
        })
        n_mild <- sum(pat_max == "Mild")
        n_mod <- sum(pat_max == "Moderate")
        n_sev <- sum(pat_max == "Severe")
      } else {
        n_mild <- n_mod <- n_sev <- 0
      }
      rows[[paste(term, arm)]] <- c(
        AE = term, ARM = arm, N = n_arm,
        Mild = sprintf("%d (%d%%)", n_mild, round(n_mild / n_arm * 100)),
        Moderate = sprintf("%d (%d%%)", n_mod, round(n_mod / n_arm * 100)),
        Severe = sprintf("%d (%d%%)", n_sev, round(n_sev / n_arm * 100)),
        Total = sprintf("%d (%d%%)", n_mild + n_mod + n_sev, round((n_mild + n_mod + n_sev) / n_arm * 100))
      )
    }
  }

  tbl_s3 <- do.call(rbind, rows)
  write.csv(tbl_s3, file.path(outdir, "table_s3_ae_severity.csv"), row.names = FALSE)
  cat("Table S3 written.\n")
  tbl_s3
}

# ============================================================
# TABLE S6: Additional laboratory values at Week 48
# ============================================================
generate_table_s6 <- function() {
  bl_lb <- lb[lb$VISIT_WEEK == 0, ]
  w48_lb <- lb[lb$VISIT_WEEK == 48, ]

  dat <- merge(bl_lb, w48_lb, by = "SUBJID", suffixes = c("_BL", "_W48"))
  dat <- merge(dat, dm[, c("SUBJID", "ARM")], by = "SUBJID")

  vars <- c("HBA1C", "GLUC", "INSULIN", "CHOL", "LDL", "HDL", "TRIG", "HSCRP")
  var_labels <- c("HbA1c (mmol/mol)", "Fasting glucose (mmol/L)",
                  "Fasting insulin (mIU/L)", "Total cholesterol (mmol/L)",
                  "LDL (mmol/L)", "HDL (mmol/L)",
                  "Triglycerides (mmol/L)", "hsCRP (mg/L)")

  results <- list()
  for (arm in arms_order) {
    ad <- dat[dat$ARM == arm, ]
    arm_results <- list()
    for (i in seq_along(vars)) {
      v <- vars[i]
      bl_vals <- ad[[paste0(v, "_BL")]]
      w48_vals <- ad[[paste0(v, "_W48")]]
      change <- w48_vals - bl_vals
      arm_results[[var_labels[i]]] <- c(
        Baseline = sprintf("%.2f (%.2f)", mean(bl_vals, na.rm = TRUE), sd(bl_vals, na.rm = TRUE)),
        Week48 = sprintf("%.2f (%.2f)", mean(w48_vals, na.rm = TRUE), sd(w48_vals, na.rm = TRUE)),
        Change = sprintf("%.2f (%.2f)", mean(change, na.rm = TRUE), sd(change, na.rm = TRUE))
      )
    }
    results[[arm]] <- arm_results
  }

  # Format as wide table
  out_rows <- list()
  for (i in seq_along(var_labels)) {
    vl <- var_labels[i]
    for (metric in c("Baseline", "Week48", "Change")) {
      row <- sapply(arms_order, function(arm) results[[arm]][[vl]][metric])
      out_rows[[paste(vl, metric)]] <- row
    }
  }
  tbl_s6 <- do.call(rbind, out_rows)
  colnames(tbl_s6) <- arms_order

  write.csv(tbl_s6, file.path(outdir, "table_s6_lab_values.csv"))
  cat("Table S6 written.\n")
  tbl_s6
}

# ============================================================
# TABLE S8: Percentage weight loss at Week 48
# ============================================================
generate_table_s8 <- function() {
  thresholds <- c(5, 10, 15, 20, 25, 30)

  rows <- list()
  for (arm in arms_order) {
    arm_ef <- ef[ef$ARM == arm & !is.na(ef$PCT_CHANGE_48), ]
    n <- nrow(arm_ef)
    row <- c(N = n)
    for (thr in thresholds) {
      n_resp <- sum(arm_ef$PCT_CHANGE_48 <= -thr)
      row[paste0(">=", thr, "%")] <- sprintf("%d (%d%%)", n_resp, round(n_resp / n * 100))
    }
    rows[[arm]] <- row
  }

  tbl_s8 <- do.call(rbind, rows)
  write.csv(tbl_s8, file.path(outdir, "table_s8_responders.csv"))
  cat("Table S8 written.\n")
  tbl_s8
}

# ============================================================
# TABLE: Disposition summary
# ============================================================
generate_table_disposition <- function() {
  rows <- list()
  for (arm in arms_order) {
    arm_ds <- ds[ds$ARM == arm, ]
    n <- nrow(arm_ds)
    n_tx_disc <- sum(arm_ds$TX_DISC)
    n_study_disc <- sum(arm_ds$STUDY_DISC)
    n_ae_disc <- sum(arm_ds$TX_DISC_REASON == "Adverse Event", na.rm = TRUE)
    n_withdrawal <- sum(arm_ds$TX_DISC_REASON == "Withdrawal by Subject", na.rm = TRUE)
    n_ltfu <- sum(arm_ds$TX_DISC_REASON == "Lost to Follow-up", na.rm = TRUE)
    n_completed <- n - n_tx_disc

    rows[[arm]] <- c(
      N = n,
      "Completed treatment" = sprintf("%d (%d%%)", n_completed, round(n_completed / n * 100)),
      "Discontinued treatment" = sprintf("%d (%d%%)", n_tx_disc, round(n_tx_disc / n * 100)),
      "  Due to AE" = sprintf("%d (%d%%)", n_ae_disc, round(n_ae_disc / n * 100)),
      "  Withdrawal by participant" = sprintf("%d (%d%%)", n_withdrawal, round(n_withdrawal / n * 100)),
      "  Lost to follow-up" = sprintf("%d (%d%%)", n_ltfu, round(n_ltfu / n * 100)),
      "Discontinued study" = sprintf("%d (%d%%)", n_study_disc, round(n_study_disc / n * 100)),
      "Completed or continuing study" = sprintf("%d (%d%%)", n - n_study_disc, round((n - n_study_disc) / n * 100))
    )
  }

  tbl_disp <- do.call(cbind, rows)
  write.csv(tbl_disp, file.path(outdir, "table_disposition.csv"))
  cat("Disposition table written.\n")
  tbl_disp
}

# ============================================================
# RUN ALL TABLES
# ============================================================
cat("=== Generating Tables ===\n\n")
generate_table1()
generate_table2()
generate_table3()
generate_table_s3()
generate_table_s6()
generate_table_s8()
generate_table_disposition()
cat("\nAll tables written to output/tlf/\n")
