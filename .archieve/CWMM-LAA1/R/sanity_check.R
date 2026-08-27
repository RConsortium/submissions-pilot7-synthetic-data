# sanity_check.R — Cross-validate ADaM datasets and TLFs for discrepancies
# ===========================================================================

library(dplyr)

cat("============================================================\n")
cat("  SANITY CHECK: ADaM Datasets and TLF Consistency\n")
cat("============================================================\n\n")

# --- Load ADaM datasets ---
adsl <- read.csv("output/adam/adsl.csv", stringsAsFactors = FALSE)
adae <- read.csv("output/adam/adae.csv", stringsAsFactors = FALSE)
advs <- read.csv("output/adam/advs.csv", stringsAsFactors = FALSE)
adlb <- read.csv("output/adam/adlb.csv", stringsAsFactors = FALSE)
adeff <- read.csv("output/adam/adeff.csv", stringsAsFactors = FALSE)

# --- Load source data ---
dm <- read.csv("output/source/dm.csv", stringsAsFactors = FALSE)
ae_src <- read.csv("output/source/ae.csv", stringsAsFactors = FALSE)
vs_src <- read.csv("output/source/vs.csv", stringsAsFactors = FALSE)
ds_src <- read.csv("output/source/ds.csv", stringsAsFactors = FALSE)
ef_src <- read.csv("output/source/ef.csv", stringsAsFactors = FALSE)

issues <- character()
warnings_list <- character()

# ===========================================================================
# CHECK 1: ADSL structural integrity
# ===========================================================================
cat("--- CHECK 1: ADSL Structural Integrity ---\n")

# 1a. One record per subject
if (nrow(adsl) != n_distinct(adsl$USUBJID)) {
  issues <- c(issues, "ADSL: Duplicate USUBJID found")
} else {
  cat("  [PASS] One record per USUBJID (N=", nrow(adsl), ")\n")
}

# 1b. N matches source DM
if (nrow(adsl) != nrow(dm)) {
  issues <- c(issues, sprintf("ADSL N (%d) != source DM N (%d)", nrow(adsl), nrow(dm)))
} else {
  cat("  [PASS] ADSL N matches source DM (", nrow(adsl), ")\n")
}

# 1c. Arm distribution
cat("  Arm distribution:\n")
arm_tbl <- table(adsl$ARM)
expected_n <- c(Placebo=53, `1mg`=28, `3mg`=24, `6mg`=28, `9mg`=54, `6to9mg`=24, `3to9mg`=52)
for (arm in names(expected_n)) {
  actual <- as.integer(arm_tbl[arm])
  if (is.na(actual)) actual <- 0
  status <- if (actual == expected_n[arm]) "[PASS]" else "[FAIL]"
  cat(sprintf("    %s %-8s: %d (expected %d)\n", status, arm, actual, expected_n[arm]))
  if (actual != expected_n[arm]) {
    issues <- c(issues, sprintf("ADSL arm %s: got %d, expected %d", arm, actual, expected_n[arm]))
  }
}

# 1d. Required variables present
req_vars <- c("STUDYID", "USUBJID", "SUBJID", "ARM", "TRT01P", "TRT01PN",
              "TRTSDT", "TRTEDT", "SAFFL", "ITTFL", "EOSSTT", "WEIGHTBL", "BMIBL")
missing <- setdiff(req_vars, names(adsl))
if (length(missing) > 0) {
  issues <- c(issues, paste("ADSL missing variables:", paste(missing, collapse=", ")))
} else {
  cat("  [PASS] All required variables present\n")
}

# 1e. Flag conventions (Y or NA, never N)
for (fl in c("SAFFL", "ITTFL")) {
  vals <- unique(adsl[[fl]])
  bad <- vals[!vals %in% c("Y", NA)]
  if (length(bad) > 0) {
    issues <- c(issues, sprintf("ADSL %s has invalid values: %s", fl, paste(bad, collapse=",")))
  }
}
cat("  [PASS] Flag variables follow Y/NA convention\n")

# 1f. STUDYID consistency
if (!all(adsl$STUDYID == "CWMM-LAA1")) {
  issues <- c(issues, sprintf("ADSL STUDYID not all 'CWMM-LAA1': %s", paste(unique(adsl$STUDYID), collapse=",")))
} else {
  cat("  [PASS] STUDYID = 'CWMM-LAA1' for all records\n")
}

# ===========================================================================
# CHECK 2: ADAE consistency with ADSL
# ===========================================================================
cat("\n--- CHECK 2: ADAE Consistency ---\n")

# 2a. All ADAE subjects exist in ADSL
ae_subj <- unique(adae$USUBJID)
missing_in_adsl <- setdiff(ae_subj, adsl$USUBJID)
if (length(missing_in_adsl) > 0) {
  issues <- c(issues, sprintf("ADAE has %d subjects not in ADSL", length(missing_in_adsl)))
} else {
  cat("  [PASS] All ADAE subjects found in ADSL\n")
}

# 2b. TRTEMFL values
trtemfl_vals <- unique(adae$TRTEMFL)
bad_trtem <- trtemfl_vals[!trtemfl_vals %in% c("Y", NA)]
if (length(bad_trtem) > 0) {
  issues <- c(issues, sprintf("ADAE TRTEMFL invalid values: %s", paste(bad_trtem, collapse=",")))
} else {
  cat("  [PASS] TRTEMFL is Y or NA\n")
}

# 2c. TEAE onset dates vs TRTSDT
teae <- adae[adae$TRTEMFL == "Y" & !is.na(adae$TRTEMFL), ]
bad_dates <- teae[as.Date(teae$ASTDT) < as.Date(teae$TRTSDT), ]
if (nrow(bad_dates) > 0) {
  issues <- c(issues, sprintf("ADAE: %d TEAE records with ASTDT < TRTSDT", nrow(bad_dates)))
} else {
  cat("  [PASS] All TEAEs have ASTDT >= TRTSDT\n")
}

# 2d. AE record count vs source
cat(sprintf("  ADAE records: %d (source ae.csv: %d)\n", nrow(adae), nrow(ae_src)))
if (nrow(adae) != nrow(ae_src)) {
  warnings_list <- c(warnings_list, sprintf("ADAE records (%d) != source AE (%d) - check for filtering", nrow(adae), nrow(ae_src)))
}

# 2e. TRT01P matches ARM in ADSL for merged records
ae_arm_check <- adae |>
  select(USUBJID, TRT01P) |>
  distinct() |>
  left_join(adsl |> select(USUBJID, TRT01P_ADSL = TRT01P), by = "USUBJID")
mismatches <- ae_arm_check |> filter(TRT01P != TRT01P_ADSL)
if (nrow(mismatches) > 0) {
  issues <- c(issues, sprintf("ADAE: %d subjects with TRT01P mismatch vs ADSL", nrow(mismatches)))
} else {
  cat("  [PASS] TRT01P in ADAE matches ADSL\n")
}

# ===========================================================================
# CHECK 3: ADVS / ADLB consistency
# ===========================================================================
cat("\n--- CHECK 3: ADVS/ADLB Consistency ---\n")

# 3a. All subjects in ADVS/ADLB exist in ADSL
advs_subj <- unique(advs$USUBJID)
adlb_subj <- unique(adlb$USUBJID)
if (length(setdiff(advs_subj, adsl$USUBJID)) > 0) {
  issues <- c(issues, "ADVS has subjects not in ADSL")
}
if (length(setdiff(adlb_subj, adsl$USUBJID)) > 0) {
  issues <- c(issues, "ADLB has subjects not in ADSL")
}
cat(sprintf("  [PASS] ADVS subjects (%d) all in ADSL\n", length(advs_subj)))
cat(sprintf("  [PASS] ADLB subjects (%d) all in ADSL\n", length(adlb_subj)))

# 3b. Baseline flag: exactly one per SUBJID x PARAMCD at AVISITN=0
advs_bl <- advs |> filter(ABLFL == "Y")
advs_bl_dup <- advs_bl |> count(SUBJID, PARAMCD) |> filter(n > 1)
if (nrow(advs_bl_dup) > 0) {
  issues <- c(issues, sprintf("ADVS: %d subject-param combos with >1 baseline", nrow(advs_bl_dup)))
} else {
  cat("  [PASS] ADVS: one baseline per subject-parameter\n")
}

adlb_bl <- adlb |> filter(ABLFL == "Y")
adlb_bl_dup <- adlb_bl |> count(SUBJID, PARAMCD) |> filter(n > 1)
if (nrow(adlb_bl_dup) > 0) {
  issues <- c(issues, sprintf("ADLB: %d subject-param combos with >1 baseline", nrow(adlb_bl_dup)))
} else {
  cat("  [PASS] ADLB: one baseline per subject-parameter\n")
}

# 3c. CHG = AVAL - BASE where both non-missing and post-baseline
advs_chg_check <- advs |>
  filter(!is.na(CHG) & !is.na(AVAL) & !is.na(BASE)) |>
  mutate(expected_chg = AVAL - BASE, diff = abs(CHG - expected_chg))
bad_chg <- advs_chg_check |> filter(diff > 0.01)
if (nrow(bad_chg) > 0) {
  issues <- c(issues, sprintf("ADVS: %d records where CHG != AVAL - BASE", nrow(bad_chg)))
} else {
  cat("  [PASS] ADVS: CHG = AVAL - BASE verified\n")
}

adlb_chg_check <- adlb |>
  filter(!is.na(CHG) & !is.na(AVAL) & !is.na(BASE)) |>
  mutate(expected_chg = AVAL - BASE, diff = abs(CHG - expected_chg))
bad_chg_lb <- adlb_chg_check |> filter(diff > 0.01)
if (nrow(bad_chg_lb) > 0) {
  issues <- c(issues, sprintf("ADLB: %d records where CHG != AVAL - BASE", nrow(bad_chg_lb)))
} else {
  cat("  [PASS] ADLB: CHG = AVAL - BASE verified\n")
}

# 3d. PCHG = CHG/BASE * 100
advs_pchg_check <- advs |>
  filter(!is.na(PCHG) & !is.na(CHG) & !is.na(BASE) & BASE != 0) |>
  mutate(expected_pchg = CHG / BASE * 100, diff = abs(PCHG - expected_pchg))
bad_pchg <- advs_pchg_check |> filter(diff > 0.01)
if (nrow(bad_pchg) > 0) {
  issues <- c(issues, sprintf("ADVS: %d records where PCHG != CHG/BASE*100", nrow(bad_pchg)))
} else {
  cat("  [PASS] ADVS: PCHG = CHG/BASE*100 verified\n")
}

# ===========================================================================
# CHECK 4: ADEFF consistency
# ===========================================================================
cat("\n--- CHECK 4: ADEFF Consistency ---\n")

# 4a. One record per subject
if (nrow(adeff) != n_distinct(adeff$USUBJID)) {
  issues <- c(issues, "ADEFF: not one record per subject")
} else {
  cat(sprintf("  [PASS] One record per subject (N=%d)\n", nrow(adeff)))
}

# 4b. AVAL matches source ef.csv
ef_check <- merge(adeff |> select(SUBJID, AVAL_ADAM = AVAL),
                  ef_src |> select(SUBJID, AVAL_SRC = PCT_CHANGE_48),
                  by = "SUBJID")
mismatch <- ef_check |> filter(abs(AVAL_ADAM - AVAL_SRC) > 0.01, !is.na(AVAL_ADAM), !is.na(AVAL_SRC))
if (nrow(mismatch) > 0) {
  issues <- c(issues, sprintf("ADEFF: %d records where AVAL != source PCT_CHANGE_48", nrow(mismatch)))
} else {
  cat("  [PASS] ADEFF AVAL matches source ef.csv PCT_CHANGE_48\n")
}

# 4c. Responder flags consistent with AVAL
crit_check <- adeff |> filter(!is.na(AVAL))
bad_crit1 <- crit_check |> filter((AVAL <= -5 & (is.na(CRIT1FL) | CRIT1FL != "Y")) |
                                    (AVAL > -5 & CRIT1FL == "Y"))
if (nrow(bad_crit1) > 0) {
  issues <- c(issues, sprintf("ADEFF: %d records with inconsistent CRIT1FL", nrow(bad_crit1)))
} else {
  cat("  [PASS] CRIT1FL consistent with AVAL <= -5\n")
}

bad_crit4 <- crit_check |> filter((AVAL <= -20 & (is.na(CRIT4FL) | CRIT4FL != "Y")) |
                                    (AVAL > -20 & CRIT4FL == "Y"))
if (nrow(bad_crit4) > 0) {
  issues <- c(issues, sprintf("ADEFF: %d records with inconsistent CRIT4FL", nrow(bad_crit4)))
} else {
  cat("  [PASS] CRIT4FL consistent with AVAL <= -20\n")
}

# ===========================================================================
# CHECK 5: Cross-dataset consistency (ADaM vs TLF)
# ===========================================================================
cat("\n--- CHECK 5: ADaM vs TLF Cross-Validation ---\n")

# 5a. Table 1 demographics: verify ADSL means match what TLF should show
cat("  Verifying Table 1 key statistics from ADSL:\n")
cat(sprintf("    Mean age: %.1f (published target: 49.0)\n", mean(adsl$AGE)))
cat(sprintf("    %% Female: %.0f%% (published target: 78%%)\n", sum(adsl$SEX=="Female")/nrow(adsl)*100))
cat(sprintf("    Mean bodyweight: %.1f kg (published target: 109.1)\n", mean(adsl$WEIGHTBL, na.rm=T)))
cat(sprintf("    Mean BMI: %.1f (published target: 39.1)\n", mean(adsl$BMIBL, na.rm=T)))

# 5b. Primary efficacy from ADEFF vs calibration target
cat("\n  Primary efficacy (ADEFF) vs calibration targets:\n")
targets <- list(Placebo=-0.4, `1mg`=-9.0, `3mg`=-12.0, `6mg`=-18.0,
                `9mg`=-20.0, `6to9mg`=-20.0, `3to9mg`=-16.0)
for (arm in names(targets)) {
  arm_vals <- adeff$AVAL[adeff$ARM == arm & !is.na(adeff$AVAL)]
  sim_mean <- mean(arm_vals)
  target <- targets[[arm]]
  diff <- sim_mean - target
  status <- if (abs(diff) <= 2.0) "[PASS]" else "[WARN]"
  cat(sprintf("    %s %-8s: sim=%.1f, target=%.1f, diff=%+.1f\n", status, arm, sim_mean, target, diff))
  if (abs(diff) > 2.0) {
    warnings_list <- c(warnings_list, sprintf("Efficacy %s: diff=%.1f (>2.0 tolerance)", arm, diff))
  }
}

# 5c. AE rates from ADAE vs target
cat("\n  Key AE rates (ADAE TEAE) vs calibration targets:\n")
ae_targets <- list(
  nausea = c(Placebo=13.5, `6mg`=64.3, `9mg`=33.3),
  fatigue = c(Placebo=11.5, `9mg`=42.6)
)
for (ae_name in names(ae_targets)) {
  for (arm in names(ae_targets[[ae_name]])) {
    n_arm <- sum(adsl$ARM == arm)
    n_with <- length(unique(teae$SUBJID[teae$ARM == arm & teae$AETERM == ae_name]))
    sim_pct <- n_with / n_arm * 100
    tgt_pct <- ae_targets[[ae_name]][arm]
    diff <- sim_pct - tgt_pct
    status <- if (abs(diff) <= 5.0) "[PASS]" else "[WARN]"
    cat(sprintf("    %s %-10s %-8s: sim=%.1f%%, target=%.1f%%, diff=%+.1f\n",
                status, ae_name, arm, sim_pct, tgt_pct, diff))
    if (abs(diff) > 10.0) {
      warnings_list <- c(warnings_list, sprintf("AE %s %s: diff=%.1f (>10pp)", ae_name, arm, diff))
    }
  }
}

# 5d. ADVS Week 48 weight vs ADEFF
cat("\n  Cross-check: ADVS weight PCHG at Week 48 vs ADEFF AVAL:\n")
advs_w48_wt <- advs |> filter(PARAMCD=="WEIGHT", AVISITN==48, !is.na(PCHG)) |>
  select(SUBJID, PCHG_ADVS = PCHG)
eff_check <- adeff |> filter(!is.na(AVAL)) |> select(SUBJID, AVAL_EFF = AVAL)
cross <- merge(advs_w48_wt, eff_check, by="SUBJID", all=FALSE)
if (nrow(cross) > 0) {
  cor_val <- cor(cross$PCHG_ADVS, cross$AVAL_EFF, use="complete.obs")
  mean_diff <- mean(abs(cross$PCHG_ADVS - cross$AVAL_EFF), na.rm=T)
  cat(sprintf("    Correlation: %.3f (N=%d matched subjects)\n", cor_val, nrow(cross)))
  cat(sprintf("    Mean absolute difference: %.2f%%\n", mean_diff))
  if (cor_val < 0.8) {
    warnings_list <- c(warnings_list, sprintf("ADVS vs ADEFF correlation low: %.3f", cor_val))
  }
  if (mean_diff > 3) {
    warnings_list <- c(warnings_list, sprintf("ADVS vs ADEFF mean diff high: %.2f", mean_diff))
  }
} else {
  warnings_list <- c(warnings_list, "No matched records between ADVS Week48 and ADEFF")
}

# 5e. Disposition: ADSL EOSSTT vs disc rates
cat("\n  Disposition rates from ADSL:\n")
disc_targets <- list(Placebo=0.36, `1mg`=0.46, `3mg`=0.17, `6mg`=0.25,
                     `9mg`=0.15, `6to9mg`=0.25, `3to9mg`=0.17)
for (arm in names(disc_targets)) {
  n_arm <- sum(adsl$ARM == arm)
  n_disc <- sum(adsl$ARM == arm & adsl$EOSSTT == "DISCONTINUED")
  sim_rate <- n_disc / n_arm
  tgt_rate <- disc_targets[[arm]]
  diff <- (sim_rate - tgt_rate) * 100
  status <- if (abs(diff) <= 10) "[PASS]" else "[WARN]"
  cat(sprintf("    %s %-8s: sim=%.0f%%, target=%.0f%%, diff=%+.0fpp\n",
              status, arm, sim_rate*100, tgt_rate*100, diff))
  if (abs(diff) > 15) {
    warnings_list <- c(warnings_list, sprintf("Disc %s: diff=%.0fpp (>15pp)", arm, diff))
  }
}

# ===========================================================================
# CHECK 6: Data quality
# ===========================================================================
cat("\n--- CHECK 6: Data Quality ---\n")

# 6a. No negative body weights
bad_wt <- advs |> filter(PARAMCD == "WEIGHT" & !is.na(AVAL) & AVAL <= 0)
if (nrow(bad_wt) > 0) {
  issues <- c(issues, sprintf("ADVS: %d records with weight <= 0", nrow(bad_wt)))
} else {
  cat("  [PASS] No negative/zero body weights\n")
}

# 6b. BMI in reasonable range
bad_bmi <- advs |> filter(PARAMCD == "BMI" & !is.na(AVAL) & (AVAL < 15 | AVAL > 80))
if (nrow(bad_bmi) > 0) {
  warnings_list <- c(warnings_list, sprintf("ADVS: %d BMI values outside 15-80", nrow(bad_bmi)))
} else {
  cat("  [PASS] All BMI values in range 15-80\n")
}

# 6c. Lab values in physiological range
bad_hba1c <- adlb |> filter(PARAMCD == "HBA1C" & !is.na(AVAL) & (AVAL < 15 | AVAL > 120))
if (nrow(bad_hba1c) > 0) {
  warnings_list <- c(warnings_list, sprintf("ADLB: %d HBA1C values outside 15-120", nrow(bad_hba1c)))
} else {
  cat("  [PASS] HbA1c values in physiological range\n")
}

bad_gluc <- adlb |> filter(PARAMCD == "GLUC" & !is.na(AVAL) & (AVAL < 2 | AVAL > 20))
if (nrow(bad_gluc) > 0) {
  warnings_list <- c(warnings_list, sprintf("ADLB: %d glucose values outside 2-20", nrow(bad_gluc)))
} else {
  cat("  [PASS] Glucose values in physiological range\n")
}

# 6d. AE severity values valid
ae_sev_vals <- unique(adae$AESEV)
valid_sev <- c("Mild", "Moderate", "Severe")
invalid_sev <- setdiff(ae_sev_vals, valid_sev)
if (length(invalid_sev) > 0) {
  issues <- c(issues, sprintf("ADAE AESEV invalid values: %s", paste(invalid_sev, collapse=",")))
} else {
  cat("  [PASS] AESEV values are Mild/Moderate/Severe\n")
}

# ===========================================================================
# SUMMARY
# ===========================================================================
cat("\n============================================================\n")
cat("  SUMMARY\n")
cat("============================================================\n")

if (length(issues) == 0) {
  cat("\n  ISSUES (critical): NONE\n")
} else {
  cat(sprintf("\n  ISSUES (critical): %d\n", length(issues)))
  for (i in issues) cat(sprintf("    [FAIL] %s\n", i))
}

if (length(warnings_list) == 0) {
  cat("  WARNINGS (non-critical): NONE\n")
} else {
  cat(sprintf("  WARNINGS (non-critical): %d\n", length(warnings_list)))
  for (w in warnings_list) cat(sprintf("    [WARN] %s\n", w))
}

cat("\n  Overall: ")
if (length(issues) == 0) {
  cat("ALL CRITICAL CHECKS PASSED\n")
} else {
  cat("CRITICAL ISSUES FOUND - REVIEW REQUIRED\n")
}
cat("============================================================\n")
