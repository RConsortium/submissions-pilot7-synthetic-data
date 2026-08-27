# validate.R — Quick validation of output data
# ==============================================

dm <- read.csv("output/source/dm.csv")
cat("=== Demographics ===\n")
cat("N:", nrow(dm), "\n")
cat("Arms:\n")
print(table(dm$ARM))
cat("\nSex:\n")
print(table(dm$SEX))
cat("\nRace:\n")
print(table(dm$RACE))
cat("\nAge: mean=", round(mean(dm$AGE), 1), " sd=", round(sd(dm$AGE), 1), "\n")

vs <- read.csv("output/source/vs.csv")
cat("\n=== Vitals ===\n")
cat("Rows:", nrow(vs), "\n")
bl_wt <- vs$WEIGHT[vs$VISIT_WEEK == 0]
cat("Baseline weight: mean=", round(mean(bl_wt, na.rm = TRUE), 1),
    " sd=", round(sd(bl_wt, na.rm = TRUE), 1), "\n")

ae <- read.csv("output/source/ae.csv")
cat("\n=== AE ===\n")
cat("Total AE records:", nrow(ae), "\n")
cat("Patients with AE:", length(unique(ae$SUBJID)), "/", nrow(dm), "\n")
cat("AE terms:\n")
print(sort(table(ae$AETERM), decreasing = TRUE))

ef <- read.csv("output/source/ef.csv")
cat("\n=== Efficacy: % weight change at Week 48 ===\n")
arms <- c("Placebo", "1mg", "3mg", "6mg", "9mg", "6to9mg", "3to9mg")
for (arm in arms) {
  vals <- ef$PCT_CHANGE_48[ef$ARM == arm]
  cat(sprintf("  %-8s: mean=%6.1f  sd=%5.1f  n=%d\n",
              arm, mean(vals, na.rm = TRUE), sd(vals, na.rm = TRUE), sum(!is.na(vals))))
}

ds <- read.csv("output/source/ds.csv")
cat("\n=== Disposition ===\n")
for (arm in arms) {
  arm_ds <- ds[ds$ARM == arm, ]
  n <- nrow(arm_ds)
  cat(sprintf("  %-8s: tx_disc=%4.1f%%  study_disc=%4.1f%%  (n=%d)\n",
              arm,
              sum(arm_ds$TX_DISC) / n * 100,
              sum(arm_ds$STUDY_DISC) / n * 100,
              n))
}

lb <- read.csv("output/source/lb.csv")
cat("\n=== Labs (baseline) ===\n")
bl_lb <- lb[lb$VISIT_WEEK == 0, ]
cat("HbA1c: mean=", round(mean(bl_lb$HBA1C, na.rm = TRUE), 1), "\n")
cat("Glucose: mean=", round(mean(bl_lb$GLUC, na.rm = TRUE), 2), "\n")
cat("Trig: mean=", round(mean(bl_lb$TRIG, na.rm = TRUE), 2), "\n")
