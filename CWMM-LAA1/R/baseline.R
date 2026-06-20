# baseline.R — Layer L₀: Baseline covariate generation
# =====================================================

source("R/dag_state.R")

#' Generate baseline covariates for all patients
#' @param params List of parameters from initial_params.json
#' @param seed Random seed
#' @return data.frame with one row per patient
generate_baseline <- function(params, seed = NULL) {
  if (!is.null(seed)) set.seed(seed)

  bp <- params$baseline
  n_total <- sum(unlist(params$sample_size))

  # --- Arm assignment (stratified by design ratio) ---
  arm <- rep(ARM_LABELS, times = unlist(params$sample_size[ARM_LABELS]))
  n <- length(arm)

  # --- Demographics ---
  age <- rtruncnorm(n, bp$age$mean, bp$age$sd, bp$age$min, bp$age$max)
  sex <- rbinom(n, 1, bp$pct_female)  # 1 = female
  race <- sample(c("White", "Black", "Other"), n, replace = TRUE,
                 prob = unlist(bp$race_probs))

  # Height conditional on sex
  height <- ifelse(sex == 1,
                   rnorm(n, bp$height_female$mean, bp$height_female$sd),
                   rnorm(n, bp$height_male$mean, bp$height_male$sd))

  # --- Anthropometrics ---
  bmi_0 <- rtruncnorm(n, bp$bmi$mean, bp$bmi$sd, bp$bmi$min, bp$bmi$max)
  bmi_strat <- ifelse(bmi_0 >= 35, ">=35", "<35")
  body_weight_0 <- bmi_0 * (height / 100)^2
  waist_0 <- rnorm(n, bp$waist$mean + 0.5 * (bmi_0 - bp$bmi$mean), bp$waist$sd * 0.7)

  # --- Metabolic markers ---
  hba1c_0 <- rtruncnorm(n, bp$hba1c$mean + 0.1 * (bmi_0 - bp$bmi$mean),
                         bp$hba1c$sd, bp$hba1c$min, bp$hba1c$max)
  fasting_glucose_0 <- rnorm(n, bp$fasting_glucose$mean + 0.02 * (hba1c_0 - bp$hba1c$mean),
                             bp$fasting_glucose$sd)
  fasting_glucose_0 <- pmax(fasting_glucose_0, 3.0)

  fasting_insulin_0 <- rlnorm(n, bp$fasting_insulin_log$meanlog + 0.005 * (bmi_0 - bp$bmi$mean),
                              bp$fasting_insulin_log$sdlog)
  homa_ir_0 <- fasting_glucose_0 * fasting_insulin_0 / 135

  # Lipids
  chol_0 <- rnorm(n, bp$chol$mean, bp$chol$sd)
  ldl_0 <- rnorm(n, bp$ldl$mean, bp$ldl$sd)
  ldl_0 <- pmax(ldl_0, 1.0)
  hdl_0 <- rnorm(n, bp$hdl$mean + 0.1 * sex, bp$hdl$sd)
  hdl_0 <- pmax(hdl_0, 0.5)
  trig_0 <- rlnorm(n, bp$trig_log$meanlog + 0.02 * (bmi_0 - bp$bmi$mean), bp$trig_log$sdlog)

  # Inflammatory

  hscrp_0 <- rlnorm(n, bp$hscrp_log$meanlog + 0.02 * (bmi_0 - bp$bmi$mean), bp$hscrp_log$sdlog)

  # Vitals
  sysbp_0 <- rnorm(n, bp$sysbp$mean + 0.1 * (age - 49) + 0.3 * (bmi_0 - bp$bmi$mean), bp$sysbp$sd)
  diabp_0 <- rnorm(n, bp$diabp$mean + 0.05 * (age - 49) + 0.15 * (bmi_0 - bp$bmi$mean), bp$diabp$sd)
  pulse_0 <- rnorm(n, bp$pulse$mean, bp$pulse$sd)

  # --- Latent frailties ---
  fp <- params$frailty
  f_GI <- rnorm(n, 0, fp$f_GI_sd)
  f_fatigue <- rnorm(n, 0, fp$f_fatigue_sd)
  f_metabolic <- rnorm(n, 0, fp$f_metabolic_sd)
  f_dropout <- rnorm(n, 0, fp$f_dropout_sd)

  # --- Assemble data.frame ---
  df <- data.frame(
    SUBJID = sprintf("LAA1-%04d", seq_len(n)),
    ARM = arm,
    AGE = round(age, 1),
    SEX = ifelse(sex == 1, "Female", "Male"),
    RACE = race,
    HEIGHT = round(height, 1),
    BMI_0 = round(bmi_0, 1),
    BMI_STRAT = bmi_strat,
    WEIGHT_0 = round(body_weight_0, 1),
    WAIST_0 = round(waist_0, 1),
    HBA1C_0 = round(hba1c_0, 1),
    GLUC_0 = round(fasting_glucose_0, 2),
    INSULIN_0 = round(fasting_insulin_0, 1),
    HOMA_IR_0 = round(homa_ir_0, 2),
    CHOL_0 = round(chol_0, 2),
    LDL_0 = round(ldl_0, 2),
    HDL_0 = round(hdl_0, 2),
    TRIG_0 = round(trig_0, 2),
    HSCRP_0 = round(hscrp_0, 2),
    SYSBP_0 = round(sysbp_0, 0),
    DIABP_0 = round(diabp_0, 0),
    PULSE_0 = round(pulse_0, 0),
    F_GI = f_GI,
    F_FATIGUE = f_fatigue,
    F_METABOLIC = f_metabolic,
    F_DROPOUT = f_dropout,
    stringsAsFactors = FALSE
  )

  df
}
