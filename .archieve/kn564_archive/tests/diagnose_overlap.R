## Diagnose the Grade3+ = Serious = TRAE overlap issue
setwd("C:/Users/lengnx/Documents/ipd_sim_examples/kn564")
library(data.table)

ae <- fread("output/source/AE.csv")

cat("=== Diagnosing Grade 3+ / Serious / TRAE Perfect Overlap ===\n\n")
cat(sprintf("Total AE records: %d\n", nrow(ae)))
cat(sprintf("Grade 3+ records: %d\n", sum(ae$AEGR >= 3)))
cat(sprintf("AESER=1 records: %d\n", sum(ae$AESER == 1)))
cat(sprintf("Related (RELATED or POSSIBLY RELATED): %d\n",
            sum(ae$AEREL %in% c("RELATED", "POSSIBLY RELATED"))))

cat("\n--- Among Grade 3+ AEs: ---\n")
gr3 <- ae[AEGR >= 3]
cat(sprintf("  All AESER=1? %d / %d (%.0f%%)\n",
            sum(gr3$AESER == 1), nrow(gr3), 100*mean(gr3$AESER == 1)))
cat(sprintf("  All Related? %d / %d (%.0f%%)\n",
            sum(gr3$AEREL %in% c("RELATED","POSSIBLY RELATED")), nrow(gr3),
            100*mean(gr3$AEREL %in% c("RELATED","POSSIBLY RELATED"))))

cat("\n--- Among AESER=1 AEs: ---\n")
ser <- ae[AESER == 1]
cat(sprintf("  All Grade 3+? %d / %d (%.0f%%)\n",
            sum(ser$AEGR >= 3), nrow(ser), 100*mean(ser$AEGR >= 3)))

cat("\n--- Root Cause ---\n")
cat("AESER is defined as: AESER = as.integer(AEGR >= 3L) in emit_source.R\n")
cat("AEREL: all AEs from pembro arm = RELATED/POSSIBLY RELATED\n")
cat("       all AEs from placebo = POSSIBLY RELATED (after fix)\n")
cat("\nThis means:\n")
cat("  1. Serious AE ≡ Grade 3+ (by construction) - WRONG\n")
cat("  2. TRAE ≡ All AEs (since all coded RELATED/POSSIBLY RELATED) - WRONG\n")
cat("  3. These should be INDEPENDENT categories in real data\n")

cat("\n--- Grade distribution ---\n")
print(table(ae$AEGR))
cat("\n--- AEREL distribution ---\n")
print(table(ae$AEREL))
cat("\n--- Cross-tab: Grade vs AESER ---\n")
print(table(Grade=ae$AEGR, Serious=ae$AESER))

cat("\n\n=== Required Fixes ===\n")
cat("1. AESER should NOT be deterministic from grade.\n")
cat("   Real SAE criteria: death, hospitalization, life-threatening, disability.\n")
cat("   Some Grade 2 can be serious (hospitalization); most Grade 3 are NOT serious.\n")
cat("   Fix: P(serious | Grade 1) ~ 0.01, P(serious | Grade 2) ~ 0.05,\n")
cat("        P(serious | Grade 3) ~ 0.35, P(serious | Grade 4) ~ 0.80\n")
cat("2. AEREL should vary independently of grade.\n")
cat("   In blinded trial, ~60-70% of AEs deemed related in active arm,\n")
cat("   ~40-50% in placebo arm.\n")
cat("   Fix: P(related) ~ 0.85 pembro, ~0.55 placebo (for general AEs)\n")
cat("        Immune/thyroid AEs: ~0.95 pembro, ~0.70 placebo\n")
