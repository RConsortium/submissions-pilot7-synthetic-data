# tlf_generate.R — Generate Tables, Listings, Figures from ADaM datasets
# Matches publication shells from Lancet 2025 eloralintide Phase 2
# ===========================================================================

library(dplyr)
library(tidyr)
library(ggplot2)
library(stringr)

# --- Load ADaM datasets ---
adsl <- read.csv("output/adam/adsl.csv", stringsAsFactors = FALSE)
adae <- read.csv("output/adam/adae.csv", stringsAsFactors = FALSE)
advs <- read.csv("output/adam/advs.csv", stringsAsFactors = FALSE)
adlb <- read.csv("output/adam/adlb.csv", stringsAsFactors = FALSE)
adeff <- read.csv("output/adam/adeff.csv", stringsAsFactors = FALSE)

outdir <- "output/tlf"
dir.create(outdir, recursive = TRUE, showWarnings = FALSE)

# Arm ordering and labels
arm_order <- c("Placebo", "1mg", "3mg", "6mg", "9mg", "6to9mg", "3to9mg")
arm_display <- c("Placebo", "Elora 1 mg", "Elora 3 mg", "Elora 6 mg",
                 "Elora 9 mg", "Elora 6\u20139 mg", "Elora 3\u20139 mg")
arm_colors <- c("grey50", "#1b9e77", "#d95f02", "#7570b3",
                "#e7298a", "#66a61e", "#e6ab02")

adsl$ARM <- factor(adsl$ARM, levels = arm_order)
adeff$ARM <- factor(adeff$ARM, levels = arm_order)

# --- Helper: write table with caption ---
write_table_with_caption <- function(tbl, filepath, caption) {
  con <- file(filepath, "w")
  writeLines(paste0("# CAPTION: ", caption), con)
  writeLines("# ---", con)
  close(con)
  write.table(tbl, filepath, sep = ",", row.names = TRUE, col.names = NA, append = TRUE)
}

# ===========================================================================
# TABLE 1: Demographics and Baseline Characteristics
# ===========================================================================
cat("Generating Table 1...\n")

mean_sd <- function(x) sprintf("%.1f (%.1f)", mean(x, na.rm=TRUE), sd(x, na.rm=TRUE))
n_pct <- function(x, val, n) sprintf("%d (%d%%)", sum(x==val, na.rm=TRUE), round(sum(x==val, na.rm=TRUE)/n*100))

tbl1_rows <- list()
for (arm in arm_order) {
  d <- adsl[adsl$ARM == arm, ]
  n <- nrow(d)
  tbl1_rows[[arm]] <- c(
    N = n,
    `Age, years` = mean_sd(d$AGE),
    Female = n_pct(d$SEX, "Female", n),
    Male = n_pct(d$SEX, "Male", n),
    White = n_pct(d$RACE, "White", n),
    `Black or African American` = n_pct(d$RACE, "Black", n),
    `Bodyweight, kg` = mean_sd(d$WEIGHTBL),
    `BMI, kg/m2` = mean_sd(d$BMIBL),
    `HbA1c, mmol/mol` = mean_sd(d$HBA1CBL),
    `Fasting glucose, mmol/L` = mean_sd(d$GLUCBL),
    `Fasting insulin, mIU/L` = mean_sd(d$INSULBL),
    `Pulse, bpm` = mean_sd(d$PULSEBL),
    `Systolic BP, mmHg` = mean_sd(d$SYSBPBL),
    `Diastolic BP, mmHg` = mean_sd(d$DIABPBL),
    `Total cholesterol, mmol/L` = mean_sd(d$CHOLBL),
    `HDL cholesterol, mmol/L` = mean_sd(d$HDLBL),
    `LDL cholesterol, mmol/L` = mean_sd(d$LDLBL),
    `Triglycerides, mmol/L` = mean_sd(d$TRIGBL),
    `hsCRP, mg/L` = mean_sd(d$HSCRPBL)
  )
}
d <- adsl; n <- nrow(d)
tbl1_rows[["Overall"]] <- c(
  N = n,
  `Age, years` = mean_sd(d$AGE),
  Female = n_pct(d$SEX, "Female", n),
  Male = n_pct(d$SEX, "Male", n),
  White = n_pct(d$RACE, "White", n),
  `Black or African American` = n_pct(d$RACE, "Black", n),
  `Bodyweight, kg` = mean_sd(d$WEIGHTBL),
  `BMI, kg/m2` = mean_sd(d$BMIBL),
  `HbA1c, mmol/mol` = mean_sd(d$HBA1CBL),
  `Fasting glucose, mmol/L` = mean_sd(d$GLUCBL),
  `Fasting insulin, mIU/L` = mean_sd(d$INSULBL),
  `Pulse, bpm` = mean_sd(d$PULSEBL),
  `Systolic BP, mmHg` = mean_sd(d$SYSBPBL),
  `Diastolic BP, mmHg` = mean_sd(d$DIABPBL),
  `Total cholesterol, mmol/L` = mean_sd(d$CHOLBL),
  `HDL cholesterol, mmol/L` = mean_sd(d$HDLBL),
  `LDL cholesterol, mmol/L` = mean_sd(d$LDLBL),
  `Triglycerides, mmol/L` = mean_sd(d$TRIGBL),
  `hsCRP, mg/L` = mean_sd(d$HSCRPBL)
)
tbl1 <- as.data.frame(do.call(cbind, tbl1_rows))
write_table_with_caption(tbl1, file.path(outdir, "Table1_Demographics.csv"),
  "Data are n (%) or mean (SD). Source: ADSL. Continuous variables computed as arithmetic mean and SD from baseline values (WEIGHTBL, BMIBL, etc.). Categorical variables computed as count and percentage of N randomised per arm. Population: all randomised participants (ITT).")

# ===========================================================================
# TABLE 2: Efficacy and Secondary Endpoints
# ===========================================================================
cat("Generating Table 2...\n")

mean_ci <- function(x) {
  x <- x[!is.na(x)]; if(length(x)<3) return("--")
  m <- mean(x); se <- sd(x)/sqrt(length(x))
  sprintf("%.1f (%.1f to %.1f)", m, m-1.96*se, m+1.96*se)
}

tbl2_primary <- sapply(arm_order, function(a) mean_ci(adeff$AVAL[adeff$ARM == a]))
advs_w48 <- advs |> filter(AVISITN == 48, ANL01FL == "Y")
tbl2_wt <- sapply(arm_order, function(a) mean_ci(advs_w48$CHG[advs_w48$ARM == a & advs_w48$PARAMCD == "WEIGHT"]))
tbl2_bmi <- sapply(arm_order, function(a) mean_ci(advs_w48$CHG[advs_w48$ARM == a & advs_w48$PARAMCD == "BMI"]))
tbl2_sbp <- sapply(arm_order, function(a) mean_ci(advs_w48$CHG[advs_w48$ARM == a & advs_w48$PARAMCD == "SYSBP"]))
tbl2_dbp <- sapply(arm_order, function(a) mean_ci(advs_w48$CHG[advs_w48$ARM == a & advs_w48$PARAMCD == "DIABP"]))
tbl2_pulse <- sapply(arm_order, function(a) mean_ci(advs_w48$CHG[advs_w48$ARM == a & advs_w48$PARAMCD == "PULSE"]))

adlb_w48 <- adlb |> filter(AVISITN == 48, ANL01FL == "Y")
tbl2_hba1c <- sapply(arm_order, function(a) mean_ci(adlb_w48$CHG[adlb_w48$ARM == a & adlb_w48$PARAMCD == "HBA1C"]))
tbl2_gluc <- sapply(arm_order, function(a) mean_ci(adlb_w48$CHG[adlb_w48$ARM == a & adlb_w48$PARAMCD == "GLUC"]))
tbl2_chol_pchg <- sapply(arm_order, function(a) mean_ci(adlb_w48$PCHG[adlb_w48$ARM == a & adlb_w48$PARAMCD == "CHOL"]))
tbl2_ldl_pchg <- sapply(arm_order, function(a) mean_ci(adlb_w48$PCHG[adlb_w48$ARM == a & adlb_w48$PARAMCD == "LDL"]))
tbl2_hdl_pchg <- sapply(arm_order, function(a) mean_ci(adlb_w48$PCHG[adlb_w48$ARM == a & adlb_w48$PARAMCD == "HDL"]))
tbl2_trig_pchg <- sapply(arm_order, function(a) mean_ci(adlb_w48$PCHG[adlb_w48$ARM == a & adlb_w48$PARAMCD == "TRIG"]))
tbl2_crp_pchg <- sapply(arm_order, function(a) mean_ci(adlb_w48$PCHG[adlb_w48$ARM == a & adlb_w48$PARAMCD == "HSCRP"]))

tbl2 <- rbind(
  `% change bodyweight (efficacy estimand)` = tbl2_primary,
  `Bodyweight change, kg` = tbl2_wt,
  `BMI change, kg/m2` = tbl2_bmi,
  `Systolic BP change, mmHg` = tbl2_sbp,
  `Diastolic BP change, mmHg` = tbl2_dbp,
  `Pulse change, bpm` = tbl2_pulse,
  `HbA1c change, mmol/mol` = tbl2_hba1c,
  `Fasting glucose change, mmol/L` = tbl2_gluc,
  `Total cholesterol, % change` = tbl2_chol_pchg,
  `LDL cholesterol, % change` = tbl2_ldl_pchg,
  `HDL cholesterol, % change` = tbl2_hdl_pchg,
  `Triglycerides, % change` = tbl2_trig_pchg,
  `hsCRP, % change` = tbl2_crp_pchg
)
colnames(tbl2) <- arm_order
write_table_with_caption(tbl2, file.path(outdir, "Table2_Endpoints.csv"),
  "Data are mean (95% CI). Source: ADEFF (primary), ADVS/ADLB at Week 48 (secondary/exploratory). Primary endpoint: percent change from baseline computed as (AVAL) from ADEFF using the efficacy estimand (on-treatment data with hypothetical strategy for discontinuation). Secondary endpoints: CHG = AVAL - BASE from ADVS/ADLB at AVISITN=48 with ANL01FL='Y'. Lipids and hsCRP show PCHG (percent change). 95% CI = mean +/- 1.96*SE where SE = SD/sqrt(n).")

# ===========================================================================
# TABLE 3: Adverse Events
# ===========================================================================
cat("Generating Table 3...\n")

teae <- adae |> filter(TRTEMFL == "Y")
ae_terms <- c("nausea", "fatigue", "diarrhoea", "constipation",
              "decreased_appetite", "vomiting", "alopecia", "headache")

tbl3_rows <- list()
for (arm in arm_order) {
  n_arm <- sum(adsl$ARM == arm)
  arm_ae <- teae[teae$ARM == arm, ]
  any_ae <- length(unique(arm_ae$SUBJID))
  serious <- length(unique(arm_ae$SUBJID[!is.na(arm_ae$AESER) & arm_ae$AESER == "Y"]))
  disc_ae <- sum(adsl$ARM == arm & !is.na(adsl$DCSREAS) & adsl$DCSREAS == "Adverse Event")
  row <- c(
    `Any AE` = sprintf("%d (%d%%)", any_ae, round(any_ae/n_arm*100)),
    `Serious AE` = sprintf("%d (%d%%)", serious, round(serious/n_arm*100)),
    `AE leading to discontinuation` = sprintf("%d (%d%%)", disc_ae, round(disc_ae/n_arm*100))
  )
  for (term in ae_terms) {
    n_with <- length(unique(arm_ae$SUBJID[arm_ae$AETERM == term]))
    row[term] <- sprintf("%d (%d%%)", n_with, round(n_with/n_arm*100))
  }
  tbl3_rows[[arm]] <- row
}
tbl3 <- as.data.frame(do.call(cbind, tbl3_rows))
write_table_with_caption(tbl3, file.path(outdir, "Table3_AE.csv"),
  "Data are n (%). Source: ADAE (treatment-emergent AEs, TRTEMFL='Y'). Denominator is all randomised participants who received at least one dose (safety population, SAFFL='Y' in ADSL). Each participant counted once per preferred term regardless of number of episodes. TEAE defined as AE with onset on or after first dose date (ASTDT >= TRTSDT) and up to 30 days post last dose. AE leading to discontinuation sourced from ADSL.DCSREAS = 'Adverse Event'.")

# ===========================================================================
# TABLE S3: AEs by Maximum Severity
# ===========================================================================
cat("Generating Table S3...\n")

tbl_s3 <- list()
for (term in ae_terms) {
  for (arm in arm_order) {
    n_arm <- sum(adsl$ARM == arm)
    arm_term <- teae[teae$ARM == arm & teae$AETERM == term, ]
    if (nrow(arm_term) > 0) {
      max_sev <- arm_term |> group_by(SUBJID) |>
        summarise(max_sev = max(AESEVN), .groups="drop")
      n_mild <- sum(max_sev$max_sev == 1)
      n_mod <- sum(max_sev$max_sev == 2)
      n_sev <- sum(max_sev$max_sev == 3)
    } else { n_mild <- n_mod <- n_sev <- 0 }
    tbl_s3[[length(tbl_s3)+1]] <- data.frame(
      AE=term, ARM=arm, N=n_arm,
      Mild=sprintf("%d (%d%%)", n_mild, round(n_mild/n_arm*100)),
      Moderate=sprintf("%d (%d%%)", n_mod, round(n_mod/n_arm*100)),
      Severe=sprintf("%d (%d%%)", n_sev, round(n_sev/n_arm*100)),
      Total=sprintf("%d (%d%%)", n_mild+n_mod+n_sev, round((n_mild+n_mod+n_sev)/n_arm*100)),
      stringsAsFactors=FALSE)
  }
}
tbl_s3_df <- do.call(rbind, tbl_s3)
con <- file(file.path(outdir, "TableS3_AE_Severity.csv"), "w")
writeLines("# CAPTION: Treatment-emergent adverse events by maximum severity. Source: ADAE (TRTEMFL='Y'). For each participant, the maximum severity (AESEVN: 1=Mild, 2=Moderate, 3=Severe) across all episodes of the given preferred term is reported. Denominator is safety population (N randomised who received >=1 dose). Participants are counted once per term at their worst severity grade.", con)
writeLines("# ---", con)
close(con)
write.table(tbl_s3_df, file.path(outdir, "TableS3_AE_Severity.csv"), sep=",", row.names=FALSE, append=TRUE)

# ===========================================================================
# TABLE S8: Responders at Weight Loss Thresholds
# ===========================================================================
cat("Generating Table S8...\n")

tbl_s8 <- list()
for (arm in arm_order) {
  ae_d <- adeff[adeff$ARM == arm & !is.na(adeff$AVAL), ]
  n <- nrow(ae_d)
  tbl_s8[[arm]] <- c(
    N = n,
    `>=5%` = sprintf("%d (%d%%)", sum(ae_d$CRIT1FL=="Y", na.rm=T), round(sum(ae_d$CRIT1FL=="Y", na.rm=T)/n*100)),
    `>=10%` = sprintf("%d (%d%%)", sum(ae_d$CRIT2FL=="Y", na.rm=T), round(sum(ae_d$CRIT2FL=="Y", na.rm=T)/n*100)),
    `>=15%` = sprintf("%d (%d%%)", sum(ae_d$CRIT3FL=="Y", na.rm=T), round(sum(ae_d$CRIT3FL=="Y", na.rm=T)/n*100)),
    `>=20%` = sprintf("%d (%d%%)", sum(ae_d$CRIT4FL=="Y", na.rm=T), round(sum(ae_d$CRIT4FL=="Y", na.rm=T)/n*100))
  )
}
tbl_s8_df <- as.data.frame(do.call(cbind, tbl_s8))
write_table_with_caption(tbl_s8_df, file.path(outdir, "TableS8_Responders.csv"),
  "Percentage of participants achieving bodyweight reduction thresholds at Week 48. Source: ADEFF (efficacy estimand). A responder is defined as a participant with percent change from baseline (AVAL) <= threshold (e.g., CRIT1FL='Y' when AVAL <= -5). Denominator is all ITT participants with non-missing Week 48 efficacy estimate. Efficacy estimand uses on-treatment trajectory with hypothetical extrapolation for discontinued participants.")

# ===========================================================================
# TABLE: Disposition
# ===========================================================================
cat("Generating Disposition Table...\n")

tbl_disp <- list()
for (arm in arm_order) {
  d <- adsl[adsl$ARM == arm, ]
  n <- nrow(d)
  n_disc <- sum(d$EOSSTT == "DISCONTINUED")
  n_comp <- sum(d$EOSSTT == "COMPLETED")
  n_ae <- sum(d$DCSREAS == "Adverse Event", na.rm=T)
  n_wbs <- sum(d$DCSREAS == "Withdrawal by Subject", na.rm=T)
  n_ltfu <- sum(d$DCSREAS == "Lost to Follow-up", na.rm=T)
  tbl_disp[[arm]] <- c(
    N = n,
    Completed = sprintf("%d (%d%%)", n_comp, round(n_comp/n*100)),
    Discontinued = sprintf("%d (%d%%)", n_disc, round(n_disc/n*100)),
    `  Due to AE` = sprintf("%d (%d%%)", n_ae, round(n_ae/n*100)),
    `  Withdrawal by participant` = sprintf("%d (%d%%)", n_wbs, round(n_wbs/n*100)),
    `  Lost to follow-up` = sprintf("%d (%d%%)", n_ltfu, round(n_ltfu/n*100))
  )
}
write_table_with_caption(as.data.frame(do.call(cbind, tbl_disp)),
  file.path(outdir, "Table_Disposition.csv"),
  "Participant disposition. Source: ADSL. Completed = EOSSTT='COMPLETED' (participants who remained in study through Week 48). Discontinued = EOSSTT='DISCONTINUED'. Reason categories derived from DCSREAS. Denominator is N randomised per arm. Percentages = n/N*100, rounded to nearest integer.")

# ===========================================================================
# Helper: Create a longitudinal figure with N-at-risk table below
# ===========================================================================

#' Build a "number at risk" table as a ggplot object to place below the main plot
make_n_at_risk_table <- function(n_data, visit_breaks, arm_order, arm_display, arm_colors) {
  # n_data should have columns: ARM, AVISITN, n
  # Filter to only visit_breaks
  tbl_data <- n_data |>
    filter(AVISITN %in% visit_breaks) |>
    mutate(ARM = factor(ARM, levels = rev(arm_order)))

  p_tbl <- ggplot(tbl_data, aes(x = AVISITN, y = ARM, label = n)) +
    geom_text(size = 2.8) +
    scale_x_continuous(breaks = visit_breaks, limits = range(visit_breaks) + c(-1, 1),
                       expand = c(0, 0)) +
    scale_y_discrete(labels = rev(arm_display)) +
    labs(x = NULL, y = NULL) +
    theme_minimal(base_size = 9) +
    theme(
      axis.text.x = element_blank(),
      axis.ticks = element_blank(),
      panel.grid = element_blank(),
      plot.margin = margin(0, 5.5, 0, 5.5)
    ) +
    ggtitle("Number of participants at each timepoint")

  p_tbl
}

#' Combine main plot and N-at-risk table into a single saved figure
save_with_n_table <- function(main_plot, n_table, filepath, width=10, height=9) {
  library(grid)
  png(filepath, width = width, height = height, units = "in", res = 150)
  # Main plot gets ~70% of height, table gets ~30%
  grid.newpage()
  pushViewport(viewport(layout = grid.layout(2, 1, heights = unit(c(0.72, 0.28), "npc"))))
  print(main_plot, vp = viewport(layout.pos.row = 1, layout.pos.col = 1))
  print(n_table, vp = viewport(layout.pos.row = 2, layout.pos.col = 1))
  dev.off()
}

# ===========================================================================
# FIGURE 2A: Mean % Change in Bodyweight Over Time (Longitudinal)
# ===========================================================================
cat("Generating Figure 2A...\n")

wt_long <- advs |>
  filter(PARAMCD == "WEIGHT", AVISITN <= 48, !is.na(PCHG)) |>
  mutate(ARM = factor(ARM, levels = arm_order))

fig2a_data <- wt_long |>
  group_by(ARM, AVISITN) |>
  summarise(mean_pchg = mean(PCHG, na.rm=TRUE),
            se = sd(PCHG, na.rm=TRUE)/sqrt(n()),
            n = n(), .groups = "drop")

fig2a_caption <- paste0(
  "Source: ADVS (PARAMCD='WEIGHT', AVISITN 0\u201348). Values are observed arithmetic means of PCHG ",
  "(percent change from baseline = [AVAL-BASE]/BASE*100) with error bars showing \u00b1 1 SE. ",
  "SE = SD/sqrt(n) at each visit. Population: ITT (all randomised). ",
  "Only on-treatment data included (ANL01FL='Y').")

fig2a_visits <- c(0, 4, 8, 12, 16, 20, 24, 28, 32, 36, 40, 44, 48)

fig2a_main <- ggplot(fig2a_data, aes(x=AVISITN, y=mean_pchg, color=ARM, group=ARM)) +
  geom_hline(yintercept=0, linetype="dashed", color="grey60") +
  geom_line(linewidth=0.8) +
  geom_point(size=1.5) +
  geom_errorbar(aes(ymin=mean_pchg-se, ymax=mean_pchg+se), width=0.8, linewidth=0.4) +
  scale_color_manual(values=arm_colors, labels=arm_display) +
  scale_x_continuous(breaks=fig2a_visits) +
  labs(x=NULL, y="Mean percent change in bodyweight\nfrom baseline (%)",
       title="Figure 2A. Mean Percent Change in Bodyweight from Baseline to Week 48",
       subtitle="Efficacy estimand; observed means \u00b1 SE",
       caption=str_wrap(fig2a_caption, width=110)) +
  theme_bw(base_size=11) +
  theme(legend.position="bottom", legend.title=element_blank(),
        plot.caption = element_text(hjust=0, size=7.5, color="grey30"),
        plot.margin = margin(5.5, 5.5, 0, 5.5))

fig2a_ntbl <- make_n_at_risk_table(fig2a_data, fig2a_visits, arm_order, arm_display, arm_colors)

save_with_n_table(fig2a_main, fig2a_ntbl,
                  file.path(outdir, "Fig2A_Weight_Change_Longitudinal.png"), width=10, height=9)

# ===========================================================================
# FIGURE 2B: Efficacy Estimand at Week 48 (Forest plot)
# ===========================================================================
cat("Generating Figure 2B...\n")

fig2b_data <- adeff |>
  filter(!is.na(AVAL)) |>
  group_by(ARM) |>
  summarise(mean_pchg = mean(AVAL), se = sd(AVAL)/sqrt(n()), n = n(),
            ci_lo = mean_pchg - 1.96*se, ci_hi = mean_pchg + 1.96*se,
            .groups="drop") |>
  mutate(ARM = factor(ARM, levels=rev(arm_order)),
         label = sprintf("%.1f%% (%.1f to %.1f)", mean_pchg, ci_lo, ci_hi))

fig2b_caption <- paste0(
  "Source: ADEFF (PARAMCD='PCHGBW', AVISIT='Week 48'). Mean and 95% CI of percent change ",
  "from baseline in bodyweight (efficacy estimand). CI = mean \u00b1 1.96*SE, SE = SD/sqrt(n). ",
  "Population: all randomised (ITT). Efficacy estimand uses on-treatment data; for discontinued ",
  "participants, the on-treatment trajectory is extrapolated to Week 48.")

fig2b <- ggplot(fig2b_data, aes(x=mean_pchg, y=ARM)) +
  geom_vline(xintercept=0, linetype="dashed", color="grey60") +
  geom_point(size=3, color="steelblue") +
  geom_errorbar(aes(xmin=ci_lo, xmax=ci_hi), width=0.2, color="steelblue",
                orientation="y") +
  geom_text(aes(label=label), hjust=-0.1, size=3.2, color="grey20") +
  scale_x_continuous(limits=c(-28, 5)) +
  labs(x="% Change in Bodyweight from Baseline at Week 48",
       y="",
       title="Figure 2B. Efficacy Estimand: Percent Weight Change at Week 48",
       subtitle="Mean (95% CI)",
       caption=str_wrap(fig2b_caption, width=100)) +
  scale_y_discrete(labels=rev(arm_display)) +
  theme_bw(base_size=11) +
  theme(plot.caption = element_text(hjust=0, size=8, color="grey30"))

ggsave(file.path(outdir, "Fig2B_Efficacy_Estimand.png"), fig2b,
       width=9, height=5.5, dpi=150)

# ===========================================================================
# FIGURE 2C: Responder Bar Chart (% achieving thresholds)
# ===========================================================================
cat("Generating Figure 2C...\n")

resp_data <- adeff |>
  filter(!is.na(AVAL)) |>
  group_by(ARM) |>
  summarise(
    n = n(),
    pct5 = sum(CRIT1FL=="Y", na.rm=T)/n*100,
    pct10 = sum(CRIT2FL=="Y", na.rm=T)/n*100,
    pct15 = sum(CRIT3FL=="Y", na.rm=T)/n*100,
    pct20 = sum(CRIT4FL=="Y", na.rm=T)/n*100,
    .groups="drop"
  ) |>
  pivot_longer(cols=c(pct5, pct10, pct15, pct20),
               names_to="Threshold", values_to="Pct") |>
  mutate(ARM = factor(ARM, levels=arm_order),
         Threshold = factor(Threshold, levels=c("pct5","pct10","pct15","pct20"),
                            labels=c("\u22655%","\u226510%","\u226515%","\u226520%")))

fig2c_caption <- paste0(
 "Source: ADEFF. Percentage of participants achieving bodyweight reductions of \u22655%, \u226510%, ",
  "\u226515%, and \u226520% from baseline at Week 48 (efficacy estimand). ",
  "A responder is counted if AVAL (percent change) \u2264 -threshold. ",
  "Percentage = n responders / N with non-missing AVAL * 100. ",
  "Population: all randomised (ITT) with available efficacy estimate.")

fig2c <- ggplot(resp_data, aes(x=Threshold, y=Pct, fill=ARM)) +
  geom_col(position=position_dodge(0.8), width=0.7) +
  geom_text(aes(label=ifelse(Pct>=3, sprintf("%.0f", Pct), "")),
            position=position_dodge(0.8), vjust=-0.3, size=2.8) +
  scale_fill_manual(values=arm_colors, labels=arm_display) +
  scale_y_continuous(expand=expansion(mult=c(0, 0.1))) +
  labs(x="Bodyweight Reduction Target",
       y="Participants (%)",
       title="Figure 2C. Percentage of Participants Achieving Weight Loss Thresholds at Week 48",
       subtitle="Efficacy estimand",
       fill="",
       caption=str_wrap(fig2c_caption, width=120)) +
  theme_bw(base_size=11) +
  theme(legend.position="bottom",
        plot.caption = element_text(hjust=0, size=8, color="grey30"))

ggsave(file.path(outdir, "Fig2C_Responders.png"), fig2c,
       width=10, height=7, dpi=150)

# ===========================================================================
# FIGURE S6: Change in HbA1c Over Time
# ===========================================================================
cat("Generating Figure S6...\n")

hba1c_data <- adlb |>
  filter(PARAMCD=="HBA1C", AVISITN<=48, !is.na(CHG)) |>
  mutate(ARM=factor(ARM, levels=arm_order)) |>
  group_by(ARM, AVISITN) |>
  summarise(mean_chg=mean(CHG, na.rm=T), se=sd(CHG, na.rm=T)/sqrt(n()), n=n(), .groups="drop")

figs6_caption <- paste0(
  "Source: ADLB (PARAMCD='HBA1C'). Observed mean change from baseline (CHG = AVAL - BASE) ",
  "at each scheduled visit with \u00b1 1 SE bars. SE = SD/sqrt(n). ",
  "Population: ITT, on-treatment data (ANL01FL='Y'). Baseline = Week 0 value (ABLFL='Y').")

figs6_visits <- c(0, 4, 8, 12, 16, 20, 24, 28, 32, 36, 40, 44, 48)

fig_s6_main <- ggplot(hba1c_data |> filter(AVISITN > 0), aes(x=AVISITN, y=mean_chg, color=ARM)) +
  geom_hline(yintercept=0, linetype="dashed", color="grey60") +
  geom_line(linewidth=0.7) + geom_point(size=1.3) +
  geom_errorbar(aes(ymin=mean_chg-se, ymax=mean_chg+se), width=0.8, linewidth=0.3) +
  scale_color_manual(values=arm_colors, labels=arm_display) +
  scale_x_continuous(breaks=figs6_visits) +
  labs(x=NULL, y="Mean change from baseline (mmol/mol)",
       title="Figure S6. Change in Glycated Haemoglobin (HbA1c) from Baseline to Week 48",
       subtitle="Observed means \u00b1 SE",
       caption=str_wrap(figs6_caption, width=110), color="") +
  theme_bw(base_size=11) +
  theme(legend.position="bottom",
        plot.caption = element_text(hjust=0, size=7.5, color="grey30"),
        plot.margin = margin(5.5, 5.5, 0, 5.5))

figs6_ntbl <- make_n_at_risk_table(hba1c_data, figs6_visits, arm_order, arm_display, arm_colors)
save_with_n_table(fig_s6_main, figs6_ntbl,
                  file.path(outdir, "FigS6_HbA1c_Change.png"), width=10, height=9)

# ===========================================================================
# FIGURE S9: Change in Pulse Over Time
# ===========================================================================
cat("Generating Figure S9...\n")

pulse_data <- advs |>
  filter(PARAMCD=="PULSE", AVISITN<=48, !is.na(CHG)) |>
  mutate(ARM=factor(ARM, levels=arm_order)) |>
  group_by(ARM, AVISITN) |>
  summarise(mean_chg=mean(CHG, na.rm=T), se=sd(CHG, na.rm=T)/sqrt(n()), n=n(), .groups="drop")

figs9_caption <- paste0(
  "Source: ADVS (PARAMCD='PULSE'). Observed mean change from baseline (CHG = AVAL - BASE) ",
  "at each visit with \u00b1 1 SE bars. SE = SD/sqrt(n). Safety analysis: data included regardless ",
  "of treatment discontinuation. Baseline = Week 0 (ABLFL='Y').")

figs9_visits <- c(0, 4, 8, 12, 16, 20, 24, 28, 32, 36, 40, 44, 48)

fig_s9_main <- ggplot(pulse_data |> filter(AVISITN > 0), aes(x=AVISITN, y=mean_chg, color=ARM)) +
  geom_hline(yintercept=0, linetype="dashed", color="grey60") +
  geom_line(linewidth=0.7) + geom_point(size=1.3) +
  geom_errorbar(aes(ymin=mean_chg-se, ymax=mean_chg+se), width=0.8, linewidth=0.3) +
  scale_color_manual(values=arm_colors, labels=arm_display) +
  scale_x_continuous(breaks=figs9_visits) +
  labs(x=NULL, y="Mean change from baseline (bpm)",
       title="Figure S9. Change in Pulse Rate from Baseline to Week 48",
       subtitle="Observed means \u00b1 SE",
       caption=str_wrap(figs9_caption, width=110), color="") +
  theme_bw(base_size=11) +
  theme(legend.position="bottom",
        plot.caption = element_text(hjust=0, size=7.5, color="grey30"),
        plot.margin = margin(5.5, 5.5, 0, 5.5))

figs9_ntbl <- make_n_at_risk_table(pulse_data, figs9_visits, arm_order, arm_display, arm_colors)
save_with_n_table(fig_s9_main, figs9_ntbl,
                  file.path(outdir, "FigS9_Pulse_Change.png"), width=10, height=9)

# ===========================================================================
# FIGURE S10: Change in Blood Pressure Over Time
# ===========================================================================
cat("Generating Figure S10...\n")

bp_data <- advs |>
  filter(PARAMCD %in% c("SYSBP","DIABP"), AVISITN<=48, !is.na(CHG)) |>
  mutate(ARM=factor(ARM, levels=arm_order),
         BP_Type = ifelse(PARAMCD=="SYSBP", "A. Systolic Blood Pressure", "B. Diastolic Blood Pressure")) |>
  group_by(ARM, AVISITN, BP_Type) |>
  summarise(mean_chg=mean(CHG, na.rm=T), se=sd(CHG, na.rm=T)/sqrt(n()), n=n(), .groups="drop")

# N-at-risk from systolic (same N for both)
bp_n_data <- bp_data |> filter(BP_Type == "A. Systolic Blood Pressure") |> select(ARM, AVISITN, n)

figs10_caption <- paste0(
  "Source: ADVS (PARAMCD='SYSBP','DIABP'). Observed mean change from baseline (CHG = AVAL - BASE) ",
  "with \u00b1 1 SE bars. SE = SD/sqrt(n). Safety analysis: data included regardless of treatment ",
  "discontinuation. Baseline = Week 0 (ABLFL='Y').")

figs10_visits <- c(0, 4, 8, 12, 16, 20, 24, 28, 32, 36, 40, 44, 48)

fig_s10_main <- ggplot(bp_data |> filter(AVISITN > 0), aes(x=AVISITN, y=mean_chg, color=ARM)) +
  geom_hline(yintercept=0, linetype="dashed", color="grey60") +
  geom_line(linewidth=0.6) + geom_point(size=1) +
  scale_color_manual(values=arm_colors, labels=arm_display) +
  scale_x_continuous(breaks=seq(0,48,8)) +
  facet_wrap(~BP_Type, ncol=1, scales="free_y") +
  labs(x=NULL, y="Mean change from baseline (mmHg)",
       title="Figure S10. Change in Blood Pressure from Baseline to Week 48",
       subtitle="Observed means \u00b1 SE",
       caption=str_wrap(figs10_caption, width=110), color="") +
  theme_bw(base_size=11) +
  theme(legend.position="bottom",
        plot.caption = element_text(hjust=0, size=7.5, color="grey30"),
        plot.margin = margin(5.5, 5.5, 0, 5.5))

figs10_ntbl <- make_n_at_risk_table(bp_n_data, figs10_visits, arm_order, arm_display, arm_colors)
save_with_n_table(fig_s10_main, figs10_ntbl,
                  file.path(outdir, "FigS10_BP_Change.png"), width=10, height=10)

# ===========================================================================
# FIGURE S17: % Change in hsCRP Over Time
# ===========================================================================
cat("Generating Figure S17...\n")

crp_data <- adlb |>
  filter(PARAMCD=="HSCRP", AVISITN<=48, !is.na(PCHG)) |>
  mutate(ARM=factor(ARM, levels=arm_order)) |>
  group_by(ARM, AVISITN) |>
  summarise(mean_pchg=mean(PCHG, na.rm=T), se=sd(PCHG, na.rm=T)/sqrt(n()), n=n(), .groups="drop")

figs17_caption <- paste0(
  "Source: ADLB (PARAMCD='HSCRP'). Percent change from baseline (PCHG = [AVAL-BASE]/BASE*100) ",
  "shown as observed mean \u00b1 1 SE at each visit. SE = SD/sqrt(n). ",
  "Population: ITT, on-treatment data (ANL01FL='Y'). Baseline = Week 0 (ABLFL='Y').")

figs17_visits <- c(0, 4, 8, 12, 16, 20, 24, 28, 32, 36, 40, 44, 48)

fig_s17_main <- ggplot(crp_data |> filter(AVISITN > 0), aes(x=AVISITN, y=mean_pchg, color=ARM)) +
  geom_hline(yintercept=0, linetype="dashed", color="grey60") +
  geom_line(linewidth=0.7) + geom_point(size=1.3) +
  scale_color_manual(values=arm_colors, labels=arm_display) +
  scale_x_continuous(breaks=figs17_visits) +
  labs(x=NULL, y="Mean percent change from baseline (%)",
       title="Figure S17. Percent Change in High-Sensitivity CRP from Baseline to Week 48",
       subtitle="Observed means \u00b1 SE",
       caption=str_wrap(figs17_caption, width=110), color="") +
  theme_bw(base_size=11) +
  theme(legend.position="bottom",
        plot.caption = element_text(hjust=0, size=7.5, color="grey30"),
        plot.margin = margin(5.5, 5.5, 0, 5.5))

figs17_ntbl <- make_n_at_risk_table(crp_data, figs17_visits, arm_order, arm_display, arm_colors)
save_with_n_table(fig_s17_main, figs17_ntbl,
                  file.path(outdir, "FigS17_hsCRP_Change.png"), width=10, height=9)

# ===========================================================================
# FIGURE S16: % Change in Triglycerides Over Time
# ===========================================================================
cat("Generating Figure S16...\n")

trig_data <- adlb |>
  filter(PARAMCD=="TRIG", AVISITN<=48, !is.na(PCHG)) |>
  mutate(ARM=factor(ARM, levels=arm_order)) |>
  group_by(ARM, AVISITN) |>
  summarise(mean_pchg=mean(PCHG, na.rm=T), se=sd(PCHG, na.rm=T)/sqrt(n()), n=n(), .groups="drop")

figs16_caption <- paste0(
  "Source: ADLB (PARAMCD='TRIG'). Percent change from baseline (PCHG = [AVAL-BASE]/BASE*100) ",
  "shown as observed mean \u00b1 1 SE at each visit. SE = SD/sqrt(n). ",
  "Population: ITT, on-treatment data (ANL01FL='Y'). Baseline = Week 0 (ABLFL='Y').")

figs16_visits <- c(0, 4, 8, 12, 16, 20, 24, 28, 32, 36, 40, 44, 48)

fig_s16_main <- ggplot(trig_data |> filter(AVISITN > 0), aes(x=AVISITN, y=mean_pchg, color=ARM)) +
  geom_hline(yintercept=0, linetype="dashed", color="grey60") +
  geom_line(linewidth=0.7) + geom_point(size=1.3) +
  scale_color_manual(values=arm_colors, labels=arm_display) +
  scale_x_continuous(breaks=figs16_visits) +
  labs(x=NULL, y="Mean percent change from baseline (%)",
       title="Figure S16. Percent Change in Triglycerides from Baseline to Week 48",
       subtitle="Observed means \u00b1 SE",
       caption=str_wrap(figs16_caption, width=110), color="") +
  theme_bw(base_size=11) +
  theme(legend.position="bottom",
        plot.caption = element_text(hjust=0, size=7.5, color="grey30"),
        plot.margin = margin(5.5, 5.5, 0, 5.5))

figs16_ntbl <- make_n_at_risk_table(trig_data, figs16_visits, arm_order, arm_display, arm_colors)
save_with_n_table(fig_s16_main, figs16_ntbl,
                  file.path(outdir, "FigS16_Triglycerides_Change.png"), width=10, height=9)

# ===========================================================================
cat("\n=== All TLFs generated in output/tlf/ ===\n")
