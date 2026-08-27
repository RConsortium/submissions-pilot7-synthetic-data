## Diagnose ae_frailty and discontinuation gates
setwd("C:/Users/lengnx/Documents/ipd_sim_examples/kn564")
library(data.table)

ae <- fread("output/source/AE.csv")
ex <- fread("output/source/EX.csv")
dm <- fread("output/source/DM.csv")

cat("=== AE Frailty Diagnosis ===\n")
immune_aes <- ae[AECAT %in% c("IMMUNE_MEDIATED", "THYROID")]
cat(sprintf("Total immune AE events: %d\n", nrow(immune_aes)))
cat(sprintf("Unique patients with immune AEs: %d\n", uniqueN(immune_aes$SUBJID)))
cat(sprintf("Unique AE terms in immune AEs: %s\n",
            paste(unique(immune_aes$AETERM), collapse=", ")))

# The gate dcast and correlate
counts <- dcast(immune_aes, SUBJID ~ AETERM, value.var = "AEGR", fun.aggregate = length)
ae_cols <- setdiff(names(counts), "SUBJID")
cat(sprintf("\nAE types in matrix: %s\n", paste(ae_cols, collapse=", ")))
cat(sprintf("Patients in matrix: %d\n", nrow(counts)))

# Show distribution per AE type
for (col in ae_cols) {
  vals <- counts[[col]]
  cat(sprintf("  %s: mean=%.2f, >0: %d/%d (%.1f%%)\n",
              col, mean(vals), sum(vals > 0), length(vals), 100*mean(vals > 0)))
}

# Correlation matrix
corr_mat <- cor(counts[, ..ae_cols], use = "pairwise.complete.obs")
cat("\nCorrelation matrix:\n")
print(round(corr_mat, 3))

upper_tri <- corr_mat[upper.tri(corr_mat)]
cat(sprintf("\nMean pairwise correlation: %.4f (need > 0.15)\n", mean(upper_tri, na.rm=TRUE)))

cat("\n=== Discontinuation Diagnosis ===\n")
# Per-patient: did they discontinue?
disc <- ex[DOSE_STATUS == "DISCONTINUED", .(DISC = TRUE), by = SUBJID]
disc_full <- merge(dm[, .(SUBJID, ARM)], disc, by = "SUBJID", all.x = TRUE)
disc_full[is.na(DISC), DISC := FALSE]

disc_pembro <- mean(disc_full[ARM == "PEMBROLIZUMAB"]$DISC)
disc_placebo <- mean(disc_full[ARM == "PLACEBO"]$DISC)
cat(sprintf("Discontinuation rate pembro:  %.3f (target: 0.211)\n", disc_pembro))
cat(sprintf("Discontinuation rate placebo: %.3f (target: 0.022)\n", disc_placebo))
cat(sprintf("Gap needed: %.3f, actual gap: %.3f\n", 0.211-0.022, disc_pembro - disc_placebo))

# How many cycles per patient?
cycles_per_patient <- ex[, .N, by = SUBJID]
cat(sprintf("\nMean cycles: %.1f, median: %d\n",
            mean(cycles_per_patient$N), median(cycles_per_patient$N)))
