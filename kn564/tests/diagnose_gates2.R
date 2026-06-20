## Diagnose gates with corrected logic
setwd("C:/Users/lengnx/Documents/ipd_sim_examples/kn564")
library(data.table)

ae <- fread("output/source/AE.csv")
ex <- fread("output/source/EX.csv")
dm <- fread("output/source/DM.csv")

cat("=== AE Frailty (ALL patients, matching new gate logic) ===\n")
immune_aes <- ae[AECAT %in% c("IMMUNE_MEDIATED", "THYROID")]
counts <- dcast(immune_aes, SUBJID ~ AETERM, value.var = "AEGR", fun.aggregate = length)

# Include ALL patients with zeros
all_patients <- data.table(SUBJID = dm$SUBJID)
counts <- merge(all_patients, counts, by = "SUBJID", all.x = TRUE)
ae_cols <- setdiff(names(counts), "SUBJID")
for (col in ae_cols) counts[is.na(get(col)), (col) := 0L]

cat(sprintf("Matrix: %d patients x %d AE types\n", nrow(counts), length(ae_cols)))
for (col in ae_cols) {
  cat(sprintf("  %s: mean=%.3f, >0: %d (%.1f%%)\n",
              col, mean(counts[[col]]), sum(counts[[col]] > 0), 100*mean(counts[[col]] > 0)))
}

corr_mat <- cor(counts[, ..ae_cols], use = "pairwise.complete.obs")
cat("\nCorrelation matrix (all 994 patients):\n")
print(round(corr_mat, 3))
upper_tri <- corr_mat[upper.tri(corr_mat)]
cat(sprintf("\nMean pairwise correlation: %.4f (need > 0.15)\n", mean(upper_tri, na.rm=TRUE)))

cat("\n=== Discontinuation ===\n")
disc <- ex[DOSE_STATUS == "DISCONTINUED", .(DISC = TRUE), by = SUBJID]
disc_full <- merge(dm[, .(SUBJID, ARM)], disc, by = "SUBJID", all.x = TRUE)
disc_full[is.na(DISC), DISC := FALSE]
disc_pembro <- mean(disc_full[ARM == "PEMBROLIZUMAB"]$DISC)
disc_placebo <- mean(disc_full[ARM == "PLACEBO"]$DISC)
cat(sprintf("Pembro:  %.3f (target: 0.211, tol: 0.04) => %s\n",
            disc_pembro, ifelse(abs(disc_pembro - 0.211) < 0.04, "PASS", "FAIL")))
cat(sprintf("Placebo: %.3f (target: 0.022, tol: 0.04) => %s\n",
            disc_placebo, ifelse(abs(disc_placebo - 0.022) < 0.04, "PASS", "FAIL")))

cat("\n=== AE Rates ===\n")
n_pembro <- sum(dm$ARM == "PEMBROLIZUMAB")
n_placebo <- sum(dm$ARM == "PLACEBO")
ae_arm <- merge(ae, dm[, .(SUBJID, ARM)], by = "SUBJID")
trae_pembro <- uniqueN(ae_arm[ARM == "PEMBROLIZUMAB"]$SUBJID) / n_pembro
trae_placebo <- uniqueN(ae_arm[ARM == "PLACEBO"]$SUBJID) / n_placebo
gr34_pembro <- uniqueN(ae_arm[ARM == "PEMBROLIZUMAB" & AEGR >= 3]$SUBJID) / n_pembro
imm_pembro <- uniqueN(ae_arm[ARM == "PEMBROLIZUMAB" & AECAT %in% c("IMMUNE_MEDIATED","THYROID")]$SUBJID) / n_pembro
cat(sprintf("TRAE any (pembro):  %.3f (target: 0.791, tol: 0.04) => %s\n",
            trae_pembro, ifelse(abs(trae_pembro - 0.791) < 0.04, "PASS", "FAIL")))
cat(sprintf("TRAE any (placebo): %.3f (target: 0.530)\n", trae_placebo))
cat(sprintf("TRAE Gr3+ (pembro): %.3f (target: 0.186, tol: 0.04) => %s\n",
            gr34_pembro, ifelse(abs(gr34_pembro - 0.186) < 0.04, "PASS", "FAIL")))
cat(sprintf("Immune-med (pembro):%.3f (target: 0.365, tol: 0.04) => %s\n",
            imm_pembro, ifelse(abs(imm_pembro - 0.365) < 0.04, "PASS", "FAIL")))
