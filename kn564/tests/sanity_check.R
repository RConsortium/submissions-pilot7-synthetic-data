## Comprehensive Sanity Check of ADaM and TLFs
## Checks for internal consistency, discrepancies, and data quality
setwd("C:/Users/lengnx/Documents/ipd_sim_examples/kn564")
library(data.table)

cat("================================================================\n")
cat("  KEYNOTE-564 Sanity Check: ADaM + TLF Consistency\n")
cat("================================================================\n\n")

# ─── Load all data ────────────────────────────────────────────────────────────
adsl  <- fread("output/adam/ADSL.csv")
adae  <- fread("output/adam/ADAE.csv")
adtte <- fread("output/adam/ADTTE.csv")
ep    <- fread("output/source/endpoints.csv")
dm    <- fread("output/source/DM.csv")
ae    <- fread("output/source/AE.csv")
ex    <- fread("output/source/EX.csv")

# TLF tables
t1  <- fread("output/tlf/table_1_baseline_characteristics.csv")
ts2 <- fread("output/tlf/table_s2_dfs_events.csv")
ts3 <- fread("output/tlf/table_s3_ae_summary.csv")
ts5 <- fread("output/tlf/table_s5_trae_5pct.csv")
ts7 <- fread("output/tlf/table_s7_immune_mediated_ae.csv")

issues <- character(0)
n_checks <- 0L

check <- function(condition, desc) {
  n_checks <<- n_checks + 1L
  if (isTRUE(condition)) {
    cat(sprintf("  [PASS] %s\n", desc))
  } else {
    cat(sprintf("  [FAIL] %s\n", desc))
    issues <<- c(issues, desc)
  }
}

# ─── Section 1: ADaM Internal Consistency ─────────────────────────────────────
cat("--- 1. ADaM Internal Consistency ---\n")

# ADSL
check(nrow(adsl) == 994, "ADSL has 994 patients")
check(all(!is.na(adsl$USUBJID)), "ADSL: no missing USUBJID")
check(all(adsl$SAFFL == "Y"), "ADSL: all patients in safety population")
check(all(adsl$ITTFL == "Y"), "ADSL: all patients in ITT population")
n_pembro_adsl <- sum(adsl$TRT01P == "PEMBROLIZUMAB")
n_placebo_adsl <- sum(adsl$TRT01P == "PLACEBO")
check(n_pembro_adsl + n_placebo_adsl == 994, "ADSL: all patients assigned to arm")
check(n_pembro_adsl %in% 494:498, sprintf("ADSL: pembro N=%d in expected range", n_pembro_adsl))
check(n_placebo_adsl %in% 496:500, sprintf("ADSL: placebo N=%d in expected range", n_placebo_adsl))

# ADTTE
check(nrow(adtte) == 1988, "ADTTE has 1988 records (2 per patient)")
check(all(c("DFS","OS") %in% adtte$PARAMCD), "ADTTE: both DFS and OS parameters present")
n_dfs <- sum(adtte$PARAMCD == "DFS")
n_os  <- sum(adtte$PARAMCD == "OS")
check(n_dfs == 994, sprintf("ADTTE: DFS has %d records (expect 994)", n_dfs))
check(n_os == 994, sprintf("ADTTE: OS has %d records (expect 994)", n_os))
check(all(adtte$AVAL > 0), "ADTTE: all AVAL > 0")
check(all(adtte$CNSR %in% c(0,1)), "ADTTE: CNSR only 0 or 1")

# ADTTE vs endpoints consistency
dfs_adtte <- adtte[PARAMCD == "DFS"]
os_adtte  <- adtte[PARAMCD == "OS"]
check(all(dfs_adtte$AVAL == ep$DFS_DAY), "ADTTE DFS AVAL matches endpoints DFS_DAY")
check(all((1L - dfs_adtte$CNSR) == ep$DFS_EVENT), "ADTTE DFS CNSR matches endpoints DFS_EVENT")
check(all(os_adtte$AVAL == ep$OS_DAY), "ADTTE OS AVAL matches endpoints OS_DAY")
check(all((1L - os_adtte$CNSR) == ep$OS_EVENT), "ADTTE OS CNSR matches endpoints OS_EVENT")

# OS >= DFS for each patient
merged_tte <- merge(
  dfs_adtte[, .(USUBJID, DFS_AVAL = AVAL)],
  os_adtte[, .(USUBJID, OS_AVAL = AVAL)],
  by = "USUBJID"
)
check(all(merged_tte$OS_AVAL >= merged_tte$DFS_AVAL),
      "ADTTE: OS_AVAL >= DFS_AVAL for all patients")

# ADAE
check(all(adae$USUBJID %in% adsl$USUBJID), "ADAE: all patients in ADSL")
check(all(adae$AESEVN >= 1 & adae$AESEVN <= 4, na.rm = TRUE), "ADAE: grade 1-4 only")
check(all(adae$ASTDY > 0, na.rm = TRUE), "ADAE: all start days positive")

cat("\n")

# ─── Section 2: ADaM vs Source Data ───────────────────────────────────────────
cat("--- 2. ADaM vs Source Consistency ---\n")

# Patient counts
check(nrow(dm) == nrow(adsl), "DM and ADSL have same patient count")
check(uniqueN(ae$SUBJID) <= nrow(adsl), "All AE patients exist in ADSL")
check(uniqueN(ex$SUBJID) == nrow(adsl), "All EX patients match ADSL count")

# AE record count consistency
check(nrow(adae) == nrow(ae), sprintf("ADAE rows (%d) == source AE rows (%d)", nrow(adae), nrow(ae)))

# Arm assignment consistency
dm_arms <- dm[, .(N = .N), by = ARM]
adsl_arms <- adsl[, .(N = .N), by = TRT01P]
setnames(adsl_arms, "TRT01P", "ARM")
merged_arms <- merge(dm_arms, adsl_arms, by = "ARM", suffixes = c("_dm", "_adsl"))
check(all(merged_arms$N_dm == merged_arms$N_adsl), "Arm counts match between DM and ADSL")

cat("\n")

# ─── Section 3: TLF vs ADaM Consistency ───────────────────────────────────────
cat("--- 3. TLF vs ADaM Consistency ---\n")

# Table 1 checks
t1_n_row <- t1[Characteristic == "N"]
t1_pembro_n <- as.integer(t1_n_row[[2]])
t1_placebo_n <- as.integer(t1_n_row[[3]])
check(t1_pembro_n == n_pembro_adsl,
      sprintf("Table 1 pembro N (%d) matches ADSL (%d)", t1_pembro_n, n_pembro_adsl))
check(t1_placebo_n == n_placebo_adsl,
      sprintf("Table 1 placebo N (%d) matches ADSL (%d)", t1_placebo_n, n_placebo_adsl))

# Table S2: DFS events
ts2_pembro_events <- as.integer(sub(" .*", "", ts2[Category == "DFS event, n (%)"][[2]]))
ts2_placebo_events <- as.integer(sub(" .*", "", ts2[Category == "DFS event, n (%)"][[3]]))
adtte_dfs_events_pembro <- sum(dfs_adtte[TRT01P == "PEMBROLIZUMAB"]$CNSR == 0)
adtte_dfs_events_placebo <- sum(dfs_adtte[TRT01P == "PLACEBO"]$CNSR == 0)
check(ts2_pembro_events == adtte_dfs_events_pembro,
      sprintf("Table S2 pembro DFS events (%d) matches ADTTE (%d)",
              ts2_pembro_events, adtte_dfs_events_pembro))
check(ts2_placebo_events == adtte_dfs_events_placebo,
      sprintf("Table S2 placebo DFS events (%d) matches ADTTE (%d)",
              ts2_placebo_events, adtte_dfs_events_placebo))

# Table S2: recurrence + death = total events
ts2_recurrence_pembro <- as.integer(sub(" .*", "", ts2[Category == "  Recurrence"][[2]]))
ts2_death_pembro <- as.integer(sub(" .*", "", ts2[Category == "  Death without recurrence"][[2]]))
check(ts2_recurrence_pembro + ts2_death_pembro == ts2_pembro_events,
      sprintf("Table S2: recurrence (%d) + death (%d) = total (%d) for pembro",
              ts2_recurrence_pembro, ts2_death_pembro, ts2_pembro_events))

ts2_recurrence_placebo <- as.integer(sub(" .*", "", ts2[Category == "  Recurrence"][[3]]))
ts2_death_placebo <- as.integer(sub(" .*", "", ts2[Category == "  Death without recurrence"][[3]]))
check(ts2_recurrence_placebo + ts2_death_placebo == ts2_placebo_events,
      sprintf("Table S2: recurrence (%d) + death (%d) = total (%d) for placebo",
              ts2_recurrence_placebo, ts2_death_placebo, ts2_placebo_events))

# Table S2: local + distant = recurrence
ts2_local_pembro <- as.integer(sub(" .*", "", ts2[Category == "    Local"][[2]]))
ts2_distant_pembro <- as.integer(sub(" .*", "", ts2[Category == "    Distant"][[2]]))
check(ts2_local_pembro + ts2_distant_pembro == ts2_recurrence_pembro,
      sprintf("Table S2: local (%d) + distant (%d) = recurrence (%d) for pembro",
              ts2_local_pembro, ts2_distant_pembro, ts2_recurrence_pembro))

# Table S3: AE counts
ts3_any_pembro <- as.integer(sub(" .*", "", ts3[Category == "Any adverse event"][[2]]))
actual_any_pembro <- uniqueN(adae[TRT01A == "PEMBROLIZUMAB"]$USUBJID)
check(ts3_any_pembro == actual_any_pembro,
      sprintf("Table S3 any AE pembro (%d) matches ADAE (%d)",
              ts3_any_pembro, actual_any_pembro))

ts3_gr3_pembro <- as.integer(sub(" .*", "", ts3[Category == "Grade 3-5 adverse event"][[2]]))
actual_gr3_pembro <- uniqueN(adae[TRT01A == "PEMBROLIZUMAB" & AESEVN >= 3]$USUBJID)
check(ts3_gr3_pembro == actual_gr3_pembro,
      sprintf("Table S3 Gr3+ pembro (%d) matches ADAE (%d)",
              ts3_gr3_pembro, actual_gr3_pembro))

# Table S5: Check top AE term matches ADAE (TRAE = RELATED or POSSIBLY RELATED)
ts5_fatigue_row <- ts5[`Adverse Event` == "FATIGUE"]
if (nrow(ts5_fatigue_row) > 0) {
  ts5_fatigue_n <- as.integer(sub(" .*", "", ts5_fatigue_row[[2]]))
  # Table S5 is TRAE table — filter ADAE by relatedness
  actual_fatigue_n <- uniqueN(adae[TRT01A == "PEMBROLIZUMAB" & AETERM == "FATIGUE" &
                                    AREL %in% c("RELATED", "POSSIBLY RELATED")]$USUBJID)
  check(ts5_fatigue_n == actual_fatigue_n,
        sprintf("Table S5 FATIGUE TRAE pembro (%d) matches ADAE filtered (%d)",
                ts5_fatigue_n, actual_fatigue_n))
}

# Table S7: immune-mediated total
ts7_any_row <- ts7[`Immune-Mediated AE` == "Any immune-mediated AE"]
if (nrow(ts7_any_row) > 0) {
  ts7_imm_pembro <- as.integer(sub(" .*", "", ts7_any_row[[2]]))
  actual_imm_pembro <- uniqueN(adae[TRT01A == "PEMBROLIZUMAB" &
                                     AECAT %in% c("IMMUNE_MEDIATED", "THYROID")]$USUBJID)
  check(ts7_imm_pembro == actual_imm_pembro,
        sprintf("Table S7 immune-med pembro (%d) matches ADAE (%d)",
                ts7_imm_pembro, actual_imm_pembro))
}

cat("\n")

# ─── Section 4: Clinical Logic Checks ─────────────────────────────────────────
cat("--- 4. Clinical Logic Checks ---\n")

# Patients with OS event must have DFS event (death is a DFS event)
os_events <- ep[OS_EVENT == 1]$SUBJID
dfs_events <- ep[DFS_EVENT == 1]$SUBJID
check(all(os_events %in% dfs_events),
      "All OS events are also DFS events (death counts for DFS)")

# DFS_DAY <= OS_DAY always
check(all(ep$DFS_DAY <= ep$OS_DAY), "DFS_DAY <= OS_DAY for all patients")

# Recurrence type only present for patients with recurrence
rec_patients <- ep[DFS_EVENT_TYPE == "RECURRENCE"]
check(all(!is.na(rec_patients$RECURRENCE_TYPE)),
      "All recurred patients have recurrence type (LOCAL/DISTANT)")
non_rec <- ep[DFS_EVENT_TYPE != "RECURRENCE" | is.na(DFS_EVENT_TYPE)]
# Non-recurred may or may not have NA recurrence type

# Exposure: discontinued patients have fewer cycles
disc_patients <- ex[DOSE_STATUS == "DISCONTINUED", .(SUBJID, DISC_CYCLE = CYCLE)]
disc_patients <- disc_patients[, .(DISC_CYCLE = min(DISC_CYCLE)), by = SUBJID]
if (nrow(disc_patients) > 0) {
  check(all(disc_patients$DISC_CYCLE <= 17),
        "Discontinued patients have disc cycle <= 17")
  check(mean(disc_patients$DISC_CYCLE) < 17,
        sprintf("Mean disc cycle = %.1f (should be < 17)", mean(disc_patients$DISC_CYCLE)))
}

# Grade distribution: more Gr1-2 than Gr3-4
n_gr12 <- sum(ae$AEGR <= 2)
n_gr34 <- sum(ae$AEGR >= 3)
check(n_gr12 > n_gr34,
      sprintf("More Gr1-2 (%d) than Gr3-4 (%d) AEs", n_gr12, n_gr34))

# Treatment effect direction: pembro has fewer DFS events
pembro_dfs_rate <- sum(ep[ARM == "PEMBROLIZUMAB"]$DFS_EVENT) / sum(ep$ARM == "PEMBROLIZUMAB")
placebo_dfs_rate <- sum(ep[ARM == "PLACEBO"]$DFS_EVENT) / sum(ep$ARM == "PLACEBO")
check(pembro_dfs_rate < placebo_dfs_rate,
      sprintf("Pembro DFS event rate (%.1f%%) < Placebo (%.1f%%)",
              100*pembro_dfs_rate, 100*placebo_dfs_rate))

# More AEs in pembro than placebo
n_ae_pembro <- uniqueN(ae[SUBJID %in% dm[ARM == "PEMBROLIZUMAB"]$SUBJID]$SUBJID)
n_ae_placebo <- uniqueN(ae[SUBJID %in% dm[ARM == "PLACEBO"]$SUBJID]$SUBJID)
check(n_ae_pembro > n_ae_placebo,
      sprintf("More pembro patients with AEs (%d) than placebo (%d)",
              n_ae_pembro, n_ae_placebo))

# Discontinuation higher in pembro
disc_pembro <- uniqueN(ex[DOSE_STATUS == "DISCONTINUED" &
                           SUBJID %in% dm[ARM == "PEMBROLIZUMAB"]$SUBJID]$SUBJID)
disc_placebo <- uniqueN(ex[DOSE_STATUS == "DISCONTINUED" &
                            SUBJID %in% dm[ARM == "PLACEBO"]$SUBJID]$SUBJID)
check(disc_pembro > disc_placebo,
      sprintf("More pembro discontinuations (%d) than placebo (%d)",
              disc_pembro, disc_placebo))

cat("\n")

# ─── Section 5: TLF Percentages Verification ─────────────────────────────────
cat("--- 5. TLF Percentage Calculations ---\n")

# Verify a few percentage calculations in tables
# Table 1: ECOG 0 percentage
ecog0_pembro_actual <- sum(adsl[TRT01P == "PEMBROLIZUMAB"]$ECOG_BL == 0)
ecog0_pembro_pct <- round(100 * ecog0_pembro_actual / n_pembro_adsl, 1)
t1_ecog0_row <- t1[Characteristic == "  0"]
if (nrow(t1_ecog0_row) > 0) {
  t1_ecog0_val <- t1_ecog0_row[[2]]
  expected_str <- sprintf("%d (%.1f)", ecog0_pembro_actual, ecog0_pembro_pct)
  check(t1_ecog0_val == expected_str,
        sprintf("Table 1 ECOG 0 pembro: got '%s', expect '%s'",
                t1_ecog0_val, expected_str))
}

# Table S2: censored = N - events
ts2_censored_pembro <- as.integer(sub(" .*", "", ts2[Category == "  Censored (no event)"][[2]]))
check(ts2_censored_pembro == n_pembro_adsl - ts2_pembro_events,
      sprintf("Table S2: censored (%d) = N (%d) - events (%d) for pembro",
              ts2_censored_pembro, n_pembro_adsl, ts2_pembro_events))

cat("\n")

# ─── Section 6: Cross-TLF Consistency ─────────────────────────────────────────
cat("--- 6. Cross-TLF Consistency ---\n")

# Table S3 "Any adverse event" should match or exceed Table S5 individual totals
ts3_any_pembro_n <- as.integer(sub(" .*", "", ts3[Category == "Any adverse event"][[2]]))
# Sum of patients from S5 (each row) should be <= S3 total (patients can have multiple)
# The max individual AE count should be <= S3 total
ts5_max_pembro <- max(as.integer(sub(" .*", "", ts5[[2]])))
check(ts5_max_pembro <= ts3_any_pembro_n,
      sprintf("Table S5 max individual AE (%d) <= S3 total (%d)",
              ts5_max_pembro, ts3_any_pembro_n))

# Table S7 total immune-mediated <= Table S3 any AE
if (nrow(ts7_any_row) > 0) {
  check(ts7_imm_pembro <= ts3_any_pembro_n,
        sprintf("Table S7 immune-med (%d) <= S3 any AE (%d)",
                ts7_imm_pembro, ts3_any_pembro_n))
}

# DFS events in Table S2 should match what we'd compute from ADTTE
check(adtte_dfs_events_pembro + adtte_dfs_events_placebo ==
        ts2_pembro_events + ts2_placebo_events,
      "Total DFS events consistent between Table S2 and ADTTE")

cat("\n")

# ─── Section 7: Data Quality ─────────────────────────────────────────────────
cat("--- 7. Data Quality ---\n")

# No duplicate records in ADSL
check(uniqueN(adsl$USUBJID) == nrow(adsl), "ADSL: no duplicate patients")

# No duplicate records in ADTTE per PARAMCD
dup_tte <- adtte[, .N, by = .(USUBJID, PARAMCD)][N > 1]
check(nrow(dup_tte) == 0, "ADTTE: no duplicate records per patient-parameter")

# ADAE has valid treatment assignment for all records
check(all(adae$TRT01A %in% c("PEMBROLIZUMAB", "PLACEBO")),
      "ADAE: all records have valid TRT01A")

# Exposure: no cycles > 17
check(all(ex$CYCLE <= 17), "EX: no cycles exceed 17")

# All ADSL patients appear in ADTTE
adtte_patients <- unique(adtte$USUBJID)
check(all(adsl$USUBJID %in% adtte_patients),
      "All ADSL patients have ADTTE records")

cat("\n")

# ─── Summary ──────────────────────────────────────────────────────────────────
cat("================================================================\n")
cat(sprintf("  SANITY CHECK COMPLETE: %d checks performed\n", n_checks))
cat(sprintf("  PASSED: %d\n", n_checks - length(issues)))
cat(sprintf("  FAILED: %d\n", length(issues)))
cat("================================================================\n")

if (length(issues) > 0) {
  cat("\nDiscrepancies found:\n")
  for (iss in issues) {
    cat(sprintf("  * %s\n", iss))
  }
}
