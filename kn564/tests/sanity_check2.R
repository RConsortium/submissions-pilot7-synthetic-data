## Additional sanity checks — focusing on discovered issues
setwd("C:/Users/lengnx/Documents/ipd_sim_examples/kn564")
library(data.table)

adae  <- fread("output/adam/ADAE.csv")
adsl  <- fread("output/adam/ADSL.csv")
ts5   <- fread("output/tlf/table_s5_trae_5pct.csv")
ts3   <- fread("output/tlf/table_s3_ae_summary.csv")
ae    <- fread("output/source/AE.csv")
dm    <- fread("output/source/DM.csv")
ex    <- fread("output/source/EX.csv")

n_pembro <- sum(adsl$TRT01P == "PEMBROLIZUMAB")
n_placebo <- sum(adsl$TRT01P == "PLACEBO")

cat("=== Additional Discrepancy Checks ===\n\n")

# ─── Check 1: Table S5 placebo column shows zeros ────────────────────────────
cat("--- Check 1: Table S5 Placebo AE Rates ---\n")
cat("Table S5 content:\n")
print(ts5)
cat("\n")

# Verify from ADAE directly
placebo_ae_counts <- adae[TRT01A == "PLACEBO", .(
  N = uniqueN(USUBJID)
), by = AETERM]
cat("Actual placebo AE counts from ADAE:\n")
print(placebo_ae_counts[order(-N)])
cat(sprintf("\nTotal unique placebo patients with AEs: %d / %d\n",
            uniqueN(adae[TRT01A == "PLACEBO"]$USUBJID), n_placebo))

# Why are placebo values 0 in Table S5?
# Check if the TLF generation filtered by TRTEMFL or AREL
cat("\nADAE TRTEMFL values: ", paste(unique(adae$TRTEMFL), collapse=", "), "\n")
cat("ADAE AREL values: ", paste(unique(adae$AREL[!is.na(adae$AREL)]), collapse=", "), "\n")

# Check: does the TLF filter by AREL == "RELATED"?
related_placebo <- adae[TRT01A == "PLACEBO" & AREL %in% c("RELATED", "POSSIBLY RELATED")]
cat(sprintf("Placebo patients with related AEs: %d\n", uniqueN(related_placebo$USUBJID)))

cat("\n--- Check 2: Table S3 TRAE discrepancy ---\n")
cat("Table S3:\n")
print(ts3)
cat(sprintf("\nExpected TRAE any placebo: patients with AREL in (RELATED, POSSIBLY RELATED)\n"))
trae_placebo <- uniqueN(adae[TRT01A == "PLACEBO" &
                              AREL %in% c("RELATED", "POSSIBLY RELATED")]$USUBJID)
cat(sprintf("Actual TRAE placebo: %d / %d = %.1f%%\n",
            trae_placebo, n_placebo, 100*trae_placebo/n_placebo))

# S3 says "Treatment-related AE (any grade)" placebo = 95/498
# But "Any adverse event" placebo = 246/498
# TRAE should be subset of any AE
ts3_trae_placebo <- as.integer(sub(" .*", "",
  ts3[Category == "Treatment-related AE (any grade)"][[3]]))
ts3_any_placebo <- as.integer(sub(" .*", "",
  ts3[Category == "Any adverse event"][[3]]))
cat(sprintf("Table S3: Any AE placebo = %d, TRAE placebo = %d\n",
            ts3_any_placebo, ts3_trae_placebo))
if (ts3_trae_placebo > ts3_any_placebo) {
  cat("  [ISSUE] TRAE > Any AE — logically impossible!\n")
}

cat("\n--- Check 3: Table S3 'AE leading to discontinuation' ---\n")
# Currently shows 0 - but we know 20% pembro discontinued
disc_pembro <- uniqueN(ex[DOSE_STATUS == "DISCONTINUED" &
                           SUBJID %in% dm[ARM == "PEMBROLIZUMAB"]$SUBJID]$SUBJID)
cat(sprintf("Actual discontinuations from EX: pembro=%d, ", disc_pembro))
disc_placebo <- uniqueN(ex[DOSE_STATUS == "DISCONTINUED" &
                            SUBJID %in% dm[ARM == "PLACEBO"]$SUBJID]$SUBJID)
cat(sprintf("placebo=%d\n", disc_placebo))

# Check ADAE AEACN for discontinuation
disc_ae_pembro <- uniqueN(adae[TRT01A == "PEMBROLIZUMAB" & AEACN == "DISCONTINUED"]$USUBJID)
disc_ae_placebo <- uniqueN(adae[TRT01A == "PLACEBO" & AEACN == "DISCONTINUED"]$USUBJID)
cat(sprintf("ADAE AEACN=DISCONTINUED: pembro=%d, placebo=%d\n",
            disc_ae_pembro, disc_ae_placebo))
cat("Note: Disc in EX includes AE-driven + cumulative-burden + frailty-driven (not all have AEACN)\n")

cat("\n--- Check 4: Verify ECOG/age from Table 1 match ADSL ---\n")
cat(sprintf("ADSL ECOG 0 pembro: %d (%.1f%%)\n",
            sum(adsl[TRT01P=="PEMBROLIZUMAB"]$ECOG_BL == 0),
            100*mean(adsl[TRT01P=="PEMBROLIZUMAB"]$ECOG_BL == 0)))
cat(sprintf("ADSL ECOG 0 placebo: %d (%.1f%%)\n",
            sum(adsl[TRT01P=="PLACEBO"]$ECOG_BL == 0),
            100*mean(adsl[TRT01P=="PLACEBO"]$ECOG_BL == 0)))
cat(sprintf("ADSL mean age pembro: %.1f (SD %.1f)\n",
            mean(adsl[TRT01P=="PEMBROLIZUMAB"]$AGE),
            sd(adsl[TRT01P=="PEMBROLIZUMAB"]$AGE)))

cat("\n=== Summary ===\n")
cat("Issues identified:\n")
cat("1. Table S5 placebo column shows 0s — likely TLF generation filters by\n")
cat("   AREL='RELATED' which excludes most placebo AEs (coded POSSIBLY RELATED/NOT RELATED)\n")
cat("2. Table S3 'AE leading to discontinuation' = 0 — the AEACN field in ADAE\n")
cat("   does not capture all discontinuations (many are from cumulative burden pathway)\n")
cat("3. These are TLF logic issues, not data integrity issues\n")
