## Diagnose all reported findings
setwd("C:/Users/lengnx/Documents/ipd_sim_examples/kn564")
library(data.table)

ae <- fread("output/source/AE.csv")
dm <- fread("output/source/DM.csv")
ex <- fread("output/source/EX.csv")
ep <- fread("output/source/endpoints.csv")
adae <- fread("output/adam/ADAE.csv")
adtte <- fread("output/adam/ADTTE.csv")
adsl <- fread("output/adam/ADSL.csv")
ts3 <- fread("output/tlf/table_s3_ae_summary.csv")
ts5 <- fread("output/tlf/table_s5_trae_5pct.csv")
ts7 <- fread("output/tlf/table_s7_immune_mediated_ae.csv")

n_pembro <- sum(dm$ARM == "PEMBROLIZUMAB")
n_placebo <- sum(dm$ARM == "PLACEBO")

cat("================================================================\n")
cat("  FINDING DIAGNOSIS REPORT\n")
cat("================================================================\n\n")

# ─── TLF-S3-001 ──────────────────────────────────────────────────────────────
cat("--- TLF-S3-001: Grade 3-5, SAE, TRAE G3-5 implausibly identical ---\n")
cat("Table S3 values:\n")
print(ts3[Category %in% c("Grade 3-5 adverse event", "Serious adverse event",
                           "Treatment-related AE (grade 3-5)")])
gr3_p <- as.integer(sub(" .*", "", ts3[Category == "Grade 3-5 adverse event"][[2]]))
sae_p <- as.integer(sub(" .*", "", ts3[Category == "Serious adverse event"][[2]]))
trae35_p <- as.integer(sub(" .*", "", ts3[Category == "Treatment-related AE (grade 3-5)"][[2]]))
cat(sprintf("\nPembro: Gr3-5=%d, SAE=%d, TRAE Gr3-5=%d\n", gr3_p, sae_p, trae35_p))
cat(sprintf("Are they all different? Gr3!=SAE: %s, Gr3!=TRAE35: %s, SAE!=TRAE35: %s\n",
            gr3_p != sae_p, gr3_p != trae35_p, sae_p != trae35_p))

# Verify from ADAE
cat("\nFrom ADAE directly:\n")
cat(sprintf("  Gr3+ pembro: %d\n", uniqueN(adae[TRT01A=="PEMBROLIZUMAB" & AESEVN>=3]$USUBJID)))
cat(sprintf("  SAE pembro (AESER=Y or 1): %d\n",
            uniqueN(adae[TRT01A=="PEMBROLIZUMAB" & (AESER=="Y"|AESER=="1")]$USUBJID)))
cat(sprintf("  TRAE Gr3+ pembro: %d\n",
            uniqueN(adae[TRT01A=="PEMBROLIZUMAB" & AESEVN>=3 &
                          AREL %in% c("RELATED","POSSIBLY RELATED")]$USUBJID)))
cat("\n")

# ─── TLF-S3-002 ──────────────────────────────────────────────────────────────
cat("--- TLF-S3-002: Any AE = TRAE in pembro arm ---\n")
any_p <- as.integer(sub(" .*", "", ts3[Category == "Any adverse event"][[2]]))
trae_p <- as.integer(sub(" .*", "", ts3[Category == "Treatment-related AE (any grade)"][[2]]))
cat(sprintf("Any AE pembro: %d, TRAE pembro: %d, Difference: %d\n", any_p, trae_p, any_p - trae_p))
cat(sprintf("Pembro AEREL distribution:\n"))
print(table(adae[TRT01A=="PEMBROLIZUMAB"]$AREL))
cat(sprintf("Pembro NOT RELATED patients: %d\n",
            uniqueN(adae[TRT01A=="PEMBROLIZUMAB" & AREL=="NOT RELATED"]$USUBJID)))
cat("\n")

# ─── XLAY-DS-001 ─────────────────────────────────────────────────────────────
cat("--- XLAY-DS-001: DS shows 99 disc; ADAE/TLF shows 35 ---\n")
disc_ex <- ex[DOSE_STATUS == "DISCONTINUED"]
disc_ex_pembro <- uniqueN(disc_ex[SUBJID %in% dm[ARM=="PEMBROLIZUMAB"]$SUBJID]$SUBJID)
disc_adae <- uniqueN(adae[TRT01A=="PEMBROLIZUMAB" & AEACN=="DISCONTINUED"]$USUBJID)
disc_tlf <- as.integer(sub(" .*", "", ts3[Category == "AE leading to discontinuation"][[2]]))
cat(sprintf("EX DISCONTINUED (pembro): %d\n", disc_ex_pembro))
cat(sprintf("ADAE AEACN=DISCONTINUED (pembro): %d\n", disc_adae))
cat(sprintf("Table S3 AE leading to disc (pembro): %d\n", disc_tlf))
cat(sprintf("Gap: %d patients disc in EX but no AEACN=DISC in ADAE\n",
            disc_ex_pembro - disc_adae))
cat("Reason: cumulative-burden and frailty-driven disc pathways don't attribute to specific AE\n\n")

# ─── TLF-S7-001 ──────────────────────────────────────────────────────────────
cat("--- TLF-S7-001: Placebo immune-mediated AEs marked NOT RELATED ---\n")
imm_placebo <- adae[TRT01A=="PLACEBO" & AECAT %in% c("IMMUNE_MEDIATED","THYROID")]
cat(sprintf("Placebo immune/thyroid AEs: %d records from %d patients\n",
            nrow(imm_placebo), uniqueN(imm_placebo$USUBJID)))
cat("AEREL distribution in placebo immune AEs:\n")
print(table(imm_placebo$AREL))
cat(sprintf("Patients with RELATED/POSSIBLY RELATED: %d\n",
            uniqueN(imm_placebo[AREL %in% c("RELATED","POSSIBLY RELATED")]$USUBJID)))
cat("\n")

# ─── ADAM-ADTTE-001 ───────────────────────────────────────────────────────────
cat("--- ADAM-ADTTE-001: OS HR 0.784 deviates from target 0.62 ---\n")
library(survival)
os_data <- adtte[PARAMCD == "OS"]
os_data[, ARM := factor(TRT01P, levels=c("PLACEBO","PEMBROLIZUMAB"))]
cox_os <- coxph(Surv(AVAL, 1-CNSR) ~ ARM, data=os_data)
os_hr <- exp(coef(cox_os))
os_ci <- exp(confint(cox_os))
cat(sprintf("Current OS HR: %.3f (%.3f-%.3f)\n", os_hr, os_ci[1], os_ci[2]))
cat(sprintf("Target: 0.62, Deviation: %.1f%%\n", 100*(os_hr - 0.62)/0.62))
cat(sprintf("OS events: pembro=%d, placebo=%d\n",
            sum(os_data[TRT01P=="PEMBROLIZUMAB"]$CNSR==0),
            sum(os_data[TRT01P=="PLACEBO"]$CNSR==0)))
cat("\n")

# ─── ADAM-ADTTE-002 ───────────────────────────────────────────────────────────
cat("--- ADAM-ADTTE-002: All censored at day 1740 exactly ---\n")
censored <- adtte[CNSR == 1]
cat(sprintf("Censored records: %d\n", nrow(censored)))
cat(sprintf("All at day 1740? %s\n", all(censored$AVAL == 1740)))
cat(sprintf("Unique censor times: %s\n", paste(unique(censored$AVAL), collapse=", ")))
cat("Issue: administrative censoring is fixed at exactly day 1740 for all patients\n")
cat("Real trials have staggered enrollment -> variable follow-up\n\n")

# ─── SDTM-EX-001 ─────────────────────────────────────────────────────────────
cat("--- SDTM-EX-001: Zero-dose records ---\n")
zero_dose <- ex[EXDOSE == 0]
cat(sprintf("Zero-dose records: %d\n", nrow(zero_dose)))
cat(sprintf("Dose status of zero-dose: \n"))
print(table(zero_dose$DOSE_STATUS))
# Patients with ALL zero doses
all_zero <- ex[, .(total_dose = sum(EXDOSE)), by=SUBJID][total_dose == 0]
cat(sprintf("Patients with no actual drug at all: %d\n", nrow(all_zero)))
cat("\n")

# ─── TLF-S5-001 ──────────────────────────────────────────────────────────────
cat("--- TLF-S5-001: Placebo hypothyroidism 0% in S5 vs 3.6% in S7 ---\n")
cat("Table S5 (TRAE >=5%):\n")
hypo_s5 <- ts5[`Adverse Event` == "HYPOTHYROIDISM"]
if (nrow(hypo_s5) > 0) {
  cat(sprintf("  S5 placebo hypothyroidism: %s\n", hypo_s5[[4]]))
} else {
  cat("  HYPOTHYROIDISM not in S5 (below 5% threshold in placebo?)\n")
}
cat("Table S7 (immune-mediated):\n")
hypo_s7 <- ts7[`Immune-Mediated AE` == "HYPOTHYROIDISM"]
if (nrow(hypo_s7) > 0) {
  cat(sprintf("  S7 placebo hypothyroidism: %s\n", hypo_s7[[4]]))
}
cat("\nFrom ADAE:\n")
hypo_placebo_all <- uniqueN(adae[TRT01A=="PLACEBO" & AETERM=="HYPOTHYROIDISM"]$USUBJID)
hypo_placebo_rel <- uniqueN(adae[TRT01A=="PLACEBO" & AETERM=="HYPOTHYROIDISM" &
                                   AREL %in% c("RELATED","POSSIBLY RELATED")]$USUBJID)
cat(sprintf("  Placebo hypothyroidism (all): %d (%.1f%%)\n",
            hypo_placebo_all, 100*hypo_placebo_all/n_placebo))
cat(sprintf("  Placebo hypothyroidism (TRAE): %d (%.1f%%)\n",
            hypo_placebo_rel, 100*hypo_placebo_rel/n_placebo))
cat("  S5 filters by TRAE (AREL=RELATED/POSSIBLY RELATED)\n")
cat("  S7 uses AECAT filter (IMMUNE_MEDIATED/THYROID) regardless of AREL\n")
cat("  Discrepancy: thyroid events in placebo coded NOT RELATED -> excluded from S5\n")
